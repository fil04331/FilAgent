"""
Classe de base pour les benchmarks d'évaluation
Interface commune pour tous les harness de tests
"""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class BenchmarkTask:
    """Tâche de benchmark"""

    id: str
    prompt: str
    ground_truth: str  # Réponse attendue
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class BenchmarkResult:
    """Résultat d'un benchmark"""

    task_id: str
    passed: bool
    response: str
    ground_truth: str
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    latency_ms: Optional[float] = None


class BenchmarkHarness(ABC):
    """Harness de base pour les benchmarks"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def load_tasks(self) -> List[BenchmarkTask]:
        """
        Charger les tâches du benchmark

        Returns:
            Liste de tâches de benchmark
        """
        pass

    @abstractmethod
    def evaluate(self, task: BenchmarkTask, response: str) -> BenchmarkResult:
        """
        Évaluer une réponse

        Args:
            task: Tâche du benchmark
            response: Réponse générée

        Returns:
            Résultat de l'évaluation
        """
        pass

    def run_benchmark(
        self,
        agent_callback,  # Fonction qui prend un prompt et retourne une réponse
        num_tasks: Optional[int] = None,
        k: int = 1,
        verbose: bool = False,
    ) -> Dict[str, Any]:
        """
        Exécuter le benchmark complet

        Args:
            agent_callback: Fonction callback agent
            num_tasks: Nombre de tâches à exécuter (None = toutes)
            k: Nombre de générations par tâche pour le calcul de pass@k
            verbose: Afficher les détails

        Returns:
            Dict avec métriques et résultats
        """
        tasks = self.load_tasks()

        if num_tasks:
            tasks = tasks[:num_tasks]

        results = []
        passed_at_k = 0
        total = len(tasks)

        print(f"Running {self.name} with {total} tasks (pass@{k})...")

        for i, task in enumerate(tasks, 1):
            if verbose:
                print(f"  [{i}/{total}] Task: {task.id}")

            task_passed = False
            task_results = []

            for _ in range(k):
                # Appeler l'agent
                start_time = datetime.now()
                try:
                    response = agent_callback(task.prompt)
                except Exception as e:
                    response = f"ERROR: {str(e)}"

                latency_ms = (datetime.now() - start_time).total_seconds() * 1000

                # Évaluer
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
                print(f"    ✓ PASS (at least one of {k})")
            elif verbose and not task_passed:
                print(f"    ✗ FAIL (none of {k} passed)")

        # Calculer les métriques
        pass_at_k_rate = passed_at_k / total if total > 0 else 0
        avg_latency = (
            sum(r.latency_ms for r in results if r.latency_ms) / len(results) if results else 0
        )

        # Report
        report = {
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
                    "latency_ms": r.latency_ms,
                    "error": r.error,
                }
                for r in results
            ],
        }

        print(f"\n✓ {self.name} complete:")
        print(f"  Pass@{k}: {passed_at_k}/{total} ({pass_at_k_rate*100:.1f}%)")
        print(f"  Avg Latency: {avg_latency:.0f}ms")

        return report

    def save_report(self, report: Dict[str, Any], output_dir: str = "eval/reports"):
        """Sauvegarder le rapport d'évaluation"""
        from pathlib import Path

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.name.lower()}_{timestamp}.json"
        filepath = output_path / filename

        with open(filepath, "w") as f:
            json.dump(report, f, indent=2)

        print(f"✓ Report saved: {filepath}")
