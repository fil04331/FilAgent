#!/usr/bin/env python3
"""
Script pour générer les badges de couverture et de tests

Génère des badges shields.io pour:
- Couverture de code
- Statut des tests
- Nombre de tests

Usage:
    python scripts/generate_badges.py
    python scripts/generate_badges.py --output badges.json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any


def load_coverage_data() -> Dict[str, Any]:
    """
    Charge les données de couverture depuis coverage.json

    Returns:
        Dict avec les données de couverture
    """
    coverage_file = Path("coverage.json")

    if not coverage_file.exists():
        print("⚠️  No coverage.json found. Run tests with coverage first.")
        return {"coverage_percentage": 0.0, "status": "unknown"}

    with open(coverage_file, "r") as f:
        data = json.load(f)

    if "totals" in data:
        return {
            "coverage_percentage": round(data["totals"]["percent_covered"], 2),
            "lines_covered": data["totals"]["covered_lines"],
            "lines_missing": data["totals"]["missing_lines"],
            "total_lines": data["totals"]["num_statements"],
            "status": "measured",
        }

    return {"coverage_percentage": 0.0, "status": "unknown"}


def load_test_metrics() -> Dict[str, Any]:
    """
    Charge les métriques de tests depuis la base de données

    Returns:
        Dict avec les métriques de tests
    """
    try:
        from eval.metrics import get_test_metrics

        metrics = get_test_metrics()
        recent_runs = metrics.get_recent_runs(limit=1)

        if not recent_runs:
            return {
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "status": "no_data",
            }

        latest = recent_runs[0]
        return {
            "total_tests": latest["total_tests"],
            "passed": latest["passed"],
            "failed": latest["failed"],
            "skipped": latest["skipped"],
            "errors": latest["errors"],
            "duration_seconds": latest["duration_seconds"],
            "status": "passing" if latest["failed"] == 0 and latest["errors"] == 0 else "failing",
        }

    except Exception as e:
        print(f"⚠️  Could not load test metrics: {e}")
        return {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "status": "error",
        }


def get_coverage_color(percentage: float) -> str:
    """
    Détermine la couleur du badge selon le pourcentage de couverture

    Args:
        percentage: Pourcentage de couverture

    Returns:
        Couleur shields.io (red, yellow, green, brightgreen)
    """
    if percentage >= 90:
        return "brightgreen"
    elif percentage >= 80:
        return "green"
    elif percentage >= 70:
        return "yellow"
    elif percentage >= 50:
        return "orange"
    else:
        return "red"


def get_test_status_color(status: str) -> str:
    """
    Détermine la couleur du badge selon le statut des tests

    Args:
        status: Statut (passing, failing, error, no_data)

    Returns:
        Couleur shields.io
    """
    colors = {
        "passing": "brightgreen",
        "failing": "red",
        "error": "orange",
        "no_data": "lightgrey",
    }
    return colors.get(status, "lightgrey")


def generate_badges() -> Dict[str, str]:
    """
    Génère les URLs des badges shields.io

    Returns:
        Dict avec les URLs des badges
    """
    coverage = load_coverage_data()
    tests = load_test_metrics()

    coverage_pct = coverage["coverage_percentage"]
    coverage_color = get_coverage_color(coverage_pct)

    test_status = tests["status"]
    test_color = get_test_status_color(test_status)

    # URLs shields.io
    badges = {
        "coverage": f"https://img.shields.io/badge/coverage-{coverage_pct}%25-{coverage_color}",
        "tests": f"https://img.shields.io/badge/tests-{test_status}-{test_color}",
        "test_count": f"https://img.shields.io/badge/tests-{tests['total_tests']}_total-blue",
        "passed": f"https://img.shields.io/badge/passed-{tests['passed']}-brightgreen",
        "python": "https://img.shields.io/badge/python-3.10%2B-blue",
        "license": "https://img.shields.io/badge/license-MIT-blue",
    }

    # Markdown snippets
    markdown = {
        "coverage": f"![Coverage]({badges['coverage']})",
        "tests": f"![Tests]({badges['tests']})",
        "test_count": f"![Test Count]({badges['test_count']})",
        "passed": f"![Passed]({badges['passed']})",
        "python": f"![Python]({badges['python']})",
        "license": f"![License]({badges['license']})",
    }

    # Full badge line for README
    badge_line = " ".join([
        markdown["coverage"],
        markdown["tests"],
        markdown["test_count"],
        markdown["python"],
        markdown["license"],
    ])

    return {
        "urls": badges,
        "markdown": markdown,
        "badge_line": badge_line,
        "metadata": {
            "coverage_percentage": coverage_pct,
            "coverage_status": coverage["status"],
            "test_status": test_status,
            "total_tests": tests["total_tests"],
            "passed_tests": tests["passed"],
            "failed_tests": tests["failed"],
        },
    }


def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(
        description="Generate coverage and test badges",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file for badge data (JSON format)",
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Print markdown badge line",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("🏷️  BADGE GENERATION")
    print("=" * 70)

    badges = generate_badges()

    # Print summary
    print("\nMetadata:")
    print(f"  Coverage: {badges['metadata']['coverage_percentage']:.2f}%")
    print(f"  Tests: {badges['metadata']['test_status']}")
    print(f"  Total: {badges['metadata']['total_tests']}")
    print(f"  Passed: {badges['metadata']['passed_tests']}")
    print(f"  Failed: {badges['metadata']['failed_tests']}")

    # Print badge line if requested
    if args.markdown:
        print("\nMarkdown badge line:")
        print(badges["badge_line"])

    # Save to file if requested
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(badges, f, indent=2)

        print(f"\n✓ Badge data saved to {output_path}")

    print("=" * 70)


if __name__ == "__main__":
    main()
