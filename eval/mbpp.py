import os
from typing import List
from datasets import load_dataset, load_from_disk
from eval.base import BenchmarkHarness, BenchmarkTask, BenchmarkResult
from tools.python_sandbox import PythonSandboxTool

class MBPPHarness(BenchmarkHarness):
    def __init__(self):
        super().__init__("MBPP", "MBPP benchmark for code generation")
        self.dataset_path = "eval/benchmarks/mbpp"
        if not os.path.exists(self.dataset_path):
            self.dataset = load_dataset("mbpp")
            self.dataset.save_to_disk(self.dataset_path)
        else:
            self.dataset = load_from_disk(self.dataset_path)
        self.sandbox = PythonSandboxTool()

    def load_tasks(self) -> List[BenchmarkTask]:
        tasks = []
        for item in self.dataset['test']:
            tasks.append(
                BenchmarkTask(
                    id=str(item['task_id']),
                    prompt=item['text'],
                    ground_truth=item['code'],
                    metadata={
                        'test_list': item['test_list'],
                        'test_setup_code': item['test_setup_code'],
                    },
                )
            )
        return tasks

    def evaluate(self, task: BenchmarkTask, response: str) -> BenchmarkResult:
        full_code = (
            f"{task.metadata['test_setup_code']}\n"
            f"{response}\n"
            f"{'\\n'.join(task.metadata['test_list'])}\n"
        )

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
