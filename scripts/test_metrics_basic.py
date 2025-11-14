#!/usr/bin/env python3
"""
Test basique du système de métriques sans dépendances pytest

Vérifie que le système de métriques fonctionne correctement
"""

import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import directly from metrics module to avoid eval package dependencies
from eval.metrics.test_metrics import TestMetrics, TestRunResult


def test_basic_functionality():
    """Test la fonctionnalité de base"""
    print("=" * 70)
    print("TEST: Basic Functionality")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_metrics.db"

        # Create metrics instance
        metrics = TestMetrics(db_path=db_path)
        print("✓ TestMetrics initialized")

        # Create a test result
        result = TestRunResult(
            timestamp=datetime.utcnow().isoformat(),
            commit_hash="test123",
            branch="test-branch",
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
            ],
        )

        # Record test run
        regressions = metrics.record_test_run(result, check_regression=False)
        print("✓ Test run recorded")

        # Verify data was recorded
        recent_runs = metrics.get_recent_runs(limit=1)
        assert len(recent_runs) == 1, "Expected 1 run"
        assert recent_runs[0]["commit_hash"] == "test123", "Commit hash mismatch"
        assert recent_runs[0]["coverage_percentage"] == 85.5, "Coverage mismatch"
        print("✓ Data verified")

        print("\nRun details:")
        run = recent_runs[0]
        print(f"  - Commit: {run['commit_hash']}")
        print(f"  - Branch: {run['branch']}")
        print(f"  - Tests: {run['total_tests']} (passed: {run['passed']}, failed: {run['failed']})")
        print(f"  - Coverage: {run['coverage_percentage']:.2f}%")
        print(f"  - Duration: {run['duration_seconds']:.2f}s")

    print("\n✓ Basic functionality test passed\n")


def test_regression_detection():
    """Test la détection de régressions"""
    print("=" * 70)
    print("TEST: Regression Detection")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_metrics.db"
        metrics = TestMetrics(db_path=db_path)

        # First run with good coverage
        result1 = TestRunResult(
            timestamp=datetime.utcnow().isoformat(),
            commit_hash="baseline",
            branch="main",
            total_tests=100,
            passed=100,
            failed=0,
            skipped=0,
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
        print("✓ Baseline run recorded (90% coverage)")

        # Second run with coverage regression
        result2 = TestRunResult(
            timestamp=datetime.utcnow().isoformat(),
            commit_hash="regression",
            branch="main",
            total_tests=100,
            passed=100,
            failed=0,
            skipped=0,
            errors=0,
            duration_seconds=10.0,
            coverage_percentage=83.0,  # -7% regression (critical)
            coverage_lines_total=1000,
            coverage_lines_covered=830,
            coverage_lines_missing=170,
            test_markers={},
            slowest_tests=[],
        )
        regressions = metrics.record_test_run(result2, check_regression=True)

        # Verify regression was detected
        assert regressions is not None, "Expected regressions dict"
        assert regressions["coverage"] is not None, "Expected coverage regression"
        assert regressions["coverage"]["severity"] == "critical", "Expected critical severity"
        print("✓ Coverage regression detected")

        print("\nRegression details:")
        reg = regressions["coverage"]
        print(f"  - Type: {reg['type']}")
        print(f"  - Severity: {reg['severity']}")
        print(f"  - Previous: {reg['previous_value']:.2f}%")
        print(f"  - Current: {reg['current_value']:.2f}%")
        print(f"  - Threshold: {reg['threshold']:.2f}%")

        # Verify regression was stored
        db_regressions = metrics.get_regressions(days=1)
        assert len(db_regressions) > 0, "Expected regressions in database"
        print("✓ Regression stored in database")

    print("\n✓ Regression detection test passed\n")


def test_coverage_trends():
    """Test le suivi des tendances de couverture"""
    print("=" * 70)
    print("TEST: Coverage Trends")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_metrics.db"
        metrics = TestMetrics(db_path=db_path)

        # Record multiple runs with varying coverage
        coverages = [80.0, 82.5, 85.0, 83.0, 87.5]
        for i, cov in enumerate(coverages):
            result = TestRunResult(
                timestamp=datetime.utcnow().isoformat(),
                commit_hash=f"commit{i}",
                branch="main",
                total_tests=100,
                passed=int(cov),
                failed=100 - int(cov),
                skipped=0,
                errors=0,
                duration_seconds=10.0,
                coverage_percentage=cov,
                coverage_lines_total=1000,
                coverage_lines_covered=int(cov * 10),
                coverage_lines_missing=int((100 - cov) * 10),
                test_markers={},
                slowest_tests=[],
            )
            metrics.record_test_run(result, check_regression=False)

        print(f"✓ Recorded {len(coverages)} test runs")

        # Get coverage trends
        trends = metrics.get_coverage_trends(days=1)
        assert len(trends) > 0, "Expected coverage trends"
        print("✓ Coverage trends computed")

        trend = trends[0]
        print("\nTrend summary:")
        print(f"  - Runs: {trend['test_runs_count']}")
        print(f"  - Avg coverage: {trend['avg_coverage']:.2f}%")
        print(f"  - Min coverage: {trend['min_coverage']:.2f}%")
        print(f"  - Max coverage: {trend['max_coverage']:.2f}%")

    print("\n✓ Coverage trends test passed\n")


def test_report_generation():
    """Test la génération de rapports"""
    print("=" * 70)
    print("TEST: Report Generation")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_metrics.db"
        metrics = TestMetrics(db_path=db_path)

        # Record some runs
        for i in range(3):
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
                coverage_percentage=80.0 + i * 2,
                coverage_lines_total=1000,
                coverage_lines_covered=800 + i * 20,
                coverage_lines_missing=200 - i * 20,
                test_markers={"unit": 80, "integration": 20},
                slowest_tests=[],
            )
            metrics.record_test_run(result, check_regression=False)

        print("✓ Test runs recorded")

        # Generate report
        report = metrics.generate_report()
        assert "generated_at" in report, "Expected generated_at field"
        assert "summary" in report, "Expected summary field"
        assert "recent_runs" in report, "Expected recent_runs field"
        print("✓ Report generated")

        print("\nReport summary:")
        print(f"  - Total runs: {report['summary']['total_runs']}")
        print(f"  - Latest coverage: {report['summary']['latest_coverage']:.2f}%")
        print(f"  - Recent runs: {len(report['recent_runs'])}")

    print("\n✓ Report generation test passed\n")


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("TESTING METRICS SYSTEM")
    print("=" * 70 + "\n")

    try:
        test_basic_functionality()
        test_regression_detection()
        test_coverage_trends()
        test_report_generation()

        print("=" * 70)
        print("✓ ALL TESTS PASSED")
        print("=" * 70)
        return 0

    except AssertionError as e:
        print("\n" + "=" * 70)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 70)
        return 1

    except Exception as e:
        print("\n" + "=" * 70)
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
