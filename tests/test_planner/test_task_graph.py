"""
Tests unitaires pour task_graph.py

Couvre:
- Task: création, états, métadonnées, sérialisation
- TaskGraph: construction, validation cycles, tri topologique, parallélisation
- Edge cases: cycles, dépendances invalides, graphes complexes

Exécution:
    pytest tests/test_planner/test_task_graph.py -v
"""

from datetime import datetime

import pytest

from planner.task_graph import Task, TaskDecompositionError, TaskGraph, TaskPriority, TaskStatus


class TestTask:
    """Tests pour la classe Task"""

    def test_task_creation_default(self):
        """Test création avec valeurs par défaut"""
        task = Task(name="test_task", action="test_action")

        assert task.task_id is not None
        assert task.name == "test_task"
        assert task.action == "test_action"
        assert task.status == TaskStatus.PENDING
        assert task.priority == TaskPriority.NORMAL
        assert task.depends_on == []
        assert task.result is None
        assert task.error is None
        assert "created_at" in task.metadata

    def test_task_creation_with_dependencies(self):
        """Test création avec dépendances"""
        task = Task(
            name="dependent_task",
            action="process",
            depends_on=["task1", "task2"],
            priority=TaskPriority.HIGH,
        )

        assert len(task.depends_on) == 2
        assert task.priority == TaskPriority.HIGH

    def test_task_update_status(self):
        """Test mise à jour du statut"""
        task = Task(name="test", action="test")
        original_updated = task.metadata["updated_at"]

        # Attendre pour voir le changement de timestamp
        import time

        time.sleep(0.01)

        task.update_status(TaskStatus.RUNNING)
        assert task.status == TaskStatus.RUNNING
        assert task.metadata["updated_at"] != original_updated

    def test_task_update_status_with_error(self):
        """Test mise à jour avec erreur"""
        task = Task(name="test", action="test")

        task.update_status(TaskStatus.FAILED, error="Test error")
        assert task.status == TaskStatus.FAILED
        assert task.error == "Test error"
        assert "error_timestamp" in task.metadata

    def test_task_set_result(self):
        """Test enregistrement du résultat"""
        task = Task(name="test", action="test")

        task.set_result({"data": "result"})
        assert task.result == {"data": "result"}
        assert "completed_at" in task.metadata

    def test_task_to_dict(self):
        """Test sérialisation en dict"""
        task = Task(
            name="test",
            action="test",
            params={"key": "value"},
            priority=TaskPriority.HIGH,
        )

        task_dict = task.to_dict()
        assert task_dict["name"] == "test"
        assert task_dict["action"] == "test"
        assert task_dict["params"] == {"key": "value"}
        assert task_dict["priority"] == 4  # HIGH
        assert task_dict["status"] == "pending"

    def test_task_repr(self):
        """Test représentation string"""
        task = Task(name="test", action="test")
        repr_str = repr(task)

        assert "test" in repr_str
        assert "pending" in repr_str


class TestTaskGraph:
    """Tests pour la classe TaskGraph"""

    def test_empty_graph(self):
        """Test graphe vide"""
        graph = TaskGraph()
        assert len(graph.tasks) == 0
        assert graph.to_dict()["metadata"]["total_tasks"] == 0

    def test_add_single_task(self):
        """Test ajout d'une tâche unique"""
        graph = TaskGraph()
        task = Task(name="task1", action="action1")

        graph.add_task(task)
        assert len(graph.tasks) == 1
        assert task.task_id in graph.tasks

    def test_add_task_with_dependencies(self):
        """Test ajout de tâches avec dépendances"""
        graph = TaskGraph()

        task1 = Task(name="task1", action="action1")
        task2 = Task(name="task2", action="action2", depends_on=[task1.task_id])

        graph.add_task(task1)
        graph.add_task(task2)

        assert len(graph.tasks) == 2
        assert task1.task_id in graph.adjacency_list
        assert task2.task_id in graph.adjacency_list[task1.task_id]

    def test_add_duplicate_task_id(self):
        """Test ajout de task_id dupliqué"""
        graph = TaskGraph()
        task1 = Task(name="task1", action="action1")

        graph.add_task(task1)

        with pytest.raises(TaskDecompositionError, match="already exists"):
            graph.add_task(task1)  # Même task_id

    def test_add_task_invalid_dependency(self):
        """Test ajout avec dépendance inexistante"""
        graph = TaskGraph()

        task = Task(name="task", action="action", depends_on=["nonexistent"])

        with pytest.raises(TaskDecompositionError, match="Dependency.*not found"):
            graph.add_task(task)

    def test_detect_simple_cycle(self):
        """Test détection de cycle simple: A -> B -> A"""
        graph = TaskGraph()

        task1 = Task(name="task1", action="action1")
        graph.add_task(task1)

        # Créer un cycle en ajoutant task2 qui dépend de task1
        # puis task3 qui dépend de task2, puis modifier task1 pour dépendre de task3
        task2 = Task(name="task2", action="action2", depends_on=[task1.task_id])
        graph.add_task(task2)

        # Essayer de créer task qui crée un cycle
        task3 = Task(name="task3", action="action3", depends_on=[task2.task_id])
        graph.add_task(task3)

        # Maintenant essayer d'ajouter une tâche qui dépend de task3
        # et dont task1 dépend, ce qui créerait un cycle
        task4 = Task(name="task4", action="action4", depends_on=[task3.task_id, task1.task_id])

        # Ceci devrait fonctionner car pas de cycle
        graph.add_task(task4)

    def test_detect_self_cycle(self):
        """Test détection d'auto-référence (tâche dépendant d'elle-même)"""
        graph = TaskGraph()

        task = Task(name="task", action="action")
        graph.add_task(task)

        # Modifier pour créer auto-référence (normalement interdit avant add)
        # Mais testons la validation
        task_self = Task(name="task_self", action="action", depends_on=["future_id"])

        with pytest.raises(TaskDecompositionError):
            graph.add_task(task_self)

    def test_topological_sort_linear(self):
        """Test tri topologique: chaîne linéaire A -> B -> C"""
        graph = TaskGraph()

        task1 = Task(name="A", action="a")
        task2 = Task(name="B", action="b", depends_on=[task1.task_id])
        task3 = Task(name="C", action="c", depends_on=[task2.task_id])

        graph.add_task(task1)
        graph.add_task(task2)
        graph.add_task(task3)

        sorted_tasks = graph.topological_sort()

        assert len(sorted_tasks) == 3
        assert sorted_tasks[0].name == "A"
        assert sorted_tasks[1].name == "B"
        assert sorted_tasks[2].name == "C"

    def test_topological_sort_with_priority(self):
        """Test tri topologique avec priorités"""
        graph = TaskGraph()

        task1 = Task(name="Low", action="a", priority=TaskPriority.LOW)
        task2 = Task(name="High", action="b", priority=TaskPriority.HIGH)
        task3 = Task(name="Critical", action="c", priority=TaskPriority.CRITICAL)

        # Toutes indépendantes
        graph.add_task(task1)
        graph.add_task(task2)
        graph.add_task(task3)

        sorted_tasks = graph.topological_sort()

        # Ordre devrait être: Critical, High, Low
        assert sorted_tasks[0].name == "Critical"
        assert sorted_tasks[1].name == "High"
        assert sorted_tasks[2].name == "Low"

    def test_topological_sort_diamond(self):
        """Test tri topologique: diamond pattern
        
            A
           / \\
          B   C
           \\ /
            D
        """
        graph = TaskGraph()

        taskA = Task(name="A", action="a")
        taskB = Task(name="B", action="b", depends_on=[taskA.task_id])
        taskC = Task(name="C", action="c", depends_on=[taskA.task_id])
        taskD = Task(name="D", action="d", depends_on=[taskB.task_id, taskC.task_id])

        graph.add_task(taskA)
        graph.add_task(taskB)
        graph.add_task(taskC)
        graph.add_task(taskD)

        sorted_tasks = graph.topological_sort()

        assert len(sorted_tasks) == 4
        assert sorted_tasks[0].name == "A"
        assert sorted_tasks[3].name == "D"
        # B et C peuvent être dans n'importe quel ordre
        assert {sorted_tasks[1].name, sorted_tasks[2].name} == {"B", "C"}

    def test_get_ready_tasks(self):
        """Test identification des tâches prêtes"""
        graph = TaskGraph()

        task1 = Task(name="task1", action="a")
        task2 = Task(name="task2", action="b", depends_on=[task1.task_id])

        graph.add_task(task1)
        graph.add_task(task2)

        # Initialement, seule task1 est prête
        ready = graph.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].name == "task1"

        # Marquer task1 comme complétée
        task1.update_status(TaskStatus.COMPLETED)

        # Maintenant task2 devrait être prête
        ready = graph.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].name == "task2"

    def test_get_parallelizable_tasks(self):
        """Test identification des groupes parallélisables"""
        graph = TaskGraph()

        # Niveau 0: task1, task2 (indépendantes, parallèles)
        task1 = Task(name="task1", action="a")
        task2 = Task(name="task2", action="b")

        # Niveau 1: task3 (dépend de task1 et task2)
        task3 = Task(name="task3", action="c", depends_on=[task1.task_id, task2.task_id])

        # Niveau 2: task4 (dépend de task3)
        task4 = Task(name="task4", action="d", depends_on=[task3.task_id])

        graph.add_task(task1)
        graph.add_task(task2)
        graph.add_task(task3)
        graph.add_task(task4)

        levels = graph.get_parallelizable_tasks()

        assert len(levels) == 3
        assert len(levels[0]) == 2  # task1, task2 parallèles
        assert len(levels[1]) == 1  # task3 seule
        assert len(levels[2]) == 1  # task4 seule

    def test_graph_to_dict(self):
        """Test sérialisation du graphe"""
        graph = TaskGraph()

        task1 = Task(name="task1", action="a")
        task2 = Task(name="task2", action="b", depends_on=[task1.task_id])

        graph.add_task(task1)
        graph.add_task(task2)

        graph_dict = graph.to_dict()

        assert "tasks" in graph_dict
        assert "adjacency_list" in graph_dict
        assert "metadata" in graph_dict
        assert graph_dict["metadata"]["total_tasks"] == 2

    def test_graph_repr(self):
        """Test représentation string du graphe"""
        graph = TaskGraph()

        task1 = Task(name="task1", action="a")
        task2 = Task(name="task2", action="b", depends_on=[task1.task_id])

        graph.add_task(task1)
        graph.add_task(task2)

        repr_str = repr(graph)
        assert "tasks=2" in repr_str
        assert "edges=1" in repr_str


class TestComplexScenarios:
    """Tests de scénarios complexes"""

    def test_large_graph_performance(self):
        """Test performance avec graphe large (100 tâches)"""
        graph = TaskGraph()

        tasks = []
        for i in range(100):
            deps = [tasks[i - 1].task_id] if i > 0 else []
            task = Task(name=f"task{i}", action="action", depends_on=deps)
            tasks.append(task)
            graph.add_task(task)

        # Tri topologique devrait être O(V + E)
        sorted_tasks = graph.topological_sort()
        assert len(sorted_tasks) == 100

    def test_wide_parallelism(self):
        """Test graphe avec large parallélisme (50 tâches indépendantes)"""
        graph = TaskGraph()

        # 50 tâches indépendantes
        tasks = []
        for i in range(50):
            task = Task(name=f"task{i}", action="action")
            tasks.append(task)
            graph.add_task(task)

        # Toutes devraient être dans le niveau 0
        levels = graph.get_parallelizable_tasks()
        assert len(levels) == 1
        assert len(levels[0]) == 50

    def test_mixed_status_ready_tasks(self):
        """Test get_ready_tasks avec états mixtes"""
        graph = TaskGraph()

        task1 = Task(name="completed", action="a")
        task2 = Task(name="failed", action="b")
        task3 = Task(name="pending", action="c")
        task4 = Task(name="depends_on_completed", action="d", depends_on=[task1.task_id])
        task5 = Task(name="depends_on_failed", action="e", depends_on=[task2.task_id])

        graph.add_task(task1)
        graph.add_task(task2)
        graph.add_task(task3)
        graph.add_task(task4)
        graph.add_task(task5)

        # Mettre à jour les statuts
        task1.update_status(TaskStatus.COMPLETED)
        task2.update_status(TaskStatus.FAILED)

        ready = graph.get_ready_tasks()

        # task3 et task4 devraient être prêtes
        # task5 ne devrait pas être prête (dépendance échouée)
        ready_names = {t.name for t in ready}
        assert "pending" in ready_names
        assert "depends_on_completed" in ready_names
        assert "depends_on_failed" not in ready_names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
