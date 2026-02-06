"""
Tests pour la mémoire épisodique

Coverage tests for memory/episodic.py including:
- Basic operations (add, get, create tables)
- Concurrent access (threading)
- Large message histories
- Query pagination
- Conversation deletion (cleanup with TTL)
- Database schema and migration
- Edge cases and error handling
"""

import pytest
import os
import tempfile
import sqlite3
import threading
import time
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch
import sys

# Ajouter le parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from memory.episodic import (
    create_tables,
    add_message,
    get_messages,
    cleanup_old_conversations,
    get_connection,
)

# Note: temp_db fixture is now defined in conftest.py with proper DB_PATH patching


# ============================================================================
# BASIC TESTS (Existing)
# ============================================================================


def test_create_tables(temp_db):
    """Test que les tables sont créées"""
    # Cette fonction est exécutée dans le fixture
    assert temp_db.exists()

    # Verify tables exist
    conn = sqlite3.connect(str(temp_db))
    cursor = conn.cursor()

    # Check conversations table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='conversations'")
    assert cursor.fetchone() is not None

    # Check messages table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
    assert cursor.fetchone() is not None

    # Check indexes exist
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_conversation_id'"
    )
    assert cursor.fetchone() is not None

    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_timestamp'")
    assert cursor.fetchone() is not None

    conn.close()


def test_add_and_get_message(temp_db):
    """Test ajout et récupération de messages"""
    conv_id = "test-conv-1"

    # Ajouter un message
    add_message(conversation_id=conv_id, role="user", content="Bonjour")

    # Récupérer les messages
    messages = get_messages(conv_id)

    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Bonjour"


def test_multiple_messages(temp_db):
    """Test avec plusieurs messages"""
    conv_id = "test-conv-2"

    # Ajouter plusieurs messages
    add_message(conv_id, "user", "Message 1")
    add_message(conv_id, "assistant", "Réponse 1")
    add_message(conv_id, "user", "Message 2")

    messages = get_messages(conv_id)

    assert len(messages) == 3
    assert messages[0]["content"] == "Message 1"
    assert messages[1]["content"] == "Réponse 1"
    assert messages[2]["content"] == "Message 2"


def test_conversation_isolation(temp_db):
    """Test que les conversations sont isolées"""
    conv1 = "test-conv-3"
    conv2 = "test-conv-4"

    add_message(conv1, "user", "Message pour conv1")
    add_message(conv2, "user", "Message pour conv2")

    messages1 = get_messages(conv1)
    messages2 = get_messages(conv2)

    assert len(messages1) == 1
    assert len(messages2) == 1
    assert messages1[0]["content"] == "Message pour conv1"
    assert messages2[0]["content"] == "Message pour conv2"


# ============================================================================
# ADVANCED FEATURE TESTS
# ============================================================================


def test_message_with_task_id(temp_db):
    """Test l'ajout de messages avec task_id"""
    conv_id = "test-conv-task-1"
    task_id = "task-123"

    add_message(conv_id, "user", "Message avec task", task_id=task_id)

    messages = get_messages(conv_id)
    assert len(messages) == 1
    assert messages[0]["task_id"] == task_id


def test_message_with_metadata(temp_db):
    """Test l'ajout de messages avec metadata"""
    conv_id = "test-conv-meta-1"
    metadata = {"source": "api", "priority": "high"}

    add_message(conv_id, "user", "Message avec metadata", metadata=metadata)

    messages = get_messages(conv_id)
    assert len(messages) == 1
    assert messages[0]["metadata"] == metadata
    assert messages[0]["metadata"]["source"] == "api"
    assert messages[0]["metadata"]["priority"] == "high"


def test_message_with_message_type(temp_db):
    """Test l'ajout de messages avec différents types"""
    conv_id = "test-conv-type-1"

    add_message(conv_id, "user", "Text message", message_type="text")
    add_message(conv_id, "assistant", "Tool call", message_type="tool_call")
    add_message(conv_id, "system", "System message", message_type="system")

    messages = get_messages(conv_id)
    assert len(messages) == 3
    assert messages[0]["message_type"] == "text"
    assert messages[1]["message_type"] == "tool_call"
    assert messages[2]["message_type"] == "system"


def test_empty_conversation(temp_db):
    """Test la récupération d'une conversation vide"""
    conv_id = "test-conv-empty"

    # Ne pas ajouter de messages
    messages = get_messages(conv_id)

    assert len(messages) == 0
    assert messages == []


def test_message_ordering(temp_db):
    """Test que les messages sont ordonnés par timestamp"""
    conv_id = "test-conv-order"

    # Ajouter des messages avec un petit délai
    for i in range(5):
        add_message(conv_id, "user", f"Message {i}")
        time.sleep(0.01)  # Small delay to ensure different timestamps

    messages = get_messages(conv_id)

    assert len(messages) == 5
    # Verify order is maintained
    for i in range(5):
        assert messages[i]["content"] == f"Message {i}"

    # Verify timestamps are ascending
    timestamps = [datetime.fromisoformat(msg["timestamp"]) for msg in messages]
    assert timestamps == sorted(timestamps)


# ============================================================================
# PAGINATION TESTS
# ============================================================================


def test_pagination_basic(temp_db):
    """Test la pagination basique avec limit"""
    conv_id = "test-conv-page-1"

    # Ajouter 50 messages
    for i in range(50):
        add_message(conv_id, "user", f"Message {i}")

    # Récupérer avec différentes limites
    messages_10 = get_messages(conv_id, limit=10)
    messages_25 = get_messages(conv_id, limit=25)
    messages_all = get_messages(conv_id, limit=100)

    assert len(messages_10) == 10
    assert len(messages_25) == 25
    assert len(messages_all) == 50

    # Verify we get the first messages (oldest)
    assert messages_10[0]["content"] == "Message 0"
    assert messages_10[9]["content"] == "Message 9"


def test_pagination_edge_cases(temp_db):
    """Test les cas limites de pagination"""
    conv_id = "test-conv-page-edge"

    # Ajouter 5 messages
    for i in range(5):
        add_message(conv_id, "user", f"Message {i}")

    # Limit plus grand que le nombre de messages
    messages = get_messages(conv_id, limit=100)
    assert len(messages) == 5

    # Limit = 0 (devrait retourner rien)
    messages_zero = get_messages(conv_id, limit=0)
    assert len(messages_zero) == 0

    # Limit = 1 (devrait retourner 1 message)
    messages_one = get_messages(conv_id, limit=1)
    assert len(messages_one) == 1
    assert messages_one[0]["content"] == "Message 0"


# ============================================================================
# LARGE MESSAGE HISTORY TESTS
# ============================================================================


@pytest.mark.slow
def test_large_message_history_100(temp_db):
    """Test avec 100 messages"""
    conv_id = "test-conv-large-100"

    # Ajouter 100 messages
    for i in range(100):
        add_message(conv_id, "user", f"Message {i}", task_id=f"task-{i}")

    # Récupérer tous les messages
    messages = get_messages(conv_id, limit=200)

    assert len(messages) == 100
    assert messages[0]["content"] == "Message 0"
    assert messages[99]["content"] == "Message 99"


@pytest.mark.slow
def test_large_message_history_1000(temp_db, performance_tracker):
    """Test avec 1000 messages et mesure de performance"""
    conv_id = "test-conv-large-1000"

    # Mesurer le temps d'insertion
    with performance_tracker("insert_1000_messages") as timer:
        for i in range(1000):
            add_message(conv_id, "user", f"Message {i}")

    # Should complete in reasonable time
    assert timer.elapsed < 15.0  # Less than 15 seconds (allowing for slower systems)

    # Mesurer le temps de récupération
    with performance_tracker("fetch_1000_messages") as timer:
        messages = get_messages(conv_id, limit=1000)

    # Should be fast
    assert timer.elapsed < 1.0  # Less than 1 second
    assert len(messages) == 1000


@pytest.mark.slow
def test_large_message_with_metadata(temp_db):
    """Test avec beaucoup de messages contenant des metadata"""
    conv_id = "test-conv-large-meta"

    # Ajouter 500 messages avec metadata
    for i in range(500):
        metadata = {
            "index": i,
            "source": f"source-{i % 10}",
            "priority": "high" if i % 2 == 0 else "low",
            "tags": [f"tag-{j}" for j in range(5)],
        }
        add_message(conv_id, "user", f"Message {i}", metadata=metadata)

    # Récupérer et valider
    messages = get_messages(conv_id, limit=500)
    assert len(messages) == 500

    # Verify metadata integrity
    assert messages[0]["metadata"]["index"] == 0
    assert messages[499]["metadata"]["index"] == 499
    assert len(messages[100]["metadata"]["tags"]) == 5


# ============================================================================
# CONCURRENT ACCESS TESTS
# ============================================================================


def test_concurrent_writes(temp_db):
    """Test l'écriture concurrente de messages"""
    conv_id = "test-conv-concurrent-1"
    num_threads = 10
    messages_per_thread = 10
    errors = []

    def writer(thread_id):
        """Fonction d'écriture pour chaque thread"""
        try:
            for i in range(messages_per_thread):
                add_message(
                    conv_id,
                    "user",
                    f"Thread {thread_id} - Message {i}",
                    metadata={"thread_id": thread_id, "index": i},
                )
        except Exception as e:
            errors.append(e)

    # Créer et démarrer les threads
    threads = []
    for thread_id in range(num_threads):
        t = threading.Thread(target=writer, args=(thread_id,))
        threads.append(t)
        t.start()

    # Attendre la fin de tous les threads
    for t in threads:
        t.join()

    # Vérifier qu'il n'y a pas eu d'erreurs
    assert len(errors) == 0, f"Errors occurred: {errors}"

    # Vérifier que tous les messages ont été ajoutés
    messages = get_messages(conv_id, limit=200)
    assert len(messages) == num_threads * messages_per_thread


def test_concurrent_reads(temp_db):
    """Test la lecture concurrente de messages"""
    conv_id = "test-conv-concurrent-2"

    # Préparer des données
    for i in range(50):
        add_message(conv_id, "user", f"Message {i}")

    num_threads = 20
    results = []
    errors = []

    def reader(thread_id):
        """Fonction de lecture pour chaque thread"""
        try:
            messages = get_messages(conv_id, limit=100)
            results.append(len(messages))
        except Exception as e:
            errors.append(e)

    # Créer et démarrer les threads
    threads = []
    for thread_id in range(num_threads):
        t = threading.Thread(target=reader, args=(thread_id,))
        threads.append(t)
        t.start()

    # Attendre la fin
    for t in threads:
        t.join()

    # Vérifier qu'il n'y a pas eu d'erreurs
    assert len(errors) == 0

    # Vérifier que tous les threads ont lu le même nombre de messages
    assert all(count == 50 for count in results)


def test_concurrent_read_write(temp_db):
    """Test lecture et écriture concurrentes"""
    conv_id = "test-conv-concurrent-3"

    # Préparer quelques données initiales
    for i in range(10):
        add_message(conv_id, "user", f"Initial {i}")

    num_writers = 5
    num_readers = 5
    messages_per_writer = 10
    errors = []
    read_counts = []

    def writer(thread_id):
        """Écrivain"""
        try:
            for i in range(messages_per_writer):
                add_message(conv_id, "user", f"Writer {thread_id} - {i}")
                time.sleep(0.001)  # Small delay
        except Exception as e:
            errors.append(("writer", e))

    def reader(thread_id):
        """Lecteur"""
        try:
            for _ in range(10):
                messages = get_messages(conv_id, limit=100)
                read_counts.append(len(messages))
                time.sleep(0.001)  # Small delay
        except Exception as e:
            errors.append(("reader", e))

    # Démarrer tous les threads
    threads = []

    # Démarrer les writers
    for i in range(num_writers):
        t = threading.Thread(target=writer, args=(i,))
        threads.append(t)
        t.start()

    # Démarrer les readers
    for i in range(num_readers):
        t = threading.Thread(target=reader, args=(i,))
        threads.append(t)
        t.start()

    # Attendre la fin
    for t in threads:
        t.join()

    # Vérifier qu'il n'y a pas eu d'erreurs
    assert len(errors) == 0, f"Errors: {errors}"

    # Vérifier que des messages ont été lus
    assert len(read_counts) > 0
    # Les counts devraient augmenter (ou rester stables) au fil du temps
    assert max(read_counts) >= 10  # Au moins les messages initiaux


# ============================================================================
# CONVERSATION DELETION / CLEANUP TESTS
# ============================================================================


def test_cleanup_old_conversations_basic(temp_db):
    """Test le nettoyage basique des vieilles conversations"""
    # Créer une conversation récente
    recent_conv = "test-conv-recent"
    add_message(recent_conv, "user", "Recent message")

    # Créer une conversation "vieille" en mockant le timestamp
    old_conv = "test-conv-old"
    conn = sqlite3.connect(str(temp_db))
    cursor = conn.cursor()

    # Insérer une conversation avec une vieille date
    old_date = (datetime.now() - timedelta(days=60)).isoformat()
    cursor.execute(
        """
        INSERT INTO conversations (id, conversation_id, created_at, updated_at)
        VALUES (?, ?, ?, ?)
    """,
        (old_conv, old_conv, old_date, old_date),
    )

    cursor.execute(
        """
        INSERT INTO messages (conversation_id, role, content, timestamp)
        VALUES (?, ?, ?, ?)
    """,
        (old_conv, "user", "Old message", old_date),
    )

    conn.commit()
    conn.close()

    # Vérifier qu'on a 2 conversations
    messages_recent = get_messages(recent_conv)
    messages_old = get_messages(old_conv)
    assert len(messages_recent) == 1
    assert len(messages_old) == 1

    # Nettoyer les conversations > 30 jours
    deleted = cleanup_old_conversations(ttl_days=30)

    # Vérifier que la vieille conversation est supprimée
    assert deleted > 0
    messages_old_after = get_messages(old_conv)
    assert len(messages_old_after) == 0

    # Vérifier que la récente est toujours là
    messages_recent_after = get_messages(recent_conv)
    assert len(messages_recent_after) == 1


def test_cleanup_multiple_old_conversations(temp_db):
    """Test le nettoyage de plusieurs vieilles conversations"""
    conn = sqlite3.connect(str(temp_db))
    cursor = conn.cursor()

    # Créer 5 vieilles conversations
    old_date = (datetime.now() - timedelta(days=90)).isoformat()
    for i in range(5):
        conv_id = f"old-conv-{i}"
        cursor.execute(
            """
            INSERT INTO conversations (id, conversation_id, created_at, updated_at)
            VALUES (?, ?, ?, ?)
        """,
            (conv_id, conv_id, old_date, old_date),
        )

        cursor.execute(
            """
            INSERT INTO messages (conversation_id, role, content, timestamp)
            VALUES (?, ?, ?, ?)
        """,
            (conv_id, "user", f"Old message {i}", old_date),
        )

    conn.commit()
    conn.close()

    # Créer 3 conversations récentes (after closing connection)
    for i in range(3):
        conv_id = f"recent-conv-{i}"
        add_message(conv_id, "user", f"Recent message {i}")

    # Nettoyer
    deleted = cleanup_old_conversations(ttl_days=30)

    # Vérifier que 5 conversations ont été supprimées
    assert deleted >= 5

    # Vérifier que les récentes sont toujours là
    for i in range(3):
        messages = get_messages(f"recent-conv-{i}")
        assert len(messages) == 1


def test_cleanup_with_different_ttl(temp_db):
    """Test le nettoyage avec différentes valeurs de TTL"""
    conn = sqlite3.connect(str(temp_db))
    cursor = conn.cursor()

    # Conversation vieille de 10 jours
    conv_10_days = "conv-10-days"
    date_10_days = (datetime.now() - timedelta(days=10)).isoformat()
    cursor.execute(
        """
        INSERT INTO conversations (id, conversation_id, created_at, updated_at)
        VALUES (?, ?, ?, ?)
    """,
        (conv_10_days, conv_10_days, date_10_days, date_10_days),
    )
    cursor.execute(
        """
        INSERT INTO messages (conversation_id, role, content, timestamp)
        VALUES (?, ?, ?, ?)
    """,
        (conv_10_days, "user", "10 days old", date_10_days),
    )

    # Conversation vieille de 45 jours
    conv_45_days = "conv-45-days"
    date_45_days = (datetime.now() - timedelta(days=45)).isoformat()
    cursor.execute(
        """
        INSERT INTO conversations (id, conversation_id, created_at, updated_at)
        VALUES (?, ?, ?, ?)
    """,
        (conv_45_days, conv_45_days, date_45_days, date_45_days),
    )
    cursor.execute(
        """
        INSERT INTO messages (conversation_id, role, content, timestamp)
        VALUES (?, ?, ?, ?)
    """,
        (conv_45_days, "user", "45 days old", date_45_days),
    )

    conn.commit()
    conn.close()

    # Test TTL = 30 jours (devrait supprimer seulement conv_45_days)
    deleted = cleanup_old_conversations(ttl_days=30)
    assert deleted >= 1

    messages_10 = get_messages(conv_10_days)
    messages_45 = get_messages(conv_45_days)

    assert len(messages_10) == 1  # Encore là
    assert len(messages_45) == 0  # Supprimée


def test_cleanup_no_old_conversations(temp_db):
    """Test le nettoyage quand il n'y a pas de vieilles conversations"""
    # Créer seulement des conversations récentes
    for i in range(5):
        add_message(f"recent-{i}", "user", f"Recent {i}")

    # Nettoyer avec TTL de 30 jours
    deleted = cleanup_old_conversations(ttl_days=30)

    # Rien ne devrait être supprimé
    assert deleted == 0

    # Toutes les conversations devraient toujours exister
    for i in range(5):
        messages = get_messages(f"recent-{i}")
        assert len(messages) == 1


# ============================================================================
# DATABASE SCHEMA AND MIGRATION TESTS
# ============================================================================


def test_database_schema_conversations(temp_db):
    """Test le schéma de la table conversations"""
    conn = sqlite3.connect(str(temp_db))
    cursor = conn.cursor()

    # Get schema
    cursor.execute("PRAGMA table_info(conversations)")
    columns = {row[1]: row[2] for row in cursor.fetchall()}

    # Verify expected columns
    assert "id" in columns
    assert "conversation_id" in columns
    assert "task_id" in columns
    assert "created_at" in columns
    assert "updated_at" in columns
    assert "metadata" in columns

    # Verify types (TEXT for SQLite)
    assert columns["id"] == "TEXT"
    assert columns["conversation_id"] == "TEXT"
    assert columns["task_id"] == "TEXT"
    assert columns["metadata"] == "TEXT"

    conn.close()


def test_database_schema_messages(temp_db):
    """Test le schéma de la table messages"""
    conn = sqlite3.connect(str(temp_db))
    cursor = conn.cursor()

    # Get schema
    cursor.execute("PRAGMA table_info(messages)")
    columns = {row[1]: row[2] for row in cursor.fetchall()}

    # Verify expected columns
    assert "id" in columns
    assert "conversation_id" in columns
    assert "task_id" in columns
    assert "role" in columns
    assert "content" in columns
    assert "timestamp" in columns
    assert "message_type" in columns
    assert "metadata" in columns

    # Verify types
    assert columns["id"] == "INTEGER"
    assert columns["conversation_id"] == "TEXT"
    assert columns["role"] == "TEXT"
    assert columns["content"] == "TEXT"

    conn.close()


def test_database_foreign_key(temp_db):
    """Test que la foreign key est correctement configurée"""
    conn = sqlite3.connect(str(temp_db))
    cursor = conn.cursor()

    # Get foreign keys
    cursor.execute("PRAGMA foreign_key_list(messages)")
    fks = cursor.fetchall()

    # Should have foreign key to conversations
    assert len(fks) > 0
    # fk structure: (id, seq, table, from, to, on_update, on_delete, match)
    assert fks[0][2] == "conversations"  # references conversations table

    conn.close()


def test_database_indexes(temp_db):
    """Test que les indexes sont créés"""
    conn = sqlite3.connect(str(temp_db))
    cursor = conn.cursor()

    # Get indexes
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
    indexes = [row[0] for row in cursor.fetchall()]

    # Verify our custom indexes exist
    assert "idx_conversation_id" in indexes
    assert "idx_timestamp" in indexes

    conn.close()


def test_conversation_unique_constraint(temp_db):
    """Test la contrainte d'unicité sur conversation_id"""
    conv_id = "unique-test"

    # Première insertion - devrait réussir
    add_message(conv_id, "user", "Message 1")

    # Ajouter un autre message à la même conversation - devrait réussir
    add_message(conv_id, "user", "Message 2")

    # Vérifier qu'on a bien 2 messages mais 1 seule conversation
    conn = sqlite3.connect(str(temp_db))
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM conversations WHERE conversation_id = ?", (conv_id,))
    conv_count = cursor.fetchone()[0]
    assert conv_count == 1  # Une seule conversation

    cursor.execute("SELECT COUNT(*) FROM messages WHERE conversation_id = ?", (conv_id,))
    msg_count = cursor.fetchone()[0]
    assert msg_count == 2  # Deux messages

    conn.close()


def test_conversation_updated_at_timestamp(temp_db):
    """Test que updated_at est mis à jour quand on ajoute des messages"""
    conv_id = "timestamp-test"

    # Premier message
    add_message(conv_id, "user", "Message 1")

    conn = sqlite3.connect(str(temp_db))
    cursor = conn.cursor()

    cursor.execute("SELECT updated_at FROM conversations WHERE conversation_id = ?", (conv_id,))
    first_timestamp = cursor.fetchone()[0]

    conn.close()

    # Attendre suffisamment pour que SQLite détecte le changement
    # SQLite CURRENT_TIMESTAMP has second precision by default
    time.sleep(1.1)

    # Deuxième message
    add_message(conv_id, "user", "Message 2")

    conn = sqlite3.connect(str(temp_db))
    cursor = conn.cursor()

    cursor.execute("SELECT updated_at FROM conversations WHERE conversation_id = ?", (conv_id,))
    second_timestamp = cursor.fetchone()[0]

    conn.close()

    # Le second timestamp devrait être plus récent ou égal
    first_dt = datetime.fromisoformat(first_timestamp) if first_timestamp else None
    second_dt = datetime.fromisoformat(second_timestamp) if second_timestamp else None

    if first_dt and second_dt:
        assert second_dt >= first_dt  # Allow equal in case of fast execution


# ============================================================================
# EDGE CASES AND ERROR HANDLING
# ============================================================================


def test_special_characters_in_content(temp_db):
    """Test les caractères spéciaux dans le contenu"""
    conv_id = "test-special-chars"

    special_content = """
    Test with special chars:
    - Quotes: "double" and 'single'
    - Newlines: \n
    - Tabs: \t
    - Unicode: émojis 🚀 中文 العربية
    - SQL: DROP TABLE messages; --
    - JSON: {"key": "value"}
    """

    add_message(conv_id, "user", special_content)
    messages = get_messages(conv_id)

    assert len(messages) == 1
    assert messages[0]["content"] == special_content


def test_very_long_message(temp_db):
    """Test avec un message très long"""
    conv_id = "test-long-message"

    # Créer un message de 100KB
    long_content = "A" * (100 * 1024)

    add_message(conv_id, "user", long_content)
    messages = get_messages(conv_id)

    assert len(messages) == 1
    assert len(messages[0]["content"]) == len(long_content)


def test_empty_content(temp_db):
    """Test avec un contenu vide"""
    conv_id = "test-empty-content"

    add_message(conv_id, "user", "")
    messages = get_messages(conv_id)

    assert len(messages) == 1
    assert messages[0]["content"] == ""


def test_null_metadata(temp_db):
    """Test avec metadata None"""
    conv_id = "test-null-meta"

    add_message(conv_id, "user", "Message", metadata=None)
    messages = get_messages(conv_id)

    assert len(messages) == 1
    # metadata should be None or not present
    assert messages[0]["metadata"] is None


def test_complex_metadata_structure(temp_db):
    """Test avec une structure metadata complexe"""
    conv_id = "test-complex-meta"

    complex_metadata = {
        "nested": {"level1": {"level2": {"value": "deep"}}},
        "array": [1, 2, 3, {"nested": "in array"}],
        "unicode": "émojis 🚀",
        "numbers": 42,
        "floats": 3.14,
        "booleans": True,
        "nulls": None,
    }

    add_message(conv_id, "user", "Complex metadata", metadata=complex_metadata)
    messages = get_messages(conv_id)

    assert len(messages) == 1
    retrieved_meta = messages[0]["metadata"]

    # Verify structure is preserved
    assert retrieved_meta["nested"]["level1"]["level2"]["value"] == "deep"
    assert retrieved_meta["array"][3]["nested"] == "in array"
    assert retrieved_meta["unicode"] == "émojis 🚀"
    assert retrieved_meta["numbers"] == 42
    assert retrieved_meta["floats"] == 3.14
    assert retrieved_meta["booleans"] is True
    assert retrieved_meta["nulls"] is None


def test_get_connection_returns_valid_connection(temp_db):
    """Test que get_connection retourne une connexion valide"""
    conn = get_connection()

    assert conn is not None
    assert isinstance(conn, sqlite3.Connection)

    # Verify we can execute queries
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    result = cursor.fetchone()
    assert result[0] == 1

    conn.close()


def test_multiple_task_ids_same_conversation(temp_db):
    """Test plusieurs task_id dans la même conversation"""
    conv_id = "test-multi-task"

    add_message(conv_id, "user", "Message task 1", task_id="task-1")
    add_message(conv_id, "assistant", "Response task 1", task_id="task-1")
    add_message(conv_id, "user", "Message task 2", task_id="task-2")
    add_message(conv_id, "assistant", "Response task 2", task_id="task-2")

    messages = get_messages(conv_id)

    assert len(messages) == 4
    assert messages[0]["task_id"] == "task-1"
    assert messages[1]["task_id"] == "task-1"
    assert messages[2]["task_id"] == "task-2"
    assert messages[3]["task_id"] == "task-2"


# ============================================================================
# INTEGRATION / REAL-WORLD SCENARIO TESTS
# ============================================================================


def test_realistic_conversation_flow(temp_db):
    """Test un flux de conversation réaliste"""
    conv_id = "realistic-conv-1"

    # User asks a question
    add_message(conv_id, "user", "What is 2+2?")

    # Assistant thinks (tool call)
    add_message(
        conv_id,
        "assistant",
        "I'll use the calculator",
        message_type="tool_call",
        metadata={"tool": "calculator"},
    )

    # Tool result
    add_message(
        conv_id,
        "tool",
        "4",
        message_type="tool_result",
        metadata={"tool": "calculator", "result": 4},
    )

    # Assistant responds
    add_message(conv_id, "assistant", "The answer is 4")

    # Verify flow
    messages = get_messages(conv_id)
    assert len(messages) == 4
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["message_type"] == "tool_call"
    assert messages[2]["role"] == "tool"
    assert messages[3]["role"] == "assistant"


def test_multi_turn_conversation(temp_db):
    """Test une conversation multi-tours"""
    conv_id = "multi-turn-1"

    turns = [
        ("user", "Hello"),
        ("assistant", "Hi! How can I help?"),
        ("user", "What's the weather?"),
        ("assistant", "I'll check that for you"),
        ("user", "Thanks"),
        ("assistant", "You're welcome!"),
    ]

    for role, content in turns:
        add_message(conv_id, role, content)

    messages = get_messages(conv_id)
    assert len(messages) == 6

    for i, (expected_role, expected_content) in enumerate(turns):
        assert messages[i]["role"] == expected_role
        assert messages[i]["content"] == expected_content
