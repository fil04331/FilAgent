"""
Classe de base pour les benchmarks d'évaluation
Interface commune pour tous les harness de tests
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json


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
        verbose: bool = False
    ) -> Dict[str, Any]:
        """
        Exécuter le benchmark complet
        
        Args:
            agent_callback: Fonction callback agent
            num_tasks: Nombre de tâches à exécuter (None = toutes)
            verbose: Afficher les détails
        
        Returns:
            Dict avec métriques et résultats
        """
        tasks = self.load_tasks()
        
        if num_tasks:
            tasks = tasks[:num_tasks]
        
        results = []
        passed = 0
        total = len(tasks)
        
        print(f"Running {self.name} with {total} tasks...")
        
        for i, task in enumerate(tasks, 1):
            if verbose:
                print(f"  [{i}/{total}] Task: {task.id}")
            
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
            results.append(result)
            
            if result.passed:
                passed += 1
            
            if verbose and result.passed:
                print(f"    ✓ PASS")
            elif verbose and not result.passed:
                print(f"    ✗ FAIL: {result.error}")
        
        # Calculer les métriques
        pass_rate = passed / total if total > 0 else 0
        avg_latency = sum(r.latency_ms for r in results if r.latency_ms) / len(results) if results else 0
        
        # Report
        report = {
            "benchmark": self.name,
            "timestamp": datetime.now().isoformat(),
            "total_tasks": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": pass_rate,
            "avg_latency_ms": avg_latency,
            "results": [
                {
                    "task_id": r.task_id,
                    "passed": r.passed,
                    "latency_ms": r.latency_ms,
                    "error": r.error
                }
                for r in results
            ]
        }
        
        print(f"\n✓ {self.name} complete:")
        print(f"  Pass: {passed}/{total} ({pass_rate*100:.1f}%)")
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
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"✓ Report saved: {filepath}")
