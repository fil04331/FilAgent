# Test Data Generators - FilAgent

This module provides comprehensive test data generators for the FilAgent test suite.

## Overview

The test data generators create realistic, compliant test data for:
- **Conversations**: Multi-turn conversations with tool calls and metadata
- **HTN Task Graphs**: Simple to complex task graphs with various execution patterns
- **Compliance Scenarios**: Decision Records, PROV-JSON graphs, and compliance events

## Installation

No additional installation required. The generators are part of the test suite and integrate with existing fixtures.

## Usage

### Basic Examples

```python
from tests.utils.test_data_generators import (
    generate_conversation,
    generate_task_graph,
    generate_decision_record,
    generate_complete_test_scenario
)

# Generate a conversation
conv = generate_conversation(num_turns=3, include_tool_calls=True)

# Generate a task graph
graph = generate_task_graph(complexity="complex")

# Generate a Decision Record
dr = generate_decision_record(decision_type="tool_invocation")

# Generate a complete test scenario
scenario = generate_complete_test_scenario()
```

## API Reference

### Conversation Generators

#### `generate_conversation_id() -> str`
Generate a unique conversation ID.

**Returns**: ID in format `conv-{uuid}`

#### `generate_task_id() -> str`
Generate a unique task ID.

**Returns**: ID in format `task-{uuid}`

#### `generate_message(role, content, message_type, metadata, timestamp) -> Dict`
Generate a single conversation message.

**Args**:
- `role` (str): Message role ('user', 'assistant', 'system')
- `content` (Optional[str]): Message content (auto-generated if None)
- `message_type` (str): Type ('text', 'tool_call', 'tool_result')
- `metadata` (Optional[Dict]): Additional metadata
- `timestamp` (Optional[str]): ISO timestamp (auto-generated if None)

**Returns**: Message dictionary

#### `generate_conversation(num_turns, include_system, include_tool_calls, conversation_id, task_id) -> ConversationData`
Generate a complete multi-turn conversation.

**Args**:
- `num_turns` (int): Number of conversation turns (default: 3)
- `include_system` (bool): Include system message (default: False)
- `include_tool_calls` (bool): Include tool calls (default: False)
- `conversation_id` (Optional[str]): Conversation ID (auto-generated if None)
- `task_id` (Optional[str]): Task ID (auto-generated if None)

**Returns**: `ConversationData` object with messages and metadata

**Example**:
```python
conv = generate_conversation(
    num_turns=5,
    include_system=True,
    include_tool_calls=True
)
print(f"Generated {len(conv.messages)} messages")
```

#### `generate_multi_user_conversation(num_participants, num_turns) -> ConversationData`
Generate a conversation with multiple users.

**Args**:
- `num_participants` (int): Number of participants (default: 2)
- `num_turns` (int): Total number of turns (default: 5)

**Returns**: `ConversationData` with multi-user metadata

### HTN Task Graph Generators

#### `generate_simple_task_graph() -> TaskGraph`
Generate a simple linear task graph (3 tasks: T1 → T2 → T3).

**Returns**: `TaskGraph` with 3 sequential tasks

#### `generate_parallel_task_graph() -> TaskGraph`
Generate a task graph with parallel execution.

**Structure**:
```
    T1 (root)
   / | \
  T2 T3 T4 (parallel)
   \ | /
    T5 (merge)
```

**Returns**: `TaskGraph` with 5 tasks (1 root, 3 parallel, 1 merge)

#### `generate_complex_task_graph() -> TaskGraph`
Generate a complex task graph (~10 tasks) representing a realistic workflow.

**Returns**: `TaskGraph` with multiple levels and dependencies

#### `generate_task_graph_with_failures() -> TaskGraph`
Generate a task graph with failed and skipped tasks.

**Returns**: `TaskGraph` with various task statuses

#### `generate_task_graph_with_priorities() -> TaskGraph`
Generate a task graph with different priority levels.

**Returns**: `TaskGraph` with CRITICAL, HIGH, NORMAL, LOW, and OPTIONAL priorities

#### `generate_task_graph(complexity, num_tasks) -> TaskGraph`
Flexible task graph generator.

**Args**:
- `complexity` (str): Complexity level
  - `"simple"`: 3 sequential tasks
  - `"parallel"`: 5 tasks with parallel execution
  - `"complex"`: 10 tasks with multiple levels
  - `"with_failures"`: Tasks with failures
  - `"with_priorities"`: Tasks with varied priorities
- `num_tasks` (Optional[int]): Number of tasks (overrides complexity)

**Returns**: `TaskGraph` according to parameters

### Compliance Scenario Generators

#### `generate_decision_record(decision_type, actor, task_id, include_signature) -> Dict`
Generate a Decision Record (DR).

**Args**:
- `decision_type` (str): Type of decision
  - `"tool_invocation"`: Tool execution decision
  - `"planning"`: HTN planning decision
  - `"data_access"`: Data access decision
  - `"pii_handling"`: PII handling decision
- `actor` (str): Actor making the decision (default: "agent.core")
- `task_id` (Optional[str]): Task ID (auto-generated if None)
- `include_signature` (bool): Include mock EdDSA signature (default: True)

**Returns**: Complete Decision Record as dictionary

**Example**:
```python
dr = generate_decision_record(
    decision_type="tool_invocation",
    actor="agent.core"
)
print(f"DR ID: {dr['dr_id']}")
print(f"Decision: {dr['decision']}")
```

#### `generate_prov_graph(conversation_id, include_tool_calls) -> Dict`
Generate a W3C PROV-JSON provenance graph.

**Args**:
- `conversation_id` (Optional[str]): Conversation ID (auto-generated if None)
- `include_tool_calls` (bool): Include tool execution in graph (default: True)

**Returns**: Complete PROV-JSON graph with entities, activities, agents, and relations

**Example**:
```python
prov = generate_prov_graph(include_tool_calls=True)
assert 'entity' in prov
assert 'activity' in prov
assert 'agent' in prov
```

#### `generate_compliance_event(event_type, level, conversation_id, task_id, pii_redacted) -> Dict`
Generate a structured compliance event.

**Args**:
- `event_type` (str): Event type
  - `"tool.call"`: Tool invocation
  - `"pii.detected"`: PII detection
  - `"decision.made"`: Decision recorded
  - `"error.occurred"`: Error event
- `level` (str): Log level ('INFO', 'WARNING', 'ERROR') (default: 'INFO')
- `conversation_id` (Optional[str]): Conversation ID
- `task_id` (Optional[str]): Task ID
- `pii_redacted` (bool): Whether PII was redacted (default: True)

**Returns**: Structured event in JSONL format (OpenTelemetry-compatible)

#### `generate_pii_scenario(include_email, include_phone, include_ssn, include_address) -> Tuple[str, Dict]`
Generate a scenario with PII for testing redaction.

**Args**:
- `include_email` (bool): Include email addresses (default: True)
- `include_phone` (bool): Include phone numbers (default: True)
- `include_ssn` (bool): Include SSN (default: False)
- `include_address` (bool): Include addresses (default: False)

**Returns**: Tuple of (text_with_pii, pii_detection_map)

**Example**:
```python
text, pii_map = generate_pii_scenario(
    include_email=True,
    include_phone=True
)
print(f"Text: {text}")
print(f"Detected PII: {pii_map}")
```

### Batch Generators

#### `generate_batch_conversations(count, min_turns, max_turns) -> List[ConversationData]`
Generate multiple conversations for performance testing.

**Args**:
- `count` (int): Number of conversations (default: 10)
- `min_turns` (int): Minimum turns per conversation (default: 1)
- `max_turns` (int): Maximum turns per conversation (default: 5)

**Returns**: List of `ConversationData` objects

#### `generate_batch_task_graphs(count, complexity) -> List[TaskGraph]`
Generate multiple task graphs.

**Args**:
- `count` (int): Number of graphs (default: 10)
- `complexity` (str): Complexity level (default: "simple")

**Returns**: List of `TaskGraph` objects

#### `generate_batch_decision_records(count, decision_types) -> List[Dict]`
Generate multiple Decision Records.

**Args**:
- `count` (int): Number of DRs (default: 10)
- `decision_types` (Optional[List[str]]): Types to use (all types if None)

**Returns**: List of Decision Record dictionaries

### Integration Helpers

#### `populate_test_database(db_connection, num_conversations, messages_per_conversation) -> List[str]`
Populate a test database with conversations.

**Args**:
- `db_connection`: SQLite connection
- `num_conversations` (int): Number of conversations (default: 5)
- `messages_per_conversation` (int): Messages per conversation (default: 10)

**Returns**: List of conversation IDs created

**Example**:
```python
import sqlite3
from memory.episodic import create_tables

conn = sqlite3.connect(':memory:')
create_tables()
conv_ids = populate_test_database(conn, num_conversations=3)
```

#### `generate_complete_test_scenario() -> Dict`
Generate a complete integrated test scenario with all components.

**Returns**: Dictionary containing:
- `conversation_id`: Unique conversation ID
- `task_id`: Unique task ID
- `conversation`: ConversationData object
- `task_graph`: TaskGraph object
- `decision_records`: List of Decision Records
- `provenance`: PROV-JSON graph
- `compliance_events`: List of compliance events
- `metadata`: Scenario metadata

**Example**:
```python
scenario = generate_complete_test_scenario()

# Use all components together
conv = scenario['conversation']
graph = scenario['task_graph']
drs = scenario['decision_records']
prov = scenario['provenance']

# All components share the same conversation_id and task_id
assert conv.conversation_id == scenario['conversation_id']
```

## Data Structures

### ConversationData

```python
@dataclass
class ConversationData:
    conversation_id: str
    messages: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    created_at: str
    task_id: Optional[str] = None
```

**Fields**:
- `conversation_id`: Unique conversation identifier
- `messages`: List of message dictionaries with `role`, `content`, `timestamp`, etc.
- `metadata`: Conversation metadata (num_turns, has_tool_calls, language)
- `created_at`: ISO timestamp of creation
- `task_id`: Optional associated task ID

## Integration with Existing Fixtures

The generators integrate seamlessly with existing pytest fixtures:

```python
def test_with_fixtures(temp_db, mock_model):
    """Example test using generators with fixtures"""
    from tests.utils.test_data_generators import generate_conversation
    from memory.episodic import add_message, get_messages

    # Generate conversation
    conv = generate_conversation(num_turns=3)

    # Add to temp database
    for msg in conv.messages:
        add_message(
            conversation_id=conv.conversation_id,
            role=msg['role'],
            content=msg['content'],
            task_id=conv.task_id
        )

    # Retrieve and verify
    messages = get_messages(conv.conversation_id)
    assert len(messages) == len(conv.messages)
```

## Testing the Generators

Run the comprehensive test suite:

```bash
pytest tests/test_data_generators.py -v
```

All 31 tests should pass, covering:
- Conversation generation (7 tests)
- HTN task graph generation (6 tests)
- Compliance scenario generation (9 tests)
- Batch generators (3 tests)
- Integration helpers (3 tests)
- Integration with existing fixtures (3 tests)

## Best Practices

1. **Use appropriate complexity**: Choose the right complexity level for your test
   - Use `"simple"` for unit tests
   - Use `"complex"` for integration tests
   - Use `"with_failures"` for error handling tests

2. **Leverage batch generators**: For performance tests, use batch generators
   ```python
   conversations = generate_batch_conversations(count=100)
   ```

3. **Use complete scenarios**: For E2E tests, use `generate_complete_test_scenario()`
   ```python
   scenario = generate_complete_test_scenario()
   # All components are pre-integrated and consistent
   ```

4. **Verify data consistency**: Generated IDs are consistent across related components
   ```python
   scenario = generate_complete_test_scenario()
   assert scenario['conversation'].conversation_id == scenario['conversation_id']
   ```

5. **Test with realistic data**: Generators produce realistic data patterns
   - Timestamps are sequential
   - Dependencies are valid
   - Metadata is complete

## Compliance & Governance

All generated data respects FilAgent's compliance requirements:

- **Decision Records**: Include all required fields (dr_id, timestamp, actor, etc.)
- **PROV-JSON**: Conform to W3C PROV standard
- **PII Scenarios**: Realistic PII patterns for testing redaction
- **Structured Logs**: OpenTelemetry-compatible trace IDs

## Examples

### Example 1: Simple Conversation Test

```python
def test_conversation_storage(temp_db):
    """Test storing a conversation in the database"""
    conv = generate_conversation(num_turns=2)

    # Store in database
    for msg in conv.messages:
        add_message(
            conversation_id=conv.conversation_id,
            role=msg['role'],
            content=msg['content']
        )

    # Retrieve and verify
    messages = get_messages(conv.conversation_id)
    assert len(messages) == len(conv.messages)
```

### Example 2: HTN Planning Test

```python
def test_task_execution():
    """Test task graph execution"""
    graph = generate_complex_task_graph()

    # Get execution order
    sorted_tasks = graph.topological_sort()

    # Simulate execution
    for task in sorted_tasks:
        task.update_status(TaskStatus.RUNNING)
        # ... execute task ...
        task.update_status(TaskStatus.COMPLETED)

    # Verify all tasks completed
    assert all(t.status == TaskStatus.COMPLETED for t in graph.tasks.values())
```

### Example 3: Compliance Testing

```python
def test_decision_record_compliance():
    """Test Decision Record compliance"""
    dr = generate_decision_record(decision_type="pii_handling")

    # Verify required fields
    assert 'dr_id' in dr
    assert 'timestamp' in dr
    assert 'actor' in dr
    assert 'decision' in dr
    assert 'reasoning_markers' in dr

    # Verify signature
    assert 'signature' in dr
    assert dr['signature'].startswith('ed25519:')
```

### Example 4: Complete E2E Scenario

```python
def test_complete_workflow():
    """Test complete agent workflow"""
    scenario = generate_complete_test_scenario()

    # Access all components
    conv = scenario['conversation']
    graph = scenario['task_graph']
    drs = scenario['decision_records']
    prov = scenario['provenance']
    events = scenario['compliance_events']

    # Verify integration
    assert conv.conversation_id == scenario['conversation_id']
    assert all(dr['task_id'] == scenario['task_id'] for dr in drs)

    # Execute workflow
    # ... workflow implementation ...
```

## Contributing

When adding new generators:

1. Follow existing naming conventions (`generate_*`)
2. Add comprehensive docstrings (French)
3. Include type hints
4. Add tests in `tests/test_data_generators.py`
5. Update this README

## Version

Version: 1.0.0
Last Updated: 2025-11-14

## License

MIT License (same as FilAgent project)
