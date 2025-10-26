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
from .model_interface import GenerationConfig, GenerationResult
from memory.episodic import add_message, get_messages
from tools.registry import get_registry
from tools.base import BaseTool, ToolResult, ToolStatus

# Import des middlewares de conformité
from .middleware.logging import get_logger
from .middleware.audittrail import get_dr_manager
from .middleware.provenance import get_tracker


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
    
    def initialize_model(self):
        """Initialiser le modèle"""
        from .model_interface import init_model
        
        model_config = {
            'context_size': self.config.model.context_size,
            'n_gpu_layers': self.config.model.n_gpu_layers
        }
        
        self.model = init_model(
            backend=self.config.model.backend,
            model_path=self.config.model.path,
            config=model_config
        )
        print("✓ Model initialized")
    
    def chat(self, message: str, conversation_id: str, task_id: Optional[str] = None) -> Dict[str, Any]:
        """Analyser un message utilisateur et orchestrer la réponse de l'agent."""

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
        add_message(
            conversation_id=conversation_id,
            role="user",
            content=message,
            task_id=task_id,
        )

        history = get_messages(conversation_id)
        context = self._build_context(history, conversation_id, task_id)

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
            current_prompt_hash = hashlib.sha256(full_prompt.encode("utf-8")).hexdigest()

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
                            print(f"⚠ Failed to log tool call: {e}")

                    if self.tracker:
                        try:
                            input_hash = hashlib.sha256(str(arguments).encode()).hexdigest()
                            output_payload = execution_result.output if execution_result.is_success() else execution_result.error or ""
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
                            print(f"⚠ Failed to track tool execution: {e}")

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
            final_prompt_hash = final_prompt_hash or hashlib.sha256(
                self._compose_prompt(context, current_message).encode("utf-8")
            ).hexdigest()

        add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=final_response,
            task_id=task_id,
        )

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
            or any(
                keyword in final_response.lower()
                for keyword in ["execute", "write", "delete", "create"]
            )
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
                        print(f"⚠ Failed to log DR created event: {e}")
            except Exception as e:
                print(f"⚠ Failed to create decision record: {e}")

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
        return f"{context}\n\nUtilisateur: {message}\nAssistant:"
    
    def _build_context(self, history: List[Dict], conversation_id: str, task_id: Optional[str]) -> str:
        """Construire le contexte pour le modèle"""
        context = f"Conversation ID: {conversation_id}\n"
        if task_id:
            context += f"Task ID: {task_id}\n"
        
        context += "\nHistorique:\n"
        for msg in history[-10:]:  # 10 derniers messages
            role = msg['role']
            content = msg['content']
            context += f"{role}: {content}\n"
        
        return context
    
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
        pattern = r'<tool_call>(.*?)</tool_call>'
        matches = re.findall(pattern, text, re.DOTALL)
        
        tool_calls = []
        for match in matches:
            try:
                tool_json = json.loads(match.strip())
                if 'tool' in tool_json and 'arguments' in tool_json:
                    tool_calls.append(tool_json)
            except json.JSONDecodeError:
                continue
        
        return tool_calls
    
    def _execute_tool(self, tool_call: Dict[str, Any]) -> ToolResult:
        """Exécuter un outil"""
        tool_name = tool_call.get('tool')
        arguments = tool_call.get('arguments', {})
        
        tool = self.tool_registry.get(tool_name)
        
        if not tool:
            return ToolResult(
                status=ToolStatus.ERROR,
                output="",
                error=f"Tool not found: {tool_name}"
            )
        
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
