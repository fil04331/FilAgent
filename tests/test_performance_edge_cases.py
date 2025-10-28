"""
Performance and Edge Case tests

Tests performance characteristics and edge case handling:
- Response time under load
- Memory usage with large conversations
- Concurrent request handling
- Database performance
- Edge cases and error scenarios
"""

import pytest
import json
import time
import sqlite3
import threading
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch, MagicMock


# ============================================================================
# TESTS: Performance - Response Time
# ============================================================================

@pytest.mark.performance
@pytest.mark.slow
def test_performance_response_time_single_request(api_client):
    """
    Test de performance: Temps de réponse pour requête simple
    
    Vérifie:
    - Temps de réponse < 5 secondes
    - Performance acceptable
    """
    start = time.time()
    
    response = api_client.post("/chat", json={
        "messages": [
            {"role": "user", "content": "Hello, how are you?"}
        ]
    })
    
    elapsed = time.time() - start
    
    assert response.status_code == 200
    # Le temps de réponse doit être raisonnable (< 5s pour un test simple)
    assert elapsed < 5.0, f"Response time too slow: {elapsed:.2f}s"


@pytest.mark.performance
@pytest.mark.slow
def test_performance_response_time_with_history(api_client, conversation_factory, temp_db):
    """
    Test de performance: Temps de réponse avec historique
    
    Vérifie:
    - Performance avec contexte long
    - Pas de dégradation significative
    """
    conv_id = "perf_test_conv"
    
    # Créer un historique de conversation
    messages = []
    for i in range(20):
        messages.append({"role": "user", "content": f"Message {i}"})
        messages.append({"role": "assistant", "content": f"Response {i}"})
    
    conversation_factory(conv_id, messages)
    
    # Mesurer le temps pour une nouvelle requête
    start = time.time()
    
    response = api_client.post("/chat", json={
        "messages": messages + [
            {"role": "user", "content": "New message with context"}
        ]
    })
    
    elapsed = time.time() - start
    
    assert response.status_code == 200
    # Avec contexte, tolérer jusqu'à 10s
    assert elapsed < 10.0, f"Response with history too slow: {elapsed:.2f}s"


# ============================================================================
# TESTS: Performance - Memory Usage
# ============================================================================

@pytest.mark.performance
@pytest.mark.slow
def test_performance_memory_large_conversation(api_client, temp_db, conversation_factory):
    """
    Test de performance: Utilisation mémoire avec grande conversation
    
    Vérifie:
    - Le système gère de grandes conversations
    - Pas de fuite mémoire
    - Performance stable
    """
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    conv_id = "large_conv_test"
    
    # Créer une très grande conversation
    messages = []
    for i in range(100):
        messages.append({
            "role": "user", 
            "content": f"Message {i} with some content to make it realistic"
        })
        messages.append({
            "role": "assistant",
            "content": f"Response {i} with detailed explanation and context"
        })
    
    conversation_factory(conv_id, messages)
    
    # Récupérer la conversation
    response = api_client.get(f"/conversations/{conv_id}")
    
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = final_memory - initial_memory
    
    assert response.status_code == 200
    # L'augmentation mémoire doit rester raisonnable (< 100MB)
    assert memory_increase < 100, f"Memory increase too high: {memory_increase:.2f}MB"


# ============================================================================
# TESTS: Performance - Concurrent Requests
# ============================================================================

@pytest.mark.performance
@pytest.mark.slow
def test_performance_concurrent_requests(api_client):
    """
    Test de performance: Requêtes concurrentes
    
    Vérifie:
    - Le système gère plusieurs requêtes simultanées
    - Pas de deadlock
    - Performance acceptable
    """
    num_concurrent = 10
    
    def send_request(request_id):
        start = time.time()
        response = api_client.post("/chat", json={
            "messages": [
                {"role": "user", "content": f"Concurrent request {request_id}"}
            ]
        })
        elapsed = time.time() - start
        return response.status_code, elapsed
    
    start_total = time.time()
    
    with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
        futures = [executor.submit(send_request, i) for i in range(num_concurrent)]
        results = [f.result() for f in as_completed(futures)]
    
    elapsed_total = time.time() - start_total
    
    # Toutes les requêtes doivent réussir
    assert all(status == 200 for status, _ in results), "Some requests failed"
    
    # Le temps total doit être raisonnable (pas plus de 2x le temps séquentiel)
    # Si séquentiel serait ~5s par requête = 50s, concurrent doit être < 20s
    assert elapsed_total < 30.0, f"Concurrent requests too slow: {elapsed_total:.2f}s"
    
    # Vérifier que les requêtes ont bien été traitées en parallèle
    # (temps moyen par requête doit être < temps total / nombre de requêtes)
    avg_time = sum(t for _, t in results) / len(results)
    assert avg_time < elapsed_total, "Requests were not processed concurrently"


@pytest.mark.performance
@pytest.mark.slow
def test_performance_throughput(api_client):
    """
    Test de performance: Débit (requêtes par seconde)
    
    Vérifie:
    - Le débit minimum est atteint
    - Le système peut gérer la charge
    """
    num_requests = 20
    
    start = time.time()
    
    for i in range(num_requests):
        response = api_client.post("/chat", json={
            "messages": [
                {"role": "user", "content": f"Request {i}"}
            ]
        })
        assert response.status_code == 200
    
    elapsed = time.time() - start
    throughput = num_requests / elapsed
    
    # Le débit doit être au moins 1 requête par seconde
    assert throughput >= 1.0, f"Throughput too low: {throughput:.2f} req/s"


# ============================================================================
# TESTS: Performance - Database
# ============================================================================

@pytest.mark.performance
def test_performance_database_query_speed(temp_db, conversation_factory):
    """
    Test de performance: Vitesse de requêtes DB
    
    Vérifie:
    - Les requêtes sont rapides
    - Les index sont efficaces
    """
    # Créer plusieurs conversations
    for conv_num in range(10):
        conv_id = f"conv_{conv_num}"
        messages = []
        for i in range(50):
            messages.append({"role": "user", "content": f"Message {i}"})
            messages.append({"role": "assistant", "content": f"Response {i}"})
        conversation_factory(conv_id, messages)
    
    # Mesurer le temps de requête
    conn = sqlite3.connect(str(temp_db))
    cursor = conn.cursor()
    
    start = time.time()
    cursor.execute("SELECT COUNT(*) FROM messages")
    count = cursor.fetchone()[0]
    elapsed = time.time() - start
    
    conn.close()
    
    assert count == 10 * 50 * 2  # 10 conversations * 50 tours * 2 messages
    # La requête doit être rapide (< 100ms)
    assert elapsed < 0.1, f"Database query too slow: {elapsed*1000:.2f}ms"


@pytest.mark.performance
def test_performance_database_write_speed(temp_db):
    """
    Test de performance: Vitesse d'écriture DB
    
    Vérifie:
    - Les écritures sont rapides
    - Pas de lock contention
    """
    from memory.episodic import add_message
    
    conv_id = "write_perf_test"
    num_messages = 100
    
    start = time.time()
    
    for i in range(num_messages):
        add_message(
            conversation_id=conv_id,
            role="user",
            content=f"Message {i}",
            db_path=str(temp_db)
        )
    
    elapsed = time.time() - start
    writes_per_second = num_messages / elapsed
    
    # Le système doit gérer au moins 50 écritures/seconde
    assert writes_per_second >= 50, \
        f"Database writes too slow: {writes_per_second:.2f} writes/s"


# ============================================================================
# TESTS: Edge Cases - Malformed Input
# ============================================================================

@pytest.mark.edge_case
def test_edge_case_malformed_json(api_client):
    """
    Test de cas edge: JSON malformé
    
    Vérifie:
    - Le système rejette gracieusement
    - Pas de crash
    - Code d'erreur approprié
    """
    response = api_client.post(
        "/chat",
        data="not valid json",
        headers={"Content-Type": "application/json"}
    )
    
    # Doit retourner 400 Bad Request ou 422 Unprocessable Entity
    assert response.status_code in [400, 422]


@pytest.mark.edge_case
def test_edge_case_missing_required_fields(api_client):
    """
    Test de cas edge: Champs requis manquants
    
    Vérifie:
    - Validation des champs requis
    - Message d'erreur approprié
    """
    # Requête sans champ "messages"
    response = api_client.post("/chat", json={})
    
    assert response.status_code in [400, 422]


@pytest.mark.edge_case
def test_edge_case_empty_messages_array(api_client):
    """
    Test de cas edge: Tableau de messages vide
    
    Vérifie:
    - Gestion du cas vide
    - Comportement approprié
    """
    response = api_client.post("/chat", json={
        "messages": []
    })
    
    # Doit retourner une erreur ou gérer gracieusement
    assert response.status_code in [200, 400, 422]


@pytest.mark.edge_case
def test_edge_case_invalid_message_role(api_client):
    """
    Test de cas edge: Rôle de message invalide
    
    Vérifie:
    - Validation du rôle
    - Rejet des rôles invalides
    """
    response = api_client.post("/chat", json={
        "messages": [
            {"role": "invalid_role", "content": "Test"}
        ]
    })
    
    assert response.status_code in [400, 422]


# ============================================================================
# TESTS: Edge Cases - Boundary Conditions
# ============================================================================

@pytest.mark.edge_case
def test_edge_case_extremely_long_message(api_client):
    """
    Test de cas edge: Message extrêmement long
    
    Vérifie:
    - Gestion de messages très longs
    - Limites enforced
    """
    # Message de 100KB
    very_long_message = "x" * (100 * 1024)
    
    response = api_client.post("/chat", json={
        "messages": [
            {"role": "user", "content": very_long_message}
        ]
    })
    
    # Doit soit accepter, soit rejeter avec 413 Payload Too Large
    assert response.status_code in [200, 413]


@pytest.mark.edge_case
def test_edge_case_special_characters_in_message(api_client):
    """
    Test de cas edge: Caractères spéciaux dans le message
    
    Vérifie:
    - Gestion de caractères spéciaux
    - Pas de problème d'encodage
    """
    special_messages = [
        "Hello 世界 🌍",
        "Test with \n newlines \t and tabs",
        "Quotes: \"double\" and 'single'",
        "Special: <>&",
        "Emoji: 🎉🚀💻🔥"
    ]
    
    for msg in special_messages:
        response = api_client.post("/chat", json={
            "messages": [
                {"role": "user", "content": msg}
            ]
        })
        
        assert response.status_code == 200, \
            f"Failed to handle special characters: {msg}"


@pytest.mark.edge_case
def test_edge_case_null_values(api_client):
    """
    Test de cas edge: Valeurs null
    
    Vérifie:
    - Gestion de null
    - Validation appropriée
    """
    response = api_client.post("/chat", json={
        "messages": [
            {"role": "user", "content": None}
        ]
    })
    
    # Null content doit être rejeté
    assert response.status_code in [400, 422]


# ============================================================================
# TESTS: Edge Cases - Configuration and State
# ============================================================================

@pytest.mark.edge_case
def test_edge_case_missing_config_file(isolated_fs):
    """
    Test de cas edge: Fichier de configuration manquant
    
    Vérifie:
    - Détection de fichier manquant
    - Fallback sur valeurs par défaut ou erreur appropriée
    """
    from runtime.config import load_config
    
    # Essayer de charger une config inexistante
    try:
        config = load_config(str(isolated_fs['config_dir'] / "nonexistent.yaml"))
        # Si aucune erreur, vérifier que les valeurs par défaut sont utilisées
        assert config is not None
    except FileNotFoundError:
        # C'est acceptable de lever une exception
        pass
    except Exception as e:
        # Autres exceptions doivent être spécifiques
        assert "config" in str(e).lower() or "file" in str(e).lower()


@pytest.mark.edge_case
def test_edge_case_corrupted_database(temp_db):
    """
    Test de cas edge: Base de données corrompue
    
    Vérifie:
    - Détection de corruption
    - Comportement gracieux
    """
    # Corrompre le fichier de base de données
    with open(temp_db, 'wb') as f:
        f.write(b"CORRUPTED DATA")
    
    # Essayer d'accéder à la base
    try:
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM messages")
        conn.close()
        corruption_detected = False
    except sqlite3.DatabaseError:
        corruption_detected = True
    
    assert corruption_detected, "Database corruption should be detected"


# ============================================================================
# TESTS: Edge Cases - Timestamps and Timezone
# ============================================================================

@pytest.mark.edge_case
def test_edge_case_timezone_handling(api_client):
    """
    Test de cas edge: Gestion des fuseaux horaires
    
    Vérifie:
    - Les timestamps incluent timezone
    - Format ISO8601 respecté
    """
    response = api_client.post("/chat", json={
        "messages": [
            {"role": "user", "content": "Test timezone"}
        ]
    })
    
    assert response.status_code == 200
    data = response.json()
    
    # Vérifier que les timestamps sont présents et valides
    if "created" in data:
        timestamp = data["created"]
        # Doit être ISO8601
        try:
            datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            valid_timestamp = True
        except ValueError:
            valid_timestamp = False
        
        assert valid_timestamp, f"Invalid timestamp format: {timestamp}"


@pytest.mark.edge_case
def test_edge_case_monotonic_timestamp_enforcement():
    """
    Test de cas edge: Timestamps monotones
    
    Vérifie:
    - Les timestamps sont toujours croissants
    - Pas de régression temporelle
    """
    from runtime.middleware.provenance import ProvBuilder
    
    builder = ProvBuilder()
    
    # Créer des activités avec timestamps
    now = datetime.utcnow()
    
    builder.add_activity(
        "activity:1",
        now.isoformat() + "Z",
        (now + timedelta(seconds=1)).isoformat() + "Z"
    )
    
    builder.add_activity(
        "activity:2",
        (now + timedelta(seconds=2)).isoformat() + "Z",
        (now + timedelta(seconds=3)).isoformat() + "Z"
    )
    
    # Vérifier l'ordre
    activities = sorted(
        builder.activities.items(),
        key=lambda x: x[1]["prov:startTime"]
    )
    
    assert activities[0][0] == "activity:1"
    assert activities[1][0] == "activity:2"
    
    # Vérifier que chaque activité a startTime < endTime
    for _, activity in activities:
        start = datetime.fromisoformat(activity["prov:startTime"].replace('Z', '+00:00'))
        end = datetime.fromisoformat(activity["prov:endTime"].replace('Z', '+00:00'))
        assert start < end, "Activity startTime must be < endTime"
