---
title: "[Feature] Implement Transformer for format conversion pipeline"
labels: enhancement, feature, htn-planning, priority-p1
assignees:
milestone: HTN Orchestration Refactor
---

## Summary

Implement a `Transformer` class that converts `TypedResult` from one format to another, enabling document format changes and data transformations within the HTN pipeline.

## Problem

Currently, format conversion requires:
- Custom tool implementation for each conversion
- Manual handling of intermediate formats
- No standard interface for transformations
- Lost metadata during conversions

## Proposed Solution

Create `planner/transformer.py`:

```python
class TransformationType(str, Enum):
    # Format conversions
    TO_JSON = "to_json"
    TO_CSV = "to_csv"
    TO_EXCEL = "to_excel"
    TO_PDF = "to_pdf"
    TO_MARKDOWN = "to_markdown"
    TO_HTML = "to_html"

    # Data transformations
    EXTRACT_FIELDS = "extract_fields"
    FILTER_ROWS = "filter_rows"
    MAP_VALUES = "map_values"
    SORT_BY = "sort_by"
    GROUP_BY = "group_by"

    # Custom
    CUSTOM = "custom"

@dataclass
class Transformer:
    transformation: TransformationType
    config: Dict[str, Any] = field(default_factory=dict)
    preserve_metadata: bool = True

    def transform(self, input_result: TypedResult) -> TypedResult:
        """Apply transformation to input result."""
        ...

    def _to_excel(self, result: TypedResult) -> TypedResult: ...
    def _to_csv(self, result: TypedResult) -> TypedResult: ...
    def _to_pdf(self, result: TypedResult) -> TypedResult: ...
    def _extract_fields(self, result: TypedResult) -> TypedResult: ...
    def _filter_rows(self, result: TypedResult) -> TypedResult: ...
```

## Acceptance Criteria

- [ ] `TransformationType` enum with all transformation types
- [ ] `Transformer` dataclass with configuration
- [ ] Format conversions: JSON, CSV, Excel, PDF, Markdown, HTML
- [ ] Data transformations: extract, filter, map, sort, group
- [ ] `preserve_metadata` carries forward provenance info
- [ ] Custom transformer support via callable in config
- [ ] Error handling for incompatible input types
- [ ] Unit tests for each transformation

## Configuration Examples

```python
# To Excel with formatting
Transformer(
    transformation=TransformationType.TO_EXCEL,
    config={
        "sheet_name": "Financial Report",
        "include_header": True,
        "column_widths": {"A": 20, "B": 15}
    }
)

# Extract specific fields
Transformer(
    transformation=TransformationType.EXTRACT_FIELDS,
    config={
        "fields": ["id", "name", "total"],
        "rename": {"total": "amount"}
    }
)

# Filter rows
Transformer(
    transformation=TransformationType.FILTER_ROWS,
    config={
        "condition": "amount > 1000",  # Simple expression
        # OR
        "predicate": lambda row: row["amount"] > 1000
    }
)

# Chain transformations (via multiple tasks)
# Task 1: filter → Task 2: sort → Task 3: to_excel
```

## Technical Notes

- Excel: Use `openpyxl` (already in dependencies)
- PDF: Use existing PyPDF2 or add reportlab for generation
- CSV: Standard library `csv` module
- Handle binary data appropriately (BytesIO for Excel/PDF)
- Transformation metadata should track: original_type, transformation_chain

## Dependencies

- Depends on: #1 (TypedResult)
- Libraries: openpyxl (existing), reportlab (new, optional)

## Testing Requirements

```python
@pytest.mark.unit
class TestTransformer:
    def test_to_json_from_dict(self): ...
    def test_to_csv_from_table(self): ...
    def test_to_excel_from_json(self): ...
    def test_to_markdown_from_table(self): ...
    def test_extract_fields(self): ...
    def test_filter_rows_expression(self): ...
    def test_filter_rows_predicate(self): ...
    def test_sort_by_single_field(self): ...
    def test_sort_by_multiple_fields(self): ...
    def test_group_by(self): ...
    def test_metadata_preserved(self): ...
    def test_incompatible_input_error(self): ...

@pytest.mark.integration
class TestTransformerChain:
    def test_filter_then_excel(self): ...
    def test_aggregate_then_pdf(self): ...
```

## Estimated Effort

3-4 days

## Related Issues

- Depends on: #1 (TypedResult)
- Related: #4 (Aggregator) - often used after aggregation
- Related: #6 (OrchestrationPlan) - orchestrates transformers
