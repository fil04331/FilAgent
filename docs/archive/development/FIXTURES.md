# Test Fixtures Guide

This document describes the test fixtures available in FilAgent and how to use them effectively.

## Overview

The test fixtures in `tests/conftest.py` provide isolated, reusable test components that ensure:
- **Isolation**: Each test runs with fresh state
- **Reusability**: Common setup code is centralized
- **Maintainability**: Fixtures are well-documented and type-safe
- **Performance**: Proper scoping minimizes overhead

## Organization

Fixtures are organized into categories:

1. **Mock Models**: LLM model simulation
2. **Temporary Databases**: Isolated SQLite and FAISS
3. **Isolated File Systems**: Temporary directory structures
4. **Configuration & Middleware**: Test configuration and middleware mocking
5. **FastAPI Test Client**: API client fixtures
6. **Tool Mocks**: Mock tool implementations
7. **Utility Helpers**: Helper functions for common operations
8. **Cleanup & Teardown**: Automatic cleanup

## Core Fixtures

### Database Fixtures

#### `temp_db`
Creates an isolated SQLite database with proper schema.

```python
def test_database_operation(temp_db):
    """temp_db automatically patches memory.episodic.DB_PATH"""
    conn = sqlite3.connect(str(temp_db))
    cursor = conn.cursor()
    cursor.execute("INSERT INTO conversations ...")
    # Database is cleaned up automatically
```

**Features:**
- Uses `monkeypatch` to isolate `DB_PATH`
- Calls `create_tables()` for consistent schema
- Function scope: new DB per test
- Automatic cleanup

#### `temp_faiss`
Creates an isolated FAISS index directory.

```python
def test_semantic_search(temp_faiss):
    index_path = temp_faiss / "index.faiss"
    # Work with FAISS index in isolation
```

### Mock Model Fixtures

#### `mock_model`
Basic mock LLM model with default responses.

```python
def test_generation(mock_model):
    result = mock_model.generate("prompt", GenerationConfig())
    assert result.text == "I'll help with that task."
```

#### `mock_tool_model`
Mock model that simulates tool calls.

```python
def test_tool_execution(mock_tool_model):
    result = mock_tool_model.generate("prompt", GenerationConfig())
    assert result.tool_calls is not None
```

#### `mock_model_with_responses`
Factory fixture for custom responses.

```python
def test_custom_flow(mock_model_with_responses):
    model = mock_model_with_responses([
        "Step 1 response",
        "Step 2 response",
        "Final response"
    ])
    # Model cycles through these responses
```

### Isolated File System Fixtures

#### `isolated_fs`
Creates temporary directory structure mimicking production.

```python
def test_logging(isolated_fs):
    log_dir = isolated_fs['logs_events']
    decision_dir = isolated_fs['logs_decisions']
    # Write to isolated directories
```

**Structure:**
- `root`: Base temporary directory
- `logs`: Logs directory
- `logs_events`: Event logs
- `logs_decisions`: Decision records
- `logs_digests`: WORM digests
- `memory`: Memory storage
- `config`: Configuration files

#### `isolated_logging`
Provides isolated event and WORM loggers.

```python
def test_event_logging(isolated_logging):
    logger = isolated_logging['event_logger']
    logger.log_event(actor="test", event="test.event")
    # Logs written to isolated directory
```

### Middleware Fixtures

#### `patched_middlewares`
Patches all middleware singletons with isolated instances.

```python
def test_with_middleware(patched_middlewares):
    logger = patched_middlewares['event_logger']
    dr_manager = patched_middlewares['dr_manager']
    tracker = patched_middlewares['tracker']
    # All middlewares are isolated
```

**Includes:**
- `event_logger`: Event logging
- `worm_logger`: WORM (Write-Once-Read-Many) logging
- `dr_manager`: Decision Record manager
- `tracker`: Provenance tracker
- `isolated_fs`: File system structure

### API Client Fixtures

#### `api_client`
Full FastAPI test client with mocked model and database.

```python
def test_api_endpoint(api_client):
    response = api_client.post("/chat", json={
        "messages": [{"role": "user", "content": "Hello"}]
    })
    assert response.status_code == 200
```

#### `api_client_with_tool_model`
API client with tool call support.

```python
def test_tool_api(api_client_with_tool_model):
    response = api_client_with_tool_model.post("/chat", json={
        "messages": [{"role": "user", "content": "Run Python"}]
    })
    # Tool calls are simulated
```

### Tool Mock Fixtures

#### `mock_tool_success`
Tool that always succeeds.

```python
def test_successful_tool(mock_tool_success):
    result = mock_tool_success.execute({'param': 'value'})
    assert result.status == ToolStatus.SUCCESS
```

#### `mock_tool_failure`
Tool that always fails.

```python
def test_error_handling(mock_tool_failure):
    result = mock_tool_failure.execute({'param': 'value'})
    assert result.status == ToolStatus.ERROR
```

### Utility Fixtures

#### `conversation_factory`
Factory for creating test conversations in database.

```python
def test_conversation(conversation_factory):
    conv_id = conversation_factory(
        "conv-123",
        [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"}
        ],
        task_id="task-456"
    )
    # Conversation now exists in temp_db
```

#### `assert_file_contains`
Helper for asserting file contents.

```python
def test_log_output(assert_file_contains, tmp_path):
    log_file = tmp_path / "test.log"
    log_file.write_text("Test log content")
    assert_file_contains(log_file, "Test log")
```

#### `assert_json_file_valid`
Helper for validating JSON files.

```python
def test_json_output(assert_json_file_valid, tmp_path):
    json_file = tmp_path / "data.json"
    json_file.write_text('{"key": "value"}')
    data = assert_json_file_valid(json_file, {"key": str})
```

#### `performance_tracker`
Context manager for timing code execution.

```python
def test_performance(performance_tracker):
    with performance_tracker("database_query") as timer:
        # Code to measure
        expensive_operation()
    assert timer.elapsed < 1.0  # Should be fast
```

### Configuration Fixtures

#### `test_config`
Provides test configuration with safe defaults.

```python
def test_with_config(test_config):
    assert test_config.model.backend == "mock"
    assert test_config.agent.max_iterations == 5
```

## Automatic Fixtures

These fixtures are applied automatically to all tests.

### `clean_environment`
Isolates environment variables between tests.

```python
# Applied automatically - no need to request it
def test_with_env_var(monkeypatch):
    monkeypatch.setenv("TEST_VAR", "value")
    # Automatically cleaned up after test
```

### `reset_singletons`
Ensures singleton state is reset between tests.

```python
# Applied automatically - handles cleanup
def test_middleware():
    # Middleware singletons are fresh
```

## Best Practices

### 1. Use Appropriate Scope

Fixtures use **function scope** by default for maximum isolation:
- Each test gets fresh instances
- No state leakage between tests
- Automatic cleanup

### 2. Compose Fixtures

Combine fixtures for complex scenarios:

```python
def test_full_stack(api_client, patched_middlewares, conversation_factory):
    # Create a conversation
    conv_id = conversation_factory("test", [{"role": "user", "content": "Hi"}])
    
    # Make API call
    response = api_client.get(f"/conversations/{conv_id}")
    
    # Check middleware logged it
    assert patched_middlewares['event_logger'].call_count > 0
```

### 3. Leverage Type Hints

All fixtures have proper type hints for IDE support:

```python
from pathlib import Path

def test_typed(temp_db: Path, mock_model: MockModelInterface):
    # IDE knows the types
    assert temp_db.exists()
    result = mock_model.generate(...)
```

### 4. Use Factory Fixtures for Variations

When you need multiple instances or variations:

```python
def test_multiple_conversations(conversation_factory):
    conv1 = conversation_factory("conv-1", [{"role": "user", "content": "A"}])
    conv2 = conversation_factory("conv-2", [{"role": "user", "content": "B"}])
    # Each conversation is isolated
```

### 5. Check Examples in Docstrings

Every fixture has an example in its docstring:

```python
# In your IDE or editor, view the fixture definition to see examples
def test_example(temp_db):  # Hover over temp_db to see usage example
    pass
```

## Test Markers

Use markers to categorize tests:

```python
@pytest.mark.fixtures
def test_fixture_behavior():
    """Tests that validate fixture functionality"""
    pass

@pytest.mark.e2e
def test_full_flow(api_client):
    """End-to-end test"""
    pass

@pytest.mark.slow
def test_expensive_operation():
    """Long-running test"""
    pass
```

Available markers:
- `fixtures`: Fixture validation tests
- `e2e`: End-to-end tests
- `compliance`: Compliance tests
- `resilience`: Resilience tests
- `slow`: Slow tests (> 1 second)
- `integration`: Integration tests
- `unit`: Unit tests
- `memory`: Memory tests
- `tools`: Tool tests

## Common Patterns

### Testing API Endpoints

```python
def test_chat_endpoint(api_client, patched_middlewares):
    response = api_client.post("/chat", json={
        "messages": [{"role": "user", "content": "Hello"}]
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "choices" in data
    
    # Verify logging occurred
    log_dir = patched_middlewares['isolated_fs']['logs_events']
    assert len(list(log_dir.glob("*.jsonl"))) > 0
```

### Testing Database Operations

```python
def test_memory_operations(temp_db):
    from memory.episodic import add_message, get_messages
    
    add_message("conv-1", "user", "Hello")
    messages = get_messages("conv-1")
    
    assert len(messages) == 1
    assert messages[0]['content'] == "Hello"
```

### Testing Tool Execution

```python
def test_tool_flow(api_client_with_tool_model, patched_middlewares):
    response = api_client_with_tool_model.post("/chat", json={
        "messages": [{"role": "user", "content": "Calculate 2+2"}]
    })
    
    # Tool execution is logged
    dr_manager = patched_middlewares['dr_manager']
    # Check decision records...
```

### Testing File Operations

```python
def test_log_creation(isolated_logging, assert_file_contains):
    logger = isolated_logging['event_logger']
    log_dir = isolated_logging['event_log_dir']
    
    logger.log_event(actor="test", event="test.event")
    
    log_files = list(log_dir.glob("*.jsonl"))
    assert len(log_files) > 0
    assert_file_contains(log_files[0], "test.event")
```

## Migration from Old Fixtures

If you have tests using the old `temp_db` fixture from `test_memory.py`:

**Before:**
```python
# In test file
@pytest.fixture
def temp_db():
    # Custom implementation
    ...

def test_something(temp_db):
    ...
```

**After:**
```python
# Just use the conftest fixture
def test_something(temp_db):
    # Works the same, but better isolated
    ...
```

The new fixture:
- ✅ Uses monkeypatch for proper isolation
- ✅ Calls create_tables() for correct schema
- ✅ Has proper type hints
- ✅ Includes documentation
- ✅ Automatic cleanup

## Troubleshooting

### Fixture Not Found

If pytest can't find a fixture:
1. Check that `conftest.py` is in the `tests/` directory
2. Verify the fixture name spelling
3. Check for scope conflicts

### State Leaking Between Tests

If tests affect each other:
1. Verify fixtures use `function` scope
2. Check that `reset_singletons` is not disabled
3. Use `isolated_fs` and `patched_middlewares`

### Slow Tests

If tests are slow:
1. Use `performance_tracker` to identify bottlenecks
2. Consider if session/module scope is appropriate
3. Mark slow tests with `@pytest.mark.slow`

### Cleanup Issues

If resources aren't cleaned up:
1. Use context managers (`with` statements)
2. Rely on fixture teardown (after `yield`)
3. Use `tmp_path` for temporary files

## Further Reading

- [pytest fixtures documentation](https://docs.pytest.org/en/stable/fixture.html)
- [pytest markers](https://docs.pytest.org/en/stable/mark.html)
- Test files in `tests/test_fixtures.py` for examples
