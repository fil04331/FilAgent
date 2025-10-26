"""
Tests pour la mémoire épisodique
"""
import pytest
import os
import tempfile
from pathlib import Path
import sys

# Ajouter le parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from memory.episodic import create_tables, add_message, get_messages, cleanup_old_conversations


@pytest.fixture
def temp_db():
    """Créer une base de données temporaire pour les tests"""
    # Sauvegarder le chemin original
    original_path = Path("memory/episodic.sqlite")
    
    # Créer un fichier temporaire
    tmpdir = tempfile.mkdtemp()
    tmp_db = Path(tmpdir) / "test_episodic.sqlite"
    
    # Modifier temporairement le chemin
    import memory.episodic
    original_db_path = memory.episodic.DB_PATH
    memory.episodic.DB_PATH = tmp_db
    
    # Créer les tables
    create_tables()
    
    yield tmp_db
    
    # Restaurer
    memory.episodic.DB_PATH = original_db_path
    if tmp_db.exists():
        tmp_db.unlink()


def test_create_tables(temp_db):
    """Test que les tables sont créées"""
    # Cette fonction est exécutée dans le fixture
    assert temp_db.exists()


def test_add_and_get_message(temp_db):
    """Test ajout et récupération de messages"""
    conv_id = "test-conv-1"
    
    # Ajouter un message
    add_message(
        conversation_id=conv_id,
        role="user",
        content="Bonjour"
    )
    
    # Récupérer les messages
    messages = get_messages(conv_id)
    
    assert len(messages) == 1
    assert messages[0]['role'] == "user"
    assert messages[0]['content'] == "Bonjour"


def test_multiple_messages(temp_db):
    """Test avec plusieurs messages"""
    conv_id = "test-conv-2"
    
    # Ajouter plusieurs messages
    add_message(conv_id, "user", "Message 1")
    add_message(conv_id, "assistant", "Réponse 1")
    add_message(conv_id, "user", "Message 2")
    
    messages = get_messages(conv_id)
    
    assert len(messages) == 3
    assert messages[0]['content'] == "Message 1"
    assert messages[1]['content'] == "Réponse 1"
    assert messages[2]['content'] == "Message 2"


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
    assert messages1[0]['content'] == "Message pour conv1"
    assert messages2[0]['content'] == "Message pour conv2"


@pytest.mark.skip(reason="Requiert une implémentation plus avancée du TTL")
def test_cleanup_old_conversations(temp_db):
    """Test du nettoyage des vieilles conversations"""
    # À implémenter avec un mock de timestamp
    pass
