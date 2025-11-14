"""
Tests pour les générateurs de données de test

Vérifie que tous les générateurs produisent des données valides et conformes.
"""

import pytest
import json
from datetime import datetime
from tests.utils.test_data_generators import (
    # Conversation generators
    generate_conversation_id,
    generate_task_id,
    generate_message,
    generate_conversation,
    generate_multi_user_conversation,
    # HTN generators
    generate_simple_task_graph,
    generate_parallel_task_graph,
    generate_complex_task_graph,
    generate_task_graph_with_failures,
    generate_task_graph_with_priorities,
    generate_task_graph,
    # Compliance generators
    generate_decision_record,
    generate_prov_graph,
    generate_compliance_event,
    generate_pii_scenario,
    # Batch generators
    generate_batch_conversations,
    generate_batch_task_graphs,
    generate_batch_decision_records,
    # Integration helpers
    generate_complete_test_scenario
)
from planner.task_graph import TaskGraph, TaskStatus, TaskPriority


# ============================================================================
# Tests: Conversation Generators
# ============================================================================


@pytest.mark.unit
def test_generate_conversation_id():
    """Test génération d'ID de conversation"""
    conv_id = generate_conversation_id()

    assert conv_id.startswith('conv-')
    assert len(conv_id) > 5

    # Verify uniqueness
    conv_id2 = generate_conversation_id()
    assert conv_id != conv_id2


@pytest.mark.unit
def test_generate_task_id():
    """Test génération d'ID de tâche"""
    task_id = generate_task_id()

    assert task_id.startswith('task-')
    assert len(task_id) > 5


@pytest.mark.unit
def test_generate_message():
    """Test génération de message individuel"""
    msg = generate_message(role="user", content="Test message")

    assert msg['role'] == 'user'
    assert msg['content'] == 'Test message'
    assert msg['message_type'] == 'text'
    assert 'timestamp' in msg

    # Validate timestamp format
    datetime.fromisoformat(msg['timestamp'])


@pytest.mark.unit
def test_generate_message_with_metadata():
    """Test génération de message avec métadonnées"""
    metadata = {'user_id': 'user123', 'session': 'abc'}
    msg = generate_message(role="assistant", metadata=metadata)

    assert 'metadata' in msg
    assert msg['metadata']['user_id'] == 'user123'


@pytest.mark.unit
def test_generate_conversation():
    """Test génération de conversation complète"""
    conv = generate_conversation(num_turns=3, include_system=True)

    assert conv.conversation_id.startswith('conv-')
    assert len(conv.messages) >= 3 * 2  # 3 turns * (user + assistant)

    # First message should be system if include_system=True
    assert conv.messages[0]['role'] == 'system'

    # Verify alternating user/assistant pattern (after system message)
    roles = [msg['role'] for msg in conv.messages[1:]]
    assert roles[0] == 'user'
    assert roles[1] == 'assistant'


@pytest.mark.unit
def test_generate_conversation_with_tool_calls():
    """Test conversation avec appels d'outils"""
    conv = generate_conversation(num_turns=2, include_tool_calls=True)

    # Check for tool call messages
    tool_messages = [msg for msg in conv.messages if msg.get('message_type') == 'tool_call']
    assert len(tool_messages) > 0

    # Check for tool result messages
    result_messages = [msg for msg in conv.messages if msg.get('message_type') == 'tool_result']
    assert len(result_messages) > 0


@pytest.mark.unit
def test_generate_multi_user_conversation():
    """Test conversation multi-utilisateurs"""
    conv = generate_multi_user_conversation(num_participants=3, num_turns=6)

    assert len(conv.messages) == 6 * 2  # 6 turns * 2 messages per turn
    assert conv.metadata['num_participants'] == 3

    # Check metadata for user identification
    user_messages = [msg for msg in conv.messages if msg['role'] == 'user']
    assert all('metadata' in msg and 'user_id' in msg['metadata'] for msg in user_messages)


# ============================================================================
# Tests: HTN Task Graph Generators
# ============================================================================


@pytest.mark.unit
def test_generate_simple_task_graph():
    """Test graphe de tâches simple"""
    graph = generate_simple_task_graph()

    assert isinstance(graph, TaskGraph)
    assert len(graph.tasks) == 3

    # Verify topological order
    sorted_tasks = graph.topological_sort()
    assert len(sorted_tasks) == 3

    # First task should have no dependencies
    assert len(sorted_tasks[0].depends_on) == 0


@pytest.mark.unit
def test_generate_parallel_task_graph():
    """Test graphe avec tâches parallèles"""
    graph = generate_parallel_task_graph()

    assert len(graph.tasks) == 5  # 1 root + 3 parallel + 1 merge

    # Get parallelizable tasks
    levels = graph.get_parallelizable_tasks()
    assert len(levels) >= 2

    # Second level should have 3 parallel tasks
    assert len(levels[1]) == 3


@pytest.mark.unit
def test_generate_complex_task_graph():
    """Test graphe complexe"""
    graph = generate_complex_task_graph()

    assert len(graph.tasks) == 10
    assert len(graph.tasks) >= 5

    # Verify no cycles
    sorted_tasks = graph.topological_sort()
    assert len(sorted_tasks) == len(graph.tasks)


@pytest.mark.unit
def test_generate_task_graph_with_failures():
    """Test graphe avec tâches échouées"""
    graph = generate_task_graph_with_failures()

    # Check for failed tasks
    failed_tasks = [t for t in graph.tasks.values() if t.status == TaskStatus.FAILED]
    assert len(failed_tasks) > 0

    # Check for skipped tasks
    skipped_tasks = [t for t in graph.tasks.values() if t.status == TaskStatus.SKIPPED]
    assert len(skipped_tasks) > 0

    # Failed task should have error message
    assert failed_tasks[0].error is not None


@pytest.mark.unit
def test_generate_task_graph_with_priorities():
    """Test graphe avec priorités variées"""
    graph = generate_task_graph_with_priorities()

    # Check that all priority levels are present
    priorities = [t.priority for t in graph.tasks.values()]
    assert TaskPriority.CRITICAL in priorities
    assert TaskPriority.HIGH in priorities
    assert TaskPriority.NORMAL in priorities


@pytest.mark.unit
def test_generate_task_graph_parametric():
    """Test générateur flexible"""
    # Simple
    simple = generate_task_graph(complexity="simple")
    assert len(simple.tasks) == 3

    # Parallel
    parallel = generate_task_graph(complexity="parallel")
    assert len(parallel.tasks) == 5

    # Complex
    complex_graph = generate_task_graph(complexity="complex")
    assert len(complex_graph.tasks) == 10


# ============================================================================
# Tests: Compliance Scenario Generators
# ============================================================================


@pytest.mark.unit
def test_generate_decision_record():
    """Test génération de Decision Record"""
    dr = generate_decision_record(decision_type="tool_invocation")

    # Verify required fields
    assert 'dr_id' in dr
    assert dr['dr_id'].startswith('DR-')
    assert 'ts' in dr
    assert dr['actor'] == 'agent.core'
    assert 'task_id' in dr
    assert dr['task_id'].startswith('task-')

    # Verify hash fields
    assert 'prompt_hash' in dr
    assert dr['prompt_hash'].startswith('sha256:')

    # Verify decision content
    assert 'decision' in dr
    assert 'reasoning_markers' in dr
    assert 'tools_used' in dr
    assert 'alternatives_considered' in dr


@pytest.mark.unit
def test_generate_decision_record_with_signature():
    """Test DR avec signature"""
    dr = generate_decision_record(include_signature=True)

    assert 'signature' in dr
    assert dr['signature'].startswith('ed25519:')


@pytest.mark.unit
def test_generate_decision_record_types():
    """Test différents types de décisions"""
    types = ["tool_invocation", "planning", "data_access", "pii_handling"]

    for decision_type in types:
        dr = generate_decision_record(decision_type=decision_type)
        assert 'decision' in dr
        assert len(dr['tools_used']) > 0


@pytest.mark.unit
def test_generate_prov_graph():
    """Test génération de graphe PROV-JSON"""
    prov = generate_prov_graph(include_tool_calls=True)

    # Verify W3C PROV structure
    assert 'entity' in prov
    assert 'activity' in prov
    assert 'agent' in prov
    assert 'wasGeneratedBy' in prov
    assert 'used' in prov
    assert 'wasAssociatedWith' in prov
    assert 'wasAttributedTo' in prov

    # Verify entities
    assert len(prov['entity']) >= 2  # At least input and output

    # Verify activities
    assert len(prov['activity']) >= 1

    # Verify agents
    assert len(prov['agent']) >= 1


@pytest.mark.unit
def test_generate_prov_graph_with_tool_calls():
    """Test PROV avec appels d'outils"""
    prov = generate_prov_graph(include_tool_calls=True)

    # Should have tool-related entities and activities
    entities = prov['entity']
    activities = prov['activity']

    # Check for tool output entity
    tool_entities = [e for e in entities.keys() if 'tool_output' in e]
    assert len(tool_entities) > 0

    # Check for tool execution activity
    tool_activities = [a for a in activities.keys() if 'tool_exec' in a]
    assert len(tool_activities) > 0

    # Check for derivation relation
    assert 'wasDerivedFrom' in prov


@pytest.mark.unit
def test_generate_compliance_event():
    """Test génération d'événement de conformité"""
    event = generate_compliance_event(event_type="tool.call")

    # Verify structured log format
    assert 'ts' in event
    assert 'trace_id' in event
    assert 'span_id' in event
    assert 'level' in event
    assert event['level'] == 'INFO'
    assert 'actor' in event
    assert event['event'] == 'tool.call'
    assert 'pii_redacted' in event

    # Verify OpenTelemetry-compatible IDs
    assert len(event['trace_id']) == 16
    assert len(event['span_id']) == 8


@pytest.mark.unit
def test_generate_compliance_event_types():
    """Test différents types d'événements"""
    event_types = ["tool.call", "pii.detected", "decision.made", "error.occurred"]

    for event_type in event_types:
        event = generate_compliance_event(event_type=event_type)
        assert event['event'] == event_type

        # Verify event-specific fields
        if event_type == "tool.call":
            assert 'tool_name' in event
        elif event_type == "pii.detected":
            assert 'pii_types' in event


@pytest.mark.unit
def test_generate_pii_scenario():
    """Test génération de scénario PII"""
    text, pii_map = generate_pii_scenario(
        include_email=True,
        include_phone=True
    )

    # Verify text contains PII
    assert '@' in text  # Email
    assert '(' in text or '+' in text  # Phone

    # Verify PII map
    assert 'email' in pii_map
    assert 'phone' in pii_map
    assert len(pii_map['email']) > 0
    assert len(pii_map['phone']) > 0


@pytest.mark.unit
def test_generate_pii_scenario_selective():
    """Test PII avec sélection"""
    text, pii_map = generate_pii_scenario(
        include_email=True,
        include_phone=False,
        include_ssn=False
    )

    assert 'email' in pii_map
    assert 'phone' not in pii_map
    assert 'ssn' not in pii_map


# ============================================================================
# Tests: Batch Generators
# ============================================================================


@pytest.mark.unit
def test_generate_batch_conversations():
    """Test génération de lot de conversations"""
    conversations = generate_batch_conversations(count=5, min_turns=2, max_turns=4)

    assert len(conversations) == 5

    for conv in conversations:
        assert conv.conversation_id.startswith('conv-')
        assert len(conv.messages) >= 4  # min 2 turns * 2 messages


@pytest.mark.unit
def test_generate_batch_task_graphs():
    """Test génération de lot de graphes"""
    graphs = generate_batch_task_graphs(count=3, complexity="simple")

    assert len(graphs) == 3

    for graph in graphs:
        assert isinstance(graph, TaskGraph)
        assert len(graph.tasks) > 0


@pytest.mark.unit
def test_generate_batch_decision_records():
    """Test génération de lot de DRs"""
    records = generate_batch_decision_records(count=10)

    assert len(records) == 10

    for dr in records:
        assert 'dr_id' in dr
        assert dr['dr_id'].startswith('DR-')


# ============================================================================
# Tests: Integration Helpers
# ============================================================================


@pytest.mark.unit
def test_generate_complete_test_scenario():
    """Test génération de scénario complet"""
    scenario = generate_complete_test_scenario()

    # Verify all components present
    assert 'conversation_id' in scenario
    assert 'task_id' in scenario
    assert 'conversation' in scenario
    assert 'task_graph' in scenario
    assert 'decision_records' in scenario
    assert 'provenance' in scenario
    assert 'compliance_events' in scenario
    assert 'metadata' in scenario

    # Verify conversation
    conv = scenario['conversation']
    assert len(conv.messages) > 0

    # Verify task graph
    graph = scenario['task_graph']
    assert isinstance(graph, TaskGraph)
    assert len(graph.tasks) > 0

    # Verify decision records
    drs = scenario['decision_records']
    assert len(drs) > 0
    assert all('dr_id' in dr for dr in drs)

    # Verify provenance
    prov = scenario['provenance']
    assert 'entity' in prov
    assert 'activity' in prov

    # Verify compliance events
    events = scenario['compliance_events']
    assert len(events) > 0
    assert all('event' in e for e in events)


@pytest.mark.unit
def test_scenario_id_consistency():
    """Test cohérence des IDs dans le scénario"""
    scenario = generate_complete_test_scenario()

    # All components should use the same conversation_id and task_id
    conv_id = scenario['conversation_id']
    task_id = scenario['task_id']

    assert scenario['conversation'].conversation_id == conv_id
    assert scenario['conversation'].task_id == task_id

    # Decision records should use the same task_id
    for dr in scenario['decision_records']:
        assert dr['task_id'] == task_id

    # Compliance events should use the same IDs
    for event in scenario['compliance_events']:
        assert event['conversation_id'] == conv_id
        assert event['task_id'] == task_id


# ============================================================================
# Tests: Integration with existing fixtures
# ============================================================================


@pytest.mark.unit
def test_integration_with_temp_db(temp_db):
    """Test intégration avec base de données temporaire"""
    from memory.episodic import add_message, get_messages

    # Generate conversation
    conv = generate_conversation(num_turns=2)

    # Add messages to database
    for msg in conv.messages:
        add_message(
            conversation_id=conv.conversation_id,
            role=msg['role'],
            content=msg['content'],
            task_id=conv.task_id,
            message_type=msg.get('message_type', 'text'),
            metadata=msg.get('metadata')
        )

    # Retrieve and verify
    retrieved_messages = get_messages(conv.conversation_id)
    assert len(retrieved_messages) == len(conv.messages)


@pytest.mark.unit
def test_task_graph_serialization():
    """Test sérialisation du graphe de tâches"""
    graph = generate_complex_task_graph()

    # Serialize to dict
    graph_dict = graph.to_dict()

    # Verify structure
    assert 'tasks' in graph_dict
    assert 'adjacency_list' in graph_dict
    assert 'metadata' in graph_dict

    # Verify serialization is JSON-compatible
    json_str = json.dumps(graph_dict)
    assert len(json_str) > 0


@pytest.mark.unit
def test_decision_record_json_serialization():
    """Test sérialisation JSON des DRs"""
    dr = generate_decision_record()

    # Should be JSON serializable
    json_str = json.dumps(dr)
    assert len(json_str) > 0

    # Deserialize and verify
    dr_loaded = json.loads(json_str)
    assert dr_loaded['dr_id'] == dr['dr_id']


@pytest.mark.unit
def test_prov_graph_json_serialization():
    """Test sérialisation JSON du graphe PROV"""
    prov = generate_prov_graph()

    # Should be JSON serializable
    json_str = json.dumps(prov)
    assert len(json_str) > 0

    # Deserialize and verify
    prov_loaded = json.loads(json_str)
    assert 'entity' in prov_loaded
    assert 'activity' in prov_loaded
