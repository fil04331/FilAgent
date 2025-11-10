"""
Work-Stealing Executor - Exécution parallèle avec vol de travail

Implémente le pattern Work-Stealing pour exécution parallèle efficace
de tâches HTN, inspiré de Go goroutines et Java ForkJoinPool.

Caractéristiques:
- Work-Stealing Queue par worker thread
- Load balancing automatique
- Thread-safe avec RLock
- Métriques Prometheus pour monitoring

Standards:
- Work-Stealing Pattern (Go, Java ForkJoinPool)
- Thread safety: threading.RLock()
- Monitoring: Prometheus metrics
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Any, Callable, Deque
from datetime import datetime
from collections import deque
import threading
import time
import traceback

from .task_graph import Task, TaskGraph, TaskStatus, TaskPriority
from .metrics import get_metrics


class StealStrategy(str, Enum):
    """Stratégies de vol de travail"""
    RANDOM = "random"        # Vol aléatoire
    ROUND_ROBIN = "round_robin"  # Round-robin
    LEAST_LOADED = "least_loaded"  # Moins chargé


@dataclass
class StealResult:
    """Résultat d'une tentative de vol"""
    success: bool
    task: Optional[Task] = None
    from_worker: Optional[int] = None
    attempt_count: int = 0


class WorkStealingQueue:
    """
    Queue thread-safe pour work-stealing
    
    Caractéristiques:
    - Push/Pop depuis le même thread (owner)
    - Steal depuis autres threads
    - Thread-safe avec locks
    """
    
    def __init__(self, worker_id: int):
        """
        Initialise la queue
        
        Args:
            worker_id: Identifiant du worker propriétaire
        """
        self.worker_id = worker_id
        self._queue: Deque[Task] = deque()
        self._lock = threading.RLock()
    
    def push(self, task: Task):
        """Ajoute une tâche à la queue (owner thread)"""
        with self._lock:
            self._queue.append(task)
    
    def pop(self) -> Optional[Task]:
        """Retire une tâche de la queue (owner thread)"""
        with self._lock:
            if len(self._queue) == 0:
                return None
            return self._queue.pop()
    
    def steal(self) -> Optional[Task]:
        """Vol une tâche depuis un autre thread"""
        with self._lock:
            if len(self._queue) == 0:
                return None
            # Vol depuis le début (FIFO pour le voleur)
            return self._queue.popleft()
    
    def size(self) -> int:
        """Taille actuelle de la queue"""
        with self._lock:
            return len(self._queue)
    
    def is_empty(self) -> bool:
        """Vérifie si la queue est vide"""
        with self._lock:
            return len(self._queue) == 0


class WorkStealingExecutor:
    """
    Exécuteur avec work-stealing pour parallélisation efficace
    
    Caractéristiques:
    - Pool de workers avec queue par worker
    - Work-stealing automatique quand queue vide
    - Load balancing dynamique
    - Thread-safe pour métriques partagées
    """
    
    def __init__(
        self,
        num_workers: int = 4,
        steal_strategy: StealStrategy = StealStrategy.LEAST_LOADED,
        action_registry: Optional[Dict[str, Callable]] = None,
        enable_metrics: bool = True,
    ):
        """
        Initialise l'exécuteur
        
        Args:
            num_workers: Nombre de workers threads
            steal_strategy: Stratégie de vol
            action_registry: Registre d'actions (nom -> fonction)
            enable_metrics: Active métriques Prometheus
        """
        self.num_workers = num_workers
        self.steal_strategy = steal_strategy
        self.action_registry = action_registry or {}
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
        
        # Statistiques partagées (protégées par _global_lock)
        self._total_tasks_completed = 0
        self._total_tasks_stolen = 0
        self._successful_steals = 0
        self._total_steal_attempts = 0
        self._failed_steals = 0
        
        # Métriques
        self.metrics = get_metrics() if enable_metrics else None
    
    def start(self):
        """Démarre les workers threads"""
        if self._started:
            return
        
        self._shutdown_event.clear()
        self._started = True
        
        # Créer et démarrer les workers
        for i in range(self.num_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                args=(i,),
                name=f"WorkStealingWorker-{i}",
                daemon=True,
            )
            worker.start()
            self._workers.append(worker)
    
    def shutdown(self, timeout: Optional[float] = None):
        """Arrête les workers threads"""
        if not self._started:
            return
        
        self._shutdown_event.set()
        
        # Attendre que tous les workers terminent
        for worker in self._workers:
            worker.join(timeout=timeout)
        
        self._workers.clear()
        self._started = False
    
    def submit(self, task: Task, worker_id: Optional[int] = None):
        """
        Soumet une tâche à un worker
        
        Args:
            task: Tâche à exécuter
            worker_id: Worker spécifique (None = round-robin)
        """
        if not self._started:
            self.start()
        
        # Assigner à un worker (round-robin si non spécifié)
        if worker_id is None:
            worker_id = hash(task.task_id) % self.num_workers
        
        self._queues[worker_id].push(task)
    
    def submit_batch(self, tasks: List[Task]):
        """Soumet plusieurs tâches (distribution round-robin)"""
        for i, task in enumerate(tasks):
            worker_id = i % self.num_workers
            self.submit(task, worker_id=worker_id)
    
    def _worker_loop(self, worker_id: int):
        """Boucle principale du worker"""
        queue = self._queues[worker_id]
        
        while not self._shutdown_event.is_set():
            # 1. Essayer de prendre une tâche de sa propre queue
            task = queue.pop()
            
            if task is None:
                # 2. Queue vide: essayer de voler depuis autres workers
                task = self._steal_task(worker_id)
            
            if task is None:
                # 3. Aucune tâche disponible: attendre un peu
                time.sleep(0.01)  # 10ms
                continue
            
            # 4. Exécuter la tâche
            try:
                self._execute_task(task, worker_id)
                
                # BUG FIX: Protéger l'incrément avec le lock global
                with self._global_lock:
                    self._total_tasks_completed += 1
                    self._record_metrics("task_completed")
            except Exception as e:
                # Erreur d'exécution: log et continuer
                self._handle_task_error(task, e, worker_id)
    
    def _steal_task(self, worker_id: int) -> Optional[Task]:
        """
        Tente de voler une tâche depuis un autre worker
        
        Args:
            worker_id: Worker qui tente de voler
            
        Returns:
            Task volée ou None si échec
        """
        # BUG FIX: Protéger l'incrément avec le lock global
        with self._global_lock:
            self._total_steal_attempts += 1
        
        # Stratégie de vol
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
                # BUG FIX: Protéger les incréments avec le lock global
                with self._global_lock:
                    self._total_tasks_stolen += 1
                    self._successful_steals += 1
                    self._record_metrics("steal_success")
                return stolen_task
        
        # Échec: aucune tâche volée
        with self._global_lock:
            self._failed_steals += 1
            self._record_metrics("steal_failed")
        
        return None
    
    def _get_random_targets(self, worker_id: int) -> List[int]:
        """Retourne des cibles aléatoires pour vol"""
        import random
        targets = list(range(self.num_workers))
        targets.remove(worker_id)
        random.shuffle(targets)
        return targets
    
    def _get_round_robin_targets(self, worker_id: int) -> List[int]:
        """Retourne des cibles en round-robin"""
        targets = []
        for i in range(1, self.num_workers):
            target_id = (worker_id + i) % self.num_workers
            targets.append(target_id)
        return targets
    
    def _get_least_loaded_targets(self, worker_id: int) -> List[int]:
        """Retourne des cibles triées par charge (plus chargé d'abord)"""
        # Calculer la charge de chaque queue
        loads = []
        for i in range(self.num_workers):
            if i != worker_id:
                load = self._queues[i].size()
                loads.append((load, i))
        
        # Trier par charge décroissante (voler depuis le plus chargé)
        loads.sort(reverse=True, key=lambda x: x[0])
        return [worker_id for _, worker_id in loads]
    
    def _execute_task(self, task: Task, worker_id: int):
        """
        Exécute une tâche
        
        Args:
            task: Tâche à exécuter
            worker_id: Worker qui exécute
        """
        # Mettre à jour le statut
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        
        # Chercher l'action dans le registre
        action_name = task.action_name
        if action_name not in self.action_registry:
            raise ValueError(f"Action '{action_name}' non trouvée dans le registre")
        
        action_func = self.action_registry[action_name]
        
        # Exécuter l'action
        try:
            result = action_func(**task.parameters)
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now()
            raise
    
    def _handle_task_error(self, task: Task, error: Exception, worker_id: int):
        """Gère une erreur d'exécution"""
        task.status = TaskStatus.FAILED
        task.error = str(error)
        task.completed_at = datetime.now()
        
        # Log l'erreur (conformité Loi 25)
        error_trace = traceback.format_exc()
        # TODO: Intégrer avec système de logging
        
        self._record_metrics("task_failed")
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de l'exécuteur"""
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
    
    def _record_metrics(self, event: str):
        """Enregistre les métriques Prometheus"""
        if not self.metrics or not hasattr(self.metrics, 'record_work_stealing'):
            return
        
        try:
            self.metrics.record_work_stealing(
                event=event,
                num_workers=self.num_workers,
            )
        except Exception:
            # Ignorer les erreurs de métriques (ne pas casser l'exécuteur)
            pass


# Instance globale (singleton)
_executor_instance: Optional[WorkStealingExecutor] = None
_executor_lock = threading.RLock()


def get_work_stealing_executor(
    num_workers: int = 4,
    steal_strategy: StealStrategy = StealStrategy.LEAST_LOADED,
    action_registry: Optional[Dict[str, Callable]] = None,
    enable_metrics: bool = True,
) -> WorkStealingExecutor:
    """
    Obtient ou crée l'instance globale de l'exécuteur
    
    Args:
        num_workers: Nombre de workers (ignoré si instance existe)
        steal_strategy: Stratégie de vol (ignoré si instance existe)
        action_registry: Registre d'actions (ignoré si instance existe)
        enable_metrics: Active métriques (ignoré si instance existe)
        
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


def reset_work_stealing_executor():
    """Réinitialise l'exécuteur global (utile pour tests)"""
    global _executor_instance
    
    with _executor_lock:
        if _executor_instance is not None:
            _executor_instance.shutdown()
        _executor_instance = None
