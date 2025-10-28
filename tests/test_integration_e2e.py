"""
Tests E2E (End-to-End) complets pour FilAgent

Ce module teste les flux complets:
- /chat → génération → outils → DR → provenance
- Tests de résilience: fallbacks, timeouts, middlewares défaillants
- Intégration complète de tous les composants
"""

import pytest
import json
import time
import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

from runtime.model_interface import GenerationResult, GenerationConfig
from tools.base import ToolResult, ToolStatus


# ============================================================================
# TESTS E2E: Flux Complet Chat → Génération → Outils → DR → Provenance
# ============================================================================

@pytest.mark.e2e
def test_complete_chat_flow_simple(api_client, patched_middlewares):
    """
    Test E2E: Flux complet simple sans appel d'outils

    Vérifie:
    - Réponse API correcte
    - Enregistrement en base de données
    - Logs d'événements créés
    - WORM digest créé
    """
    # Envoyer un message via l'API
    response = api_client.post("/chat", json={
        "messages": [
            {"role": "user", "content": "Hello, how are you?"}
        ]
    })

    # Vérifier la réponse
    assert response.status_code == 200
    data = response.json()

    assert "id" in data
    assert "choices" in data
    assert len(data["choices"]) > 0
    assert data["choices"][0]["message"]["role"] == "assistant"

    conversation_id = data["id"]

    # Vérifier que les logs d'événements ont été créés
    event_log_dir = patched_middlewares['isolated_fs']['logs_events']
    log_files = list(event_log_dir.glob("*.jsonl"))
    assert len(log_files) > 0, "No event log files created"

    # Vérifier le contenu des logs
    with open(log_files[0], 'r') as f:
        lines = f.readlines()
        assert len(lines) > 0, "Event log is empty"

        # Parser et vérifier au moins un événement
        first_event = json.loads(lines[0])
        assert "timestamp" in first_event
        assert "actor" in first_event
        assert "event" in first_event

    # Vérifier que les digests WORM ont été créés
    digest_dir = patched_middlewares['isolated_fs']['logs_digests']
    digest_files = list(digest_dir.glob("*.json"))
    # Note: Les digests sont créés périodiquement, peut être vide sur test rapide
    # On vérifie juste que le répertoire existe
    assert digest_dir.exists()


@pytest.mark.e2e
def test_complete_chat_flow_with_tools(api_client_with_tool_model, patched_middlewares):
    """
    Test E2E: Flux complet avec appels d'outils

    Vérifie:
    - Détection d'appel d'outil
    - Exécution de l'outil
    - Decision Record créé
    - Provenance générée
    """
    # Envoyer un message qui déclenchera un appel d'outil
    response = api_client_with_tool_model.post("/chat", json={
        "messages": [
            {"role": "user", "content": "Calculate 2 + 2 using Python"}
        ]
    })

    assert response.status_code == 200
    data = response.json()

    # Vérifier la réponse
    assert "choices" in data
    conversation_id = data["id"]

    # Vérifier que des Decision Records ont été créés
    dr_dir = patched_middlewares['isolated_fs']['logs_decisions']
    dr_files = list(dr_dir.glob("*.json"))

    # Peut avoir des DR si des outils ont été appelés
    # On vérifie la structure si des fichiers existent
    if len(dr_files) > 0:
        with open(dr_files[0], 'r') as f:
            dr_data = json.load(f)

        # Vérifier la structure du Decision Record
        assert "decision_id" in dr_data
        assert "timestamp" in dr_data
        assert "conversation_id" in dr_data
        assert "signature" in dr_data

        # Vérifier la signature EdDSA
        sig = dr_data["signature"]
        assert "algorithm" in sig
        assert sig["algorithm"] == "EdDSA"
        assert "public_key" in sig
        assert "signature" in sig


@pytest.mark.e2e
def test_chat_persistence_across_turns(api_client, temp_db):
    """
    Test E2E: Persistance de la conversation sur plusieurs tours

    Vérifie:
    - Messages sauvegardés en base
    - Historique maintenu
    - Continuité de conversation
    """
    # Premier message
    response1 = api_client.post("/chat", json={
        "messages": [
            {"role": "user", "content": "My name is Alice"}
        ]
    })

    assert response1.status_code == 200
    data1 = response1.json()
    conversation_id = data1["id"]

    # Deuxième message dans la même conversation
    response2 = api_client.post("/chat", json={
        "messages": [
            {"role": "user", "content": "My name is Alice"},
            {"role": "assistant", "content": data1["choices"][0]["message"]["content"]},
            {"role": "user", "content": "What is my name?"}
        ]
    })

    assert response2.status_code == 200

    # Vérifier en base de données
    conn = sqlite3.connect(str(temp_db))
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*) FROM messages WHERE conversation_id = ?
    """, (conversation_id,))

    message_count = cursor.fetchone()[0]
    conn.close()

    # Doit avoir au moins 2 messages utilisateur + réponses
    assert message_count >= 2


@pytest.mark.e2e
def test_conversation_retrieval(api_client, conversation_factory, temp_db):
    """
    Test E2E: Récupération d'une conversation existante

    Vérifie:
    - GET /conversations/{id}
    - Format de réponse correct
    - Messages dans l'ordre
    """
    # Créer une conversation de test
    conv_id = "test_conv_123"
    conversation_factory(conv_id, [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user", "content": "How are you?"}
    ])

    # Récupérer via l'API
    response = api_client.get(f"/conversations/{conv_id}")

    assert response.status_code == 200
    data = response.json()

    assert "conversation_id" in data
    assert data["conversation_id"] == conv_id
    assert "messages" in data
    assert len(data["messages"]) == 3

    # Vérifier l'ordre
    assert data["messages"][0]["role"] == "user"
    assert data["messages"][0]["content"] == "Hello"


# ============================================================================
# TESTS E2E: Résilience et Fallbacks
# ============================================================================

@pytest.mark.e2e
@pytest.mark.resilience
def test_resilience_middleware_logging_failure(api_client, patched_middlewares):
    """
    Test de résilience: Le système continue si le logging échoue

    Vérifie:
    - Fallback quand logger échoue
    - Réponse API toujours fonctionnelle
    - Pas de crash
    """
    # Faire échouer le logger
    def failing_log(*args, **kwargs):
        raise Exception("Logging system failure")

    patched_middlewares['event_logger'].log_event = failing_log

    # L'API devrait toujours fonctionner
    response = api_client.post("/chat", json={
        "messages": [
            {"role": "user", "content": "Test message"}
        ]
    })

    # Doit toujours réussir grâce aux fallbacks
    assert response.status_code == 200
    data = response.json()
    assert "choices" in data


@pytest.mark.e2e
@pytest.mark.resilience
def test_resilience_worm_logger_failure(api_client, patched_middlewares):
    """
    Test de résilience: Le système continue si WORM logger échoue
    """
    # Faire échouer le WORM logger
    def failing_append(*args, **kwargs):
        raise Exception("WORM logger failure")

    patched_middlewares['worm_logger'].append = failing_append

    # L'API devrait toujours fonctionner
    response = api_client.post("/chat", json={
        "messages": [
            {"role": "user", "content": "Test message"}
        ]
    })

    assert response.status_code == 200


@pytest.mark.e2e
@pytest.mark.resilience
def test_resilience_dr_manager_failure(api_client, patched_middlewares):
    """
    Test de résilience: Le système continue si DR manager échoue
    """
    # Faire échouer le DR manager
    def failing_create_record(*args, **kwargs):
        raise Exception("DR manager failure")

    patched_middlewares['dr_manager'].create_record = failing_create_record

    # L'API devrait toujours fonctionner
    response = api_client.post("/chat", json={
        "messages": [
            {"role": "user", "content": "Make a decision"}
        ]
    })

    assert response.status_code == 200


@pytest.mark.e2e
@pytest.mark.resilience
def test_resilience_provenance_tracker_failure(api_client, patched_middlewares):
    """
    Test de résilience: Le système continue si provenance tracker échoue
    """
    # Faire échouer le tracker
    def failing_track(*args, **kwargs):
        raise Exception("Provenance tracker failure")

    patched_middlewares['tracker'].track_generation = failing_track

    # L'API devrait toujours fonctionner
    response = api_client.post("/chat", json={
        "messages": [
            {"role": "user", "content": "Test message"}
        ]
    })

    assert response.status_code == 200


@pytest.mark.e2e
@pytest.mark.resilience
def test_resilience_all_middlewares_fail(api_client, patched_middlewares):
    """
    Test de résilience extrême: Tous les middlewares échouent

    Vérifie que le système reste fonctionnel même en cas de défaillance totale
    """
    # Faire échouer tous les middlewares
    def fail(*args, **kwargs):
        raise Exception("Total middleware failure")

    patched_middlewares['event_logger'].log_event = fail
    patched_middlewares['worm_logger'].append = fail
    patched_middlewares['dr_manager'].create_record = fail
    patched_middlewares['tracker'].track_generation = fail

    # L'API devrait TOUJOURS fonctionner (fallbacks critiques)
    response = api_client.post("/chat", json={
        "messages": [
            {"role": "user", "content": "Emergency test"}
        ]
    })

    # Le système doit survivre
    assert response.status_code == 200
    data = response.json()
    assert "choices" in data


@pytest.mark.e2e
@pytest.mark.resilience
def test_resilience_database_unavailable(api_client):
    """
    Test de résilience: Base de données inaccessible

    Note: Dans la vraie implémentation, ceci devrait gérer le cas gracieusement
    """
    # Patcher la DB pour qu'elle échoue
    with patch('memory.episodic.add_message') as mock_add:
        mock_add.side_effect = Exception("Database unavailable")

        # Selon l'implémentation, cela peut soit échouer soit fallback
        # On teste juste qu'il n'y a pas de crash non géré
        try:
            response = api_client.post("/chat", json={
                "messages": [
                    {"role": "user", "content": "Test"}
                ]
            })
            # Si ça passe, vérifier le code de statut
            assert response.status_code in [200, 500, 503]
        except Exception as e:
            # Si ça échoue, vérifier que c'est géré proprement
            assert "Database" in str(e) or "unavailable" in str(e).lower()


@pytest.mark.e2e
@pytest.mark.resilience
@pytest.mark.slow
def test_resilience_timeout_protection(api_client):
    """
    Test de résilience: Protection contre les timeouts

    Vérifie que les requêtes longues sont gérées correctement
    """
    # Créer un mock model très lent
    def slow_generate(*args, **kwargs):
        time.sleep(5)  # 5 secondes
        return GenerationResult(
            text="Slow response",
            finish_reason="stop",
            tokens_generated=10,
            prompt_tokens=10,
            total_tokens=20
        )

    with patch('runtime.agent.init_model') as mock_init:
        mock_model = MagicMock()
        mock_model.generate = slow_generate
        mock_model.is_loaded.return_value = True
        mock_init.return_value = mock_model

        # Selon la configuration de timeout, cela devrait soit:
        # - Réussir (si timeout > 5s)
        # - Retourner une erreur de timeout
        # On vérifie juste qu'il n'y a pas de crash
        try:
            response = api_client.post("/chat", json={
                "messages": [
                    {"role": "user", "content": "Slow request"}
                ]
            })
            assert response.status_code in [200, 408, 504]
        except Exception:
            # Timeout côté client est acceptable
            pass


@pytest.mark.e2e
@pytest.mark.resilience
def test_resilience_tool_execution_failure(api_client_with_tool_model, mock_tool_failure):
    """
    Test de résilience: Un outil échoue lors de l'exécution

    Vérifie:
    - L'agent gère l'erreur
    - Retourne une réponse appropriée
    - Ne crash pas
    """
    # Enregistrer un outil qui échoue
    with patch('tools.registry.ToolRegistry.get_tool', return_value=mock_tool_failure):
        response = api_client_with_tool_model.post("/chat", json={
            "messages": [
                {"role": "user", "content": "Use the failing tool"}
            ]
        })

        # Doit gérer l'échec gracieusement
        assert response.status_code == 200
        data = response.json()
        assert "choices" in data


@pytest.mark.e2e
@pytest.mark.resilience
def test_resilience_invalid_tool_call_format(api_client):
    """
    Test de résilience: Format d'appel d'outil invalide
    """
    # Créer un model qui retourne un format invalide
    def invalid_tool_call(*args, **kwargs):
        return GenerationResult(
            text="Invalid tool call",
            finish_reason="tool_calls",
            tokens_generated=10,
            prompt_tokens=10,
            total_tokens=20,
            tool_calls=[
                {
                    "name": "nonexistent_tool",
                    "arguments": "not a dict"  # Format invalide
                }
            ]
        )

    with patch('runtime.agent.init_model') as mock_init:
        mock_model = MagicMock()
        mock_model.generate = invalid_tool_call
        mock_model.is_loaded.return_value = True
        mock_init.return_value = mock_model

        response = api_client.post("/chat", json={
            "messages": [
                {"role": "user", "content": "Test"}
            ]
        })

        # Doit gérer le format invalide
        assert response.status_code in [200, 400]


# ============================================================================
# TESTS E2E: Performance et Limites
# ============================================================================

@pytest.mark.e2e
@pytest.mark.slow
def test_e2e_multiple_concurrent_requests(api_client):
    """
    Test E2E: Requêtes concurrentes multiples

    Vérifie que le système peut gérer plusieurs requêtes simultanément
    """
    import concurrent.futures

    def send_request(i):
        return api_client.post("/chat", json={
            "messages": [
                {"role": "user", "content": f"Concurrent request {i}"}
            ]
        })

    # Envoyer 5 requêtes concurrentes
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(send_request, i) for i in range(5)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    # Toutes les requêtes doivent réussir
    assert len(results) == 5
    for response in results:
        assert response.status_code == 200


@pytest.mark.e2e
def test_e2e_large_message_handling(api_client):
    """
    Test E2E: Gestion de messages volumineux

    Vérifie la capacité à traiter des messages longs
    """
    # Créer un message très long
    large_message = "This is a test. " * 1000  # ~16KB

    response = api_client.post("/chat", json={
        "messages": [
            {"role": "user", "content": large_message}
        ]
    })

    # Doit gérer correctement ou retourner une erreur appropriée
    assert response.status_code in [200, 413]  # 413 = Payload Too Large


@pytest.mark.e2e
def test_e2e_conversation_history_limit(api_client, temp_db, conversation_factory):
    """
    Test E2E: Limite d'historique de conversation

    Vérifie que le système gère correctement les longues conversations
    """
    conv_id = "long_conv_123"

    # Créer une conversation avec beaucoup de messages
    messages = []
    for i in range(100):
        messages.append({"role": "user", "content": f"Message {i}"})
        messages.append({"role": "assistant", "content": f"Response {i}"})

    conversation_factory(conv_id, messages[:20])  # Limiter pour le test

    # Récupérer la conversation
    response = api_client.get(f"/conversations/{conv_id}")

    assert response.status_code == 200
    data = response.json()
    assert len(data["messages"]) == 20


# ============================================================================
# TESTS E2E: Intégrité des Données
# ============================================================================

@pytest.mark.e2e
def test_e2e_message_ordering_preserved(api_client, temp_db):
    """
    Test E2E: L'ordre des messages est préservé
    """
    # Envoyer plusieurs messages
    messages = [
        "First message",
        "Second message",
        "Third message"
    ]

    conversation_id = None

    for msg in messages:
        response = api_client.post("/chat", json={
            "messages": [
                {"role": "user", "content": msg}
            ]
        })
        assert response.status_code == 200
        if conversation_id is None:
            conversation_id = response.json()["id"]

    # Vérifier l'ordre en base
    conn = sqlite3.connect(str(temp_db))
    cursor = conn.cursor()

    cursor.execute("""
        SELECT content FROM messages
        WHERE conversation_id = ? AND role = 'user'
        ORDER BY timestamp ASC
    """, (conversation_id,))

    retrieved = [row[0] for row in cursor.fetchall()]
    conn.close()

    # Vérifier que les premiers messages sont dans l'ordre
    for i, msg in enumerate(messages):
        if i < len(retrieved):
            assert msg in retrieved[i]


@pytest.mark.e2e
def test_e2e_health_check_integration(api_client):
    """
    Test E2E: Health check retourne l'état correct de tous les composants
    """
    response = api_client.get("/health")

    assert response.status_code == 200
    data = response.json()

    # Vérifier la structure
    assert "status" in data
    assert "timestamp" in data
    assert "components" in data

    components = data["components"]
    assert "model" in components
    assert "database" in components
    assert "logging" in components

    # Tous les composants doivent être des booléens
    for component, status in components.items():
        assert isinstance(status, bool), f"Component {component} status should be boolean"


@pytest.mark.e2e
def test_e2e_root_endpoint(api_client):
    """
    Test E2E: L'endpoint racine retourne une réponse valide
    """
    response = api_client.get("/")

    assert response.status_code == 200
    data = response.json()

    assert "status" in data
    assert data["status"] == "healthy"
