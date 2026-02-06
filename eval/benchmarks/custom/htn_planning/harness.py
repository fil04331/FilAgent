"""
HTN Planning Benchmark Harness for FilAgent

Evalue les capacites de planification hierarchique:
- Decomposition de taches complexes
- Creation de DAGs (Directed Acyclic Graphs)
- Execution parallele vs sequentielle
- Gestion d'erreurs et fallback
- Verification de resultats
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, List, Union

from eval.base import BenchmarkHarness, BenchmarkResult, BenchmarkTask

# Type aliases for strict typing
MetricValue = Union[str, int, float, bool]
TaskMetadata = Dict[str, Union[str, int, float, bool, List[str]]]
EvaluatorFunc = Callable[["HTNPlanningHarness", BenchmarkTask, str], BenchmarkResult]


class HTNPlanningHarness(BenchmarkHarness):
    """
    Harness pour evaluer HTN Planning

    Tests:
    1. Detection de taches multi-etapes
    2. Decomposition en sous-taches
    3. Identification de dependances
    4. Execution dans le bon ordre
    5. Gestion de l'echec et fallback
    """

    def __init__(self) -> None:
        super().__init__("HTN-Planning", "HTN Planning capability benchmark")
        self.tasks_dir = Path("eval/benchmarks/custom/htn_planning/tasks")
        self.tasks_dir.mkdir(parents=True, exist_ok=True)

    def load_tasks(self) -> List[BenchmarkTask]:
        """
        Charger les taches HTN planning

        Chaque tache teste un aspect du planning hierarchique
        """
        return [
            # Task 1: Simple multi-step (sequential)
            BenchmarkTask(
                id="htn-001-sequential",
                prompt="Lis le fichier data.csv, puis calcule la moyenne, puis affiche le resultat",
                ground_truth="sequential_execution",
                metadata={
                    "test_type": "sequential",
                    "expected_steps": 3,
                    "expected_order": ["read", "calculate", "display"],
                    "complexity": "simple",
                },
            ),
            # Task 2: Parallel tasks
            BenchmarkTask(
                id="htn-002-parallel",
                prompt="Lis file1.csv, file2.csv et file3.csv en meme temps",
                ground_truth="parallel_execution",
                metadata={
                    "test_type": "parallel",
                    "expected_parallel_tasks": 3,
                    "complexity": "medium",
                },
            ),
            # Task 3: Mixed parallel + sequential
            BenchmarkTask(
                id="htn-003-mixed",
                prompt="Lis file1.csv et file2.csv, puis merge les donnees, puis genere un rapport",
                ground_truth="mixed_execution",
                metadata={
                    "test_type": "mixed",
                    "expected_stages": 3,  # parallel read, merge, report
                    "complexity": "medium",
                },
            ),
            # Task 4: Nested decomposition
            BenchmarkTask(
                id="htn-004-nested",
                prompt="Analyse les ventes: lis tous les fichiers CSV du dossier 'data/', "
                "calcule les statistiques par region, genere des graphiques, "
                "puis cree un rapport final avec recommandations",
                ground_truth="nested_decomposition",
                metadata={
                    "test_type": "nested",
                    "min_decomposition_depth": 2,
                    "complexity": "high",
                },
            ),
            # Task 5: Error handling and fallback
            BenchmarkTask(
                id="htn-005-error-handling",
                prompt="Lis le fichier inexistant.csv, puis analyse les donnees",
                ground_truth="error_handled_gracefully",
                metadata={
                    "test_type": "error_handling",
                    "expected_error": True,
                    "expected_fallback": True,
                    "complexity": "medium",
                },
            ),
            # Task 6: Dynamic replanning
            BenchmarkTask(
                id="htn-006-replanning",
                prompt="Trouve tous les fichiers JSON, convertis-les en CSV, "
                "puis analyse les resultats. Si aucun JSON, cherche des XML.",
                ground_truth="dynamic_replanning",
                metadata={
                    "test_type": "replanning",
                    "requires_conditional_logic": True,
                    "complexity": "high",
                },
            ),
            # Task 7: Resource constraints
            BenchmarkTask(
                id="htn-007-resource-aware",
                prompt="Traite 100 fichiers en parallele avec un maximum de 4 workers",
                ground_truth="resource_constrained_execution",
                metadata={
                    "test_type": "resource_aware",
                    "max_workers": 4,
                    "complexity": "medium",
                },
            ),
            # Task 8: Long-running task
            BenchmarkTask(
                id="htn-008-long-running",
                prompt="Telecharge un dataset, nettoie les donnees, entraine un modele, "
                "evalue les performances, puis genere un rapport",
                ground_truth="long_running_pipeline",
                metadata={
                    "test_type": "long_running",
                    "expected_checkpoints": True,
                    "complexity": "high",
                },
            ),
            # Task 9: Verification at each step
            BenchmarkTask(
                id="htn-009-verification",
                prompt="Lis data.csv (verifie format), nettoie les donnees (verifie qualite), "
                "analyse (verifie resultats), genere rapport (verifie completude)",
                ground_truth="verified_execution",
                metadata={
                    "test_type": "verification",
                    "verification_level": "strict",
                    "expected_verifications": 4,
                    "complexity": "high",
                },
            ),
            # Task 10: Adaptive strategy
            BenchmarkTask(
                id="htn-010-adaptive",
                prompt="Traite des donnees: si petit dataset, execute sequentiellement; "
                "si grand dataset, parallelise le traitement",
                ground_truth="adaptive_execution",
                metadata={
                    "test_type": "adaptive",
                    "requires_strategy_selection": True,
                    "complexity": "high",
                },
            ),
        ]

    def evaluate(self, task: BenchmarkTask, response: str) -> BenchmarkResult:
        """
        Evaluer la capacite de planning HTN

        Pour une evaluation complete, on devrait:
        1. Verifier qu'un plan a ete cree
        2. Valider la structure du DAG
        3. Verifier l'ordre d'execution
        4. Confirmer que les verifications ont ete faites

        Pour cette version, on fait une evaluation basique
        """
        if task.metadata is None:
            return BenchmarkResult(
                task_id=task.id,
                passed=False,
                response=response,
                ground_truth=task.ground_truth,
                error="Missing task metadata",
            )

        test_type = str(task.metadata.get("test_type", ""))

        # Dispatch to specific evaluator
        evaluators: Dict[str, EvaluatorFunc] = {
            "sequential": self._evaluate_sequential,
            "parallel": self._evaluate_parallel,
            "mixed": self._evaluate_mixed,
            "nested": self._evaluate_nested,
            "error_handling": self._evaluate_error_handling,
            "replanning": self._evaluate_replanning,
            "resource_aware": self._evaluate_resource_aware,
            "long_running": self._evaluate_long_running,
            "verification": self._evaluate_verification,
            "adaptive": self._evaluate_adaptive,
        }

        evaluator = evaluators.get(test_type)
        if not evaluator:
            return BenchmarkResult(
                task_id=task.id,
                passed=False,
                response=response,
                ground_truth=task.ground_truth,
                error=f"Unknown test type: {test_type}",
            )

        return evaluator(task, response)

    def _evaluate_sequential(self, task: BenchmarkTask, response: str) -> BenchmarkResult:
        """Evaluer execution sequentielle"""
        if task.metadata is None:
            return BenchmarkResult(
                task_id=task.id,
                passed=False,
                response=response,
                ground_truth=task.ground_truth,
                error="Missing metadata",
            )

        # Check for keywords indicating sequential execution
        sequential_indicators = [
            "puis",
            "ensuite",
            "apres",
            "step",
            "etape",
            "then",
            "after",
            "finally",
            "first",
            "second",
            "next",
        ]
        found_indicators = sum(1 for ind in sequential_indicators if ind in response.lower())

        expected_steps = task.metadata.get("expected_steps", 0)
        expected_steps_val = int(expected_steps) if isinstance(expected_steps, (int, float)) else 0

        # Basic heuristic: response should mention steps
        passed = found_indicators >= 2 or str(expected_steps_val) in response

        return BenchmarkResult(
            task_id=task.id,
            passed=passed,
            response=response,
            ground_truth=task.ground_truth,
            metadata={
                "found_indicators": found_indicators,
                "expected_steps": expected_steps_val,
            },
        )

    def _evaluate_parallel(self, task: BenchmarkTask, response: str) -> BenchmarkResult:
        """Evaluer execution parallele"""
        parallel_indicators = [
            "parallel",
            "parallele",
            "simultane",
            "en meme temps",
            "concurrent",
        ]
        found_indicators = sum(1 for ind in parallel_indicators if ind in response.lower())

        passed = found_indicators >= 1

        return BenchmarkResult(
            task_id=task.id,
            passed=passed,
            response=response,
            ground_truth=task.ground_truth,
            metadata={"found_parallel_indicators": found_indicators},
        )

    def _evaluate_mixed(self, task: BenchmarkTask, response: str) -> BenchmarkResult:
        """Evaluer execution mixte (parallele + sequentiel)"""
        # Should show both parallel and sequential aspects
        parallel_words = ["parallel", "simultane", "concurrent"]
        sequential_words = ["puis", "ensuite", "apres"]

        has_parallel = any(w in response.lower() for w in parallel_words)
        has_sequential = any(w in response.lower() for w in sequential_words)

        passed = has_parallel and has_sequential

        return BenchmarkResult(
            task_id=task.id,
            passed=passed,
            response=response,
            ground_truth=task.ground_truth,
            metadata={"has_parallel": has_parallel, "has_sequential": has_sequential},
        )

    def _evaluate_nested(self, task: BenchmarkTask, response: str) -> BenchmarkResult:
        """Evaluer decomposition imbriquee"""
        # Complex task should result in detailed breakdown
        min_words = 100  # Expect detailed response
        passed = len(response.split()) >= min_words

        return BenchmarkResult(
            task_id=task.id,
            passed=passed,
            response=response,
            ground_truth=task.ground_truth,
            metadata={"response_length": len(response.split())},
        )

    def _evaluate_error_handling(self, task: BenchmarkTask, response: str) -> BenchmarkResult:
        """Evaluer gestion d'erreur"""
        error_indicators = [
            "error",
            "erreur",
            "echec",
            "failed",
            "not found",
            "impossible",
        ]
        found_error = any(ind in response.lower() for ind in error_indicators)

        passed = found_error  # Should acknowledge the error

        return BenchmarkResult(
            task_id=task.id,
            passed=passed,
            response=response,
            ground_truth=task.ground_truth,
            metadata={"found_error_handling": found_error},
        )

    def _evaluate_replanning(self, task: BenchmarkTask, response: str) -> BenchmarkResult:
        """Evaluer replanning dynamique"""
        conditional_indicators = [
            "if",
            "si",
            "sinon",
            "else",
            "fallback",
            "alternative",
        ]
        found = sum(1 for ind in conditional_indicators if ind in response.lower())

        passed = found >= 2  # Should show conditional logic

        return BenchmarkResult(
            task_id=task.id,
            passed=passed,
            response=response,
            ground_truth=task.ground_truth,
            metadata={"conditional_indicators": found},
        )

    def _evaluate_resource_aware(self, task: BenchmarkTask, response: str) -> BenchmarkResult:
        """Evaluer awareness des ressources"""
        resource_indicators = [
            "worker",
            "thread",
            "process",
            "limit",
            "maximum",
            "constraint",
        ]
        found = sum(1 for ind in resource_indicators if ind in response.lower())

        passed = found >= 1

        return BenchmarkResult(
            task_id=task.id,
            passed=passed,
            response=response,
            ground_truth=task.ground_truth,
            metadata={"resource_indicators": found},
        )

    def _evaluate_long_running(self, task: BenchmarkTask, response: str) -> BenchmarkResult:
        """Evaluer tache longue avec checkpoints"""
        checkpoint_indicators = [
            "checkpoint",
            "sauvegarde",
            "save",
            "progress",
            "etape",
        ]
        found = sum(1 for ind in checkpoint_indicators if ind in response.lower())

        passed = found >= 1 or len(response.split()) >= 150

        return BenchmarkResult(
            task_id=task.id,
            passed=passed,
            response=response,
            ground_truth=task.ground_truth,
        )

    def _evaluate_verification(self, task: BenchmarkTask, response: str) -> BenchmarkResult:
        """Evaluer verification a chaque etape"""
        if task.metadata is None:
            return BenchmarkResult(
                task_id=task.id,
                passed=False,
                response=response,
                ground_truth=task.ground_truth,
                error="Missing metadata",
            )

        verify_indicators = ["verify", "verifie", "check", "validate", "validation"]
        found = sum(1 for ind in verify_indicators if ind in response.lower())

        expected_val = task.metadata.get("expected_verifications", 1)
        expected = int(expected_val) if isinstance(expected_val, (int, float)) else 1
        passed = found >= expected

        return BenchmarkResult(
            task_id=task.id,
            passed=passed,
            response=response,
            ground_truth=task.ground_truth,
            metadata={"verifications_found": found, "expected": expected},
        )

    def _evaluate_adaptive(self, task: BenchmarkTask, response: str) -> BenchmarkResult:
        """Evaluer strategie adaptive"""
        adaptive_indicators = ["adapt", "adaptive", "selon", "depending", "dynamique"]
        found = sum(1 for ind in adaptive_indicators if ind in response.lower())

        passed = found >= 1

        return BenchmarkResult(
            task_id=task.id,
            passed=passed,
            response=response,
            ground_truth=task.ground_truth,
            metadata={"adaptive_indicators": found},
        )
