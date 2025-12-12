"""
Metrics Aggregation and Dashboard for FilAgent Benchmarks

Collecte, agrege et visualise les metriques de performance:
- Pass rates par benchmark
- Temps d'execution moyens
- Trends historiques
- Comparaison avec targets
- Detection de regressions
"""
from __future__ import annotations

import json
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union


# Type aliases for strict typing
MetricValue = Union[str, int, float, bool, None]
TrendData = Dict[str, Union[str, int, float, bool, List[float], List[str], None]]
DashboardData = Dict[str, Union[str, int, float, Dict[str, TrendData], None]]
ReportData = Dict[str, Union[str, int, float, bool, List[str], Dict[str, MetricValue], None]]
AggregateStats = Dict[str, Union[int, float, None]]
RegressionInfo = Dict[str, Union[str, float, None]]


class MetricsAggregator:
    """
    Agregateur de metriques pour benchmarks

    Analyse les rapports historiques et genere des statistiques
    """

    def __init__(self, reports_dir: str = "eval/reports") -> None:
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def collect_historical_data(
        self,
        days: int = 30,
        benchmark_name: Optional[str] = None
    ) -> List[ReportData]:
        """
        Collecter les donnees historiques

        Args:
            days: Nombre de jours a analyser
            benchmark_name: Filtrer par benchmark (None = tous)

        Returns:
            Liste de rapports historiques
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        historical_data: List[ReportData] = []

        # Find all report files
        if benchmark_name:
            pattern = f"{benchmark_name}_*.json"
        else:
            pattern = "*.json"

        for report_file in self.reports_dir.glob(pattern):
            # Skip "latest" files
            if 'latest' in report_file.name:
                continue

            # Check file modification time
            file_mtime = datetime.fromtimestamp(report_file.stat().st_mtime)
            if file_mtime < cutoff_date:
                continue

            # Load report
            try:
                with open(report_file) as f:
                    report: ReportData = json.load(f)
                    report['_file'] = report_file.name
                    report['_mtime'] = file_mtime.isoformat()
                    historical_data.append(report)
            except (json.JSONDecodeError, OSError) as e:
                print(f"Warning: Could not load {report_file}: {e}")

        # Sort by timestamp
        historical_data.sort(key=lambda x: str(x.get('timestamp', '')))

        return historical_data

    def compute_trend(
        self,
        benchmark_name: str,
        metric_name: str = 'pass_at_1',
        days: int = 30
    ) -> TrendData:
        """
        Calculer la tendance pour une metrique

        Args:
            benchmark_name: Nom du benchmark
            metric_name: Nom de la metrique (ex: 'pass_at_1')
            days: Periode d'analyse

        Returns:
            Statistiques de tendance
        """
        data = self.collect_historical_data(days=days, benchmark_name=benchmark_name)

        if not data:
            return {
                'benchmark': benchmark_name,
                'metric': metric_name,
                'error': 'No historical data found'
            }

        # Extract metric values
        values: List[float] = []
        timestamps: List[str] = []

        for report in data:
            value = report.get(metric_name)
            if value is not None and isinstance(value, (int, float)):
                values.append(float(value))
                timestamp = report.get('timestamp')
                timestamps.append(str(timestamp) if timestamp is not None else '')

        if not values:
            return {
                'benchmark': benchmark_name,
                'metric': metric_name,
                'error': 'No metric values found'
            }

        # Calculate statistics
        return {
            'benchmark': benchmark_name,
            'metric': metric_name,
            'count': len(values),
            'latest': values[-1],
            'mean': statistics.mean(values),
            'median': statistics.median(values),
            'stdev': statistics.stdev(values) if len(values) > 1 else 0.0,
            'min': min(values),
            'max': max(values),
            'trend': self._calculate_trend_direction(values),
            'regression_detected': self._detect_regression(values),
            'values': values,
            'timestamps': timestamps,
        }

    def _calculate_trend_direction(self, values: List[float]) -> str:
        """
        Calculer la direction de la tendance

        Args:
            values: Liste de valeurs

        Returns:
            'improving', 'declining', or 'stable'
        """
        if len(values) < 3:
            return 'stable'

        # Compare recent average with older average
        mid_point = len(values) // 2
        recent_avg = statistics.mean(values[mid_point:])
        older_avg = statistics.mean(values[:mid_point])

        diff = recent_avg - older_avg

        # Threshold for significance (5%)
        threshold = 0.05

        if diff > threshold:
            return 'improving'
        elif diff < -threshold:
            return 'declining'
        else:
            return 'stable'

    def _detect_regression(self, values: List[float], threshold: float = 0.05) -> bool:
        """
        Detecter une regression (drop > threshold)

        Args:
            values: Liste de valeurs
            threshold: Seuil de regression (5% par defaut)

        Returns:
            True si regression detectee
        """
        if len(values) < 2:
            return False

        # Check if latest is significantly worse than recent average
        recent_avg = statistics.mean(values[-5:]) if len(values) >= 5 else statistics.mean(values)
        latest = values[-1]

        drop = recent_avg - latest

        return drop > threshold

    def generate_dashboard(self, days: int = 30) -> DashboardData:
        """
        Generer un dashboard de metriques

        Args:
            days: Periode d'analyse

        Returns:
            Dashboard avec toutes les metriques
        """
        dashboard: DashboardData = {
            'generated_at': datetime.now().isoformat(),
            'period_days': days,
            'benchmarks': {},
        }

        # Collect data for all benchmarks
        all_data = self.collect_historical_data(days=days)

        if not all_data:
            dashboard['error'] = 'No historical data found'
            return dashboard

        # Get unique benchmark names
        benchmark_names: set[str] = set()
        for report in all_data:
            benchmarks_field = report.get('benchmarks')
            if benchmarks_field is not None and isinstance(benchmarks_field, dict):
                # Aggregate report
                benchmark_names.update(benchmarks_field.keys())
            else:
                # Individual benchmark report
                benchmark_val = report.get('benchmark')
                if benchmark_val is not None and isinstance(benchmark_val, str):
                    benchmark_names.add(benchmark_val)

        # Compute trends for each benchmark
        benchmarks_dict: Dict[str, TrendData] = {}
        for benchmark_name in benchmark_names:
            if not benchmark_name:
                continue

            trend = self.compute_trend(benchmark_name, days=days)
            benchmarks_dict[benchmark_name] = trend

        dashboard['benchmarks'] = benchmarks_dict

        # Add aggregate statistics
        dashboard['aggregate'] = self._compute_aggregate_stats(all_data)

        return dashboard

    def _compute_aggregate_stats(self, reports: List[ReportData]) -> AggregateStats:
        """
        Calculer des statistiques agregees

        Args:
            reports: Liste de rapports

        Returns:
            Statistiques agregees
        """
        if not reports:
            return {}

        # Count total runs
        total_runs = len(reports)

        # Calculate average pass rate across all benchmarks
        all_pass_rates: List[float] = []
        for report in reports:
            # Check different possible structures
            summary = report.get('summary')
            if summary is not None and isinstance(summary, dict):
                pass_rate = summary.get('overall_pass_rate')
                if pass_rate is not None and isinstance(pass_rate, (int, float)):
                    all_pass_rates.append(float(pass_rate))
            elif 'pass_at_1' in report:
                pass_at_1 = report['pass_at_1']
                if pass_at_1 is not None and isinstance(pass_at_1, (int, float)):
                    all_pass_rates.append(float(pass_at_1))

        return {
            'total_runs': total_runs,
            'avg_pass_rate': statistics.mean(all_pass_rates) if all_pass_rates else None,
            'median_pass_rate': statistics.median(all_pass_rates) if all_pass_rates else None,
        }

    def save_dashboard(self, dashboard: DashboardData, output_path: Optional[str] = None) -> None:
        """
        Sauvegarder le dashboard

        Args:
            dashboard: Dashboard data
            output_path: Chemin de sortie (None = auto)
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            final_path = self.reports_dir / f"dashboard_{timestamp}.json"
        else:
            final_path = Path(output_path)

        with open(final_path, 'w') as f:
            json.dump(dashboard, f, indent=2)

        print(f" Dashboard saved: {final_path}")

        # Save as latest
        latest_path = self.reports_dir / "dashboard_latest.json"
        with open(latest_path, 'w') as f:
            json.dump(dashboard, f, indent=2)

    def print_dashboard(self, dashboard: DashboardData) -> None:
        """
        Afficher le dashboard dans le terminal

        Args:
            dashboard: Dashboard data
        """
        print(f"\n{'='*60}")
        print("FilAgent Benchmarks Dashboard")
        print(f"{'='*60}\n")

        print(f"Generated: {dashboard['generated_at']}")
        print(f"Period: Last {dashboard['period_days']} days\n")

        # Aggregate stats
        aggregate = dashboard.get('aggregate')
        if aggregate is not None and isinstance(aggregate, dict):
            print("Aggregate Statistics")
            print(f"{'='*60}")
            print(f"Total Runs: {aggregate.get('total_runs', 0)}")
            avg_pass_rate = aggregate.get('avg_pass_rate')
            if avg_pass_rate is not None and isinstance(avg_pass_rate, (int, float)):
                print(f"Average Pass Rate: {float(avg_pass_rate)*100:.1f}%")
            print()

        # Per-benchmark trends
        benchmarks = dashboard.get('benchmarks')
        if benchmarks is not None and isinstance(benchmarks, dict):
            print("Per-Benchmark Trends")
            print(f"{'='*60}")

            for benchmark_name, trend in benchmarks.items():
                if not isinstance(trend, dict):
                    continue
                if 'error' in trend:
                    print(f"{benchmark_name:20s}: {trend['error']}")
                    continue

                latest = trend.get('latest', 0)
                mean = trend.get('mean', 0)
                trend_dir = trend.get('trend', 'unknown')
                regression = trend.get('regression_detected', False)

                # Format trend indicator
                if trend_dir == 'improving':
                    indicator = '^'
                elif trend_dir == 'declining':
                    indicator = 'v'
                else:
                    indicator = '->'

                # Format regression warning
                warning = " REGRESSION" if regression else ""

                latest_val = float(latest) if isinstance(latest, (int, float)) else 0.0
                mean_val = float(mean) if isinstance(mean, (int, float)) else 0.0

                print(f"{benchmark_name:20s}: {latest_val*100:5.1f}% (avg: {mean_val*100:5.1f}%) {indicator}{warning}")

        print(f"\n{'='*60}\n")

    def check_regressions(self, threshold: float = 0.05) -> List[RegressionInfo]:
        """
        Verifier les regressions dans tous les benchmarks

        Args:
            threshold: Seuil de regression (5% par defaut)

        Returns:
            Liste des regressions detectees
        """
        dashboard = self.generate_dashboard()
        regressions: List[RegressionInfo] = []

        benchmarks = dashboard.get('benchmarks')
        if benchmarks is None or not isinstance(benchmarks, dict):
            return regressions

        for benchmark_name, trend in benchmarks.items():
            if not isinstance(trend, dict):
                continue
            if trend.get('regression_detected'):
                latest = trend.get('latest')
                mean = trend.get('mean')
                latest_val = float(latest) if isinstance(latest, (int, float)) else 0.0
                mean_val = float(mean) if isinstance(mean, (int, float)) else 0.0
                regressions.append({
                    'benchmark': benchmark_name,
                    'latest': latest_val,
                    'mean': mean_val,
                    'drop': mean_val - latest_val,
                })

        return regressions


def main() -> None:
    """Main entry point for metrics dashboard"""
    import argparse

    parser = argparse.ArgumentParser(description="FilAgent Benchmarks Metrics Dashboard")

    parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='Number of days to analyze (default: 30)'
    )

    parser.add_argument(
        '--benchmark',
        type=str,
        default=None,
        help='Specific benchmark to analyze (default: all)'
    )

    parser.add_argument(
        '--check-regressions',
        action='store_true',
        help='Check for regressions'
    )

    args = parser.parse_args()

    # Create aggregator
    aggregator = MetricsAggregator()

    if args.check_regressions:
        # Check regressions
        regressions = aggregator.check_regressions()

        if regressions:
            print(f"\n {len(regressions)} regression(s) detected:\n")
            for reg in regressions:
                latest = reg.get('latest')
                drop = reg.get('drop')
                latest_val = float(latest) if latest is not None else 0.0
                drop_val = float(drop) if drop is not None else 0.0
                print(f"  - {reg['benchmark']}: {latest_val*100:.1f}% (drop: {drop_val*100:.1f}%)")
            print()
        else:
            print("\n No regressions detected\n")

    elif args.benchmark:
        # Show trend for specific benchmark
        trend = aggregator.compute_trend(args.benchmark, days=args.days)
        print(json.dumps(trend, indent=2))

    else:
        # Generate and display dashboard
        dashboard = aggregator.generate_dashboard(days=args.days)
        aggregator.print_dashboard(dashboard)
        aggregator.save_dashboard(dashboard)


if __name__ == '__main__':
    main()
