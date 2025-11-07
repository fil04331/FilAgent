"""Tests de stress et de conformité pour le planificateur HTN."""

import pytest

from planner import (
    HierarchicalPlanner,
    PlanningStrategy,
)
from planner.task_graph import TaskDecompositionError


@pytest.mark.parametrize("iterations", [25])
def test_htn_rule_based_stress_runs(iterations: int):
    """Exécuter plusieurs planifications rule-based pour détecter les régressions."""

    planner = HierarchicalPlanner()

    # Rendre le guardian légèrement plus permissif pour éviter les faux positifs
    guardian = planner.compliance_guardian
    guardian.settings.max_tasks = 10
    guardian.settings.failure_stress_threshold = 0.95

    complex_queries = [
        "Analyse donnees.csv, génère statistiques, crée rapport",
        "Lis data.csv, calcule la moyenne",
        "Trouve articles et sources, puis compile synthèse",
    ]

    stress_scores = []

    for idx in range(iterations):
        query = complex_queries[idx % len(complex_queries)]
        result = planner.plan(query, strategy=PlanningStrategy.RULE_BASED)

        report = result.metadata.get("compliance_guardian")
        assert report is not None, "Le guardian doit produire un rapport"
        assert report["passed"] is True
        stress_scores.append(report["stress_score"])

    # Vérifier que le stress moyen reste sous contrôle
    avg_stress = sum(stress_scores) / len(stress_scores)
    assert avg_stress < 0.8


def test_compliance_guardian_strict_mode_blocks_overload():
    """Le mode strict doit bloquer les plans qui dépassent les seuils déclarés."""

    planner = HierarchicalPlanner()
    guardian = planner.compliance_guardian
    guardian.settings.strict_mode = True
    guardian.settings.max_tasks = 1  # Force un dépassement immédiat
    guardian.settings.failure_stress_threshold = 0.5

    with pytest.raises(TaskDecompositionError) as exc:
        planner.plan(
            "Analyse donnees.csv, génère statistiques, crée rapport",
            strategy=PlanningStrategy.RULE_BASED,
        )

    assert "ComplianceGuardian" in str(exc.value)
