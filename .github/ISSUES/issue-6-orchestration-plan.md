---
title: "[Feature] Implement OrchestrationPlan builder for multi-source pipelines"
labels: enhancement, feature, htn-planning, priority-p1
assignees:
milestone: HTN Orchestration Refactor
---

## Summary

Implement an `OrchestrationPlan` class that provides a high-level, fluent API for building multi-source data pipelines that compile to executable `TaskGraph` structures.

## Problem

Building complex HTN task graphs manually is:
- Error-prone (dependency management)
- Verbose (many Task instantiations)
- Not intuitive for common patterns (fetch → merge → transform → output)
- Hard to visualize the pipeline

## Proposed Solution

Create `planner/orchestration.py`:

```python
@dataclass
class SourceSpec:
    name: str
    action: str
    params: Dict[str, Any]
    output_schema: Optional[Dict] = None
    timeout_seconds: int = 60

@dataclass
class TransformSpec:
    name: str
    transformation: TransformationType
    input_source: str
    config: Dict[str, Any] = field(default_factory=dict)

@dataclass
class OrchestrationPlan:
    sources: List[SourceSpec] = field(default_factory=list)
    aggregation: Optional[AggregationStrategy] = None
    aggregation_config: Dict[str, Any] = field(default_factory=dict)
    transforms: List[TransformSpec] = field(default_factory=list)
    final_action: Optional[str] = None

    # Fluent API
    def add_source(self, name: str, action: str, params: Dict,
                   **kwargs) -> "OrchestrationPlan": ...

    def aggregate(self, strategy: AggregationStrategy,
                  **config) -> "OrchestrationPlan": ...

    def transform(self, name: str, transformation: TransformationType,
                  input_source: str, **config) -> "OrchestrationPlan": ...

    def finalize_with(self, action: str) -> "OrchestrationPlan": ...

    def compile(self) -> TaskGraph:
        """Compile to executable TaskGraph with proper dependencies."""
        ...

    def visualize(self) -> str:
        """Generate Mermaid diagram of the pipeline."""
        ...

    def validate(self) -> List[str]:
        """Validate plan structure, return list of errors."""
        ...
```

## Acceptance Criteria

- [ ] `SourceSpec` and `TransformSpec` dataclasses
- [ ] `OrchestrationPlan` with fluent builder API
- [ ] `add_source()` adds parallel data sources
- [ ] `aggregate()` configures multi-source merging
- [ ] `transform()` adds transformation steps with dependencies
- [ ] `compile()` generates valid `TaskGraph` with:
  - Sources as independent tasks (level 0)
  - Aggregation depending on all sources
  - Transforms chained with proper dependencies
- [ ] `visualize()` generates Mermaid flowchart
- [ ] `validate()` checks for: missing inputs, circular refs, invalid actions
- [ ] Integration tests for compile → execute flow

## Usage Examples

```python
# Example 1: Multi-source financial report
plan = (
    OrchestrationPlan()
    .add_source("revenue", "file_read", {"file_path": "revenue.json"})
    .add_source("expenses", "file_read", {"file_path": "expenses.json"})
    .add_source("forecast", "web_fetch", {"url": "https://api.example.com/forecast"})
    .aggregate(AggregationStrategy.DEEP_MERGE)
    .transform("filter", TransformationType.FILTER_ROWS,
               "aggregate_sources", condition="amount > 0")
    .transform("excel", TransformationType.TO_EXCEL,
               "filter", sheet_name="Q4 Report")
)

graph = plan.compile()
result = executor.execute(graph)

# Example 2: Document processing pipeline
plan = (
    OrchestrationPlan()
    .add_source("contract", "document_analyzer_pme",
                {"file_path": "contract.pdf", "analysis_type": "contract"})
    .transform("extract", TransformationType.EXTRACT_FIELDS,
               "contract", fields=["parties", "clauses", "dates"])
    .transform("report", TransformationType.TO_MARKDOWN, "extract")
)

# Visualize before executing
print(plan.visualize())
# ```mermaid
# graph TD
#     A[contract: document_analyzer_pme] --> B[extract: EXTRACT_FIELDS]
#     B --> C[report: TO_MARKDOWN]
# ```
```

## Technical Notes

- `compile()` must handle:
  - Empty sources (error)
  - Single source (no aggregation needed)
  - Transform referencing non-existent source (error)
  - Multiple transform chains (parallel post-aggregation)
- Thread-safe compilation (stateless)
- Consider plan caching by hash

## Dependencies

- Depends on: #1 (TypedResult), #2 (ResultReference), #4 (Aggregator), #5 (Transformer)
- Modifies: `planner/task_graph.py` (Task class for ResultReference support)

## Testing Requirements

```python
@pytest.mark.unit
class TestOrchestrationPlan:
    def test_single_source_compiles(self): ...
    def test_multiple_sources_parallel(self): ...
    def test_aggregation_depends_on_sources(self): ...
    def test_transform_chain_dependencies(self): ...
    def test_validate_missing_source_error(self): ...
    def test_validate_circular_ref_error(self): ...
    def test_visualize_mermaid(self): ...

@pytest.mark.integration
class TestOrchestrationExecution:
    def test_compile_and_execute(self): ...
    def test_parallel_sources_performance(self): ...
    def test_full_pipeline_revenue_report(self): ...
```

## Estimated Effort

3-4 days

## Related Issues

- Depends on: #1-#5 (all previous issues)
- Blocks: #7 (Enhanced HierarchicalPlanner)
