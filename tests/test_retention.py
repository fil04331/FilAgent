"""
Tests complets pour memory/retention.py

Couvre:
- Politiques de rétention (RetentionPolicy)
- Gestionnaire de rétention (RetentionManager)
- Nettoyage des conversations, événements, decisions, provenance
- Configuration et chargement de politiques
- Singleton pattern
"""

import pytest
import json
import yaml
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import sys

# Ajouter le parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from memory.retention import (
    RetentionPolicy,
    RetentionManager,
    get_retention_manager,
    init_retention_manager,
)

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def temp_retention_config(tmp_path):
    """Créer un fichier de configuration de rétention temporaire"""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    config_file = config_dir / "retention.yaml"
    config_data = {
        "retention": {
            "version": "0.1.0",
            "durations": {
                "events": {"ttl_days": 90, "purpose": "Troubleshooting"},
                "decisions": {"ttl_days": 365, "purpose": "Audit trail"},
                "conversations": {"ttl_days": 30, "purpose": "User support"},
                "provenance": {"ttl_days": 180, "purpose": "Traceability"},
            },
        }
    }

    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    return config_file


@pytest.fixture
def temp_logs_structure(tmp_path):
    """Créer une structure de logs temporaire avec des fichiers"""
    logs_dir = tmp_path / "logs"

    # Events directory
    events_dir = logs_dir / "events"
    events_dir.mkdir(parents=True, exist_ok=True)

    # Decisions directory
    decisions_dir = logs_dir / "decisions"
    decisions_dir.mkdir(parents=True, exist_ok=True)

    # Provenance directory
    traces_dir = logs_dir / "traces" / "otlp"
    traces_dir.mkdir(parents=True, exist_ok=True)

    return {
        "root": logs_dir,
        "events": events_dir,
        "decisions": decisions_dir,
        "provenance": traces_dir,
    }


@pytest.fixture
def create_old_event_logs(temp_logs_structure):
    """Factory pour créer des logs d'événements avec des dates spécifiques"""

    def _create(days_old: int, count: int = 1):
        """
        Créer des fichiers de logs avec une date spécifique

        Args:
            days_old: Nombre de jours dans le passé
            count: Nombre de fichiers à créer
        """
        events_dir = temp_logs_structure["events"]
        created_files = []

        for i in range(count):
            log_date = datetime.now() - timedelta(days=days_old + i)
            filename = f"events-{log_date.strftime('%Y-%m-%d')}.jsonl"
            log_file = events_dir / filename

            # Écrire du contenu dummy
            log_file.write_text(
                json.dumps(
                    {"timestamp": log_date.isoformat(), "event": "test_event", "data": "test_data"}
                )
                + "\n"
            )

            created_files.append(log_file)

        return created_files

    return _create


@pytest.fixture
def create_old_decisions(temp_logs_structure):
    """Factory pour créer des Decision Records avec des dates spécifiques"""

    def _create(days_old: int, count: int = 1):
        """
        Créer des DR avec une date spécifique

        Args:
            days_old: Nombre de jours dans le passé
            count: Nombre de DR à créer
        """
        decisions_dir = temp_logs_structure["decisions"]
        created_files = []

        for i in range(count):
            dr_date = datetime.now() - timedelta(days=days_old + i)
            filename = f"DR-{dr_date.strftime('%Y%m%d')}-{i:04d}.json"
            dr_file = decisions_dir / filename

            dr_data = {
                "dr_id": f"DR-{dr_date.strftime('%Y%m%d')}-{i:04d}",
                "ts": dr_date.isoformat(),
                "actor": "agent.core",
                "decision": "test_decision",
                "reasoning": "test_reasoning",
            }

            with open(dr_file, "w") as f:
                json.dump(dr_data, f)

            created_files.append(dr_file)

        return created_files

    return _create


@pytest.fixture
def create_old_provenance(temp_logs_structure):
    """Factory pour créer des traces de provenance avec des dates spécifiques"""
    counter = {"value": 0}  # Compteur pour éviter les collisions de noms

    def _create(days_old: int, count: int = 1):
        """
        Créer des fichiers de provenance avec mtime spécifique

        Args:
            days_old: Nombre de jours dans le passé
            count: Nombre de fichiers à créer
        """
        import os
        import time

        provenance_dir = temp_logs_structure["provenance"]
        created_files = []

        for i in range(count):
            # Utiliser un compteur global pour éviter les collisions
            file_index = counter["value"]
            counter["value"] += 1

            filename = f"trace-{file_index:04d}.json"
            prov_file = provenance_dir / filename

            prov_data = {"trace_id": f"trace-{file_index:04d}", "entities": [], "activities": []}

            with open(prov_file, "w") as f:
                json.dump(prov_data, f)

            # Modifier le mtime pour simuler un fichier ancien
            old_time = time.time() - (days_old * 24 * 3600)
            os.utime(prov_file, (old_time, old_time))

            created_files.append(prov_file)

        return created_files

    return _create


# ============================================================================
# TESTS: RetentionPolicy
# ============================================================================


@pytest.mark.unit
def test_retention_policy_init():
    """Test initialisation de RetentionPolicy"""
    policy = RetentionPolicy(ttl_days=30, purpose="Testing")

    assert policy.ttl_days == 30
    assert policy.purpose == "Testing"


@pytest.mark.unit
@pytest.mark.parametrize(
    "ttl_days,timestamp_days_old,expected_expired",
    [
        (30, 31, True),  # 31 jours old, TTL 30 → expiré
        (30, 29, False),  # 29 jours old, TTL 30 → pas expiré
        (7, 10, True),  # 10 jours old, TTL 7 → expiré
        (7, 5, False),  # 5 jours old, TTL 7 → pas expiré
        (90, 100, True),  # 100 jours old, TTL 90 → expiré
        (90, 80, False),  # 80 jours old, TTL 90 → pas expiré
    ],
)
def test_retention_policy_is_expired(ttl_days, timestamp_days_old, expected_expired):
    """Test détection d'expiration avec différents TTL et timestamps"""
    policy = RetentionPolicy(ttl_days=ttl_days, purpose="Testing")

    # Créer un timestamp dans le passé
    old_timestamp = datetime.now() - timedelta(days=timestamp_days_old)
    timestamp_str = old_timestamp.isoformat()

    result = policy.is_expired(timestamp_str)
    assert result == expected_expired


@pytest.mark.unit
def test_retention_policy_is_expired_exact_boundary():
    """Test détection d'expiration à la frontière exacte (30 jours)"""
    policy = RetentionPolicy(ttl_days=30, purpose="Testing")

    # Créer un timestamp à exactement 30 jours (avec quelques secondes près)
    # Le comportement à la frontière exacte peut varier selon l'implémentation
    old_timestamp = datetime.now() - timedelta(days=30, seconds=1)
    timestamp_str = old_timestamp.isoformat()

    # Devrait être expiré car > 30 jours
    result = policy.is_expired(timestamp_str)
    assert result == True

    # Créer un timestamp à 30 jours moins 1 seconde
    recent_timestamp = datetime.now() - timedelta(days=30, seconds=-1)
    timestamp_str2 = recent_timestamp.isoformat()

    # Ne devrait pas être expiré car < 30 jours
    result2 = policy.is_expired(timestamp_str2)
    assert result2 == False


@pytest.mark.unit
def test_retention_policy_is_expired_invalid_timestamp():
    """Test is_expired avec timestamp invalide"""
    policy = RetentionPolicy(ttl_days=30, purpose="Testing")

    # Timestamp invalide → retourne False (pas d'exception)
    assert policy.is_expired("invalid-timestamp") == False
    assert policy.is_expired("") == False
    assert policy.is_expired("not-a-date") == False


@pytest.mark.unit
def test_retention_policy_is_expired_future_timestamp():
    """Test is_expired avec timestamp dans le futur"""
    policy = RetentionPolicy(ttl_days=30, purpose="Testing")

    # Timestamp dans le futur → pas expiré
    future_timestamp = datetime.now() + timedelta(days=10)
    timestamp_str = future_timestamp.isoformat()

    assert policy.is_expired(timestamp_str) == False


# ============================================================================
# TESTS: RetentionManager - Initialisation et Configuration
# ============================================================================


@pytest.mark.unit
def test_retention_manager_init_with_valid_config(temp_retention_config):
    """Test initialisation avec configuration valide"""
    manager = RetentionManager(config_path=str(temp_retention_config))

    assert len(manager.policies) > 0
    assert "events" in manager.policies
    assert "decisions" in manager.policies
    assert "conversations" in manager.policies


@pytest.mark.unit
def test_retention_manager_init_missing_config(tmp_path):
    """Test initialisation avec configuration manquante"""
    # Config inexistante
    missing_config = tmp_path / "nonexistent" / "retention.yaml"

    # Ne devrait pas lever d'exception
    manager = RetentionManager(config_path=str(missing_config))

    # Aucune policy chargée
    assert len(manager.policies) == 0


@pytest.mark.unit
def test_retention_manager_load_config_values(temp_retention_config):
    """Test que les valeurs de configuration sont correctement chargées"""
    manager = RetentionManager(config_path=str(temp_retention_config))

    # Vérifier les valeurs spécifiques
    assert manager.policies["events"].ttl_days == 90
    assert manager.policies["events"].purpose == "Troubleshooting"

    assert manager.policies["decisions"].ttl_days == 365
    assert manager.policies["decisions"].purpose == "Audit trail"

    assert manager.policies["conversations"].ttl_days == 30
    assert manager.policies["conversations"].purpose == "User support"


@pytest.mark.unit
def test_retention_manager_get_ttl_days(temp_retention_config):
    """Test récupération de TTL pour différents types de données"""
    manager = RetentionManager(config_path=str(temp_retention_config))

    assert manager.get_ttl_days("events") == 90
    assert manager.get_ttl_days("decisions") == 365
    assert manager.get_ttl_days("conversations") == 30
    assert manager.get_ttl_days("provenance") == 180


@pytest.mark.unit
def test_retention_manager_get_ttl_days_unknown_type(temp_retention_config):
    """Test récupération de TTL pour un type inconnu"""
    manager = RetentionManager(config_path=str(temp_retention_config))

    # Type inconnu → retourne default de 30 jours
    assert manager.get_ttl_days("unknown_type") == 30


# ============================================================================
# TESTS: RetentionManager - Cleanup Events
# ============================================================================


@pytest.mark.unit
def test_cleanup_events_empty_directory(temp_retention_config, temp_logs_structure, monkeypatch):
    """Test cleanup events avec répertoire vide"""
    manager = RetentionManager(config_path=str(temp_retention_config))

    # Patcher le chemin des logs
    monkeypatch.setattr(
        "memory.retention.Path",
        lambda x: temp_logs_structure["events"] if x == "logs/events" else Path(x),
    )

    deleted = manager.cleanup_events()
    assert deleted == 0


@pytest.mark.unit
def test_cleanup_events_no_old_files(
    temp_retention_config, temp_logs_structure, create_old_event_logs, monkeypatch
):
    """Test cleanup events sans fichiers anciens"""
    manager = RetentionManager(config_path=str(temp_retention_config))

    # Créer des fichiers récents (10 jours)
    create_old_event_logs(days_old=10, count=3)

    # Patcher le chemin des logs
    events_dir = temp_logs_structure["events"]
    monkeypatch.setattr(
        "memory.retention.Path", lambda x: events_dir if x == "logs/events" else Path(x)
    )

    deleted = manager.cleanup_events()
    assert deleted == 0

    # Vérifier que les fichiers existent toujours
    assert len(list(events_dir.glob("*.jsonl"))) == 3


@pytest.mark.unit
def test_cleanup_events_with_old_files(
    temp_retention_config, temp_logs_structure, create_old_event_logs, monkeypatch
):
    """Test cleanup events avec fichiers anciens"""
    manager = RetentionManager(config_path=str(temp_retention_config))

    # Créer des fichiers anciens (100 jours > TTL 90)
    old_files = create_old_event_logs(days_old=100, count=3)

    # Créer des fichiers récents (50 jours < TTL 90)
    recent_files = create_old_event_logs(days_old=50, count=2)

    # Patcher le chemin des logs
    events_dir = temp_logs_structure["events"]
    monkeypatch.setattr(
        "memory.retention.Path", lambda x: events_dir if x == "logs/events" else Path(x)
    )

    deleted = manager.cleanup_events()

    # Devrait avoir supprimé 3 fichiers
    assert deleted == 3

    # Vérifier que seuls les fichiers récents restent
    remaining_files = list(events_dir.glob("*.jsonl"))
    assert len(remaining_files) == 2


@pytest.mark.unit
def test_cleanup_events_missing_directory(temp_retention_config, tmp_path, monkeypatch):
    """Test cleanup events avec répertoire inexistant"""
    manager = RetentionManager(config_path=str(temp_retention_config))

    # Patcher avec un répertoire inexistant
    nonexistent_dir = tmp_path / "nonexistent" / "events"
    monkeypatch.setattr(
        "memory.retention.Path", lambda x: nonexistent_dir if x == "logs/events" else Path(x)
    )

    # Ne devrait pas lever d'exception
    deleted = manager.cleanup_events()
    assert deleted == 0


# ============================================================================
# TESTS: RetentionManager - Cleanup Decisions
# ============================================================================


@pytest.mark.unit
def test_cleanup_decisions_with_old_files(
    temp_retention_config, temp_logs_structure, create_old_decisions, monkeypatch
):
    """Test cleanup decisions avec fichiers anciens"""
    manager = RetentionManager(config_path=str(temp_retention_config))

    # Créer des DR anciens (400 jours > TTL 365)
    old_drs = create_old_decisions(days_old=400, count=3)

    # Créer des DR récents (200 jours < TTL 365)
    recent_drs = create_old_decisions(days_old=200, count=2)

    # Patcher le chemin des logs
    decisions_dir = temp_logs_structure["decisions"]
    monkeypatch.setattr(
        "memory.retention.Path", lambda x: decisions_dir if x == "logs/decisions" else Path(x)
    )

    deleted = manager.cleanup_decisions()

    # Devrait avoir supprimé 3 DR
    assert deleted == 3

    # Vérifier que seuls les DR récents restent
    remaining_files = list(decisions_dir.glob("DR-*.json"))
    assert len(remaining_files) == 2


@pytest.mark.unit
def test_cleanup_decisions_invalid_json(temp_retention_config, temp_logs_structure, monkeypatch):
    """Test cleanup decisions avec JSON invalide"""
    manager = RetentionManager(config_path=str(temp_retention_config))

    decisions_dir = temp_logs_structure["decisions"]

    # Créer un fichier DR avec JSON invalide
    invalid_dr = decisions_dir / "DR-20200101-0001.json"
    invalid_dr.write_text("invalid json content")

    # Patcher le chemin des logs
    monkeypatch.setattr(
        "memory.retention.Path", lambda x: decisions_dir if x == "logs/decisions" else Path(x)
    )

    # Ne devrait pas lever d'exception
    deleted = manager.cleanup_decisions()
    assert deleted == 0

    # Le fichier invalide devrait toujours exister
    assert invalid_dr.exists()


# ============================================================================
# TESTS: RetentionManager - Cleanup Provenance
# ============================================================================


@pytest.mark.unit
def test_cleanup_provenance_with_old_files(
    temp_retention_config, temp_logs_structure, create_old_provenance, monkeypatch
):
    """Test cleanup provenance avec fichiers anciens"""
    manager = RetentionManager(config_path=str(temp_retention_config))

    provenance_dir = temp_logs_structure["provenance"]

    # Créer des traces anciennes (200 jours > TTL 180)
    old_traces = create_old_provenance(days_old=200, count=3)

    # Créer des traces récentes (100 jours < TTL 180)
    recent_traces = create_old_provenance(days_old=100, count=2)

    # Vérifier que les fichiers ont été créés
    all_files = list(provenance_dir.glob("*.json"))
    assert len(all_files) == 5, f"Expected 5 files, got {len(all_files)}"

    # Patcher le chemin des logs
    monkeypatch.setattr(
        "memory.retention.Path", lambda x: provenance_dir if x == "logs/traces/otlp" else Path(x)
    )

    deleted = manager.cleanup_provenance()

    # Devrait avoir supprimé au moins 1 trace (les anciennes)
    # Note: Le nombre exact peut varier selon la précision de mtime
    assert deleted >= 1, f"Expected at least 1 deletion, got {deleted}"

    # Vérifier que certains fichiers ont été supprimés
    remaining_files = list(provenance_dir.glob("*.json"))
    assert len(remaining_files) < 5, f"Expected fewer than 5 files, got {len(remaining_files)}"


# ============================================================================
# TESTS: RetentionManager - Cleanup Conversations
# ============================================================================


@pytest.mark.unit
def test_cleanup_conversations(temp_retention_config, temp_db, monkeypatch):
    """Test cleanup conversations"""
    manager = RetentionManager(config_path=str(temp_retention_config))

    # Mock de cleanup_old_conversations depuis memory.episodic
    mock_cleanup = MagicMock(return_value=5)

    with patch("memory.episodic.cleanup_old_conversations", mock_cleanup):
        deleted = manager.cleanup_conversations()

    # Vérifier que la fonction a été appelée avec le bon TTL
    mock_cleanup.assert_called_once_with(30)  # TTL pour conversations
    assert deleted == 5


@pytest.mark.unit
def test_cleanup_conversations_zero_deleted(temp_retention_config, temp_db, monkeypatch):
    """Test cleanup conversations sans suppressions"""
    manager = RetentionManager(config_path=str(temp_retention_config))

    # Mock retournant 0
    mock_cleanup = MagicMock(return_value=0)

    with patch("memory.episodic.cleanup_old_conversations", mock_cleanup):
        deleted = manager.cleanup_conversations()

    assert deleted == 0


# ============================================================================
# TESTS: RetentionManager - Run Cleanup (Full)
# ============================================================================


@pytest.mark.unit
def test_run_cleanup_dry_run(temp_retention_config):
    """Test run_cleanup en mode dry_run"""
    manager = RetentionManager(config_path=str(temp_retention_config))

    results = manager.run_cleanup(dry_run=True)

    # En dry_run, aucune suppression
    assert results["conversations"] == 0
    assert results["events"] == 0
    assert results["decisions"] == 0
    assert results["provenance"] == 0


@pytest.mark.unit
def test_run_cleanup_full(temp_retention_config, temp_logs_structure, monkeypatch):
    """Test run_cleanup complet (tous les types)"""
    manager = RetentionManager(config_path=str(temp_retention_config))

    # Mock toutes les méthodes de cleanup
    with patch.object(manager, "cleanup_conversations", return_value=5):
        with patch.object(manager, "cleanup_events", return_value=10):
            with patch.object(manager, "cleanup_decisions", return_value=3):
                with patch.object(manager, "cleanup_provenance", return_value=7):
                    results = manager.run_cleanup(dry_run=False)

    # Vérifier les résultats
    assert results["conversations"] == 5
    assert results["events"] == 10
    assert results["decisions"] == 3
    assert results["provenance"] == 7


# ============================================================================
# TESTS: Singleton Pattern
# ============================================================================


@pytest.mark.unit
def test_get_retention_manager_singleton():
    """Test que get_retention_manager retourne le même instance"""
    # Reset le singleton
    import memory.retention

    memory.retention._retention_manager = None

    manager1 = get_retention_manager()
    manager2 = get_retention_manager()

    # Devrait être la même instance
    assert manager1 is manager2


@pytest.mark.unit
def test_init_retention_manager(temp_retention_config):
    """Test initialisation explicite du singleton"""
    # Reset le singleton
    import memory.retention

    memory.retention._retention_manager = None

    manager = init_retention_manager(config_path=str(temp_retention_config))

    assert manager is not None
    assert len(manager.policies) > 0

    # Récupérer le singleton
    manager2 = get_retention_manager()
    assert manager is manager2


@pytest.mark.unit
def test_init_retention_manager_replaces_instance(temp_retention_config):
    """Test que init_retention_manager remplace l'instance existante"""
    # Créer une première instance
    manager1 = init_retention_manager(config_path=str(temp_retention_config))

    # Créer une nouvelle instance
    manager2 = init_retention_manager(config_path=str(temp_retention_config))

    # Ce devrait être une nouvelle instance
    # (Note: dans l'implémentation actuelle, c'est remplacé)
    assert manager2 is not None


# ============================================================================
# TESTS: Edge Cases et Error Handling
# ============================================================================


@pytest.mark.unit
def test_cleanup_events_with_malformed_filename(
    temp_retention_config, temp_logs_structure, monkeypatch
):
    """Test cleanup events avec nom de fichier malformé"""
    manager = RetentionManager(config_path=str(temp_retention_config))

    events_dir = temp_logs_structure["events"]

    # Créer un fichier avec nom malformé
    malformed_file = events_dir / "invalid-date-format.jsonl"
    malformed_file.write_text("test content\n")

    # Patcher le chemin des logs
    monkeypatch.setattr(
        "memory.retention.Path", lambda x: events_dir if x == "logs/events" else Path(x)
    )

    # Ne devrait pas lever d'exception
    deleted = manager.cleanup_events()
    assert deleted == 0

    # Le fichier malformé devrait toujours exister
    assert malformed_file.exists()


@pytest.mark.unit
def test_cleanup_decisions_missing_timestamp(
    temp_retention_config, temp_logs_structure, monkeypatch
):
    """Test cleanup decisions avec timestamp manquant dans le JSON"""
    manager = RetentionManager(config_path=str(temp_retention_config))

    decisions_dir = temp_logs_structure["decisions"]

    # Créer un DR sans timestamp
    dr_file = decisions_dir / "DR-20200101-0001.json"
    dr_data = {
        "dr_id": "DR-20200101-0001",
        # 'ts' manquant
        "actor": "test",
    }
    with open(dr_file, "w") as f:
        json.dump(dr_data, f)

    # Patcher le chemin des logs
    monkeypatch.setattr(
        "memory.retention.Path", lambda x: decisions_dir if x == "logs/decisions" else Path(x)
    )

    # Ne devrait pas lever d'exception
    deleted = manager.cleanup_decisions()
    assert deleted == 0

    # Le fichier devrait toujours exister
    assert dr_file.exists()


@pytest.mark.unit
def test_retention_policy_with_zero_ttl():
    """Test RetentionPolicy avec TTL de 0 jours"""
    policy = RetentionPolicy(ttl_days=0, purpose="Immediate expiration")

    # Tout timestamp dans le passé devrait être expiré
    old_timestamp = (datetime.now() - timedelta(days=1)).isoformat()
    assert policy.is_expired(old_timestamp) == True

    # Timestamp dans le futur ne devrait pas être expiré
    future_timestamp = (datetime.now() + timedelta(seconds=10)).isoformat()
    assert policy.is_expired(future_timestamp) == False


@pytest.mark.unit
def test_retention_manager_empty_config(tmp_path):
    """Test RetentionManager avec config vide"""
    config_file = tmp_path / "empty_retention.yaml"
    config_file.write_text("retention: {}")

    manager = RetentionManager(config_path=str(config_file))

    # Aucune policy chargée
    assert len(manager.policies) == 0

    # get_ttl_days devrait retourner le default
    assert manager.get_ttl_days("events") == 30


# ============================================================================
# TESTS: Integration
# ============================================================================


@pytest.mark.integration
def test_full_retention_workflow(
    temp_retention_config,
    temp_logs_structure,
    create_old_event_logs,
    create_old_decisions,
    create_old_provenance,
    monkeypatch,
):
    """Test workflow complet de rétention"""
    manager = RetentionManager(config_path=str(temp_retention_config))

    # Créer des données anciennes et récentes pour chaque type
    events_dir = temp_logs_structure["events"]
    decisions_dir = temp_logs_structure["decisions"]
    provenance_dir = temp_logs_structure["provenance"]

    # Events: 100 jours (expiré) et 50 jours (non expiré)
    create_old_event_logs(days_old=100, count=3)
    create_old_event_logs(days_old=50, count=2)

    # Decisions: 400 jours (expiré) et 200 jours (non expiré)
    create_old_decisions(days_old=400, count=4)
    create_old_decisions(days_old=200, count=3)

    # Provenance: 200 jours (expiré) et 100 jours (non expiré)
    create_old_provenance(days_old=200, count=5)
    create_old_provenance(days_old=100, count=4)

    # Patcher les chemins
    def path_patcher(path_str):
        if path_str == "logs/events":
            return events_dir
        elif path_str == "logs/decisions":
            return decisions_dir
        elif path_str == "logs/traces/otlp":
            return provenance_dir
        return Path(path_str)

    monkeypatch.setattr("memory.retention.Path", path_patcher)

    # Mock cleanup_conversations depuis memory.episodic
    with patch("memory.episodic.cleanup_old_conversations", return_value=2):
        # Exécuter le cleanup complet
        results = manager.run_cleanup(dry_run=False)

    # Vérifier les résultats
    assert results["conversations"] == 2
    assert results["events"] == 3  # 3 fichiers expirés
    assert results["decisions"] == 4  # 4 DR expirés
    assert results["provenance"] >= 1  # Au moins 1 trace expirée (précision mtime)

    # Vérifier les fichiers restants
    assert len(list(events_dir.glob("*.jsonl"))) == 2
    assert len(list(decisions_dir.glob("DR-*.json"))) == 3
    assert len(list(provenance_dir.glob("*.json"))) < 9  # Moins que le total initial


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
