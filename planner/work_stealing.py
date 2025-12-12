"""
Work-Stealing Executor - Execution parallele avec vol de travail

Implemente le pattern Work-Stealing pour execution parallele efficace
de taches HTN, inspire de Go goroutines et Java ForkJoinPool.

Caracteristiques:
- Work-Stealing Queue par worker thread
- Load balancing automatique
- Thread-safe avec RLock
- Metriques Prometheus pour monitoring

Standards:
- Work-Stealing Pattern (Go, Java ForkJoinPool)
- Thread safety: threading.RLock()
- Monitoring: Prometheus metrics
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Callable, Deque, Dict, List, Optional, Union
from datetime import datetime
from collections import deque
import threading
import time
import traceback

if TYPE_CHECKING:
    from .task_graph import Task, TaskGraph

from .task_graph import TaskStatus
from .metrics import get_metrics


# Type aliases for strict typing
TaskResult = Union[str, int, float, bool, Dict[str, object], List[object], None]
ActionFunc = Callable[..., TaskResult]
ActionRegistry = Dict[str, ActionFunc]
StatsDict = Dict[str, Union[str, int, float, List[int]]]


class StealStrategy(str, Enum):
    """Strategies de vol de travail"""
    RANDOM = "random"        # Vol aleatoire
    ROUND_ROBIN = "round_robin"  # Round-robin
    LEAST_LOADED = "least_loaded"  # Moins charge


@dataclass
class StealResult:
    """Resultat d'une tentative de vol"""
    success: bool
    task: Optional[Task] = None
    from_worker: Optional[int] = None
    attempt_count: int = 0


class WorkStealingQueue:
    """
    Queue thread-safe pour work-stealing

    Caracteristiques:
    - Push/Pop depuis le meme thread (owner)
    - Steal depuis autres threads
    - Thread-safe avec locks
    """

    def __init__(self, worker_id: int) -> None:
        """
        Initialise la queue

        Args:
            worker_id: Identifiant du worker proprietaire
        """
        self.worker_id = worker_id
        self._queue: Deque[Task] = deque()
        self._lock = threading.RLock()

    def push(self, task: Task) -> None:
        """Ajoute une tache a la queue (owner thread)"""
        with self._lock:
            self._queue.append(task)

    def pop(self) -> Optional[Task]:
        """Retire une tache de la queue (owner thread)"""
        with self._lock:
            if len(self._queue) == 0:
                return None
            return self._queue.pop()

    def steal(self) -> Optional[Task]:
        """Vol une tache depuis un autre thread"""
        with self._lock:
            if len(self._queue) == 0:
                return None
            # Vol depuis le debut (FIFO pour le voleur)
            return self._queue.popleft()

    def size(self) -> int:
        """Taille actuelle de la queue"""
        with self._lock:
            return len(self._queue)

    def is_empty(self) -> bool:
        """Verifie si la queue est vide"""
        with self._lock:
            return len(self._queue) == 0


class WorkStealingExecutor:
    """
    Executeur avec work-stealing pour parallelisation efficace

    Caracteristiques:
    - Pool de workers avec queue par worker
    - Work-stealing automatique quand queue vide
    - Load balancing dynamique
    - Thread-safe pour metriques partagees
    """

    def __init__(
        self,
        num_workers: int = 4,
        steal_strategy: StealStrategy = StealStrategy.LEAST_LOADED,
        action_registry: Optional[ActionRegistry] = None,
        enable_metrics: bool = True,
    ) -> None:
        """
        Initialise l'executeur

        Args:
            num_workers: Nombre de workers threads
            steal_strategy: Strategie de vol
            action_registry: Registre d'actions (nom -> fonction)
            enable_metrics: Active metriques Prometheus
        """
        self.num_workers = num_workers
        self.steal_strategy = steal_strategy
        self.action_registry: ActionRegistry = action_registry or {}
        self.enable_metrics = enable_metrics

        # Queues par worker
        self._queues: List[WorkStealingQueue] = [
            WorkStealingQueue(worker_id=i) for i in range(num_workers)
        ]

        # Thread safety global
        self._global_lock = threading.RLock()

        # Workers threads
        self._workers: List[threading.Thread] = []
        self._shutdown_event = threading.Event()
        self._started = False

        # Statistiques partagees (protegees par _global_lock)
        self._total_tasks_completed = 0
        self._total_tasks_stolen = 0
        self._successful_steals = 0
        self._total_steal_attempts = 0
        self._failed_steals = 0

        # Metriques
        self.metrics = get_metrics() if enable_metrics else None

    def start(self) -> None:
        """Demarre les workers threads"""
        if self._started:
            return

        self._shutdown_event.clear()
        self._started = True

        # Creer et demarrer les workers
        for i in range(self.num_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                args=(i,),
                name=f"WorkStealingWorker-{i}",
                daemon=True,
            )
            worker.start()
            self._workers.append(worker)

    def shutdown(self, timeout: Optional[float] = None) -> None:
        """Arrete les workers threads"""
        if not self._started:
            return

        self._shutdown_event.set()

        # Attendre que tous les workers terminent
        for worker in self._workers:
            worker.join(timeout=timeout)

        self._workers.clear()
        self._started = False

    def submit(self, task: Task, worker_id: Optional[int] = None) -> None:
        """
        Soumet une tache a un worker

        Args:
            task: Tache a executer
            worker_id: Worker specifique (None = round-robin)
        """
        if not self._started:
            self.start()

        # Assigner a un worker (round-robin si non specifie)
        if worker_id is None:
            worker_id = hash(task.task_id) % self.num_workers

        self._queues[worker_id].push(task)

    def submit_batch(self, tasks: List[Task]) -> None:
        """Soumet plusieurs taches (distribution round-robin)"""
        for i, task in enumerate(tasks):
            worker_id = i % self.num_workers
            self.submit(task, worker_id=worker_id)

    def _worker_loop(self, worker_id: int) -> None:
        """Boucle principale du worker"""
        queue = self._queues[worker_id]

        while not self._shutdown_event.is_set():
            # 1. Essayer de prendre une tache de sa propre queue
            task = queue.pop()

            if task is None:
                # 2. Queue vide: essayer de voler depuis autres workers
                task = self._steal_task(worker_id)

            if task is None:
                # 3. Aucune tache disponible: attendre un peu
                time.sleep(0.01)  # 10ms
                continue

            # 4. Executer la tache
            try:
                self._execute_task(task, worker_id)

                # BUG FIX: Proteger l'increment avec le lock global
                with self._global_lock:
                    self._total_tasks_completed += 1
                    self._record_metrics("task_completed")
            except Exception as e:
                # Erreur d'execution: log et continuer
                self._handle_task_error(task, e, worker_id)

    def _steal_task(self, worker_id: int) -> Optional[Task]:
        """
        Tente de voler une tache depuis un autre worker

        Args:
            worker_id: Worker qui tente de voler

        Returns:
            Task volee ou None si echec
        """
        # BUG FIX: Proteger l'increment avec le lock global
        with self._global_lock:
            self._total_steal_attempts += 1

        # Strategie de vol
        if self.steal_strategy == StealStrategy.RANDOM:
            targets = self._get_random_targets(worker_id)
        elif self.steal_strategy == StealStrategy.ROUND_ROBIN:
            targets = self._get_round_robin_targets(worker_id)
        else:  # LEAST_LOADED
            targets = self._get_least_loaded_targets(worker_id)

        # Essayer de voler depuis chaque cible
        for target_id in targets:
            if target_id == worker_id:
                continue

            stolen_task = self._queues[target_id].steal()
            if stolen_task is not None:
                # BUG FIX: Proteger les increments avec le lock global
                with self._global_lock:
                    self._total_tasks_stolen += 1
                    self._successful_steals += 1
                    self._record_metrics("steal_success")
                return stolen_task

        # Echec: aucune tache volee
        with self._global_lock:
            self._failed_steals += 1
            self._record_metrics("steal_failed")

        return None

    def _get_random_targets(self, worker_id: int) -> List[int]:
        """Retourne des cibles aleatoires pour vol"""
        import random
        targets = list(range(self.num_workers))
        targets.remove(worker_id)
        random.shuffle(targets)
        return targets

    def _get_round_robin_targets(self, worker_id: int) -> List[int]:
        """Retourne des cibles en round-robin"""
        targets: List[int] = []
        for i in range(1, self.num_workers):
            target_id = (worker_id + i) % self.num_workers
            targets.append(target_id)
        return targets

    def _get_least_loaded_targets(self, worker_id: int) -> List[int]:
        """Retourne des cibles triees par charge (plus charge d'abord)"""
        # Calculer la charge de chaque queue
        loads: List[tuple[int, int]] = []
        for i in range(self.num_workers):
            if i != worker_id:
                load = self._queues[i].size()
                loads.append((load, i))

        # Trier par charge decroissante (voler depuis le plus charge)
        loads.sort(reverse=True, key=lambda x: x[0])
        return [wid for _, wid in loads]

    def _execute_task(self, task: Task, worker_id: int) -> None:
        """
        Execute une tache

        Args:
            task: Tache a executer
            worker_id: Worker qui execute
        """
        # Mettre a jour le statut
        task.status = TaskStatus.RUNNING
        task.metadata["started_at"] = datetime.now().isoformat()

        # Chercher l'action dans le registre
        action_name = task.action
        if action_name not in self.action_registry:
            raise ValueError(f"Action '{action_name}' non trouvee dans le registre")

        action_func = self.action_registry[action_name]

        # Executer l'action
        try:
            result = action_func(**task.params)
            task.set_result(result)
            task.status = TaskStatus.COMPLETED
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.metadata["completed_at"] = datetime.now().isoformat()
            raise

    def _handle_task_error(self, task: Task, error: Exception, worker_id: int) -> None:
        """Gere une erreur d'execution"""
        task.status = TaskStatus.FAILED
        task.error = str(error)
        task.metadata["completed_at"] = datetime.now().isoformat()

        # Log l'erreur (conformite Loi 25)
        _error_trace = traceback.format_exc()
        # TODO: Integrer avec systeme de logging

        self._record_metrics("task_failed")

    def get_stats(self) -> StatsDict:
        """Retourne les statistiques de l'executeur"""
        with self._global_lock:
            total_steals = self._successful_steals + self._failed_steals
            steal_success_rate = (
                self._successful_steals / total_steals
                if total_steals > 0 else 0.0
            )

            return {
                "total_tasks_completed": self._total_tasks_completed,
                "total_tasks_stolen": self._total_tasks_stolen,
                "successful_steals": self._successful_steals,
                "failed_steals": self._failed_steals,
                "total_steal_attempts": self._total_steal_attempts,
                "steal_success_rate": steal_success_rate,
                "num_workers": self.num_workers,
                "steal_strategy": self.steal_strategy.value,
                "queue_sizes": [q.size() for q in self._queues],
            }

    def _record_metrics(self, event: str) -> None:
        """Enregistre les metriques Prometheus"""
        if not self.metrics or not hasattr(self.metrics, 'record_work_stealing'):
            return

        try:
            self.metrics.record_work_stealing(
                event=event,
                num_workers=self.num_workers,
            )
        except Exception:
            # Ignorer les erreurs de metriques (ne pas casser l'executeur)
            pass


# Instance globale (singleton)
_executor_instance: Optional[WorkStealingExecutor] = None
_executor_lock = threading.RLock()


def get_work_stealing_executor(
    num_workers: int = 4,
    steal_strategy: StealStrategy = StealStrategy.LEAST_LOADED,
    action_registry: Optional[ActionRegistry] = None,
    enable_metrics: bool = True,
) -> WorkStealingExecutor:
    """
    Obtient ou cree l'instance globale de l'executeur

    Args:
        num_workers: Nombre de workers (ignore si instance existe)
        steal_strategy: Strategie de vol (ignore si instance existe)
        action_registry: Registre d'actions (ignore si instance existe)
        enable_metrics: Active metriques (ignore si instance existe)

    Returns:
        Instance WorkStealingExecutor (singleton)
    """
    global _executor_instance

    with _executor_lock:
        if _executor_instance is None:
            _executor_instance = WorkStealingExecutor(
                num_workers=num_workers,
                steal_strategy=steal_strategy,
                action_registry=action_registry,
                enable_metrics=enable_metrics,
            )

        return _executor_instance


def reset_work_stealing_executor() -> None:
    """Reinitialise l'executeur global (utile pour tests)"""
    global _executor_instance

    with _executor_lock:
        if _executor_instance is not None:
            _executor_instance.shutdown()
        _executor_instance = None
