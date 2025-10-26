"""
Agent core : Intègre le modèle et les outils
Gère les boucles de raisonnement et les appels d'outils
"""
import json
import re
import hashlib
from typing import List, Dict, Optional, Any
from datetime import datetime

from .config import get_config
from .model_interface import get_model, GenerationConfig, GenerationResult
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
        """
        Analyser un message et générer une réponse
        Gère les appels d'outils de manière itérative
        """
        # Logger le début de la conversation (avec fallback)
        if self.logger:
            try:
                self.logger.log_event(
            actor="agent.core",
            event="conversation.start",
            level="INFO",
            conversation_id=conversation_id,
            task_id=task_id
        )
        
        # Enregistrer le message utilisateur
        add_message(
            conversation_id=conversation_id,
            role="user",
            content=message,
            task_id=task_id
        )
        
        # Hasher le prompt pour traçabilité
        prompt_hash = hashlib.sha256(message.encode('utf-8')).hexdigest()
        
        # Récupérer l'historique
        history = get_messages(conversation_id)
        
        # Construire le contexte pour le modèle
        context = self._build_context(history, conversation_id, task_id)
        
        # Boucle de raisonnement (max 10 tours)
        max_iterations = 10
        iterations = 0
        final_response = None
        start_time = datetime.now().isoformat()
        tools_used = []
        
        while iterations < max_iterations:
            iterations += 1
            
            # Générer une réponse
            generation_config = GenerationConfig(
                temperature=self.config.generation.temperature,
                top_p=self.config.generation.top_p,
                max_tokens=self.config.generation.max_tokens,
                seed=self.config.generation.seed,
                top_k=self.config.generation.top_k,
                repetition_penalty=self.config.generation.repetition_penalty
            )
            
            result = self.model.generate(
                prompt=message,
                config=generation_config,
                system_prompt=self._get_system_prompt()
            )
            
            response_text = result.text
            
            # Parser pour détecter les appels d'outils
            tool_calls = self._parse_tool_calls(response_text)
            
            if tool_calls:
                # Exécuter les outils
                tool_results = []
                for tool_call in tool_calls:
                    tool_name = tool_call.get('tool')
                    arguments = tool_call.get('arguments', {})
                    
                    # Logger l'appel d'outil (avec fallback)
                    if self.logger:
                        try:
                            self.logger.log_tool_call(
                                tool_name=tool_name,
                                arguments=arguments,
                                conversation_id=conversation_id,
                                task_id=task_id
                            )
                        except Exception:
                            pass  # Silent fail for logging
                    
                    # Exécuter l'outil
                    result = self._execute_tool(tool_call)
                    tool_results.append(result)
                    
                    # Tracer provenance de l'outil (avec fallback)
                    if self.tracker:
                        try:
                            input_hash = hashlib.sha256(str(arguments).encode()).hexdigest()
                            output_hash = hashlib.sha256(str(result.output).encode()).hexdigest()
                            
                            self.tracker.track_tool_execution(
                                tool_name=tool_name,
                                tool_input_hash=input_hash,
                                tool_output_hash=output_hash,
                                task_id=task_id or conversation_id,
                                start_time=datetime.now().isoformat(),
                                end_time=datetime.now().isoformat()
                            )
                        except Exception:
                            pass  # Silent fail for tracking
                    
                    tools_used.append(tool_name)
                
                # Ajouter les résultats au contexte et continuer
                context += f"\n\n[Résultats des outils]\n{self._format_tool_results(tool_results)}"
                message = f"Voici les résultats des outils exécutés :\n{self._format_tool_results(tool_results)}\n\nContinuez votre réponse en utilisant ces résultats."
            else:
                # Pas d'appels d'outils, réponse finale
                final_response = response_text
                break
        
        # Enregistrer la réponse
        end_time = datetime.now().isoformat()
        
        if final_response:
            add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=final_response,
                task_id=task_id
            )
            
            # Hasher la réponse
            response_hash = hashlib.sha256(final_response.encode('utf-8')).hexdigest()
            
            # Logger la génération (avec fallback)
            if self.logger:
                try:
                    self.logger.log_generation(
                        conversation_id=conversation_id,
                        task_id=task_id,
                        prompt_hash=prompt_hash,
                        response_hash=response_hash,
                        tokens_used=len(final_response.split())  # Approximation
                    )
                except Exception:
                    pass
            
            # Tracer la provenance (avec fallback)
            if self.tracker:
                try:
                    self.tracker.track_generation(
                agent_id="agent:llmagenta",
                agent_version=self.config.version,
                task_id=task_id or conversation_id,
                prompt_hash=prompt_hash,
                response_hash=response_hash,
                start_time=start_time,
                end_time=end_time
            )
            
            # Créer un Decision Record si des outils ont été utilisés ou si décision significative (avec fallback)
            if self.dr_manager and (tools_used or any(keyword in final_response.lower() for keyword in ['execute', 'write', 'delete', 'create'])):
                try:
                    dr = self.dr_manager.create_dr(
                    actor="agent.core",
                    task_id=task_id or conversation_id,
                    decision="generate_response_with_tools" if tools_used else "generate_response",
                    prompt_hash=prompt_hash,
                    tools_used=tools_used,
                    reasoning_markers=[f"iterations:{iterations}"],
                    alternatives_considered=["do_nothing", "ask_clarification"],
                    constraints={
                        "max_tokens": self.config.generation.max_tokens,
                        "temperature": self.config.generation.temperature
                    },
                    expected_risk=["hallucination:medium", "tool_execution:low"]
                )
                
                    # Logger le DR créé
                    if self.logger:
                        try:
                            self.logger.log_event(
                                actor="agent.core",
                                event="dr.created",
                                level="INFO",
                                conversation_id=conversation_id,
                                task_id=task_id,
                                metadata={"dr_id": dr.dr_id}
                            )
                        except Exception:
                            pass
                except Exception:
                    pass  # Silent fail for DR
        
        # Logger la fin de la conversation (avec fallback)
        if self.logger:
            try:
                self.logger.log_event(
                    actor="agent.core",
                    event="conversation.end",
                    level="INFO",
                    conversation_id=conversation_id,
                    task_id=task_id,
                    metadata={"iterations": iterations}
                )
            except Exception:
                pass
        
        return {
            "response": final_response or "Erreur: boucle de raisonnement trop longue",
            "iterations": iterations,
            "conversation_id": conversation_id,
            "task_id": task_id,
            "tools_used": tools_used
        }
    
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
        
        system_prompt = f"""Tu es un assistant IA capable d'utiliser des outils.

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
        
        return system_prompt
    
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
