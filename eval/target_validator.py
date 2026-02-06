"""
Data-driven evaluation target validation system

This module provides a framework for validating benchmark results against
configured targets defined in YAML files. It supports flexible comparison
operators and multiple benchmark types.
"""

import os
import yaml
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
from enum import Enum


class ComparisonOperator(str, Enum):
    """Supported comparison operators"""

    GREATER_EQUAL = ">="
    GREATER = ">"
    EQUAL = "=="
    LESS_EQUAL = "<="
    LESS = "<"


@dataclass
class EvaluationTarget:
    """
    Evaluation target configuration

    Attributes:
        benchmark: Benchmark name (e.g., "humaneval", "compliance")
        metric: Metric name (e.g., "pass_rate", "provenance_integrity")
        operator: Comparison operator (>=, >, ==, <=, <)
        value: Target value to compare against
        description: Human-readable description
    """

    benchmark: str
    metric: str
    operator: str
    value: float
    description: str = ""

    def __post_init__(self):
        """Validate the target configuration"""
        if self.operator not in [op.value for op in ComparisonOperator]:
            raise ValueError(
                f"Invalid operator: {self.operator}. Must be one of {[op.value for op in ComparisonOperator]}"
            )


class EvaluationTargetLoader:
    """Load and manage evaluation targets from configuration files"""

    @staticmethod
    def load_targets(config_path: str = "config/eval_targets.yaml") -> List[EvaluationTarget]:
        """
        Load evaluation targets from YAML configuration

        Expected YAML format:
        ```yaml
        targets:
          - benchmark: humaneval
            metric: pass_rate
            operator: ">="
            value: 65
            description: "HumanEval pass@1 baseline"

          - benchmark: compliance
            metric: provenance_integrity
            operator: "=="
            value: 100
            description: "Provenance tests must pass 100%"
        ```

        Args:
            config_path: Path to the YAML configuration file

        Returns:
            List of EvaluationTarget objects

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config format is invalid
            yaml.YAMLError: If YAML parsing fails
        """
        config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Invalid YAML format in {config_path}: {e}")

        if not config:
            raise ValueError(f"Config file is empty: {config_path}")

        # Support both "targets" list and benchmark-structured format
        targets = []

        # Check for explicit targets list
        if "targets" in config:
            for target_dict in config["targets"]:
                target = EvaluationTargetLoader._parse_target(target_dict)
                targets.append(target)

        # Parse from eval_targets.yaml structure (benchmarks section)
        elif "benchmarks" in config:
            targets = EvaluationTargetLoader._parse_benchmarks(config["benchmarks"])

        # Parse from acceptance_criteria
        if "acceptance_criteria" in config:
            targets.extend(EvaluationTargetLoader._parse_criteria(config["acceptance_criteria"]))

        if not targets:
            raise ValueError(f"No targets found in config: {config_path}")

        return targets

    @staticmethod
    def _parse_target(target_dict: Dict[str, Any]) -> EvaluationTarget:
        """Parse a single target dictionary"""
        required_fields = ["benchmark", "metric", "operator", "value"]
        missing = [f for f in required_fields if f not in target_dict]

        if missing:
            raise ValueError(f"Missing required fields in target: {missing}")

        return EvaluationTarget(
            benchmark=target_dict["benchmark"],
            metric=target_dict["metric"],
            operator=target_dict["operator"],
            value=float(target_dict["value"]),
            description=target_dict.get("description", ""),
        )

    @staticmethod
    def _parse_benchmarks(benchmarks: Dict[str, Any]) -> List[EvaluationTarget]:
        """Parse targets from benchmarks section of eval_targets.yaml"""
        targets = []

        for benchmark_name, benchmark_config in benchmarks.items():
            if not isinstance(benchmark_config, dict):
                continue

            # Skip if not enabled
            if not benchmark_config.get("enabled", True):
                continue

            # Extract metrics with thresholds
            for metric, value in benchmark_config.items():
                if metric in [
                    "enabled",
                    "time_limit_seconds",
                    "temperature",
                    "max_tokens",
                    "tasks_to_run",
                ]:
                    continue

                if isinstance(value, (int, float)):
                    targets.append(
                        EvaluationTarget(
                            benchmark=benchmark_name,
                            metric=metric,
                            operator=">=",
                            value=float(value),
                            description=f"{benchmark_name} {metric} target",
                        )
                    )

        return targets

    @staticmethod
    def _parse_criteria(criteria: Dict[str, Any]) -> List[EvaluationTarget]:
        """Parse targets from acceptance_criteria section"""
        targets = []

        # This is for future expansion - parse complex criteria expressions
        # For now, just extract simple metrics

        return targets


class TargetValidator:
    """Validate benchmark results against configured targets"""

    def __init__(self, targets: List[EvaluationTarget]):
        """
        Initialize validator with targets

        Args:
            targets: List of evaluation targets to validate against
        """
        self.targets = targets

    def validate(self, benchmark_results: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
        """
        Validate benchmark results against all targets

        Args:
            benchmark_results: Dict mapping benchmark names to their metric results
                Example: {
                    "humaneval": {"pass_rate": 0.67, "latency_ms": 450},
                    "compliance": {"provenance_integrity": 100}
                }

        Returns:
            Validation results with pass/fail status for each target
        """
        results = []

        for target in self.targets:
            current_value = self._get_metric_value(
                benchmark_results, target.benchmark, target.metric
            )
            passed = self._evaluate_comparison(current_value, target.operator, target.value)

            results.append(
                {
                    "target": target,
                    "current_value": current_value,
                    "target_value": target.value,
                    "operator": target.operator,
                    "passed": passed,
                    "description": target.description,
                }
            )

        # Calculate summary
        passed_count = sum(1 for r in results if r["passed"])
        total_count = len(results)

        return {
            "passed": passed_count == total_count,
            "passed_count": passed_count,
            "total_count": total_count,
            "pass_rate": passed_count / total_count if total_count > 0 else 0,
            "results": results,
        }

    def _get_metric_value(
        self, benchmark_results: Dict[str, Dict[str, float]], benchmark: str, metric: str
    ) -> Optional[float]:
        """Get the current value for a specific benchmark metric"""
        if benchmark not in benchmark_results:
            return None

        benchmark_data = benchmark_results[benchmark]
        return benchmark_data.get(metric)

    def _evaluate_comparison(self, current: Optional[float], operator: str, target: float) -> bool:
        """Evaluate a comparison operation"""
        if current is None:
            return False

        if operator == ">=":
            return current >= target
        elif operator == ">":
            return current > target
        elif operator == "==":
            return current == target
        elif operator == "<=":
            return current <= target
        elif operator == "<":
            return current < target
        else:
            raise ValueError(f"Unknown operator: {operator}")

    def print_report(self, validation_results: Dict[str, Any]) -> None:
        """Print a formatted validation report"""
        print("\n" + "=" * 80)
        print("EVALUATION TARGET VALIDATION REPORT")
        print("=" * 80)

        for result in validation_results["results"]:
            target = result["target"]
            status = "✅ PASS" if result["passed"] else "❌ FAIL"

            print(f"\n{status}: {target.description or f'{target.benchmark}.{target.metric}'}")
            print(f"  Target: {target.metric} {target.operator} {target.value}")

            if result["current_value"] is not None:
                print(f"  Current: {result['current_value']}")
            else:
                print(f"  Current: N/A (metric not available)")

        print("\n" + "-" * 80)
        print(
            f"SUMMARY: {validation_results['passed_count']}/{validation_results['total_count']} targets passed"
        )
        print(f"Pass Rate: {validation_results['pass_rate']*100:.1f}%")
        print("=" * 80 + "\n")


def validate_from_config(
    benchmark_results: Dict[str, Dict[str, float]], config_path: str = "config/eval_targets.yaml"
) -> Dict[str, Any]:
    """
    Convenience function to load targets from config and validate results

    Args:
        benchmark_results: Benchmark results to validate
        config_path: Path to evaluation targets config

    Returns:
        Validation results
    """
    targets = EvaluationTargetLoader.load_targets(config_path)
    validator = TargetValidator(targets)
    return validator.validate(benchmark_results)
