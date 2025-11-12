"""
Agent core : Intègre le modèle et les outils
Gère les boucles de raisonnement et les appels d'outils
"""

import json
import re
import hashlib
import textwrap
from typing import List, Dict, Optional, Any
from datetime import datetime

from .config import get_config
from .model_interface import GenerationConfig, init_model as _init_model
from memory.episodic import add_message, get_messages
from tools.registry import get_registry
from tools.base import ToolResult, ToolStatus

# Import des middlewares de conformité
from .middleware.logging import get_logger
from .middleware.audittrail import get_dr_manager
from .middleware.provenance import get_tracker

# Import du ComplianceGuardian
from planner.compliance_guardian import ComplianceGuardian

# Import du planificateur HTN
from planner import (
    HierarchicalPlanner,
    TaskExecutor,
    TaskVerifier,
    PlanningStrategy,
    ExecutionStrategy,
    VerificationLevel,
)
from planner.task_graph import TaskStatus


class Agent:
    """
    Agent LLM avec capacités d'appel d'outils
    """

    def __init__(self, config=None):
        self.config = config or get_config()
        self.model = None  # Sera initialisé plus tard
        self.tool_registry = get_registry()
        self.conversation_history: List[Dict[str, str]] = []

        # Initialiser les middlewares de conformité avec fallbacks
        try:
            self.logger = get_logger()
        except Exception as e:
            print(f"⚠ Failed to initialize logger: {e}")
            self.logger = None

        try:
            self.dr_manager = get_dr_manager()
        except Exception as e:
            print(f"⚠ Failed to initialize DR manager: {e}")
            self.dr_manager = None

        try:
            self.tracker = get_tracker()
        except Exception as e:
            print(f"⚠ Failed to initialize tracker: {e}")
            self.tracker = None

        # Initialiser le ComplianceGuardian si activé dans la configuration
        try:
            cg_config = getattr(self.config, 'compliance_guardian', None)
            if cg_config and getattr(cg_config, 'enabled', True):
                rules_path = getattr(cg_config, 'rules_path', 'config/compliance_rules.yaml')
                self.compliance_guardian = ComplianceGuardian(config_path=rules_path)
            else:
                self.compliance_guardian = None
        except Exception as e:
            print(f"⚠ Failed to initialize ComplianceGuardian: {e}")
            self.compliance_guardian = None

        # S'assurer que les middlewares reflètent les éventuels patches actifs
        self._refresh_middlewares()

        # Initialiser le planificateur HTN (sera configuré après initialisation du modèle)
        self.planner = None
        self.executor = None
        self.verifier = None

    @staticmethod
    def _is_mock(obj: Any) -> bool:
        """Déterminer si l'objet est un mock unittest."""
        return hasattr(obj, "__class__") and getattr(obj.__class__, "__module__", "").startswith("unittest.mock")

    def _refresh_middlewares(self):
        """Synchroniser logger, DR manager et tracker avec les singletons (patchables)."""
        from .middleware import logging as logging_mw
        from .middleware import audittrail as audittrail_mw
        from .middleware import provenance as provenance_mw

        try:
            current_logger = logging_mw.get_logger()
            if not self._is_mock(self.logger) and self.logger is not current_logger:
                self.logger = current_logger
        except Exception as e:
            print(f"⚠ Failed to refresh logger: {e}")

        try:
            current_dr_manager = audittrail_mw.get_dr_manager()
            if not self._is_mock(self.dr_manager) and self.dr_manager is not current_dr_manager:
                self.dr_manager = current_dr_manager
        except Exception as e:
            print(f"⚠ Failed to refresh DR manager: {e}")

        try:
            current_tracker = provenance_mw.get_tracker()
            if not self._is_mock(self.tracker) and self.tracker is not current_tracker:
                self.tracker = current_tracker
        except Exception as e:
            print(f"⚠ Failed to refresh tracker: {e}")

    def initialize_model(self):
        """Initialiser le modèle"""
        from .model_interface import init_model

        model_config = {"context_size": self.config.model.context_size, "n_gpu_layers": self.config.model.n_gpu_layers}

        self.model = init_model(
            backend=self.config.model.backend, model_path=self.config.model.path, config=model_config
        )
        print("✓ Model initialized")

        # Initialiser le planificateur HTN après l'initialisation du modèle
        self._initialize_htn()

    def _initialize_htn(self):
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
        self.planner = HierarchicalPlanner(
            model_interface=self.model,
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
        print("✓ HTN system initialized")

    def _resolve_verification_level(self, verif_config: Any) -> VerificationLevel:
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

    def chat(self, message: str, conversation_id: str, task_id: Optional[str] = None) -> Dict[str, Any]:
        """Analyser un message utilisateur et orchestrer la réponse de l'agent."""

        # Métriques: compter requête totale
        from planner.metrics import get_metrics

        metrics = get_metrics()

        # NOUVEAU: Détecter si la requête nécessite HTN
        requires_htn = self._requires_planning(message)

        if requires_htn:
            # Métriques: requête HTN
            metrics.htn_requests_total.labels(strategy="auto", status="requested").inc()
            return self._run_with_htn(message, conversation_id, task_id)
        else:
            # Mode simple (pas de métriques HTN pour les requêtes simples)
            return self._run_simple(message, conversation_id, task_id)  # Ancien comportement

    def _requires_planning(self, query: str) -> bool:
        """
        Détermine si HTN est nécessaire

        Critères:
        - Mots-clés multi-étapes: "puis", "ensuite", "après"
        - Requêtes complexes: "analyse... génère... crée..."
        - Nombre de verbes d'action > 2
        """
        # Vérifier si HTN est activé
        htn_config = getattr(self.config, "htn_planning", None)
        if htn_config and not getattr(htn_config, "enabled", True):
            return False

        # Si le planificateur n'est pas initialisé, ne pas utiliser HTN
        if self.planner is None:
            return False

        keywords = ["puis", "ensuite", "après", "finalement", "et"]
        action_verbs = [
            "lis",
            "analyse",
            "génère",
            "crée",
            "calcule",
            "read",
            "analyze",
            "generate",
            "create",
            "calculate",
        ]

        has_multi_step = any(kw in query.lower() for kw in keywords)
        num_actions = sum(1 for verb in action_verbs if verb in query.lower())

        return has_multi_step or num_actions >= 2

    def _run_with_htn(self, user_query: str, conversation_id: str, task_id: Optional[str] = None) -> Dict[str, Any]:
        """Exécution avec planification HTN"""

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
                print(f"⚠ Failed to log conversation.start.htn event: {e}")

        # 1. Planifier
        htn_config = getattr(self.config, "htn_planning", None)
        strategy_str = htn_config.default_strategy if htn_config else "hybrid"
        strategy = PlanningStrategy.HYBRID
        if strategy_str == "rule_based":
            strategy = PlanningStrategy.RULE_BASED
        elif strategy_str == "llm_based":
            strategy = PlanningStrategy.LLM_BASED

        plan_result = self.planner.plan(
            query=user_query,
            strategy=strategy,
            context={"conversation_id": conversation_id, "task_id": task_id},
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
                print(f"⚠ Failed to create decision record for planning: {e}")

        # 2. Exécuter
        exec_result = self.executor.execute(
            graph=plan_result.graph,
            context={"conversation_id": conversation_id, "task_id": task_id},
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
            print("⚠ HTN execution failed, falling back to simple mode")
            response = self._run_simple(user_query, conversation_id, task_id)

        # Métriques: calculer et mettre à jour métriques agrégées
        # (calculées périodiquement, pas à chaque requête pour performance)
        # Ces métriques peuvent être calculées via PromQL ou dans un job séparé

        return response

    def _run_simple(self, message: str, conversation_id: str, task_id: Optional[str] = None) -> Dict[str, Any]:
        """Exécution en mode simple (ancien comportement sans HTN)"""

        # Rafraîchir les middlewares patchables (important pour les tests)
        self._refresh_middlewares()

        # COMPLIANCE: Valider la requête avant exécution
        if self.compliance_guardian:
            try:
                cg_config = getattr(self.config, 'compliance_guardian', None)
                if cg_config and cg_config.validate_queries:
                    context = {
                        'conversation_id': conversation_id,
                        'task_id': task_id,
                        'user_id': conversation_id  # Utiliser conversation_id comme proxy pour user_id
                    }
                    self.compliance_guardian.validate_query(message, context)
            except Exception as e:
                # En mode strict, propager l'erreur
                cg_config = getattr(self.config, 'compliance_guardian', None)
                if cg_config and cg_config.strict_mode:
                    raise
                else:
                    print(f"⚠ Compliance validation warning: {e}")

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
                print(f"⚠ Failed to log conversation.start event: {e}")

        # Enregistrer le message utilisateur en mémoire persistante
        try:
            add_message(
                conversation_id=conversation_id,
                role="user",
                content=message,
                task_id=task_id,
            )
        except Exception as e:
            print(f"⚠ Failed to persist user message: {e}")

        try:
            history = get_messages(conversation_id)
        except Exception as e:
            print(f"⚠ Failed to load conversation history: {e}")
            history = []
        trimmed_history = history[:-1] if history else history
        context = self._build_context(trimmed_history, conversation_id, task_id)

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

            full_prompt = self._compose_prompt(context, current_message)
            current_prompt_hash = self._compute_prompt_hash(
                context,
                current_message,
                conversation_id,
                task_id,
            )

            generation_result = self.model.generate(
                prompt=full_prompt,
                config=generation_config,
                system_prompt=self._get_system_prompt(),
            )
            end_time = datetime.now().isoformat()

            usage["prompt_tokens"] += generation_result.prompt_tokens
            usage["completion_tokens"] += generation_result.tokens_generated
            usage["total_tokens"] += generation_result.total_tokens

            response_text = generation_result.text.strip()

            tool_calls_attr = getattr(generation_result, "tool_calls", None)
            tool_calls: List[Dict[str, Any]] = []
            if isinstance(tool_calls_attr, list) and tool_calls_attr:
                tool_calls = tool_calls_attr
            elif "<tool_call>" in response_text:
                tool_calls = self._parse_tool_calls(response_text)
            if tool_calls:
                tool_results = []
                for tool_call in tool_calls:
                    tool_name = tool_call.get("tool")
                    arguments = tool_call.get("arguments", {})

                    if not tool_name:
                        continue

                    tool_start_time = datetime.now().isoformat()
                    execution_result = self._execute_tool(tool_call)
                    tool_end_time = datetime.now().isoformat()
                    tool_results.append(execution_result)
                    tools_used.append(tool_name)

                    if self.logger:
                        try:
                            self.logger.log_tool_call(
                                tool_name=tool_name,
                                arguments=arguments,
                                conversation_id=conversation_id,
                                task_id=task_id,
                                success=execution_result.is_success(),
                                output=execution_result.output if execution_result.output else execution_result.error,
                            )
                        except Exception as e:
                            print(f"⚠ Failed to log tool call for '{tool_name}': {e}")

                    if self.tracker:
                        try:
                            input_hash = hashlib.sha256(str(arguments).encode()).hexdigest()
                            output_payload = (
                                execution_result.output
                                if execution_result.is_success()
                                else execution_result.error or ""
                            )
                            output_hash = hashlib.sha256(str(output_payload).encode()).hexdigest()
                            self.tracker.track_tool_execution(
                                tool_name=tool_name,
                                tool_input_hash=input_hash,
                                tool_output_hash=output_hash,
                                task_id=task_id or conversation_id,
                                start_time=tool_start_time,
                                end_time=tool_end_time,
                            )
                        except Exception as e:
                            print(f"⚠ Failed to track tool execution for '{tool_name}': {e}")

                # Injecter les résultats des outils dans le contexte et relancer le modèle
                formatted_results = self._format_tool_results(tool_results)
                context = f"{context}\n\n[Résultats des outils]\n{formatted_results}".strip()
                current_message = (
                    "Voici les résultats des outils exécutés :\n"
                    f"{formatted_results}\n\nContinuez votre réponse en utilisant ces résultats."
                )
                continue

            final_response = response_text
            final_prompt_hash = current_prompt_hash
            break

        if final_response is None:
            final_response = "Erreur: boucle de raisonnement trop longue"
            final_prompt_hash = final_prompt_hash or self._compute_prompt_hash(
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
            print(f"⚠ Failed to persist assistant message: {e}")

        response_hash = hashlib.sha256(final_response.encode("utf-8")).hexdigest()
        unique_tools = list(dict.fromkeys(tools_used))

        if self.logger:
            try:
                self.logger.log_generation(
                    conversation_id=conversation_id,
                    task_id=task_id,
                    prompt_hash=final_prompt_hash,
                    response_hash=response_hash,
                    tokens_used=usage["total_tokens"],
                )
            except Exception as e:
                print(f"⚠ Failed to log generation: {e}")

        if self.tracker:
            try:
                self.tracker.track_generation(
                    agent_id="agent:llmagenta",
                    agent_version=self.config.version,
                    task_id=task_id or conversation_id,
                    prompt_hash=final_prompt_hash,
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
                print(f"⚠ Failed to track generation: {e}")

        if self.dr_manager and (
            unique_tools
            or any(keyword in final_response.lower() for keyword in ["execute", "write", "delete", "create"])
        ):
            try:
                dr = self.dr_manager.create_dr(
                    actor="agent.core",
                    task_id=task_id or conversation_id,
                    decision="generate_response_with_tools" if unique_tools else "generate_response",
                    prompt_hash=final_prompt_hash,
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
                        print(f"⚠ Failed to log dr.created event: {e}")
            except Exception as e:
                print(f"⚠ Failed to create decision record: {e}")

        # COMPLIANCE: Auditer l'exécution et générer Decision Record
        if self.compliance_guardian:
            try:
                cg_config = getattr(self.config, 'compliance_guardian', None)
                
                # Auditer l'exécution
                if cg_config and cg_config.audit_executions:
                    exec_result = {
                        'success': final_response is not None and "Erreur" not in final_response,
                        'errors': [] if final_response is not None else ['No response generated']
                    }
                    audit_context = {
                        'conversation_id': conversation_id,
                        'task_id': task_id,
                    }
                    self.compliance_guardian.audit_execution(exec_result, audit_context)
                
                # Générer Decision Record
                if cg_config and cg_config.auto_generate_dr:
                    plan = {
                        'actions': [{'tool': tool, 'params': {}} for tool in unique_tools],
                        'tools_used': unique_tools
                    }
                    exec_result = {
                        'success': final_response is not None and "Erreur" not in final_response,
                        'errors': [] if final_response is not None else ['No response generated']
                    }
                    dr_context = {
                        'actor': 'agent.core',
                        'conversation_id': conversation_id,
                        'task_id': task_id,
                    }
                    self.compliance_guardian.generate_decision_record(
                        decision_type='simple_execution',
                        query=message,
                        plan=plan,
                        execution_result=exec_result,
                        context=dr_context
                    )
            except Exception as e:
                print(f"⚠ Compliance audit/DR generation warning: {e}")

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
                print(f"⚠ Failed to log conversation.end event: {e}")

        return {
            "response": final_response,
            "iterations": iterations,
            "conversation_id": conversation_id,
            "task_id": task_id,
            "tools_used": unique_tools,
            "usage": usage,
        }

    def _compose_prompt(self, context: str, message: str) -> str:
        """Assembler le contexte et le dernier message utilisateur pour le modèle."""
        context = context.strip()
        message = message.strip()
        assistant_header = "Assistant:"
        if not context:
            return f"Utilisateur: {message}\n{assistant_header}\n"
        return f"{context}\n\nUtilisateur: {message}\n{assistant_header}\n"

    def _build_context(self, history: List[Dict], conversation_id: str, task_id: Optional[str]) -> str:
        """Construire le contexte conversationnel pour le modèle."""
        role_labels = {
            "user": "Utilisateur",
            "assistant": "Assistant",
            "system": "Système",
            "tool": "Outil",
        }

        context_messages = []
        for msg in history[-10:]:  # 10 derniers messages
            role_key = msg.get("role", "assistant")
            role = role_labels.get(role_key, role_key.capitalize())
            content = msg.get("content", "").strip()
            if not content:
                continue
            context_messages.append(f"{role}: {content}")

        return "\n".join(context_messages)

    def _compute_prompt_hash(
        self,
        context: str,
        message: str,
        conversation_id: str,
        task_id: Optional[str] = None,
    ) -> str:
        """Générer un hash stable incluant les identifiants de conversation."""

        payload = {
            "conversation_id": conversation_id,
            "task_id": task_id,
            "context": context,
            "message": message,
        }
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _get_system_prompt(self) -> str:
        """Retourner le prompt système avec les outils disponibles"""
        tools = self.tool_registry.list_all()
        tool_descriptions = []

        for tool_name, tool in tools.items():
            schema = tool.get_schema()
            tool_descriptions.append(
                f"- {tool_name}: {schema['description']}\n  Paramètres: {json.dumps(schema['parameters'])}"
            )

        raw_prompt = f"""Tu es un assistant IA capable d'utiliser des outils.

Outils disponibles:
{chr(10).join(tool_descriptions)}

Instructions:
1. Si tu as besoin d'exécuter du code Python, utilise l'outil python_sandbox
2. Si tu as besoin de lire un fichier, utilise l'outil file_read
3. Si tu as besoin de calculer, utilise l'outil math_calculator

Format pour appeler un outil:
<tool_call>
{{
    "tool": "nom_outil",
    "arguments": {{"param": "valeur"}}
}}
</tool_call>

Réponds naturellement et utilise les outils quand c'est nécessaire."""

        return textwrap.dedent(raw_prompt).strip()

    def _parse_tool_calls(self, text: str) -> List[Dict[str, Any]]:
        """
        Parser le texte pour détecter les appels d'outils
        Format attendu:
        <tool_call>
        {{"tool": "nom", "arguments": {{}}}}
        </tool_call>
        """
        pattern = r"<tool_call>(.*?)</tool_call>"
        matches = re.findall(pattern, text, re.DOTALL)

        tool_calls = []
        for match in matches:
            try:
                tool_json = json.loads(match.strip())
                if "tool" in tool_json and "arguments" in tool_json:
                    tool_calls.append(tool_json)
            except json.JSONDecodeError:
                continue

        return tool_calls

    def _execute_tool(self, tool_call: Dict[str, Any]) -> ToolResult:
        """Exécuter un outil"""
        tool_name = tool_call.get("tool")
        arguments = tool_call.get("arguments", {})

        tool = self.tool_registry.get_tool(tool_name)

        if not tool:
            return ToolResult(status=ToolStatus.ERROR, output="", error=f"Tool not found: {tool_name}")

        # Exécuter l'outil
        result = tool.execute(arguments)
        return result

    def _format_tool_results(self, results: List[ToolResult]) -> str:
        """Formatter les résultats des outils pour le contexte"""
        formatted = []
        for i, result in enumerate(results, 1):
            if result.is_success():
                formatted.append(f"Outil {i}: SUCCESS\n{result.output}")
            else:
                formatted.append(f"Outil {i}: ERROR\n{result.error}")
        return "\n---\n".join(formatted)

    def _build_action_registry(self) -> Dict[str, Any]:
        """
        Mappe les actions HTN aux outils FilAgent

        Returns:
            Dict[action_name, fonction_executable]
        """
        from typing import Callable

        registry: Dict[str, Callable] = {}

        # Mapper chaque outil du registre
        tools = self.tool_registry.list_all()
        for tool_name, tool in tools.items():
            # Wrapper pour adapter l'interface (avec closure corrigée)
            def make_tool_wrapper(t):
                def wrapper(params: Dict):
                    return t.execute(params)

                return wrapper

            registry[tool_name] = make_tool_wrapper(tool)

        # Actions génériques
        registry["generic_execute"] = self._generic_execute

        return registry

    def _generic_execute(self, params: Dict) -> Any:
        """Action générique pour tâches non-mappées"""
        query = params.get("query", "")
        # Utiliser le mode simple pour exécuter la requête
        conversation_id = params.get("conversation_id", "default")
        task_id = params.get("task_id")
        result = self._run_simple(query, conversation_id, task_id)
        return result.get("response", "")

    def _format_htn_response(
        self,
        plan_result,
        exec_result,
        verifications: Dict[str, Any],
        conversation_id: str,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Formate la réponse finale"""

        # Agréger les résultats
        results = []
        sorted_tasks = plan_result.graph.topological_sort()
        for task in sorted_tasks:
            if task.status == TaskStatus.COMPLETED:
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
            print(f"⚠ Failed to persist assistant message: {e}")

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
                print(f"⚠ Failed to log conversation.end.htn event: {e}")

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

    def _generate_response_from_results(self, results: List[Dict[str, Any]]) -> str:
        """Génère un texte de réponse à partir des résultats des tâches"""
        if not results:
            return "Aucun résultat disponible."

        response_parts = []
        response_parts.append("J'ai complété les tâches suivantes:\n")

        for i, result in enumerate(results, 1):
            task_name = result.get("task", "Tâche inconnue")
            task_result = result.get("result", "")
            verified = result.get("verified", None)

            response_parts.append(f"{i}. {task_name}")
            if verified and verified.get("passed", False):
                response_parts.append("   ✓ Vérifié")
            elif verified:
                response_parts.append(f"   ⚠ Vérification: {verified.get('reason', 'Échec')}")

            if task_result:
                # Tronquer si trop long
                result_str = str(task_result)
                if len(result_str) > 200:
                    result_str = result_str[:200] + "..."
                response_parts.append(f"   Résultat: {result_str}")

        return "\n".join(response_parts)


# Classe helper pour l'intégration avec le serveur
class AgentManager:
    """Gestionnaire de l'agent (singleton)"""

    def __init__(self):
        self.agent: Optional[Agent] = None

    def get_agent(self) -> Agent:
        """Récupérer ou créer l'instance de l'agent"""
        if self.agent is None:
            self.agent = Agent()
            self.agent.initialize_model()
        return self.agent

    def reload_agent(self):
        """Recharger l'agent (utile pour les tests)"""
        self.agent = None
        return self.get_agent()


# Instance globale
_agent_manager = AgentManager()


def get_agent() -> Agent:
    """Récupérer l'instance de l'agent"""
    return _agent_manager.get_agent()


def init_model(backend: str, model_path: str, config: Dict[str, Any]):
    """Proxy vers runtime.model_interface.init_model pour compatibilité tests"""
    return _init_model(backend=backend, model_path=model_path, config=config)
