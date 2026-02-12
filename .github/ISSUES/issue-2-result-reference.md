---
title: "[Refactor] Implement ResultReference for declarative result chaining"
labels: enhancement, refactor, htn-planning, priority-p0
assignees:
milestone: HTN Orchestration Refactor
---

## Summary

Implement a `ResultReference` class that enables declarative chaining between tasks, allowing task parameters to reference outputs from previous tasks.

## Problem

Currently, task parameters must be explicitly specified at planning time. There's no mechanism to:
- Reference output from a completed task
- Extract specific fields from previous results
- Apply transformations during parameter injection

This forces manual parameter wiring or LLM-based text parsing (error-prone).

## Proposed Solution

Create `planner/result_reference.py` with:

```python
@dataclass
class ResultReference:
    source_task_id: str                   # Task ID to reference
    extract_path: Optional[str] = None    # JSONPath extraction (e.g., "data.rows")
    transform: Optional[str] = None       # Optional transformation ("to_json", "to_csv")

    def resolve(self, task_results: Dict[str, TypedResult]) -> Any:
        """Resolve reference to actual value from completed tasks."""
        ...

    def _apply_transform(self, value: Any) -> Any:
        """Apply transformation to extracted value."""
        ...

class ResolutionError(Exception):
    """Raised when a ResultReference cannot be resolved."""
    pass
```

## Acceptance Criteria

- [ ] `ResultReference` dataclass with all fields
- [ ] `resolve()` fetches value from `task_results` dictionary
- [ ] `extract_path` supports JSONPath-like syntax
- [ ] `transform` supports: `to_json`, `to_csv`, `to_string`, `to_list`
- [ ] `ResolutionError` raised when source task not found or extraction fails
- [ ] Serialization support (for plan persistence)
- [ ] Unit tests with >90% coverage

## Technical Notes

- Must handle missing tasks gracefully with clear error messages
- Support both `TypedResult` and raw values in `task_results`
- Thread-safe resolution (concurrent task execution)

## Dependencies

- Depends on: #1 (TypedResult)

## Testing Requirements

```python
@pytest.mark.unit
class TestResultReference:
    def test_resolve_simple(self): ...
    def test_resolve_with_extraction(self): ...
    def test_resolve_with_transform(self): ...
    def test_resolve_missing_task_raises(self): ...
    def test_resolve_invalid_path_raises(self): ...
    def test_chained_extraction(self): ...
    def test_serialization_roundtrip(self): ...
```

## Estimated Effort

1-2 days

## Related Issues

- Depends on: #1 (TypedResult)
- Blocks: #3 (Enhanced TaskExecutor)
