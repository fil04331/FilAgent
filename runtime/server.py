"""
Serveur API pour l'agent LLM
Compatible avec le format OpenAI pour faciliter l'intégration
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import os

from .config import get_config
from .agent import get_agent
from memory.episodic import add_message, get_messages

app = FastAPI(
    title="FilAgent API",
    version="0.1.0",
    description="Agent LLM avec gouvernance et traçabilité"
)

# Configuration
config = get_config()


class Message(BaseModel):
    """Message dans une conversation"""
    role: str  # "user" ou "assistant"
    content: str


class ChatRequest(BaseModel):
    """Requête de chat"""
    messages: List[Message]
    conversation_id: Optional[str] = None
    task_id: Optional[str] = None
    # Compatibilité OpenAI
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


class ChatResponse(BaseModel):
    """Réponse du chat"""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[dict]
    usage: dict


@app.get("/")
async def root():
    """Endpoint de santé"""
    return {
        "service": "FilAgent",
        "version": config.version,
        "status": "running"
    }


@app.get("/health")
async def health():
    """Vérification de santé"""
    # TODO: Vérifier que le modèle est chargé, DB disponible, etc.
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Endpoint principal pour les conversations avec l'agent
    """
    # Récupérer l'agent
    try:
        agent = get_agent()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize agent: {str(e)}"
        )
    
    conversation_id = request.conversation_id or f"conv-{int(datetime.now().timestamp())}"
    
    # Trouver le dernier message utilisateur
    user_messages = [msg for msg in request.messages if msg.role == "user"]
    if not user_messages:
        raise HTTPException(status_code=400, detail="No user message provided")
    
    last_user_message = user_messages[-1].content
    
    # Appeler l'agent
    try:
        result = agent.chat(
            message=last_user_message,
            conversation_id=conversation_id,
            task_id=request.task_id
        )
        
        response_content = result["response"]
        
        return ChatResponse(
            id=f"chatcmpl-{int(datetime.now().timestamp())}",
            created=int(datetime.now().timestamp()),
            model=config.model.name,
            choices=[{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_content
                },
                "finish_reason": "stop"
            }],
            usage={
                "prompt_tokens": 0,  # TODO: Calculer réellement
                "completion_tokens": 0,
                "total_tokens": 0
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Agent error: {str(e)}"
        )


@app.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Récupérer l'historique d'une conversation"""
    messages = get_messages(conversation_id)
    
    if not messages:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {
        "conversation_id": conversation_id,
        "messages": messages
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
