---
title: "[Feature] Enhance HierarchicalPlanner with orchestration detection and planning"
labels: enhancement, feature, htn-planning, priority-p2
assignees:
milestone: HTN Orchestration Refactor
---

## Summary

Enhance `HierarchicalPlanner` to detect multi-source orchestration queries and generate `OrchestrationPlan` structures automatically using LLM-based analysis.

## Problem

The current planner:
- Only generates flat task lists or simple dependency chains
- Cannot identify multi-source fetch patterns
- Doesn't recognize transformation/format requirements
- No support for generating OrchestrationPlan from natural language

## Proposed Solution

Modify `planner/planner.py`:

```python
class HierarchicalPlanner:

    def plan(self, query: str, strategy: PlanningStrategy,
             context: Optional[Dict] = None) -> PlanningResult:
        """Enhanced plan method with orchestration detection."""

        # Check if orchestration is needed
        if self._detect_orchestration_need(query):
            return self._plan_orchestration(query, context)

        # Fall back to existing planning logic
        return self._plan_standard(query, strategy, context)

    def _detect_orchestration_need(self, query: str) -> bool:
        """Detect if query requires multi-source orchestration."""
        indicators = [
            # Multi-source patterns
            r"(from|get|fetch|read).+(and|,).+(from|get|fetch|read)",
            r"combine|merge|aggregate|join",
            r"multiple (sources|files|apis)",

            # Transformation patterns
            r"convert to|export as|transform to|format as",
            r"(then|and then|after that).+(create|generate|export)",

            # Output format requirements
            r"(excel|pdf|csv|json|markdown) (file|format|output)"
        ]
        return any(re.search(pattern, query, re.IGNORECASE) for pattern in indicators)

    def _plan_orchestration(self, query: str, context: Dict) -> PlanningResult:
        """Generate OrchestrationPlan from natural language query."""
        ...

    def plan_orchestration(self, query: str,
                          context: Optional[Dict] = None) -> OrchestrationPlan:
        """Direct orchestration planning API."""
        ...
```

## Acceptance Criteria

- [ ] `_detect_orchestration_need()` identifies multi-source patterns
- [ ] `_plan_orchestration()` generates `OrchestrationPlan` from query
- [ ] LLM prompt extracts: sources, aggregation strategy, transforms, output format
- [ ] JSON schema validation for LLM response
- [ ] Fallback to rule-based detection if LLM fails
- [ ] `plan_orchestration()` public API for explicit orchestration
- [ ] Integration with existing `plan()` method (backward compatible)
- [ ] E2E tests for natural language → execution

## LLM Prompt Design

```python
ORCHESTRATION_SYSTEM_PROMPT = """
Analyze the user query and extract orchestration components.

Return JSON with structure:
{
    "is_orchestration": true/false,
    "sources": [
        {
            "name": "descriptive_name",
            "action": "tool_name",  // file_read, web_fetch, document_analyzer_pme, etc.
            "params": {}
        }
    ],
    "aggregation": {
        "strategy": "merge_dict",
        "config": {}
    },
    "transforms": [
        {
            "name": "step_name",
            "type": "to_excel",
            "input": "source_name or previous_transform_name",
            "config": {}
        }
    ],
    "final_format": "text|json|excel|pdf|csv|markdown"
}

Available tools:
- file_read: Read files from disk (params: file_path)
- web_fetch: Fetch from URL (params: url)
- document_analyzer_pme: Analyze PDF/DOCX/XLSX (params: file_path, analysis_type)
- python_sandbox: Execute Python code (params: code)
- math_calculator: Calculate expressions (params: expression)

Example query: "Read revenue.json and expenses.csv, merge them, and export as Excel"
Example output:
{
    "is_orchestration": true,
    "sources": [
        {"name": "revenue", "action": "file_read", "params": {"file_path": "revenue.json"}},
        {"name": "expenses", "action": "file_read", "params": {"file_path": "expenses.csv"}}
    ],
    "aggregation": {"strategy": "merge_dict", "config": {}},
    "transforms": [
        {"name": "excel_export", "type": "to_excel", "input": "aggregate_sources", "config": {}}
    ],
    "final_format": "excel"
}
"""
```

## Technical Notes

- Use low temperature (0.1) for structured output
- Validate JSON against schema before processing
- Handle edge cases: single source (no aggregation), no transforms
- Cache common patterns for faster detection
- Consider confidence scoring for orchestration detection

## Dependencies

- Depends on: #6 (OrchestrationPlan)
- Modifies: `planner/planner.py`

## Testing Requirements

```python
@pytest.mark.unit
class TestOrchestrationDetection:
    def test_detect_multi_source_and(self): ...
    def test_detect_combine_keyword(self): ...
    def test_detect_export_format(self): ...
    def test_no_detect_simple_query(self): ...

@pytest.mark.integration
class TestOrchestrationPlanning:
    def test_plan_two_sources_merge(self): ...
    def test_plan_transform_chain(self): ...
    def test_plan_full_pipeline(self): ...
    def test_fallback_on_llm_error(self): ...

@pytest.mark.e2e
class TestOrchestrationE2E:
    def test_natural_language_to_excel(self): ...
    def test_api_endpoint_orchestration(self): ...
    def test_complex_financial_report(self): ...
```

## Example Queries to Support

1. "Read data.csv and api_response.json, merge them, and export as Excel"
2. "Analyze contract.pdf, extract key clauses, and generate a summary in Markdown"
3. "Fetch revenue from accounting API and expenses from the database, combine them, filter amounts over $1000, and create a PDF report"
4. "Get customer data from CRM and order history from sales DB, join by customer_id, export to CSV"

## Estimated Effort

4-5 days

## Related Issues

- Depends on: #1-#6 (all previous issues)
- Final issue in the refactor sprint
