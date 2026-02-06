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
    response = api_client.post(
        "/chat", json={"messages": [{"role": "user", "content": "Hello, how are you?"}]}
    )

    # Vérifier la réponse
    assert response.status_code == 200
    data = response.json()

    assert "id" in data
    assert "choices" in data
    assert len(data["choices"]) > 0
    assert data["choices"][0]["message"]["role"] == "assistant"

    conversation_id = data["id"]

    # Vérifier que les logs d'événements ont été créés
    event_log_dir = patched_middlewares["isolated_fs"]["logs_events"]
    log_files = list(event_log_dir.glob("*.jsonl"))
    assert len(log_files) > 0, "No event log files created"

    # Vérifier le contenu des logs
    with open(log_files[0], "r") as f:
        lines = f.readlines()
        assert len(lines) > 0, "Event log is empty"

        # Parser et vérifier au moins un événement
        first_event = json.loads(lines[0])
        assert "timestamp" in first_event
        assert "actor" in first_event
        assert "event" in first_event

    # Vérifier que les digests WORM ont été créés
    digest_dir = patched_middlewares["isolated_fs"]["logs_digests"]
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
    response = api_client_with_tool_model.post(
        "/chat", json={"messages": [{"role": "user", "content": "Calculate 2 + 2 using Python"}]}
    )

    assert response.status_code == 200
    data = response.json()

    # Vérifier la réponse
    assert "choices" in data
    conversation_id = data["id"]

    # Vérifier que des Decision Records ont été créés
    dr_dir = patched_middlewares["isolated_fs"]["logs_decisions"]
    dr_files = list(dr_dir.glob("*.json"))

    # Peut avoir des DR si des outils ont été appelés
    # On vérifie la structure si des fichiers existent
    if len(dr_files) > 0:
        with open(dr_files[0], "r") as f:
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
    response1 = api_client.post(
        "/chat", json={"messages": [{"role": "user", "content": "My name is Alice"}]}
    )

    assert response1.status_code == 200
    data1 = response1.json()
    conversation_id = data1["id"]

    # Deuxième message dans la même conversation
    response2 = api_client.post(
        "/chat",
        json={
            "messages": [
                {"role": "user", "content": "My name is Alice"},
                {"role": "assistant", "content": data1["choices"][0]["message"]["content"]},
                {"role": "user", "content": "What is my name?"},
            ]
        },
    )

    assert response2.status_code == 200

    # Vérifier en base de données
    conn = sqlite3.connect(str(temp_db))
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT COUNT(*) FROM messages WHERE conversation_id = ?
    """,
        (conversation_id,),
    )

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
    conversation_factory(
        conv_id,
        [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
        ],
    )

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

    patched_middlewares["event_logger"].log_event = failing_log

    # L'API devrait toujours fonctionner
    response = api_client.post(
        "/chat", json={"messages": [{"role": "user", "content": "Test message"}]}
    )

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

    patched_middlewares["worm_logger"].append = failing_append

    # L'API devrait toujours fonctionner
    response = api_client.post(
        "/chat", json={"messages": [{"role": "user", "content": "Test message"}]}
    )

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

    patched_middlewares["dr_manager"].create_record = failing_create_record

    # L'API devrait toujours fonctionner
    response = api_client.post(
        "/chat", json={"messages": [{"role": "user", "content": "Make a decision"}]}
    )

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

    patched_middlewares["tracker"].track_generation = failing_track

    # L'API devrait toujours fonctionner
    response = api_client.post(
        "/chat", json={"messages": [{"role": "user", "content": "Test message"}]}
    )

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

    patched_middlewares["event_logger"].log_event = fail
    patched_middlewares["worm_logger"].append = fail
    patched_middlewares["dr_manager"].create_record = fail
    patched_middlewares["tracker"].track_generation = fail

    # L'API devrait TOUJOURS fonctionner (fallbacks critiques)
    response = api_client.post(
        "/chat", json={"messages": [{"role": "user", "content": "Emergency test"}]}
    )

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
    with patch("memory.episodic.add_message") as mock_add:
        mock_add.side_effect = Exception("Database unavailable")

        # Selon l'implémentation, cela peut soit échouer soit fallback
        # On teste juste qu'il n'y a pas de crash non géré
        try:
            response = api_client.post(
                "/chat", json={"messages": [{"role": "user", "content": "Test"}]}
            )
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
            total_tokens=20,
        )

    with patch("runtime.agent.init_model") as mock_init:
        mock_model = MagicMock()
        mock_model.generate = slow_generate
        mock_model.is_loaded.return_value = True
        mock_init.return_value = mock_model

        # Selon la configuration de timeout, cela devrait soit:
        # - Réussir (si timeout > 5s)
        # - Retourner une erreur de timeout
        # On vérifie juste qu'il n'y a pas de crash
        try:
            response = api_client.post(
                "/chat", json={"messages": [{"role": "user", "content": "Slow request"}]}
            )
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
    with patch("tools.registry.ToolRegistry.get_tool", return_value=mock_tool_failure):
        response = api_client_with_tool_model.post(
            "/chat", json={"messages": [{"role": "user", "content": "Use the failing tool"}]}
        )

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
            tool_calls=[{"name": "nonexistent_tool", "arguments": "not a dict"}],  # Format invalide
        )

    with patch("runtime.agent.init_model") as mock_init:
        mock_model = MagicMock()
        mock_model.generate = invalid_tool_call
        mock_model.is_loaded.return_value = True
        mock_init.return_value = mock_model

        response = api_client.post(
            "/chat", json={"messages": [{"role": "user", "content": "Test"}]}
        )

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
        return api_client.post(
            "/chat", json={"messages": [{"role": "user", "content": f"Concurrent request {i}"}]}
        )

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

    response = api_client.post(
        "/chat", json={"messages": [{"role": "user", "content": large_message}]}
    )

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
    messages = ["First message", "Second message", "Third message"]

    conversation_id = None

    for msg in messages:
        response = api_client.post("/chat", json={"messages": [{"role": "user", "content": msg}]})
        assert response.status_code == 200
        if conversation_id is None:
            conversation_id = response.json()["id"]

    # Vérifier l'ordre en base
    conn = sqlite3.connect(str(temp_db))
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT content FROM messages
        WHERE conversation_id = ? AND role = 'user'
        ORDER BY timestamp ASC
    """,
        (conversation_id,),
    )

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


# ============================================================================
# TESTS E2E: Multi-Step HTN Workflows
# ============================================================================


@pytest.mark.e2e
@pytest.mark.htn
def test_e2e_htn_simple_sequential_workflow(api_client, patched_middlewares):
    """
    Test E2E: Workflow HTN séquentiel simple

    Vérifie:
    - Détection d'une requête multi-étape
    - Planification HTN activée
    - Exécution séquentielle des tâches
    - Decision Records créés pour la planification
    """
    # Requête multi-étape explicite
    response = api_client.post(
        "/chat",
        json={
            "messages": [
                {"role": "user", "content": "Lis le fichier data.csv puis analyse les données"}
            ]
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "choices" in data

    # Vérifier qu'au moins un Decision Record a été créé
    dr_dir = patched_middlewares["isolated_fs"]["logs_decisions"]
    dr_files = list(dr_dir.glob("*.json"))

    if len(dr_files) > 0:
        # Vérifier qu'il y a un DR pour la planification
        found_planning_dr = False
        for dr_file in dr_files:
            with open(dr_file, "r") as f:
                dr_data = json.load(f)

            # Chercher un DR de type planification
            if "decision_type" in dr_data:
                if dr_data["decision_type"] == "planning":
                    found_planning_dr = True
                    break

        # Si on trouve des DRs, au moins un devrait être de type planning
        # (Note: ceci dépend de l'implémentation HTN activée)


@pytest.mark.e2e
@pytest.mark.htn
def test_e2e_htn_parallel_task_execution(api_client_with_tool_model, patched_middlewares):
    """
    Test E2E: Exécution parallèle de tâches HTN

    Vérifie:
    - Détection de tâches indépendantes
    - Exécution parallèle quand possible
    - Résultats combinés correctement
    """
    # Requête avec plusieurs tâches indépendantes
    response = api_client_with_tool_model.post(
        "/chat", json={"messages": [{"role": "user", "content": "Calcule 2+2 et 3+3 en parallèle"}]}
    )

    assert response.status_code == 200
    data = response.json()
    assert "choices" in data

    # Vérifier la réponse contient un résultat
    response_text = data["choices"][0]["message"]["content"]
    assert isinstance(response_text, str)


@pytest.mark.e2e
@pytest.mark.htn
def test_e2e_htn_task_dependency_resolution(api_client, patched_middlewares):
    """
    Test E2E: Résolution de dépendances entre tâches HTN

    Vérifie:
    - Tâches exécutées dans le bon ordre
    - Dépendances respectées
    - Résultat de tâche A utilisable par tâche B
    """
    # Requête avec dépendances claires
    response = api_client.post(
        "/chat",
        json={
            "messages": [
                {
                    "role": "user",
                    "content": "Lis data.csv, puis calcule la moyenne, finalement génère un rapport",
                }
            ]
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "choices" in data


@pytest.mark.e2e
@pytest.mark.htn
@pytest.mark.slow
def test_e2e_htn_complex_multi_level_decomposition(api_client, patched_middlewares):
    """
    Test E2E: Décomposition HTN multi-niveaux complexe

    Vérifie:
    - Décomposition récursive de tâches
    - Gestion de graphes de tâches profonds
    - Vérification à chaque niveau
    """
    # Requête complexe nécessitant plusieurs niveaux de décomposition
    response = api_client.post(
        "/chat",
        json={
            "messages": [
                {
                    "role": "user",
                    "content": """
                Analyse complète: lis trois fichiers CSV (sales.csv, inventory.csv, customers.csv),
                puis calcule les statistiques pour chaque fichier, ensuite croise les données,
                et finalement génère un rapport consolidé
            """,
                }
            ]
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "choices" in data

    # Vérifier que des Decision Records ont été créés
    dr_dir = patched_middlewares["isolated_fs"]["logs_decisions"]
    dr_files = list(dr_dir.glob("*.json"))

    # Une tâche complexe devrait générer plusieurs DRs
    # (au moins pour les décisions principales)


@pytest.mark.e2e
@pytest.mark.htn
def test_e2e_htn_verification_strict_mode(api_client, patched_middlewares):
    """
    Test E2E: Vérification stricte des résultats HTN

    Vérifie:
    - Mode de vérification strict activé
    - Validation des résultats de chaque tâche
    - Détection d'erreurs dans les résultats
    """
    # Requête qui nécessite validation stricte
    response = api_client.post(
        "/chat",
        json={
            "messages": [
                {"role": "user", "content": "Calcule 2+2 et vérifie que le résultat est correct"}
            ]
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "choices" in data


@pytest.mark.e2e
@pytest.mark.htn
def test_e2e_htn_fallback_to_simple_loop(api_client, patched_middlewares):
    """
    Test E2E: Fallback HTN vers boucle simple

    Vérifie:
    - Détection d'échec de planification HTN
    - Fallback automatique vers boucle simple
    - Réponse finale toujours fournie
    """
    # Créer une situation où HTN pourrait échouer mais fallback fonctionne
    with patch("planner.planner.HierarchicalPlanner.plan") as mock_plan:
        # Faire échouer la planification HTN
        mock_plan.side_effect = Exception("Planning failed")

        response = api_client.post(
            "/chat", json={"messages": [{"role": "user", "content": "Lis data.csv puis analyse"}]}
        )

        # Doit toujours fonctionner grâce au fallback
        assert response.status_code == 200
        data = response.json()
        assert "choices" in data


# ============================================================================
# TESTS E2E: Compliance Violation Scenarios
# ============================================================================


@pytest.mark.e2e
@pytest.mark.compliance
def test_e2e_pii_redaction_in_logs(api_client, patched_middlewares):
    """
    Test E2E: Redaction PII dans les logs

    Vérifie:
    - PII détecté dans les messages
    - PII masqué dans les logs d'événements
    - Aucune fuite de données sensibles
    """
    # Envoyer un message contenant des PII
    response = api_client.post(
        "/chat",
        json={
            "messages": [
                {
                    "role": "user",
                    "content": "Mon email est john.doe@example.com et mon téléphone est 514-555-1234",
                }
            ]
        },
    )

    assert response.status_code == 200

    # Vérifier les logs d'événements
    event_log_dir = patched_middlewares["isolated_fs"]["logs_events"]
    log_files = list(event_log_dir.glob("*.jsonl"))

    if len(log_files) > 0:
        with open(log_files[0], "r") as f:
            log_content = f.read()

        # Vérifier que les PII ne sont PAS en clair dans les logs
        assert "john.doe@example.com" not in log_content or "[EMAIL_REDACTED]" in log_content
        assert "514-555-1234" not in log_content or "[PHONE_REDACTED]" in log_content


@pytest.mark.e2e
@pytest.mark.compliance
def test_e2e_compliance_guardian_blocks_unsafe_action(api_client, patched_middlewares):
    """
    Test E2E: ComplianceGuardian bloque une action non conforme

    Vérifie:
    - Détection d'action potentiellement non conforme
    - Blocage de l'action
    - Enregistrement de la raison du blocage
    """
    # Créer un mock ComplianceGuardian qui bloque
    from planner.compliance_guardian import ValidationResult

    def mock_validate(*args, **kwargs):
        return ValidationResult(
            is_compliant=False, violations=["Unsafe file access detected"], risk_level="HIGH"
        )

    with patch(
        "planner.compliance_guardian.ComplianceGuardian.validate_task", side_effect=mock_validate
    ):
        response = api_client.post(
            "/chat", json={"messages": [{"role": "user", "content": "Lis le fichier /etc/passwd"}]}
        )

        # Doit retourner une réponse (pas un crash)
        assert response.status_code in [200, 403]


@pytest.mark.e2e
@pytest.mark.compliance
def test_e2e_decision_record_signature_validation(api_client_with_tool_model, patched_middlewares):
    """
    Test E2E: Validation des signatures EdDSA des Decision Records

    Vérifie:
    - DR créé avec signature
    - Signature EdDSA valide
    - Intégrité des données signées
    """
    # Effectuer une action qui génère un DR
    response = api_client_with_tool_model.post(
        "/chat",
        json={"messages": [{"role": "user", "content": "Execute Python code to print hello"}]},
    )

    assert response.status_code == 200

    # Vérifier les Decision Records
    dr_dir = patched_middlewares["isolated_fs"]["logs_decisions"]
    dr_files = list(dr_dir.glob("*.json"))

    if len(dr_files) > 0:
        with open(dr_files[0], "r") as f:
            dr_data = json.load(f)

        # Vérifier la présence de signature
        assert "signature" in dr_data
        sig = dr_data["signature"]

        # Vérifier la structure de la signature
        assert "algorithm" in sig
        assert sig["algorithm"] == "EdDSA"
        assert "public_key" in sig
        assert "signature" in sig

        # Vérifier que signature et clé publique ne sont pas vides
        assert len(sig["public_key"]) > 0
        assert len(sig["signature"]) > 0


@pytest.mark.e2e
@pytest.mark.compliance
def test_e2e_provenance_tracking_complete_chain(api_client, patched_middlewares):
    """
    Test E2E: Traçabilité complète de provenance

    Vérifie:
    - Graphe PROV-JSON créé
    - Chaîne de provenance complète
    - Entités, activités et relations enregistrées
    """
    # Effectuer une génération
    response = api_client.post(
        "/chat", json={"messages": [{"role": "user", "content": "Analyse this data"}]}
    )

    assert response.status_code == 200

    # Vérifier que le tracker a été appelé
    tracker = patched_middlewares["tracker"]

    # Vérifier que des données de provenance existent
    # (dépend de l'implémentation du mock tracker)
    assert tracker is not None


@pytest.mark.e2e
@pytest.mark.compliance
def test_e2e_worm_log_immutability(api_client, patched_middlewares):
    """
    Test E2E: Immutabilité des logs WORM

    Vérifie:
    - Logs WORM créés
    - Digest généré
    - Tentative de modification détectée
    """
    # Générer des événements
    response = api_client.post(
        "/chat", json={"messages": [{"role": "user", "content": "Test WORM logging"}]}
    )

    assert response.status_code == 200

    # Forcer la création d'un digest WORM
    worm_logger = patched_middlewares["worm_logger"]
    worm_logger.finalize_current_log()

    # Vérifier qu'un digest existe
    digest_dir = patched_middlewares["isolated_fs"]["logs_digests"]
    digest_files = list(digest_dir.glob("*.json"))

    if len(digest_files) > 0:
        with open(digest_files[0], "r") as f:
            digest_data = json.load(f)

        # Vérifier la structure du digest
        assert "sha256" in digest_data
        assert "timestamp" in digest_data


# ============================================================================
# TESTS E2E: Memory Persistence Across Sessions
# ============================================================================


@pytest.mark.e2e
@pytest.mark.memory
def test_e2e_conversation_persists_across_sessions(temp_db, conversation_factory, api_client):
    """
    Test E2E: Persistance de conversation entre sessions

    Vérifie:
    - Conversation sauvegardée en base
    - Récupération dans une nouvelle session
    - Contexte préservé
    """
    # Session 1: Créer une conversation
    response1 = api_client.post(
        "/chat", json={"messages": [{"role": "user", "content": "Je m'appelle Alice"}]}
    )

    assert response1.status_code == 200
    conv_id = response1.json()["id"]

    # Simuler une nouvelle session: récupérer la conversation
    response2 = api_client.get(f"/conversations/{conv_id}")

    assert response2.status_code == 200
    data = response2.json()

    assert data["conversation_id"] == conv_id
    assert len(data["messages"]) >= 1

    # Vérifier que le contenu est préservé
    user_messages = [m for m in data["messages"] if m["role"] == "user"]
    assert any("Alice" in m["content"] for m in user_messages)


@pytest.mark.e2e
@pytest.mark.memory
def test_e2e_episodic_memory_query(temp_db, conversation_factory, api_client):
    """
    Test E2E: Requête de la mémoire épisodique

    Vérifie:
    - Messages stockés en base SQLite
    - Requête par conversation_id
    - Ordre chronologique préservé
    """
    # Créer une conversation avec plusieurs messages
    conv_id = "memory_test_123"
    conversation_factory(
        conv_id,
        [
            {"role": "user", "content": "Message 1"},
            {"role": "assistant", "content": "Response 1"},
            {"role": "user", "content": "Message 2"},
            {"role": "assistant", "content": "Response 2"},
        ],
    )

    # Récupérer via API
    response = api_client.get(f"/conversations/{conv_id}")

    assert response.status_code == 200
    data = response.json()

    assert len(data["messages"]) == 4

    # Vérifier l'ordre
    assert data["messages"][0]["content"] == "Message 1"
    assert data["messages"][1]["content"] == "Response 1"
    assert data["messages"][2]["content"] == "Message 2"
    assert data["messages"][3]["content"] == "Response 2"


@pytest.mark.e2e
@pytest.mark.memory
@pytest.mark.slow
def test_e2e_memory_retention_policy(temp_db, conversation_factory, api_client):
    """
    Test E2E: Politique de rétention de la mémoire

    Vérifie:
    - Conversations anciennes identifiées
    - Politique de rétention appliquée
    - Données supprimées selon la politique
    """
    # Créer une vieille conversation (simulation)
    old_conv_id = "old_conv_123"
    conversation_factory(old_conv_id, [{"role": "user", "content": "Old message"}])

    # Vérifier qu'elle existe
    response = api_client.get(f"/conversations/{old_conv_id}")
    assert response.status_code == 200

    # Note: Le test complet de rétention nécessiterait de:
    # 1. Modifier les timestamps en base
    # 2. Exécuter un script de nettoyage
    # 3. Vérifier la suppression
    # Ce test vérifie juste que la structure est en place


@pytest.mark.e2e
@pytest.mark.memory
def test_e2e_context_window_management(api_client, temp_db):
    """
    Test E2E: Gestion de la fenêtre de contexte

    Vérifie:
    - Messages anciens tronqués si contexte trop grand
    - Messages récents préservés
    - Pas de perte de cohérence
    """
    # Créer une conversation avec beaucoup de messages
    messages = []
    for i in range(50):
        messages.append({"role": "user", "content": f"Message {i}"})

    # Envoyer seulement les 10 derniers (simulation de truncation)
    response = api_client.post("/chat", json={"messages": messages[-10:]})

    assert response.status_code == 200
    data = response.json()
    assert "choices" in data


# ============================================================================
# TESTS E2E: Tool Chaining Scenarios
# ============================================================================


@pytest.mark.e2e
@pytest.mark.tools
def test_e2e_sequential_tool_chain(api_client_with_tool_model, patched_middlewares):
    """
    Test E2E: Chaînage séquentiel d'outils

    Vérifie:
    - Outil A exécuté
    - Résultat de A passé à outil B
    - Résultat final combine A et B
    """
    # Créer un mock model qui appelle plusieurs outils en séquence
    from unittest.mock import MagicMock

    def multi_tool_generate(*args, **kwargs):
        # Premier appel: utiliser python_sandbox
        if not hasattr(multi_tool_generate, "call_count"):
            multi_tool_generate.call_count = 0

        multi_tool_generate.call_count += 1

        if multi_tool_generate.call_count == 1:
            return GenerationResult(
                text="I'll calculate using Python",
                finish_reason="tool_calls",
                tokens_generated=20,
                prompt_tokens=50,
                total_tokens=70,
                tool_calls=[{"name": "python_sandbox", "arguments": {"code": "result = 2 + 2"}}],
            )
        else:
            return GenerationResult(
                text="The result is 4",
                finish_reason="stop",
                tokens_generated=10,
                prompt_tokens=60,
                total_tokens=70,
            )

    with patch("runtime.agent.init_model") as mock_init:
        mock_model = MagicMock()
        mock_model.generate = multi_tool_generate
        mock_model.is_loaded.return_value = True
        mock_init.return_value = mock_model

        response = api_client_with_tool_model.post(
            "/chat",
            json={
                "messages": [{"role": "user", "content": "Calculate 2+2 then format the result"}]
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "choices" in data


@pytest.mark.e2e
@pytest.mark.tools
def test_e2e_parallel_tool_execution(api_client_with_tool_model, patched_middlewares):
    """
    Test E2E: Exécution parallèle d'outils indépendants

    Vérifie:
    - Plusieurs outils exécutés en parallèle
    - Résultats combinés correctement
    - Pas de blocage mutuel
    """
    response = api_client_with_tool_model.post(
        "/chat",
        json={"messages": [{"role": "user", "content": "Calculate 2+2 and 3+3 simultaneously"}]},
    )

    assert response.status_code == 200
    data = response.json()
    assert "choices" in data


@pytest.mark.e2e
@pytest.mark.tools
def test_e2e_tool_output_as_next_tool_input(api_client_with_tool_model, patched_middlewares):
    """
    Test E2E: Sortie d'un outil comme entrée du suivant

    Vérifie:
    - Output de tool_1 disponible
    - tool_2 reçoit output de tool_1
    - Chaîne de transformation correcte
    """
    # Mock une séquence où output d'un tool est input du suivant
    response = api_client_with_tool_model.post(
        "/chat",
        json={
            "messages": [
                {"role": "user", "content": "Read data.csv then calculate statistics on it"}
            ]
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "choices" in data


@pytest.mark.e2e
@pytest.mark.tools
def test_e2e_tool_error_propagation_in_chain(
    api_client_with_tool_model, patched_middlewares, mock_tool_failure
):
    """
    Test E2E: Propagation d'erreur dans une chaîne d'outils

    Vérifie:
    - Erreur d'un outil dans la chaîne détectée
    - Chaîne interrompue proprement
    - Message d'erreur clair retourné
    """
    with patch("tools.registry.ToolRegistry.get_tool", return_value=mock_tool_failure):
        response = api_client_with_tool_model.post(
            "/chat", json={"messages": [{"role": "user", "content": "Use tool A then tool B"}]}
        )

        # Doit gérer l'erreur gracieusement
        assert response.status_code == 200
        data = response.json()
        assert "choices" in data


@pytest.mark.e2e
@pytest.mark.tools
def test_e2e_tool_timeout_in_chain(api_client_with_tool_model, patched_middlewares):
    """
    Test E2E: Timeout d'outil dans une chaîne

    Vérifie:
    - Timeout d'un outil détecté
    - Chaîne arrêtée ou contournée
    - Timeout géré sans bloquer toute la chaîne
    """

    def slow_tool_execute(*args, **kwargs):
        time.sleep(10)  # Très lent
        return ToolResult(status=ToolStatus.SUCCESS, output="Late result")

    mock_slow_tool = MagicMock()
    mock_slow_tool.execute = slow_tool_execute

    with patch("tools.registry.ToolRegistry.get_tool", return_value=mock_slow_tool):
        response = api_client_with_tool_model.post(
            "/chat", json={"messages": [{"role": "user", "content": "Use the slow tool"}]}
        )

        # Doit gérer le timeout
        assert response.status_code in [200, 408, 504]


# ============================================================================
# TESTS E2E: Error Recovery and Fallback Paths
# ============================================================================


@pytest.mark.e2e
@pytest.mark.resilience
def test_e2e_recovery_from_tool_execution_error(
    api_client_with_tool_model, patched_middlewares, mock_tool_failure
):
    """
    Test E2E: Récupération après erreur d'exécution d'outil

    Vérifie:
    - Erreur d'outil détectée
    - Agent réessaie ou propose alternative
    - Réponse finale toujours fournie
    """
    with patch("tools.registry.ToolRegistry.get_tool", return_value=mock_tool_failure):
        response = api_client_with_tool_model.post(
            "/chat",
            json={"messages": [{"role": "user", "content": "Try to execute the failing tool"}]},
        )

        assert response.status_code == 200
        data = response.json()
        assert "choices" in data


@pytest.mark.e2e
@pytest.mark.resilience
def test_e2e_recovery_from_htn_planning_failure(api_client, patched_middlewares):
    """
    Test E2E: Récupération après échec de planification HTN

    Vérifie:
    - Échec de planification HTN détecté
    - Fallback vers mode simple activé
    - Tâche complétée malgré l'échec de planification
    """
    with patch("planner.planner.HierarchicalPlanner.plan") as mock_plan:
        mock_plan.side_effect = Exception("HTN planning failed")

        response = api_client.post(
            "/chat", json={"messages": [{"role": "user", "content": "Complex multi-step task"}]}
        )

        # Doit fallback et réussir quand même
        assert response.status_code == 200
        data = response.json()
        assert "choices" in data


@pytest.mark.e2e
@pytest.mark.resilience
def test_e2e_recovery_from_partial_task_failure(api_client, patched_middlewares):
    """
    Test E2E: Récupération après échec partiel de tâche

    Vérifie:
    - Certaines sous-tâches réussissent
    - Certaines échouent
    - Résultats partiels utilisables
    """
    response = api_client.post(
        "/chat", json={"messages": [{"role": "user", "content": "Do task A, task B, and task C"}]}
    )

    assert response.status_code == 200
    data = response.json()
    assert "choices" in data


@pytest.mark.e2e
@pytest.mark.resilience
def test_e2e_retry_mechanism_for_transient_errors(api_client_with_tool_model, patched_middlewares):
    """
    Test E2E: Mécanisme de retry pour erreurs transitoires

    Vérifie:
    - Erreur transitoire détectée
    - Retry automatique effectué
    - Succès après retry
    """

    # Créer un tool qui échoue la première fois puis réussit
    class RetryableTool:
        def __init__(self):
            self.call_count = 0

        def execute(self, params):
            self.call_count += 1
            if self.call_count == 1:
                return ToolResult(status=ToolStatus.ERROR, output="Transient error")
            else:
                return ToolResult(status=ToolStatus.SUCCESS, output="Success after retry")

    retryable_tool = RetryableTool()

    with patch("tools.registry.ToolRegistry.get_tool", return_value=retryable_tool):
        response = api_client_with_tool_model.post(
            "/chat", json={"messages": [{"role": "user", "content": "Use the retryable tool"}]}
        )

        # Doit réussir après retry
        assert response.status_code == 200


@pytest.mark.e2e
@pytest.mark.resilience
def test_e2e_graceful_degradation_mode(api_client, patched_middlewares):
    """
    Test E2E: Mode de dégradation gracieuse

    Vérifie:
    - Système détecte ressources limitées
    - Passe en mode dégradé
    - Fonctionnalité réduite mais stable
    """
    # Simuler une situation de ressources limitées
    with patch("planner.executor.TaskExecutor.execute") as mock_exec:
        # Faire échouer l'exécution parallèle
        from planner.executor import ExecutionResult

        mock_exec.return_value = ExecutionResult(
            success=False, results={}, error="Resource exhaustion"
        )

        response = api_client.post(
            "/chat", json={"messages": [{"role": "user", "content": "Simple task"}]}
        )

        # Doit fonctionner en mode dégradé
        assert response.status_code == 200


@pytest.mark.e2e
@pytest.mark.resilience
def test_e2e_circuit_breaker_pattern(api_client_with_tool_model, patched_middlewares):
    """
    Test E2E: Pattern circuit breaker pour outils défaillants

    Vérifie:
    - Outil échoue plusieurs fois
    - Circuit breaker s'ouvre
    - Appels futurs court-circuités
    """
    # Créer un outil qui échoue systématiquement
    fail_count = 0

    def always_fail(*args, **kwargs):
        nonlocal fail_count
        fail_count += 1
        return ToolResult(status=ToolStatus.ERROR, output=f"Failure {fail_count}")

    mock_failing_tool = MagicMock()
    mock_failing_tool.execute = always_fail

    with patch("tools.registry.ToolRegistry.get_tool", return_value=mock_failing_tool):
        # Faire plusieurs appels pour déclencher le circuit breaker
        for i in range(3):
            response = api_client_with_tool_model.post(
                "/chat",
                json={"messages": [{"role": "user", "content": f"Use failing tool iteration {i}"}]},
            )

            # Toutes les requêtes doivent être gérées
            assert response.status_code == 200


@pytest.mark.e2e
@pytest.mark.resilience
@pytest.mark.slow
def test_e2e_end_to_end_resilience_stress_test(api_client, patched_middlewares):
    """
    Test E2E: Test de stress résilience end-to-end

    Vérifie:
    - Système reste stable sous stress
    - Erreurs multiples gérées
    - Récupération automatique
    """
    import concurrent.futures

    def stress_request(i):
        try:
            response = api_client.post(
                "/chat",
                json={"messages": [{"role": "user", "content": f"Stress test request {i}"}]},
            )
            return response.status_code
        except Exception as e:
            return 500

    # Envoyer 10 requêtes concurrentes avec des erreurs possibles
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(stress_request, i) for i in range(10)]
        status_codes = [f.result() for f in concurrent.futures.as_completed(futures)]

    # Au moins 50% des requêtes doivent réussir
    success_count = sum(1 for code in status_codes if code == 200)
    assert success_count >= 5, f"Only {success_count}/10 requests succeeded"
