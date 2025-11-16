"""
HTN Planning Benchmark Harness for FilAgent

Évalue les capacités de planification hiérarchique:
- Décomposition de tâches complexes
- Création de DAGs (Directed Acyclic Graphs)
- Exécution parallèle vs séquentielle
- Gestion d'erreurs et fallback
- Vérification de résultats
"""
import json
from typing import List, Dict, Any
from pathlib import Path
from eval.base import BenchmarkHarness, BenchmarkTask, BenchmarkResult


class HTNPlanningHarness(BenchmarkHarness):
    """
    Harness pour évaluer HTN Planning

    Tests:
    1. Détection de tâches multi-étapes
    2. Décomposition en sous-tâches
    3. Identification de dépendances
    4. Exécution dans le bon ordre
    5. Gestion de l'échec et fallback
    """

    def __init__(self):
        super().__init__("HTN-Planning", "HTN Planning capability benchmark")
        self.tasks_dir = Path("eval/benchmarks/custom/htn_planning/tasks")
        self.tasks_dir.mkdir(parents=True, exist_ok=True)

    def load_tasks(self) -> List[BenchmarkTask]:
        """
        Charger les tâches HTN planning

        Chaque tâche teste un aspect du planning hiérarchique
        """
        return [
            # Task 1: Simple multi-step (sequential)
            BenchmarkTask(
                id="htn-001-sequential",
                prompt="Lis le fichier data.csv, puis calcule la moyenne, puis affiche le résultat",
                ground_truth="sequential_execution",
                metadata={
                    'test_type': 'sequential',
                    'expected_steps': 3,
                    'expected_order': ['read', 'calculate', 'display'],
                    'complexity': 'simple',
                }
            ),

            # Task 2: Parallel tasks
            BenchmarkTask(
                id="htn-002-parallel",
                prompt="Lis file1.csv, file2.csv et file3.csv en même temps",
                ground_truth="parallel_execution",
                metadata={
                    'test_type': 'parallel',
                    'expected_parallel_tasks': 3,
                    'complexity': 'medium',
                }
            ),

            # Task 3: Mixed parallel + sequential
            BenchmarkTask(
                id="htn-003-mixed",
                prompt="Lis file1.csv et file2.csv, puis merge les données, puis génère un rapport",
                ground_truth="mixed_execution",
                metadata={
                    'test_type': 'mixed',
                    'expected_stages': 3,  # parallel read, merge, report
                    'complexity': 'medium',
                }
            ),

            # Task 4: Nested decomposition
            BenchmarkTask(
                id="htn-004-nested",
                prompt="Analyse les ventes: lis tous les fichiers CSV du dossier 'data/', "
                       "calcule les statistiques par région, génère des graphiques, "
                       "puis crée un rapport final avec recommandations",
                ground_truth="nested_decomposition",
                metadata={
                    'test_type': 'nested',
                    'min_decomposition_depth': 2,
                    'complexity': 'high',
                }
            ),

            # Task 5: Error handling and fallback
            BenchmarkTask(
                id="htn-005-error-handling",
                prompt="Lis le fichier inexistant.csv, puis analyse les données",
                ground_truth="error_handled_gracefully",
                metadata={
                    'test_type': 'error_handling',
                    'expected_error': True,
                    'expected_fallback': True,
                    'complexity': 'medium',
                }
            ),

            # Task 6: Dynamic replanning
            BenchmarkTask(
                id="htn-006-replanning",
                prompt="Trouve tous les fichiers JSON, convertis-les en CSV, "
                       "puis analyse les résultats. Si aucun JSON, cherche des XML.",
                ground_truth="dynamic_replanning",
                metadata={
                    'test_type': 'replanning',
                    'requires_conditional_logic': True,
                    'complexity': 'high',
                }
            ),

            # Task 7: Resource constraints
            BenchmarkTask(
                id="htn-007-resource-aware",
                prompt="Traite 100 fichiers en parallèle avec un maximum de 4 workers",
                ground_truth="resource_constrained_execution",
                metadata={
                    'test_type': 'resource_aware',
                    'max_workers': 4,
                    'complexity': 'medium',
                }
            ),

            # Task 8: Long-running task
            BenchmarkTask(
                id="htn-008-long-running",
                prompt="Télécharge un dataset, nettoie les données, entraine un modèle, "
                       "évalue les performances, puis génère un rapport",
                ground_truth="long_running_pipeline",
                metadata={
                    'test_type': 'long_running',
                    'expected_checkpoints': True,
                    'complexity': 'high',
                }
            ),

            # Task 9: Verification at each step
            BenchmarkTask(
                id="htn-009-verification",
                prompt="Lis data.csv (vérifie format), nettoie les données (vérifie qualité), "
                       "analyse (vérifie résultats), génère rapport (vérifie complétude)",
                ground_truth="verified_execution",
                metadata={
                    'test_type': 'verification',
                    'verification_level': 'strict',
                    'expected_verifications': 4,
                    'complexity': 'high',
                }
            ),

            # Task 10: Adaptive strategy
            BenchmarkTask(
                id="htn-010-adaptive",
                prompt="Traite des données: si petit dataset, exécute séquentiellement; "
                       "si grand dataset, parallélise le traitement",
                ground_truth="adaptive_execution",
                metadata={
                    'test_type': 'adaptive',
                    'requires_strategy_selection': True,
                    'complexity': 'high',
                }
            ),
        ]

    def evaluate(self, task: BenchmarkTask, response: str) -> BenchmarkResult:
        """
        Évaluer la capacité de planning HTN

        Pour une évaluation complète, on devrait:
        1. Vérifier qu'un plan a été créé
        2. Valider la structure du DAG
        3. Vérifier l'ordre d'exécution
        4. Confirmer que les vérifications ont été faites

        Pour cette version, on fait une évaluation basique
        """
        test_type = task.metadata['test_type']

        # Dispatch to specific evaluator
        evaluators = {
            'sequential': self._evaluate_sequential,
            'parallel': self._evaluate_parallel,
            'mixed': self._evaluate_mixed,
            'nested': self._evaluate_nested,
            'error_handling': self._evaluate_error_handling,
            'replanning': self._evaluate_replanning,
            'resource_aware': self._evaluate_resource_aware,
            'long_running': self._evaluate_long_running,
            'verification': self._evaluate_verification,
            'adaptive': self._evaluate_adaptive,
        }

        evaluator = evaluators.get(test_type)
        if not evaluator:
            return BenchmarkResult(
                task_id=task.id,
                passed=False,
                response=response,
                ground_truth=task.ground_truth,
                error=f"Unknown test type: {test_type}"
            )

        return evaluator(task, response)

    def _evaluate_sequential(self, task: BenchmarkTask, response: str) -> BenchmarkResult:
        """Évaluer exécution séquentielle"""
        # Check for keywords indicating sequential execution
        sequential_indicators = ['puis', 'ensuite', 'après', 'step', 'étape']
        found_indicators = sum(1 for ind in sequential_indicators if ind in response.lower())

        expected_steps = task.metadata['expected_steps']

        # Basic heuristic: response should mention steps
        passed = found_indicators >= 2 or str(expected_steps) in response

        return BenchmarkResult(
            task_id=task.id,
            passed=passed,
            response=response,
            ground_truth=task.ground_truth,
            metadata={
                'found_indicators': found_indicators,
                'expected_steps': expected_steps
            }
        )

    def _evaluate_parallel(self, task: BenchmarkTask, response: str) -> BenchmarkResult:
        """Évaluer exécution parallèle"""
        parallel_indicators = ['parallel', 'parallèle', 'simultané', 'en même temps', 'concurrent']
        found_indicators = sum(1 for ind in parallel_indicators if ind in response.lower())

        passed = found_indicators >= 1

        return BenchmarkResult(
            task_id=task.id,
            passed=passed,
            response=response,
            ground_truth=task.ground_truth,
            metadata={'found_parallel_indicators': found_indicators}
        )

    def _evaluate_mixed(self, task: BenchmarkTask, response: str) -> BenchmarkResult:
        """Évaluer exécution mixte (parallèle + séquentiel)"""
        # Should show both parallel and sequential aspects
        parallel_words = ['parallel', 'simultané', 'concurrent']
        sequential_words = ['puis', 'ensuite', 'après']

        has_parallel = any(w in response.lower() for w in parallel_words)
        has_sequential = any(w in response.lower() for w in sequential_words)

        passed = has_parallel and has_sequential

        return BenchmarkResult(
            task_id=task.id,
            passed=passed,
            response=response,
            ground_truth=task.ground_truth,
            metadata={'has_parallel': has_parallel, 'has_sequential': has_sequential}
        )

    def _evaluate_nested(self, task: BenchmarkTask, response: str) -> BenchmarkResult:
        """Évaluer décomposition imbriquée"""
        # Complex task should result in detailed breakdown
        min_words = 100  # Expect detailed response
        passed = len(response.split()) >= min_words

        return BenchmarkResult(
            task_id=task.id,
            passed=passed,
            response=response,
            ground_truth=task.ground_truth,
            metadata={'response_length': len(response.split())}
        )

    def _evaluate_error_handling(self, task: BenchmarkTask, response: str) -> BenchmarkResult:
        """Évaluer gestion d'erreur"""
        error_indicators = ['error', 'erreur', 'échec', 'failed', 'not found', 'impossible']
        found_error = any(ind in response.lower() for ind in error_indicators)

        passed = found_error  # Should acknowledge the error

        return BenchmarkResult(
            task_id=task.id,
            passed=passed,
            response=response,
            ground_truth=task.ground_truth,
            metadata={'found_error_handling': found_error}
        )

    def _evaluate_replanning(self, task: BenchmarkTask, response: str) -> BenchmarkResult:
        """Évaluer replanning dynamique"""
        conditional_indicators = ['if', 'si', 'sinon', 'else', 'fallback', 'alternative']
        found = sum(1 for ind in conditional_indicators if ind in response.lower())

        passed = found >= 2  # Should show conditional logic

        return BenchmarkResult(
            task_id=task.id,
            passed=passed,
            response=response,
            ground_truth=task.ground_truth,
            metadata={'conditional_indicators': found}
        )

    def _evaluate_resource_aware(self, task: BenchmarkTask, response: str) -> BenchmarkResult:
        """Évaluer awareness des ressources"""
        resource_indicators = ['worker', 'thread', 'process', 'limit', 'maximum', 'constraint']
        found = sum(1 for ind in resource_indicators if ind in response.lower())

        passed = found >= 1

        return BenchmarkResult(
            task_id=task.id,
            passed=passed,
            response=response,
            ground_truth=task.ground_truth,
            metadata={'resource_indicators': found}
        )

    def _evaluate_long_running(self, task: BenchmarkTask, response: str) -> BenchmarkResult:
        """Évaluer tâche longue avec checkpoints"""
        checkpoint_indicators = ['checkpoint', 'sauvegarde', 'save', 'progress', 'étape']
        found = sum(1 for ind in checkpoint_indicators if ind in response.lower())

        passed = found >= 1 or len(response.split()) >= 150

        return BenchmarkResult(
            task_id=task.id,
            passed=passed,
            response=response,
            ground_truth=task.ground_truth
        )

    def _evaluate_verification(self, task: BenchmarkTask, response: str) -> BenchmarkResult:
        """Évaluer vérification à chaque étape"""
        verify_indicators = ['verify', 'vérifie', 'check', 'validate', 'validation']
        found = sum(1 for ind in verify_indicators if ind in response.lower())

        expected = task.metadata.get('expected_verifications', 1)
        passed = found >= expected

        return BenchmarkResult(
            task_id=task.id,
            passed=passed,
            response=response,
            ground_truth=task.ground_truth,
            metadata={'verifications_found': found, 'expected': expected}
        )

    def _evaluate_adaptive(self, task: BenchmarkTask, response: str) -> BenchmarkResult:
        """Évaluer stratégie adaptive"""
        adaptive_indicators = ['adapt', 'adaptive', 'selon', 'depending', 'dynamique']
        found = sum(1 for ind in adaptive_indicators if ind in response.lower())

        passed = found >= 1

        return BenchmarkResult(
            task_id=task.id,
            passed=passed,
            response=response,
            ground_truth=task.ground_truth,
            metadata={'adaptive_indicators': found}
        )
