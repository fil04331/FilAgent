"""
Context Builder Component - Prompt and Context Construction

Handles all context building and prompt composition logic.
Separates the concern of how to format conversation history and prompts
from the execution logic.

Key Principles:
1. Single Responsibility: ONLY builds context and prompts
2. Stateless: No instance state, pure functions
3. Configurable: Templates can be injected
4. Type Safety: Clear input/output contracts
5. Template-based: Uses Jinja2 templates for maintainability
"""

import json
import hashlib
from typing import List, Dict, Optional, Any

from pydantic import BaseModel

from runtime.template_loader import get_template_loader, TemplateLoader


class Message(BaseModel):
    """Structured message format"""
    
    role: str  # 'user', 'assistant', 'system', 'tool'
    content: str
    metadata: Optional[Dict[str, Any]] = None


class ContextBuilder:
    """
    Builds conversation context and prompts for LLM.
    
    This component handles formatting of conversation history,
    tool descriptions, and system prompts in a consistent way.
    """
    
    def __init__(
        self,
        max_history_messages: int = 10,
        role_labels: Optional[Dict[str, str]] = None,
        template_loader: Optional[TemplateLoader] = None,
        template_version: str = "v1",
    ):
        """
        Initialize context builder with configuration.
        
        Args:
            max_history_messages: Maximum number of messages to include in context
            role_labels: Custom role labels for formatting
            template_loader: Custom template loader (uses global if None)
            template_version: Template version to use (default: 'v1')
        """
        self.max_history_messages = max_history_messages
        self.role_labels = role_labels or {
            "user": "Utilisateur",
            "assistant": "Assistant",
            "system": "Système",
            "tool": "Outil",
        }
        
        # Template loader for prompt generation
        if template_loader is None:
            self.template_loader = get_template_loader(version=template_version)
        else:
            self.template_loader = template_loader
    
    def build_context(
        self,
        history: List[Dict[str, Any]],
        conversation_id: str,
        task_id: Optional[str] = None,
    ) -> str:
        """
        Build conversation context from history.
        
        Args:
            history: List of message dictionaries
            conversation_id: Conversation identifier
            task_id: Optional task identifier
            
        Returns:
            Formatted context string
        """
        # Take only recent messages
        recent_messages = history[-self.max_history_messages:] if history else []
        
        context_messages = []
        for msg in recent_messages:
            role_key = msg.get("role", "assistant")
            role = self.role_labels.get(role_key, role_key.capitalize())
            content = msg.get("content", "").strip()
            
            if not content:
                continue
            
            context_messages.append(f"{role}: {content}")
        
        return "\n".join(context_messages)
    
    def compose_prompt(self, context: str, message: str) -> str:
        """
        Compose final prompt from context and current message.
        
        Args:
            context: Pre-built context string
            message: Current user message
            
        Returns:
            Complete prompt for LLM
        """
        context = context.strip()
        message = message.strip()
        assistant_header = "Assistant:"
        
        if not context:
            return f"Utilisateur: {message}\n{assistant_header}\n"
        
        return f"{context}\n\nUtilisateur: {message}\n{assistant_header}\n"
    
    def compute_prompt_hash(
        self,
        context: str,
        message: str,
        conversation_id: str,
        task_id: Optional[str] = None,
    ) -> str:
        """
        Compute stable hash for prompt reproducibility.
        
        Args:
            context: Conversation context
            message: Current message
            conversation_id: Conversation identifier
            task_id: Optional task identifier
            
        Returns:
            SHA256 hash of prompt components
        """
        payload = {
            "conversation_id": conversation_id,
            "task_id": task_id,
            "context": context,
            "message": message,
        }
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    
    def inject_semantic_context(
        self,
        query: str,
        top_k: int = 3,
        semantic_memory: Optional[Any] = None,
    ) -> str:
        """
        Retrieve relevant context from semantic memory
        
        Args:
            query: User query to search for relevant context
            top_k: Number of relevant chunks to retrieve
            semantic_memory: Optional SemanticMemory instance (uses global if None)
            
        Returns:
            Formatted context string from semantic search
        """
        if semantic_memory is None:
            try:
                from memory.semantic import get_semantic_memory
                semantic_memory = get_semantic_memory()
            except Exception:
                return ""  # Semantic memory not available
        
        try:
            # Search for relevant documents
            results = semantic_memory.similarity_search(query, k=top_k)
            
            if not results:
                return ""
            
            # Format retrieved context
            context_parts = ["[Contexte sémantique pertinent]"]
            for i, result in enumerate(results, 1):
                text = result.get("text", "")
                score = result.get("score", 0.0)
                source = result.get("metadata", {}).get("source", "unknown")
                
                context_parts.append(
                    f"\n{i}. (Score: {score:.2f}, Source: {source})\n{text}"
                )
            
            return "\n".join(context_parts)
            
        except Exception as e:
            print(f"Warning: Could not retrieve semantic context: {e}")
            return ""
    
    def build_system_prompt(
        self,
        tool_registry: Any,
        domain_context: Optional[str] = None,
        semantic_context: Optional[str] = None,
    ) -> str:
        """
        Build system prompt with tool descriptions and optional semantic context.
        
        Uses Jinja2 template from prompts/templates/v1/system_prompt.j2
        
        Args:
            tool_registry: Registry of available tools
            domain_context: Optional domain-specific context (currently unused, reserved for future)
            semantic_context: Optional semantic search results
            
        Returns:
            Complete system prompt
        """
        tools = tool_registry.list_all()
        tool_descriptions = []
        
        for tool_name, tool in tools.items():
            schema = tool.get_schema()
            tool_descriptions.append(
                f"- {tool_name}: {schema['description']}\n  Paramètres: {json.dumps(schema['parameters'])}"
            )
        
        tools_section = "\n".join(tool_descriptions)
        
        # Render template with variables
        try:
            prompt = self.template_loader.render(
                'system_prompt',
                tools=tools_section,
                semantic_context=semantic_context or "",
            )
        except Exception as e:
            # Fallback to inline prompt if template fails
            # This ensures backward compatibility during migration
            print(f"Warning: Failed to load template, using fallback: {e}")
            prompt = self._build_system_prompt_fallback(tools_section, semantic_context)
        
        return prompt.strip()
    
    def _build_system_prompt_fallback(
        self, 
        tools_section: str, 
        semantic_context: Optional[str] = None
    ) -> str:
        """
        Fallback system prompt if template loading fails.
        
        This preserves the original hardcoded prompt for backward compatibility.
        """
        base_prompt = """Tu es FilAgent, un assistant IA spécialisé pour les propriétaires de PME québécoises.

CONTEXTE:
Tu aides les propriétaires de petites et moyennes entreprises (PME) au Québec avec leurs défis d'affaires quotidiens.
Tes réponses doivent TOUJOURS considérer le contexte québécois, incluant:
- Le bilinguisme français-anglais
- Les lois et règlements québécois (Loi 25, Loi 101, etc.)
- Le marché local et les spécificités du Québec
- Les programmes de subventions gouvernementales disponibles

DOMAINES D'EXPERTISE:
- Marketing et communications (stratégie, réseaux sociaux, contenu)
- Juridique et conformité (contrats, propriété intellectuelle, Loi 25)
- Opérations et chaîne d'approvisionnement (gestion stocks, fournisseurs)
- Ressources humaines (recrutement, rétention, grilles salariales)
- Environnement et transition énergétique (certifications, subventions)
- Technologies et transformation numérique

QUALITÉ DES RÉPONSES:
1. Reste STRICTEMENT pertinent au sujet exact de la question posée
2. Fournis des informations SPÉCIFIQUES au Québec (lois, programmes, contexte local)
3. Inclus des CHIFFRES, exemples concrets et données factuelles quand disponibles
4. Structure tes réponses de façon CLAIRE et ACTIONNABLE
5. Si tu manques d'information, DIS-LE clairement plutôt que de dévier du sujet

OUTILS DISPONIBLES:
{tools}

Format pour appeler un outil:
<tool_call>
{{
    "tool": "nom_outil",
    "arguments": {{"param": "valeur"}}
}}
</tool_call>

IMPORTANT: Utilise les outils SEULEMENT quand nécessaire. Pour des questions générales d'affaires, réponds directement avec tes connaissances et des recherches web pertinentes.

Réponds toujours de manière professionnelle, concrète et utile pour un propriétaire de PME québécoise."""
        
        prompt = base_prompt.format(tools=tools_section)
        
        if semantic_context:
            prompt = f"{prompt}\n\n{semantic_context}"
        
        return prompt
    
    def format_tool_results_for_context(
        self,
        context: str,
        tool_results_formatted: str,
    ) -> str:
        """
        Inject tool results into context.
        
        Args:
            context: Existing context
            tool_results_formatted: Formatted tool results string
            
        Returns:
            Updated context with tool results
        """
        return f"{context}\n\n[Résultats des outils]\n{tool_results_formatted}".strip()
    
    def create_followup_message(
        self,
        tool_results_formatted: str,
    ) -> str:
        """
        Create followup message after tool execution.
        
        Args:
            tool_results_formatted: Formatted tool results
            
        Returns:
            Followup message for LLM
        """
        return (
            "Voici les résultats des outils exécutés :\n"
            f"{tool_results_formatted}\n\nContinuez votre réponse en utilisant ces résultats."
        )
