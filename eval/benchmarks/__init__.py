"""
Benchmarks package for FilAgent evaluation

Includes:
- HumanEval: Code generation benchmark (openai_humaneval)
- MBPP: Mostly Basic Python Problems
- SWE-bench: Software Engineering benchmark
- Custom FilAgent benchmarks:
  - Compliance: Decision Records, PII masking, WORM logging
  - HTN Planning: Task decomposition and execution
  - Tool Orchestration: Multi-tool coordination
"""

__all__ = [
    'HumanEvalHarness',
    'MBPPHarness',
    'SWEBenchHarness',
    'ComplianceHarness',
    'HTNPlanningHarness',
    'ToolOrchestrationHarness',
]
