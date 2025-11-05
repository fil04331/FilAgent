import os
from typing import List
from datasets import load_dataset, load_from_disk
from filelock import FileLock
from eval.base import BenchmarkHarness, BenchmarkTask, BenchmarkResult
from tools.python_sandbox import PythonSandboxTool


class MBPPHarness(BenchmarkHarness):
    def __init__(self):
        super().__init__("MBPP", "MBPP benchmark for code generation")
        self.dataset_path = "eval/benchmarks/mbpp"
        lock_path = f"{self.dataset_path}.lock"

        # Use filelock to prevent race conditions during dataset download
        with FileLock(lock_path):
            if not os.path.exists(self.dataset_path):
                self.dataset = load_dataset("mbpp")
                self.dataset.save_to_disk(self.dataset_path)
            else:
                self.dataset = load_from_disk(self.dataset_path)

    def load_tasks(self) -> List[BenchmarkTask]:
        tasks = []
        for item in self.dataset["test"]:
            tasks.append(
                BenchmarkTask(
                    id=str(item["task_id"]),
                    prompt=item["text"],
                    ground_truth=item["code"],
                    metadata={
                        "test_list": item["test_list"],
                        "test_setup_code": item["test_setup_code"],
                    },
                )
            )
        return tasks

    def evaluate(self, task: BenchmarkTask, response: str) -> BenchmarkResult:
        test_code = "\n".join(task.metadata["test_list"])
        full_code = f"{task.metadata['test_setup_code']}\n" f"{response}\n" f"{test_code}\n"

        # Create a new sandbox with modified dangerous_patterns to allow imports
        # This is necessary for tests to run properly
        safe_patterns = [
            "eval(",
            "exec(",
            "open(",
            "file(",
            "os.system",
            "subprocess",
            "pickle",
        ]
        sandbox = PythonSandboxTool(dangerous_patterns=safe_patterns)

        result = sandbox.execute({"code": full_code})

        return BenchmarkResult(
            task_id=task.id,
            passed=result.status == "SUCCESS",
            response=response,
            ground_truth=task.ground_truth,
            error=result.error,
            metadata=result.metadata,
        )
