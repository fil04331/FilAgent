"""
Task Executor - Exécution de plans HTN avec parallélisation

Implémente:
- Exécution séquentielle et parallèle de tâches
- Gestion des dépendances via tri topologique
- Recovery gracieux sur échec
- Traçabilité complète (conformité Loi 25, RGPD)

Stratégies d'exécution:
- Sequential: Une tâche à la fois (sécuritaire)
- Parallel: Tâches indépendantes en parallèle (performance)
- Adaptive: Hybride selon disponibilité ressources

Conformité:
- Logs WORM pour chaque exécution
- Decision Records pour choix d'exécution
- Provenance tracking (W3C PROV)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Any, Callable
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
import traceback
import time

from .task_graph import Task, TaskGraph, TaskStatus, TaskPriority
from .metrics import get_metrics


class ExecutionStrategy(str, Enum):
    """Stratégies d'exécution"""

    SEQUENTIAL = "sequential"  # Une à la fois
    PARALLEL = "parallel"  # Parallélisation maximale
    ADAPTIVE = "adaptive"  # Hybride selon contexte


class ExecutionError(Exception):
    """Erreur lors de l'exécution d'une tâche"""

    pass


@dataclass
class ExecutionResult:
    """
    Résultat d'une exécution de plan

    Attributes:
        success: True si toutes les tâches critiques ont réussi
        completed_tasks: Nombre de tâches complétées
        failed_tasks: Nombre de tâches échouées
        skipped_tasks: Nombre de tâches sautées
        total_duration_ms: Durée totale d'exécution (millisecondes)
        task_results: Résultats par task_id
        errors: Erreurs rencontrées par task_id
        metadata: Métadonnées de traçabilité
    """

    success: bool
    completed_tasks: int
    failed_tasks: int
    skipped_tasks: int
    total_duration_ms: float
    task_results: Dict[str, Any] = field(default_factory=dict)
    errors: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Sérialise pour logging"""
        return {
            "success": self.success,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "skipped_tasks": self.skipped_tasks,
            "total_duration_ms": self.total_duration_ms,
            "task_results": {k: str(v) for k, v in self.task_results.items()},
            "errors": self.errors,
            "metadata": self.metadata,
        }


class TaskExecutor:
    """
    Exécuteur de graphes de tâches HTN

    Responsabilités:
        - Orchestrer l'exécution selon le plan
        - Gérer les dépendances et ordre d'exécution
        - Paralléliser les tâches indépendantes
        - Gérer les erreurs et recovery
        - Tracer toutes les exécutions

    Usage:
        executor = TaskExecutor(
            action_registry=registry,
            strategy=ExecutionStrategy.PARALLEL,
            max_workers=4
        )
        result = executor.execute(plan_result.graph)
    """

    def __init__(
        self,
        action_registry: Optional[Dict[str, Callable]] = None,
        strategy: ExecutionStrategy = ExecutionStrategy.ADAPTIVE,
        max_workers: int = 4,
        timeout_per_task_sec: int = 60,
        enable_tracing: bool = True,
    ):
        """
        Initialise l'exécuteur

        Args:
            action_registry: Mapping action_name -> fonction exécutable
            strategy: Stratégie d'exécution
            max_workers: Nombre max de workers parallèles
            timeout_per_task_sec: Timeout par tâche (secondes)
            enable_tracing: Active traçabilité complète
        """
        self.actions = action_registry or {}
        self.strategy = strategy
        self.max_workers = max_workers
        self.timeout = timeout_per_task_sec
        self.enable_tracing = enable_tracing

        # Statistiques d'exécution
        self._execution_stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
        }

    def register_action(self, name: str, func: Callable):
        """
        Enregistre une action exécutable

        Args:
            name: Nom de l'action
            func: Fonction à exécuter (signature: func(params: Dict) -> Any)
        """
        self.actions[name] = func

    def execute(
        self,
        graph: TaskGraph,
        context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """
        Exécute un graphe de tâches

        Args:
            graph: Graphe de tâches à exécuter
            context: Contexte d'exécution (conversation, état, etc.)

        Returns:
            ExecutionResult avec statistiques et résultats

        Raises:
            ExecutionError: Si l'exécution échoue de manière critique
        """
        start_time = datetime.utcnow()
        execution_start_time = time.time()
        metadata = {
            "started_at": start_time.isoformat(),
            "strategy": self.strategy.value,
            "total_tasks": len(graph.tasks),
            "context": context or {},
        }

        # Métriques: mettre à jour tâches en cours
        metrics = get_metrics()
        metrics.update_task_in_progress(self.strategy.value, len(graph.tasks))

        try:
            # Choisir la stratégie d'exécution
            if self.strategy == ExecutionStrategy.SEQUENTIAL:
                results = self._execute_sequential(graph, metadata)
            elif self.strategy == ExecutionStrategy.PARALLEL:
                results = self._execute_parallel(graph, metadata)
            else:  # ADAPTIVE
                results = self._execute_adaptive(graph, metadata)

            # Calculer statistiques finales
            end_time = datetime.utcnow()
            duration_ms = (end_time - start_time).total_seconds() * 1000
            duration_seconds = time.time() - execution_start_time

            completed = sum(1 for t in graph.tasks.values() if t.status == TaskStatus.COMPLETED)
            failed = sum(1 for t in graph.tasks.values() if t.status == TaskStatus.FAILED)
            skipped = sum(1 for t in graph.tasks.values() if t.status == TaskStatus.SKIPPED)

            # Compter tâches parallèles (approximation)
            parallel_tasks = 0
            if self.strategy in [ExecutionStrategy.PARALLEL, ExecutionStrategy.ADAPTIVE]:
                levels = graph.get_parallelizable_tasks()
                for level in levels:
                    if len(level) > 1:
                        parallel_tasks += len(level)

            # Déterminer le succès global
            # Succès si toutes les tâches CRITICAL/HIGH sont complétées
            critical_failed = any(
                t.status == TaskStatus.FAILED and t.priority.value >= TaskPriority.HIGH.value
                for t in graph.tasks.values()
            )
            success = not critical_failed

            # Construire le résultat
            metadata["completed_at"] = end_time.isoformat()
            metadata["duration_ms"] = duration_ms

            result = ExecutionResult(
                success=success,
                completed_tasks=completed,
                failed_tasks=failed,
                skipped_tasks=skipped,
                total_duration_ms=duration_ms,
                task_results=results["task_results"],
                errors=results["errors"],
                metadata=metadata,
            )

            # Métriques: enregistrer exécution
            metrics.record_execution(
                strategy=self.strategy.value,
                success=success,
                duration_seconds=duration_seconds,
                completed_tasks=completed,
                failed_tasks=failed,
                skipped_tasks=skipped,
                parallel_tasks=parallel_tasks,
            )

            # Métriques: enregistrer chaque tâche
            for task in graph.tasks.values():
                if task.status == TaskStatus.COMPLETED:
                    metrics.record_task(
                        priority=task.priority.name.lower(),
                        action=task.action,
                        status="completed",
                    )
                elif task.status == TaskStatus.FAILED:
                    error_type = type(task.error).__name__ if task.error else "unknown"
                    metrics.record_task(
                        priority=task.priority.name.lower(),
                        action=task.action,
                        status="failed",
                        error_type=error_type,
                    )
                elif task.status == TaskStatus.SKIPPED:
                    metrics.record_task(
                        priority=task.priority.name.lower(),
                        action=task.action,
                        status="skipped",
                    )

            # Métriques: remettre à zéro tâches en cours
            metrics.update_task_in_progress(self.strategy.value, 0)

            # Mettre à jour les statistiques
            self._execution_stats["total_executions"] += 1
            if success:
                self._execution_stats["successful_executions"] += 1
            else:
                self._execution_stats["failed_executions"] += 1

            return result

        except Exception as e:
            # Traçabilité: échec critique
            metadata["completed_at"] = datetime.utcnow().isoformat()
            metadata["critical_error"] = str(e)
            metadata["traceback"] = traceback.format_exc()

            self._execution_stats["total_executions"] += 1
            self._execution_stats["failed_executions"] += 1

            raise ExecutionError(f"Execution failed critically: {str(e)}") from e

    def _execute_sequential(self, graph: TaskGraph, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Exécution séquentielle (une tâche à la fois)

        Avantages: Prévisible, déterministe, facile à debugger
        Limitations: Pas de parallélisation, plus lent
        """
        task_results = {}
        errors = {}

        # Tri topologique pour ordre d'exécution
        sorted_tasks = graph.topological_sort()

        for task in sorted_tasks:
            # Vérifier si les dépendances ont réussi
            if not self._check_dependencies(task, graph):
                task.update_status(TaskStatus.SKIPPED, "Dependency failed")
                continue

            # Exécuter la tâche
            task.update_status(TaskStatus.RUNNING)

            try:
                result = self._execute_task(task)
                task.set_result(result)
                task.update_status(TaskStatus.COMPLETED)
                task_results[task.task_id] = result

            except Exception as e:
                error_msg = f"{type(e).__name__}: {str(e)}"
                task.update_status(TaskStatus.FAILED, error_msg)
                errors[task.task_id] = error_msg

                # Propager l'échec aux tâches dépendantes
                self._propagate_failure(task, graph)

        return {
            "task_results": task_results,
            "errors": errors,
        }

    def _execute_parallel(self, graph: TaskGraph, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Exécution parallèle (tâches indépendantes en parallèle)

        Avantages: Rapide, exploite concurrence
        Limitations: Plus complexe, nécessite thread-safety
        """
        task_results = {}
        errors = {}

        # Identifier les niveaux de parallélisation
        levels = graph.get_parallelizable_tasks()

        # Exécuter niveau par niveau
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            for level_tasks in levels:
                # Soumettre toutes les tâches du niveau
                futures: Dict[Future, Task] = {}

                for task in level_tasks:
                    # Vérifier dépendances
                    if not self._check_dependencies(task, graph):
                        task.update_status(TaskStatus.SKIPPED, "Dependency failed")
                        continue

                    # Soumettre à l'exécuteur
                    task.update_status(TaskStatus.RUNNING)
                    future = executor.submit(self._execute_task, task)
                    futures[future] = task

                # Attendre la complétion du niveau
                for future in as_completed(futures):
                    task = futures[future]

                    try:
                        result = future.result(timeout=self.timeout)
                        task.set_result(result)
                        task.update_status(TaskStatus.COMPLETED)
                        task_results[task.task_id] = result

                    except Exception as e:
                        error_msg = f"{type(e).__name__}: {str(e)}"
                        task.update_status(TaskStatus.FAILED, error_msg)
                        errors[task.task_id] = error_msg

                        # Propager l'échec
                        self._propagate_failure(task, graph)

        return {
            "task_results": task_results,
            "errors": errors,
        }

    def _execute_adaptive(self, graph: TaskGraph, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Exécution adaptive (hybride selon contexte)

        Stratégie:
        - Si < 3 tâches: séquentiel
        - Si tâches critiques: séquentiel
        - Sinon: parallèle
        """
        # Décider de la stratégie
        num_tasks = len(graph.tasks)
        has_critical = any(t.priority == TaskPriority.CRITICAL for t in graph.tasks.values())

        if num_tasks < 3 or has_critical:
            # Séquentiel pour sécurité
            metadata["adaptive_choice"] = "sequential"
            metadata["adaptive_reason"] = "Few tasks or critical priority"
            return self._execute_sequential(graph, metadata)
        else:
            # Parallèle pour performance
            metadata["adaptive_choice"] = "parallel"
            metadata["adaptive_reason"] = "Multiple independent tasks"
            return self._execute_parallel(graph, metadata)

    def _execute_task(self, task: Task) -> Any:
        """
        Exécute une tâche atomique

        Args:
            task: Tâche à exécuter

        Returns:
            Résultat de l'exécution

        Raises:
            ExecutionError: Si l'action n'existe pas ou échoue
        """
        # Vérifier que l'action existe
        if task.action not in self.actions:
            raise ExecutionError(f"Unknown action '{task.action}' for task {task.task_id}")

        # Exécuter l'action
        action_func = self.actions[task.action]

        try:
            result = action_func(task.params)
            return result
        except Exception as e:
            # Preserve original exception type in error message for traceability
            raise ExecutionError(
                f"Action '{task.action}' failed: {type(e).__name__}: {str(e)}"
            ) from e
    
    def _check_dependencies(self, task: Task, graph: TaskGraph) -> bool:
        """
        Vérifie que toutes les dépendances sont complétées

        Args:
            task: Tâche à vérifier
            graph: Graphe contenant les dépendances

        Returns:
            True si toutes les dépendances sont COMPLETED
        """
        for dep_id in task.depends_on:
            dep_task = graph.tasks.get(dep_id)
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                return False
        return True

    def _propagate_failure(self, failed_task: Task, graph: TaskGraph):
        """
        Propage l'échec d'une tâche à ses dépendants

        Marque toutes les tâches qui dépendent de failed_task comme SKIPPED
        """
        # Trouver tous les dépendants (BFS)
        to_skip = []
        queue = [failed_task.task_id]
        visited = set()

        while queue:
            current_id = queue.pop(0)
            if current_id in visited:
                continue
            visited.add(current_id)

            # Trouver les tâches qui dépendent de current
            for task in graph.tasks.values():
                if current_id in task.depends_on and task.task_id not in visited:
                    to_skip.append(task)
                    queue.append(task.task_id)

        # Marquer comme sautées
        for task in to_skip:
            if task.status == TaskStatus.PENDING:
                task.update_status(TaskStatus.SKIPPED, f"Dependency {failed_task.task_id} failed")

    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques d'exécution"""
        return self._execution_stats.copy()
