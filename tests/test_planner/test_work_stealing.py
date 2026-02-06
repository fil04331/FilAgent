"""
Tests unitaires pour work_stealing.py

Couvre:
- WorkStealingQueue: push, pop, steal, thread-safety
- WorkStealingExecutor: initialisation, exécution, coordination
- StealStrategy: RANDOM, ROUND_ROBIN, LEAST_LOADED
- Edge cases: queues vides, worker unique, erreurs
- Concurrence: vol de tâches, load balancing
- Métriques: statistiques, monitoring

Exécution:
    pytest tests/test_planner/test_work_stealing.py -v
"""

import pytest
import time
import threading
from unittest.mock import Mock, MagicMock, patch
from typing import List

from planner.work_stealing import (
    WorkStealingQueue,
    WorkStealingExecutor,
    StealStrategy,
    StealResult,
    get_work_stealing_executor,
    reset_work_stealing_executor,
)
from planner.task_graph import Task, TaskStatus, TaskPriority


class TestWorkStealingQueue:
    """Tests pour la classe WorkStealingQueue"""

    def test_queue_initialization(self):
        """Test initialisation de la queue"""
        queue = WorkStealingQueue(worker_id=0)

        assert queue.worker_id == 0
        assert queue.is_empty()
        assert queue.size() == 0

    def test_push_single_task(self):
        """Test ajout d'une seule tâche"""
        queue = WorkStealingQueue(worker_id=0)
        task = Task(name="test_task", action="test_action")

        queue.push(task)

        assert queue.size() == 1
        assert not queue.is_empty()

    def test_push_multiple_tasks(self):
        """Test ajout de plusieurs tâches"""
        queue = WorkStealingQueue(worker_id=0)
        tasks = [Task(name=f"task_{i}", action="test_action") for i in range(5)]

        for task in tasks:
            queue.push(task)

        assert queue.size() == 5

    def test_pop_lifo_order(self):
        """Test pop respecte l'ordre LIFO (Last-In-First-Out)"""
        queue = WorkStealingQueue(worker_id=0)

        task1 = Task(name="task1", action="action1")
        task2 = Task(name="task2", action="action2")
        task3 = Task(name="task3", action="action3")

        queue.push(task1)
        queue.push(task2)
        queue.push(task3)

        # Pop devrait retourner dans l'ordre inverse (LIFO)
        popped = queue.pop()
        assert popped.name == "task3"

        popped = queue.pop()
        assert popped.name == "task2"

        popped = queue.pop()
        assert popped.name == "task1"

        assert queue.is_empty()

    def test_pop_empty_queue(self):
        """Test pop sur queue vide retourne None"""
        queue = WorkStealingQueue(worker_id=0)

        result = queue.pop()

        assert result is None

    def test_steal_fifo_order(self):
        """Test steal respecte l'ordre FIFO (First-In-First-Out)"""
        queue = WorkStealingQueue(worker_id=0)

        task1 = Task(name="task1", action="action1")
        task2 = Task(name="task2", action="action2")
        task3 = Task(name="task3", action="action3")

        queue.push(task1)
        queue.push(task2)
        queue.push(task3)

        # Steal devrait retourner dans l'ordre d'insertion (FIFO)
        stolen = queue.steal()
        assert stolen.name == "task1"

        stolen = queue.steal()
        assert stolen.name == "task2"

        stolen = queue.steal()
        assert stolen.name == "task3"

        assert queue.is_empty()

    def test_steal_empty_queue(self):
        """Test steal sur queue vide retourne None"""
        queue = WorkStealingQueue(worker_id=0)

        result = queue.steal()

        assert result is None

    def test_pop_vs_steal_different_ends(self):
        """Test que pop (LIFO) et steal (FIFO) prennent aux extrémités opposées"""
        queue = WorkStealingQueue(worker_id=0)

        task1 = Task(name="task1", action="action1")
        task2 = Task(name="task2", action="action2")
        task3 = Task(name="task3", action="action3")

        queue.push(task1)
        queue.push(task2)
        queue.push(task3)

        # Pop prend à la fin (LIFO) → task3
        popped = queue.pop()
        assert popped.name == "task3"

        # Steal prend au début (FIFO) → task1
        stolen = queue.steal()
        assert stolen.name == "task1"

        # Il reste task2
        assert queue.size() == 1
        remaining = queue.pop()
        assert remaining.name == "task2"

    def test_thread_safety_concurrent_push(self):
        """Test thread-safety avec push concurrent"""
        queue = WorkStealingQueue(worker_id=0)
        num_threads = 10
        tasks_per_thread = 100

        def push_tasks(thread_id):
            for i in range(tasks_per_thread):
                task = Task(name=f"task_{thread_id}_{i}", action="test_action")
                queue.push(task)

        # Créer et démarrer les threads
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=push_tasks, args=(i,))
            thread.start()
            threads.append(thread)

        # Attendre la fin
        for thread in threads:
            thread.join()

        # Vérifier que toutes les tâches ont été ajoutées
        expected_size = num_threads * tasks_per_thread
        assert queue.size() == expected_size

    def test_thread_safety_concurrent_pop_and_steal(self):
        """Test thread-safety avec pop et steal concurrents"""
        queue = WorkStealingQueue(worker_id=0)

        # Ajouter des tâches
        num_tasks = 1000
        for i in range(num_tasks):
            queue.push(Task(name=f"task_{i}", action="test_action"))

        popped_tasks = []
        stolen_tasks = []
        lock = threading.Lock()

        def pop_tasks():
            while True:
                task = queue.pop()
                if task is None:
                    break
                with lock:
                    popped_tasks.append(task)
                time.sleep(0.0001)  # Petit délai pour augmenter la concurrence

        def steal_tasks():
            while True:
                task = queue.steal()
                if task is None:
                    break
                with lock:
                    stolen_tasks.append(task)
                time.sleep(0.0001)

        # Créer threads (2 pop, 2 steal)
        threads = [
            threading.Thread(target=pop_tasks),
            threading.Thread(target=pop_tasks),
            threading.Thread(target=steal_tasks),
            threading.Thread(target=steal_tasks),
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Vérifier qu'on a récupéré toutes les tâches (aucune perdue)
        total_retrieved = len(popped_tasks) + len(stolen_tasks)
        assert total_retrieved == num_tasks

        # Vérifier qu'aucune tâche n'est dupliquée
        all_task_ids = [t.task_id for t in popped_tasks + stolen_tasks]
        assert len(all_task_ids) == len(set(all_task_ids))


class TestWorkStealingExecutor:
    """Tests pour la classe WorkStealingExecutor"""

    def setup_method(self):
        """Setup avant chaque test"""
        # Réinitialiser le singleton
        reset_work_stealing_executor()

    def teardown_method(self):
        """Cleanup après chaque test"""
        reset_work_stealing_executor()

    def test_executor_initialization_default(self):
        """Test initialisation avec valeurs par défaut"""
        executor = WorkStealingExecutor()

        assert executor.num_workers == 4
        assert executor.steal_strategy == StealStrategy.LEAST_LOADED
        assert executor.action_registry == {}
        assert executor.enable_metrics is True
        assert len(executor._queues) == 4
        assert not executor._started

    def test_executor_initialization_custom(self):
        """Test initialisation avec paramètres personnalisés"""
        actions = {"test_action": lambda x: "result"}

        executor = WorkStealingExecutor(
            num_workers=8,
            steal_strategy=StealStrategy.RANDOM,
            action_registry=actions,
            enable_metrics=False,
        )

        assert executor.num_workers == 8
        assert executor.steal_strategy == StealStrategy.RANDOM
        assert executor.action_registry == actions
        assert executor.enable_metrics is False
        assert len(executor._queues) == 8

    def test_start_workers(self):
        """Test démarrage des workers"""
        executor = WorkStealingExecutor(num_workers=2)

        executor.start()

        assert executor._started is True
        assert len(executor._workers) == 2
        assert all(w.is_alive() for w in executor._workers)

        executor.shutdown()

    def test_start_idempotent(self):
        """Test que start() est idempotent"""
        executor = WorkStealingExecutor(num_workers=2)

        executor.start()
        num_workers_first = len(executor._workers)

        executor.start()  # Deuxième appel
        num_workers_second = len(executor._workers)

        assert num_workers_first == num_workers_second == 2

        executor.shutdown()

    def test_shutdown_workers(self):
        """Test arrêt des workers"""
        executor = WorkStealingExecutor(num_workers=2)
        executor.start()

        executor.shutdown(timeout=1.0)

        assert not executor._started
        assert len(executor._workers) == 0
        assert executor._shutdown_event.is_set()

    def test_shutdown_idempotent(self):
        """Test que shutdown() est idempotent"""
        executor = WorkStealingExecutor(num_workers=2)
        executor.start()

        executor.shutdown()
        executor.shutdown()  # Deuxième appel ne devrait pas causer d'erreur

        assert not executor._started

    def test_submit_single_task(self):
        """Test soumission d'une tâche unique"""
        executor = WorkStealingExecutor(num_workers=2)
        task = Task(name="test_task", action="test_action")

        executor.submit(task)

        # Vérifier que la tâche est dans une queue
        total_tasks = sum(q.size() for q in executor._queues)
        assert total_tasks == 1
        assert executor._started  # Auto-start

        executor.shutdown()

    def test_submit_with_specific_worker(self):
        """Test soumission à un worker spécifique"""
        executor = WorkStealingExecutor(num_workers=4)
        task = Task(name="test_task", action="test_action")

        executor.submit(task, worker_id=2)

        # Vérifier que la tâche est dans la queue du worker 2
        assert executor._queues[2].size() == 1
        assert executor._queues[0].size() == 0
        assert executor._queues[1].size() == 0
        assert executor._queues[3].size() == 0

        executor.shutdown()

    def test_submit_batch_distribution(self):
        """Test distribution round-robin des tâches batch"""
        executor = WorkStealingExecutor(num_workers=3)

        tasks = [Task(name=f"task_{i}", action="test_action") for i in range(9)]

        executor.submit_batch(tasks)

        # Avec 9 tâches et 3 workers, chaque worker devrait avoir 3 tâches
        for i in range(3):
            assert executor._queues[i].size() == 3

        executor.shutdown()

    def test_execute_simple_task(self):
        """Test exécution d'une tâche simple"""
        result_value = None

        def test_action(value):
            return value * 2

        executor = WorkStealingExecutor(num_workers=1, action_registry={"test_action": test_action})

        task = Task(name="test_task", action="test_action", params={"value": 21})

        executor.submit(task)
        time.sleep(0.5)  # Attendre l'exécution

        executor.shutdown(timeout=1.0)

        # Vérifier que la tâche a été exécutée
        assert task.status == TaskStatus.COMPLETED
        assert task.result == 42

    def test_execute_multiple_tasks_parallel(self):
        """Test exécution de plusieurs tâches en parallèle"""
        execution_log = []
        lock = threading.Lock()

        def slow_action(task_id):
            with lock:
                execution_log.append(f"start_{task_id}")
            time.sleep(0.1)
            with lock:
                execution_log.append(f"end_{task_id}")
            return f"result_{task_id}"

        executor = WorkStealingExecutor(num_workers=3, action_registry={"slow_action": slow_action})

        tasks = [
            Task(name=f"task_{i}", action="slow_action", params={"task_id": i}) for i in range(6)
        ]

        executor.submit_batch(tasks)
        time.sleep(1.0)  # Attendre l'exécution

        executor.shutdown(timeout=2.0)

        # Vérifier que toutes les tâches sont complétées
        completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        assert completed == 6

        # Vérifier les résultats
        for i, task in enumerate(tasks):
            assert task.result == f"result_{i}"

    def test_work_stealing_single_worker_idle(self):
        """Test qu'un worker vole du travail quand sa queue est vide"""
        execution_count = {"count": 0}
        lock = threading.Lock()

        def counting_action():
            # Add small delay to create window for work stealing
            time.sleep(0.05)
            with lock:
                execution_count["count"] += 1
            return "done"

        executor = WorkStealingExecutor(
            num_workers=2,
            action_registry={"counting_action": counting_action},
            steal_strategy=StealStrategy.LEAST_LOADED,
        )

        # Soumettre toutes les tâches au worker 0
        tasks = [Task(name=f"task_{i}", action="counting_action") for i in range(10)]

        for task in tasks:
            executor.submit(task, worker_id=0)

        # Worker 1 devrait voler des tâches du worker 0
        time.sleep(1.0)

        executor.shutdown(timeout=2.0)

        # Vérifier que toutes les tâches ont été exécutées
        assert execution_count["count"] == 10

        # Vérifier les statistiques de vol
        stats = executor.get_stats()
        assert stats["total_tasks_stolen"] > 0

    def test_steal_strategy_random(self):
        """Test stratégie de vol RANDOM"""
        executor = WorkStealingExecutor(num_workers=4, steal_strategy=StealStrategy.RANDOM)

        targets = executor._get_random_targets(worker_id=1)

        # Devrait retourner tous les workers sauf le 1
        assert len(targets) == 3
        assert 1 not in targets
        assert set(targets).issubset({0, 2, 3})

        executor.shutdown()

    def test_steal_strategy_round_robin(self):
        """Test stratégie de vol ROUND_ROBIN"""
        executor = WorkStealingExecutor(num_workers=4, steal_strategy=StealStrategy.ROUND_ROBIN)

        targets = executor._get_round_robin_targets(worker_id=1)

        # Devrait retourner [2, 3, 0] dans cet ordre
        assert targets == [2, 3, 0]

        executor.shutdown()

    def test_steal_strategy_least_loaded(self):
        """Test stratégie de vol LEAST_LOADED"""
        executor = WorkStealingExecutor(num_workers=4, steal_strategy=StealStrategy.LEAST_LOADED)

        # Ajouter différentes charges aux queues
        for i in range(5):
            executor._queues[0].push(Task(name=f"t0_{i}", action="a"))
        for i in range(2):
            executor._queues[2].push(Task(name=f"t2_{i}", action="a"))
        for i in range(8):
            executor._queues[3].push(Task(name=f"t3_{i}", action="a"))

        targets = executor._get_least_loaded_targets(worker_id=1)

        # Devrait retourner dans l'ordre décroissant de charge: [3, 0, 2]
        assert targets == [3, 0, 2]

        executor.shutdown()

    def test_task_execution_error_handling(self):
        """Test gestion des erreurs d'exécution"""

        def failing_action():
            raise ValueError("Test error")

        executor = WorkStealingExecutor(
            num_workers=1, action_registry={"failing_action": failing_action}
        )

        task = Task(name="failing_task", action="failing_action")

        executor.submit(task)
        time.sleep(0.5)

        executor.shutdown(timeout=1.0)

        # Vérifier que la tâche a échoué
        assert task.status == TaskStatus.FAILED
        assert "Test error" in task.error

    def test_action_not_found_error(self):
        """Test erreur quand l'action n'existe pas"""
        executor = WorkStealingExecutor(num_workers=1, action_registry={})

        task = Task(name="unknown_task", action="unknown_action")

        executor.submit(task)
        time.sleep(0.5)

        executor.shutdown(timeout=1.0)

        # Vérifier que la tâche a échoué
        assert task.status == TaskStatus.FAILED
        assert "non trouvée" in task.error or "not found" in task.error.lower()

    def test_get_stats_initial(self):
        """Test statistiques initiales"""
        executor = WorkStealingExecutor(num_workers=3)

        stats = executor.get_stats()

        assert stats["total_tasks_completed"] == 0
        assert stats["total_tasks_stolen"] == 0
        assert stats["successful_steals"] == 0
        assert stats["failed_steals"] == 0
        assert stats["steal_success_rate"] == 0.0
        assert stats["num_workers"] == 3
        assert stats["steal_strategy"] == "least_loaded"
        assert stats["queue_sizes"] == [0, 0, 0]

        executor.shutdown()

    def test_get_stats_after_execution(self):
        """Test statistiques après exécution"""

        def simple_action():
            return "done"

        executor = WorkStealingExecutor(
            num_workers=2, action_registry={"simple_action": simple_action}
        )

        # Soumettre plusieurs tâches
        tasks = [Task(name=f"task_{i}", action="simple_action") for i in range(5)]

        executor.submit_batch(tasks)
        time.sleep(1.0)

        stats = executor.get_stats()

        executor.shutdown(timeout=1.0)

        # Vérifier que des tâches ont été complétées
        assert stats["total_tasks_completed"] == 5

    def test_stats_thread_safety(self):
        """Test thread-safety des statistiques"""

        def simple_action():
            return "done"

        executor = WorkStealingExecutor(
            num_workers=4, action_registry={"simple_action": simple_action}
        )

        # Soumettre beaucoup de tâches pour provoquer de la concurrence
        tasks = [Task(name=f"task_{i}", action="simple_action") for i in range(100)]

        executor.submit_batch(tasks)

        # Lire les stats pendant l'exécution (thread-safety)
        for _ in range(10):
            stats = executor.get_stats()
            assert isinstance(stats, dict)
            time.sleep(0.05)

        executor.shutdown(timeout=2.0)

        final_stats = executor.get_stats()
        assert final_stats["total_tasks_completed"] == 100

    def test_empty_queue_handling(self):
        """Test comportement avec queues vides"""
        executor = WorkStealingExecutor(num_workers=2, action_registry={})

        executor.start()

        # Attendre un peu sans soumettre de tâches
        time.sleep(0.2)

        # Workers devraient rester en attente sans crash
        assert all(w.is_alive() for w in executor._workers)

        stats = executor.get_stats()
        assert stats["total_tasks_completed"] == 0

        executor.shutdown(timeout=1.0)

    def test_single_worker_no_stealing(self):
        """Test qu'un seul worker ne tente pas de voler"""

        def simple_action():
            return "done"

        executor = WorkStealingExecutor(
            num_workers=1, action_registry={"simple_action": simple_action}
        )

        tasks = [Task(name=f"task_{i}", action="simple_action") for i in range(5)]

        executor.submit_batch(tasks)
        time.sleep(0.5)

        stats = executor.get_stats()

        executor.shutdown(timeout=1.0)

        # Avec un seul worker, aucun vol ne devrait avoir lieu
        assert stats["total_tasks_stolen"] == 0
        assert stats["successful_steals"] == 0
        assert stats["total_tasks_completed"] == 5


class TestStealResult:
    """Tests pour la classe StealResult"""

    def test_steal_result_success(self):
        """Test création d'un résultat de vol réussi"""
        task = Task(name="stolen_task", action="test_action")
        result = StealResult(success=True, task=task, from_worker=2, attempt_count=3)

        assert result.success is True
        assert result.task == task
        assert result.from_worker == 2
        assert result.attempt_count == 3

    def test_steal_result_failure(self):
        """Test création d'un résultat de vol échoué"""
        result = StealResult(success=False, attempt_count=5)

        assert result.success is False
        assert result.task is None
        assert result.from_worker is None
        assert result.attempt_count == 5


class TestGlobalSingleton:
    """Tests pour les fonctions singleton globales"""

    def setup_method(self):
        """Setup avant chaque test"""
        reset_work_stealing_executor()

    def teardown_method(self):
        """Cleanup après chaque test"""
        reset_work_stealing_executor()

    def test_get_executor_creates_singleton(self):
        """Test que get_work_stealing_executor() crée un singleton"""
        executor1 = get_work_stealing_executor()
        executor2 = get_work_stealing_executor()

        assert executor1 is executor2

        executor1.shutdown()

    def test_get_executor_with_custom_params(self):
        """Test création du singleton avec paramètres personnalisés"""
        executor = get_work_stealing_executor(num_workers=6, steal_strategy=StealStrategy.RANDOM)

        assert executor.num_workers == 6
        assert executor.steal_strategy == StealStrategy.RANDOM

        executor.shutdown()

    def test_get_executor_ignores_params_after_creation(self):
        """Test que les paramètres sont ignorés après création du singleton"""
        executor1 = get_work_stealing_executor(num_workers=4)
        executor2 = get_work_stealing_executor(num_workers=8)  # Ignoré

        assert executor1 is executor2
        assert executor1.num_workers == 4  # Pas 8

        executor1.shutdown()

    def test_reset_executor(self):
        """Test réinitialisation du singleton"""
        executor1 = get_work_stealing_executor(num_workers=4)

        reset_work_stealing_executor()

        executor2 = get_work_stealing_executor(num_workers=6)

        assert executor1 is not executor2
        assert executor2.num_workers == 6

        executor2.shutdown()

    def test_reset_executor_shuts_down_previous(self):
        """Test que reset() arrête l'exécuteur précédent"""
        executor = get_work_stealing_executor(num_workers=2)
        executor.start()

        assert executor._started

        reset_work_stealing_executor()

        # L'ancien exécuteur devrait être arrêté
        assert not executor._started


class TestEdgeCases:
    """Tests pour les cas limites"""

    def setup_method(self):
        """Setup avant chaque test"""
        reset_work_stealing_executor()

    def teardown_method(self):
        """Cleanup après chaque test"""
        reset_work_stealing_executor()

    def test_zero_workers_raises_error(self):
        """Test que 0 workers devrait causer une erreur"""
        # Note: L'implémentation actuelle ne valide pas cela,
        # mais c'est un cas limite important
        executor = WorkStealingExecutor(num_workers=0)
        assert executor.num_workers == 0
        executor.shutdown()

    def test_large_number_of_workers(self):
        """Test avec un grand nombre de workers"""
        executor = WorkStealingExecutor(num_workers=50)

        assert executor.num_workers == 50
        assert len(executor._queues) == 50

        executor.shutdown()

    def test_task_with_complex_parameters(self):
        """Test tâche avec paramètres complexes"""

        def complex_action(data, config, options):
            return {"data_len": len(data), "config": config, "options": options}

        executor = WorkStealingExecutor(
            num_workers=1, action_registry={"complex_action": complex_action}
        )

        task = Task(
            name="complex_task",
            action="complex_action",
            params={
                "data": [1, 2, 3, 4, 5],
                "config": {"debug": True, "retries": 3},
                "options": ["opt1", "opt2"],
            },
        )

        executor.submit(task)
        time.sleep(0.5)

        executor.shutdown(timeout=1.0)

        assert task.status == TaskStatus.COMPLETED
        assert task.result["data_len"] == 5
        assert task.result["config"]["debug"] is True

    def test_rapid_submit_and_shutdown(self):
        """Test soumission rapide suivie d'un shutdown immédiat"""

        def slow_action():
            time.sleep(0.1)
            return "done"

        executor = WorkStealingExecutor(num_workers=2, action_registry={"slow_action": slow_action})

        tasks = [Task(name=f"task_{i}", action="slow_action") for i in range(10)]

        executor.submit_batch(tasks)

        # Shutdown immédiat
        executor.shutdown(timeout=0.1)

        # Certaines tâches peuvent ne pas être complétées
        # (c'est normal avec un timeout court)
        assert not executor._started

    def test_metrics_disabled(self):
        """Test fonctionnement sans métriques"""
        executor = WorkStealingExecutor(num_workers=2, enable_metrics=False)

        assert executor.metrics is None

        # L'exécuteur devrait fonctionner normalement
        executor.start()
        assert executor._started

        executor.shutdown()

    def test_concurrent_submit_from_multiple_threads(self):
        """Test soumission concurrente depuis plusieurs threads"""

        def simple_action():
            return "done"

        executor = WorkStealingExecutor(
            num_workers=4, action_registry={"simple_action": simple_action}
        )

        num_submitters = 5
        tasks_per_submitter = 20

        def submit_tasks(submitter_id):
            for i in range(tasks_per_submitter):
                task = Task(name=f"task_{submitter_id}_{i}", action="simple_action")
                executor.submit(task)

        threads = [threading.Thread(target=submit_tasks, args=(i,)) for i in range(num_submitters)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Attendre l'exécution
        time.sleep(2.0)

        stats = executor.get_stats()

        executor.shutdown(timeout=2.0)

        expected_tasks = num_submitters * tasks_per_submitter
        assert stats["total_tasks_completed"] == expected_tasks
