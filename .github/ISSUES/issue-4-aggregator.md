---
title: "[Feature] Implement Aggregator for multi-source result merging"
labels: enhancement, feature, htn-planning, priority-p1
assignees:
milestone: HTN Orchestration Refactor
---

## Summary

Implement an `Aggregator` class that combines results from multiple parallel tasks into a single structured output for downstream processing.

## Problem

When fetching data from multiple sources in parallel, there's no standard way to:
- Merge results into a unified structure
- Handle different merge strategies (dict merge, list concat, etc.)
- Map/rename keys from different sources
- Validate merged output

## Proposed Solution

Create `planner/aggregator.py`:

```python
class AggregationStrategy(str, Enum):
    MERGE_DICT = "merge_dict"       # Shallow dict merge
    DEEP_MERGE = "deep_merge"       # Recursive dict merge
    CONCAT_LIST = "concat_list"     # Concatenate lists
    UNION_SET = "union_set"         # Union of sets
    ZIP_RECORDS = "zip_records"     # Zip parallel arrays into records
    CUSTOM = "custom"               # Custom aggregator function

@dataclass
class Aggregator:
    strategy: AggregationStrategy
    source_tasks: List[str]
    output_key_mapping: Optional[Dict[str, str]] = None  # Rename keys
    conflict_resolution: str = "last_wins"  # or "first_wins", "error"
    custom_aggregator: Optional[Callable] = None

    def aggregate(self, task_results: Dict[str, TypedResult]) -> TypedResult:
        """Aggregate results from source_tasks into single TypedResult."""
        ...

    def _merge_dict(self, results: List[TypedResult]) -> Dict: ...
    def _deep_merge(self, results: List[TypedResult]) -> Dict: ...
    def _concat_list(self, results: List[TypedResult]) -> List: ...
    def _apply_key_mapping(self, data: Dict) -> Dict: ...
```

## Acceptance Criteria

- [ ] `AggregationStrategy` enum with 6 strategies
- [ ] `Aggregator` dataclass with configuration fields
- [ ] `aggregate()` method handles all strategy types
- [ ] `output_key_mapping` renames keys in output
- [ ] `conflict_resolution` handles key collisions in MERGE_DICT
- [ ] Custom aggregator support via callable
- [ ] Returns `TypedResult` with `result_type=AGGREGATED`
- [ ] Metadata tracks source task IDs
- [ ] Unit tests for each strategy

## Use Cases

```python
# Example 1: Merge financial data from multiple sources
aggregator = Aggregator(
    strategy=AggregationStrategy.MERGE_DICT,
    source_tasks=["fetch_revenue", "fetch_expenses", "fetch_taxes"],
    output_key_mapping={
        "total": "revenue_total",  # Rename 'total' from revenue task
    }
)

# Example 2: Concatenate records from paginated API
aggregator = Aggregator(
    strategy=AggregationStrategy.CONCAT_LIST,
    source_tasks=["page_1", "page_2", "page_3"]
)

# Example 3: Custom aggregation logic
aggregator = Aggregator(
    strategy=AggregationStrategy.CUSTOM,
    source_tasks=["source_a", "source_b"],
    custom_aggregator=lambda results: weighted_merge(results, weights=[0.7, 0.3])
)
```

## Technical Notes

- Deep merge should handle nested dicts recursively
- List concatenation preserves order (source_tasks order)
- Handle type mismatches gracefully (e.g., dict + list)
- Consider memory efficiency for large aggregations

## Dependencies

- Depends on: #1 (TypedResult), #3 (Enhanced TaskExecutor)

## Testing Requirements

```python
@pytest.mark.unit
class TestAggregator:
    def test_merge_dict_simple(self): ...
    def test_merge_dict_conflict_last_wins(self): ...
    def test_merge_dict_conflict_error(self): ...
    def test_deep_merge_nested(self): ...
    def test_concat_list(self): ...
    def test_union_set(self): ...
    def test_zip_records(self): ...
    def test_key_mapping(self): ...
    def test_custom_aggregator(self): ...
    def test_missing_source_task(self): ...
```

## Estimated Effort

2-3 days

## Related Issues

- Depends on: #1 (TypedResult), #3 (Enhanced TaskExecutor)
- Related: #5 (Transformer) - often used together
