---
title: "[Refactor] Implement TypedResult class for structured result preservation"
labels: enhancement, refactor, htn-planning, priority-p0
assignees:
milestone: HTN Orchestration Refactor
---

## Summary

Implement a `TypedResult` class that preserves type information through the HTN execution pipeline, replacing string-only `ToolResult.output`.

## Problem

Currently, all tool outputs are converted to strings in `ToolResult`, losing:
- Type information (JSON structure, tables, binary data)
- Schema validation capability
- Efficient extraction of nested values
- Merge/aggregation capabilities

## Proposed Solution

Create `planner/typed_result.py` with:

```python
@dataclass
class TypedResult:
    value: Any                              # Raw value (typed)
    result_type: ResultType                 # TEXT, JSON, BINARY, TABLE, DOCUMENT, AGGREGATED
    schema: Optional[Dict[str, Any]] = None # JSON schema for validation
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_task_id: Optional[str] = None    # Origin task for provenance

    def as_text(self) -> str: ...
    def extract(self, path: str) -> Any: ...  # JSONPath-like extraction
    def validate_schema(self) -> bool: ...
    def merge_with(self, other: "TypedResult") -> "TypedResult": ...
```

## Acceptance Criteria

- [ ] `TypedResult` dataclass with all fields implemented
- [ ] `ResultType` enum with 6 types: TEXT, JSON, BINARY, TABLE, DOCUMENT, AGGREGATED
- [ ] `as_text()` serializes all types to string (for LLM context)
- [ ] `extract(path)` supports dot notation and array indexing (`data.items[0].name`)
- [ ] `validate_schema()` validates against JSON schema if provided
- [ ] `merge_with()` combines two TypedResults intelligently
- [ ] Unit tests with >90% coverage
- [ ] Documentation with usage examples

## Technical Notes

- Use `jsonpath-ng` or custom parser for `extract()`
- Handle edge cases: None values, empty containers, circular references
- Consider memory efficiency for large binary data (lazy loading?)

## Dependencies

None (foundational component)

## Testing Requirements

```python
@pytest.mark.unit
class TestTypedResult:
    def test_json_serialization(self): ...
    def test_extract_nested_path(self): ...
    def test_extract_array_index(self): ...
    def test_merge_dicts(self): ...
    def test_merge_lists(self): ...
    def test_schema_validation_pass(self): ...
    def test_schema_validation_fail(self): ...
    def test_binary_to_text(self): ...
```

## Estimated Effort

2-3 days

## Related Issues

- Blocks: #2 (ResultReference), #3 (Enhanced TaskExecutor)
