import os
from typing import List
from datasets import load_dataset, load_from_disk
from eval.base import BenchmarkHarness, BenchmarkTask, BenchmarkResult
from tools.python_sandbox import PythonSandboxTool

class HumanEvalHarness(BenchmarkHarness):
    def __init__(self):
        super().__init__("HumanEval", "HumanEval benchmark for code generation")
        self.dataset_path = "eval/benchmarks/humaneval"
        if not os.path.exists(self.dataset_path):
            self.dataset = load_dataset("openai_humaneval")
            self.dataset.save_to_disk(self.dataset_path)
        else:
            self.dataset = load_from_disk(self.dataset_path)
        self.sandbox = PythonSandboxTool()

    def load_tasks(self) -> List[BenchmarkTask]:
        tasks = []
        for item in self.dataset['test']:
            tasks.append(
                BenchmarkTask(
                    id=item['task_id'],
                    prompt=item['prompt'],
                    ground_truth=item['canonical_solution'],
                    metadata={
                        'entry_point': item['entry_point'],
                        'test': item['test'],
                    },
                )
            )
        return tasks

    def evaluate(self, task: BenchmarkTask, response: str) -> BenchmarkResult:
        full_code = f"{task.prompt}\n{response}\n{task.metadata['test']}"

        # We need to allow imports for the tests to run
        original_dangerous_patterns = self.sandbox.dangerous_patterns
        self.sandbox.dangerous_patterns = [p for p in self.sandbox.dangerous_patterns if p != '__import__']

        result = self.sandbox.execute({"code": full_code})

        # Reset the dangerous patterns
        self.sandbox.dangerous_patterns = original_dangerous_patterns

        return BenchmarkResult(
            task_id=task.id,
            passed=result.status == 'SUCCESS',
            response=response,
            ground_truth=task.ground_truth,
            error=result.error,
            metadata=result.metadata,
        )
