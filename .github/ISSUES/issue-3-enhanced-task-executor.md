---
title: "[Refactor] Enhance TaskExecutor with automatic ResultReference resolution"
labels: enhancement, refactor, htn-planning, priority-p0
assignees:
milestone: HTN Orchestration Refactor
---

## Summary

Modify `TaskExecutor` to automatically resolve `ResultReference` objects in task parameters before execution, and wrap tool outputs in `TypedResult`.

## Problem

The current `TaskExecutor`:
- Passes parameters as-is without resolution
- Stores results as strings (truncated at 283 chars in debug)
- Cannot handle dependencies that require data from previous tasks
- No automatic type inference for tool outputs

## Proposed Solution

Modify `planner/executor.py`:

```python
class TaskExecutor:
    def __init__(self, ...):
        self.task_results: Dict[str, TypedResult] = {}  # Changed from Any

    def _resolve_params(self, task: Task) -> Dict[str, Any]:
        """Resolve ResultReferences in task params to actual values."""
        resolved = {}
        for key, value in task.params.items():
            if isinstance(value, ResultReference):
                resolved[key] = value.resolve(self.task_results)
            else:
                resolved[key] = value
        return resolved

    def _execute_task(self, task: Task) -> TypedResult:
        """Execute task with param resolution and result wrapping."""
        resolved_params = self._resolve_params(task)
        raw_result = self.actions[task.action](**resolved_params)
        return self._wrap_result(raw_result, task)

    def _wrap_result(self, raw_result: Any, task: Task) -> TypedResult:
        """Convert raw tool output to TypedResult with type inference."""
        ...

    def _infer_result_type(self, result: Any) -> ResultType:
        """Infer ResultType from raw value."""
        ...
```

## Acceptance Criteria

- [ ] `task_results` stores `TypedResult` instead of raw values
- [ ] `_resolve_params()` resolves all `ResultReference` objects
- [ ] `_wrap_result()` converts `ToolResult` to `TypedResult`
- [ ] `_infer_result_type()` correctly identifies JSON, TABLE, BINARY, TEXT
- [ ] Execution flow: resolve → execute → wrap → store
- [ ] Backward compatible with existing tools (no changes to tool code)
- [ ] Integration tests for param resolution chain
- [ ] No result truncation in storage

## Technical Notes

- Handle nested `ResultReference` in dict/list params
- Type inference heuristics:
  - Dict/List → JSON
  - bytes → BINARY
  - str with CSV pattern → TABLE
  - Default → TEXT
- Preserve original `ToolResult.metadata` in `TypedResult.metadata`

## Dependencies

- Depends on: #1 (TypedResult), #2 (ResultReference)

## Testing Requirements

```python
@pytest.mark.integration
class TestTaskExecutorResolution:
    def test_resolve_single_reference(self): ...
    def test_resolve_nested_references(self): ...
    def test_wrap_tool_result_json(self): ...
    def test_wrap_tool_result_binary(self): ...
    def test_execution_chain_two_tasks(self): ...
    def test_execution_chain_three_tasks(self): ...
    def test_parallel_execution_with_references(self): ...
    def test_backward_compatible_no_references(self): ...
```

## Estimated Effort

3-4 days

## Related Issues

- Depends on: #1 (TypedResult), #2 (ResultReference)
- Blocks: #4 (Aggregator), #5 (Transformer)
