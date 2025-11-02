"""
Script de validation manuelle des tests HTN

Exécute une validation basique sans pytest pour vérifier:
- Imports fonctionnent
- Classes peuvent être instanciées
- Méthodes principales fonctionnent

Usage:
    python3 tests/test_planner/run_validation.py
"""

import sys
import os

# Ajouter le répertoire racine au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

def test_planner_validation():
    """Validation basique du planner"""
    print("\n" + "="*70)
    print("VALIDATION: HierarchicalPlanner")
    print("="*70)
    
    from planner import HierarchicalPlanner, PlanningStrategy
    from planner.task_graph import TaskDecompositionError
    
    try:
        # Test initialisation
        planner = HierarchicalPlanner()
        assert planner is not None
        print("✓ Initialisation OK")
        
        # Test planification rule-based
        query = "Lis data.csv, calcule la moyenne"
        result = planner.plan(query, strategy=PlanningStrategy.RULE_BASED)
        assert result is not None
        assert len(result.graph.tasks) > 0
        print(f"✓ Planification RULE_BASED OK ({len(result.graph.tasks)} tâches)")
        
        # Test planification hybrid
        result2 = planner.plan(query, strategy=PlanningStrategy.HYBRID)
        assert result2 is not None
        print(f"✓ Planification HYBRID OK ({len(result2.graph.tasks)} tâches)")
        
        # Test validation
        from planner.task_graph import TaskGraph, Task
        empty_graph = TaskGraph()
        try:
            planner._validate_plan(empty_graph)
            assert False, "Should raise error for empty graph"
        except TaskDecompositionError:
            print("✓ Validation empty graph OK (erreur attendue)")
        
        return True
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_executor_validation():
    """Validation basique de l'executor"""
    print("\n" + "="*70)
    print("VALIDATION: TaskExecutor")
    print("="*70)
    
    from planner import TaskExecutor, ExecutionStrategy
    from planner.task_graph import TaskGraph, Task, TaskStatus
    
    try:
        # Test initialisation
        executor = TaskExecutor()
        assert executor is not None
        print("✓ Initialisation OK")
        
        # Test exécution simple
        graph = TaskGraph()
        
        def test_action(params):
            return "result"
        
        task = Task(name="test_task", action="test_action")
        graph.add_task(task)
        
        executor.actions["test_action"] = test_action
        
        result = executor.execute(graph)
        assert result is not None
        assert result.completed_tasks == 1
        assert task.status == TaskStatus.COMPLETED
        print(f"✓ Exécution SEQUENTIAL OK (1 tâche complétée)")
        
        # Test registre d'actions
        executor.register_action("custom_action", test_action)
        assert "custom_action" in executor.actions
        print("✓ Registre d'actions OK")
        
        # Test statistiques
        stats = executor.get_stats()
        assert "total_executions" in stats
        print(f"✓ Statistiques OK ({stats['total_executions']} exécutions)")
        
        return True
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_verifier_validation():
    """Validation basique du verifier"""
    print("\n" + "="*70)
    print("VALIDATION: TaskVerifier")
    print("="*70)
    
    from planner import TaskVerifier, VerificationLevel
    from planner.task_graph import Task, TaskStatus
    
    try:
        # Test initialisation
        verifier = TaskVerifier()
        assert verifier is not None
        print("✓ Initialisation OK")
        
        # Test vérification tâche réussie
        task = Task(name="test_task", action="test_action")
        task.set_result({"data": "result"})
        task.update_status(TaskStatus.COMPLETED)
        
        result = verifier.verify_task(task, level=VerificationLevel.BASIC)
        assert result is not None
        assert result.passed is True
        print(f"✓ Vérification BASIC OK (passed={result.passed})")
        
        # Test vérification STRICT
        result2 = verifier.verify_task(task, level=VerificationLevel.STRICT)
        assert result2 is not None
        print(f"✓ Vérification STRICT OK (passed={result2.passed})")
        
        # Test self-check
        self_check = verifier.self_check()
        assert isinstance(self_check, dict)
        assert "passed" in self_check
        print(f"✓ Self-check OK (passed={self_check['passed']})")
        
        # Test statistiques
        stats = verifier.get_stats()
        assert "total_verifications" in stats
        print(f"✓ Statistiques OK ({stats['total_verifications']} vérifications)")
        
        return True
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration_validation():
    """Validation intégration basique"""
    print("\n" + "="*70)
    print("VALIDATION: Intégration Complète")
    print("="*70)
    
    from planner import (
        HierarchicalPlanner,
        TaskExecutor,
        TaskVerifier,
        PlanningStrategy,
        ExecutionStrategy,
        VerificationLevel,
    )
    from planner.task_graph import TaskGraph, Task, TaskStatus
    
    try:
        # 1. Planifier
        planner = HierarchicalPlanner()
        query = "Lis fichier.csv, analyse les données"
        plan_result = planner.plan(query, strategy=PlanningStrategy.RULE_BASED)
        assert len(plan_result.graph.tasks) > 0
        print(f"✓ Planification OK ({len(plan_result.graph.tasks)} tâches)")
        
        # 2. Exécuter
        executor = TaskExecutor(
            action_registry={
                "read_file": lambda p: {"content": "test"},
                "analyze_data": lambda p: {"mean": 42.0},
                "generic_execute": lambda p: "executed",
            },
            strategy=ExecutionStrategy.SEQUENTIAL,
        )
        exec_result = executor.execute(plan_result.graph)
        assert exec_result is not None
        print(f"✓ Exécution OK (completed={exec_result.completed_tasks}, success={exec_result.success})")
        
        # 3. Vérifier
        verifier = TaskVerifier(default_level=VerificationLevel.STRICT)
        verifications = verifier.verify_graph_results(plan_result.graph)
        assert isinstance(verifications, dict)
        print(f"✓ Vérification OK ({len(verifications)} tâches vérifiées)")
        
        return True
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Exécute toutes les validations"""
    print("\n" + "🚀"*35)
    print("VALIDATION DES TESTS HTN")
    print("🚀"*35)
    
    results = []
    
    # Exécuter validations
    results.append(("Planner", test_planner_validation()))
    results.append(("Executor", test_executor_validation()))
    results.append(("Verifier", test_verifier_validation()))
    results.append(("Intégration", test_integration_validation()))
    
    # Résumé
    print("\n" + "="*70)
    print("RÉSUMÉ DE VALIDATION")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {name}")
    
    print(f"\n📊 Score: {passed}/{total} validations réussies")
    
    if passed == total:
        print("\n✨ TOUTES LES VALIDATIONS RÉUSSIES!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} validation(s) ont échoué")
        return 1


if __name__ == "__main__":
    sys.exit(main())

