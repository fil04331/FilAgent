"""
Générateurs de données de test pour FilAgent

Ce module fournit des générateurs pour créer des données de test réalistes:
- Conversations et messages (mémoire épisodique)
- Graphes de tâches HTN (planification hiérarchique)
- Scénarios de conformité (Decision Records, PROV-JSON)

Usage:
    from tests.utils.test_data_generators import (
        generate_conversation,
        generate_task_graph,
        generate_decision_record
    )

    # Generate a sample conversation
    conv_data = generate_conversation(num_turns=3)

    # Generate a sample HTN task graph
    graph = generate_task_graph(complexity="complex")

    # Generate a Decision Record
    dr = generate_decision_record(decision_type="tool_invocation")

Conformité:
- Respecte les schémas de la base de données épisodique
- Compatible avec les structures HTN du module planner/
- Génère des Decision Records conformes au format de audittrail.py
- Crée des graphes PROV-JSON valides selon W3C PROV
"""

import json
import uuid
import hashlib
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

# Import TaskGraph for type hints
from planner.task_graph import TaskGraph

# ============================================================================
# SECTION 1: Conversation Generators
# ============================================================================


@dataclass
class ConversationData:
    """
    Structure de données pour une conversation générée

    Attributes:
        conversation_id: Identifiant unique de la conversation
        messages: Liste de messages (role, content, metadata)
        metadata: Métadonnées de la conversation
        created_at: Timestamp de création
        task_id: ID de tâche optionnel
    """
    conversation_id: str
    messages: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    created_at: str
    task_id: Optional[str] = None


def generate_conversation_id() -> str:
    """
    Générer un ID de conversation unique

    Returns:
        str: ID au format 'conv-{uuid}'

    Example:
        >>> conv_id = generate_conversation_id()
        >>> assert conv_id.startswith('conv-')
    """
    return f"conv-{uuid.uuid4().hex[:12]}"


def generate_task_id() -> str:
    """
    Générer un ID de tâche unique

    Returns:
        str: ID au format 'task-{uuid}'
    """
    return f"task-{uuid.uuid4().hex[:12]}"


def generate_message(
    role: str = "user",
    content: Optional[str] = None,
    message_type: str = "text",
    metadata: Optional[Dict[str, Any]] = None,
    timestamp: Optional[str] = None
) -> Dict[str, Any]:
    """
    Générer un message de conversation

    Args:
        role: Rôle ('user', 'assistant', 'system')
        content: Contenu du message (généré si None)
        message_type: Type de message ('text', 'tool_call', 'tool_result')
        metadata: Métadonnées optionnelles
        timestamp: Timestamp optionnel (généré si None)

    Returns:
        Dict contenant le message complet

    Example:
        >>> msg = generate_message(role="user", content="Hello")
        >>> assert msg['role'] == 'user'
        >>> assert msg['content'] == 'Hello'
    """
    # Generate content based on role if not provided
    if content is None:
        content = _generate_content_for_role(role, message_type)

    # Generate timestamp if not provided
    if timestamp is None:
        timestamp = datetime.now(timezone.utc).isoformat()

    message = {
        'role': role,
        'content': content,
        'message_type': message_type,
        'timestamp': timestamp
    }

    if metadata:
        message['metadata'] = metadata

    return message


def _generate_content_for_role(role: str, message_type: str) -> str:
    """Generate realistic content based on role and message type"""

    user_messages = [
        "Peux-tu m'aider avec ce fichier?",
        "Analyse les données dans data.csv",
        "Crée un rapport à partir de ces résultats",
        "Calcule la moyenne des valeurs",
        "Lis le fichier et génère un résumé"
    ]

    assistant_messages = [
        "Je vais analyser ce fichier pour vous.",
        "D'accord, je vais lire les données et les analyser.",
        "Je vais créer un rapport basé sur ces informations.",
        "Laissez-moi calculer ces statistiques.",
        "Je vais générer un résumé détaillé."
    ]

    system_messages = [
        "System initialized",
        "Configuration loaded",
        "Tools registered successfully"
    ]

    tool_call_messages = [
        "Calling python_sandbox with code: print('test')",
        "Using file_reader to read data.csv",
        "Executing calculator for statistics"
    ]

    if message_type == "tool_call":
        return random.choice(tool_call_messages)
    elif role == "user":
        return random.choice(user_messages)
    elif role == "assistant":
        return random.choice(assistant_messages)
    elif role == "system":
        return random.choice(system_messages)
    else:
        return "Generic message content"


def generate_conversation(
    num_turns: int = 3,
    include_system: bool = False,
    include_tool_calls: bool = False,
    conversation_id: Optional[str] = None,
    task_id: Optional[str] = None
) -> ConversationData:
    """
    Générer une conversation complète avec plusieurs tours

    Args:
        num_turns: Nombre de tours de conversation (user + assistant)
        include_system: Inclure un message système initial
        include_tool_calls: Inclure des appels d'outils dans l'assistant
        conversation_id: ID de conversation (généré si None)
        task_id: ID de tâche optionnel

    Returns:
        ConversationData: Données de conversation complètes

    Example:
        >>> conv = generate_conversation(num_turns=2, include_system=True)
        >>> assert len(conv.messages) >= 4  # system + 2 turns * 2 messages
        >>> assert conv.messages[0]['role'] == 'system'
    """
    if conversation_id is None:
        conversation_id = generate_conversation_id()

    if task_id is None:
        task_id = generate_task_id()

    messages = []
    base_time = datetime.now(timezone.utc) - timedelta(hours=1)

    # Add system message if requested
    if include_system:
        messages.append(generate_message(
            role="system",
            content="FilAgent initialized with HTN planning enabled",
            timestamp=(base_time + timedelta(seconds=len(messages))).isoformat()
        ))

    # Generate conversation turns
    for turn in range(num_turns):
        # User message
        messages.append(generate_message(
            role="user",
            timestamp=(base_time + timedelta(seconds=len(messages) * 10)).isoformat()
        ))

        # Assistant message (possibly with tool calls)
        if include_tool_calls and turn % 2 == 0:
            # Add tool call message
            messages.append(generate_message(
                role="assistant",
                message_type="tool_call",
                content="I need to use a tool to help with this.",
                metadata={'tool_name': 'python_sandbox'},
                timestamp=(base_time + timedelta(seconds=len(messages) * 10)).isoformat()
            ))

            # Add tool result message
            messages.append(generate_message(
                role="assistant",
                message_type="tool_result",
                content="Tool execution successful: Output data",
                metadata={'tool_name': 'python_sandbox', 'status': 'success'},
                timestamp=(base_time + timedelta(seconds=len(messages) * 10)).isoformat()
            ))
        else:
            # Regular assistant response
            messages.append(generate_message(
                role="assistant",
                timestamp=(base_time + timedelta(seconds=len(messages) * 10)).isoformat()
            ))

    metadata = {
        'num_turns': num_turns,
        'has_tool_calls': include_tool_calls,
        'created_at': base_time.isoformat(),
        'language': 'fr'
    }

    return ConversationData(
        conversation_id=conversation_id,
        messages=messages,
        metadata=metadata,
        created_at=base_time.isoformat(),
        task_id=task_id
    )


def generate_multi_user_conversation(
    num_participants: int = 2,
    num_turns: int = 5
) -> ConversationData:
    """
    Générer une conversation avec plusieurs utilisateurs

    Utile pour tester les scénarios multi-agents ou collaboratifs.

    Args:
        num_participants: Nombre de participants
        num_turns: Nombre total de tours

    Returns:
        ConversationData: Conversation multi-utilisateurs
    """
    conversation_id = generate_conversation_id()
    task_id = generate_task_id()

    messages = []
    base_time = datetime.now(timezone.utc) - timedelta(hours=1)

    user_names = [f"user{i+1}" for i in range(num_participants)]

    for turn in range(num_turns):
        # Rotate through participants
        user = user_names[turn % num_participants]

        messages.append(generate_message(
            role="user",
            content=f"Message from {user}: Can you help with this?",
            metadata={'user_id': user},
            timestamp=(base_time + timedelta(seconds=turn * 30)).isoformat()
        ))

        messages.append(generate_message(
            role="assistant",
            content=f"Response to {user}: I can help with that.",
            timestamp=(base_time + timedelta(seconds=turn * 30 + 15)).isoformat()
        ))

    metadata = {
        'num_participants': num_participants,
        'num_turns': num_turns,
        'created_at': base_time.isoformat()
    }

    return ConversationData(
        conversation_id=conversation_id,
        messages=messages,
        metadata=metadata,
        created_at=base_time.isoformat(),
        task_id=task_id
    )


# ============================================================================
# SECTION 2: HTN Task Graph Generators
# ============================================================================


def generate_simple_task_graph() -> 'TaskGraph':
    """
    Générer un graphe de tâches simple (linéaire)

    Crée un graphe avec 3 tâches séquentielles:
    T1 → T2 → T3

    Returns:
        TaskGraph: Graphe de tâches simple

    Example:
        >>> graph = generate_simple_task_graph()
        >>> assert len(graph.tasks) == 3
        >>> sorted_tasks = graph.topological_sort()
        >>> assert len(sorted_tasks) == 3
    """
    from planner.task_graph import TaskGraph, Task, TaskPriority, TaskStatus

    graph = TaskGraph()

    # Task 1: Read file
    t1 = Task(
        name="Read data file",
        action="read_file",
        params={"file_path": "data.csv"},
        priority=TaskPriority.HIGH,
        status=TaskStatus.PENDING
    )
    graph.add_task(t1)

    # Task 2: Analyze data (depends on T1)
    t2 = Task(
        name="Analyze data",
        action="analyze_data",
        params={"analysis_type": "statistical"},
        depends_on=[t1.task_id],
        priority=TaskPriority.NORMAL,
        status=TaskStatus.PENDING
    )
    graph.add_task(t2)

    # Task 3: Generate report (depends on T2)
    t3 = Task(
        name="Generate report",
        action="generate_report",
        params={"format": "pdf"},
        depends_on=[t2.task_id],
        priority=TaskPriority.NORMAL,
        status=TaskStatus.PENDING
    )
    graph.add_task(t3)

    return graph


def generate_parallel_task_graph() -> 'TaskGraph':
    """
    Générer un graphe de tâches avec exécution parallèle

    Structure:
          T1 (root)
         /  |  \\
        T2  T3  T4 (parallel)
         \\  |  /
           T5 (merge)

    Returns:
        TaskGraph: Graphe avec tâches parallélisables
    """
    from planner.task_graph import TaskGraph, Task, TaskPriority, TaskStatus

    graph = TaskGraph()

    # Root task
    t1 = Task(
        name="Initialize data sources",
        action="initialize",
        params={},
        priority=TaskPriority.HIGH,
        status=TaskStatus.PENDING
    )
    graph.add_task(t1)

    # Parallel tasks
    t2 = Task(
        name="Process file A",
        action="process_file",
        params={"file": "a.csv"},
        depends_on=[t1.task_id],
        priority=TaskPriority.NORMAL,
        status=TaskStatus.PENDING
    )
    graph.add_task(t2)

    t3 = Task(
        name="Process file B",
        action="process_file",
        params={"file": "b.csv"},
        depends_on=[t1.task_id],
        priority=TaskPriority.NORMAL,
        status=TaskStatus.PENDING
    )
    graph.add_task(t3)

    t4 = Task(
        name="Process file C",
        action="process_file",
        params={"file": "c.csv"},
        depends_on=[t1.task_id],
        priority=TaskPriority.NORMAL,
        status=TaskStatus.PENDING
    )
    graph.add_task(t4)

    # Merge task
    t5 = Task(
        name="Merge results",
        action="merge",
        params={"output": "combined.csv"},
        depends_on=[t2.task_id, t3.task_id, t4.task_id],
        priority=TaskPriority.HIGH,
        status=TaskStatus.PENDING
    )
    graph.add_task(t5)

    return graph


def generate_complex_task_graph() -> 'TaskGraph':
    """
    Générer un graphe de tâches complexe avec multiples niveaux

    Structure représentant un workflow réaliste:
    - Lecture de données multiples
    - Transformations parallèles
    - Agrégations
    - Génération de rapport final

    Returns:
        TaskGraph: Graphe complexe avec ~10 tâches
    """
    from planner.task_graph import TaskGraph, Task, TaskPriority, TaskStatus

    graph = TaskGraph()

    # Level 0: Initialize
    t1 = Task(
        name="Initialize workflow",
        action="initialize",
        params={"workflow_id": "wf-001"},
        priority=TaskPriority.CRITICAL,
        status=TaskStatus.PENDING
    )
    graph.add_task(t1)

    # Level 1: Data loading (parallel)
    t2 = Task(
        name="Load sales data",
        action="load_data",
        params={"source": "sales.db", "table": "transactions"},
        depends_on=[t1.task_id],
        priority=TaskPriority.HIGH,
        status=TaskStatus.PENDING
    )
    graph.add_task(t2)

    t3 = Task(
        name="Load customer data",
        action="load_data",
        params={"source": "customers.db", "table": "profiles"},
        depends_on=[t1.task_id],
        priority=TaskPriority.HIGH,
        status=TaskStatus.PENDING
    )
    graph.add_task(t3)

    t4 = Task(
        name="Load product catalog",
        action="load_data",
        params={"source": "products.csv"},
        depends_on=[t1.task_id],
        priority=TaskPriority.NORMAL,
        status=TaskStatus.PENDING
    )
    graph.add_task(t4)

    # Level 2: Data transformation (parallel)
    t5 = Task(
        name="Clean sales data",
        action="clean_data",
        params={"remove_nulls": True, "deduplicate": True},
        depends_on=[t2.task_id],
        priority=TaskPriority.HIGH,
        status=TaskStatus.PENDING
    )
    graph.add_task(t5)

    t6 = Task(
        name="Enrich customer profiles",
        action="enrich_data",
        params={"add_demographics": True},
        depends_on=[t3.task_id],
        priority=TaskPriority.NORMAL,
        status=TaskStatus.PENDING
    )
    graph.add_task(t6)

    # Level 3: Join operations
    t7 = Task(
        name="Join sales with customers",
        action="join_tables",
        params={"join_type": "left", "on_field": "customer_id"},
        depends_on=[t5.task_id, t6.task_id],
        priority=TaskPriority.HIGH,
        status=TaskStatus.PENDING
    )
    graph.add_task(t7)

    t8 = Task(
        name="Enrich with product data",
        action="join_tables",
        params={"join_type": "left", "on_field": "product_id"},
        depends_on=[t7.task_id, t4.task_id],
        priority=TaskPriority.HIGH,
        status=TaskStatus.PENDING
    )
    graph.add_task(t8)

    # Level 4: Analytics
    t9 = Task(
        name="Calculate KPIs",
        action="calculate_metrics",
        params={"metrics": ["revenue", "churn_rate", "ltv"]},
        depends_on=[t8.task_id],
        priority=TaskPriority.HIGH,
        status=TaskStatus.PENDING
    )
    graph.add_task(t9)

    # Level 5: Report generation
    t10 = Task(
        name="Generate executive dashboard",
        action="generate_report",
        params={"format": "pdf", "include_charts": True},
        depends_on=[t9.task_id],
        priority=TaskPriority.CRITICAL,
        status=TaskStatus.PENDING
    )
    graph.add_task(t10)

    return graph


def generate_task_graph_with_failures() -> 'TaskGraph':
    """
    Générer un graphe avec des tâches en état d'échec

    Utile pour tester la gestion des erreurs et les fallbacks.

    Returns:
        TaskGraph: Graphe contenant des tâches échouées
    """
    from planner.task_graph import TaskGraph, Task, TaskPriority, TaskStatus

    graph = TaskGraph()

    # Task 1: Success
    t1 = Task(
        name="Read file",
        action="read_file",
        params={"file_path": "data.csv"},
        priority=TaskPriority.HIGH,
        status=TaskStatus.COMPLETED,
        result={"rows": 100, "columns": 5}
    )
    graph.add_task(t1)

    # Task 2: Failed
    t2 = Task(
        name="Validate data",
        action="validate",
        params={"schema": "strict"},
        depends_on=[t1.task_id],
        priority=TaskPriority.CRITICAL,
        status=TaskStatus.FAILED,
        error="Schema validation failed: missing required field 'timestamp'"
    )
    graph.add_task(t2)

    # Task 3: Skipped (dependency failed)
    t3 = Task(
        name="Process data",
        action="process",
        params={},
        depends_on=[t2.task_id],
        priority=TaskPriority.NORMAL,
        status=TaskStatus.SKIPPED
    )
    graph.add_task(t3)

    return graph


def generate_task_graph_with_priorities() -> 'TaskGraph':
    """
    Générer un graphe avec différents niveaux de priorité

    Utile pour tester l'ordonnancement basé sur la priorité.

    Returns:
        TaskGraph: Graphe avec tâches de priorités variées
    """
    from planner.task_graph import TaskGraph, Task, TaskPriority, TaskStatus

    graph = TaskGraph()

    # Critical priority
    t1 = Task(
        name="Security check",
        action="security_scan",
        params={},
        priority=TaskPriority.CRITICAL,
        status=TaskStatus.PENDING
    )
    graph.add_task(t1)

    # High priority (depends on critical)
    t2 = Task(
        name="Load sensitive data",
        action="load_data",
        params={"encrypted": True},
        depends_on=[t1.task_id],
        priority=TaskPriority.HIGH,
        status=TaskStatus.PENDING
    )
    graph.add_task(t2)

    # Normal priority (depends on high)
    t3 = Task(
        name="Process data",
        action="process",
        params={},
        depends_on=[t2.task_id],
        priority=TaskPriority.NORMAL,
        status=TaskStatus.PENDING
    )
    graph.add_task(t3)

    # Low priority (optional, parallel to normal)
    t4 = Task(
        name="Generate debug logs",
        action="log_debug",
        params={"verbose": True},
        depends_on=[t2.task_id],
        priority=TaskPriority.LOW,
        status=TaskStatus.PENDING
    )
    graph.add_task(t4)

    # Optional (can fail without blocking)
    t5 = Task(
        name="Send telemetry",
        action="send_metrics",
        params={"endpoint": "metrics.example.com"},
        depends_on=[t3.task_id],
        priority=TaskPriority.OPTIONAL,
        status=TaskStatus.PENDING
    )
    graph.add_task(t5)

    return graph


def generate_task_graph(
    complexity: str = "simple",
    num_tasks: Optional[int] = None
) -> 'TaskGraph':
    """
    Générateur flexible de graphes de tâches

    Args:
        complexity: Niveau de complexité ('simple', 'parallel', 'complex')
        num_tasks: Nombre de tâches (ignore complexity si spécifié)

    Returns:
        TaskGraph: Graphe généré selon les paramètres

    Example:
        >>> graph = generate_task_graph(complexity="complex")
        >>> assert len(graph.tasks) > 5
    """
    if complexity == "simple":
        return generate_simple_task_graph()
    elif complexity == "parallel":
        return generate_parallel_task_graph()
    elif complexity == "complex":
        return generate_complex_task_graph()
    elif complexity == "with_failures":
        return generate_task_graph_with_failures()
    elif complexity == "with_priorities":
        return generate_task_graph_with_priorities()
    else:
        # Default to simple
        return generate_simple_task_graph()


# ============================================================================
# SECTION 3: Compliance Scenario Generators
# ============================================================================


def generate_decision_record(
    decision_type: str = "tool_invocation",
    actor: str = "agent.core",
    task_id: Optional[str] = None,
    include_signature: bool = True
) -> Dict[str, Any]:
    """
    Générer un Decision Record (DR) de test

    Args:
        decision_type: Type de décision
        actor: Acteur ayant pris la décision
        task_id: ID de tâche (généré si None)
        include_signature: Inclure une signature mock

    Returns:
        Dict: Decision Record complet au format JSON

    Example:
        >>> dr = generate_decision_record(decision_type="planning")
        >>> assert 'dr_id' in dr
        >>> assert dr['actor'] == 'agent.core'
    """
    if task_id is None:
        task_id = generate_task_id()

    # Generate unique DR ID
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    random_suffix = hashlib.md5(datetime.now(timezone.utc).isoformat().encode()).hexdigest()[:6]
    dr_id = f"DR-{timestamp}-{random_suffix}"

    # Generate prompt hash
    prompt_text = f"Sample prompt for {decision_type} at {datetime.now(timezone.utc).isoformat()}"
    prompt_hash = hashlib.sha256(prompt_text.encode()).hexdigest()

    # Decision content based on type
    decision_content = _generate_decision_content(decision_type)

    dr = {
        "dr_id": dr_id,
        "ts": datetime.now(timezone.utc).isoformat(),
        "actor": actor,
        "task_id": task_id,
        "policy_version": "policies@0.1.0",
        "model_fingerprint": "weights/base.gguf@sha256:abc123",
        "prompt_hash": f"sha256:{prompt_hash}",
        "reasoning_markers": decision_content["reasoning_markers"],
        "tools_used": decision_content["tools_used"],
        "alternatives_considered": decision_content["alternatives"],
        "decision": decision_content["decision"],
        "constraints": decision_content.get("constraints", {}),
        "expected_risk": decision_content.get("expected_risk", [])
    }

    if include_signature:
        # Mock signature (in real scenario, would use EdDSA)
        data_str = json.dumps(dr, sort_keys=True)
        signature_hash = hashlib.sha256(data_str.encode()).hexdigest()
        dr["signature"] = f"ed25519:{signature_hash}"

    return dr


def _generate_decision_content(decision_type: str) -> Dict[str, Any]:
    """Generate realistic decision content based on type"""

    decision_types = {
        "tool_invocation": {
            "decision": "proceed_execute_python_sandbox",
            "reasoning_markers": ["plan:execute-code", "safety:sandboxed"],
            "tools_used": ["python_sandbox@v0.3"],
            "alternatives": ["do_nothing", "ask_clarification"],
            "constraints": {"max_execution_time": 30, "memory_limit_mb": 512},
            "expected_risk": ["code_execution", "resource_usage"]
        },
        "planning": {
            "decision": "decompose_to_htn",
            "reasoning_markers": ["plan:multi-step", "complexity:high"],
            "tools_used": ["planner@v1.0"],
            "alternatives": ["simple_loop", "ask_user"],
            "constraints": {"max_depth": 3, "max_tasks": 20},
            "expected_risk": ["complexity", "execution_time"]
        },
        "data_access": {
            "decision": "proceed_read_file",
            "reasoning_markers": ["access:file-system", "pii:none-detected"],
            "tools_used": ["file_reader@v1.0"],
            "alternatives": ["deny_access", "ask_permission"],
            "constraints": {"max_file_size_mb": 10, "allowed_extensions": [".csv", ".txt"]},
            "expected_risk": ["data_leak", "file_access"]
        },
        "pii_handling": {
            "decision": "mask_pii_before_logging",
            "reasoning_markers": ["compliance:loi25", "pii:detected"],
            "tools_used": ["redaction@v1.0"],
            "alternatives": ["block_completely", "ask_consent"],
            "constraints": {"redaction_level": "strict", "keep_format": True},
            "expected_risk": ["privacy_violation", "data_exposure"]
        }
    }

    return decision_types.get(decision_type, decision_types["tool_invocation"])


def generate_prov_graph(
    conversation_id: Optional[str] = None,
    include_tool_calls: bool = True
) -> Dict[str, Any]:
    """
    Générer un graphe de provenance W3C PROV-JSON

    Crée un graphe de provenance représentant une génération complète:
    - Entités (input, output, artifacts)
    - Activités (generation, tool_execution)
    - Agents (agent, model)
    - Relations (wasGeneratedBy, used, wasAttributedTo, etc.)

    Args:
        conversation_id: ID de conversation (généré si None)
        include_tool_calls: Inclure des appels d'outils dans le graphe

    Returns:
        Dict: Graphe PROV-JSON complet

    Example:
        >>> prov = generate_prov_graph(include_tool_calls=True)
        >>> assert 'entity' in prov
        >>> assert 'activity' in prov
        >>> assert 'agent' in prov
    """
    if conversation_id is None:
        conversation_id = generate_conversation_id()

    # Generate unique IDs
    generation_id = f"gen-{uuid.uuid4().hex[:8]}"
    input_hash = hashlib.sha256(b"sample input message").hexdigest()[:16]
    output_hash = hashlib.sha256(b"sample output message").hexdigest()[:16]

    # Timestamps
    start_time = datetime.now(timezone.utc).isoformat()
    end_time = (datetime.now(timezone.utc) + timedelta(seconds=5)).isoformat()

    # Build PROV graph
    prov_graph = {
        "entity": {
            f"input:{input_hash}": {
                "prov:label": "User prompt",
                "prov:type": "Input",
                "content_hash": f"sha256:{input_hash}",
                "conversation_id": conversation_id
            },
            f"output:{output_hash}": {
                "prov:label": "Agent response",
                "prov:type": "Output",
                "content_hash": f"sha256:{output_hash}",
                "conversation_id": conversation_id
            }
        },
        "activity": {
            f"generation:{generation_id}": {
                "prov:type": "TextGeneration",
                "prov:startTime": start_time,
                "prov:endTime": end_time,
                "model": "llama-3-8b",
                "temperature": 0.7
            }
        },
        "agent": {
            "agent:filagent": {
                "prov:type": "softwareAgent",
                "version": "1.0.0"
            },
            "model:llama3": {
                "prov:type": "softwareAgent",
                "version": "llama-3-8b"
            }
        },
        "wasGeneratedBy": [
            {
                "prov:entity": f"output:{output_hash}",
                "prov:activity": f"generation:{generation_id}"
            }
        ],
        "used": [
            {
                "prov:activity": f"generation:{generation_id}",
                "prov:entity": f"input:{input_hash}"
            }
        ],
        "wasAssociatedWith": [
            {
                "prov:activity": f"generation:{generation_id}",
                "prov:agent": "agent:filagent"
            }
        ],
        "wasAttributedTo": [
            {
                "prov:entity": f"output:{output_hash}",
                "prov:agent": "agent:filagent"
            }
        ]
    }

    # Add tool calls if requested
    if include_tool_calls:
        tool_id = f"tool-{uuid.uuid4().hex[:8]}"
        tool_output_hash = hashlib.sha256(b"tool output").hexdigest()[:16]

        prov_graph["entity"][f"tool_output:{tool_output_hash}"] = {
            "prov:label": "Tool execution result",
            "prov:type": "ToolOutput",
            "tool_name": "python_sandbox"
        }

        prov_graph["activity"][f"tool_exec:{tool_id}"] = {
            "prov:type": "ToolExecution",
            "prov:startTime": start_time,
            "prov:endTime": (datetime.now(timezone.utc) + timedelta(seconds=2)).isoformat(),
            "tool_name": "python_sandbox"
        }

        prov_graph["wasGeneratedBy"].append({
            "prov:entity": f"tool_output:{tool_output_hash}",
            "prov:activity": f"tool_exec:{tool_id}"
        })

        prov_graph["used"].append({
            "prov:activity": f"generation:{generation_id}",
            "prov:entity": f"tool_output:{tool_output_hash}"
        })

        prov_graph["wasDerivedFrom"] = [
            {
                "prov:generatedEntity": f"output:{output_hash}",
                "prov:usedEntity": f"tool_output:{tool_output_hash}"
            }
        ]

    return prov_graph


def generate_compliance_event(
    event_type: str = "tool.call",
    level: str = "INFO",
    conversation_id: Optional[str] = None,
    task_id: Optional[str] = None,
    pii_redacted: bool = True
) -> Dict[str, Any]:
    """
    Générer un événement de conformité (structured log)

    Args:
        event_type: Type d'événement
        level: Niveau de log (INFO, WARNING, ERROR)
        conversation_id: ID de conversation
        task_id: ID de tâche
        pii_redacted: Indiquer si PII a été masqué

    Returns:
        Dict: Événement structuré au format JSONL

    Example:
        >>> event = generate_compliance_event(event_type="pii.detected")
        >>> assert event['level'] == 'INFO'
        >>> assert event['pii_redacted'] is True
    """
    if conversation_id is None:
        conversation_id = generate_conversation_id()

    if task_id is None:
        task_id = generate_task_id()

    # Generate trace IDs (OpenTelemetry format)
    trace_id = uuid.uuid4().hex[:16]
    span_id = uuid.uuid4().hex[:8]

    event = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "trace_id": trace_id,
        "span_id": span_id,
        "level": level,
        "actor": "agent.core",
        "event": event_type,
        "task_id": task_id,
        "conversation_id": conversation_id,
        "pii_redacted": pii_redacted
    }

    # Add event-specific data
    event_data = _generate_event_data(event_type)
    event.update(event_data)

    return event


def _generate_event_data(event_type: str) -> Dict[str, Any]:
    """Generate event-specific data"""

    event_types = {
        "tool.call": {
            "tool_name": "python_sandbox",
            "tool_version": "v0.3",
            "execution_time_ms": 120
        },
        "pii.detected": {
            "pii_types": ["email", "phone"],
            "redaction_applied": True,
            "patterns_matched": 2
        },
        "decision.made": {
            "decision_type": "tool_invocation",
            "confidence": 0.85,
            "reasoning": "User requested code execution"
        },
        "error.occurred": {
            "error_type": "ValidationError",
            "error_message": "Input validation failed",
            "stack_trace": "..."
        }
    }

    return event_types.get(event_type, {})


def generate_pii_scenario(
    include_email: bool = True,
    include_phone: bool = True,
    include_ssn: bool = False,
    include_address: bool = False
) -> Tuple[str, Dict[str, List[str]]]:
    """
    Générer un scénario avec PII pour tester la redaction

    Args:
        include_email: Inclure des emails
        include_phone: Inclure des téléphones
        include_ssn: Inclure des numéros d'assurance sociale
        include_address: Inclure des adresses

    Returns:
        Tuple[str, Dict]: (texte avec PII, dictionnaire des PII détectés)

    Example:
        >>> text, pii_map = generate_pii_scenario(include_email=True)
        >>> assert '@' in text
        >>> assert 'email' in pii_map
    """
    text_parts = ["Voici les informations du client:"]
    pii_detected = {}

    if include_email:
        email = "john.doe@example.com"
        text_parts.append(f"Email: {email}")
        pii_detected['email'] = [email]

    if include_phone:
        phone = "+1 (555) 123-4567"
        text_parts.append(f"Téléphone: {phone}")
        pii_detected['phone'] = [phone]

    if include_ssn:
        ssn = "123-45-6789"
        text_parts.append(f"SSN: {ssn}")
        pii_detected['ssn'] = [ssn]

    if include_address:
        address = "123 Main Street, Montreal, QC H3A 1A1"
        text_parts.append(f"Adresse: {address}")
        pii_detected['address'] = [address]

    full_text = " ".join(text_parts)

    return full_text, pii_detected


# ============================================================================
# SECTION 4: Batch Generators
# ============================================================================


def generate_batch_conversations(
    count: int = 10,
    min_turns: int = 1,
    max_turns: int = 5
) -> List[ConversationData]:
    """
    Générer un lot de conversations pour tests de performance

    Args:
        count: Nombre de conversations à générer
        min_turns: Nombre minimum de tours par conversation
        max_turns: Nombre maximum de tours par conversation

    Returns:
        List[ConversationData]: Liste de conversations générées

    Example:
        >>> conversations = generate_batch_conversations(count=5)
        >>> assert len(conversations) == 5
    """
    conversations = []

    for i in range(count):
        num_turns = random.randint(min_turns, max_turns)
        include_tool_calls = random.choice([True, False])

        conv = generate_conversation(
            num_turns=num_turns,
            include_tool_calls=include_tool_calls
        )

        conversations.append(conv)

    return conversations


def generate_batch_task_graphs(
    count: int = 10,
    complexity: str = "simple"
) -> List['TaskGraph']:
    """
    Générer un lot de graphes de tâches

    Args:
        count: Nombre de graphes à générer
        complexity: Niveau de complexité

    Returns:
        List[TaskGraph]: Liste de graphes générés
    """
    graphs = []

    for i in range(count):
        graph = generate_task_graph(complexity=complexity)
        graphs.append(graph)

    return graphs


def generate_batch_decision_records(
    count: int = 10,
    decision_types: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Générer un lot de Decision Records

    Args:
        count: Nombre de DRs à générer
        decision_types: Types de décisions (tous types si None)

    Returns:
        List[Dict]: Liste de Decision Records
    """
    if decision_types is None:
        decision_types = ["tool_invocation", "planning", "data_access", "pii_handling"]

    records = []

    for i in range(count):
        decision_type = random.choice(decision_types)
        dr = generate_decision_record(decision_type=decision_type)
        records.append(dr)

    return records


# ============================================================================
# SECTION 5: Integration Helpers
# ============================================================================


def populate_test_database(
    db_connection,
    num_conversations: int = 5,
    messages_per_conversation: int = 10
) -> List[str]:
    """
    Peupler une base de données de test avec des conversations

    Args:
        db_connection: Connexion SQLite
        num_conversations: Nombre de conversations
        messages_per_conversation: Messages par conversation

    Returns:
        List[str]: Liste des conversation_ids créés

    Example:
        >>> import sqlite3
        >>> conn = sqlite3.connect(':memory:')
        >>> # Create tables first...
        >>> conv_ids = populate_test_database(conn, num_conversations=3)
        >>> assert len(conv_ids) == 3
    """
    from memory.episodic import create_tables, add_message

    conversation_ids = []

    for i in range(num_conversations):
        conv_data = generate_conversation(
            num_turns=messages_per_conversation // 2,
            include_tool_calls=i % 2 == 0
        )

        # Add messages to database
        for msg in conv_data.messages:
            add_message(
                conversation_id=conv_data.conversation_id,
                role=msg['role'],
                content=msg['content'],
                task_id=conv_data.task_id,
                message_type=msg.get('message_type', 'text'),
                metadata=msg.get('metadata')
            )

        conversation_ids.append(conv_data.conversation_id)

    return conversation_ids


def generate_complete_test_scenario() -> Dict[str, Any]:
    """
    Générer un scénario de test complet avec tous les éléments

    Crée un scénario intégré comprenant:
    - Une conversation multi-tours
    - Un graphe HTN associé
    - Des Decision Records pour chaque étape
    - Un graphe de provenance PROV-JSON
    - Des événements de conformité

    Returns:
        Dict: Scénario de test complet avec tous les composants

    Example:
        >>> scenario = generate_complete_test_scenario()
        >>> assert 'conversation' in scenario
        >>> assert 'task_graph' in scenario
        >>> assert 'decision_records' in scenario
        >>> assert 'provenance' in scenario
    """
    # Generate base identifiers
    conversation_id = generate_conversation_id()
    task_id = generate_task_id()

    # Generate conversation
    conversation = generate_conversation(
        num_turns=3,
        include_system=True,
        include_tool_calls=True,
        conversation_id=conversation_id,
        task_id=task_id
    )

    # Generate HTN task graph
    task_graph = generate_complex_task_graph()

    # Generate decision records for each major step
    decision_records = [
        generate_decision_record(
            decision_type="planning",
            task_id=task_id
        ),
        generate_decision_record(
            decision_type="tool_invocation",
            task_id=task_id
        ),
        generate_decision_record(
            decision_type="data_access",
            task_id=task_id
        )
    ]

    # Generate provenance graph
    provenance = generate_prov_graph(
        conversation_id=conversation_id,
        include_tool_calls=True
    )

    # Generate compliance events
    compliance_events = [
        generate_compliance_event(
            event_type="tool.call",
            conversation_id=conversation_id,
            task_id=task_id
        ),
        generate_compliance_event(
            event_type="decision.made",
            conversation_id=conversation_id,
            task_id=task_id
        )
    ]

    return {
        "conversation_id": conversation_id,
        "task_id": task_id,
        "conversation": conversation,
        "task_graph": task_graph,
        "decision_records": decision_records,
        "provenance": provenance,
        "compliance_events": compliance_events,
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "scenario_type": "complete_integration",
            "version": "1.0.0"
        }
    }
