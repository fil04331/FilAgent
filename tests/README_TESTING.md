# Testing Guide for FilAgent

## Overview

This guide explains how to run tests in the FilAgent project, especially tests with optional dependencies.

## Test Markers

The project uses pytest markers to categorize tests:

- **`unit`**: Unit tests (fast, isolated)
- **`integration`**: Integration tests (slower)
- **`compliance`**: Compliance and validation tests
- **`e2e`**: End-to-end tests (slowest)
- **`htn`**: HTN (Hierarchical Task Network) planning tests
- **`requires_llama_cpp`**: Tests requiring llama-cpp-python package (optional ML dependency)

## Running Tests

### Run All Tests

```bash
pdm run pytest
```

### Run Tests by Marker

```bash
# Run only unit tests
pdm run pytest -m unit

# Run only integration tests
pdm run pytest -m integration

# Run only compliance tests
pdm run pytest -m compliance
```

### Run Specific Test File

```bash
pdm run pytest tests/test_model_interface.py
```

### Run Tests with Coverage

```bash
pdm run pytest --cov=. --cov-report=html
```

## Optional Dependencies: llama-cpp-python

### Why Tests Are Skipped

The project has **26 tests** in `tests/test_model_interface.py` that require the optional `llama-cpp-python` package. This package is part of the `ml` dependency group in `pyproject.toml`.

When `llama-cpp-python` is not installed, these tests are **automatically skipped** (not failed) to ensure:
- Developers can run tests without installing heavy ML dependencies
- CI/CD pipelines remain fast for non-ML work
- Test suite is robust and doesn't fail due to missing optional dependencies

### Installing Optional ML Dependencies

To run the llama.cpp tests, install the optional ML dependencies:

```bash
pdm install --with ml
```

After installation, run the llama.cpp tests:

```bash
# Run all tests requiring llama_cpp
pdm run pytest -m requires_llama_cpp

# Run all model_interface tests (including llama_cpp tests)
pdm run pytest tests/test_model_interface.py
```

### Verifying Test Status

Without llama-cpp-python:
```bash
pdm run pytest tests/test_model_interface.py -v
# Expected: 20 passed, 26 skipped
```

With llama-cpp-python:
```bash
pdm install --with ml
pdm run pytest tests/test_model_interface.py -v
# Expected: 46 passed
```

## Test Structure

Tests are organized following pytest best practices:

```
tests/
├── conftest.py                    # Shared fixtures and markers
├── test_model_interface.py        # Model interface tests (26 require llama_cpp)
├── test_agent.py                  # Agent core tests
├── test_compliance_flow.py        # Compliance tests
├── test_integration_e2e.py        # E2E tests
└── test_planner/                  # HTN planner tests
    ├── test_task_graph.py
    ├── test_planner.py
    ├── test_executor.py
    └── test_verifier.py
```

## Writing Tests with Optional Dependencies

If you need to write tests that require optional dependencies:

1. **Mark the test with the appropriate marker:**

```python
import pytest

@pytest.mark.requires_llama_cpp
@skip_if_no_llama_cpp
def test_my_llama_feature():
    from llama_cpp import Llama
    # Your test code
```

2. **The `skip_if_no_llama_cpp` decorator:**
   - Defined in `tests/conftest.py` and `tests/test_model_interface.py`
   - Automatically skips the test if llama-cpp-python is not installed
   - Provides a helpful message: "llama-cpp-python not installed (optional ml dependency). Install with: pdm install --with ml"

3. **Best practices:**
   - Always use both `@pytest.mark.requires_llama_cpp` (for filtering) and `@skip_if_no_llama_cpp` (for skipping)
   - Document in test docstring that the test requires optional dependencies
   - Ensure tests gracefully skip rather than fail

## Troubleshooting

### Tests failing instead of skipping

If tests are failing with `ModuleNotFoundError: No module named 'llama_cpp'` instead of skipping:
- Ensure `@skip_if_no_llama_cpp` decorator is applied to the test
- Check that `conftest.py` has the skip marker defined
- Verify that pytest is loading the conftest.py correctly

### Unable to run llama_cpp tests after installation

If tests still skip after installing ML dependencies:
```bash
# Verify installation
python -c "import llama_cpp; print('llama_cpp available')"

# Ensure you're using the right Python environment
pdm run python -c "import llama_cpp; print('llama_cpp available')"
```

## CI/CD Considerations

In CI/CD pipelines:

- **Standard pipeline**: Runs without `--with ml` → 26 tests skipped
- **ML validation pipeline**: Runs with `--with ml` → All tests pass

This allows:
- Fast feedback for standard code changes
- Dedicated ML validation when needed
- No broken tests due to missing optional dependencies

## Contact

For questions about testing:
- Review test documentation in `tests/conftest.py`
- Check existing test patterns in `tests/test_model_interface.py`
- Consult CLAUDE.md for project coding standards
