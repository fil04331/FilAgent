# Tests Directory

This directory contains the test suite for FilAgent.

## Structure

```
tests/
├── conftest.py              # Shared fixtures and pytest configuration
├── test_config.py           # Configuration management tests
├── test_fixtures.py         # Fixture validation tests
├── test_memory.py           # Memory/episodic storage tests
├── test_tools.py            # Tool execution tests
├── test_server.py           # Server API tests
├── test_server_health.py    # Health check endpoint tests
├── test_agent_*.py          # Agent functionality tests
├── test_compliance_flow.py  # Compliance and governance tests
└── test_integration_e2e.py  # End-to-end integration tests
```

## Running Tests

### All Tests
```bash
pytest
```

### Specific Test File
```bash
pytest tests/test_memory.py
```

### Specific Test
```bash
pytest tests/test_memory.py::test_add_and_get_message
```

### By Marker
```bash
pytest -m unit           # Unit tests only
pytest -m integration    # Integration tests only
pytest -m e2e           # End-to-end tests only
pytest -m fixtures      # Fixture validation tests only
pytest -m "not slow"    # Skip slow tests
```

### With Coverage
```bash
pytest --cov=. --cov-report=html
```

## Test Categories

### Unit Tests
Fast, isolated tests of individual components.
- `test_memory.py`
- `test_tools.py`
- `test_fixtures.py`

Mark with: `@pytest.mark.unit`

### Integration Tests
Tests of multiple components working together.
- `test_server.py`
- `test_agent_*.py`

Mark with: `@pytest.mark.integration`

### End-to-End Tests
Full system tests from API to database.
- `test_integration_e2e.py`

Mark with: `@pytest.mark.e2e`

### Compliance Tests
Governance, security, and regulatory tests.
- `test_compliance_flow.py`

Mark with: `@pytest.mark.compliance`

## Using Fixtures

See [FIXTURES.md](../FIXTURES.md) for comprehensive fixture documentation.

### Quick Examples

#### Database Testing
```python
def test_database(temp_db):
    from memory.episodic import add_message, get_messages
    add_message("conv-1", "user", "Hello")
    messages = get_messages("conv-1")
    assert len(messages) == 1
```

#### API Testing
```python
def test_api(api_client):
    response = api_client.post("/chat", json={
        "messages": [{"role": "user", "content": "Hi"}]
    })
    assert response.status_code == 200
```

#### Mock Model Testing
```python
def test_generation(mock_model):
    result = mock_model.generate("prompt", GenerationConfig())
    assert result.text is not None
```

## Best Practices

### 1. Test Isolation
- Each test should be independent
- Use fixtures for setup/teardown
- Don't rely on test execution order

### 2. Test Names
- Use descriptive names: `test_that_something_happens`
- Follow pattern: `test_<what>_<when>_<expected>`

### 3. Assertions
- Use clear assertion messages
- Test one thing per test
- Use pytest assertions for better error messages

### 4. Markers
- Mark tests appropriately (unit, integration, slow, etc.)
- Use markers for selective test execution

### 5. Fixtures
- Use provided fixtures from conftest.py
- Don't create duplicate fixtures
- Compose fixtures for complex scenarios

## Common Issues

### Import Errors
If you get import errors, ensure the project root is in sys.path:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
```

### Database Conflicts
Use the `temp_db` fixture which automatically isolates the database.

### Middleware State
Use the `patched_middlewares` fixture to isolate middleware singletons.

### Environment Variables
The `clean_environment` fixture (autouse) isolates environment variables.

## Writing New Tests

### 1. Choose the Right Test File
- Memory tests → `test_memory.py`
- Tool tests → `test_tools.py`
- API tests → `test_server.py` or create new file

### 2. Import Required Fixtures
```python
def test_something(temp_db, mock_model, isolated_fs):
    # Fixtures are automatically set up
    ...
```

### 3. Add Appropriate Markers
```python
@pytest.mark.unit
def test_unit_functionality():
    ...

@pytest.mark.slow
def test_expensive_operation():
    ...
```

### 4. Write Clear Tests
```python
def test_feature_works_correctly():
    # Arrange
    setup_data = "test"
    
    # Act
    result = function_under_test(setup_data)
    
    # Assert
    assert result == expected_value
```

## Debugging Tests

### Run with Verbose Output
```bash
pytest -v
```

### Show Print Statements
```bash
pytest -s
```

### Stop on First Failure
```bash
pytest -x
```

### Run Last Failed Tests
```bash
pytest --lf
```

### Run with PDB Debugger
```bash
pytest --pdb
```

## Continuous Integration

Tests are run automatically on:
- Push to main branches
- Pull requests
- Scheduled runs

See `.github/workflows/` for CI configuration.

## Test Coverage

Aim for:
- Unit tests: > 80% coverage
- Integration tests: Cover main workflows
- E2E tests: Cover critical user paths

Check coverage:
```bash
pytest --cov=. --cov-report=term-missing
```

## Contributing Tests

When adding features:
1. Write tests first (TDD)
2. Ensure tests pass locally
3. Add appropriate markers
4. Update documentation if needed
5. Verify coverage doesn't decrease

## Further Reading

- [FIXTURES.md](../FIXTURES.md) - Comprehensive fixture guide
- [pytest documentation](https://docs.pytest.org/)
- Main project README for setup instructions
