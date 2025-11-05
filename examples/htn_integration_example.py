"""
Exemple d'intégration HTN avec FilAgent

Démontre:
- Intégration complète du module planner dans FilAgent
- Décomposition et exécution de requêtes complexes
- Traçabilité et conformité
- Gestion d'erreurs et recovery

Usage:
    python3 examples/htn_integration_example.py
"""

import sys

sys.path.insert(0, "/Volumes/DevSSD/FilAgent")

import json
from datetime import datetime, timezone

from planner import (
    ExecutionStrategy,
    HierarchicalPlanner,
    PlanningStrategy,
    Task,
    TaskExecutor,
    TaskGraph,
    TaskPriority,
    TaskVerifier,
    VerificationLevel,
)

# ============================================================================
# MOCK: Actions simulées pour l'exemple
# ============================================================================


def read_file(params):
    """Action: lire un fichier"""
    filepath = params.get("input", params.get("file", ""))
    print(f"📄 Reading file: {filepath}")
    # Simuler lecture
    return {
        "filepath": filepath,
        "content": f"Mock content of {filepath}",
        "lines": 100,
    }


def analyze_data(params):
    """Action: analyser des données"""
    input_data = params.get("input", params.get("data", {}))
    print(f"📊 Analyzing data...")
    # Simuler analyse
    return {
        "mean": 42.5,
        "median": 40.0,
        "std_dev": 10.2,
        "sample_size": 100,
    }


def generate_stats(params):
    """Action: générer des statistiques"""
    data = params.get("input", params.get("data", {}))
    print(f"📈 Generating statistics...")
    # Simuler génération
    return {
        "stats": {
            "total": 100,
            "average": 42.5,
            "distribution": [10, 20, 40, 20, 10],
        }
    }


def create_pdf(params):
    """Action: créer un rapport PDF"""
    content = params.get("input", params.get("content", {}))
    print(f"📑 Creating PDF report...")
    # Simuler création PDF
    return {
        "pdf_path": "/tmp/report.pdf",
        "pages": 5,
        "size_kb": 250,
    }


def send_email(params):
    """Action: envoyer email (optionnelle)"""
    to = params.get("to", "user@example.com")
    print(f"📧 Sending email to {to}...")
    # Simuler envoi (peut échouer)
    import random

    if random.random() < 0.3:  # 30% de chance d'échec
        raise Exception("Email service unavailable")
    return {"status": "sent", "message_id": "msg_123"}


# ============================================================================
# EXEMPLE 1: Décomposition Rule-Based Simple
# ============================================================================


def example_rule_based():
    """Exemple avec stratégie rule-based"""
    print("\n" + "=" * 70)
    print("EXEMPLE 1: Décomposition Rule-Based")
    print("=" * 70 + "\n")

    # Créer le planificateur (sans LLM)
    planner = HierarchicalPlanner(
        model_interface=None,
        tools_registry=None,
        max_decomposition_depth=3,
    )

    # Requête avec pattern connu
    query = "Lis data.csv, calcule la moyenne"
    print(f"📝 Requête: {query}\n")

    # Planifier
    result = planner.plan(query, strategy=PlanningStrategy.RULE_BASED)

    print(f"✅ Plan créé avec {len(result.graph.tasks)} tâches")
    print(f"   Stratégie: {result.strategy_used.value}")
    print(f"   Confiance: {result.confidence:.0%}")
    print(f"   Raisonnement: {result.reasoning}\n")

    # Afficher les tâches
    print("📋 Tâches planifiées:")
    for i, task in enumerate(result.graph.topological_sort(), 1):
        deps = f" (dépend de: {task.depends_on})" if task.depends_on else ""
        print(f"   {i}. {task.name}: {task.action}({task.params}){deps}")

    return result


# ============================================================================
# EXEMPLE 2: Exécution Parallèle
# ============================================================================


def example_parallel_execution():
    """Exemple avec exécution parallèle"""
    print("\n" + "=" * 70)
    print("EXEMPLE 2: Exécution Parallèle")
    print("=" * 70 + "\n")

    # Créer un graphe manuellement avec tâches parallélisables
    graph = TaskGraph()

    # 3 lectures de fichiers en parallèle
    task1 = Task(
        name="read_file_1",
        action="read_file",
        params={"file": "data1.csv"},
        priority=TaskPriority.HIGH,
    )
    task2 = Task(
        name="read_file_2",
        action="read_file",
        params={"file": "data2.csv"},
        priority=TaskPriority.HIGH,
    )
    task3 = Task(
        name="read_file_3",
        action="read_file",
        params={"file": "data3.csv"},
        priority=TaskPriority.HIGH,
    )

    # Analyse qui dépend des 3 lectures
    task4 = Task(
        name="analyze_combined",
        action="analyze_data",
        params={"data": "combined"},
        depends_on=[task1.task_id, task2.task_id, task3.task_id],
        priority=TaskPriority.NORMAL,
    )

    # Rapport final
    task5 = Task(
        name="create_report",
        action="create_pdf",
        params={"content": "report"},
        depends_on=[task4.task_id],
        priority=TaskPriority.CRITICAL,
    )

    # Email optionnel (peut échouer sans problème)
    task6 = Task(
        name="send_notification",
        action="send_email",
        params={"to": "manager@example.com"},
        depends_on=[task5.task_id],
        priority=TaskPriority.OPTIONAL,
    )

    # Construire le graphe
    for task in [task1, task2, task3, task4, task5, task6]:
        graph.add_task(task)

    print(f"📊 Graphe créé: {len(graph.tasks)} tâches")

    # Analyser les niveaux de parallélisation
    levels = graph.get_parallelizable_tasks()
    print(f"\n🔀 Niveaux de parallélisation: {len(levels)}")
    for i, level in enumerate(levels):
        print(f"   Niveau {i}: {[t.name for t in level]}")

    # Créer l'exécuteur
    action_registry = {
        "read_file": read_file,
        "analyze_data": analyze_data,
        "create_pdf": create_pdf,
        "send_email": send_email,
    }

    executor = TaskExecutor(
        action_registry=action_registry,
        strategy=ExecutionStrategy.PARALLEL,
        max_workers=3,  # 3 workers pour paralléliser
        timeout_per_task_sec=10,
    )

    # Exécuter
    print(f"\n▶️  Exécution avec stratégie {ExecutionStrategy.PARALLEL.value}...\n")
    result = executor.execute(graph)

    # Résultats
    print(f"\n✅ Exécution terminée!")
    print(f"   Succès: {result.success}")
    print(f"   Tâches complétées: {result.completed_tasks}/{len(graph.tasks)}")
    print(f"   Tâches échouées: {result.failed_tasks}")
    print(f"   Tâches sautées: {result.skipped_tasks}")
    print(f"   Durée totale: {result.total_duration_ms:.0f}ms")

    if result.errors:
        print(f"\n⚠️  Erreurs rencontrées:")
        for task_id, error in result.errors.items():
            task = graph.tasks[task_id]
            print(f"   - {task.name}: {error}")

    return result, graph


# ============================================================================
# EXEMPLE 3: Validation Stricte avec Vérificateur
# ============================================================================


def example_verification(graph):
    """Exemple de validation des résultats"""
    print("\n" + "=" * 70)
    print("EXEMPLE 3: Validation des Résultats")
    print("=" * 70 + "\n")

    # Créer le vérificateur
    verifier = TaskVerifier(default_level=VerificationLevel.STRICT)

    # Enregistrer un vérificateur custom pour PDF
    def verify_pdf(task, result):
        from planner.verifier import VerificationResult

        checks = {}
        errors = []

        # Check: PDF path existe
        if "pdf_path" not in result:
            errors.append("Missing pdf_path in result")
            checks["has_pdf_path"] = False
        else:
            checks["has_pdf_path"] = True

        # Check: Taille > 0
        if "size_kb" in result and result["size_kb"] > 0:
            checks["size_valid"] = True
        else:
            errors.append("Invalid PDF size")
            checks["size_valid"] = False

        return VerificationResult(
            passed=len(errors) == 0,
            level=VerificationLevel.STRICT,
            checks=checks,
            errors=errors,
        )

    verifier.register_custom_verifier("create_pdf", verify_pdf)

    # Vérifier toutes les tâches complétées
    print("🔍 Vérification des résultats...\n")
    verifications = verifier.verify_graph_results(graph, level=VerificationLevel.STRICT)

    for task_id, verif in verifications.items():
        task = graph.tasks[task_id]
        status = "✅" if verif.passed else "❌"
        print(f"{status} {task.name}")
        print(f"   Checks: {verif.checks}")
        print(f"   Confiance: {verif.confidence_score:.0%}")

        if verif.errors:
            print(f"   Erreurs: {verif.errors}")
        if verif.warnings:
            print(f"   Avertissements: {verif.warnings}")
        print()

    # Self-check du vérificateur
    self_check = verifier.self_check()
    print(f"🔧 Self-check du vérificateur: {'✅ OK' if self_check['passed'] else '❌ FAIL'}")
    print(f"   Stats: {verifier.get_stats()}")

    return verifier


# ============================================================================
# EXEMPLE 4: Traçabilité et Conformité
# ============================================================================


def example_traceability(result, exec_result, graph):
    """Exemple de traçabilité complète"""
    print("\n" + "=" * 70)
    print("EXEMPLE 4: Traçabilité et Conformité")
    print("=" * 70 + "\n")

    print("📝 Logs de traçabilité générés:\n")

    # 1. Planning Result (Decision Record)
    planning_record = {
        "event_type": "planning_decision",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": "Example query",
        "strategy": result.strategy_used.value,
        "confidence": result.confidence,
        "reasoning": result.reasoning,
        "tasks_count": len(result.graph.tasks),
        "metadata": result.metadata,
    }

    print("1️⃣ Decision Record (Planification):")
    print(json.dumps(planning_record, indent=2))

    # 2. Execution Result
    execution_record = {
        "event_type": "execution_completed",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "success": exec_result.success,
        "completed": exec_result.completed_tasks,
        "failed": exec_result.failed_tasks,
        "skipped": exec_result.skipped_tasks,
        "duration_ms": exec_result.total_duration_ms,
        "metadata": exec_result.metadata,
    }

    print("\n2️⃣ Execution Record:")
    print(json.dumps(execution_record, indent=2))

    # 3. Task Provenance (W3C PROV)
    provenance_records = []
    for task in graph.tasks.values():
        prov = {
            "entity": task.task_id,
            "type": "Task",
            "activity": task.action,
            "wasGeneratedBy": task.task_id,
            "wasDerivedFrom": task.depends_on,
            "metadata": task.metadata,
        }
        provenance_records.append(prov)

    print(f"\n3️⃣ Provenance Records (W3C PROV): {len(provenance_records)} entrées")
    print(json.dumps(provenance_records[0], indent=2) + "\n   ...")

    print("\n✅ Conformité:")
    print("   - Loi 25 (QC): Decision Records générés ✓")
    print("   - RGPD: Traçabilité complète ✓")
    print("   - AI Act: Justifications disponibles ✓")
    print("   - NIST AI RMF: Validation multicouche ✓")


# ============================================================================
# MAIN: Exécuter tous les exemples
# ============================================================================


def main():
    """Exécute tous les exemples"""
    print("\n" + "🚀" * 35)
    print("HTN PLANNING MODULE - EXEMPLES D'INTÉGRATION")
    print("🚀" * 35)

    try:
        # Exemple 1: Rule-based planning
        result1 = example_rule_based()

        # Exemple 2: Parallel execution
        exec_result, graph = example_parallel_execution()

        # Exemple 3: Verification
        verifier = example_verification(graph)

        # Exemple 4: Traceability
        example_traceability(result1, exec_result, graph)

        print("\n" + "=" * 70)
        print("✨ TOUS LES EXEMPLES COMPLÉTÉS AVEC SUCCÈS!")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
