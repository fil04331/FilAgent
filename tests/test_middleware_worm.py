"""
Comprehensive unit tests for WORM middleware (Write Once Read Many)

Tests cover:
- MerkleNode functionality
- MerkleTree construction and hashing
- WormLogger initialization and graceful fallbacks
- Append-only logging
- Checkpoint creation and verification
- Integrity verification
- Thread safety
- Error handling and edge cases
"""

import json
import pytest
from pathlib import Path
from datetime import datetime
import threading

from runtime.middleware.worm import (
    MerkleNode,
    MerkleTree,
    WormLogger,
    get_worm_logger,
    init_worm_logger,
)


@pytest.fixture
def temp_log_dir(tmp_path):
    """Temporary directory for WORM logs"""
    log_dir = tmp_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


@pytest.fixture
def temp_digest_dir(tmp_path):
    """Temporary directory for digests"""
    digest_dir = tmp_path / "logs" / "digests"
    digest_dir.mkdir(parents=True, exist_ok=True)
    return digest_dir


class TestMerkleNode:
    """Test MerkleNode functionality"""

    def test_create_leaf_node(self):
        """Test création d'un nœud feuille"""
        node = MerkleNode(data="test data")

        assert node.data == "test data"
        assert node.hash is not None
        assert node.left is None
        assert node.right is None

    def test_node_hash_deterministic(self):
        """Test que le hash est déterministe"""
        node1 = MerkleNode(data="test data")
        node2 = MerkleNode(data="test data")

        assert node1.hash == node2.hash

    def test_different_data_different_hash(self):
        """Test que des données différentes donnent des hash différents"""
        node1 = MerkleNode(data="data1")
        node2 = MerkleNode(data="data2")

        assert node1.hash != node2.hash

    def test_create_parent_node(self):
        """Test création d'un nœud parent"""
        left = MerkleNode(data="left")
        right = MerkleNode(data="right")
        parent = MerkleNode(left=left, right=right)

        assert parent.left == left
        assert parent.right == right
        assert parent.data == ""

    def test_compute_hash_for_parent(self):
        """Test calcul de hash pour un nœud parent"""
        left = MerkleNode(data="left")
        right = MerkleNode(data="right")
        parent = MerkleNode(left=left, right=right)
        parent.compute_hash()

        assert parent.hash is not None
        assert parent.hash != left.hash
        assert parent.hash != right.hash


class TestMerkleTree:
    """Test MerkleTree construction and hashing"""

    def test_build_tree_single_element(self):
        """Test construction d'arbre avec un seul élément"""
        tree = MerkleTree()
        root = tree.build_tree(["data1"])

        assert root is not None
        assert tree.root is not None
        assert len(tree.nodes) == 1

    def test_build_tree_multiple_elements(self):
        """Test construction d'arbre avec plusieurs éléments"""
        tree = MerkleTree()
        data = ["data1", "data2", "data3", "data4"]
        root = tree.build_tree(data)

        assert root is not None
        assert tree.root is not None
        assert len(tree.nodes) == 4

    def test_build_tree_odd_number_of_elements(self):
        """Test construction d'arbre avec nombre impair d'éléments"""
        tree = MerkleTree()
        data = ["data1", "data2", "data3"]
        root = tree.build_tree(data)

        assert root is not None

    def test_get_root_hash(self):
        """Test récupération du hash racine"""
        tree = MerkleTree()
        tree.build_tree(["data1", "data2"])

        root_hash = tree.get_root_hash()

        assert root_hash is not None
        assert isinstance(root_hash, str)
        assert len(root_hash) == 64  # SHA-256 hex

    def test_root_hash_changes_with_data(self):
        """Test que le hash racine change avec les données"""
        tree1 = MerkleTree()
        tree1.build_tree(["data1", "data2"])
        hash1 = tree1.get_root_hash()

        tree2 = MerkleTree()
        tree2.build_tree(["data1", "data3"])
        hash2 = tree2.get_root_hash()

        assert hash1 != hash2

    def test_root_hash_same_for_same_data(self):
        """Test que le hash racine est le même pour les mêmes données"""
        tree1 = MerkleTree()
        tree1.build_tree(["data1", "data2"])
        hash1 = tree1.get_root_hash()

        tree2 = MerkleTree()
        tree2.build_tree(["data1", "data2"])
        hash2 = tree2.get_root_hash()

        assert hash1 == hash2

    def test_build_tree_empty_list(self):
        """Test construction d'arbre avec liste vide"""
        tree = MerkleTree()
        root = tree.build_tree([])

        assert root is None
        assert tree.get_root_hash() is None


class TestWormLoggerInitialization:
    """Test WormLogger initialization"""

    def test_basic_initialization(self, temp_log_dir, temp_digest_dir):
        """Test initialisation basique"""
        logger = WormLogger(log_dir=str(temp_log_dir), digest_dir=str(temp_digest_dir))

        assert logger.log_dir == temp_log_dir
        assert logger.digest_dir == temp_digest_dir
        assert temp_log_dir.exists()
        assert temp_digest_dir.exists()

    def test_creates_log_directory(self, tmp_path):
        """Test création du répertoire de log"""
        log_dir = tmp_path / "non_existent" / "logs"
        assert not log_dir.exists()

        logger = WormLogger(log_dir=str(log_dir))

        assert log_dir.exists()

    def test_creates_digest_directory(self, tmp_path):
        """Test création du répertoire de digest"""
        log_dir = tmp_path / "logs"
        digest_dir = tmp_path / "digests"

        logger = WormLogger(log_dir=str(log_dir), digest_dir=str(digest_dir))

        assert digest_dir.exists()

    def test_default_digest_directory(self, temp_log_dir):
        """Test répertoire de digest par défaut"""
        logger = WormLogger(log_dir=str(temp_log_dir))

        assert "logs/digests" in str(logger.digest_dir)


class TestAppendOnlyLogging:
    """Test append-only logging functionality"""

    def test_append_to_default_log(self, temp_log_dir, temp_digest_dir):
        """Test ajout au log par défaut"""
        logger = WormLogger(log_dir=str(temp_log_dir), digest_dir=str(temp_digest_dir))

        success = logger.append("Test log line")

        assert success is True
        assert logger.default_log_file.exists()

    def test_append_to_specific_log(self, temp_log_dir, temp_digest_dir):
        """Test ajout à un log spécifique"""
        logger = WormLogger(log_dir=str(temp_log_dir), digest_dir=str(temp_digest_dir))

        log_file = temp_log_dir / "custom.log"
        success = logger.append("Test log line", log_file=log_file)

        assert success is True
        assert log_file.exists()

    def test_append_creates_file(self, temp_log_dir, temp_digest_dir):
        """Test que append crée le fichier s'il n'existe pas"""
        logger = WormLogger(log_dir=str(temp_log_dir), digest_dir=str(temp_digest_dir))

        log_file = temp_log_dir / "new.log"
        assert not log_file.exists()

        logger.append("First line", log_file=log_file)

        assert log_file.exists()

    def test_append_multiple_lines(self, temp_log_dir, temp_digest_dir):
        """Test ajout de plusieurs lignes"""
        logger = WormLogger(log_dir=str(temp_log_dir), digest_dir=str(temp_digest_dir))

        logger.append("Line 1")
        logger.append("Line 2")
        logger.append("Line 3")

        with open(logger.default_log_file, "r") as f:
            lines = f.readlines()

        assert len(lines) == 3
        assert lines[0].strip() == "Line 1"
        assert lines[1].strip() == "Line 2"
        assert lines[2].strip() == "Line 3"

    def test_append_is_immediate(self, temp_log_dir, temp_digest_dir):
        """Test que append écrit immédiatement (fsync)"""
        logger = WormLogger(log_dir=str(temp_log_dir), digest_dir=str(temp_digest_dir))

        logger.append("Test line")

        # Should be immediately available
        with open(logger.default_log_file, "r") as f:
            content = f.read()

        assert "Test line" in content

    def test_append_with_path_object(self, temp_log_dir, temp_digest_dir):
        """Test append avec Path object"""
        logger = WormLogger(log_dir=str(temp_log_dir), digest_dir=str(temp_digest_dir))

        log_file = Path(temp_log_dir) / "test.log"
        logger.append("Test", log_file=log_file)

        assert log_file.exists()

    def test_append_with_string_path(self, temp_log_dir, temp_digest_dir):
        """Test append avec string path"""
        logger = WormLogger(log_dir=str(temp_log_dir), digest_dir=str(temp_digest_dir))

        log_file = str(temp_log_dir / "test.log")
        logger.append("Test", log_file=log_file)

        assert Path(log_file).exists()


class TestCheckpointCreation:
    """Test checkpoint creation"""

    def test_create_checkpoint_basic(self, temp_log_dir, temp_digest_dir):
        """Test création de checkpoint basique"""
        logger = WormLogger(log_dir=str(temp_log_dir), digest_dir=str(temp_digest_dir))

        logger.append("Line 1")
        logger.append("Line 2")

        checkpoint_hash = logger.create_checkpoint()

        assert checkpoint_hash is not None
        assert len(checkpoint_hash) == 64  # SHA-256

    def test_create_checkpoint_for_specific_file(self, temp_log_dir, temp_digest_dir):
        """Test création de checkpoint pour fichier spécifique"""
        logger = WormLogger(log_dir=str(temp_log_dir), digest_dir=str(temp_digest_dir))

        log_file = temp_log_dir / "custom.log"
        logger.append("Line 1", log_file=log_file)
        logger.append("Line 2", log_file=log_file)

        checkpoint_hash = logger.create_checkpoint(log_file=log_file)

        assert checkpoint_hash is not None

    def test_create_checkpoint_saves_file(self, temp_log_dir, temp_digest_dir):
        """Test que create_checkpoint sauvegarde un fichier"""
        logger = WormLogger(log_dir=str(temp_log_dir), digest_dir=str(temp_digest_dir))

        logger.append("Line 1")
        logger.create_checkpoint()

        # Should create checkpoint file
        checkpoint_files = list(temp_digest_dir.glob("*-checkpoint.json"))
        assert len(checkpoint_files) >= 1

    def test_checkpoint_file_structure(self, temp_log_dir, temp_digest_dir):
        """Test structure du fichier de checkpoint"""
        logger = WormLogger(log_dir=str(temp_log_dir), digest_dir=str(temp_digest_dir))

        logger.append("Line 1")
        logger.create_checkpoint()

        checkpoint_file = temp_digest_dir / "events-checkpoint.json"
        with open(checkpoint_file, "r") as f:
            data = json.load(f)

        assert "file" in data
        assert "timestamp" in data
        assert "root_hash" in data
        assert "num_entries" in data

    def test_create_checkpoint_for_nonexistent_file(self, temp_log_dir, temp_digest_dir):
        """Test création de checkpoint pour fichier inexistant"""
        logger = WormLogger(log_dir=str(temp_log_dir), digest_dir=str(temp_digest_dir))

        log_file = temp_log_dir / "nonexistent.log"
        checkpoint_hash = logger.create_checkpoint(log_file=log_file)

        assert checkpoint_hash is None


class TestIntegrityVerification:
    """Test integrity verification"""

    def test_verify_integrity_valid(self, temp_log_dir, temp_digest_dir):
        """Test vérification d'intégrité valide"""
        logger = WormLogger(log_dir=str(temp_log_dir), digest_dir=str(temp_digest_dir))

        logger.append("Line 1")
        logger.append("Line 2")

        checkpoint_hash = logger.create_checkpoint()
        is_valid = logger.verify_integrity(expected_hash=checkpoint_hash)

        assert is_valid is True

    def test_verify_integrity_invalid(self, temp_log_dir, temp_digest_dir):
        """Test vérification d'intégrité invalide"""
        logger = WormLogger(log_dir=str(temp_log_dir), digest_dir=str(temp_digest_dir))

        logger.append("Line 1")
        logger.create_checkpoint()

        # Tamper with log
        logger.append("Line 2")

        # Verification should fail with old hash
        is_valid = logger.verify_integrity()

        assert is_valid is False

    def test_verify_integrity_loads_checkpoint(self, temp_log_dir, temp_digest_dir):
        """Test que verify_integrity charge le checkpoint automatiquement"""
        logger = WormLogger(log_dir=str(temp_log_dir), digest_dir=str(temp_digest_dir))

        logger.append("Line 1")
        logger.create_checkpoint()

        # Verify without providing expected_hash (should load from checkpoint)
        is_valid = logger.verify_integrity()

        assert is_valid is True

    def test_verify_integrity_for_specific_file(self, temp_log_dir, temp_digest_dir):
        """Test vérification pour fichier spécifique"""
        logger = WormLogger(log_dir=str(temp_log_dir), digest_dir=str(temp_digest_dir))

        log_file = temp_log_dir / "custom.log"
        logger.append("Line 1", log_file=log_file)

        checkpoint_hash = logger.create_checkpoint(log_file=log_file)
        is_valid = logger.verify_integrity(log_file=log_file, expected_hash=checkpoint_hash)

        assert is_valid is True

    def test_verify_integrity_nonexistent_file(self, temp_log_dir, temp_digest_dir):
        """Test vérification pour fichier inexistant"""
        logger = WormLogger(log_dir=str(temp_log_dir), digest_dir=str(temp_digest_dir))

        log_file = temp_log_dir / "nonexistent.log"
        is_valid = logger.verify_integrity(log_file=log_file, expected_hash="abc123")

        assert is_valid is False

    def test_verify_integrity_no_checkpoint(self, temp_log_dir, temp_digest_dir):
        """Test vérification sans checkpoint"""
        logger = WormLogger(log_dir=str(temp_log_dir), digest_dir=str(temp_digest_dir))

        logger.append("Line 1")

        # No checkpoint created
        is_valid = logger.verify_integrity()

        assert is_valid is False


class TestThreadSafety:
    """Test thread safety"""

    def test_concurrent_appends(self, temp_log_dir, temp_digest_dir):
        """Test appends concurrents"""
        logger = WormLogger(log_dir=str(temp_log_dir), digest_dir=str(temp_digest_dir))

        def append_lines(thread_id):
            for i in range(10):
                logger.append(f"Thread {thread_id} - Line {i}")

        threads = []
        for i in range(5):
            thread = threading.Thread(target=append_lines, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All lines should be written
        with open(logger.default_log_file, "r") as f:
            lines = f.readlines()

        assert len(lines) == 50  # 5 threads * 10 lines


class TestSingletonPattern:
    """Test singleton pattern"""

    def test_get_worm_logger_returns_singleton(self):
        """Test que get_worm_logger retourne toujours la même instance"""
        logger1 = get_worm_logger()
        logger2 = get_worm_logger()

        assert logger1 is logger2

    def test_init_worm_logger_creates_new_instance(self, temp_log_dir):
        """Test que init_worm_logger crée une nouvelle instance"""
        logger1 = init_worm_logger(log_dir=str(temp_log_dir))
        logger2 = get_worm_logger()

        assert logger1 is logger2


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_append_empty_string(self, temp_log_dir, temp_digest_dir):
        """Test append de chaîne vide"""
        logger = WormLogger(log_dir=str(temp_log_dir), digest_dir=str(temp_digest_dir))

        success = logger.append("")

        assert success is True

        with open(logger.default_log_file, "r") as f:
            lines = f.readlines()

        assert len(lines) == 1

    def test_append_special_characters(self, temp_log_dir, temp_digest_dir):
        """Test append avec caractères spéciaux"""
        logger = WormLogger(log_dir=str(temp_log_dir), digest_dir=str(temp_digest_dir))

        logger.append("Line with accents: éàü")
        logger.append("Line with symbols: €£¥")

        with open(logger.default_log_file, "r", encoding="utf-8") as f:
            content = f.read()

        assert "éàü" in content
        assert "€£¥" in content

    def test_append_very_long_line(self, temp_log_dir, temp_digest_dir):
        """Test append de ligne très longue"""
        logger = WormLogger(log_dir=str(temp_log_dir), digest_dir=str(temp_digest_dir))

        long_line = "x" * 100000
        success = logger.append(long_line)

        assert success is True

    def test_checkpoint_snapshot_timestamped(self, temp_log_dir, temp_digest_dir):
        """Test que les snapshots de checkpoint sont horodatés"""
        logger = WormLogger(log_dir=str(temp_log_dir), digest_dir=str(temp_digest_dir))

        logger.append("Line 1")
        logger.create_checkpoint()

        # Should create timestamped snapshot
        snapshot_files = list(temp_digest_dir.glob("events-*.json"))
        assert len(snapshot_files) >= 1

        # Should have timestamp in filename
        for f in snapshot_files:
            if "checkpoint" not in f.name:
                # Timestamped file
                assert len(f.stem.split("-")) >= 2


class TestComplianceRequirements:
    """Test compliance with WORM requirements"""

    def test_append_only_no_modification(self, temp_log_dir, temp_digest_dir):
        """Test que les logs sont append-only"""
        logger = WormLogger(log_dir=str(temp_log_dir), digest_dir=str(temp_digest_dir))

        logger.append("Line 1")
        logger.append("Line 2")

        # Verify lines are append-only
        with open(logger.default_log_file, "r") as f:
            lines = f.readlines()

        assert len(lines) == 2
        assert lines[0].strip() == "Line 1"
        assert lines[1].strip() == "Line 2"

    def test_merkle_tree_tamper_detection(self, temp_log_dir, temp_digest_dir):
        """Test détection de modification via Merkle tree"""
        logger = WormLogger(log_dir=str(temp_log_dir), digest_dir=str(temp_digest_dir))

        logger.append("Line 1")
        logger.append("Line 2")

        checkpoint_hash = logger.create_checkpoint()

        # Manually tamper with log file
        with open(logger.default_log_file, "a") as f:
            f.write("Tampered line\n")

        # Verification should fail
        is_valid = logger.verify_integrity(expected_hash=checkpoint_hash)

        assert is_valid is False

    def test_checkpoint_preserves_history(self, temp_log_dir, temp_digest_dir):
        """Test que les checkpoints préservent l'historique"""
        logger = WormLogger(log_dir=str(temp_log_dir), digest_dir=str(temp_digest_dir))

        logger.append("Line 1")
        hash1 = logger.create_checkpoint()

        logger.append("Line 2")
        hash2 = logger.create_checkpoint()

        # Should have multiple checkpoint snapshots
        snapshot_files = list(temp_digest_dir.glob("events-*.json"))
        assert len(snapshot_files) >= 3  # 2 timestamped + 1 latest
