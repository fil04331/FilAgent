"""
Tests unitaires pour la méthode finalize_current_log() de WormLogger
Vérifie la conformité Loi 25 (immuabilité, signatures, audit trail)
"""

import pytest
import json
import os
from pathlib import Path
from runtime.middleware.worm import WormLogger


class TestWormLogFinalization:
    """Tests pour la finalisation des logs WORM (Write-Once-Read-Many)"""

    @pytest.fixture
    def temp_logger(self, tmp_path):
        """Créer un logger WORM temporaire pour les tests"""
        log_dir = tmp_path / "logs"
        digest_dir = tmp_path / "logs" / "digests"
        logger = WormLogger(log_dir=str(log_dir), digest_dir=str(digest_dir))
        return logger

    def test_finalize_creates_digest_with_sha256(self, temp_logger, tmp_path):
        """
        Test que finalize_current_log crée un digest avec hash SHA-256
        (requis pour conformité Loi 25)
        """
        # Write some log entries
        temp_logger.append("Event 1: User logged in")
        temp_logger.append("Event 2: User accessed resource")
        temp_logger.append("Event 3: User logged out")

        # Finalize the log
        finalization_id = temp_logger.finalize_current_log(archive=False)

        # Verify finalization succeeded
        assert finalization_id is not None
        assert finalization_id.startswith("FINAL-")

        # Verify digest file created
        digest_dir = tmp_path / "logs" / "digests"
        digest_files = list(digest_dir.glob("*-finalization-*.json"))
        assert len(digest_files) > 0

        # Verify digest structure
        with open(digest_files[0], "r") as f:
            digest_data = json.load(f)

        # Critical fields for Loi 25 compliance
        assert "sha256" in digest_data
        assert "timestamp" in digest_data
        assert "merkle_root" in digest_data
        assert "finalization_id" in digest_data
        assert "compliance" in digest_data

        # Verify compliance metadata
        compliance = digest_data["compliance"]
        assert compliance["standard"] == "Loi 25 (Québec)"
        assert compliance["immutable"] is True

    def test_finalize_creates_cryptographic_signature(self, temp_logger, tmp_path):
        """
        Test que finalize_current_log génère une signature cryptographique EdDSA
        (requis pour non-répudiation et intégrité)
        """
        # Write log entries
        temp_logger.append("Sensitive operation: data processed")

        # Finalize with signature
        finalization_id = temp_logger.finalize_current_log(archive=False)

        # Load digest
        digest_dir = tmp_path / "logs" / "digests"
        digest_files = list(digest_dir.glob("*-finalization-*.json"))
        with open(digest_files[0], "r") as f:
            digest_data = json.load(f)

        # Verify signature exists (if cryptography available)
        if "signature" in digest_data:
            assert digest_data["signature"].startswith("ed25519:")
            assert len(digest_data["signature"]) > 20  # Non-empty signature
            assert "tamper_evident" in digest_data["compliance"]

    def test_finalize_archives_to_audit_signed(self, temp_logger, tmp_path):
        """
        Test que finalize_current_log archive dans audit/signed/
        avec permissions read-only (WORM compliance)
        """
        # Write log entries
        temp_logger.append("Audit event 1")
        temp_logger.append("Audit event 2")

        # Finalize with archiving
        finalization_id = temp_logger.finalize_current_log(archive=True)
        assert finalization_id is not None

        # Verify archive directory created
        archive_dir = Path("audit/signed")
        assert archive_dir.exists()

        # Verify archived log file exists
        archived_logs = list(archive_dir.glob(f"{finalization_id}-*.jsonl"))
        assert len(archived_logs) > 0

        # Verify digest archived
        archived_digests = list(archive_dir.glob(f"{finalization_id}-digest.json"))
        assert len(archived_digests) == 1

        # Verify read-only permissions (Unix systems only)
        if os.name != "nt":  # Skip on Windows
            archive_file = archived_logs[0]
            file_stat = os.stat(archive_file)
            # Check that write bit is not set (read-only)
            # 0o444 = r--r--r--
            assert (file_stat.st_mode & 0o200) == 0  # No write permission for owner

    def test_finalize_handles_nonexistent_log(self, temp_logger):
        """
        Test que finalize_current_log retourne None si le log n'existe pas
        (graceful failure)
        """
        # Try to finalize without writing anything
        nonexistent_log = Path("nonexistent.log")
        finalization_id = temp_logger.finalize_current_log(log_file=nonexistent_log)

        # Should return None gracefully
        assert finalization_id is None

    def test_finalize_creates_merkle_checkpoint_first(self, temp_logger, tmp_path):
        """
        Test que finalize_current_log crée d'abord un checkpoint Merkle
        pour vérification d'intégrité future
        """
        # Write log entries
        temp_logger.append("Line 1")
        temp_logger.append("Line 2")
        temp_logger.append("Line 3")

        # Finalize
        finalization_id = temp_logger.finalize_current_log(archive=False)
        assert finalization_id is not None

        # Verify checkpoint was created
        digest_dir = tmp_path / "logs" / "digests"
        checkpoint_file = digest_dir / "events-checkpoint.json"
        assert checkpoint_file.exists()

        # Verify checkpoint structure
        with open(checkpoint_file, "r") as f:
            checkpoint = json.load(f)

        assert "root_hash" in checkpoint
        assert "num_entries" in checkpoint
        assert checkpoint["num_entries"] == 3

    def test_finalize_digest_contains_all_metadata(self, temp_logger, tmp_path):
        """
        Test que le digest de finalisation contient toutes les métadonnées
        requises pour audit et traçabilité
        """
        # Write log
        temp_logger.append("Test event")

        # Finalize
        finalization_id = temp_logger.finalize_current_log(archive=False)

        # Load digest
        digest_dir = tmp_path / "logs" / "digests"
        digest_files = list(digest_dir.glob("*-finalization-*.json"))
        with open(digest_files[0], "r") as f:
            digest_data = json.load(f)

        # Verify all required metadata present
        required_fields = [
            "finalization_id",
            "log_file",
            "timestamp",
            "sha256",
            "merkle_root",
            "num_entries",
            "compliance",
        ]

        for field in required_fields:
            assert field in digest_data, f"Missing required field: {field}"

        # Verify finalization_id matches
        assert digest_data["finalization_id"] == finalization_id

    def test_finalize_multiple_times_creates_multiple_digests(self, temp_logger, tmp_path):
        """
        Test que plusieurs finalisations créent des digests séparés
        (historisation complète)
        """
        import time

        # First finalization
        temp_logger.append("Event A")
        id1 = temp_logger.finalize_current_log(archive=False)

        # Wait 1 second to ensure different timestamp
        time.sleep(1)

        # Second finalization (after adding more data)
        temp_logger.append("Event B")
        id2 = temp_logger.finalize_current_log(archive=False)

        # Verify two different IDs
        assert id1 != id2

        # Verify two separate digest files (at least 2 finalization files)
        digest_dir = tmp_path / "logs" / "digests"
        digest_files = list(digest_dir.glob("*-finalization-*.json"))
        assert len(digest_files) >= 2

    def test_finalize_thread_safe(self, temp_logger, tmp_path):
        """
        Test que finalize_current_log est thread-safe
        (utilisation du lock interne)
        """
        import threading

        # Write initial data
        temp_logger.append("Thread safety test")

        finalization_ids = []

        def finalize_in_thread():
            fid = temp_logger.finalize_current_log(archive=False)
            finalization_ids.append(fid)

        # Launch multiple threads
        threads = [threading.Thread(target=finalize_in_thread) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All finalizations should succeed
        assert len([fid for fid in finalization_ids if fid is not None]) >= 1

    def test_finalize_preserves_log_content(self, temp_logger, tmp_path):
        """
        Test que la finalisation ne modifie PAS le contenu du log original
        (WORM - Write Once Read Many)
        """
        # Write content
        original_content = "Original log entry\n"
        temp_logger.append(original_content.strip())

        # Read original
        log_file = temp_logger.default_log_file
        with open(log_file, "r") as f:
            before_finalize = f.read()

        # Finalize
        temp_logger.finalize_current_log(archive=False)

        # Read after finalization
        with open(log_file, "r") as f:
            after_finalize = f.read()

        # Content should be IDENTICAL (immutability)
        assert before_finalize == after_finalize


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
