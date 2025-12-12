"""
Classe de base pour les benchmarks d'evaluation
Interface commune pour tous les harness de tests
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, List, Optional, Union
import json


# Type aliases for strict typing
MetricValue = Union[str, int, float, bool]
MetricDict = Dict[str, MetricValue]
TaskMetadata = Dict[str, Union[str, int, float, bool, List[str]]]


@dataclass
class BenchmarkTask:
    """Tache de benchmark"""
    id: str
    prompt: str
    ground_truth: str  # Reponse attendue
    metadata: Optional[TaskMetadata] = None


@dataclass
class BenchmarkResult:
    """Resultat d'un benchmark"""
    task_id: str
    passed: bool
    response: str
    ground_truth: str
    error: Optional[str] = None
    metadata: Optional[TaskMetadata] = None
    latency_ms: Optional[float] = None


# Type alias for the agent callback function
AgentCallback = Callable[[str], str]

# Type alias for benchmark report
BenchmarkReport = Dict[str, Union[str, int, float, bool, List[MetricDict]]]


class BenchmarkHarness(ABC):
    """Harness de base pour les benchmarks"""

    def __init__(self, name: str, description: str) -> None:
        self.name = name
        self.description = description

    @abstractmethod
    def load_tasks(self) -> List[BenchmarkTask]:
        """
        Charger les taches du benchmark

        Returns:
            Liste de taches de benchmark
        """
        pass

    @abstractmethod
    def evaluate(self, task: BenchmarkTask, response: str) -> BenchmarkResult:
        """
        Evaluer une reponse

        Args:
            task: Tache du benchmark
            response: Reponse generee

        Returns:
            Resultat de l'evaluation
        """
        pass

    def run_benchmark(
        self,
        agent_callback: AgentCallback,
        num_tasks: Optional[int] = None,
        k: int = 1,
        verbose: bool = False
    ) -> BenchmarkReport:
        """
        Executer le benchmark complet

        Args:
            agent_callback: Fonction callback agent
            num_tasks: Nombre de taches a executer (None = toutes)
            k: Nombre de generations par tache pour le calcul de pass@k
            verbose: Afficher les details

        Returns:
            Dict avec metriques et resultats
        """
        tasks = self.load_tasks()

        if num_tasks:
            tasks = tasks[:num_tasks]

        results: List[BenchmarkResult] = []
        passed_at_k = 0
        total = len(tasks)

        print(f"Running {self.name} with {total} tasks (pass@{k})...")

        for i, task in enumerate(tasks, 1):
            if verbose:
                print(f"  [{i}/{total}] Task: {task.id}")

            task_passed = False
            task_results: List[BenchmarkResult] = []

            for _ in range(k):
                # Appeler l'agent
                start_time = datetime.now()
                try:
                    response = agent_callback(task.prompt)
                except Exception as e:
                    response = f"ERROR: {str(e)}"

                latency_ms = (datetime.now() - start_time).total_seconds() * 1000

                # Evaluer
                result = self.evaluate(task, response)
                result.latency_ms = latency_ms
                task_results.append(result)

                if result.passed:
                    task_passed = True
                    break  # Exit early once we have a passing solution

            results.extend(task_results)

            if task_passed:
                passed_at_k += 1

            if verbose and task_passed:
                print(f"    PASS (at least one of {k})")
            elif verbose and not task_passed:
                print(f"    FAIL (none of {k} passed)")

        # Calculer les metriques
        pass_at_k_rate = passed_at_k / total if total > 0 else 0.0
        latencies = [r.latency_ms for r in results if r.latency_ms is not None]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

        # Report
        report: BenchmarkReport = {
            "benchmark": self.name,
            "timestamp": datetime.now().isoformat(),
            "total_tasks": total,
            "k": k,
            "passed_at_k": passed_at_k,
            "failed": total - passed_at_k,
            f"pass_at_{k}": pass_at_k_rate,
            "avg_latency_ms": avg_latency,
            "results": [
                {
                    "task_id": r.task_id,
                    "passed": r.passed,
                    "latency_ms": r.latency_ms if r.latency_ms is not None else 0.0,
                    "error": r.error if r.error is not None else ""
                }
                for r in results
            ]
        }

        print(f"\n {self.name} complete:")
        print(f"  Pass@{k}: {passed_at_k}/{total} ({pass_at_k_rate*100:.1f}%)")
        print(f"  Avg Latency: {avg_latency:.0f}ms")

        return report

    def save_report(self, report: BenchmarkReport, output_dir: str = "eval/reports") -> None:
        """Sauvegarder le rapport d'evaluation"""
        from pathlib import Path
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.name.lower()}_{timestamp}.json"
        filepath = output_path / filename

        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)

        print(f" Report saved: {filepath}")
