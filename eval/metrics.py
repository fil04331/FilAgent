"""
Metrics Aggregation and Dashboard for FilAgent Benchmarks

Collecte, agrège et visualise les métriques de performance:
- Pass rates par benchmark
- Temps d'exécution moyens
- Trends historiques
- Comparaison avec targets
- Détection de régressions
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
import statistics


class MetricsAggregator:
    """
    Agrégateur de métriques pour benchmarks

    Analyse les rapports historiques et génère des statistiques
    """

    def __init__(self, reports_dir: str = "eval/reports"):
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def collect_historical_data(
        self,
        days: int = 30,
        benchmark_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Collecter les données historiques

        Args:
            days: Nombre de jours à analyser
            benchmark_name: Filtrer par benchmark (None = tous)

        Returns:
            Liste de rapports historiques
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        historical_data = []

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
                    report = json.load(f)
                    report['_file'] = report_file.name
                    report['_mtime'] = file_mtime.isoformat()
                    historical_data.append(report)
            except Exception as e:
                print(f"⚠ Warning: Could not load {report_file}: {e}")

        # Sort by timestamp
        historical_data.sort(key=lambda x: x.get('timestamp', ''))

        return historical_data

    def compute_trend(
        self,
        benchmark_name: str,
        metric_name: str = 'pass_at_1',
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Calculer la tendance pour une métrique

        Args:
            benchmark_name: Nom du benchmark
            metric_name: Nom de la métrique (ex: 'pass_at_1')
            days: Période d'analyse

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
        values = []
        timestamps = []

        for report in data:
            value = report.get(metric_name)
            if value is not None:
                values.append(value)
                timestamps.append(report.get('timestamp'))

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
            'stdev': statistics.stdev(values) if len(values) > 1 else 0,
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
        Détecter une régression (drop > threshold)

        Args:
            values: Liste de valeurs
            threshold: Seuil de régression (5% par défaut)

        Returns:
            True si régression détectée
        """
        if len(values) < 2:
            return False

        # Check if latest is significantly worse than recent average
        recent_avg = statistics.mean(values[-5:]) if len(values) >= 5 else statistics.mean(values)
        latest = values[-1]

        drop = recent_avg - latest

        return drop > threshold

    def generate_dashboard(self, days: int = 30) -> Dict[str, Any]:
        """
        Générer un dashboard de métriques

        Args:
            days: Période d'analyse

        Returns:
            Dashboard avec toutes les métriques
        """
        dashboard = {
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
        benchmark_names = set()
        for report in all_data:
            if 'benchmarks' in report:
                # Aggregate report
                benchmark_names.update(report['benchmarks'].keys())
            else:
                # Individual benchmark report
                benchmark_names.add(report.get('benchmark'))

        # Compute trends for each benchmark
        for benchmark_name in benchmark_names:
            if not benchmark_name:
                continue

            trend = self.compute_trend(benchmark_name, days=days)
            dashboard['benchmarks'][benchmark_name] = trend

        # Add aggregate statistics
        dashboard['aggregate'] = self._compute_aggregate_stats(all_data)

        return dashboard

    def _compute_aggregate_stats(self, reports: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculer des statistiques agrégées

        Args:
            reports: Liste de rapports

        Returns:
            Statistiques agrégées
        """
        if not reports:
            return {}

        # Count total runs
        total_runs = len(reports)

        # Calculate average pass rate across all benchmarks
        all_pass_rates = []
        for report in reports:
            # Check different possible structures
            if 'summary' in report:
                pass_rate = report['summary'].get('overall_pass_rate')
                if pass_rate is not None:
                    all_pass_rates.append(pass_rate)
            elif 'pass_at_1' in report:
                all_pass_rates.append(report['pass_at_1'])

        return {
            'total_runs': total_runs,
            'avg_pass_rate': statistics.mean(all_pass_rates) if all_pass_rates else None,
            'median_pass_rate': statistics.median(all_pass_rates) if all_pass_rates else None,
        }

    def save_dashboard(self, dashboard: Dict[str, Any], output_path: Optional[str] = None):
        """
        Sauvegarder le dashboard

        Args:
            dashboard: Dashboard data
            output_path: Chemin de sortie (None = auto)
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.reports_dir / f"dashboard_{timestamp}.json"
        else:
            output_path = Path(output_path)

        with open(output_path, 'w') as f:
            json.dump(dashboard, f, indent=2)

        print(f"✓ Dashboard saved: {output_path}")

        # Save as latest
        latest_path = self.reports_dir / "dashboard_latest.json"
        with open(latest_path, 'w') as f:
            json.dump(dashboard, f, indent=2)

    def print_dashboard(self, dashboard: Dict[str, Any]):
        """
        Afficher le dashboard dans le terminal

        Args:
            dashboard: Dashboard data
        """
        print(f"\n{'='*60}")
        print(f"📊 FilAgent Benchmarks Dashboard")
        print(f"{'='*60}\n")

        print(f"Generated: {dashboard['generated_at']}")
        print(f"Period: Last {dashboard['period_days']} days\n")

        # Aggregate stats
        if 'aggregate' in dashboard:
            agg = dashboard['aggregate']
            print(f"📈 Aggregate Statistics")
            print(f"{'─'*60}")
            print(f"Total Runs: {agg.get('total_runs', 0)}")
            if agg.get('avg_pass_rate') is not None:
                print(f"Average Pass Rate: {agg['avg_pass_rate']*100:.1f}%")
            print()

        # Per-benchmark trends
        if 'benchmarks' in dashboard:
            print(f"📊 Per-Benchmark Trends")
            print(f"{'─'*60}")

            for benchmark_name, trend in dashboard['benchmarks'].items():
                if 'error' in trend:
                    print(f"{benchmark_name:20s}: {trend['error']}")
                    continue

                latest = trend.get('latest', 0)
                mean = trend.get('mean', 0)
                trend_dir = trend.get('trend', 'unknown')
                regression = trend.get('regression_detected', False)

                # Format trend indicator
                if trend_dir == 'improving':
                    indicator = '↗'
                elif trend_dir == 'declining':
                    indicator = '↘'
                else:
                    indicator = '→'

                # Format regression warning
                warning = " ⚠ REGRESSION" if regression else ""

                print(f"{benchmark_name:20s}: {latest*100:5.1f}% (avg: {mean*100:5.1f}%) {indicator}{warning}")

        print(f"\n{'='*60}\n")

    def check_regressions(self, threshold: float = 0.05) -> List[Dict[str, Any]]:
        """
        Vérifier les régressions dans tous les benchmarks

        Args:
            threshold: Seuil de régression (5% par défaut)

        Returns:
            Liste des régressions détectées
        """
        dashboard = self.generate_dashboard()
        regressions = []

        for benchmark_name, trend in dashboard.get('benchmarks', {}).items():
            if trend.get('regression_detected'):
                regressions.append({
                    'benchmark': benchmark_name,
                    'latest': trend.get('latest'),
                    'mean': trend.get('mean'),
                    'drop': trend.get('mean', 0) - trend.get('latest', 0),
                })

        return regressions


def main():
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
            print(f"\n⚠ {len(regressions)} regression(s) detected:\n")
            for reg in regressions:
                print(f"  - {reg['benchmark']}: {reg['latest']*100:.1f}% (drop: {reg['drop']*100:.1f}%)")
            print()
        else:
            print("\n✓ No regressions detected\n")

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
