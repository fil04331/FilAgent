"""
Module de métriques de tests pour FilAgent

Collecte et analyse les métriques de tests:
- Durée d'exécution des tests
- Taux de réussite/échec
- Couverture de code
- Tendances historiques

Usage:
    from eval.metrics.test_metrics import TestMetrics
    metrics = TestMetrics()
    metrics.record_test_run(...)
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import hashlib


@dataclass
class TestRunResult:
    """Résultat d'une exécution de tests"""

    timestamp: str
    commit_hash: str
    branch: str
    total_tests: int
    passed: int
    failed: int
    skipped: int
    errors: int
    duration_seconds: float
    coverage_percentage: float
    coverage_lines_total: int
    coverage_lines_covered: int
    coverage_lines_missing: int
    test_markers: Dict[str, int]  # Count per marker (unit, integration, etc.)
    slowest_tests: List[Dict[str, Any]]  # Top 10 slowest tests


class TestMetrics:
    """
    Collecteur de métriques de tests

    Fonctionnalités:
    1. Enregistrement des résultats de tests
    2. Suivi des tendances de couverture
    3. Détection de régressions
    4. Rapports historiques
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialise le collecteur de métriques

        Args:
            db_path: Chemin vers la base de données SQLite
                    (par défaut: eval/metrics/test_metrics.db)
        """
        if db_path is None:
            db_path = Path(__file__).parent / "test_metrics.db"

        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_db()

    def _init_db(self):
        """Initialise la base de données"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Table: test_runs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                commit_hash TEXT NOT NULL,
                branch TEXT NOT NULL,
                total_tests INTEGER NOT NULL,
                passed INTEGER NOT NULL,
                failed INTEGER NOT NULL,
                skipped INTEGER NOT NULL,
                errors INTEGER NOT NULL,
                duration_seconds REAL NOT NULL,
                coverage_percentage REAL NOT NULL,
                coverage_lines_total INTEGER NOT NULL,
                coverage_lines_covered INTEGER NOT NULL,
                coverage_lines_missing INTEGER NOT NULL,
                test_markers TEXT,  -- JSON
                slowest_tests TEXT,  -- JSON
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Table: coverage_trends (daily aggregates)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS coverage_trends (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                avg_coverage REAL NOT NULL,
                min_coverage REAL NOT NULL,
                max_coverage REAL NOT NULL,
                test_runs_count INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Table: test_regressions (detected regressions)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_regressions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                commit_hash TEXT NOT NULL,
                branch TEXT NOT NULL,
                regression_type TEXT NOT NULL,  -- coverage, tests_failed, duration
                previous_value REAL NOT NULL,
                current_value REAL NOT NULL,
                threshold REAL NOT NULL,
                severity TEXT NOT NULL,  -- critical, warning, info
                details TEXT,  -- JSON
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_test_runs_timestamp
            ON test_runs(timestamp DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_test_runs_branch
            ON test_runs(branch)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_coverage_trends_date
            ON coverage_trends(date DESC)
        """)

        conn.commit()
        conn.close()

    def record_test_run(
        self,
        result: TestRunResult,
        check_regression: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Enregistre un résultat de test

        Args:
            result: Résultat du test
            check_regression: Vérifier les régressions

        Returns:
            Dict avec les régressions détectées (si check_regression=True)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Insert test run
        cursor.execute(
            """
            INSERT INTO test_runs (
                timestamp, commit_hash, branch,
                total_tests, passed, failed, skipped, errors,
                duration_seconds,
                coverage_percentage, coverage_lines_total,
                coverage_lines_covered, coverage_lines_missing,
                test_markers, slowest_tests
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                result.timestamp,
                result.commit_hash,
                result.branch,
                result.total_tests,
                result.passed,
                result.failed,
                result.skipped,
                result.errors,
                result.duration_seconds,
                result.coverage_percentage,
                result.coverage_lines_total,
                result.coverage_lines_covered,
                result.coverage_lines_missing,
                json.dumps(result.test_markers),
                json.dumps(result.slowest_tests),
            ),
        )

        conn.commit()

        # Check for regressions
        regressions = None
        if check_regression:
            regressions = self._check_regressions(cursor, result)

        # Update daily trends
        self._update_coverage_trends(cursor, result)

        conn.commit()
        conn.close()

        return regressions

    def _check_regressions(
        self, cursor: sqlite3.Cursor, result: TestRunResult
    ) -> Dict[str, Any]:
        """
        Vérifie les régressions par rapport au dernier run

        Args:
            cursor: Curseur SQLite
            result: Résultat actuel

        Returns:
            Dict des régressions détectées
        """
        regressions = {
            "coverage": None,
            "tests_failed": None,
            "duration": None,
        }

        # Get previous run on same branch
        cursor.execute(
            """
            SELECT coverage_percentage, failed, duration_seconds
            FROM test_runs
            WHERE branch = ? AND timestamp < ?
            ORDER BY timestamp DESC
            LIMIT 1
        """,
            (result.branch, result.timestamp),
        )

        previous = cursor.fetchone()
        if not previous:
            return regressions  # No previous run to compare

        prev_coverage, prev_failed, prev_duration = previous

        # Check coverage regression (threshold: -2%)
        if result.coverage_percentage < prev_coverage - 2.0:
            regression = {
                "type": "coverage",
                "previous_value": prev_coverage,
                "current_value": result.coverage_percentage,
                "threshold": 2.0,
                "severity": "critical" if result.coverage_percentage < prev_coverage - 5.0 else "warning",
                "details": f"Coverage dropped from {prev_coverage:.2f}% to {result.coverage_percentage:.2f}%",
            }
            regressions["coverage"] = regression

            # Record regression
            cursor.execute(
                """
                INSERT INTO test_regressions (
                    timestamp, commit_hash, branch,
                    regression_type, previous_value, current_value,
                    threshold, severity, details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    result.timestamp,
                    result.commit_hash,
                    result.branch,
                    "coverage",
                    prev_coverage,
                    result.coverage_percentage,
                    2.0,
                    regression["severity"],
                    json.dumps({"details": regression["details"]}),
                ),
            )

        # Check test failures regression (more than 3 new failures)
        if result.failed > prev_failed + 3:
            regression = {
                "type": "tests_failed",
                "previous_value": prev_failed,
                "current_value": result.failed,
                "threshold": 3,
                "severity": "critical",
                "details": f"Failed tests increased from {prev_failed} to {result.failed}",
            }
            regressions["tests_failed"] = regression

            cursor.execute(
                """
                INSERT INTO test_regressions (
                    timestamp, commit_hash, branch,
                    regression_type, previous_value, current_value,
                    threshold, severity, details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    result.timestamp,
                    result.commit_hash,
                    result.branch,
                    "tests_failed",
                    prev_failed,
                    result.failed,
                    3,
                    regression["severity"],
                    json.dumps({"details": regression["details"]}),
                ),
            )

        # Check duration regression (>50% slower)
        if result.duration_seconds > prev_duration * 1.5:
            regression = {
                "type": "duration",
                "previous_value": prev_duration,
                "current_value": result.duration_seconds,
                "threshold": 1.5,
                "severity": "warning",
                "details": f"Test duration increased from {prev_duration:.2f}s to {result.duration_seconds:.2f}s",
            }
            regressions["duration"] = regression

            cursor.execute(
                """
                INSERT INTO test_regressions (
                    timestamp, commit_hash, branch,
                    regression_type, previous_value, current_value,
                    threshold, severity, details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    result.timestamp,
                    result.commit_hash,
                    result.branch,
                    "duration",
                    prev_duration,
                    result.duration_seconds,
                    1.5,
                    regression["severity"],
                    json.dumps({"details": regression["details"]}),
                ),
            )

        return regressions

    def _update_coverage_trends(self, cursor: sqlite3.Cursor, result: TestRunResult):
        """
        Met à jour les tendances de couverture quotidiennes

        Args:
            cursor: Curseur SQLite
            result: Résultat du test
        """
        date = result.timestamp.split("T")[0]  # Extract date (YYYY-MM-DD)

        # Get existing trend for today
        cursor.execute(
            """
            SELECT avg_coverage, min_coverage, max_coverage, test_runs_count
            FROM coverage_trends
            WHERE date = ?
        """,
            (date,),
        )

        existing = cursor.fetchone()

        if existing:
            # Update existing trend
            avg_cov, min_cov, max_cov, count = existing
            new_count = count + 1
            new_avg = (avg_cov * count + result.coverage_percentage) / new_count
            new_min = min(min_cov, result.coverage_percentage)
            new_max = max(max_cov, result.coverage_percentage)

            cursor.execute(
                """
                UPDATE coverage_trends
                SET avg_coverage = ?, min_coverage = ?, max_coverage = ?,
                    test_runs_count = ?
                WHERE date = ?
            """,
                (new_avg, new_min, new_max, new_count, date),
            )
        else:
            # Create new trend
            cursor.execute(
                """
                INSERT INTO coverage_trends (
                    date, avg_coverage, min_coverage, max_coverage, test_runs_count
                ) VALUES (?, ?, ?, ?, ?)
            """,
                (
                    date,
                    result.coverage_percentage,
                    result.coverage_percentage,
                    result.coverage_percentage,
                    1,
                ),
            )

    def get_recent_runs(self, limit: int = 10, branch: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Récupère les derniers test runs

        Args:
            limit: Nombre de runs à récupérer
            branch: Filtrer par branche (optionnel)

        Returns:
            Liste des test runs
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if branch:
            cursor.execute(
                """
                SELECT * FROM test_runs
                WHERE branch = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """,
                (branch, limit),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM test_runs
                ORDER BY timestamp DESC
                LIMIT ?
            """,
                (limit,),
            )

        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        conn.close()

        return [dict(zip(columns, row)) for row in rows]

    def get_coverage_trends(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Récupère les tendances de couverture

        Args:
            days: Nombre de jours à récupérer

        Returns:
            Liste des tendances quotidiennes
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM coverage_trends
            ORDER BY date DESC
            LIMIT ?
        """,
            (days,),
        )

        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        conn.close()

        return [dict(zip(columns, row)) for row in rows]

    def get_regressions(self, days: int = 7, severity: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Récupère les régressions détectées

        Args:
            days: Nombre de jours à récupérer
            severity: Filtrer par sévérité (critical, warning, info)

        Returns:
            Liste des régressions
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if severity:
            cursor.execute(
                """
                SELECT * FROM test_regressions
                WHERE severity = ? AND timestamp >= datetime('now', '-' || ? || ' days')
                ORDER BY timestamp DESC
            """,
                (severity, days),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM test_regressions
                WHERE timestamp >= datetime('now', '-' || ? || ' days')
                ORDER BY timestamp DESC
            """,
                (days,),
            )

        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        conn.close()

        return [dict(zip(columns, row)) for row in rows]

    def generate_report(self, output_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Génère un rapport de métriques

        Args:
            output_path: Chemin de sortie (optionnel)

        Returns:
            Dict avec le rapport complet
        """
        recent_runs = self.get_recent_runs(limit=10)
        trends = self.get_coverage_trends(days=30)
        regressions = self.get_regressions(days=7)

        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "total_runs": len(recent_runs),
                "latest_coverage": recent_runs[0]["coverage_percentage"] if recent_runs else 0.0,
                "coverage_trend_30d": len(trends),
                "critical_regressions_7d": len([r for r in regressions if r["severity"] == "critical"]),
            },
            "recent_runs": recent_runs[:5],  # Top 5
            "coverage_trends": trends[:7],  # Last 7 days
            "regressions": regressions,
        }

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(report, f, indent=2)

        return report


# Instance globale (singleton)
_metrics_instance: Optional[TestMetrics] = None


def get_test_metrics(db_path: Optional[Path] = None) -> TestMetrics:
    """
    Récupère l'instance globale de métriques

    Args:
        db_path: Chemin vers la base de données (optionnel)

    Returns:
        Instance TestMetrics
    """
    global _metrics_instance

    if _metrics_instance is None:
        _metrics_instance = TestMetrics(db_path=db_path)

    return _metrics_instance


def reset_test_metrics():
    """Réinitialise l'instance de métriques (utile pour tests)"""
    global _metrics_instance
    _metrics_instance = None
