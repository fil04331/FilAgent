"""
Task Executor - Execution de plans HTN avec parallelisation

Implemente:
- Execution sequentielle et parallele de taches
- Gestion des dependances via tri topologique
- Recovery gracieux sur echec
- Tracabilite complete (conformite Loi 25, RGPD)

Strategies d'execution:
- Sequential: Une tache a la fois (securitaire)
- Parallel: Taches independantes en parallele (performance)
- Adaptive: Hybride selon disponibilite ressources

Conformite:
- Logs WORM pour chaque execution
- Decision Records pour choix d'execution
- Provenance tracking (W3C PROV)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Callable, Dict, List, Optional, Union
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
import traceback
import time

if TYPE_CHECKING:
    from .task_graph import Task, TaskGraph

from .task_graph import TaskStatus, TaskPriority
from .metrics import get_metrics

# Type aliases for strict typing
TaskResult = Union[str, int, float, bool, Dict[str, object], List[object], None]
ActionFunc = Callable[[Dict[str, object]], TaskResult]
ActionRegistry = Dict[str, ActionFunc]
MetadataDict = Dict[str, Union[str, int, float, bool, Dict[str, object], List[object]]]


class ExecutionStrategy(str, Enum):
    """Strategies d'execution"""

    SEQUENTIAL = "sequential"  # Une a la fois
    PARALLEL = "parallel"  # Parallelisation maximale
    ADAPTIVE = "adaptive"  # Hybride selon contexte


class ExecutionError(Exception):
    """Erreur lors de l'execution d'une tache"""

    pass


@dataclass
class ExecutionResult:
    """
    Resultat d'une execution de plan

    Attributes:
        success: True si toutes les taches critiques ont reussi
        completed_tasks: Nombre de taches completees
        failed_tasks: Nombre de taches echouees
        skipped_tasks: Nombre de taches sautees
        total_duration_ms: Duree totale d'execution (millisecondes)
        task_results: Resultats par task_id
        errors: Erreurs rencontrees par task_id
        metadata: Metadonnees de tracabilite
    """

    success: bool
    completed_tasks: int
    failed_tasks: int
    skipped_tasks: int
    total_duration_ms: float
    task_results: Dict[str, TaskResult] = field(default_factory=dict)
    errors: Dict[str, str] = field(default_factory=dict)
    metadata: MetadataDict = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        """Serialise pour logging"""
        # Log task results metadata for debugging
        _logger.debug("ExecutionResult.to_dict() - Converting task_results with %d tasks", len(self.task_results))
        for k, v in self.task_results.items():
            _logger.debug("Task %s: type=%s, length=%d chars", k, type(v).__name__, len(str(v)))

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
    Executeur de graphes de taches HTN

    Responsabilites:
        - Orchestrer l'execution selon le plan
        - Gerer les dependances et ordre d'execution
        - Paralleliser les taches independantes
        - Gerer les erreurs et recovery
        - Tracer toutes les executions

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
        action_registry: Optional[ActionRegistry] = None,
        strategy: ExecutionStrategy = ExecutionStrategy.ADAPTIVE,
        max_workers: int = 4,
        timeout_per_task_sec: int = 60,
        enable_tracing: bool = True,
    ) -> None:
        """
        Initialise l'executeur

        Args:
            action_registry: Mapping action_name -> fonction executable
            strategy: Strategie d'execution
            max_workers: Nombre max de workers paralleles
            timeout_per_task_sec: Timeout par tache (secondes)
            enable_tracing: Active tracabilite complete
        """
        self.actions: ActionRegistry = action_registry or {}
        self.strategy = strategy
        self.max_workers = max_workers
        self.timeout = timeout_per_task_sec
        self.enable_tracing = enable_tracing

        # Statistiques d'execution
        self._execution_stats: Dict[str, int] = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
        }

    def register_action(self, name: str, func: ActionFunc) -> None:
        """
        Enregistre une action executable

        Args:
            name: Nom de l'action
            func: Fonction a executer (signature: func(params: Dict) -> TaskResult)
        """
        self.actions[name] = func

    def execute(
        self,
        graph: TaskGraph,
        context: Optional[MetadataDict] = None,
    ) -> ExecutionResult:
        """
        Execute un graphe de taches

        Args:
            graph: Graphe de taches a executer
            context: Contexte d'execution (conversation, etat, etc.)

        Returns:
            ExecutionResult avec statistiques et resultats

        Raises:
            ExecutionError: Si l'execution echoue de maniere critique
        """
        start_time = datetime.utcnow()
        execution_start_time = time.time()
        metadata: MetadataDict = {
            "started_at": start_time.isoformat(),
            "strategy": self.strategy.value,
            "total_tasks": len(graph.tasks),
            "context": context or {},
        }

        # Metriques: mettre a jour taches en cours
        metrics = get_metrics()
        metrics.update_task_in_progress(self.strategy.value, len(graph.tasks))

        try:
            # Choisir la strategie d'execution
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

            # Compter taches paralleles (approximation)
            parallel_tasks = 0
            if self.strategy in [ExecutionStrategy.PARALLEL, ExecutionStrategy.ADAPTIVE]:
                levels = graph.get_parallelizable_tasks()
                for level in levels:
                    if len(level) > 1:
                        parallel_tasks += len(level)

            # Determiner le succes global
            # Succes si toutes les taches CRITICAL/HIGH sont completees
            critical_failed = any(
                t.status == TaskStatus.FAILED and t.priority.value >= TaskPriority.HIGH.value
                for t in graph.tasks.values()
            )
            success = not critical_failed

            # Construire le resultat
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

            # Metriques: enregistrer execution
            metrics.record_execution(
                strategy=self.strategy.value,
                success=success,
                duration_seconds=duration_seconds,
                completed_tasks=completed,
                failed_tasks=failed,
                skipped_tasks=skipped,
                parallel_tasks=parallel_tasks,
            )

            # Metriques: enregistrer chaque tache
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

            # Metriques: remettre a zero taches en cours
            metrics.update_task_in_progress(self.strategy.value, 0)

            # Mettre a jour les statistiques
            self._execution_stats["total_executions"] += 1
            if success:
                self._execution_stats["successful_executions"] += 1
            else:
                self._execution_stats["failed_executions"] += 1

            return result

        except Exception as e:
            # Tracabilite: echec critique
            metadata["completed_at"] = datetime.utcnow().isoformat()
            metadata["critical_error"] = str(e)
            metadata["traceback"] = traceback.format_exc()

            self._execution_stats["total_executions"] += 1
            self._execution_stats["failed_executions"] += 1

            raise ExecutionError(f"Execution failed critically: {str(e)}") from e

    def _execute_sequential(
        self, graph: TaskGraph, metadata: MetadataDict
    ) -> Dict[str, Union[Dict[str, TaskResult], Dict[str, str]]]:
        """
        Execution sequentielle (une tache a la fois)

        Avantages: Previsible, deterministe, facile a debugger
        Limitations: Pas de parallelisation, plus lent
        """
        task_results: Dict[str, TaskResult] = {}
        errors: Dict[str, str] = {}

        # Tri topologique pour ordre d'execution
        sorted_tasks = graph.topological_sort()

        for task in sorted_tasks:
            # Verifier si les dependances ont reussi
            if not self._check_dependencies(task, graph):
                task.update_status(TaskStatus.SKIPPED, "Dependency failed")
                continue

            # Executer la tache
            task.update_status(TaskStatus.RUNNING)

            try:
                result = self._execute_task(task)

                # Log task execution result
                _logger.debug(
                    "Task executed: %s (name=%s, result_type=%s, result_length=%d chars)",
                    task.task_id,
                    task.name,
                    type(result).__name__,
                    len(str(result)),
                )

                task.set_result(result)
                task.update_status(TaskStatus.COMPLETED)
                task_results[task.task_id] = result

            except Exception as e:
                error_msg = f"{type(e).__name__}: {str(e)}"
                task.update_status(TaskStatus.FAILED, error_msg)
                errors[task.task_id] = error_msg

                # Propager l'echec aux taches dependantes
                self._propagate_failure(task, graph)

        return {
            "task_results": task_results,
            "errors": errors,
        }

    def _execute_parallel(
        self, graph: TaskGraph, metadata: MetadataDict
    ) -> Dict[str, Union[Dict[str, TaskResult], Dict[str, str]]]:
        """
        Execution parallele (taches independantes en parallele)

        Avantages: Rapide, exploite concurrence
        Limitations: Plus complexe, necessite thread-safety
        """
        task_results: Dict[str, TaskResult] = {}
        errors: Dict[str, str] = {}

        # Identifier les niveaux de parallelisation
        levels = graph.get_parallelizable_tasks()

        # Executer niveau par niveau
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            for level_tasks in levels:
                # Soumettre toutes les taches du niveau
                futures: Dict[Future[TaskResult], Task] = {}

                for task in level_tasks:
                    # Verifier dependances
                    if not self._check_dependencies(task, graph):
                        task.update_status(TaskStatus.SKIPPED, "Dependency failed")
                        continue

                    # Soumettre a l'executeur
                    task.update_status(TaskStatus.RUNNING)
                    future = executor.submit(self._execute_task, task)
                    futures[future] = task

                # Attendre la completion du niveau
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

                        # Propager l'echec
                        self._propagate_failure(task, graph)

        return {
            "task_results": task_results,
            "errors": errors,
        }

    def _execute_adaptive(
        self, graph: TaskGraph, metadata: MetadataDict
    ) -> Dict[str, Union[Dict[str, TaskResult], Dict[str, str]]]:
        """
        Execution adaptive (hybride selon contexte)

        Strategie:
        - Si < 3 taches: sequentiel
        - Si taches critiques: sequentiel
        - Sinon: parallele
        """
        # Decider de la strategie
        num_tasks = len(graph.tasks)
        has_critical = any(t.priority == TaskPriority.CRITICAL for t in graph.tasks.values())

        if num_tasks < 3 or has_critical:
            # Sequentiel pour securite
            metadata["adaptive_choice"] = "sequential"
            metadata["adaptive_reason"] = "Few tasks or critical priority"
            return self._execute_sequential(graph, metadata)
        else:
            # Parallele pour performance
            metadata["adaptive_choice"] = "parallel"
            metadata["adaptive_reason"] = "Multiple independent tasks"
            return self._execute_parallel(graph, metadata)

    def _execute_task(self, task: Task) -> TaskResult:
        """
        Execute une tache atomique

        Args:
            task: Tache a executer

        Returns:
            Resultat de l'execution

        Raises:
            ExecutionError: Si l'action n'existe pas ou echoue
        """
        # Verifier que l'action existe
        if task.action not in self.actions:
            raise ExecutionError(f"Unknown action '{task.action}' for task {task.task_id}")

        # Executer l'action
        action_func = self.actions[task.action]

        try:
            result = action_func(task.params)
            return result
        except Exception as e:
            # Preserve original exception type in error message for traceability
            raise ExecutionError(f"Action '{task.action}' failed: {type(e).__name__}: {str(e)}") from e

    def _check_dependencies(self, task: Task, graph: TaskGraph) -> bool:
        """
        Verifie que toutes les dependances sont completees

        Args:
            task: Tache a verifier
            graph: Graphe contenant les dependances

        Returns:
            True si toutes les dependances sont COMPLETED
        """
        for dep_id in task.depends_on:
            dep_task = graph.tasks.get(dep_id)
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                return False
        return True

    def _propagate_failure(self, failed_task: Task, graph: TaskGraph) -> None:
        """
        Propage l'echec d'une tache a ses dependants

        Marque toutes les taches qui dependent de failed_task comme SKIPPED
        """
        # Trouver tous les dependants (BFS)
        to_skip: List[Task] = []
        queue: List[str] = [failed_task.task_id]
        visited: set[str] = set()

        while queue:
            current_id = queue.pop(0)
            if current_id in visited:
                continue
            visited.add(current_id)

            # Trouver les taches qui dependent de current
            for task in graph.tasks.values():
                if current_id in task.depends_on and task.task_id not in visited:
                    to_skip.append(task)
                    queue.append(task.task_id)

        # Marquer comme sautees
        for task in to_skip:
            if task.status == TaskStatus.PENDING:
                task.update_status(TaskStatus.SKIPPED, f"Dependency {failed_task.task_id} failed")

    def get_stats(self) -> Dict[str, int]:
        """Retourne les statistiques d'execution"""
        return self._execution_stats.copy()
