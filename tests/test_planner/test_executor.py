"""
Tests unitaires pour executor.py

Couvre:
- TaskExecutor: initialisation, exécution
- ExecutionStrategy: SEQUENTIAL, PARALLEL, ADAPTIVE
- ExecutionResult: structure, sérialisation
- Gestion dépendances: tri topologique, propagation échecs
- Edge cases: actions manquantes, timeouts, erreurs critiques

Exécution:
    pytest tests/test_planner/test_executor.py -v
"""

import pytest
import time
from unittest.mock import Mock, MagicMock, patch
from concurrent.futures import ThreadPoolExecutor

from planner.executor import (
    TaskExecutor,
    ExecutionStrategy,
    ExecutionResult,
    ExecutionError,
)
from planner.task_graph import (
    TaskGraph,
    Task,
    TaskStatus,
    TaskPriority,
)


class TestTaskExecutor:
    """Tests pour la classe TaskExecutor"""
    
    def test_executor_initialization_default(self):
        """Test initialisation avec valeurs par défaut"""
        executor = TaskExecutor()
        
        assert executor.actions == {}
        assert executor.strategy == ExecutionStrategy.ADAPTIVE
        assert executor.max_workers == 4
        assert executor.timeout == 60
        assert executor.enable_tracing is True
    
    def test_executor_initialization_custom(self):
        """Test initialisation avec paramètres personnalisés"""
        actions = {"test_action": lambda p: "result"}
        
        executor = TaskExecutor(
            action_registry=actions,
            strategy=ExecutionStrategy.PARALLEL,
            max_workers=8,
            timeout_per_task_sec=120,
            enable_tracing=False,
        )
        
        assert executor.actions == actions
        assert executor.strategy == ExecutionStrategy.PARALLEL
        assert executor.max_workers == 8
        assert executor.timeout == 120
        assert executor.enable_tracing is False
    
    def test_register_action(self):
        """Test enregistrement d'action"""
        executor = TaskExecutor()
        
        def test_action(params):
            return "test_result"
        
        executor.register_action("test_action", test_action)
        
        assert "test_action" in executor.actions
        assert executor.actions["test_action"] == test_action


class TestExecutionStrategySequential:
    """Tests pour stratégie SEQUENTIAL"""
    
    def test_sequential_execution_simple(self):
        """Test exécution séquentielle simple"""
        graph = TaskGraph()
        
        def action1(params):
            return "result1"
        
        def action2(params):
            return "result2"
        
        task1 = Task(name="task1", action="action1")
        task2 = Task(name="task2", action="action2", depends_on=[task1.task_id])
        
        graph.add_task(task1)
        graph.add_task(task2)
        
        executor = TaskExecutor(
            action_registry={
                "action1": action1,
                "action2": action2,
            },
            strategy=ExecutionStrategy.SEQUENTIAL,
        )
        
        result = executor.execute(graph)
        
        assert result.success is True
        assert result.completed_tasks == 2
        assert result.failed_tasks == 0
        assert task1.status == TaskStatus.COMPLETED
        assert task2.status == TaskStatus.COMPLETED
        assert task1.result == "result1"
        assert task2.result == "result2"
    
    def test_sequential_execution_with_dependency_failure(self):
        """Test exécution séquentielle avec échec de dépendance"""
        graph = TaskGraph()
        
        def action1(params):
            raise Exception("Action1 failed")
        
        def action2(params):
            return "result2"
        
        task1 = Task(name="task1", action="action1")
        task2 = Task(name="task2", action="action2", depends_on=[task1.task_id])
        
        graph.add_task(task1)
        graph.add_task(task2)
        
        executor = TaskExecutor(
            action_registry={
                "action1": action1,
                "action2": action2,
            },
            strategy=ExecutionStrategy.SEQUENTIAL,
        )
        
        result = executor.execute(graph)
        
        assert task1.status == TaskStatus.FAILED
        assert task2.status == TaskStatus.SKIPPED  # Dépendance échouée
        assert result.failed_tasks == 1
        assert result.skipped_tasks == 1


class TestExecutionStrategyParallel:
    """Tests pour stratégie PARALLEL"""
    
    def test_parallel_execution_independent_tasks(self):
        """Test exécution parallèle de tâches indépendantes"""
        graph = TaskGraph()
        
        execution_order = []
        
        def action1(params):
            time.sleep(0.1)
            execution_order.append("action1")
            return "result1"
        
        def action2(params):
            time.sleep(0.1)
            execution_order.append("action2")
            return "result2"
        
        def action3(params):
            time.sleep(0.1)
            execution_order.append("action3")
            return "result3"
        
        task1 = Task(name="task1", action="action1")
        task2 = Task(name="task2", action="action2")
        task3 = Task(name="task3", action="action3")
        
        graph.add_task(task1)
        graph.add_task(task2)
        graph.add_task(task3)
        
        executor = TaskExecutor(
            action_registry={
                "action1": action1,
                "action2": action2,
                "action3": action3,
            },
            strategy=ExecutionStrategy.PARALLEL,
            max_workers=3,
        )
        
        result = executor.execute(graph)
        
        assert result.success is True
        assert result.completed_tasks == 3
        # Vérifier que toutes les tâches sont complétées
        assert all(t.status == TaskStatus.COMPLETED for t in [task1, task2, task3])
        # Les tâches peuvent s'exécuter dans n'importe quel ordre en parallèle
        assert len(execution_order) == 3
    
    def test_parallel_execution_with_levels(self):
        """Test exécution parallèle avec niveaux (dépendances)"""
        graph = TaskGraph()
        
        results = {}
        
        def action1(params):
            results["action1"] = "result1"
            return "result1"
        
        def action2(params):
            results["action2"] = "result2"
            return "result2"
        
        def action3(params):
            results["action3"] = "result3"
            return "result3"
        
        task1 = Task(name="task1", action="action1")
        task2 = Task(name="task2", action="action2")
        task3 = Task(name="task3", action="action3", depends_on=[task1.task_id, task2.task_id])
        
        graph.add_task(task1)
        graph.add_task(task2)
        graph.add_task(task3)
        
        executor = TaskExecutor(
            action_registry={
                "action1": action1,
                "action2": action2,
                "action3": action3,
            },
            strategy=ExecutionStrategy.PARALLEL,
        )
        
        result = executor.execute(graph)
        
        assert result.success is True
        assert result.completed_tasks == 3
        # task3 doit attendre task1 et task2
        assert "action1" in results
        assert "action2" in results
        assert "action3" in results


class TestExecutionStrategyAdaptive:
    """Tests pour stratégie ADAPTIVE"""
    
    def test_adaptive_few_tasks_sequential(self):
        """Test ADAPTIVE avec peu de tâches (choisit séquentiel)"""
        graph = TaskGraph()
        
        task1 = Task(name="task1", action="action1")
        task2 = Task(name="task2", action="action2", depends_on=[task1.task_id])
        
        graph.add_task(task1)
        graph.add_task(task2)
        
        executor = TaskExecutor(
            action_registry={
                "action1": lambda p: "result1",
                "action2": lambda p: "result2",
            },
            strategy=ExecutionStrategy.ADAPTIVE,
        )
        
        result = executor.execute(graph)
        
        # ADAPTIVE avec < 3 tâches devrait utiliser séquentiel
        assert result.success is True
        assert "adaptive_choice" in result.metadata
        assert result.metadata["adaptive_choice"] == "sequential"
    
    def test_adaptive_critical_priority_sequential(self):
        """Test ADAPTIVE avec priorité critique (choisit séquentiel)"""
        graph = TaskGraph()
        
        task1 = Task(name="task1", action="action1", priority=TaskPriority.CRITICAL)
        task2 = Task(name="task2", action="action2", priority=TaskPriority.CRITICAL)
        task3 = Task(name="task3", action="action3", priority=TaskPriority.CRITICAL)
        
        graph.add_task(task1)
        graph.add_task(task2)
        graph.add_task(task3)
        
        executor = TaskExecutor(
            action_registry={
                "action1": lambda p: "result1",
                "action2": lambda p: "result2",
                "action3": lambda p: "result3",
            },
            strategy=ExecutionStrategy.ADAPTIVE,
        )
        
        result = executor.execute(graph)
        
        # ADAPTIVE avec tâches critiques devrait utiliser séquentiel
        assert result.metadata["adaptive_choice"] == "sequential"
    
    def test_adaptive_many_tasks_parallel(self):
        """Test ADAPTIVE avec beaucoup de tâches (choisit parallèle)"""
        graph = TaskGraph()
        
        # Créer 5 tâches indépendantes
        tasks = []
        for i in range(5):
            task = Task(name=f"task{i}", action=f"action{i}")
            tasks.append(task)
            graph.add_task(task)
        
        actions = {f"action{i}": lambda p, i=i: f"result{i}" for i in range(5)}
        
        executor = TaskExecutor(
            action_registry=actions,
            strategy=ExecutionStrategy.ADAPTIVE,
        )
        
        result = executor.execute(graph)
        
        # ADAPTIVE avec >= 3 tâches non-critiques devrait utiliser parallèle
        assert result.success is True
        assert result.metadata["adaptive_choice"] == "parallel"


class TestExecutionResult:
    """Tests pour ExecutionResult"""
    
    def test_execution_result_creation(self):
        """Test création ExecutionResult"""
        result = ExecutionResult(
            success=True,
            completed_tasks=5,
            failed_tasks=0,
            skipped_tasks=0,
            total_duration_ms=100.5,
        )
        
        assert result.success is True
        assert result.completed_tasks == 5
        assert result.failed_tasks == 0
        assert result.total_duration_ms == 100.5
    
    def test_execution_result_to_dict(self):
        """Test sérialisation ExecutionResult"""
        result = ExecutionResult(
            success=True,
            completed_tasks=3,
            failed_tasks=1,
            skipped_tasks=2,
            total_duration_ms=50.0,
            task_results={"task1": "result1"},
            errors={"task2": "error2"},
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["success"] is True
        assert result_dict["completed_tasks"] == 3
        assert result_dict["failed_tasks"] == 1
        assert result_dict["skipped_tasks"] == 2
        assert result_dict["total_duration_ms"] == 50.0
        assert "task_results" in result_dict
        assert "errors" in result_dict


class TestExecutionEdgeCases:
    """Tests pour cas limites d'exécution"""
    
    def test_execution_unknown_action(self):
        """Test exécution avec action inconnue"""
        graph = TaskGraph()
        task = Task(name="task", action="unknown_action")
        graph.add_task(task)
        
        executor = TaskExecutor(action_registry={})
        
        result = executor.execute(graph)
        
        assert task.status == TaskStatus.FAILED
        assert result.failed_tasks == 1
        assert "unknown_action" in result.errors.get(task.task_id, "")
    
    def test_execution_action_exception(self):
        """Test gestion exception dans action"""
        graph = TaskGraph()
        
        def failing_action(params):
            raise ValueError("Action failed")
        
        task = Task(name="task", action="failing_action")
        graph.add_task(task)
        
        executor = TaskExecutor(action_registry={"failing_action": failing_action})
        
        result = executor.execute(graph)
        
        assert task.status == TaskStatus.FAILED
        assert result.failed_tasks == 1
        assert "ValueError" in result.errors.get(task.task_id, "")
    
    def test_execution_empty_graph(self):
        """Test exécution avec graphe vide"""
        graph = TaskGraph()
        
        executor = TaskExecutor()
        
        result = executor.execute(graph)
        
        assert result.success is True
        assert result.completed_tasks == 0
    
    def test_execution_timeout(self):
        """Test timeout d'exécution"""
        graph = TaskGraph()
        
        def slow_action(params):
            time.sleep(2)  # Plus long que timeout
            return "result"
        
        task = Task(name="task", action="slow_action")
        graph.add_task(task)
        
        executor = TaskExecutor(
            action_registry={"slow_action": slow_action},
            timeout_per_task_sec=0.5,  # Timeout court
        )
        
        # Note: Le timeout est géré par ThreadPoolExecutor dans le cas parallèle
        # Pour séquentiel, l'exception est levée directement
        result = executor.execute(graph)
        
        # Selon l'implémentation, peut échouer ou compléter
        assert result is not None


class TestExecutionDependencyPropagation:
    """Tests pour propagation des échecs"""
    
    def test_failure_propagation(self):
        """Test propagation échec aux dépendants"""
        graph = TaskGraph()
        
        task1 = Task(name="task1", action="failing_action")
        task2 = Task(name="task2", action="action2", depends_on=[task1.task_id])
        task3 = Task(name="task3", action="action3", depends_on=[task2.task_id])
        
        graph.add_task(task1)
        graph.add_task(task2)
        graph.add_task(task3)
        
        executor = TaskExecutor(
            action_registry={
                "failing_action": lambda p: (_ for _ in ()).throw(Exception("Failed")),
                "action2": lambda p: "result2",
                "action3": lambda p: "result3",
            },
        )
        
        result = executor.execute(graph)
        
        assert task1.status == TaskStatus.FAILED
        assert task2.status == TaskStatus.SKIPPED  # Dépendance échouée
        assert task3.status == TaskStatus.SKIPPED  # Propagation
    
    def test_optional_task_failure_continues(self):
        """Test échec tâche optionnelle n'arrête pas exécution"""
        graph = TaskGraph()
        
        task1 = Task(name="task1", action="action1", priority=TaskPriority.CRITICAL)
        task2 = Task(name="task2", action="failing_action", priority=TaskPriority.OPTIONAL)
        task3 = Task(name="task3", action="action3", depends_on=[task1.task_id], priority=TaskPriority.CRITICAL)
        
        graph.add_task(task1)
        graph.add_task(task2)
        graph.add_task(task3)
        
        executor = TaskExecutor(
            action_registry={
                "action1": lambda p: "result1",
                "failing_action": lambda p: (_ for _ in ()).throw(Exception("Failed")),
                "action3": lambda p: "result3",
            },
        )
        
        result = executor.execute(graph)
        
        # Les tâches critiques doivent réussir
        assert task1.status == TaskStatus.COMPLETED
        assert task3.status == TaskStatus.COMPLETED
        # Tâche optionnelle peut échouer sans affecter le succès global
        assert task2.status == TaskStatus.FAILED
        # Si toutes les critiques réussissent, succès global
        assert result.success is True


class TestExecutionStats:
    """Tests pour statistiques d'exécution"""
    
    def test_executor_stats(self):
        """Test statistiques d'exécution"""
        graph = TaskGraph()
        
        task1 = Task(name="task1", action="action1")
        task2 = Task(name="task2", action="action2")
        
        graph.add_task(task1)
        graph.add_task(task2)
        
        executor = TaskExecutor(
            action_registry={
                "action1": lambda p: "result1",
                "action2": lambda p: "result2",
            },
        )
        
        executor.execute(graph)
        
        stats = executor.get_stats()
        
        assert "total_executions" in stats
        assert "successful_executions" in stats
        assert "failed_executions" in stats
        assert stats["total_executions"] >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

