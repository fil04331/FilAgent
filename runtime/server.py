"""
Serveur API pour l'agent LLM
Compatible avec le format OpenAI pour faciliter l'intégration
"""

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()  # Load .env file at startup

from fastapi import FastAPI, HTTPException, Path as FastAPIPath, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime
from pathlib import Path
import yaml
import traceback
import re
import uuid
from .config import get_config
from .agent import get_agent
from memory.episodic import get_messages, get_connection
from memory.analytics import add_interaction_log, create_tables as create_analytics_tables, compute_hash
from .middleware.logging import get_logger
from .middleware.worm import get_worm_logger

# Import Prometheus metrics (optionnel)
try:
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

# Import OpenTelemetry for distributed tracing
try:
    from .telemetry import initialize_telemetry, get_telemetry_manager, get_trace_context
    TELEMETRY_AVAILABLE = True
except ImportError:
    TELEMETRY_AVAILABLE = False
    def get_trace_context():
        return {}

app = FastAPI(
    title="FilAgent API",
    version="0.1.0",
    description="Agent LLM avec gouvernance et traçabilité",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configuration
config = get_config()

# Initialize analytics database tables
try:
    create_analytics_tables()
    print("✅ Analytics database initialized")
except Exception as e:
    print(f"⚠️ Failed to initialize analytics database: {e}")

# Initialize OpenTelemetry tracing
if TELEMETRY_AVAILABLE:
    telemetry_initialized = initialize_telemetry()
    if telemetry_initialized:
        # Instrument FastAPI application
        telemetry_manager = get_telemetry_manager()
        telemetry_manager.instrument_fastapi(app)
        print("✅ FastAPI application instrumented with OpenTelemetry")
    else:
        print("⚠️ OpenTelemetry initialization failed, tracing disabled")
else:
    print("⚠️ OpenTelemetry not available, tracing disabled")


class Message(BaseModel):
    """Message dans une conversation"""

    role: str  # "user" ou "assistant"
    content: str


class ChatRequest(BaseModel):
    """Requête de chat"""

    messages: List[Message]
    conversation_id: Optional[str] = Field(None, max_length=128, pattern=r'^[a-zA-Z0-9\-_]+$')
    task_id: Optional[str] = Field(None, max_length=128, pattern=r'^[a-zA-Z0-9\-_]+$')
    # Compatibilité OpenAI
    model: Optional[str] = Field(None, max_length=256)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=10000)

    @field_validator('conversation_id')
    @classmethod
    def validate_conversation_id(cls, v):
        """Valider le format du conversation_id"""
        if v is not None:
            if not re.match(r'^[a-zA-Z0-9\-_]+$', v):
                raise ValueError('conversation_id must contain only alphanumeric, dash, and underscore')
            if len(v) > 128:
                raise ValueError('conversation_id too long (max 128 characters)')
        return v

    @field_validator('task_id')
    @classmethod
    def validate_task_id(cls, v):
        """Valider le format du task_id"""
        if v is not None:
            if not re.match(r'^[a-zA-Z0-9\-_]+$', v):
                raise ValueError('task_id must contain only alphanumeric, dash, and underscore')
            if len(v) > 128:
                raise ValueError('task_id too long (max 128 characters)')
        return v


class ChatResponse(BaseModel):
    """Réponse du chat"""

    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[dict]
    usage: dict


class FeedbackRequest(BaseModel):
    """Requête de feedback utilisateur"""
    
    score: int = Field(..., ge=1, le=5, description="Score de satisfaction (1-5)")
    text: Optional[str] = Field(None, max_length=2000, description="Commentaire optionnel")
    latency_ms: Optional[float] = Field(None, ge=0, description="Latence observée en ms")
    tokens_used: Optional[int] = Field(None, ge=0, description="Tokens utilisés")


def _load_manual_openapi_schema() -> dict:
    """Charge le schéma OpenAPI manuel depuis la racine.

    Recherche openapi.yaml à la racine du projet.
    """
    repo_root = Path(__file__).parent.parent
    openapi_path = repo_root / "openapi.yaml"

    if not openapi_path.exists():
        # Retour à un schéma minimal si absent, pour ne pas casser /docs
        return {
            "openapi": "3.0.3",
            "info": {"title": "FilAgent API", "version": "0.1.0"},
            "paths": {},
        }

    with open(openapi_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def custom_openapi():
    """Remplace la génération auto par le schéma OpenAPI manuel."""
    if app.openapi_schema:
        return app.openapi_schema

    app.openapi_schema = _load_manual_openapi_schema()
    return app.openapi_schema


app.openapi = custom_openapi


@app.get("/")
async def root():
    """Endpoint de santé"""
    return {"service": "FilAgent", "version": config.version, "status": "healthy"}


@app.get("/health")
async def health():
    """Vérification de santé approfondie"""

    components = {
        "model": False,
        "database": False,
        "logging": False,
    }

    # Vérifier le modèle
    try:
        agent = get_agent()
        model = getattr(agent, "model", None)
        components["model"] = bool(model and getattr(model, "is_loaded", lambda: False)())
    except Exception:
        components["model"] = False

    # Vérifier la base SQLite
    try:
        with get_connection() as conn:
            conn.execute("SELECT 1")
        components["database"] = True
    except Exception:
        components["database"] = False

    # Vérifier la journalisation (fichier et WORM)
    try:
        logger = get_logger()
        worm_logger = get_worm_logger()
        log_dir = Path(logger.current_file).parent
        digest_dir = worm_logger.digest_dir
        components["logging"] = log_dir.is_dir() and digest_dir.is_dir()
    except Exception:
        components["logging"] = False

    healthy = all(components.values())

    return {
        "status": "healthy" if healthy else "degraded",
        "timestamp": datetime.now().isoformat(),
        "components": components,
    }


@app.post("/chat")
async def chat(request: ChatRequest):
    """
    Endpoint principal pour les conversations avec l'agent
    """
    try:
        # Récupérer l'agent (mode repli si indisponible)
        agent = None
        try:
            agent = get_agent()
        except Exception:
            agent = None

        # Générer un conversation_id unique avec UUID (évite les collisions)
        conversation_id = request.conversation_id or f"conv-{uuid.uuid4().hex[:16]}"

        # Trouver le dernier message utilisateur
        user_messages = [msg for msg in request.messages if msg.role == "user"]
        if not user_messages:
            return JSONResponse(status_code=400, content={"detail": "No user message provided"})

        last_user_message = user_messages[-1].content

        if agent is not None:
            result = agent.chat(message=last_user_message, conversation_id=conversation_id, task_id=request.task_id)
            response_content = result["response"]
            usage = result.get("usage", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
        else:
            # Mode stub pour conserver la conformité API en environnement sans modèle
            response_content = "[stub] Agent indisponible. Réponse factice pour tests de contrat."
            usage = {"prompt_tokens": 0, "completion_tokens": 1, "total_tokens": 1}

        response = {
            "id": conversation_id,
            "object": "chat.completion",
            "created": int(datetime.now().timestamp()),
            "model": getattr(getattr(config, "model", None), "name", "unknown"),
            "choices": [
                {"index": 0, "message": {"role": "assistant", "content": response_content}, "finish_reason": "stop"}
            ],
            "usage": {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
            "conversation_id": conversation_id,
        }
        # Ajouter un header X-Trace-ID si disponible via logger ou OpenTelemetry
        headers = {}
        
        # Try OpenTelemetry trace context first
        if TELEMETRY_AVAILABLE:
            trace_ctx = get_trace_context()
            if trace_ctx.get("trace_id"):
                headers["X-Trace-ID"] = trace_ctx["trace_id"]
        
        # Fallback to logger trace_id
        if not headers:
            try:
                logger = get_logger()
                trace_id = getattr(logger, "current_trace_id", None)
                if trace_id:
                    headers["X-Trace-ID"] = trace_id
            except Exception:
                pass

        return JSONResponse(status_code=200, content=response, headers=headers)
    except Exception as e:
        # Dernier repli : ne pas exposer les détails d'exception à l'utilisateur; journaliser l'erreur serveur uniquement
        logger = None
        try:
            logger = get_logger()
        except Exception:
            pass
        if logger is not None:
            logger.error("Exception in chat endpoint", exc_info=True)
        else:
            print("Exception in chat endpoint:")
            print(traceback.format_exc())
        fallback = {
            "id": conversation_id,
            "object": "chat.completion",
            "created": int(datetime.now().timestamp()),
            "model": getattr(getattr(config, "model", None), "name", "unknown"),
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "[stub-error] An internal error has occurred."},
                    "finish_reason": "error",
                }
            ],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "conversation_id": conversation_id,
        }
        return JSONResponse(status_code=200, content=fallback)


@app.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str = FastAPIPath(
        ...,
        max_length=128,
        pattern=r'^[a-zA-Z0-9\-_]+$',
        description="Identifiant unique de la conversation"
    )
):
    """Récupérer l'historique d'une conversation"""
    # Validation supplémentaire du conversation_id
    if not re.match(r'^[a-zA-Z0-9\-_]+$', conversation_id):
        raise HTTPException(status_code=400, detail="Invalid conversation_id format")

    if len(conversation_id) > 128:
        raise HTTPException(status_code=400, detail="conversation_id too long")

    messages = get_messages(conversation_id)

    if not messages:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {"conversation_id": conversation_id, "messages": messages}


@app.post("/api/v1/feedback/{conversation_id}")
async def submit_feedback(
    background_tasks: BackgroundTasks,
    feedback: FeedbackRequest,
    conversation_id: str = FastAPIPath(
        ...,
        max_length=128,
        pattern=r'^[a-zA-Z0-9\-_]+$',
        description="Identifiant unique de la conversation"
    )
):
    """
    Soumettre un feedback utilisateur pour une conversation.
    
    Le feedback est stocké de manière asynchrone pour ne pas ralentir la réponse.
    Capture le score de satisfaction (1-5), commentaires optionnels,
    et métriques de performance (latence, tokens).
    """
    # Validation supplémentaire du conversation_id
    if not re.match(r'^[a-zA-Z0-9\-_]+$', conversation_id):
        raise HTTPException(status_code=400, detail="Invalid conversation_id format")
    
    if len(conversation_id) > 128:
        raise HTTPException(status_code=400, detail="conversation_id too long")
    
    # Vérifier que la conversation existe
    messages = get_messages(conversation_id)
    if not messages:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Fonction pour stocker le feedback de manière asynchrone
    def store_feedback():
        try:
            # Compute hashes from the last user message and assistant response
            input_hash = None
            output_hash = None
            
            # Find last user message and last assistant message
            user_messages = [msg for msg in messages if msg['role'] == 'user']
            assistant_messages = [msg for msg in messages if msg['role'] == 'assistant']
            
            if user_messages:
                input_hash = compute_hash(user_messages[-1]['content'])
            
            if assistant_messages:
                output_hash = compute_hash(assistant_messages[-1]['content'])
            
            # Store the feedback
            add_interaction_log(
                conversation_id=conversation_id,
                user_feedback_score=feedback.score,
                user_feedback_text=feedback.text,
                input_hash=input_hash,
                output_hash=output_hash,
                latency_ms=feedback.latency_ms,
                tokens_used=feedback.tokens_used,
                metadata={
                    "submitted_at": datetime.now().isoformat(),
                    "message_count": len(messages)
                }
            )
        except Exception as e:
            # Log error but don't fail the request
            logger = None
            try:
                logger = get_logger()
            except Exception:
                pass
            if logger:
                logger.error(f"Failed to store feedback: {e}", exc_info=True)
            else:
                print(f"Failed to store feedback: {e}")
    
    # Add the storage task to background tasks
    background_tasks.add_task(store_feedback)
    
    return {
        "status": "success",
        "message": "Feedback received and will be processed",
        "conversation_id": conversation_id,
        "feedback_score": feedback.score
    }


@app.get("/metrics")
async def metrics():
    """
    Endpoint Prometheus pour exposer les métriques HTN

    Returns:
        Métriques au format Prometheus
    """
    if not PROMETHEUS_AVAILABLE:
        from fastapi.responses import PlainTextResponse

        return PlainTextResponse(
            content="# Prometheus client not available. Install with: pip install prometheus-client\n", status_code=200
        )

    from fastapi.responses import Response

    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
