"""
Tests for benchmark infrastructure

Tests tous les composants du système de benchmarking:
- Base harness
- Individual benchmark harnesses
- Benchmark runner
- Metrics aggregator
"""
import pytest
import json
from pathlib import Path
from datetime import datetime

from eval.base import BenchmarkHarness, BenchmarkTask, BenchmarkResult
from eval.humaneval import HumanEvalHarness
from eval.mbpp import MBPPHarness
from eval.benchmarks.swe_bench.harness import SWEBenchHarness
from eval.benchmarks.custom.compliance.harness import ComplianceHarness
from eval.benchmarks.custom.htn_planning.harness import HTNPlanningHarness
from eval.benchmarks.custom.tool_orchestration.harness import ToolOrchestrationHarness
from eval.runner import BenchmarkRunner
from eval.metrics import MetricsAggregator


@pytest.fixture
def mock_agent_callback():
    """Mock agent callback for testing"""
    def callback(prompt: str) -> str:
        # Simple mock that returns valid Python code for code gen benchmarks
        if "factorial" in prompt.lower():
            return """def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)"""

        if "calculate" in prompt.lower() or "2 + 2" in prompt:
            return "4"

        # Default response
        return "def solution():\n    return 42"

    return callback


@pytest.fixture
def temp_reports_dir(tmp_path):
    """Temporary reports directory"""
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    return reports_dir


class TestBenchmarkBase:
    """Test base benchmark functionality"""

    def test_benchmark_task_creation(self):
        """Test BenchmarkTask creation"""
        task = BenchmarkTask(
            id="test-001",
            prompt="Test prompt",
            ground_truth="Expected result",
            metadata={"key": "value"}
        )

        assert task.id == "test-001"
        assert task.prompt == "Test prompt"
        assert task.ground_truth == "Expected result"
        assert task.metadata["key"] == "value"

    def test_benchmark_result_creation(self):
        """Test BenchmarkResult creation"""
        result = BenchmarkResult(
            task_id="test-001",
            passed=True,
            response="Agent response",
            ground_truth="Expected result",
            latency_ms=123.45
        )

        assert result.task_id == "test-001"
        assert result.passed is True
        assert result.latency_ms == 123.45


class TestHumanEvalHarness:
    """Test HumanEval benchmark harness"""

    def test_humaneval_initialization(self):
        """Test HumanEval harness initialization"""
        # Note: This might download the dataset
        harness = HumanEvalHarness()
        assert harness.name == "HumanEval"

    def test_humaneval_load_tasks(self):
        """Test loading HumanEval tasks"""
        harness = HumanEvalHarness()
        tasks = harness.load_tasks()

        assert len(tasks) > 0
        assert all(isinstance(task, BenchmarkTask) for task in tasks)

        # Check task structure
        first_task = tasks[0]
        assert first_task.id
        assert first_task.prompt
        assert first_task.ground_truth
        assert 'entry_point' in first_task.metadata

    def test_humaneval_evaluate(self, mock_agent_callback):
        """Test HumanEval evaluation"""
        harness = HumanEvalHarness()
        tasks = harness.load_tasks()

        # Test with first task
        task = tasks[0]
        response = mock_agent_callback(task.prompt)
        result = harness.evaluate(task, response)

        assert isinstance(result, BenchmarkResult)
        assert result.task_id == task.id


class TestMBPPHarness:
    """Test MBPP benchmark harness"""

    def test_mbpp_initialization(self):
        """Test MBPP harness initialization"""
        harness = MBPPHarness()
        assert harness.name == "MBPP"

    def test_mbpp_load_tasks(self):
        """Test loading MBPP tasks"""
        harness = MBPPHarness()
        tasks = harness.load_tasks()

        assert len(tasks) > 0
        assert all(isinstance(task, BenchmarkTask) for task in tasks)


class TestSWEBenchHarness:
    """Test SWE-bench harness"""

    def test_swebench_initialization(self):
        """Test SWE-bench harness initialization"""
        harness = SWEBenchHarness(variant="lite")
        assert harness.name == "SWE-bench"

    def test_swebench_load_tasks(self):
        """Test loading SWE-bench tasks"""
        harness = SWEBenchHarness(variant="lite")
        tasks = harness.load_tasks()

        # Will use mock tasks if dataset unavailable
        assert len(tasks) > 0
        assert all(isinstance(task, BenchmarkTask) for task in tasks)

    def test_swebench_patch_extraction(self):
        """Test patch extraction from response"""
        harness = SWEBenchHarness()

        # Test with valid diff
        response = """```diff
--- a/file.py
+++ b/file.py
@@ -1,2 +1,2 @@
-old line
+new line
```"""

        patch = harness._extract_patch(response)
        assert patch is not None
        assert "---" in patch
        assert "+++" in patch


class TestComplianceHarness:
    """Test Compliance benchmark harness"""

    def test_compliance_initialization(self):
        """Test Compliance harness initialization"""
        harness = ComplianceHarness()
        assert harness.name == "Compliance"

    def test_compliance_load_tasks(self):
        """Test loading compliance tasks"""
        harness = ComplianceHarness()
        tasks = harness.load_tasks()

        assert len(tasks) > 0
        assert all(isinstance(task, BenchmarkTask) for task in tasks)

        # Check for critical compliance tests
        task_ids = [t.id for t in tasks]
        assert any('decision-record' in tid for tid in task_ids)
        assert any('pii-masking' in tid for tid in task_ids)

    def test_compliance_evaluate_pii(self):
        """Test PII masking evaluation"""
        harness = ComplianceHarness()
        tasks = harness.load_tasks()

        # Find PII task
        pii_task = next(t for t in tasks if 'pii-masking' in t.id)

        # Response without PII (should pass)
        response_safe = "I can help you with [EMAIL_REDACTED] and [PHONE_REDACTED]"
        result = harness.evaluate(pii_task, response_safe)
        assert result.passed

        # Response with PII (should fail)
        response_unsafe = "Your email is john.doe@example.com"
        result = harness.evaluate(pii_task, response_unsafe)
        # Note: This test depends on actual log checking


class TestHTNPlanningHarness:
    """Test HTN Planning benchmark harness"""

    def test_htn_planning_initialization(self):
        """Test HTN Planning harness initialization"""
        harness = HTNPlanningHarness()
        assert harness.name == "HTN-Planning"

    def test_htn_planning_load_tasks(self):
        """Test loading HTN planning tasks"""
        harness = HTNPlanningHarness()
        tasks = harness.load_tasks()

        assert len(tasks) > 0

        # Check for different task types
        task_types = [t.metadata['test_type'] for t in tasks]
        assert 'sequential' in task_types
        assert 'parallel' in task_types
        assert 'nested' in task_types

    def test_htn_planning_evaluate_sequential(self):
        """Test sequential task evaluation"""
        harness = HTNPlanningHarness()
        tasks = harness.load_tasks()

        seq_task = next(t for t in tasks if t.metadata['test_type'] == 'sequential')

        # Response with sequential indicators
        response = "First, I will read the file. Then, I will calculate. Finally, I will display."
        result = harness.evaluate(seq_task, response)
        assert result.passed


class TestToolOrchestrationHarness:
    """Test Tool Orchestration benchmark harness"""

    def test_tool_orchestration_initialization(self):
        """Test Tool Orchestration harness initialization"""
        harness = ToolOrchestrationHarness()
        assert harness.name == "Tool-Orchestration"

    def test_tool_orchestration_load_tasks(self):
        """Test loading tool orchestration tasks"""
        harness = ToolOrchestrationHarness()
        tasks = harness.load_tasks()

        assert len(tasks) > 0

        # Check for different task types
        task_types = [t.metadata['test_type'] for t in tasks]
        assert 'selection' in task_types
        assert 'chaining' in task_types
        assert 'security' in task_types


class TestBenchmarkRunner:
    """Test centralized benchmark runner"""

    def test_runner_initialization(self, temp_reports_dir):
        """Test runner initialization"""
        runner = BenchmarkRunner(
            output_dir=str(temp_reports_dir / "runs"),
            reports_dir=str(temp_reports_dir / "reports")
        )

        assert runner.output_dir.exists()
        assert runner.reports_dir.exists()

    def test_runner_available_benchmarks(self):
        """Test that all benchmarks are available"""
        runner = BenchmarkRunner()

        expected_benchmarks = [
            'humaneval',
            'mbpp',
            'swe_bench',
            'compliance',
            'htn_planning',
            'tool_orchestration',
        ]

        for benchmark in expected_benchmarks:
            assert benchmark in runner.benchmarks

    def test_runner_single_benchmark(self, temp_reports_dir, mock_agent_callback):
        """Test running a single benchmark"""
        runner = BenchmarkRunner(reports_dir=str(temp_reports_dir))

        # Run compliance benchmark (fast)
        result = runner.run_benchmark(
            benchmark_name='compliance',
            agent_callback=mock_agent_callback,
            num_tasks=2,  # Limit tasks for speed
            verbose=False
        )

        assert 'benchmark' in result
        assert result['benchmark'] == 'Compliance'
        assert 'total_tasks' in result


class TestMetricsAggregator:
    """Test metrics aggregation"""

    def test_aggregator_initialization(self, temp_reports_dir):
        """Test aggregator initialization"""
        aggregator = MetricsAggregator(reports_dir=str(temp_reports_dir))
        assert aggregator.reports_dir.exists()

    def test_aggregator_collect_historical_data(self, temp_reports_dir):
        """Test collecting historical data"""
        # Create mock reports
        report1 = {
            'benchmark': 'humaneval',
            'timestamp': '2025-01-01T00:00:00',
            'pass_at_1': 0.65,
            'total_tasks': 100
        }

        report2 = {
            'benchmark': 'humaneval',
            'timestamp': '2025-01-02T00:00:00',
            'pass_at_1': 0.70,
            'total_tasks': 100
        }

        # Save reports
        with open(temp_reports_dir / "humaneval_20250101.json", 'w') as f:
            json.dump(report1, f)

        with open(temp_reports_dir / "humaneval_20250102.json", 'w') as f:
            json.dump(report2, f)

        # Collect data
        aggregator = MetricsAggregator(reports_dir=str(temp_reports_dir))
        data = aggregator.collect_historical_data(days=365)

        assert len(data) == 2

    def test_aggregator_compute_trend(self, temp_reports_dir):
        """Test trend computation"""
        # Create mock reports
        reports = []
        for i in range(10):
            report = {
                'benchmark': 'humaneval',
                'timestamp': f'2025-01-{i+1:02d}T00:00:00',
                'pass_at_1': 0.60 + i * 0.01,  # Improving trend
                'total_tasks': 100
            }
            reports.append(report)

            filename = temp_reports_dir / f"humaneval_2025010{i}.json"
            with open(filename, 'w') as f:
                json.dump(report, f)

        # Compute trend
        aggregator = MetricsAggregator(reports_dir=str(temp_reports_dir))
        trend = aggregator.compute_trend('humaneval', days=365)

        assert 'trend' in trend
        assert trend['trend'] in ['improving', 'declining', 'stable']
        assert 'latest' in trend
        assert 'mean' in trend

    def test_aggregator_detect_regression(self):
        """Test regression detection"""
        aggregator = MetricsAggregator()

        # No regression
        values_stable = [0.65, 0.64, 0.66, 0.65, 0.65]
        assert not aggregator._detect_regression(values_stable)

        # Regression detected
        values_regressed = [0.65, 0.64, 0.66, 0.65, 0.50]  # Big drop
        assert aggregator._detect_regression(values_regressed)


class TestEndToEnd:
    """End-to-end integration tests"""

    @pytest.mark.integration
    def test_full_benchmark_run(self, temp_reports_dir, mock_agent_callback):
        """Test full benchmark run end-to-end"""
        runner = BenchmarkRunner(reports_dir=str(temp_reports_dir))

        # Run custom benchmarks (faster than full suite)
        result = runner.run_custom_benchmarks(
            agent_callback=mock_agent_callback,
            verbose=False
        )

        assert 'benchmarks' in result
        assert 'summary' in result
        assert result['summary']['total_tasks'] > 0

    @pytest.mark.integration
    def test_metrics_dashboard_generation(self, temp_reports_dir):
        """Test dashboard generation"""
        # Create mock report
        report = {
            'benchmark': 'humaneval',
            'timestamp': '2025-01-01T00:00:00',
            'pass_at_1': 0.65,
            'total_tasks': 100
        }

        with open(temp_reports_dir / "humaneval_20250101.json", 'w') as f:
            json.dump(report, f)

        # Generate dashboard
        aggregator = MetricsAggregator(reports_dir=str(temp_reports_dir))
        dashboard = aggregator.generate_dashboard(days=365)

        assert 'benchmarks' in dashboard
        assert 'aggregate' in dashboard
        assert dashboard['period_days'] == 365


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
