#!/usr/bin/env python3
"""
Script pour vérifier les régressions de couverture

Compare la couverture actuelle avec la dernière couverture enregistrée
et échoue si la couverture a diminué de plus que le seuil configuré.

Usage:
    python scripts/check_coverage_regression.py
    python scripts/check_coverage_regression.py --threshold 2.0
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional


def load_current_coverage() -> Optional[Dict[str, Any]]:
    """
    Charge les données de couverture actuelles depuis coverage.json

    Returns:
        Dict avec les données de couverture ou None si non disponible
    """
    coverage_file = Path("coverage.json")

    if not coverage_file.exists():
        print("⚠️  No coverage.json found. Run tests with coverage first.")
        return None

    with open(coverage_file, "r") as f:
        data = json.load(f)

    # Extract total coverage percentage
    if "totals" in data:
        return {
            "coverage_percentage": data["totals"]["percent_covered"],
            "lines_covered": data["totals"]["covered_lines"],
            "lines_missing": data["totals"]["missing_lines"],
            "total_lines": data["totals"]["num_statements"],
        }

    return None


def load_previous_coverage() -> Optional[Dict[str, Any]]:
    """
    Charge la dernière couverture enregistrée depuis eval/metrics/test_metrics.db

    Returns:
        Dict avec les données de couverture précédente ou None
    """
    try:
        import sqlite3
        from eval.metrics import get_test_metrics

        metrics = get_test_metrics()
        recent_runs = metrics.get_recent_runs(limit=1)

        if not recent_runs:
            print("ℹ️  No previous test runs found in database.")
            return None

        latest = recent_runs[0]
        return {
            "coverage_percentage": latest["coverage_percentage"],
            "lines_covered": latest["coverage_lines_covered"],
            "lines_missing": latest["coverage_lines_missing"],
            "total_lines": latest["coverage_lines_total"],
            "timestamp": latest["timestamp"],
            "commit_hash": latest["commit_hash"],
        }

    except Exception as e:
        print(f"⚠️  Could not load previous coverage: {e}")
        return None


def check_regression(
    current: Dict[str, Any],
    previous: Dict[str, Any],
    threshold: float = 2.0,
) -> tuple[bool, Optional[str]]:
    """
    Vérifie s'il y a une régression de couverture

    Args:
        current: Données de couverture actuelles
        previous: Données de couverture précédentes
        threshold: Seuil de régression en pourcentage (default: 2.0%)

    Returns:
        tuple: (passed, message)
            - passed: True si pas de régression
            - message: Message d'erreur si régression détectée
    """
    current_pct = current["coverage_percentage"]
    previous_pct = previous["coverage_percentage"]

    diff = current_pct - previous_pct

    if diff < -threshold:
        # Régression détectée
        message = f"""
❌ COVERAGE REGRESSION DETECTED!

Previous coverage: {previous_pct:.2f}%
Current coverage:  {current_pct:.2f}%
Difference:        {diff:.2f}% (threshold: -{threshold:.2f}%)

Lines covered:  {current['lines_covered']} (was {previous['lines_covered']})
Lines missing:  {current['lines_missing']} (was {previous['lines_missing']})
Total lines:    {current['total_lines']} (was {previous['total_lines']})

Previous commit: {previous.get('commit_hash', 'unknown')[:8]}
Previous date:   {previous.get('timestamp', 'unknown')}

To fix this regression:
1. Add tests to cover missing lines
2. Review code changes that reduced coverage
3. Run: pytest --cov --cov-report=html
4. Open htmlcov/index.html to see uncovered lines
"""
        return False, message

    elif diff < 0:
        # Légère diminution mais dans le seuil
        print(f"⚠️  Coverage decreased by {abs(diff):.2f}% (within threshold)")
        print(f"   Previous: {previous_pct:.2f}% → Current: {current_pct:.2f}%")
        return True, None

    else:
        # Amélioration ou stable
        print(f"✓ Coverage check passed: {current_pct:.2f}%")
        if diff > 0:
            print(f"   Improved by {diff:.2f}% from {previous_pct:.2f}%")
        return True, None


def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(
        description="Check for coverage regression",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=2.0,
        help="Coverage regression threshold in percentage (default: 2.0)",
    )
    parser.add_argument(
        "--skip-if-no-previous",
        action="store_true",
        help="Skip check if no previous coverage data exists",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("📊 COVERAGE REGRESSION CHECK")
    print("=" * 70)

    # Load current coverage
    current = load_current_coverage()
    if not current:
        print("❌ Cannot load current coverage data")
        sys.exit(1)

    print(f"Current coverage: {current['coverage_percentage']:.2f}%")

    # Load previous coverage
    previous = load_previous_coverage()
    if not previous:
        if args.skip_if_no_previous:
            print("ℹ️  No previous coverage data, skipping regression check")
            sys.exit(0)
        else:
            print("⚠️  No previous coverage to compare against")
            print("   This is likely the first run. Coverage check passed.")
            sys.exit(0)

    print(f"Previous coverage: {previous['coverage_percentage']:.2f}%")

    # Check regression
    passed, message = check_regression(current, previous, args.threshold)

    print("=" * 70)

    if not passed:
        print(message)
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
