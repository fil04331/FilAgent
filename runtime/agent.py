"""
Agent core : Intègre le modèle et les outils
Gère les boucles de raisonnement et les appels d'outils

REFACTORED: Now uses Clean Architecture with dependency injection
"""

from __future__ import annotations

import json
import re
import hashlib
import textwrap
import time
import logging
from typing import TYPE_CHECKING, List, Dict, Optional, Union, Callable, cast
from datetime import datetime

from .config import get_config, AgentConfig
from .model_interface import GenerationConfig, init_model as _init_model
from memory.episodic import add_message, get_messages
from tools.registry import get_registry, ToolRegistry
from tools.base import ToolResult, ToolStatus, BaseTool

if TYPE_CHECKING:
    from .middleware.logging import EventLogger
    from .middleware.audittrail import DRManager
    from .middleware.provenance import ProvenanceTracker
    from .model_interface import ModelInterface
    from planner.planner import (
        HierarchicalPlanner as HierarchicalPlannerType,
        ModelInterface as PlannerModelInterface,
    )
    from planner.executor import TaskExecutor as TaskExecutorType
    from planner.verifier import TaskVerifier as TaskVerifierType


# Types stricts pour l'agent
AgentMetadataValue = Union[str, int, float, bool, List[str]]
ToolCallDict = Dict[str, Union[str, Dict[str, str]]]
# ChatResponseValue: Flexible type for complex HTN responses with nested dicts
ChatResponseValue = Union[str, int, float, bool, None, List[str], Dict[str, object]]
ToolArgsDict = Dict[str, str]

# Import des middlewares de conformité
from .middleware.logging import get_logger
from .middleware.audittrail import get_dr_manager
from .middleware.provenance import get_tracker
from planner.compliance_guardian import (
    ComplianceGuardian,
    ContextDict,
    ExecutionResultDict,
    PlanDict,
)

# Import metrics for observability
try:
    from runtime.metrics import get_agent_metrics
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False

# Import OpenTelemetry for distributed tracing
try:
    from runtime.telemetry import get_tracer, get_trace_context
    TELEMETRY_AVAILABLE = True
except ImportError:
    TELEMETRY_AVAILABLE = False
    def get_tracer(name=None):
        from contextlib import contextmanager
        class NoOpTracer:
            @contextmanager
            def start_as_current_span(self, name, **kwargs):
                yield None
        return NoOpTracer()
    def get_trace_context():
        return {}

# Import du planificateur HTN
from planner import (
    HierarchicalPlanner,
    TaskExecutor,
    TaskVerifier,
    PlanningStrategy,
    PlanningResult,
    ExecutionStrategy,
    ExecutionResult,
    VerificationLevel,
    VerificationResult,
)
from planner.task_graph import TaskStatus

# Import NEW architecture components
from architecture.router import StrategyRouter, ExecutionStrategy as RouterExecutionStrategy
from runtime.tool_executor import ToolExecutor, ToolCall
from runtime.tool_parser import ToolParser
from runtime.context_builder import ContextBuilder

# Import semantic cache manager
try:
    from memory.cache_manager import get_cache_manager
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    logging.warning("Semantic cache not available (missing dependencies)")


# Module-level logger for initialization warnings
_init_logger = logging.getLogger(__name__)


class Agent:
    """
    Agent LLM avec capacités d'appel d'outils
    
    REFACTORED: Now uses dependency injection for all components.
    Components can be injected for testing or will be created with defaults.
    """

    # Type hints for instance attributes
    config: AgentConfig
    model: Optional["ModelInterface"]
    tool_registry: ToolRegistry
    conversation_history: List[Dict[str, str]]
    logger: Optional["EventLogger"]
    dr_manager: Optional["DRManager"]
    tracker: Optional["ProvenanceTracker"]
    compliance_guardian: Optional[ComplianceGuardian]
    planner: Optional["HierarchicalPlannerType"]
    executor: Optional["TaskExecutorType"]
    verifier: Optional["TaskVerifierType"]

    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        tool_registry: Optional[ToolRegistry] = None,
        logger: Optional["EventLogger"] = None,
        dr_manager: Optional["DRManager"] = None,
        tracker: Optional["ProvenanceTracker"] = None,
        router: Optional[StrategyRouter] = None,
        tool_executor: Optional[ToolExecutor] = None,
        tool_parser: Optional[ToolParser] = None,
        context_builder: Optional[ContextBuilder] = None,
        compliance_guardian: Optional[ComplianceGuardian] = None,
    ) -> None:
        """
        Initialize Agent with dependency injection.

        Args:
            config: Agent configuration (created if None)
            tool_registry: Tool registry (created if None)
            logger: Logger instance (retrieved if None)
            dr_manager: Decision record manager (retrieved if None)
            tracker: Provenance tracker (retrieved if None)
            router: Strategy router (created if None)
            tool_executor: Tool executor (created if None)
            tool_parser: Tool parser (created if None)
            context_builder: Context builder (created if None)
            compliance_guardian: Compliance guardian (created based on config)
        """
        # Core configuration
        self.config = config or get_config()
        self.model = None  # Sera initialisé plus tard

        # Tool registry (injected or default)
        self.tool_registry = tool_registry or get_registry()

        # Legacy conversation history (kept for backward compatibility)
        self.conversation_history: List[Dict[str, str]] = []

        # Middlewares (injected or retrieved)
        if logger is None:
            try:
                self.logger = get_logger()
            except Exception as e:
                _init_logger.warning("Failed to initialize logger: %s", e)
                self.logger = None
        else:
            self.logger = logger

        if dr_manager is None:
            try:
                self.dr_manager = get_dr_manager()
            except Exception as e:
                _init_logger.warning("Failed to initialize DR manager: %s", e)
                self.dr_manager = None
        else:
            self.dr_manager = dr_manager

        if tracker is None:
            try:
                self.tracker = get_tracker()
            except Exception as e:
                _init_logger.warning("Failed to initialize tracker: %s", e)
                self.tracker = None
        else:
            self.tracker = tracker

        # ComplianceGuardian (injected or created based on config)
        if compliance_guardian is None:
            self.compliance_guardian = None
            try:
                cg_config = getattr(self.config, "compliance_guardian", None)
                if cg_config and getattr(cg_config, "enabled", False):
                    rules_path = getattr(cg_config, "rules_path", "config/compliance_rules.yaml")
                    self.compliance_guardian = ComplianceGuardian(config_path=rules_path)
            except Exception as e:
                _init_logger.warning("Failed to initialize ComplianceGuardian: %s", e)
                self.compliance_guardian = None
        else:
            self.compliance_guardian = compliance_guardian

        # NEW: Architecture components (injected or created)
        if router is None:
            # Create router based on config
            htn_config = getattr(self.config, "htn_planning", None)
            htn_enabled = htn_config and getattr(htn_config, "enabled", True)
            self.router = StrategyRouter(htn_enabled=htn_enabled)
        else:
            self.router = router
        
        if tool_executor is None:
            self.tool_executor = ToolExecutor(
                tool_registry=self.tool_registry,
                logger=self.logger,
                tracker=self.tracker,
            )
        else:
            self.tool_executor = tool_executor
        
        if tool_parser is None:
            self.tool_parser = ToolParser()
        else:
            self.tool_parser = tool_parser
        
        if context_builder is None:
            self.context_builder = ContextBuilder()
        else:
            self.context_builder = context_builder
        
        # Initialize metrics collector
        if METRICS_AVAILABLE:
            self.metrics = get_agent_metrics()
        else:
            self.metrics = None
        
        # Initialize OpenTelemetry tracer
        if TELEMETRY_AVAILABLE:
            self.tracer = get_tracer("filagent.agent")
        else:
            self.tracer = get_tracer()  # No-op tracer

        # S'assurer que les middlewares reflètent les éventuels patches actifs
        self._refresh_middlewares()

        # Initialiser le planificateur HTN (sera configuré après initialisation du modèle)
        self.planner = None
        self.executor = None
        self.verifier = None

    @staticmethod
    def _is_mock(obj: object) -> bool:
        """Déterminer si l'objet est un mock unittest."""
        return hasattr(obj, "__class__") and getattr(obj.__class__, "__module__", "").startswith("unittest.mock")

    def _refresh_middlewares(self) -> None:
        """Synchroniser logger, DR manager et tracker avec les singletons (patchables)."""
        from .middleware import logging as logging_mw
        from .middleware import audittrail as audittrail_mw
        from .middleware import provenance as provenance_mw

        try:
            current_logger = logging_mw.get_logger()
            if not self._is_mock(self.logger) and self.logger is not current_logger:
                self.logger = current_logger
        except Exception as e:
            _init_logger.warning("Failed to refresh logger: %s", e)

        try:
            current_dr_manager = audittrail_mw.get_dr_manager()
            if not self._is_mock(self.dr_manager) and self.dr_manager is not current_dr_manager:
                self.dr_manager = current_dr_manager
        except Exception as e:
            _init_logger.warning("Failed to refresh DR manager: %s", e)

        try:
            current_tracker = provenance_mw.get_tracker()
            if not self._is_mock(self.tracker) and self.tracker is not current_tracker:
                self.tracker = current_tracker
        except Exception as e:
            _init_logger.warning("Failed to refresh tracker: %s", e)

        # Rafraîchir le ComplianceGuardian si la configuration change
        try:
            cg_config = getattr(self.config, "compliance_guardian", None)
            if cg_config and getattr(cg_config, "enabled", False):
                if self.compliance_guardian is None:
                    rules_path = getattr(cg_config, "rules_path", "config/compliance_rules.yaml")
                    self.compliance_guardian = ComplianceGuardian(config_path=rules_path)
            else:
                self.compliance_guardian = None
        except Exception as e:
            _init_logger.warning("Failed to refresh ComplianceGuardian: %s", e)

    def initialize_model(self) -> None:
        """Initialiser le modèle"""
        from .model_interface import init_model

        model_config = {"context_size": self.config.model.context_size, "n_gpu_layers": self.config.model.n_gpu_layers}

        self.model = init_model(
            backend=self.config.model.backend, model_path=self.config.model.path, config=model_config
        )
        _init_logger.info("Model initialized successfully")

        # Initialiser le planificateur HTN après l'initialisation du modèle
        self._initialize_htn()

    def _initialize_htn(self) -> None:
        """Initialiser le système HTN (planificateur, exécuteur, vérificateur)"""
        # Récupérer la configuration HTN depuis config
        htn_config = getattr(self.config, "htn_planning", None)
        exec_config = getattr(self.config, "htn_execution", None)
        verif_config = getattr(self.config, "htn_verification", None)

        # Valeurs par défaut si configuration non présente
        max_depth = htn_config.max_decomposition_depth if htn_config else 3
        max_workers = exec_config.max_parallel_workers if exec_config else 4
        task_timeout = exec_config.task_timeout_sec if exec_config else 60
        # Vérifier que default_level est une string valide avant conversion
        if verif_config and hasattr(verif_config, "default_level"):
            default_level = verif_config.default_level
            # Si ce n'est pas une string (y compris Mock ou autre objet), on utilise STRICT par défaut
            if isinstance(default_level, str):
                try:
                    verif_level = VerificationLevel(default_level)
                except (ValueError, TypeError):
                    verif_level = VerificationLevel.STRICT
            else:
                verif_level = VerificationLevel.STRICT
        else:
            verif_level = VerificationLevel.STRICT

        # Ajouter le planificateur HTN
        # Note: cast nécessaire car runtime.ModelInterface (ABC) et planner.ModelInterface (Protocol)
        # sont structurellement compatibles mais mypy ne le détecte pas automatiquement
        model_for_planner = cast("PlannerModelInterface | None", self.model)
        self.planner = HierarchicalPlanner(
            model_interface=model_for_planner,
            tools_registry=self.tool_registry,
            max_decomposition_depth=max_depth,
            enable_tracing=True,
        )

        # Ajouter l'exécuteur
        self.executor = TaskExecutor(
            action_registry=self._build_action_registry(),
            strategy=ExecutionStrategy.ADAPTIVE,
            max_workers=max_workers,
            timeout_per_task_sec=task_timeout,
            enable_tracing=True,
        )

        # Ajouter le vérificateur
        self.verifier = TaskVerifier(
            default_level=verif_level,
            enable_tracing=True,
        )
        _init_logger.info("HTN system initialized successfully")

    def _resolve_verification_level(self, verif_config: object) -> VerificationLevel:
        """Normalise le niveau de vérification issu de la configuration."""
        if not verif_config or self._is_mock(verif_config):
            return VerificationLevel.STRICT

        level_value = getattr(verif_config, "default_level", None)

        if isinstance(level_value, VerificationLevel):
            return level_value

        if isinstance(level_value, str):
            try:
                return VerificationLevel(level_value.lower())
            except ValueError:
                pass

        # Certains objets de config utilisent .value pour stocker l'enum
        if hasattr(level_value, "value"):
            try:
                return VerificationLevel(str(level_value.value).lower())
            except ValueError:
                pass

        # Gestion des mocks ou valeurs inattendues
        return VerificationLevel.STRICT

    def chat(self, message: str, conversation_id: str, task_id: Optional[str] = None) -> Dict[str, ChatResponseValue]:
        """
        Analyser un message utilisateur et orchestrer la réponse de l'agent.

        REFACTORED: Now uses Router component for strategy decision.
        NEW: Checks semantic cache before routing to reduce inference costs.
        """

        # Métriques: compter requête totale
        from planner.metrics import get_metrics

        metrics = get_metrics()

        # NEW: Check semantic cache BEFORE routing decision
        cache_result = None
        if CACHE_AVAILABLE:
            try:
                cache_manager = get_cache_manager()
                cache_result = cache_manager.get(message)
                
                if cache_result:
                    # Cache hit! Return cached response immediately
                    _init_logger.debug("Cache hit (similarity: %.3f)", cache_result['similarity_score'])
                    
                    # Add cache metadata to response
                    cached_response = {
                        "response": cache_result['response']['response_text'],
                        "conversation_id": conversation_id,
                        "task_id": task_id,
                        "tools_used": cache_result['response']['tools_used'],
                        "usage": cache_result['response']['usage'],
                        "iterations": cache_result['response']['iterations'],
                        "cache_hit": True,
                        "cache_metadata": {
                            "similarity_score": cache_result['similarity_score'],
                            "hit_count": cache_result['hit_count'],
                            "age_hours": cache_result['age_hours'],
                            "entry_id": cache_result['entry_id']
                        }
                    }
                    
                    # Store user message in episodic memory
                    try:
                        add_message(
                            conversation_id=conversation_id,
                            role="user",
                            content=message,
                            task_id=task_id,
                        )
                        add_message(
                            conversation_id=conversation_id,
                            role="assistant",
                            content=cache_result['response']['response_text'],
                            task_id=task_id,
                        )
                    except Exception as e:
                        _init_logger.warning("Failed to persist cached messages: %s", e)
                    
                    return cached_response
                else:
                    _init_logger.debug("Cache miss - executing query")
            except Exception as e:
                _init_logger.warning("Cache lookup failed: %s. Falling back to normal execution.", e)
                cache_result = None

        # NOUVEAU: Use Router component for strategy decision
        routing_decision = self.router.route(message)
        
        if routing_decision.strategy == RouterExecutionStrategy.HTN:
            # Métriques: requête HTN
            metrics.htn_requests_total.labels(strategy="auto", status="requested").inc()
            result = self._run_with_htn(message, conversation_id, task_id)
        else:
            # Mode simple (pas de métriques HTN pour les requêtes simples)
            result = self._run_simple(message, conversation_id, task_id)
        
        # NEW: Store successful response in cache
        if CACHE_AVAILABLE and result.get("response"):
            try:
                cache_manager = get_cache_manager()
                cache_manager.store(
                    query=message,
                    response_text=result["response"],
                    conversation_id=conversation_id,
                    task_id=task_id,
                    tools_used=result.get("tools_used", []),
                    usage=result.get("usage", {}),
                    iterations=result.get("iterations", 1),
                    metadata={"strategy": routing_decision.strategy.value if hasattr(routing_decision.strategy, 'value') else str(routing_decision.strategy)}
                )
                _init_logger.debug("Response cached for future queries")
            except Exception as e:
                _init_logger.warning("Failed to cache response: %s", e)
        
        return result

    def _requires_planning(self, query: str) -> bool:
        """
        Détermine si HTN est nécessaire
        
        REFACTORED: Now delegates to Router component.
        This method is kept for backward compatibility with tests.
        """
        _init_logger.debug("_requires_planning called for query: %s...", query[:100])

        # Si le planificateur n'est pas initialisé, ne pas utiliser HTN
        if self.planner is None:
            _init_logger.debug("Planner not initialized, returning False")
            return False

        # Delegate to router component
        result = self.router.should_use_planning(query)
        
        _init_logger.debug("Planning decision (via Router): %s", result)

        return result

    def _run_with_htn(self, user_query: str, conversation_id: str, task_id: Optional[str] = None) -> Dict[str, ChatResponseValue]:
        """Exécution avec planification HTN"""

        # Vérifier que HTN est initialisé
        if self.planner is None or self.executor is None or self.verifier is None:
            # Fallback au mode simple si HTN non initialisé
            return self._run_simple(user_query, conversation_id, task_id)

        # Rafraîchir les middlewares patchables
        self._refresh_middlewares()

        # Métriques: enregistrer requête HTN
        from planner.metrics import get_metrics

        get_metrics()  # Initialiser les métriques

        # Logger le début de la conversation HTN
        if self.logger:
            try:
                self.logger.log_event(
                    actor="agent.core",
                    event="conversation.start.htn",
                    level="INFO",
                    conversation_id=conversation_id,
                    task_id=task_id,
                )
            except Exception as e:
                _init_logger.warning("Failed to log conversation.start.htn event: %s", e)

        # 1. Planifier
        htn_config = getattr(self.config, "htn_planning", None)
        strategy_str = htn_config.default_strategy if htn_config else "hybrid"
        strategy = PlanningStrategy.HYBRID
        if strategy_str == "rule_based":
            strategy = PlanningStrategy.RULE_BASED
        elif strategy_str == "llm_based":
            strategy = PlanningStrategy.LLM_BASED

        # Build context dict without None values
        plan_context: Dict[str, str] = {"conversation_id": conversation_id}
        if task_id is not None:
            plan_context["task_id"] = task_id

        plan_result = self.planner.plan(
            query=user_query,
            strategy=strategy,
            context=plan_context,
        )

        # Log decision record (conformité Loi 25)
        if self.dr_manager:
            try:
                prompt_hash = hashlib.sha256(user_query.encode("utf-8")).hexdigest()
                self.dr_manager.create_dr(
                    actor="agent.core",
                    task_id=task_id or conversation_id,
                    decision="planning",
                    prompt_hash=prompt_hash,
                    tools_used=[],
                    alternatives_considered=["simple_execution"],
                    constraints={
                        "strategy": strategy.value,
                        "max_depth": self.planner.max_depth,
                    },
                    expected_risk=["planning_error:low", "execution_error:medium"],
                    reasoning_markers=[f"plan_confidence:{plan_result.confidence}"],
                )
            except Exception as e:
                _init_logger.warning("Failed to create decision record for planning: %s", e)

        # 2. Exécuter
        exec_result = self.executor.execute(
            graph=plan_result.graph,
            context=plan_context,
        )

        # 3. Vérifier
        verif_config = getattr(self.config, "htn_verification", None)
        verif_level = VerificationLevel(verif_config.default_level) if verif_config else VerificationLevel.STRICT
        verifications = self.verifier.verify_graph_results(
            graph=plan_result.graph,
            level=verif_level,
        )

        # 4. Construire la réponse
        if exec_result.success:
            # Toutes les tâches critiques réussies
            response = self._format_htn_response(plan_result, exec_result, verifications, conversation_id, task_id)
        else:
            # Échec critique: fallback sur mode simple
            _init_logger.warning("HTN execution failed, falling back to simple mode")
            response = self._run_simple(user_query, conversation_id, task_id)

        # Métriques: calculer et mettre à jour métriques agrégées
        # (calculées périodiquement, pas à chaque requête pour performance)
        # Ces métriques peuvent être calculées via PromQL ou dans un job séparé

        return response

    def _run_simple(self, message: str, conversation_id: str, task_id: Optional[str] = None) -> Dict[str, ChatResponseValue]:
        """Exécution en mode simple (ancien comportement sans HTN)"""
        
        # Track conversation start time
        conversation_start_time = time.time()

        # Vérifier que le modèle est initialisé
        if self.model is None:
            raise RuntimeError("Model not initialized. Call initialize_model() first.")

        # Rafraîchir les middlewares patchables (important pour les tests)
        self._refresh_middlewares()

        # COMPLIANCE: Valider la requête avant exécution
        if self.compliance_guardian:
            try:
                cg_config = getattr(self.config, 'compliance_guardian', None)
                if cg_config and cg_config.validate_queries:
                    validation_context: ContextDict = {
                        'conversation_id': conversation_id,
                        'task_id': task_id or '',
                        'user_id': conversation_id  # Utiliser conversation_id comme proxy pour user_id
                    }
                    self.compliance_guardian.validate_query(message, validation_context)
            except Exception as e:
                # En mode strict, propager l'erreur
                cg_config = getattr(self.config, 'compliance_guardian', None)
                if cg_config and cg_config.strict_mode:
                    # Record failed conversation metric
                    if self.metrics:
                        conversation_duration = time.time() - conversation_start_time
                        self.metrics.record_conversation(
                            status="error",
                            duration_seconds=conversation_duration,
                            outcome="compliance_error",
                            iterations=0
                        )
                    raise
                else:
                    _init_logger.warning("Compliance validation warning: %s", e)

        # Logger le début de la conversation (avec fallback)
        if self.logger:
            try:
                self.logger.log_event(
                    actor="agent.core",
                    event="conversation.start",
                    level="INFO",
                    conversation_id=conversation_id,
                    task_id=task_id,
                )
            except Exception as e:
                _init_logger.warning("Failed to log conversation.start event: %s", e)

        # Enregistrer le message utilisateur en mémoire persistante
        try:
            add_message(
                conversation_id=conversation_id,
                role="user",
                content=message,
                task_id=task_id,
            )
        except Exception as e:
            _init_logger.warning("Failed to persist user message: %s", e)

        try:
            history = get_messages(conversation_id)
        except Exception as e:
            _init_logger.warning("Failed to load conversation history: %s", e)
            history = []
        trimmed_history = history[:-1] if history else history
        # REFACTORED: Use ContextBuilder
        context = self.context_builder.build_context(trimmed_history, conversation_id, task_id)

        max_iterations = 10
        iterations = 0
        final_response: Optional[str] = None
        final_prompt_hash: Optional[str] = None
        start_time = datetime.now().isoformat()
        end_time = start_time
        tools_used: List[str] = []
        usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

        current_message = message
        while iterations < max_iterations:
            iterations += 1
            generation_config = GenerationConfig(
                temperature=self.config.generation.temperature,
                top_p=self.config.generation.top_p,
                max_tokens=self.config.generation.max_tokens,
                seed=self.config.generation.seed,
                top_k=self.config.generation.top_k,
                repetition_penalty=self.config.generation.repetition_penalty,
            )

            # REFACTORED: Use ContextBuilder
            full_prompt = self.context_builder.compose_prompt(context, current_message)
            current_prompt_hash = self.context_builder.compute_prompt_hash(
                context,
                current_message,
                conversation_id,
                task_id,
            )

            # REFACTORED: Use ContextBuilder for system prompt
            system_prompt = self.context_builder.build_system_prompt(self.tool_registry)

            # Track generation start time for metrics
            generation_start_time = time.time()
            
            generation_result = self.model.generate(
                prompt=full_prompt,
                config=generation_config,
                system_prompt=system_prompt,
            )
            end_time = datetime.now().isoformat()
            
            # Record generation duration metric
            if self.metrics:
                generation_duration = time.time() - generation_start_time
                self.metrics.record_generation_duration(generation_duration)

            usage["prompt_tokens"] += generation_result.prompt_tokens
            usage["completion_tokens"] += generation_result.tokens_generated
            usage["total_tokens"] += generation_result.total_tokens

            response_text = generation_result.text.strip()

            # REFACTORED: Use ToolParser
            parsing_result = self.tool_parser.parse(generation_result, response_text)
            tool_calls: List[ToolCall] = parsing_result.tool_calls
            if tool_calls:
                # REFACTORED: Use ToolExecutor for batch execution
                execution_results = self.tool_executor.execute_batch(
                    tool_calls,
                    conversation_id,
                    task_id,
                )
                
                # Track tool names for decision records
                for result in execution_results:
                    tools_used.append(result.tool_name)

                # REFACTORED: Use ToolExecutor to format results
                formatted_results = self.tool_executor.format_results(execution_results)
                
                # REFACTORED: Use ContextBuilder to inject results
                context = self.context_builder.format_tool_results_for_context(
                    context, formatted_results
                )
                current_message = self.context_builder.create_followup_message(
                    formatted_results
                )
                continue

            final_response = response_text
            final_prompt_hash = current_prompt_hash
            break

        if final_response is None:
            final_response = "Erreur: boucle de raisonnement trop longue"
            # REFACTORED: Use ContextBuilder
            final_prompt_hash = final_prompt_hash or self.context_builder.compute_prompt_hash(
                context,
                current_message,
                conversation_id,
                task_id,
            )

        try:
            add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=final_response,
                task_id=task_id,
            )
        except Exception as e:
            _init_logger.warning("Failed to persist assistant message: %s", e)

        response_hash = hashlib.sha256(final_response.encode("utf-8")).hexdigest()
        unique_tools = list(dict.fromkeys(tools_used))
        # Ensure prompt_hash has a value for logging
        prompt_hash_for_logging = final_prompt_hash or hashlib.sha256(message.encode("utf-8")).hexdigest()

        if self.logger:
            try:
                self.logger.log_generation(
                    conversation_id=conversation_id,
                    task_id=task_id,
                    prompt_hash=prompt_hash_for_logging,
                    response_hash=response_hash,
                    tokens_used=usage["total_tokens"],
                )
            except Exception as e:
                _init_logger.warning("Failed to log generation: %s", e)

        if self.tracker:
            try:
                self.tracker.track_generation(
                    agent_id="agent:llmagenta",
                    agent_version=self.config.version,
                    task_id=task_id or conversation_id,
                    prompt_hash=prompt_hash_for_logging,
                    response_hash=response_hash,
                    start_time=start_time,
                    end_time=end_time,
                    metadata={
                        "iterations": iterations,
                        "tools_used": unique_tools,
                        "usage": usage,
                    },
                )
            except Exception as e:
                _init_logger.warning("Failed to track generation: %s", e)

        if self.dr_manager and (
            unique_tools
            or any(keyword in final_response.lower() for keyword in ["execute", "write", "delete", "create"])
        ):
            try:
                dr = self.dr_manager.create_dr(
                    actor="agent.core",
                    task_id=task_id or conversation_id,
                    decision="generate_response_with_tools" if unique_tools else "generate_response",
                    prompt_hash=prompt_hash_for_logging,
                    tools_used=unique_tools,
                    reasoning_markers=[f"iterations:{iterations}"],
                    alternatives_considered=["do_nothing", "ask_clarification"],
                    constraints={
                        "max_tokens": self.config.generation.max_tokens,
                        "temperature": self.config.generation.temperature,
                    },
                    expected_risk=["hallucination:medium", "tool_execution:low"],
                )

                if self.logger:
                    try:
                        self.logger.log_event(
                            actor="agent.core",
                            event="dr.created",
                            level="INFO",
                            conversation_id=conversation_id,
                            task_id=task_id,
                            metadata={"dr_id": dr.dr_id},
                        )
                    except Exception as e:
                        _init_logger.warning("Failed to log dr.created event: %s", e)
            except Exception as e:
                _init_logger.warning("Failed to create decision record: %s", e)

        # Record conversation metrics
        conversation_duration = time.time() - conversation_start_time
        if self.metrics:
            outcome = "max_iterations" if final_response and "trop longue" in final_response else "success"
            status = "completed" if outcome == "success" else "timeout"
            self.metrics.record_conversation(
                status=status,
                duration_seconds=conversation_duration,
                outcome=outcome,
                iterations=iterations
            )
            # Record token usage
            self.metrics.record_tokens(
                prompt_tokens=usage["prompt_tokens"],
                completion_tokens=usage["completion_tokens"]
            )
        
        # COMPLIANCE: Auditer l'exécution et générer Decision Record
        if self.compliance_guardian:
            try:
                cg_config = getattr(self.config, 'compliance_guardian', None)
                
                # Auditer l'exécution
                if cg_config and cg_config.audit_executions:
                    exec_result_audit: ExecutionResultDict = {
                        'success': final_response is not None and "Erreur" not in final_response,
                        'errors': [] if final_response is not None else ['No response generated']
                    }
                    audit_context: ContextDict = {
                        'conversation_id': conversation_id,
                        'task_id': task_id or '',
                    }
                    self.compliance_guardian.audit_execution(exec_result_audit, audit_context)

                # Générer Decision Record
                if cg_config and cg_config.auto_generate_dr:
                    dr_plan: PlanDict = {
                        'actions': [{'tool': tool, 'params': ''} for tool in unique_tools],
                        'tools_used': set(unique_tools)
                    }
                    exec_result_dr: ExecutionResultDict = {
                        'success': final_response is not None and "Erreur" not in final_response,
                        'errors': [] if final_response is not None else ['No response generated']
                    }
                    dr_context: ContextDict = {
                        'actor': 'agent.core',
                        'conversation_id': conversation_id,
                        'task_id': task_id or '',
                    }
                    self.compliance_guardian.generate_decision_record(
                        decision_type='simple_execution',
                        query=message,
                        plan=dr_plan,
                        execution_result=exec_result_dr,
                        context=dr_context
                    )
            except Exception as e:
                _init_logger.warning("Compliance audit/DR generation warning: %s", e)

        if self.logger:
            try:
                self.logger.log_event(
                    actor="agent.core",
                    event="conversation.end",
                    level="INFO",
                    conversation_id=conversation_id,
                    task_id=task_id,
                    metadata={"iterations": iterations},
                )
            except Exception as e:
                _init_logger.warning("Failed to log conversation.end event: %s", e)

        return {
            "response": final_response,
            "iterations": iterations,
            "conversation_id": conversation_id,
            "task_id": task_id,
            "tools_used": unique_tools,
            "usage": usage,
        }

    # =============================================================================
    # DEPRECATED METHODS - Kept for backward compatibility, delegate to components
    # =============================================================================
    
    def _compose_prompt(self, context: str, message: str) -> str:
        """
        DEPRECATED: Use context_builder.compose_prompt() instead.
        Kept for backward compatibility with tests.
        """
        return self.context_builder.compose_prompt(context, message)

    def _build_context(self, history: List[Dict[str, str]], conversation_id: str, task_id: Optional[str]) -> str:
        """
        DEPRECATED: Use context_builder.build_context() instead.
        Kept for backward compatibility with tests.
        """
        return self.context_builder.build_context(history, conversation_id, task_id)

    def _compute_prompt_hash(
        self,
        context: str,
        message: str,
        conversation_id: str,
        task_id: Optional[str] = None,
    ) -> str:
        """
        DEPRECATED: Use context_builder.compute_prompt_hash() instead.
        Kept for backward compatibility with tests.
        """
        return self.context_builder.compute_prompt_hash(context, message, conversation_id, task_id)

    def _get_system_prompt(self) -> str:
        """
        DEPRECATED: Use context_builder.build_system_prompt() instead.
        Kept for backward compatibility with tests.
        """
        return self.context_builder.build_system_prompt(self.tool_registry)

    def _parse_tool_calls(self, text: str) -> List[ToolCallDict]:
        """
        DEPRECATED: Use tool_parser.parse() instead.
        Kept for backward compatibility with tests.
        
        Note: Returns list of dicts for compatibility, not ToolCall objects.
        """
        # Create a mock generation result
        mock_result = type('obj', (object,), {'tool_calls': None})()
        parsing_result = self.tool_parser.parse(mock_result, text)

        # Convert ToolCall objects back to dicts for compatibility
        return [
            {"tool": tc.tool, "arguments": tc.arguments}
            for tc in parsing_result.tool_calls
        ]

    def _execute_tool(self, tool_call: ToolCallDict) -> ToolResult:
        """
        DEPRECATED: Use tool_executor.execute_tool() instead.
        Kept for backward compatibility with tests.
        """
        # Convert dict to ToolCall
        tc = ToolCall(
            tool=str(tool_call.get("tool", "")),
            arguments=tool_call.get("arguments", {}),
        )

        # Execute and convert result back to ToolResult
        exec_result = self.tool_executor.execute_tool(tc, "legacy", None)

        return ToolResult(
            status=exec_result.status,
            output=exec_result.output,
            error=exec_result.error,
        )

    def _format_tool_results(self, results: List[ToolResult]) -> str:
        """
        DEPRECATED: Use tool_executor.format_results() instead.
        Kept for backward compatibility with tests.
        """
        # Convert ToolResult list to ToolExecutionResult list
        from runtime.tool_executor import ToolExecutionResult
        exec_results = [
            ToolExecutionResult(
                tool_name=f"tool_{i}",
                status=r.status,
                output=r.output,
                error=r.error,
                start_time="",
                end_time="",
                duration_ms=0,
                input_hash="",
                output_hash="",
            )
            for i, r in enumerate(results)
        ]
        return self.tool_executor.format_results(exec_results)

    def _build_action_registry(self) -> Dict[str, Callable[[Dict[str, str]], object]]:
        """
        Mappe les actions HTN aux outils FilAgent

        Returns:
            Dict[action_name, fonction_executable]
        """
        registry: Dict[str, Callable[[Dict[str, str]], object]] = {}

        # Mapper chaque outil du registre
        tools = self.tool_registry.list_all()
        for tool_name, tool in tools.items():
            # Wrapper pour adapter l'interface (avec closure corrigée)
            def make_tool_wrapper(t: BaseTool) -> Callable[[Dict[str, str]], ToolResult]:
                def wrapper(params: Dict[str, str]) -> ToolResult:
                    return t.execute(params)

                return wrapper

            registry[tool_name] = make_tool_wrapper(tool)

        # Actions génériques
        registry["generic_execute"] = self._generic_execute

        return registry

    def _generic_execute(self, params: Dict[str, str]) -> str:
        """Action générique pour tâches non-mappées"""
        query = params.get("query", "")
        # Utiliser le mode simple pour exécuter la requête
        conversation_id = params.get("conversation_id", "default")
        task_id: Optional[str] = params.get("task_id")

        # Log input for debugging
        _init_logger.debug(
            "_generic_execute INPUT: query_length=%d chars, query_preview=%s",
            len(query), query[:100] if len(query) > 100 else query
        )

        result = self._run_simple(query, conversation_id, task_id)
        response = result.get("response", "")

        # Log output for debugging
        _init_logger.debug(
            "_generic_execute OUTPUT: response_type=%s, response_length=%d chars",
            type(response).__name__, len(str(response))
        )

        return response

    def _format_htn_response(
        self,
        plan_result: PlanningResult,
        exec_result: ExecutionResult,
        verifications: Dict[str, VerificationResult],
        conversation_id: str,
        task_id: Optional[str] = None,
    ) -> Dict[str, ChatResponseValue]:
        """Formate la réponse finale"""

        # Agréger les résultats
        results = []
        sorted_tasks = plan_result.graph.topological_sort()

        # Log aggregation details
        _init_logger.debug("_format_htn_response - Aggregating results: %d sorted tasks", len(sorted_tasks))

        for task in sorted_tasks:
            if task.status == TaskStatus.COMPLETED:
                # Log each task result
                _init_logger.debug(
                    "Processing task: %s (name=%s, result_type=%s, result_length=%d chars)",
                    task.task_id, task.name, type(task.result).__name__, len(str(task.result))
                )

                verification = verifications.get(task.task_id, None) if isinstance(verifications, dict) else None
                results.append(
                    {
                        "task": task.name,
                        "result": task.result,
                        "verified": (
                            verification.to_dict() if verification and hasattr(verification, "to_dict") else None
                        ),
                    }
                )

        # Générer le texte de réponse
        response_text = self._generate_response_from_results(results)

        # Enregistrer la réponse dans la mémoire
        try:
            add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=response_text,
                task_id=task_id,
            )
        except Exception as e:
            _init_logger.warning("Failed to persist assistant message: %s", e)

        # Logger la fin de la conversation HTN
        if self.logger:
            try:
                self.logger.log_event(
                    actor="agent.core",
                    event="conversation.end.htn",
                    level="INFO",
                    conversation_id=conversation_id,
                    task_id=task_id,
                    metadata={
                        "planning_strategy": plan_result.strategy_used.value,
                        "completed_tasks": exec_result.completed_tasks,
                        "failed_tasks": exec_result.failed_tasks,
                    },
                )
            except Exception as e:
                _init_logger.warning("Failed to log conversation.end.htn event: %s", e)

        return {
            "response": response_text,
            "plan": plan_result.to_dict(),
            "execution": exec_result.to_dict(),
            "verifications": {k: v.to_dict() for k, v in verifications.items()},
            "metadata": {
                "planning_strategy": plan_result.strategy_used.value,
                "execution_strategy": ExecutionStrategy.ADAPTIVE.value,
                "total_duration_ms": exec_result.total_duration_ms,
                "success": exec_result.success,
            },
            "conversation_id": conversation_id,
            "task_id": task_id,
            "tools_used": [],  # Les outils sont gérés par le planificateur
            "usage": {
                "prompt_tokens": 0,  # À implémenter si nécessaire
                "completion_tokens": 0,
                "total_tokens": 0,
            },
        }

    def _generate_response_from_results(self, results: List[Dict[str, object]]) -> str:
        """Génère un texte de réponse à partir des résultats des tâches"""
        if not results:
            return "Aucun résultat disponible."

        # Log input for debugging
        _init_logger.debug("_generate_response_from_results INPUT: %d results", len(results))
        for i, result in enumerate(results):
            task_result = result.get("result", "")
            _init_logger.debug(
                "Result %d: type=%s, length=%d chars",
                i+1, type(task_result).__name__, len(str(task_result))
            )

        response_parts = []
        response_parts.append("J'ai complété les tâches suivantes:\n")

        for i, result in enumerate(results, 1):
            task_name = result.get("task", "Tâche inconnue")
            task_result = result.get("result", "")
            verified = result.get("verified", None)

            response_parts.append(f"{i}. {task_name}")
            if verified and isinstance(verified, dict) and verified.get("passed", False):
                response_parts.append("   ✓ Vérifié")
            elif verified and isinstance(verified, dict):
                response_parts.append(f"   ⚠ Vérification: {verified.get('reason', 'Échec')}")

            if task_result:
                # Tronquer si extrêmement long (pour éviter les sorties ingérables)
                result_str = str(task_result)
                if len(result_str) > 4000:
                    result_str = result_str[:4000] + "...\n(résultat tronqué - trop long)"
                response_parts.append(f"   Résultat: {result_str}")

        final_response = "\n".join(response_parts)
        _init_logger.debug(
            "_generate_response_from_results OUTPUT: final_response_length=%d chars",
            len(final_response)
        )

        return final_response


# Classe helper pour l'intégration avec le serveur
class AgentManager:
    """Gestionnaire de l'agent (singleton)"""

    def __init__(self) -> None:
        self.agent: Optional[Agent] = None

    def get_agent(self) -> Agent:
        """Récupérer ou créer l'instance de l'agent"""
        if self.agent is None:
            self.agent = Agent()
            self.agent.initialize_model()
        return self.agent

    def reload_agent(self) -> Agent:
        """Recharger l'agent (utile pour les tests)"""
        self.agent = None
        return self.get_agent()


# Instance globale
_agent_manager: AgentManager = AgentManager()


def get_agent() -> Agent:
    """Récupérer l'instance de l'agent"""
    return _agent_manager.get_agent()


def init_model(backend: str, model_path: str, config: Dict[str, Union[str, int, bool]]) -> ModelInterface:
    """Proxy vers runtime.model_interface.init_model pour compatibilité tests"""
    return _init_model(backend=backend, model_path=model_path, config=config)
