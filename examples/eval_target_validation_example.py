#!/usr/bin/env python3
"""
Example script demonstrating the data-driven evaluation target system

This script shows how to:
1. Load evaluation targets from YAML configuration
2. Run benchmarks and collect results
3. Validate results against configured targets
4. Generate a comprehensive report
"""

import sys
from pathlib import Path

# Add parent directory to path to import eval modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from eval.target_validator import (
    EvaluationTargetLoader,
    TargetValidator,
    validate_from_config
)


def example_benchmark_results():
    """
    Example benchmark results structure
    
    In a real scenario, these would come from running actual benchmarks
    """
    return {
        "humaneval": {
            "pass_at_1": 0.67,
            "pass_at_10": 0.88,
            "avg_latency_ms": 450
        },
        "mbpp": {
            "pass_at_1": 0.62,
            "pass_at_10": 0.83,
            "avg_latency_ms": 380
        },
        "compliance": {
            "decision_record_coverage": 0.98,
            "provenance_integrity": 100,
            "pii_masking_rate": 100,
            "audit_trail_completeness": 0.95
        },
        "agent_tasks": {
            "file_navigation": 0.85,
            "code_editing": 0.78,
            "planning": 0.72,
            "tool_usage": 0.82
        }
    }


def main():
    """Main example execution"""
    print("=" * 80)
    print("DATA-DRIVEN EVALUATION TARGET VALIDATION EXAMPLE")
    print("=" * 80)
    
    # 1. Load targets from configuration
    print("\n1. Loading evaluation targets from config/eval_targets.yaml...")
    try:
        targets = EvaluationTargetLoader.load_targets("config/eval_targets.yaml")
        print(f"   ✓ Loaded {len(targets)} targets")
        
        # Display targets
        print("\n   Configured targets:")
        for target in targets[:5]:  # Show first 5
            print(f"   - {target.benchmark}.{target.metric} {target.operator} {target.value}")
        if len(targets) > 5:
            print(f"   ... and {len(targets) - 5} more")
    
    except Exception as e:
        print(f"   ✗ Failed to load targets: {e}")
        return 1
    
    # 2. Get benchmark results (simulated here)
    print("\n2. Collecting benchmark results...")
    benchmark_results = example_benchmark_results()
    print(f"   ✓ Collected results from {len(benchmark_results)} benchmarks")
    
    # 3. Validate against targets
    print("\n3. Validating results against targets...")
    validator = TargetValidator(targets)
    validation_results = validator.validate(benchmark_results)
    
    # 4. Display report
    validator.print_report(validation_results)
    
    # 5. Return exit code based on results
    if validation_results['passed']:
        print("✅ All evaluation targets met!")
        return 0
    else:
        print("❌ Some evaluation targets not met")
        return 1


def example_simple_usage():
    """
    Simplified usage example using convenience function
    """
    print("\n" + "=" * 80)
    print("SIMPLIFIED USAGE EXAMPLE")
    print("=" * 80 + "\n")
    
    # One-liner validation
    results = validate_from_config(
        benchmark_results=example_benchmark_results(),
        config_path="config/eval_targets.yaml"
    )
    
    print(f"Pass Rate: {results['pass_rate']*100:.1f}%")
    print(f"Passed: {results['passed_count']}/{results['total_count']} targets")
    
    return 0 if results['passed'] else 1


if __name__ == "__main__":
    import sys
    
    # Run main example
    exit_code = main()
    
    # Also run simplified example
    example_simple_usage()
    
    sys.exit(exit_code)
