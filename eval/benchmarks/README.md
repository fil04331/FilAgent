# FilAgent Benchmarks

This directory contains all benchmark harnesses for evaluating FilAgent performance.

## Structure

```
benchmarks/
├── swe_bench/              # SWE-bench for software engineering
│   ├── harness.py
│   └── results/
└── custom/                 # FilAgent-specific benchmarks
    ├── compliance/         # Governance & legal compliance
    │   ├── harness.py
    │   └── tasks/
    ├── htn_planning/       # HTN planning capabilities
    │   ├── harness.py
    │   └── tasks/
    └── tool_orchestration/ # Multi-tool coordination
        ├── harness.py
        └── tasks/
```

## Available Benchmarks

### Industry Standard

- **HumanEval** (`eval/humaneval.py`): Code generation benchmark
- **MBPP** (`eval/mbpp.py`): Mostly Basic Python Problems
- **SWE-bench** (`swe_bench/`): Real-world GitHub issues

### FilAgent Custom

- **Compliance** (`custom/compliance/`): Decision Records, PII, WORM, RBAC
- **HTN Planning** (`custom/htn_planning/`): Task decomposition, parallel execution
- **Tool Orchestration** (`custom/tool_orchestration/`): Multi-tool coordination

## Quick Start

```bash
# Run all benchmarks
python eval/runner.py --all

# Run specific benchmark
python eval/runner.py --benchmark compliance

# Run custom benchmarks only
python eval/runner.py --custom-only
```

## Documentation

See `/docs/BENCHMARKS.md` for comprehensive documentation.

## Targets

| Benchmark | Target | Status |
|-----------|--------|--------|
| HumanEval | ≥65% pass@1 | 🎯 |
| MBPP | ≥60% pass@1 | 🎯 |
| SWE-bench | ≥30% resolution | 🎯 |
| Compliance | 100% | ✅ CRITICAL |
| HTN Planning | ≥90% | 🎯 |
| Tool Orchestration | ≥80% | 🎯 |

## Adding Custom Benchmarks

1. Create harness class extending `BenchmarkHarness`
2. Implement `load_tasks()` and `evaluate()`
3. Register in `eval/runner.py`
4. Add tests in `tests/test_benchmarks.py`

See existing custom benchmarks for examples.
