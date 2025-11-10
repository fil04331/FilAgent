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

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Any
from datetime import datetime
import json
import re

from .task_graph import Task, TaskGraph, TaskPriority, TaskDecompositionError
from .metrics import get_metrics
import time


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
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Initialise les métadonnées de traçabilité"""
        if "planned_at" not in self.metadata:
            self.metadata["planned_at"] = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
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
        model_interface: Optional[Any] = None,
        tools_registry: Optional[Any] = None,
        max_decomposition_depth: int = 3,
        enable_tracing: bool = True,
    ):
        """
        Initialise le planificateur

        Args:
            model_interface: Interface vers le modèle LLM (pour décomposition)
            tools_registry: Registre des outils disponibles
            max_decomposition_depth: Profondeur max de décomposition récursive
            enable_tracing: Active la traçabilité complète (conformité)
        """
        self.model = model_interface
        self.tools = tools_registry
        self.max_depth = max_decomposition_depth
        self.enable_tracing = enable_tracing

        # Patterns courants pour règles prédéfinies
        self._init_rule_patterns()

    def _init_rule_patterns(self):
        """Initialise les patterns de règles courantes"""
        self.patterns = {
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
        context: Optional[Dict[str, Any]] = None,
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

    def _plan_rule_based(self, query: str, metadata: Dict[str, Any]) -> PlanningResult:
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

    def _plan_llm_based(self, query: str, metadata: Dict[str, Any]) -> PlanningResult:
        """
        Planification via LLM (décomposition intelligente)

        Avantages: Flexible, gère cas complexes, contexte
        Limitations: Plus lent, non-déterministe, nécessite LLM
        """
        if self.model is None:
            raise TaskDecompositionError("LLM-based planning requires a model_interface")

        # Construire le prompt de décomposition
        system_prompt = self._build_decomposition_prompt()
        user_prompt = f"""Décompose cette requête en tâches atomiques:

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

Actions disponibles: {self._get_available_actions()}
"""

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

    def _plan_hybrid(self, query: str, metadata: Dict[str, Any]) -> PlanningResult:
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
        """Construit le prompt système pour décomposition LLM"""
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

    def _get_available_actions(self) -> List[str]:
        """Retourne la liste des actions disponibles"""
        if self.tools:
            return [tool.name for tool in self.tools.get_all()]
        return ["read_file", "write_file", "search", "calculate", "analyze_data", "generate_report", "execute_code"]

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse la réponse JSON du LLM"""
        # Si response est déjà un dict, le retourner directement
        if isinstance(response, dict):
            return response
        # Nettoyer la réponse (enlever markdown, etc.)
        if not isinstance(response, str):
            response = str(response)
        cleaned = response.strip()
        if cleaned.startswith("```"):
            # Enlever les backticks markdown
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1])

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise TaskDecompositionError(
                f"Failed to parse LLM response as JSON: {str(e)}\nResponse: {response[:200]}"
            ) from e

    def _build_graph_from_decomposition(self, decomposition: Dict[str, Any]) -> TaskGraph:
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
