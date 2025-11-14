"""
Tests pour le système de métriques de tests

Tests unitaires pour:
- TestMetrics
- TestRunResult
- Détection de régressions
- Génération de rapports
"""

import json
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from eval.metrics import TestMetrics, TestRunResult, get_test_metrics, reset_test_metrics


@pytest.fixture
def temp_metrics_db():
    """Fixture pour une base de données de métriques temporaire"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_metrics.db"
        yield db_path


@pytest.fixture
def metrics(temp_metrics_db):
    """Fixture pour un TestMetrics isolé"""
    return TestMetrics(db_path=temp_metrics_db)


@pytest.mark.unit
def test_test_metrics_initialization(temp_metrics_db):
    """Test l'initialisation de TestMetrics"""
    metrics = TestMetrics(db_path=temp_metrics_db)

    # Vérifier que la DB existe
    assert temp_metrics_db.exists()

    # Vérifier que les tables sont créées
    conn = sqlite3.connect(temp_metrics_db)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]

    assert "test_runs" in tables
    assert "coverage_trends" in tables
    assert "test_regressions" in tables

    conn.close()


@pytest.mark.unit
def test_record_test_run(metrics):
    """Test l'enregistrement d'un test run"""
    result = TestRunResult(
        timestamp=datetime.utcnow().isoformat(),
        commit_hash="abc123",
        branch="main",
        total_tests=100,
        passed=95,
        failed=3,
        skipped=2,
        errors=0,
        duration_seconds=10.5,
        coverage_percentage=85.5,
        coverage_lines_total=1000,
        coverage_lines_covered=855,
        coverage_lines_missing=145,
        test_markers={"unit": 80, "integration": 20},
        slowest_tests=[
            {"nodeid": "test_slow.py::test_1", "duration": 2.5},
            {"nodeid": "test_slow.py::test_2", "duration": 1.8},
        ],
    )

    # Record test run
    regressions = metrics.record_test_run(result, check_regression=False)

    # Vérifier que c'est enregistré
    recent_runs = metrics.get_recent_runs(limit=1)
    assert len(recent_runs) == 1

    run = recent_runs[0]
    assert run["commit_hash"] == "abc123"
    assert run["branch"] == "main"
    assert run["total_tests"] == 100
    assert run["passed"] == 95
    assert run["failed"] == 3
    assert run["coverage_percentage"] == 85.5


@pytest.mark.unit
def test_coverage_trend_tracking(metrics):
    """Test le suivi des tendances de couverture"""
    # Record plusieurs runs
    date = datetime.utcnow().strftime("%Y-%m-%d")

    for coverage in [80.0, 82.5, 85.0]:
        result = TestRunResult(
            timestamp=datetime.utcnow().isoformat(),
            commit_hash=f"commit{coverage}",
            branch="main",
            total_tests=100,
            passed=95,
            failed=3,
            skipped=2,
            errors=0,
            duration_seconds=10.0,
            coverage_percentage=coverage,
            coverage_lines_total=1000,
            coverage_lines_covered=int(coverage * 10),
            coverage_lines_missing=int((100 - coverage) * 10),
            test_markers={},
            slowest_tests=[],
        )
        metrics.record_test_run(result, check_regression=False)

    # Vérifier les tendances
    trends = metrics.get_coverage_trends(days=1)
    assert len(trends) == 1

    trend = trends[0]
    assert trend["date"] == date
    assert trend["test_runs_count"] == 3
    assert 80.0 <= trend["avg_coverage"] <= 85.0
    assert trend["min_coverage"] == 80.0
    assert trend["max_coverage"] == 85.0


@pytest.mark.unit
def test_regression_detection_coverage(metrics):
    """Test la détection de régression de couverture"""
    # Record un premier run avec bonne couverture
    result1 = TestRunResult(
        timestamp=datetime.utcnow().isoformat(),
        commit_hash="baseline",
        branch="main",
        total_tests=100,
        passed=95,
        failed=0,
        skipped=5,
        errors=0,
        duration_seconds=10.0,
        coverage_percentage=90.0,
        coverage_lines_total=1000,
        coverage_lines_covered=900,
        coverage_lines_missing=100,
        test_markers={},
        slowest_tests=[],
    )
    metrics.record_test_run(result1, check_regression=False)

    # Record un second run avec régression de couverture
    result2 = TestRunResult(
        timestamp=datetime.utcnow().isoformat(),
        commit_hash="regression",
        branch="main",
        total_tests=100,
        passed=95,
        failed=0,
        skipped=5,
        errors=0,
        duration_seconds=10.0,
        coverage_percentage=85.0,  # -5% régression
        coverage_lines_total=1000,
        coverage_lines_covered=850,
        coverage_lines_missing=150,
        test_markers={},
        slowest_tests=[],
    )
    regressions = metrics.record_test_run(result2, check_regression=True)

    # Vérifier que la régression est détectée
    assert regressions is not None
    assert regressions["coverage"] is not None
    assert regressions["coverage"]["type"] == "coverage"
    assert regressions["coverage"]["severity"] == "critical"
    assert regressions["coverage"]["previous_value"] == 90.0
    assert regressions["coverage"]["current_value"] == 85.0

    # Vérifier que la régression est enregistrée
    db_regressions = metrics.get_regressions(days=1, severity="critical")
    assert len(db_regressions) == 1
    assert db_regressions[0]["regression_type"] == "coverage"


@pytest.mark.unit
def test_no_regression_within_threshold(metrics):
    """Test qu'une petite baisse ne déclenche pas de régression"""
    # Record un premier run
    result1 = TestRunResult(
        timestamp=datetime.utcnow().isoformat(),
        commit_hash="baseline",
        branch="main",
        total_tests=100,
        passed=95,
        failed=0,
        skipped=5,
        errors=0,
        duration_seconds=10.0,
        coverage_percentage=85.0,
        coverage_lines_total=1000,
        coverage_lines_covered=850,
        coverage_lines_missing=150,
        test_markers={},
        slowest_tests=[],
    )
    metrics.record_test_run(result1, check_regression=False)

    # Record un second run avec petite baisse (< 2%)
    result2 = TestRunResult(
        timestamp=datetime.utcnow().isoformat(),
        commit_hash="minor_drop",
        branch="main",
        total_tests=100,
        passed=95,
        failed=0,
        skipped=5,
        errors=0,
        duration_seconds=10.0,
        coverage_percentage=84.0,  # -1% (dans le seuil)
        coverage_lines_total=1000,
        coverage_lines_covered=840,
        coverage_lines_missing=160,
        test_markers={},
        slowest_tests=[],
    )
    regressions = metrics.record_test_run(result2, check_regression=True)

    # Vérifier qu'aucune régression n'est détectée
    assert regressions is not None
    assert regressions["coverage"] is None


@pytest.mark.unit
def test_test_failure_regression(metrics):
    """Test la détection de régression de tests échoués"""
    # Record un premier run avec 1 échec
    result1 = TestRunResult(
        timestamp=datetime.utcnow().isoformat(),
        commit_hash="baseline",
        branch="main",
        total_tests=100,
        passed=99,
        failed=1,
        skipped=0,
        errors=0,
        duration_seconds=10.0,
        coverage_percentage=85.0,
        coverage_lines_total=1000,
        coverage_lines_covered=850,
        coverage_lines_missing=150,
        test_markers={},
        slowest_tests=[],
    )
    metrics.record_test_run(result1, check_regression=False)

    # Record un second run avec 5 échecs (+ de 3 nouveaux)
    result2 = TestRunResult(
        timestamp=datetime.utcnow().isoformat(),
        commit_hash="more_failures",
        branch="main",
        total_tests=100,
        passed=95,
        failed=5,
        skipped=0,
        errors=0,
        duration_seconds=10.0,
        coverage_percentage=85.0,
        coverage_lines_total=1000,
        coverage_lines_covered=850,
        coverage_lines_missing=150,
        test_markers={},
        slowest_tests=[],
    )
    regressions = metrics.record_test_run(result2, check_regression=True)

    # Vérifier que la régression est détectée
    assert regressions is not None
    assert regressions["tests_failed"] is not None
    assert regressions["tests_failed"]["severity"] == "critical"


@pytest.mark.unit
def test_generate_report(metrics):
    """Test la génération de rapport"""
    # Record quelques runs
    for i in range(5):
        result = TestRunResult(
            timestamp=datetime.utcnow().isoformat(),
            commit_hash=f"commit{i}",
            branch="main",
            total_tests=100,
            passed=95 + i,
            failed=5 - i,
            skipped=0,
            errors=0,
            duration_seconds=10.0 + i,
            coverage_percentage=80.0 + i,
            coverage_lines_total=1000,
            coverage_lines_covered=800 + (i * 10),
            coverage_lines_missing=200 - (i * 10),
            test_markers={"unit": 80, "integration": 20},
            slowest_tests=[],
        )
        metrics.record_test_run(result, check_regression=False)

    # Générer un rapport
    report = metrics.generate_report()

    # Vérifier le contenu
    assert "generated_at" in report
    assert "summary" in report
    assert "recent_runs" in report
    assert "coverage_trends" in report
    assert "regressions" in report

    assert report["summary"]["total_runs"] == 5
    assert report["summary"]["latest_coverage"] == 84.0
    assert len(report["recent_runs"]) == 5


@pytest.mark.unit
def test_singleton_pattern():
    """Test le pattern singleton de get_test_metrics"""
    # Reset pour commencer propre
    reset_test_metrics()

    # Récupérer deux instances
    metrics1 = get_test_metrics()
    metrics2 = get_test_metrics()

    # Vérifier que c'est la même instance
    assert metrics1 is metrics2

    # Reset
    reset_test_metrics()

    # Vérifier qu'une nouvelle instance est créée
    metrics3 = get_test_metrics()
    assert metrics3 is not metrics1


@pytest.mark.unit
def test_get_recent_runs_with_branch_filter(metrics):
    """Test le filtrage par branche des runs récents"""
    # Record des runs sur différentes branches
    for branch in ["main", "develop", "main", "feature/test"]:
        result = TestRunResult(
            timestamp=datetime.utcnow().isoformat(),
            commit_hash=f"commit_{branch}",
            branch=branch,
            total_tests=100,
            passed=95,
            failed=5,
            skipped=0,
            errors=0,
            duration_seconds=10.0,
            coverage_percentage=85.0,
            coverage_lines_total=1000,
            coverage_lines_covered=850,
            coverage_lines_missing=150,
            test_markers={},
            slowest_tests=[],
        )
        metrics.record_test_run(result, check_regression=False)

    # Récupérer les runs de la branche main seulement
    main_runs = metrics.get_recent_runs(limit=10, branch="main")
    assert len(main_runs) == 2
    assert all(run["branch"] == "main" for run in main_runs)

    # Récupérer tous les runs
    all_runs = metrics.get_recent_runs(limit=10)
    assert len(all_runs) == 4
