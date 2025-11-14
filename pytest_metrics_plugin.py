"""
Plugin pytest pour collecter automatiquement les métriques de tests

Ce plugin s'intègre avec pytest pour capturer:
- Résultats des tests (passed, failed, skipped, errors)
- Durée d'exécution
- Couverture de code
- Tests les plus lents

Usage:
    pytest --metrics
    pytest --metrics --no-regression-check
"""

import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import pytest
from _pytest.config import Config
from _pytest.terminal import TerminalReporter

from eval.metrics import TestMetrics, TestRunResult


class MetricsPlugin:
    """Plugin pytest pour collecter les métriques"""

    def __init__(self, config: Config):
        self.config = config
        self.session_start_time = None
        self.session_end_time = None
        self.test_results = {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "error": 0,
        }
        self.test_durations = []
        self.test_markers = {}
        self.metrics_enabled = config.getoption("--metrics", default=False)
        self.check_regression = not config.getoption("--no-regression-check", default=False)
        self.metrics = TestMetrics() if self.metrics_enabled else None

    @pytest.hookimpl(tryfirst=True)
    def pytest_sessionstart(self, session):
        """Hook appelé au début de la session de tests"""
        self.session_start_time = time.time()

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item, call):
        """Hook appelé après chaque test"""
        outcome = yield
        report = outcome.get_result()

        # Capture test results
        if report.when == "call":
            if report.passed:
                self.test_results["passed"] += 1
            elif report.failed:
                self.test_results["failed"] += 1
            elif report.skipped:
                self.test_results["skipped"] += 1

            # Capture duration
            if hasattr(report, "duration"):
                self.test_durations.append(
                    {
                        "nodeid": report.nodeid,
                        "duration": report.duration,
                    }
                )

            # Capture markers
            for marker in item.iter_markers():
                if marker.name not in self.test_markers:
                    self.test_markers[marker.name] = 0
                self.test_markers[marker.name] += 1

    @pytest.hookimpl(hookwrapper=True)
    def pytest_sessionfinish(self, session, exitstatus):
        """Hook appelé à la fin de la session de tests"""
        yield

        if not self.metrics_enabled:
            return

        self.session_end_time = time.time()
        duration_seconds = self.session_end_time - self.session_start_time

        # Get coverage data
        coverage_data = self._get_coverage_data()

        # Get git information
        git_info = self._get_git_info()

        # Get slowest tests (top 10)
        slowest_tests = sorted(
            self.test_durations,
            key=lambda x: x["duration"],
            reverse=True,
        )[:10]

        # Calculate total tests
        total_tests = sum(self.test_results.values())

        # Create test run result
        result = TestRunResult(
            timestamp=datetime.utcnow().isoformat(),
            commit_hash=git_info.get("commit_hash", "unknown"),
            branch=git_info.get("branch", "unknown"),
            total_tests=total_tests,
            passed=self.test_results["passed"],
            failed=self.test_results["failed"],
            skipped=self.test_results["skipped"],
            errors=self.test_results["error"],
            duration_seconds=duration_seconds,
            coverage_percentage=coverage_data.get("coverage_percentage", 0.0),
            coverage_lines_total=coverage_data.get("lines_total", 0),
            coverage_lines_covered=coverage_data.get("lines_covered", 0),
            coverage_lines_missing=coverage_data.get("lines_missing", 0),
            test_markers=self.test_markers,
            slowest_tests=slowest_tests,
        )

        # Record metrics
        regressions = self.metrics.record_test_run(
            result=result,
            check_regression=self.check_regression,
        )

        # Display results
        self._display_metrics(result, regressions)

        # Fail build if critical regressions detected
        if regressions and self.check_regression:
            critical_regressions = [
                r for r in regressions.values()
                if r and r.get("severity") == "critical"
            ]
            if critical_regressions:
                session.exitstatus = 1  # Force failure

    def _get_coverage_data(self) -> Dict[str, Any]:
        """
        Récupère les données de couverture depuis .coverage

        Returns:
            Dict avec les données de couverture
        """
        try:
            # Try to import coverage
            import coverage

            cov = coverage.Coverage()
            cov.load()

            # Get coverage report
            total_lines = 0
            covered_lines = 0
            missing_lines = 0

            data = cov.get_data()
            for filename in data.measured_files():
                analysis = cov.analysis2(filename)
                total_lines += len(analysis[1])  # executable lines
                covered_lines += len(analysis[2])  # executed lines
                missing_lines += len(analysis[3])  # missing lines

            coverage_percentage = (covered_lines / total_lines * 100) if total_lines > 0 else 0.0

            return {
                "coverage_percentage": round(coverage_percentage, 2),
                "lines_total": total_lines,
                "lines_covered": covered_lines,
                "lines_missing": missing_lines,
            }

        except Exception as e:
            # If coverage not available, return defaults
            return {
                "coverage_percentage": 0.0,
                "lines_total": 0,
                "lines_covered": 0,
                "lines_missing": 0,
            }

    def _get_git_info(self) -> Dict[str, str]:
        """
        Récupère les informations git

        Returns:
            Dict avec commit_hash et branch
        """
        try:
            commit_hash = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                stderr=subprocess.DEVNULL,
            ).decode().strip()

            branch = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                stderr=subprocess.DEVNULL,
            ).decode().strip()

            return {
                "commit_hash": commit_hash,
                "branch": branch,
            }
        except Exception:
            return {
                "commit_hash": "unknown",
                "branch": "unknown",
            }

    def _display_metrics(self, result: TestRunResult, regressions: Optional[Dict[str, Any]]):
        """
        Affiche les métriques dans le terminal

        Args:
            result: Résultat du test
            regressions: Régressions détectées
        """
        print("\n" + "=" * 70)
        print("📊 TEST METRICS")
        print("=" * 70)
        print(f"✓ Total Tests: {result.total_tests}")
        print(f"  - Passed: {result.passed}")
        print(f"  - Failed: {result.failed}")
        print(f"  - Skipped: {result.skipped}")
        print(f"  - Errors: {result.errors}")
        print(f"⏱  Duration: {result.duration_seconds:.2f}s")
        print(f"📈 Coverage: {result.coverage_percentage:.2f}%")
        print(f"  - Total lines: {result.coverage_lines_total}")
        print(f"  - Covered: {result.coverage_lines_covered}")
        print(f"  - Missing: {result.coverage_lines_missing}")
        print(f"🏷  Markers: {json.dumps(result.test_markers, indent=2)}")
        print(f"🔍 Commit: {result.commit_hash[:8]}")
        print(f"🌿 Branch: {result.branch}")

        if result.slowest_tests:
            print(f"\n⏳ Slowest Tests (Top 5):")
            for i, test in enumerate(result.slowest_tests[:5], 1):
                print(f"  {i}. {test['nodeid']} ({test['duration']:.3f}s)")

        if regressions:
            print("\n⚠️  REGRESSIONS DETECTED:")
            for reg_type, reg_data in regressions.items():
                if reg_data:
                    severity = reg_data["severity"].upper()
                    icon = "❌" if severity == "CRITICAL" else "⚠️ "
                    print(f"\n{icon} {reg_type.upper()} [{severity}]")
                    print(f"  {reg_data['details']}")
                    print(f"  Previous: {reg_data['previous_value']:.2f}")
                    print(f"  Current: {reg_data['current_value']:.2f}")
                    print(f"  Threshold: {reg_data['threshold']:.2f}")

        print("=" * 70)


def pytest_addoption(parser):
    """Ajoute les options de ligne de commande"""
    group = parser.getgroup("metrics")
    group.addoption(
        "--metrics",
        action="store_true",
        default=False,
        help="Enable test metrics collection",
    )
    group.addoption(
        "--no-regression-check",
        action="store_true",
        default=False,
        help="Disable regression checking",
    )


def pytest_configure(config):
    """Configure le plugin"""
    if config.getoption("--metrics"):
        plugin = MetricsPlugin(config)
        config.pluginmanager.register(plugin, "metrics_plugin")
