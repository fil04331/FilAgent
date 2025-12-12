"""
Centralized Benchmark Runner for FilAgent

Orchestre l'execution de tous les benchmarks:
- HumanEval
- MBPP
- SWE-bench
- Custom FilAgent benchmarks (Compliance, HTN, Tools)

Usage:
    python eval/runner.py --all
    python eval/runner.py --benchmark humaneval
    python eval/runner.py --benchmark humaneval,mbpp
    python eval/runner.py --custom-only
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Type, Union

# Import benchmarks
from eval.humaneval import HumanEvalHarness
from eval.mbpp import MBPPHarness
from eval.benchmarks.swe_bench.harness import SWEBenchHarness
from eval.benchmarks.custom.compliance.harness import ComplianceHarness
from eval.benchmarks.custom.htn_planning.harness import HTNPlanningHarness
from eval.benchmarks.custom.tool_orchestration.harness import ToolOrchestrationHarness
from eval.base import BenchmarkHarness, BenchmarkReport

# Import config
from runtime.config import get_config


# Type aliases for strict typing
MetricValue = Union[str, int, float, bool]
BenchmarkResults = Dict[str, Union[str, int, float, bool, Dict[str, MetricValue], List[str]]]
AggregateReport = Dict[str, Union[str, int, float, bool, Dict[str, BenchmarkResults]]]
TargetResults = Dict[str, bool]
SummaryStats = Dict[str, Union[int, float]]
EvalConfig = Dict[str, Union[str, int, float, bool, Dict[str, MetricValue]]]
AgentCallback = Callable[[str], str]
HarnessType = Type[BenchmarkHarness]


class BenchmarkRunner:
    """
    Centralized runner pour tous les benchmarks FilAgent
    """

    def __init__(self, output_dir: str = "eval/runs", reports_dir: str = "eval/reports") -> None:
        self.output_dir = Path(output_dir)
        self.reports_dir = Path(reports_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        # Load config
        try:
            config = get_config()
            if hasattr(config, 'get') and callable(config.get):
                self.eval_config: EvalConfig = config.get('eval', {})
            else:
                self.eval_config = {}
        except (ImportError, AttributeError, RuntimeError) as e:
            print(f"Warning: Failed to load config: {e}")
            self.eval_config = {}

        # Available benchmarks
        self.benchmarks: Dict[str, HarnessType] = {
            'humaneval': HumanEvalHarness,
            'mbpp': MBPPHarness,
            'swe_bench': SWEBenchHarness,
            'compliance': ComplianceHarness,
            'htn_planning': HTNPlanningHarness,
            'tool_orchestration': ToolOrchestrationHarness,
        }

    def run_benchmark(
        self,
        benchmark_name: str,
        agent_callback: AgentCallback,
        num_tasks: Optional[int] = None,
        k: int = 1,
        verbose: bool = False
    ) -> BenchmarkResults:
        """
        Executer un benchmark specifique

        Args:
            benchmark_name: Nom du benchmark
            agent_callback: Fonction callback agent
            num_tasks: Nombre de taches (None = toutes)
            k: pass@k parametre
            verbose: Mode verbose

        Returns:
            Resultats du benchmark
        """
        if benchmark_name not in self.benchmarks:
            raise ValueError(f"Unknown benchmark: {benchmark_name}")

        print(f"\n{'='*60}")
        print(f"Running {benchmark_name} benchmark")
        print(f"{'='*60}\n")

        # Instantiate harness
        HarnessClass = self.benchmarks[benchmark_name]
        harness = HarnessClass()

        # Run benchmark
        try:
            results: BenchmarkReport = harness.run_benchmark(
                agent_callback=agent_callback,
                num_tasks=num_tasks,
                k=k,
                verbose=verbose
            )

            # Save report
            harness.save_report(results, str(self.reports_dir))

            # Convert to BenchmarkResults
            return dict(results)

        except (RuntimeError, ValueError, OSError) as e:
            print(f"Error running {benchmark_name}: {e}")
            import traceback
            traceback.print_exc()
            return {
                'benchmark': benchmark_name,
                'error': str(e),
                'success': False
            }

    def run_all_benchmarks(
        self,
        agent_callback: AgentCallback,
        num_tasks_per_benchmark: Optional[int] = None,
        skip_benchmarks: Optional[List[str]] = None,
        verbose: bool = False
    ) -> AggregateReport:
        """
        Executer tous les benchmarks

        Args:
            agent_callback: Fonction callback agent
            num_tasks_per_benchmark: Limiter le nombre de taches
            skip_benchmarks: Benchmarks a ignorer
            verbose: Mode verbose

        Returns:
            Resultats agreges de tous les benchmarks
        """
        skip_benchmarks = skip_benchmarks or []
        all_results: Dict[str, BenchmarkResults] = {}

        print(f"\n{'='*60}")
        print("Running ALL FilAgent Benchmarks")
        print(f"{'='*60}\n")

        for benchmark_name in self.benchmarks.keys():
            if benchmark_name in skip_benchmarks:
                print(f"Skipping {benchmark_name}")
                continue

            results = self.run_benchmark(
                benchmark_name=benchmark_name,
                agent_callback=agent_callback,
                num_tasks=num_tasks_per_benchmark,
                verbose=verbose
            )

            all_results[benchmark_name] = results

        # Generate aggregate report
        aggregate_report = self._generate_aggregate_report(all_results)

        # Save aggregate report
        self._save_aggregate_report(aggregate_report)

        return aggregate_report

    def run_custom_benchmarks(
        self,
        agent_callback: AgentCallback,
        verbose: bool = False
    ) -> AggregateReport:
        """
        Executer uniquement les benchmarks custom FilAgent

        Args:
            agent_callback: Fonction callback agent
            verbose: Mode verbose

        Returns:
            Resultats des benchmarks custom
        """
        custom_benchmarks = ['compliance', 'htn_planning', 'tool_orchestration']
        all_results: Dict[str, BenchmarkResults] = {}

        print(f"\n{'='*60}")
        print("Running Custom FilAgent Benchmarks")
        print(f"{'='*60}\n")

        for benchmark_name in custom_benchmarks:
            results = self.run_benchmark(
                benchmark_name=benchmark_name,
                agent_callback=agent_callback,
                verbose=verbose
            )
            all_results[benchmark_name] = results

        # Generate report
        report = self._generate_aggregate_report(all_results)
        self._save_aggregate_report(report, prefix="custom")

        return report

    def _generate_aggregate_report(self, results: Dict[str, BenchmarkResults]) -> AggregateReport:
        """
        Generer un rapport agrege de tous les benchmarks

        Args:
            results: Resultats de tous les benchmarks

        Returns:
            Rapport agrege
        """
        aggregate: AggregateReport = {
            'timestamp': datetime.now().isoformat(),
            'total_benchmarks': len(results),
            'benchmarks': results,
            'summary': {},
        }

        # Calculate summary statistics
        total_tasks = 0
        total_passed = 0
        total_failed = 0

        for benchmark_name, result in results.items():
            success = result.get('success', True)
            if success:
                tasks = result.get('total_tasks')
                if tasks is not None and isinstance(tasks, (int, float)):
                    total_tasks += int(tasks)

                passed_k = result.get('passed_at_k')
                passed_1 = result.get('passed_at_1')
                passed_val = passed_k if passed_k is not None else passed_1
                if passed_val is not None and isinstance(passed_val, (int, float)):
                    total_passed += int(passed_val)

                failed = result.get('failed')
                if failed is not None and isinstance(failed, (int, float)):
                    total_failed += int(failed)

        summary: SummaryStats = {
            'total_tasks': total_tasks,
            'total_passed': total_passed,
            'total_failed': total_failed,
            'overall_pass_rate': total_passed / total_tasks if total_tasks > 0 else 0.0,
        }
        aggregate['summary'] = summary

        # Check against targets
        aggregate['targets_met'] = self._check_targets(results)

        return aggregate

    def _check_targets(self, results: Dict[str, BenchmarkResults]) -> TargetResults:
        """
        Verifier si les seuils cibles sont atteints

        Uses config/eval_targets.yaml for thresholds
        """
        targets_met: TargetResults = {}

        # Load targets from config
        try:
            with open('config/eval_targets.yaml') as f:
                import yaml
                targets_config = yaml.safe_load(f)
                benchmarks_config: Dict[str, Dict[str, float]] = targets_config.get('benchmarks', {})
        except (OSError, yaml.YAMLError):
            benchmarks_config = {}

        # Check HumanEval
        if 'humaneval' in results:
            he_result = results['humaneval']
            target = benchmarks_config.get('humaneval', {}).get('pass_at_1', 0.65)
            actual = he_result.get('pass_at_1', 0)
            actual_val = float(actual) if isinstance(actual, (int, float)) else 0.0
            targets_met['humaneval_pass@1'] = actual_val >= target

        # Check MBPP
        if 'mbpp' in results:
            mbpp_result = results['mbpp']
            target = benchmarks_config.get('mbpp', {}).get('pass_at_1', 0.60)
            actual = mbpp_result.get('pass_at_1', 0)
            actual_val = float(actual) if isinstance(actual, (int, float)) else 0.0
            targets_met['mbpp_pass@1'] = actual_val >= target

        # Check compliance (should be 100%)
        if 'compliance' in results:
            comp_result = results['compliance']
            actual = comp_result.get('pass_at_1', 0)
            actual_val = float(actual) if isinstance(actual, (int, float)) else 0.0
            targets_met['compliance_100%'] = actual_val >= 1.0

        return targets_met

    def _save_aggregate_report(self, report: AggregateReport, prefix: str = "all") -> None:
        """
        Sauvegarder le rapport agrege

        Args:
            report: Rapport agrege
            prefix: Prefixe du nom de fichier
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_benchmarks_{timestamp}.json"
        filepath = self.reports_dir / filename

        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\n{'='*60}")
        print(f"Aggregate report saved: {filepath}")
        print(f"{'='*60}\n")

        # Print summary
        self._print_summary(report)

        # Save as latest
        latest_path = self.reports_dir / f"{prefix}_latest.json"
        with open(latest_path, 'w') as f:
            json.dump(report, f, indent=2)

    def _print_summary(self, report: AggregateReport) -> None:
        """Afficher un resume du rapport"""
        print("\nBenchmark Summary")
        print(f"{'='*60}")

        summary = report.get('summary')
        if summary is not None and isinstance(summary, dict):
            print(f"Total Tasks: {summary.get('total_tasks', 0)}")
            print(f"Passed: {summary.get('total_passed', 0)}")
            print(f"Failed: {summary.get('total_failed', 0)}")
            pass_rate = summary.get('overall_pass_rate', 0)
            pass_rate_val = float(pass_rate) if isinstance(pass_rate, (int, float)) else 0.0
            print(f"Overall Pass Rate: {pass_rate_val*100:.1f}%")

        # Per-benchmark results
        print(f"\nPer-Benchmark Results")
        print(f"{'='*60}")

        benchmarks = report.get('benchmarks')
        if benchmarks is not None and isinstance(benchmarks, dict):
            for name, result in benchmarks.items():
                if not isinstance(result, dict):
                    continue
                success = result.get('success', True)
                if success:
                    pass_at_1 = result.get('pass_at_1')
                    pass_at_k = result.get('pass_at_k')
                    pass_rate = pass_at_1 if pass_at_1 is not None else pass_at_k
                    pass_rate_val = float(pass_rate) if pass_rate is not None and isinstance(pass_rate, (int, float)) else 0.0

                    passed_at_k = result.get('passed_at_k', 0)
                    passed_val = int(passed_at_k) if isinstance(passed_at_k, (int, float)) else 0

                    total_tasks = result.get('total_tasks', 0)
                    total_val = int(total_tasks) if isinstance(total_tasks, (int, float)) else 0

                    print(f"{name:20s}: {pass_rate_val*100:5.1f}% ({passed_val}/{total_val})")
                else:
                    error = result.get('error', 'Unknown')
                    print(f"{name:20s}: ERROR - {error}")

        # Targets
        targets = report.get('targets_met')
        if targets is not None and isinstance(targets, dict):
            print(f"\nTargets Met")
            print(f"{'='*60}")
            for target, met in targets.items():
                status = "OK" if met else "FAIL"
                print(f"{status} {target}")


def create_agent_callback() -> AgentCallback:
    """
    Creer un callback agent pour les benchmarks

    Cette fonction devrait retourner une fonction qui prend un prompt
    et retourne une reponse de l'agent.

    Pour les tests, on utilise un mock simple.
    """
    # Import agent
    try:
        from runtime.agent import Agent
        agent = Agent()

        def callback(prompt: str) -> str:
            """Agent callback"""
            try:
                result = agent.run(prompt)
                if isinstance(result, dict):
                    response = result.get('response', '')
                    return str(response) if response is not None else ''
                return str(result) if result is not None else ''
            except (RuntimeError, ValueError) as e:
                return f"ERROR: {e}"

        return callback

    except (ImportError, RuntimeError) as e:
        print(f"Warning: Could not load agent, using mock: {e}")

        # Mock callback for testing
        def mock_callback(prompt: str) -> str:
            """Mock agent callback"""
            return "Mock response: I understand the task but this is a test response."

        return mock_callback


def main() -> None:
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Run FilAgent benchmarks")

    parser.add_argument(
        '--benchmark',
        type=str,
        help='Specific benchmark to run (comma-separated for multiple)',
        default=None
    )

    parser.add_argument(
        '--all',
        action='store_true',
        help='Run all benchmarks'
    )

    parser.add_argument(
        '--custom-only',
        action='store_true',
        help='Run only custom FilAgent benchmarks'
    )

    parser.add_argument(
        '--num-tasks',
        type=int,
        default=None,
        help='Number of tasks to run per benchmark (None = all)'
    )

    parser.add_argument(
        '--k',
        type=int,
        default=1,
        help='pass@k parameter (default: 1)'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output'
    )

    args = parser.parse_args()

    # Create runner
    runner = BenchmarkRunner()

    # Create agent callback
    agent_callback = create_agent_callback()

    # Run benchmarks
    if args.all:
        runner.run_all_benchmarks(
            agent_callback=agent_callback,
            num_tasks_per_benchmark=args.num_tasks,
            verbose=args.verbose
        )

    elif args.custom_only:
        runner.run_custom_benchmarks(
            agent_callback=agent_callback,
            verbose=args.verbose
        )

    elif args.benchmark:
        benchmarks = [b.strip() for b in args.benchmark.split(',')]
        for benchmark_name in benchmarks:
            runner.run_benchmark(
                benchmark_name=benchmark_name,
                agent_callback=agent_callback,
                num_tasks=args.num_tasks,
                k=args.k,
                verbose=args.verbose
            )

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
