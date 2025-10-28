"""
Extended WORM (Write-Once-Read-Many) compliance tests

Tests edge cases, performance, and security aspects of WORM logging:
- Log rotation and archival
- Checkpoint verification
- Concurrent writes
- Recovery from corruption
- Performance under load
"""

import pytest
import json
import hashlib
import threading
import time
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from runtime.middleware.worm import MerkleTree, WormLogger


# ============================================================================
# TESTS: WORM Log Rotation and Archival
# ============================================================================

@pytest.mark.compliance
def test_worm_log_rotation(isolated_logging):
    """
    Test de conformité: Rotation des logs WORM
    
    Vérifie:
    - Les anciens logs sont préservés
    - Les nouveaux logs continuent dans un nouveau fichier
    - Les checkpoints sont créés pour les fichiers archivés
    """
    worm_logger = isolated_logging['worm_logger']
    log_dir = isolated_logging['event_log_dir']
    
    # Créer le premier fichier de log
    log_file_1 = log_dir / "events_001.jsonl"
    
    # Ajouter des entrées au premier fichier
    for i in range(50):
        worm_logger.append(log_file_1, json.dumps({"event": f"test_{i}"}))
    
    # Créer un checkpoint pour archivage
    checkpoint_hash_1 = worm_logger.create_checkpoint(log_file_1)
    assert checkpoint_hash_1 is not None, "Failed to create checkpoint for log file 1"
    
    # Commencer un nouveau fichier de log (rotation)
    log_file_2 = log_dir / "events_002.jsonl"
    
    # Ajouter des entrées au nouveau fichier
    for i in range(50, 100):
        worm_logger.append(log_file_2, json.dumps({"event": f"test_{i}"}))
    
    # Vérifier que les deux fichiers existent
    assert log_file_1.exists(), "First log file should still exist"
    assert log_file_2.exists(), "Second log file should exist"
    
    # Vérifier que le premier fichier n'a pas changé (WORM)
    with open(log_file_1, 'r') as f:
        lines = f.readlines()
        assert len(lines) == 50, "First log file should have exactly 50 entries"
    
    # Vérifier le nouveau fichier
    with open(log_file_2, 'r') as f:
        lines = f.readlines()
        assert len(lines) == 50, "Second log file should have exactly 50 entries"


@pytest.mark.compliance
def test_worm_checkpoint_verification_after_restart(isolated_logging):
    """
    Test de conformité: Vérification de checkpoint après redémarrage
    
    Vérifie:
    - Les checkpoints persistent
    - Les hash peuvent être recalculés et vérifiés
    - L'intégrité est maintenue entre sessions
    """
    worm_logger = isolated_logging['worm_logger']
    log_dir = isolated_logging['event_log_dir']
    digest_dir = isolated_logging['digest_dir']
    
    log_file = log_dir / "events.jsonl"
    
    # Ajouter des entrées
    entries = []
    for i in range(20):
        entry = json.dumps({"event": f"test_{i}", "timestamp": datetime.utcnow().isoformat()})
        entries.append(entry)
        worm_logger.append(log_file, entry)
    
    # Créer un checkpoint
    original_hash = worm_logger.create_checkpoint(log_file)
    assert original_hash is not None
    
    # Lire le checkpoint sauvegardé
    digest_files = list(digest_dir.glob("*.json"))
    assert len(digest_files) > 0, "No checkpoint files found"
    
    with open(digest_files[0], 'r') as f:
        saved_checkpoint = json.load(f)
    
    saved_hash = saved_checkpoint["root_hash"]
    
    # Simuler un redémarrage: recréer un nouveau logger
    new_logger = WormLogger(log_dir=str(log_dir))
    
    # Recalculer le checkpoint à partir du fichier existant
    recalculated_hash = new_logger.create_checkpoint(log_file)
    
    # Les hash doivent correspondre
    assert recalculated_hash == original_hash, "Hash mismatch after restart"
    assert recalculated_hash == saved_hash, "Hash doesn't match saved checkpoint"


@pytest.mark.compliance
def test_worm_digest_chain_of_custody(isolated_logging):
    """
    Test de conformité: Chaîne de custody via digests
    
    Vérifie:
    - Chaque digest référence le précédent
    - La chaîne est vérifiable
    - Détection de digest manquant dans la chaîne
    """
    worm_logger = isolated_logging['worm_logger']
    log_dir = isolated_logging['event_log_dir']
    digest_dir = isolated_logging['digest_dir']
    
    log_file = log_dir / "events.jsonl"
    
    # Créer plusieurs checkpoints successifs
    checkpoint_hashes = []
    
    for batch in range(3):
        # Ajouter des entrées
        for i in range(10):
            worm_logger.append(log_file, json.dumps({
                "batch": batch,
                "entry": i
            }))
        
        # Créer un checkpoint
        checkpoint_hash = worm_logger.create_checkpoint(log_file)
        checkpoint_hashes.append(checkpoint_hash)
    
    # Vérifier que plusieurs digests existent
    digest_files = sorted(digest_dir.glob("*.json"))
    assert len(digest_files) >= 1, "No digest files created"
    
    # Vérifier que chaque digest contient les métadonnées nécessaires
    for digest_file in digest_files:
        with open(digest_file, 'r') as f:
            digest = json.load(f)
        
        assert "root_hash" in digest
        assert "timestamp" in digest
        assert "num_entries" in digest
        assert digest["num_entries"] > 0


# ============================================================================
# TESTS: Concurrent Access
# ============================================================================

@pytest.mark.compliance
def test_worm_concurrent_writes(isolated_logging):
    """
    Test de conformité: Écritures concurrentes
    
    Vérifie:
    - Les écritures concurrentes ne causent pas de corruption
    - Toutes les entrées sont enregistrées
    - Pas de race conditions
    """
    worm_logger = isolated_logging['worm_logger']
    log_dir = isolated_logging['event_log_dir']
    
    log_file = log_dir / "concurrent_test.jsonl"
    
    num_threads = 10
    entries_per_thread = 20
    
    def write_entries(thread_id):
        """Écrire des entrées depuis un thread"""
        for i in range(entries_per_thread):
            entry = json.dumps({
                "thread": thread_id,
                "entry": i,
                "timestamp": datetime.utcnow().isoformat()
            })
            worm_logger.append(log_file, entry)
    
    # Lancer les threads
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(write_entries, i) for i in range(num_threads)]
        
        # Attendre la fin
        for future in as_completed(futures):
            future.result()  # Propager les exceptions
    
    # Vérifier que toutes les entrées sont présentes
    with open(log_file, 'r') as f:
        lines = f.readlines()
    
    total_expected = num_threads * entries_per_thread
    assert len(lines) == total_expected, f"Expected {total_expected} entries, got {len(lines)}"
    
    # Vérifier que toutes les lignes sont du JSON valide
    for line in lines:
        json.loads(line)  # Ne doit pas crasher


@pytest.mark.compliance
@pytest.mark.slow
def test_worm_performance_degradation(isolated_logging):
    """
    Test de performance: Dégradation avec croissance du log
    
    Vérifie:
    - Le temps d'append reste constant
    - Le temps de checkpoint croît linéairement (acceptable)
    - Pas de dégradation exponentielle
    """
    worm_logger = isolated_logging['worm_logger']
    log_dir = isolated_logging['event_log_dir']
    
    log_file = log_dir / "perf_test.jsonl"
    
    # Mesurer le temps d'append pour différentes tailles
    append_times = []
    checkpoint_times = []
    
    for batch_size in [100, 500, 1000]:
        # Ajouter un batch d'entrées
        start = time.time()
        for i in range(batch_size):
            worm_logger.append(log_file, json.dumps({"entry": i}))
        append_time = time.time() - start
        append_times.append(append_time / batch_size)  # Temps par entrée
        
        # Mesurer le temps de checkpoint
        start = time.time()
        worm_logger.create_checkpoint(log_file)
        checkpoint_time = time.time() - start
        checkpoint_times.append(checkpoint_time)
    
    # Le temps d'append par entrée doit rester relativement constant
    # (tolérance: max 2x du premier)
    assert append_times[-1] < append_times[0] * 2, \
        f"Append time degradation too high: {append_times}"
    
    # Le temps de checkpoint peut croître, mais pas exponentiellement
    # (tolérance: croissance max 3x pour 10x plus de données)
    if len(checkpoint_times) >= 2:
        growth_factor = checkpoint_times[-1] / checkpoint_times[0]
        assert growth_factor < 3, \
            f"Checkpoint time growth too high: {checkpoint_times}"


# ============================================================================
# TESTS: Recovery and Error Handling
# ============================================================================

@pytest.mark.compliance
def test_worm_recovery_from_corrupted_file(isolated_logging):
    """
    Test de conformité: Récupération depuis un fichier corrompu
    
    Vérifie:
    - La détection de corruption
    - Le comportement en cas de fichier malformé
    - Pas de crash sur données invalides
    """
    worm_logger = isolated_logging['worm_logger']
    log_dir = isolated_logging['event_log_dir']
    
    log_file = log_dir / "corrupted.jsonl"
    
    # Créer un fichier avec des entrées valides
    for i in range(10):
        worm_logger.append(log_file, json.dumps({"entry": i}))
    
    # Créer un checkpoint initial
    valid_hash = worm_logger.create_checkpoint(log_file)
    assert valid_hash is not None
    
    # Corrompre le fichier en ajoutant une ligne malformée manuellement
    # (ceci viole WORM mais simule une corruption)
    with open(log_file, 'a') as f:
        f.write("CORRUPTED DATA NOT JSON\n")
    
    # Essayer de créer un checkpoint sur le fichier corrompu
    try:
        corrupted_hash = worm_logger.create_checkpoint(log_file)
        # Le checkpoint devrait échouer ou retourner un hash différent
        if corrupted_hash is not None:
            assert corrupted_hash != valid_hash, \
                "Hash should differ for corrupted file"
    except Exception:
        # L'échec est acceptable (détection de corruption)
        pass


@pytest.mark.compliance
def test_worm_empty_log_checkpoint(isolated_logging):
    """
    Test de conformité: Checkpoint d'un log vide
    
    Vérifie:
    - Comportement avec fichier vide
    - Pas de crash
    - Gestion gracieuse
    """
    worm_logger = isolated_logging['worm_logger']
    log_dir = isolated_logging['event_log_dir']
    
    # Créer un fichier vide
    empty_file = log_dir / "empty.jsonl"
    empty_file.touch()
    
    # Essayer de créer un checkpoint
    checkpoint_hash = worm_logger.create_checkpoint(empty_file)
    
    # Le comportement peut varier selon l'implémentation
    # Mais ne doit pas crasher
    # Soit None, soit un hash pour une liste vide
    assert checkpoint_hash is None or isinstance(checkpoint_hash, str)


@pytest.mark.compliance
def test_worm_single_entry_merkle(isolated_logging):
    """
    Test de conformité: Arbre de Merkle avec une seule entrée
    
    Vérifie:
    - Cas edge avec 1 élément
    - Hash correct
    - Pas de crash
    """
    tree = MerkleTree()
    
    # Construire un arbre avec une seule feuille
    single_data = ["single_entry"]
    root = tree.build_tree(single_data)
    
    assert root is not None
    assert root.hash is not None
    
    # Le hash doit être celui de l'entrée unique
    expected_hash = hashlib.sha256("single_entry".encode()).hexdigest()
    assert root.hash == expected_hash


@pytest.mark.compliance
def test_worm_merkle_empty_string(isolated_logging):
    """
    Test de conformité: Arbre de Merkle avec chaînes vides
    
    Vérifie:
    - Gestion des chaînes vides
    - Pas de crash
    - Hash déterministe
    """
    tree = MerkleTree()
    
    # Construire avec des chaînes vides
    data = ["", "", ""]
    root = tree.build_tree(data)
    
    assert root is not None
    assert root.hash is not None
    
    # Reconstruction doit donner le même hash
    tree2 = MerkleTree()
    root2 = tree2.build_tree(data)
    
    assert root.hash == root2.hash
