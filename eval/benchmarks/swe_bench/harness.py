"""
SWE-bench Harness for FilAgent

Evaluates software engineering capabilities on real-world GitHub issues.
Uses SWE-bench Lite (300 instances) for faster evaluation.

Reference: https://www.swebench.com/
"""
from __future__ import annotations

import os
import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from datasets import load_dataset, load_from_disk, DatasetDict
from filelock import FileLock

from eval.base import BenchmarkHarness, BenchmarkTask, BenchmarkResult


# Type aliases for strict typing
MetricValue = Union[str, int, float, bool]
TaskMetadata = Dict[str, Union[str, int, float, bool, List[str]]]
DatasetItem = Dict[str, Union[str, int, float, bool, None]]


class SWEBenchHarness(BenchmarkHarness):
    """
    SWE-bench Lite harness for software engineering tasks

    Evalue la capacite de l'agent a:
    - Comprendre des issues GitHub reelles
    - Naviguer dans des codebases
    - Generer des patches corrects
    - Resoudre des bugs reels
    """

    def __init__(self, variant: str = "lite") -> None:
        """
        Initialize SWE-bench harness

        Args:
            variant: "lite" (300 instances) or "full" (2294 instances)
                    Recommande: "lite" pour developpement
        """
        super().__init__("SWE-bench", "SWE-bench for software engineering tasks")
        self.variant = variant
        self.dataset_path = f"eval/benchmarks/swe_bench/{variant}"
        self.lock_path = f"{self.dataset_path}.lock"
        self.dataset: Optional[DatasetDict] = None

    def load_tasks(self) -> List[BenchmarkTask]:
        """
        Charger les taches SWE-bench

        Returns:
            Liste de taches de benchmark (issues GitHub)
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
                    if self.dataset is not None:
                        self.dataset.save_to_disk(self.dataset_path)
                except (OSError, RuntimeError, ValueError) as e:
                    print(f"Warning: Failed to load SWE-bench dataset: {e}")
                    print("Creating mock dataset for testing...")
                    # Create mock dataset for testing
                    return self._create_mock_tasks()
            else:
                self.dataset = load_from_disk(self.dataset_path)

        if self.dataset is None:
            return self._create_mock_tasks()

        tasks: List[BenchmarkTask] = []
        for item in self.dataset['test']:
            # Extract relevant fields safely
            instance_id = str(item.get('instance_id', ''))
            patch = str(item.get('patch', ''))
            repo = str(item.get('repo', ''))
            base_commit = str(item.get('base_commit', ''))
            problem_statement = str(item.get('problem_statement', ''))
            hints_text = str(item.get('hints_text', '')) if item.get('hints_text') else ''
            test_patch = str(item.get('test_patch', '')) if item.get('test_patch') else ''

            item_dict: DatasetItem = {
                'instance_id': instance_id,
                'repo': repo,
                'base_commit': base_commit,
                'problem_statement': problem_statement,
                'hints_text': hints_text,
                'test_patch': test_patch,
                'patch': patch,
            }

            tasks.append(
                BenchmarkTask(
                    id=instance_id,
                    prompt=self._format_prompt(item_dict),
                    ground_truth=patch,
                    metadata={
                        'repo': repo,
                        'base_commit': base_commit,
                        'problem_statement': problem_statement,
                        'hints_text': hints_text,
                        'test_patch': test_patch,
                    },
                )
            )
        return tasks

    def _format_prompt(self, item: DatasetItem) -> str:
        """
        Formater le prompt pour SWE-bench

        Format standard pour presenter l'issue a l'agent
        """
        repo = item.get('repo', '')
        problem_statement = item.get('problem_statement', '')
        hints_text = item.get('hints_text', '')

        prompt = f"""You are tasked with solving a real-world GitHub issue from the repository: {repo}

# Problem Statement

{problem_statement}

"""
        if hints_text:
            prompt += f"""# Hints

{hints_text}

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
        Creer des taches mock pour testing (si dataset indisponible)
        """
        mock_tasks: List[BenchmarkTask] = [
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
        Evaluer une reponse SWE-bench

        Validation simplifiee:
        1. Verifier que la reponse contient un patch
        2. Comparer avec le patch de reference (similarite)
        3. Pour l'evaluation complete, il faudrait appliquer le patch et tester

        Args:
            task: Tache SWE-bench
            response: Reponse generee (patch)

        Returns:
            Resultat de l'evaluation
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

        patch_preview = patch[:200] + '...' if len(patch) > 200 else patch

        return BenchmarkResult(
            task_id=task.id,
            passed=passed,
            response=response,
            ground_truth=task.ground_truth,
            error=None if passed else f"Patch similarity too low: {similarity:.2f}",
            metadata={
                'evaluation_type': 'similarity',
                'similarity': similarity,
                'patch_extracted': patch_preview
            }
        )

    def _extract_patch(self, response: str) -> Optional[str]:
        """Extraire le patch de la reponse"""
        # Look for code blocks with diff
        diff_pattern = r'```diff\n(.*?)\n```'
        matches = re.findall(diff_pattern, response, re.DOTALL)

        if matches:
            return matches[0].strip()

        # Look for unified diff markers
        if '---' in response and '+++' in response:
            # Extract everything that looks like a diff
            lines = response.split('\n')
            diff_lines: List[str] = []
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

    def _validate_patch_format(self, patch: str) -> Tuple[bool, Optional[str]]:
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
        Calculer la similarite entre deux patches

        Utilise Levenshtein distance normalisee
        """
        try:
            # Normalize patches
            p1_lines = [line.strip() for line in patch1.split('\n') if line.strip()]
            p2_lines = [line.strip() for line in patch2.split('\n') if line.strip()]

            # Compute similarity
            matcher = SequenceMatcher(None, p1_lines, p2_lines)
            return matcher.ratio()
        except (ValueError, TypeError) as e:
            print(f"Warning: Failed to compute patch similarity: {e}")
            return 0.0
