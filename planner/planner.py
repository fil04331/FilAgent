"""
Hierarchical Task Network (HTN) Planner

Implémente la décomposition de requêtes complexes en graphe de tâches exécutables.

Stratégies supportées:
- LLM-based: Utilise le modèle LLM pour décomposition intelligente
- Rule-based: Règles prédéfinies pour tâches courantes
- Hybrid: Combinaison des deux approches

Conformité:
- Traçabilité de chaque décision de décomposition (Loi 25)
- Justification des choix de planification (AI Act)
- Logs structurés pour auditabilité (RGPD)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, List, Dict, Optional, Union, Protocol
from datetime import datetime
import json
import re

from .task_graph import Task, TaskGraph, TaskPriority, TaskDecompositionError, TaskParamValue
from .metrics import get_metrics
import time

from runtime.template_loader import get_template_loader, TemplateLoader


# Protocol pour l'interface modèle (évite l'import circulaire)
class ModelInterface(Protocol):
    """Protocol pour les interfaces modèle LLM"""
    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 1000,
    ) -> Union[str, Dict[str, str]]: ...


# Protocol pour le registre d'outils
class ToolsRegistry(Protocol):
    """Protocol pour le registre d'outils"""
    def get_all(self) -> List[object]: ...


# Types stricts pour le planificateur
PlanningMetadataValue = Union[str, int, float, bool, List[str], Dict[str, str]]
DecompositionTask = Dict[str, Union[str, int, List[int], Dict[str, str]]]


class PlanningStrategy(str, Enum):
    """Stratégies de planification disponibles"""

    LLM_BASED = "llm_based"  # Décomposition via LLM
    RULE_BASED = "rule_based"  # Règles prédéfinies
    HYBRID = "hybrid"  # Combinaison LLM + règles


@dataclass
class PlanningResult:
    """
    Résultat d'une planification

    Attributes:
        graph: Graphe de tâches généré
        strategy_used: Stratégie utilisée
        confidence: Score de confiance (0-1)
        reasoning: Justification de la décomposition
        metadata: Métadonnées de traçabilité
    """

    graph: TaskGraph
    strategy_used: PlanningStrategy
    confidence: float
    reasoning: str
    metadata: Dict[str, PlanningMetadataValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialise les métadonnées de traçabilité"""
        if "planned_at" not in self.metadata:
            self.metadata["planned_at"] = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Union[str, float, Dict[str, PlanningMetadataValue], object]]:
        """Sérialise pour logging/traçabilité"""
        return {
            "graph": self.graph.to_dict(),
            "strategy_used": self.strategy_used.value,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "metadata": self.metadata,
        }


class HierarchicalPlanner:
    """
    Planificateur hiérarchique HTN

    Responsabilités:
        - Analyser les requêtes utilisateur
        - Décomposer en sous-tâches atomiques
        - Identifier les dépendances
        - Construire le graphe d'exécution
        - Valider la cohérence du plan

    Usage:
        planner = HierarchicalPlanner(model_interface=model, tools_registry=registry)
        result = planner.plan(
            query="Analyse data.csv, génère stats, crée rapport PDF",
            strategy=PlanningStrategy.LLM_BASED
        )
        tasks = result.graph.topological_sort()
    """

    def __init__(
        self,
        model_interface: Optional[ModelInterface] = None,
        tools_registry: Optional[ToolsRegistry] = None,
        max_decomposition_depth: int = 3,
        enable_tracing: bool = True,
        template_loader: Optional[TemplateLoader] = None,
        template_version: str = "v1",
    ):
        """
        Initialise le planificateur

        Args:
            model_interface: Interface vers le modèle LLM (pour décomposition)
            tools_registry: Registre des outils disponibles
            max_decomposition_depth: Profondeur max de décomposition récursive
            enable_tracing: Active la traçabilité complète (conformité)
            template_loader: Custom template loader (uses global if None)
            template_version: Template version to use (default: 'v1')
        """
        self.model = model_interface
        self.tools = tools_registry
        self.max_depth = max_decomposition_depth
        self.enable_tracing = enable_tracing

        # Template loader for prompt generation
        if template_loader is None:
            self.template_loader = get_template_loader(version=template_version)
        else:
            self.template_loader = template_loader

        # Patterns courants pour règles prédéfinies
        self._init_rule_patterns()

    def _init_rule_patterns(self) -> None:
        """Initialise les patterns de règles courantes"""
        self.patterns: Dict[str, List[Dict[str, Union[str, int, List[int]]]]] = {
            # Pattern: "analyse X, génère Y, crée Z"
            r"analys[er]?\s+(.+?),\s+g[ée]n[ée]r[er]?\s+(.+?),\s+cr[ée][er]?\s+(.+)": [
                {"action": "read_file", "extract": 1},
                {"action": "analyze_data", "depends_on": [0]},
                {"action": "generate_report", "depends_on": [1]},
            ],
            # Pattern: "lis X, calcule Y"
            r"li[st]?\s+(.+?),\s+calcul[er]?\s+(.+)": [
                {"action": "read_file", "extract": 1},
                {"action": "calculate", "depends_on": [0]},
            ],
            # Pattern: "trouve X et Y, puis Z"
            r"trouv[er]?\s+(.+?)\s+et\s+(.+?),\s+puis\s+(.+)": [
                {"action": "search", "extract": 1},
                {"action": "search", "extract": 2},
                {"action": "process", "depends_on": [0, 1]},
            ],
        }

    def plan(
        self,
        query: str,
        strategy: PlanningStrategy = PlanningStrategy.HYBRID,
        context: Optional[Dict[str, PlanningMetadataValue]] = None,
    ) -> PlanningResult:
        """
        Planifie l'exécution d'une requête complexe

        Args:
            query: Requête utilisateur à décomposer
            strategy: Stratégie de planification à utiliser
            context: Contexte additionnel (conversation, état, etc.)

        Returns:
            PlanningResult avec le graphe de tâches

        Raises:
            TaskDecompositionError: Si la décomposition échoue
        """
        # Métriques: début de planification
        metrics = get_metrics()
        start_time = time.time()

        # Traçabilité: enregistrer le début de planification
        planning_metadata = {
            "query": query,
            "strategy": strategy.value,
            "started_at": datetime.utcnow().isoformat(),
            "context": context or {},
        }

        try:
            if strategy == PlanningStrategy.RULE_BASED:
                result = self._plan_rule_based(query, planning_metadata)
            elif strategy == PlanningStrategy.LLM_BASED:
                result = self._plan_llm_based(query, planning_metadata)
            else:  # HYBRID
                result = self._plan_hybrid(query, planning_metadata)

            # Validation finale du plan
            self._validate_plan(result.graph)

            # Traçabilité: succès
            result.metadata["completed_at"] = datetime.utcnow().isoformat()
            result.metadata["validation_passed"] = True

            # Métriques: enregistrer succès
            duration_seconds = time.time() - start_time
            metrics.record_planning(
                strategy=strategy.value,
                success=True,
                duration_seconds=duration_seconds,
                confidence=result.confidence,
                tasks_count=len(result.graph.tasks),
            )

            return result

        except Exception as e:
            # Traçabilité: échec
            planning_metadata["completed_at"] = datetime.utcnow().isoformat()
            planning_metadata["error"] = str(e)
            planning_metadata["validation_passed"] = False

            # Métriques: enregistrer échec
            duration_seconds = time.time() - start_time
            metrics.record_planning(
                strategy=strategy.value,
                success=False,
                duration_seconds=duration_seconds,
                confidence=0.0,
                tasks_count=0,
            )

            raise TaskDecompositionError(f"Planning failed for query '{query[:50]}...': {str(e)}") from e

    def _plan_rule_based(self, query: str, metadata: Dict[str, PlanningMetadataValue]) -> PlanningResult:
        """
        Planification basée sur des règles prédéfinies

        Avantages: Rapide, prévisible, déterministe
        Limitations: Moins flexible, couvre cas limités
        """
        graph = TaskGraph()
        matched = False
        reasoning = "Rule-based decomposition: "

        # Essayer de matcher avec les patterns connus
        for pattern, task_templates in self.patterns.items():
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                matched = True
                reasoning += f"Matched pattern '{pattern}'. "

                # Créer les tâches selon le template
                created_tasks = []
                for i, template in enumerate(task_templates):
                    # Extraire les paramètres du match
                    if "extract" in template:
                        param_value = match.group(template["extract"])
                    else:
                        param_value = query

                    # Créer la tâche
                    task = Task(
                        name=f"{template['action']}_{i}",
                        action=template["action"],
                        params={"input": param_value.strip()},
                        depends_on=[created_tasks[dep_idx].task_id for dep_idx in template.get("depends_on", [])],
                        priority=TaskPriority.NORMAL,
                    )

                    graph.add_task(task)
                    created_tasks.append(task)

                break

        if not matched:
            # Fallback: créer une tâche unique
            reasoning += "No pattern matched. Created single task."
            task = Task(
                name="execute_query",
                action="generic_execute",
                params={"query": query},
                priority=TaskPriority.NORMAL,
            )
            graph.add_task(task)

        return PlanningResult(
            graph=graph,
            strategy_used=PlanningStrategy.RULE_BASED,
            confidence=0.8 if matched else 0.5,
            reasoning=reasoning,
            metadata=metadata,
        )

    def _plan_llm_based(self, query: str, metadata: Dict[str, PlanningMetadataValue]) -> PlanningResult:
        """
        Planification via LLM (décomposition intelligente)

        Avantages: Flexible, gère cas complexes, contexte
        Limitations: Plus lent, non-déterministe, nécessite LLM
        """
        if self.model is None:
            raise TaskDecompositionError("LLM-based planning requires a model_interface")

        # Construire le prompt de décomposition avec templates
        system_prompt = self._build_decomposition_prompt()
        user_prompt = self._build_user_decomposition_prompt(query)

        # Appeler le LLM
        try:
            response = self.model.generate(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,  # Bas pour cohérence
                max_tokens=1000,
            )

            # Extraire le texte de la réponse si c'est un dict
            if isinstance(response, dict):
                response = response.get("text", response)

            # Parser la réponse JSON
            decomposition = self._parse_llm_response(response)

            # Construire le graphe
            graph = self._build_graph_from_decomposition(decomposition)

            return PlanningResult(
                graph=graph,
                strategy_used=PlanningStrategy.LLM_BASED,
                confidence=0.9,
                reasoning=decomposition.get("reasoning", "LLM decomposition"),
                metadata={**metadata, "llm_response": response},
            )

        except Exception as e:
            raise TaskDecompositionError(f"LLM-based planning failed: {str(e)}") from e

    def _plan_hybrid(self, query: str, metadata: Dict[str, PlanningMetadataValue]) -> PlanningResult:
        """
        Planification hybride (règles + LLM)

        Stratégie:
        1. Essayer rule-based d'abord (rapide)
        2. Si confiance < 0.7, raffiner avec LLM
        3. Combiner les deux approches
        """
        # Étape 1: Essayer règles
        rule_result = self._plan_rule_based(query, metadata)

        # Étape 2: Si confiance suffisante, retourner
        if rule_result.confidence >= 0.7:
            rule_result.strategy_used = PlanningStrategy.HYBRID
            rule_result.reasoning = f"Hybrid (rule-based sufficient): {rule_result.reasoning}"
            return rule_result

        # Étape 3: Raffiner avec LLM
        try:
            llm_result = self._plan_llm_based(query, metadata)
            llm_result.strategy_used = PlanningStrategy.HYBRID
            llm_result.reasoning = f"Hybrid (LLM refinement): {llm_result.reasoning}"
            return llm_result
        except Exception:
            # Fallback sur règles si LLM échoue
            rule_result.strategy_used = PlanningStrategy.HYBRID
            rule_result.reasoning = f"Hybrid (LLM failed, fallback to rules): {rule_result.reasoning}"
            return rule_result

    def _build_decomposition_prompt(self) -> str:
        """
        Construit le prompt système pour décomposition LLM
        
        Uses Jinja2 template from prompts/templates/v1/planner_decomposition.j2
        """
        try:
            return self.template_loader.render('planner_decomposition')
        except Exception as e:
            # Fallback to inline prompt if template fails
            print(f"Warning: Failed to load planner template, using fallback: {e}")
            return """Tu es un expert en décomposition de tâches complexes.

Ton rôle:
- Analyser les requêtes utilisateur
- Les décomposer en sous-tâches atomiques
- Identifier les dépendances entre tâches
- Assigner des priorités appropriées

Principes:
- Tâches atomiques (1 action = 1 tâche)
- Dépendances explicites (une tâche ne peut s'exécuter que si ses dépendances sont complètes)
- Parallélisation maximale (tâches indépendantes)
- Priorités cohérentes (CRITICAL=5, HIGH=4, NORMAL=3, LOW=2, OPTIONAL=1)

Réponds TOUJOURS en JSON valide sans markdown."""
    
    def _build_user_decomposition_prompt(self, query: str) -> str:
        """
        Construit le prompt utilisateur pour décomposition
        
        Uses Jinja2 template from prompts/templates/v1/planner_user_prompt.j2
        
        Args:
            query: User query to decompose
            
        Returns:
            Formatted user prompt
        """
        available_actions = ", ".join(self._get_available_actions())
        
        try:
            return self.template_loader.render(
                'planner_user_prompt',
                query=query,
                available_actions=available_actions,
            )
        except Exception as e:
            # Fallback to inline prompt if template fails
            print(f"Warning: Failed to load planner user template, using fallback: {e}")
            return f"""Décompose cette requête en tâches atomiques:

Requête: {query}

Réponds UNIQUEMENT avec un JSON valide suivant ce format:
{{
  "tasks": [
    {{
      "name": "nom_descriptif",
      "action": "nom_action",
      "params": {{"key": "value"}},
      "depends_on": [indices des tâches requises],
      "priority": 3
    }}
  ],
  "reasoning": "Justification de la décomposition"
}}

Actions disponibles: {available_actions}
"""

    def _get_available_actions(self) -> List[str]:
        """Retourne la liste des actions disponibles"""
        if self.tools:
            return [tool.name for tool in self.tools.get_all()]
        return [
            "read_file", "write_file", "search", "calculate",
            "analyze_data", "generate_report", "execute_code"
        ]
    
    def _parse_llm_response(self, response: Union[str, Dict[str, str], object]) -> Dict[str, Union[str, List[DecompositionTask]]]:
        """Parse la réponse JSON du LLM ou retourne directement un dictionnaire."""
        response_text: str = ""

        if isinstance(response, dict):
            if "tasks" in response:
                return response  # type: ignore[return-value]
            if "text" in response and isinstance(response["text"], str):
                response_text = response["text"]
            elif "content" in response and isinstance(response["content"], str):
                response_text = response["content"]
            else:
                raise TaskDecompositionError(
                    "Failed to parse LLM response: missing JSON payload"
                )
        elif hasattr(response, "text"):
            text_attr = getattr(response, "text", None)
            if isinstance(text_attr, str):
                response_text = text_attr
            else:
                raise TaskDecompositionError(
                    f"Failed to parse LLM response: unsupported type {type(response).__name__}"
                )
        elif isinstance(response, str):
            response_text = response
        else:
            raise TaskDecompositionError(
                f"Failed to parse LLM response: unsupported type {type(response).__name__}"
            )

        # Nettoyer la réponse (enlever markdown, etc.)
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            # Enlever les backticks markdown
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1])

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise TaskDecompositionError(
                f"Failed to parse LLM response: {str(e)}\nResponse: {response_text[:200]}"
            ) from e

    def _build_graph_from_decomposition(self, decomposition: Dict[str, Union[str, List[DecompositionTask]]]) -> TaskGraph:
        """Construit un TaskGraph depuis la décomposition LLM"""
        graph = TaskGraph()
        task_list = decomposition.get("tasks", [])
        created_tasks = []

        for task_spec in task_list:
            # Résoudre les dépendances (indices -> task_ids)
            depends_on_indices = task_spec.get("depends_on", [])
            depends_on_ids = [created_tasks[idx].task_id for idx in depends_on_indices if idx < len(created_tasks)]

            # Créer la tâche
            task = Task(
                name=task_spec.get("name", "unnamed_task"),
                action=task_spec.get("action", "generic_execute"),
                params=task_spec.get("params", {}),
                depends_on=depends_on_ids,
                priority=TaskPriority(task_spec.get("priority", 3)),
            )

            graph.add_task(task)
            created_tasks.append(task)

        return graph

    def _validate_plan(self, graph: TaskGraph):
        """
        Valide la cohérence du plan

        Vérifications:
        - Au moins 1 tâche
        - Pas de cycles (déjà vérifié par TaskGraph)
        - Actions valides (si tools_registry disponible)
        - Dépendances cohérentes

        Raises:
            TaskDecompositionError: Si validation échoue
        """
        if len(graph.tasks) == 0:
            raise TaskDecompositionError("Plan must contain at least one task")

        # Vérifier que toutes les actions sont valides
        if self.tools:
            available_actions = set(self._get_available_actions())
            for task in graph.tasks.values():
                if task.action not in available_actions and task.action != "generic_execute":
                    raise TaskDecompositionError(f"Unknown action '{task.action}' in task {task.task_id}")

        # Vérifier tri topologique possible (pas de cycles)
        try:
            graph.topological_sort()
        except TaskDecompositionError as e:
            raise TaskDecompositionError(f"Plan validation failed: {str(e)}") from e
