# FilAgent Benchmarks Guide

**Version**: 1.0.0
**Last Updated**: 2025-11-14
**Status**: Production Ready

## Table of Contents

1. [Overview](#overview)
2. [Available Benchmarks](#available-benchmarks)
3. [Quick Start](#quick-start)
4. [Running Benchmarks](#running-benchmarks)
5. [Metrics and Reporting](#metrics-and-reporting)
6. [CI/CD Integration](#cicd-integration)
7. [Custom Benchmarks](#custom-benchmarks)
8. [Troubleshooting](#troubleshooting)
9. [Performance Targets](#performance-targets)

---

## Overview

FilAgent utilizes a comprehensive benchmark suite to evaluate and track performance across multiple dimensions:

- **Code Generation**: HumanEval, MBPP
- **Software Engineering**: SWE-bench
- **Compliance**: Decision Records, PII masking, WORM logging
- **HTN Planning**: Task decomposition, parallel execution
- **Tool Orchestration**: Multi-tool coordination, error handling

### Architecture

```
eval/
├── base.py                    # Base harness framework
├── humaneval.py               # HumanEval integration
├── mbpp.py                    # MBPP integration
├── runner.py                  # Centralized runner
├── metrics.py                 # Metrics aggregation
├── benchmarks/
│   ├── swe_bench/            # SWE-bench harness
│   └── custom/               # FilAgent-specific benchmarks
│       ├── compliance/
│       ├── htn_planning/
│       └── tool_orchestration/
├── reports/                   # Benchmark reports (JSON)
└── runs/                      # Execution logs
```

---

## Available Benchmarks

### 1. HumanEval

**Purpose**: Evaluate code generation capabilities
**Dataset**: 164 hand-written programming problems
**Metric**: pass@k (k=1, 10, 100)
**Target**: ≥65% pass@1

```bash
python eval/runner.py --benchmark humaneval
```

### 2. MBPP (Mostly Basic Python Problems)

**Purpose**: Evaluate basic Python programming
**Dataset**: 974 crowd-sourced Python problems
**Metric**: pass@k
**Target**: ≥60% pass@1

```bash
python eval/runner.py --benchmark mbpp
```

### 3. SWE-bench

**Purpose**: Evaluate software engineering capabilities
**Dataset**: Real-world GitHub issues from popular Python repos
**Metric**: Resolution rate
**Target**: ≥30% resolution rate (SWE-bench is challenging)

```bash
python eval/runner.py --benchmark swe_bench
```

### 4. Compliance Benchmark

**Purpose**: Validate governance and legal compliance
**Tests**: 10 critical compliance scenarios

**Test Coverage**:
- ✅ Decision Record generation
- ✅ PII masking in logs
- ✅ WORM logging
- ✅ Provenance tracking (PROV-JSON)
- ✅ RBAC enforcement
- ✅ Sensitive data handling
- ✅ Error handling compliance
- ✅ Audit trail completeness

**Target**: 100% pass rate (compliance is critical)

```bash
python eval/runner.py --benchmark compliance
```

### 5. HTN Planning Benchmark

**Purpose**: Evaluate hierarchical task network planning
**Tests**: 10 planning scenarios

**Test Coverage**:
- Sequential task execution
- Parallel task execution
- Mixed (parallel + sequential)
- Nested decomposition
- Error handling and fallback
- Dynamic replanning
- Resource-aware execution
- Long-running pipelines
- Verification at each step
- Adaptive strategy selection

**Target**: ≥90% success rate

```bash
python eval/runner.py --benchmark htn_planning
```

### 6. Tool Orchestration Benchmark

**Purpose**: Evaluate multi-tool coordination
**Tests**: 15 orchestration scenarios

**Test Coverage**:
- Tool selection
- Tool chaining (pipelines)
- Sandbox execution
- Security (dangerous code blocking)
- Timeout handling
- Error recovery
- Parallel tool execution
- Conditional tool selection
- Complex orchestration (5+ tools)
- Data transformation pipelines
- API integration
- Resource limits
- Tool versioning
- Transactional rollback

**Target**: ≥80% success rate

```bash
python eval/runner.py --benchmark tool_orchestration
```

---

## Quick Start

### Installation

Benchmarks are included in the main FilAgent installation:

```bash
# Clone repository
git clone https://github.com/fil04331/FilAgent.git
cd FilAgent

# Install dependencies
pip install -r requirements.txt

# Initialize database
python -c "from memory.episodic import create_tables; create_tables()"
```

### Run Your First Benchmark

```bash
# Run a quick compliance check (fast)
python eval/runner.py --benchmark compliance --verbose

# Run HumanEval on 10 tasks
python eval/runner.py --benchmark humaneval --num-tasks 10 --verbose

# Run all custom FilAgent benchmarks
python eval/runner.py --custom-only
```

---

## Running Benchmarks

### Command-Line Interface

The `eval/runner.py` script provides a unified interface for all benchmarks.

#### Run All Benchmarks

```bash
python eval/runner.py --all
```

#### Run Specific Benchmark

```bash
python eval/runner.py --benchmark humaneval
python eval/runner.py --benchmark mbpp
python eval/runner.py --benchmark swe_bench
python eval/runner.py --benchmark compliance
python eval/runner.py --benchmark htn_planning
python eval/runner.py --benchmark tool_orchestration
```

#### Run Multiple Benchmarks

```bash
python eval/runner.py --benchmark humaneval,mbpp,compliance
```

#### Limit Number of Tasks

```bash
# Run only 5 tasks (useful for quick tests)
python eval/runner.py --benchmark humaneval --num-tasks 5
```

#### Custom FilAgent Benchmarks Only

```bash
# Run compliance, HTN planning, and tool orchestration
python eval/runner.py --custom-only
```

#### Verbose Output

```bash
python eval/runner.py --benchmark compliance --verbose
```

### Programmatic Usage

```python
from eval.runner import BenchmarkRunner

# Create runner
runner = BenchmarkRunner()

# Create agent callback
def agent_callback(prompt: str) -> str:
    # Your agent implementation
    from runtime.agent import Agent
    agent = Agent()
    result = agent.run(prompt)
    return result['response']

# Run benchmark
result = runner.run_benchmark(
    benchmark_name='compliance',
    agent_callback=agent_callback,
    num_tasks=None,  # All tasks
    k=1,
    verbose=True
)

print(f"Pass rate: {result['pass_at_1']*100:.1f}%")
```

---

## Metrics and Reporting

### Automatic Report Generation

All benchmark runs automatically generate JSON reports in `eval/reports/`:

```
eval/reports/
├── humaneval_20251114_123456.json
├── mbpp_20251114_124500.json
├── compliance_20251114_125000.json
├── all_latest.json              # Latest aggregate report
└── dashboard_latest.json        # Latest metrics dashboard
```

### Report Structure

```json
{
  "benchmark": "HumanEval",
  "timestamp": "2025-11-14T12:34:56",
  "total_tasks": 164,
  "k": 1,
  "passed_at_k": 106,
  "failed": 58,
  "pass_at_1": 0.646,
  "avg_latency_ms": 1234.5,
  "results": [
    {
      "task_id": "HumanEval/0",
      "passed": true,
      "latency_ms": 1100.0,
      "error": null
    }
  ]
}
```

### Metrics Dashboard

Generate a comprehensive metrics dashboard:

```bash
# Generate dashboard for last 30 days
python eval/metrics.py --days 30

# Check for regressions
python eval/metrics.py --check-regressions

# View trend for specific benchmark
python eval/metrics.py --benchmark humaneval --days 30
```

#### Dashboard Output

```
📊 FilAgent Benchmarks Dashboard
============================================================

Generated: 2025-11-14T12:34:56
Period: Last 30 days

📈 Aggregate Statistics
────────────────────────────────────────────────────────────
Total Runs: 25
Average Pass Rate: 68.5%

📊 Per-Benchmark Trends
────────────────────────────────────────────────────────────
humaneval           :  65.0% (avg:  64.2%) ↗
mbpp                :  62.0% (avg:  61.5%) ↗
swe_bench           :  32.0% (avg:  31.0%) →
compliance          : 100.0% (avg: 100.0%) →
htn_planning        :  92.0% (avg:  90.5%) ↗
tool_orchestration  :  85.0% (avg:  83.0%) ↗

============================================================
```

### Regression Detection

The metrics system automatically detects performance regressions:

```bash
python eval/metrics.py --check-regressions
```

**Output**:
```
⚠ 1 regression(s) detected:

  - humaneval: 60.0% (drop: 5.2%)
```

A regression is detected when performance drops by more than 5% compared to recent average.

---

## CI/CD Integration

### GitHub Actions Workflow

The benchmark suite integrates with GitHub Actions for automated evaluation.

**File**: `.github/workflows/benchmarks.yml`

#### Triggers

1. **Weekly Schedule**: Every Sunday at 2 AM UTC
2. **Manual Trigger**: Via GitHub Actions UI
3. **On Push**: When eval/, runtime/, planner/, or tools/ changes (optional)

#### Manual Trigger

Go to **Actions** → **Benchmarks** → **Run workflow**

Options:
- **benchmark_name**: Specific benchmark (leave empty for all)
- **num_tasks**: Number of tasks per benchmark (leave empty for all)

#### Workflow Steps

1. ✅ Checkout code
2. ✅ Set up Python 3.10
3. ✅ Install dependencies
4. ✅ Initialize database
5. ✅ Run benchmarks (HumanEval, MBPP, SWE-bench, Custom)
6. ✅ Generate metrics dashboard
7. ✅ Check for regressions
8. ✅ Upload reports as artifacts
9. ✅ Comment on commit if regression detected

#### Viewing Results

**Artifacts**: Available for 90 days
- `benchmark-reports`: All JSON reports
- `regression-report`: Regression analysis

**Download**:
1. Go to **Actions** → Select workflow run
2. Scroll to **Artifacts**
3. Download `benchmark-reports.zip`

---

## Custom Benchmarks

### Creating a Custom Benchmark

1. **Create Harness Class**

```python
# eval/benchmarks/custom/my_benchmark/harness.py

from typing import List
from eval.base import BenchmarkHarness, BenchmarkTask, BenchmarkResult

class MyBenchmarkHarness(BenchmarkHarness):
    def __init__(self):
        super().__init__("MyBenchmark", "Description of my benchmark")

    def load_tasks(self) -> List[BenchmarkTask]:
        return [
            BenchmarkTask(
                id="my-001",
                prompt="Test prompt",
                ground_truth="Expected result",
                metadata={"test_type": "example"}
            )
        ]

    def evaluate(self, task: BenchmarkTask, response: str) -> BenchmarkResult:
        # Your evaluation logic
        passed = "expected" in response.lower()

        return BenchmarkResult(
            task_id=task.id,
            passed=passed,
            response=response,
            ground_truth=task.ground_truth
        )
```

2. **Register Benchmark**

```python
# eval/runner.py

from eval.benchmarks.custom.my_benchmark.harness import MyBenchmarkHarness

class BenchmarkRunner:
    def __init__(self, ...):
        # ...
        self.benchmarks = {
            # ...existing benchmarks
            'my_benchmark': MyBenchmarkHarness,
        }
```

3. **Run Your Benchmark**

```bash
python eval/runner.py --benchmark my_benchmark
```

### Example: Domain-Specific Benchmark

See `eval/benchmarks/custom/compliance/harness.py` for a complete example of a domain-specific benchmark with multiple test types.

---

## Troubleshooting

### Common Issues

#### 1. Dataset Download Fails

**Problem**: `Failed to load HumanEval dataset`

**Solution**:
```bash
# Manually download and cache
python -c "from datasets import load_dataset; load_dataset('openai_humaneval')"
```

#### 2. Out of Memory

**Problem**: Benchmark runs out of memory

**Solution**:
- Limit number of tasks: `--num-tasks 10`
- Run benchmarks separately instead of `--all`
- Increase system memory or use cloud instance

#### 3. Agent Initialization Fails

**Problem**: `Could not load agent`

**Solution**:
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check model weights are available: `ls models/weights/`
- Verify database is initialized

#### 4. Slow Execution

**Problem**: Benchmarks take too long

**Solution**:
- Use `--num-tasks` to limit tasks
- Run only custom benchmarks: `--custom-only`
- Use faster model for testing
- Enable parallel execution in config

### Debug Mode

```bash
# Run with verbose output
python eval/runner.py --benchmark compliance --verbose

# Check individual benchmark
python -c "
from eval.benchmarks.custom.compliance.harness import ComplianceHarness
harness = ComplianceHarness()
tasks = harness.load_tasks()
print(f'Loaded {len(tasks)} tasks')
"
```

---

## Performance Targets

### Industry Benchmarks

| Benchmark | Target | Status | Reference |
|-----------|--------|--------|-----------|
| HumanEval pass@1 | ≥65% | 🎯 | Codex level |
| MBPP pass@1 | ≥60% | 🎯 | ChatGPT-4 level |
| SWE-bench | ≥30% | 🎯 | SOTA for agents |

### FilAgent-Specific Targets

| Benchmark | Target | Priority | Rationale |
|-----------|--------|----------|-----------|
| Compliance | 100% | **CRITICAL** | Legal requirement |
| HTN Planning | ≥90% | High | Core capability |
| Tool Orchestration | ≥80% | High | Agent functionality |

### Acceptance Criteria

From `config/eval_targets.yaml`:

```yaml
acceptance_criteria:
  # Code generation
  code_generation: "pass_at_1_humaneval >= 0.65 AND pass_at_1_mbpp >= 0.60"

  # Agent capability
  agent_capability: "success_rate_agent_tasks >= 0.75"

  # Compliance (0 violations on 1000 tasks)
  compliance: "critical_violations == 0 AND total_tasks >= 1000"

  # Traceability (100% coverage)
  traceability: "response_with_dr_coverage >= 0.95 AND prov_coverage >= 0.95"
```

---

## Best Practices

### 1. Regular Evaluation

- Run weekly benchmarks via CI/CD
- Track trends over time
- Set up regression alerts

### 2. Incremental Testing

Start with small sets during development:

```bash
# Quick compliance check
python eval/runner.py --benchmark compliance

# Small code gen test
python eval/runner.py --benchmark humaneval --num-tasks 5
```

### 3. Comprehensive Pre-Release

Before releases, run full suite:

```bash
python eval/runner.py --all
python eval/metrics.py --check-regressions
```

### 4. Baseline Comparison

Always compare against baseline:

```bash
# Save baseline
cp eval/reports/all_latest.json eval/reports/baseline_v1.0.json

# Compare after changes
python eval/metrics.py --days 365
```

---

## References

- **HumanEval**: [Chen et al., 2021](https://arxiv.org/abs/2107.03374)
- **MBPP**: [Austin et al., 2021](https://arxiv.org/abs/2108.07732)
- **SWE-bench**: [Jimenez et al., 2023](https://www.swebench.com/)
- **FilAgent Architecture**: `docs/ADRs/`
- **Compliance Requirements**: `docs/COMPLIANCE_GUARDIAN.md`

---

## Support

- **Issues**: GitHub Issues
- **Documentation**: `/docs/`
- **Config**: `config/eval_targets.yaml`
- **CI/CD**: `.github/workflows/benchmarks.yml`

**Version**: 1.0.0
**Last Updated**: 2025-11-14
**Maintainer**: FilAgent Team
