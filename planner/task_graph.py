"""
Task Graph - Structures de données pour HTN Planning

Implémente:
- Task: Unité atomique de travail avec métadonnées
- TaskGraph: DAG (Directed Acyclic Graph) de tâches avec dépendances
- Algorithmes de validation (cycles, cohérence)
- Sérialisation pour traçabilité (conformité Loi 25)

Complexité:
- Construction: O(V + E) où V=tâches, E=dépendances
- Détection de cycles: O(V + E) via DFS
- Tri topologique: O(V + E)
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Dict, Set, Optional, Any
from datetime import datetime
import uuid
import json


class TaskStatus(str, Enum):
    """États possibles d'une tâche dans le cycle de vie"""

    PENDING = "pending"  # En attente d'exécution
    READY = "ready"  # Dépendances satisfaites, prête
    RUNNING = "running"  # En cours d'exécution
    COMPLETED = "completed"  # Terminée avec succès
    FAILED = "failed"  # Échouée
    SKIPPED = "skipped"  # Sautée (dépendance échouée)
    CANCELLED = "cancelled"  # Annulée par l'utilisateur


class TaskPriority(int, Enum):
    """Niveaux de priorité pour l'ordonnancement"""

    CRITICAL = 5  # Critique (bloquant)
    HIGH = 4  # Haute priorité
    NORMAL = 3  # Normale
    LOW = 2  # Basse priorité
    OPTIONAL = 1  # Optionnelle (peut échouer)


@dataclass
class Task:
    """
    Unité atomique de travail dans le plan hiérarchique

    Attributs:
        task_id: Identifiant unique (UUID4)
        name: Nom descriptif de la tâche
        action: Action à exécuter (ex: "read_file", "analyze_data")
        params: Paramètres pour l'action
        depends_on: Liste des task_ids dont cette tâche dépend
        priority: Priorité d'exécution
        status: État actuel de la tâche
        result: Résultat de l'exécution (None si pas encore exécutée)
        error: Message d'erreur (si échec)
        metadata: Métadonnées additionnelles (timing, provenance, etc.)

    Conformité:
        - Traçabilité complète via task_id et timestamps
        - Métadonnées pour Decision Records (ADR)
        - Sérialisation JSON pour logs WORM
    """

    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    action: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Initialise les métadonnées avec timestamps"""
        if "created_at" not in self.metadata:
            self.metadata["created_at"] = datetime.utcnow().isoformat()
        if "updated_at" not in self.metadata:
            self.metadata["updated_at"] = datetime.utcnow().isoformat()

    def update_status(self, new_status: TaskStatus, error: Optional[str] = None):
        """
        Met à jour le statut avec traçabilité

        Args:
            new_status: Nouveau statut
            error: Message d'erreur optionnel
        """
        self.status = new_status
        self.metadata["updated_at"] = datetime.utcnow().isoformat()

        if error:
            self.error = error
            self.metadata["error_timestamp"] = datetime.utcnow().isoformat()

    def set_result(self, result: Any):
        """Enregistre le résultat avec timestamp"""
        self.result = result
        self.metadata["completed_at"] = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Sérialise en dict pour logging/traçabilité"""
        return {
            "task_id": self.task_id,
            "name": self.name,
            "action": self.action,
            "params": self.params,
            "depends_on": self.depends_on,
            "priority": self.priority.value,
            "status": self.status.value,
            "result": str(self.result) if self.result is not None else None,
            "error": self.error,
            "metadata": self.metadata,
        }

    def __repr__(self) -> str:
        deps = f", deps={len(self.depends_on)}" if self.depends_on else ""
        return f"Task({self.name}, {self.status.value}, pri={self.priority.value}{deps})"


class TaskDecompositionError(Exception):
    """Erreur lors de la décomposition ou validation du graphe"""

    pass


class TaskGraph:
    """
    Graphe acyclique dirigé (DAG) de tâches avec dépendances

    Gère:
        - Construction du graphe de tâches
        - Validation (cycles, cohérence)
        - Tri topologique pour ordonnancement
        - Identification des tâches parallélisables

    Invariants:
        - Pas de cycles (vérifié à l'ajout)
        - task_id uniques
        - Dépendances valides (tâches existantes)
    """

    def __init__(self):
        self.tasks: Dict[str, Task] = {}  # task_id -> Task
        self.adjacency_list: Dict[str, List[str]] = {}  # task_id -> [dependent_task_ids]
        self.reverse_adjacency: Dict[str, List[str]] = {}  # task_id -> [dependency_task_ids]

    def add_task(self, task: Task) -> None:
        """
        Ajoute une tâche au graphe avec validation

        Args:
            task: Tâche à ajouter

        Raises:
            TaskDecompositionError: Si task_id dupliqué ou dépendances invalides
        """
        if task.task_id in self.tasks:
            raise TaskDecompositionError(f"Task ID {task.task_id} already exists in graph")

        # Valider que toutes les dépendances existent
        for dep_id in task.depends_on:
            if dep_id not in self.tasks:
                raise TaskDecompositionError(
                    f"Dependency {dep_id} not found for task {task.task_id}"
                )

        # Ajouter la tâche
        self.tasks[task.task_id] = task

        # Construire les listes d'adjacence
        self.adjacency_list[task.task_id] = []
        self.reverse_adjacency[task.task_id] = task.depends_on.copy()

        # Mettre à jour les dépendants
        for dep_id in task.depends_on:
            self.adjacency_list[dep_id].append(task.task_id)

        # Vérifier l'absence de cycles après ajout
        if self._has_cycle():
            # Rollback
            del self.tasks[task.task_id]
            del self.adjacency_list[task.task_id]
            del self.reverse_adjacency[task.task_id]
            for dep_id in task.depends_on:
                self.adjacency_list[dep_id].remove(task.task_id)

            raise TaskDecompositionError(f"Adding task {task.task_id} would create a cycle")

    def _has_cycle(self) -> bool:
        """
        Détecte les cycles via DFS

        Complexité: O(V + E)

        Returns:
            True si cycle détecté, False sinon
        """
        visited = set()
        rec_stack = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in self.adjacency_list.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for node in self.tasks.keys():
            if node not in visited:
                if dfs(node):
                    return True

        return False

    def topological_sort(self) -> List[Task]:
        """
        Tri topologique pour ordonnancement d'exécution

        Utilise l'algorithme de Kahn (BFS-based)
        Complexité: O(V + E)

        Returns:
            Liste de tâches dans l'ordre d'exécution

        Raises:
            TaskDecompositionError: Si le graphe contient un cycle
        """
        in_degree = {task_id: len(deps) for task_id, deps in self.reverse_adjacency.items()}
        queue = [task_id for task_id, degree in in_degree.items() if degree == 0]
        sorted_tasks = []

        while queue:
            # Trier par priorité (CRITICAL > HIGH > NORMAL > LOW > OPTIONAL)
            queue.sort(key=lambda tid: self.tasks[tid].priority.value, reverse=True)

            task_id = queue.pop(0)
            sorted_tasks.append(self.tasks[task_id])

            # Réduire le degré des dépendants
            for dependent_id in self.adjacency_list.get(task_id, []):
                in_degree[dependent_id] -= 1
                if in_degree[dependent_id] == 0:
                    queue.append(dependent_id)

        if len(sorted_tasks) != len(self.tasks):
            raise TaskDecompositionError("Graph contains a cycle - topological sort impossible")

        return sorted_tasks

    def get_ready_tasks(self) -> List[Task]:
        """
        Retourne les tâches prêtes à être exécutées

        Une tâche est prête si:
        - Status = PENDING ou READY
        - Toutes ses dépendances sont COMPLETED

        Returns:
            Liste de tâches prêtes (triées par priorité)
        """
        ready = []

        for task in self.tasks.values():
            if task.status not in [TaskStatus.PENDING, TaskStatus.READY]:
                continue

            # Vérifier que toutes les dépendances sont complétées
            deps_completed = all(
                self.tasks[dep_id].status == TaskStatus.COMPLETED for dep_id in task.depends_on
            )

            if deps_completed:
                task.update_status(TaskStatus.READY)
                ready.append(task)

        # Trier par priorité
        ready.sort(key=lambda t: t.priority.value, reverse=True)
        return ready

    def get_parallelizable_tasks(self) -> List[List[Task]]:
        """
        Identifie les groupes de tâches exécutables en parallèle

        Returns:
            Liste de listes de tâches (chaque sous-liste = groupe parallèle)
        """
        sorted_tasks = self.topological_sort()
        levels: List[List[Task]] = []
        task_level: Dict[str, int] = {}

        for task in sorted_tasks:
            # Le niveau d'une tâche = max(niveaux de ses dépendances) + 1
            if not task.depends_on:
                level = 0
            else:
                level = max(task_level[dep_id] for dep_id in task.depends_on) + 1

            task_level[task.task_id] = level

            # Ajouter au groupe de niveau
            while len(levels) <= level:
                levels.append([])
            levels[level].append(task)

        return levels

    def to_dict(self) -> Dict[str, Any]:
        """Sérialise le graphe complet pour traçabilité"""
        return {
            "tasks": {tid: task.to_dict() for tid, task in self.tasks.items()},
            "adjacency_list": self.adjacency_list,
            "metadata": {
                "total_tasks": len(self.tasks),
                "serialized_at": datetime.utcnow().isoformat(),
            },
        }

    def __repr__(self) -> str:
        return f"TaskGraph(tasks={len(self.tasks)}, edges={sum(len(v) for v in self.adjacency_list.values())})"
