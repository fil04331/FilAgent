"""
SWE-bench Harness for FilAgent

Evaluates software engineering capabilities on real-world GitHub issues.
Uses SWE-bench Lite (300 instances) for faster evaluation.

Référence: https://www.swebench.com/
"""
import os
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from datasets import load_dataset, load_from_disk
from filelock import FileLock
from eval.base import BenchmarkHarness, BenchmarkTask, BenchmarkResult


class SWEBenchHarness(BenchmarkHarness):
    """
    SWE-bench Lite harness for software engineering tasks

    Évalue la capacité de l'agent à:
    - Comprendre des issues GitHub réelles
    - Naviguer dans des codebases
    - Générer des patches corrects
    - Résoudre des bugs réels
    """

    def __init__(self, variant: str = "lite"):
        """
        Initialize SWE-bench harness

        Args:
            variant: "lite" (300 instances) or "full" (2294 instances)
                    Recommandé: "lite" pour développement
        """
        super().__init__("SWE-bench", "SWE-bench for software engineering tasks")
        self.variant = variant
        self.dataset_path = f"eval/benchmarks/swe_bench/{variant}"
        self.lock_path = f"{self.dataset_path}.lock"

    def load_tasks(self) -> List[BenchmarkTask]:
        """
        Charger les tâches SWE-bench

        Returns:
            Liste de tâches de benchmark (issues GitHub)
        """
        # Use filelock to prevent race conditions during dataset download
        with FileLock(self.lock_path):
            if not os.path.exists(self.dataset_path):
                # Load SWE-bench Lite (smaller, faster)
                if self.variant == "lite":
                    dataset_name = "princeton-nlp/SWE-bench_Lite"
                else:
                    dataset_name = "princeton-nlp/SWE-bench"

                try:
                    self.dataset = load_dataset(dataset_name)
                    self.dataset.save_to_disk(self.dataset_path)
                except Exception as e:
                    print(f"⚠ Failed to load SWE-bench dataset: {e}")
                    print(f"  Creating mock dataset for testing...")
                    # Create mock dataset for testing
                    return self._create_mock_tasks()
            else:
                self.dataset = load_from_disk(self.dataset_path)

        tasks = []
        for item in self.dataset['test']:
            # Extract relevant fields
            tasks.append(
                BenchmarkTask(
                    id=item['instance_id'],
                    prompt=self._format_prompt(item),
                    ground_truth=item['patch'],
                    metadata={
                        'repo': item['repo'],
                        'base_commit': item['base_commit'],
                        'problem_statement': item['problem_statement'],
                        'hints_text': item.get('hints_text', ''),
                        'test_patch': item.get('test_patch', ''),
                    },
                )
            )
        return tasks

    def _format_prompt(self, item: Dict[str, Any]) -> str:
        """
        Formater le prompt pour SWE-bench

        Format standard pour présenter l'issue à l'agent
        """
        prompt = f"""You are tasked with solving a real-world GitHub issue from the repository: {item['repo']}

# Problem Statement

{item['problem_statement']}

"""
        if item.get('hints_text'):
            prompt += f"""# Hints

{item['hints_text']}

"""

        prompt += """# Task

Analyze the problem and generate a patch that resolves the issue.
Provide your solution as a unified diff patch format.

# Instructions

1. Understand the problem statement thoroughly
2. Identify the files that need to be modified
3. Generate a correct patch in unified diff format
4. Ensure the patch applies cleanly to the base commit

Your response should contain the patch between triple backticks with 'diff' language identifier:

```diff
your patch here
```
"""
        return prompt

    def _create_mock_tasks(self) -> List[BenchmarkTask]:
        """
        Créer des tâches mock pour testing (si dataset indisponible)
        """
        mock_tasks = [
            BenchmarkTask(
                id="mock-001-simple-bug",
                prompt="""You are tasked with solving a real-world GitHub issue from the repository: mock/simple-repo

# Problem Statement

The function `calculate_total` in `src/calculator.py` is not handling negative numbers correctly.
It should return the absolute value of the sum.

# Task

Generate a patch that fixes this issue.

```python
# Current code in src/calculator.py
def calculate_total(numbers):
    return sum(numbers)
```

Expected behavior: `calculate_total([-1, -2, -3])` should return `6`, not `-6`.

Your response should contain the patch in unified diff format.
""",
                ground_truth="""--- a/src/calculator.py
+++ b/src/calculator.py
@@ -1,2 +1,2 @@
 def calculate_total(numbers):
-    return sum(numbers)
+    return abs(sum(numbers))
""",
                metadata={
                    'repo': 'mock/simple-repo',
                    'base_commit': 'abc123',
                    'problem_statement': 'Fix negative number handling',
                }
            )
        ]
        return mock_tasks

    def evaluate(self, task: BenchmarkTask, response: str) -> BenchmarkResult:
        """
        Évaluer une réponse SWE-bench

        Validation simplifiée:
        1. Vérifier que la réponse contient un patch
        2. Comparer avec le patch de référence (similarité)
        3. Pour l'évaluation complète, il faudrait appliquer le patch et tester

        Args:
            task: Tâche SWE-bench
            response: Réponse générée (patch)

        Returns:
            Résultat de l'évaluation
        """
        # Extract patch from response
        patch = self._extract_patch(response)

        if not patch:
            return BenchmarkResult(
                task_id=task.id,
                passed=False,
                response=response,
                ground_truth=task.ground_truth,
                error="No patch found in response",
                metadata={'evaluation_type': 'format_check'}
            )

        # Simple validation: check if patch looks valid
        is_valid, error_msg = self._validate_patch_format(patch)

        if not is_valid:
            return BenchmarkResult(
                task_id=task.id,
                passed=False,
                response=response,
                ground_truth=task.ground_truth,
                error=error_msg,
                metadata={'evaluation_type': 'format_validation'}
            )

        # For full evaluation, we would:
        # 1. Clone the repo at base_commit
        # 2. Apply the patch
        # 3. Run the tests
        # For now, we do similarity-based evaluation

        similarity = self._compute_patch_similarity(patch, task.ground_truth)
        passed = similarity > 0.5  # Threshold for acceptance

        return BenchmarkResult(
            task_id=task.id,
            passed=passed,
            response=response,
            ground_truth=task.ground_truth,
            error=None if passed else f"Patch similarity too low: {similarity:.2f}",
            metadata={
                'evaluation_type': 'similarity',
                'similarity': similarity,
                'patch_extracted': patch[:200] + '...' if len(patch) > 200 else patch
            }
        )

    def _extract_patch(self, response: str) -> Optional[str]:
        """Extraire le patch de la réponse"""
        import re

        # Look for code blocks with diff
        diff_pattern = r'```diff\n(.*?)\n```'
        matches = re.findall(diff_pattern, response, re.DOTALL)

        if matches:
            return matches[0].strip()

        # Look for unified diff markers
        if '---' in response and '+++' in response:
            # Extract everything that looks like a diff
            lines = response.split('\n')
            diff_lines = []
            in_diff = False
            for line in lines:
                if line.startswith('---') or line.startswith('+++'):
                    in_diff = True
                if in_diff:
                    diff_lines.append(line)
                if in_diff and line.strip() == '':
                    break
            if diff_lines:
                return '\n'.join(diff_lines)

        return None

    def _validate_patch_format(self, patch: str) -> tuple[bool, Optional[str]]:
        """Valider le format du patch"""
        if not patch:
            return False, "Empty patch"

        # Check for unified diff markers
        if '---' not in patch or '+++' not in patch:
            return False, "Missing unified diff markers (--- and +++)"

        # Check for hunk markers
        if not any(line.startswith('@@') for line in patch.split('\n')):
            return False, "Missing hunk markers (@@)"

        return True, None

    def _compute_patch_similarity(self, patch1: str, patch2: str) -> float:
        """
        Calculer la similarité entre deux patches

        Utilise Levenshtein distance normalisée
        """
        try:
            from difflib import SequenceMatcher

            # Normalize patches
            p1_lines = [line.strip() for line in patch1.split('\n') if line.strip()]
            p2_lines = [line.strip() for line in patch2.split('\n') if line.strip()]

            # Compute similarity
            matcher = SequenceMatcher(None, p1_lines, p2_lines)
            return matcher.ratio()
        except Exception:
            return 0.0
