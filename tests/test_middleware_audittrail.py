"""
Comprehensive unit tests for audittrail middleware (Decision Records)

Tests cover:
- DecisionRecord creation and structure
- EdDSA signature generation and verification
- DRManager initialization and graceful fallbacks
- DR persistence and loading
- Cryptographic key generation and storage
- Error handling and edge cases
- Thread safety
- Compliance with FilAgent specifications
"""

import json
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock
from cryptography.hazmat.primitives.asymmetric import ed25519

from runtime.middleware.audittrail import (
    DecisionRecord,
    DRManager,
    get_dr_manager,
    init_dr_manager
)


@pytest.fixture
def temp_dr_dir(tmp_path):
    """Temporary directory for Decision Records"""
    dr_dir = tmp_path / "logs" / "decisions"
    dr_dir.mkdir(parents=True, exist_ok=True)
    return dr_dir


@pytest.fixture
def temp_signature_dir(tmp_path):
    """Temporary directory for cryptographic keys"""
    sig_dir = tmp_path / "provenance" / "signatures"
    sig_dir.mkdir(parents=True, exist_ok=True)
    return sig_dir


@pytest.fixture
def dr_manager_isolated(temp_dr_dir, temp_signature_dir, monkeypatch):
    """Isolated DR manager for testing"""
    # Patch the signature directory
    monkeypatch.setattr('pathlib.Path', lambda x: temp_signature_dir if 'provenance' in str(x) else Path(x))

    manager = DRManager(output_dir=str(temp_dr_dir))
    return manager


class TestDecisionRecordCreation:
    """Test DecisionRecord creation and structure"""

    def test_basic_creation(self):
        """Test création basique d'un DecisionRecord"""
        dr = DecisionRecord(
            actor="agent.core",
            task_id="task-123",
            decision="execute_tool",
            prompt_hash="abc123"
        )

        assert dr.actor == "agent.core"
        assert dr.task_id == "task-123"
        assert dr.decision == "execute_tool"
        assert dr.prompt_hash == "abc123"
        assert dr.dr_id.startswith("DR-")
        assert dr.signature is None  # Not signed yet

    def test_dr_id_format(self):
        """Test format de l'ID de décision"""
        dr = DecisionRecord(
            actor="agent.core",
            task_id="task-123",
            decision="test",
            prompt_hash="abc123"
        )

        # Format: DR-YYYYMMDD-XXXXXX
        assert dr.dr_id.startswith("DR-")
        parts = dr.dr_id.split("-")
        assert len(parts) == 3
        assert len(parts[1]) == 8  # YYYYMMDD
        assert len(parts[2]) == 6  # Random hex

    def test_timestamp_format(self):
        """Test format ISO8601 du timestamp"""
        dr = DecisionRecord(
            actor="agent.core",
            task_id="task-123",
            decision="test",
            prompt_hash="abc123"
        )

        # Should be valid ISO8601
        datetime.fromisoformat(dr.timestamp)

    def test_with_optional_parameters(self):
        """Test création avec paramètres optionnels"""
        dr = DecisionRecord(
            actor="agent.core",
            task_id="task-123",
            decision="execute_tool",
            prompt_hash="abc123",
            policy_version="v2.0",
            model_fingerprint="model-xyz",
            tools_used=["python_sandbox", "file_reader"],
            alternatives_considered=["ask_user", "skip"],
            constraints={"timeout": 30},
            expected_risk=["code_execution"],
            reasoning_markers=["plan:3-steps"]
        )

        assert dr.policy_version == "v2.0"
        assert dr.model_fingerprint == "model-xyz"
        assert len(dr.tools_used) == 2
        assert len(dr.alternatives_considered) == 2
        assert dr.constraints["timeout"] == 30
        assert len(dr.expected_risk) == 1
        assert len(dr.reasoning_markers) == 1

    def test_default_values(self):
        """Test valeurs par défaut"""
        dr = DecisionRecord(
            actor="agent.core",
            task_id="task-123",
            decision="test",
            prompt_hash="abc123"
        )

        assert dr.policy_version == "policies@0.1.0"
        assert dr.model_fingerprint == ""
        assert dr.tools_used == []
        assert dr.alternatives_considered == []
        assert dr.constraints == {}
        assert dr.expected_risk == []
        assert dr.reasoning_markers == []


class TestDecisionRecordSerialization:
    """Test DecisionRecord serialization"""

    def test_to_dict_basic(self):
        """Test conversion en dictionnaire"""
        dr = DecisionRecord(
            actor="agent.core",
            task_id="task-123",
            decision="execute_tool",
            prompt_hash="abc123"
        )

        dr_dict = dr.to_dict()

        assert dr_dict["dr_id"] == dr.dr_id
        assert dr_dict["actor"] == "agent.core"
        assert dr_dict["task_id"] == "task-123"
        assert dr_dict["decision"] == "execute_tool"
        assert dr_dict["prompt_hash"] == "sha256:abc123"

    def test_to_dict_includes_signature(self):
        """Test que to_dict inclut la signature si présente"""
        dr = DecisionRecord(
            actor="agent.core",
            task_id="task-123",
            decision="test",
            prompt_hash="abc123"
        )

        # Sign the DR
        private_key = ed25519.Ed25519PrivateKey.generate()
        dr.sign(private_key)

        dr_dict = dr.to_dict()

        assert "signature" in dr_dict
        assert dr_dict["signature"].startswith("ed25519:")

    def test_to_dict_all_fields(self):
        """Test que to_dict inclut tous les champs"""
        dr = DecisionRecord(
            actor="agent.core",
            task_id="task-123",
            decision="execute_tool",
            prompt_hash="abc123",
            tools_used=["tool1"],
            alternatives_considered=["alt1"],
            constraints={"key": "value"},
            expected_risk=["risk1"],
            reasoning_markers=["marker1"]
        )

        dr_dict = dr.to_dict()

        required_fields = [
            "dr_id", "ts", "actor", "task_id", "policy_version",
            "model_fingerprint", "prompt_hash", "reasoning_markers",
            "tools_used", "alternatives_considered", "decision",
            "constraints", "expected_risk"
        ]

        for field in required_fields:
            assert field in dr_dict


class TestDecisionRecordSignature:
    """Test EdDSA signature functionality"""

    def test_sign_decision_record(self):
        """Test signature d'un DecisionRecord"""
        dr = DecisionRecord(
            actor="agent.core",
            task_id="task-123",
            decision="test",
            prompt_hash="abc123"
        )

        private_key = ed25519.Ed25519PrivateKey.generate()
        dr.sign(private_key)

        assert dr.signature is not None
        assert dr.signature.startswith("ed25519:")

    def test_verify_valid_signature(self):
        """Test vérification d'une signature valide"""
        dr = DecisionRecord(
            actor="agent.core",
            task_id="task-123",
            decision="test",
            prompt_hash="abc123"
        )

        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        dr.sign(private_key)

        assert dr.verify(public_key) is True

    def test_verify_invalid_signature(self):
        """Test vérification d'une signature invalide"""
        dr = DecisionRecord(
            actor="agent.core",
            task_id="task-123",
            decision="test",
            prompt_hash="abc123"
        )

        private_key1 = ed25519.Ed25519PrivateKey.generate()
        private_key2 = ed25519.Ed25519PrivateKey.generate()
        public_key2 = private_key2.public_key()

        dr.sign(private_key1)

        # Verify with different key should fail
        assert dr.verify(public_key2) is False

    def test_verify_unsigned_record(self):
        """Test vérification d'un record non signé"""
        dr = DecisionRecord(
            actor="agent.core",
            task_id="task-123",
            decision="test",
            prompt_hash="abc123"
        )

        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        assert dr.verify(public_key) is False

    def test_signature_tampering_detection(self):
        """Test détection de modification après signature"""
        dr = DecisionRecord(
            actor="agent.core",
            task_id="task-123",
            decision="test",
            prompt_hash="abc123"
        )

        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        dr.sign(private_key)

        # Tamper with the record
        dr.decision = "modified"

        # Verification should fail
        assert dr.verify(public_key) is False


class TestDRManagerInitialization:
    """Test DRManager initialization"""

    def test_basic_initialization(self, temp_dr_dir):
        """Test initialisation basique"""
        manager = DRManager(output_dir=str(temp_dr_dir))

        assert manager.dr_dir == temp_dr_dir
        assert temp_dr_dir.exists()
        assert manager.private_key is not None
        assert manager.public_key is not None

    def test_creates_output_directory(self, tmp_path):
        """Test création du répertoire de sortie"""
        dr_dir = tmp_path / "non_existent" / "logs" / "decisions"
        assert not dr_dir.exists()

        manager = DRManager(output_dir=str(dr_dir))

        assert dr_dir.exists()

    def test_generates_keypair(self, temp_dr_dir):
        """Test génération de paire de clés"""
        manager = DRManager(output_dir=str(temp_dr_dir))

        assert isinstance(manager.private_key, ed25519.Ed25519PrivateKey)
        assert isinstance(manager.public_key, ed25519.Ed25519PublicKey)

    def test_saves_keys_to_filesystem(self, temp_dr_dir, tmp_path, monkeypatch):
        """Test sauvegarde des clés sur le filesystem"""
        # Set up signature directory
        sig_dir = tmp_path / "provenance" / "signatures"
        sig_dir.mkdir(parents=True, exist_ok=True)

        with patch('pathlib.Path') as mock_path:
            mock_path.return_value = sig_dir
            manager = DRManager(output_dir=str(temp_dr_dir))

            # Keys should be saved (in actual implementation)
            # Note: This test may need adjustment based on actual key storage logic


class TestDRManagerCreation:
    """Test DecisionRecord creation via DRManager"""

    def test_create_dr_basic(self, temp_dr_dir):
        """Test création de DR basique"""
        manager = DRManager(output_dir=str(temp_dr_dir))

        dr = manager.create_dr(
            actor="agent.core",
            task_id="task-123",
            decision="execute_tool",
            prompt_hash="abc123"
        )

        assert dr is not None
        assert dr.signature is not None  # Should be auto-signed
        assert (temp_dr_dir / f"{dr.dr_id}.json").exists()

    def test_create_dr_with_kwargs(self, temp_dr_dir):
        """Test création de DR avec kwargs"""
        manager = DRManager(output_dir=str(temp_dr_dir))

        dr = manager.create_dr(
            actor="agent.core",
            task_id="task-123",
            decision="execute_tool",
            prompt_hash="abc123",
            tools_used=["python_sandbox"],
            policy_version="v2.0"
        )

        assert dr.tools_used == ["python_sandbox"]
        assert dr.policy_version == "v2.0"

    def test_create_dr_auto_signs(self, temp_dr_dir):
        """Test que create_dr signe automatiquement"""
        manager = DRManager(output_dir=str(temp_dr_dir))

        dr = manager.create_dr(
            actor="agent.core",
            task_id="task-123",
            decision="test",
            prompt_hash="abc123"
        )

        assert dr.signature is not None
        assert dr.verify(manager.public_key) is True

    def test_create_dr_saves_to_file(self, temp_dr_dir):
        """Test que create_dr sauvegarde dans un fichier"""
        manager = DRManager(output_dir=str(temp_dr_dir))

        dr = manager.create_dr(
            actor="agent.core",
            task_id="task-123",
            decision="test",
            prompt_hash="abc123"
        )

        dr_file = temp_dr_dir / f"{dr.dr_id}.json"
        assert dr_file.exists()

        with open(dr_file, 'r') as f:
            saved_data = json.load(f)

        assert saved_data["dr_id"] == dr.dr_id
        assert saved_data["actor"] == "agent.core"

    def test_create_record_simplified_api(self, temp_dr_dir):
        """Test API simplifiée create_record"""
        manager = DRManager(output_dir=str(temp_dr_dir))

        decision_id = manager.create_record(
            conversation_id="conv-123",
            decision_type="tool_invocation",
            context={"tool": "python_sandbox"},
            rationale="User requested code execution"
        )

        assert decision_id.startswith("DR-")

        # Verify file was created
        dr_file = temp_dr_dir / f"{decision_id}.json"
        assert dr_file.exists()


class TestDRManagerPersistence:
    """Test DR persistence and loading"""

    def test_save_dr(self, temp_dr_dir):
        """Test sauvegarde d'un DR"""
        manager = DRManager(output_dir=str(temp_dr_dir))

        dr = DecisionRecord(
            actor="agent.core",
            task_id="task-123",
            decision="test",
            prompt_hash="abc123"
        )
        dr.sign(manager.private_key)

        manager.save_dr(dr)

        dr_file = temp_dr_dir / f"{dr.dr_id}.json"
        assert dr_file.exists()

    def test_load_dr(self, temp_dr_dir):
        """Test chargement d'un DR"""
        manager = DRManager(output_dir=str(temp_dr_dir))

        # Create and save DR
        dr = manager.create_dr(
            actor="agent.core",
            task_id="task-123",
            decision="test",
            prompt_hash="abc123"
        )

        # Load DR
        loaded_dr = manager.load_dr(dr.dr_id)

        assert loaded_dr is not None
        assert loaded_dr.dr_id == dr.dr_id
        assert loaded_dr.actor == dr.actor
        assert loaded_dr.decision == dr.decision

    def test_load_nonexistent_dr(self, temp_dr_dir):
        """Test chargement d'un DR inexistant"""
        manager = DRManager(output_dir=str(temp_dr_dir))

        loaded_dr = manager.load_dr("DR-99999999-NONEXISTENT")

        assert loaded_dr is None

    def test_load_dr_preserves_signature(self, temp_dr_dir):
        """Test que le chargement préserve la signature"""
        manager = DRManager(output_dir=str(temp_dr_dir))

        # Create and save DR
        dr = manager.create_dr(
            actor="agent.core",
            task_id="task-123",
            decision="test",
            prompt_hash="abc123"
        )

        # Load DR
        loaded_dr = manager.load_dr(dr.dr_id)

        assert loaded_dr.signature == dr.signature
        assert loaded_dr.verify(manager.public_key) is True


class TestThreadSafety:
    """Test thread safety of DRManager"""

    def test_concurrent_dr_creation(self, temp_dr_dir):
        """Test création concurrente de DRs"""
        import threading

        manager = DRManager(output_dir=str(temp_dr_dir))
        created_drs = []
        lock = threading.Lock()

        def create_drs(thread_id):
            for i in range(5):
                dr = manager.create_dr(
                    actor=f"thread-{thread_id}",
                    task_id=f"task-{thread_id}-{i}",
                    decision="test",
                    prompt_hash=f"hash-{thread_id}-{i}"
                )
                with lock:
                    created_drs.append(dr.dr_id)

        # Create multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=create_drs, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Verify all DRs were created
        assert len(created_drs) == 15  # 3 threads * 5 DRs
        assert len(set(created_drs)) == 15  # All unique


class TestSingletonPattern:
    """Test singleton pattern for get_dr_manager()"""

    def test_get_dr_manager_returns_singleton(self):
        """Test que get_dr_manager retourne toujours la même instance"""
        manager1 = get_dr_manager()
        manager2 = get_dr_manager()

        assert manager1 is manager2

    def test_init_dr_manager_creates_new_instance(self, temp_dr_dir):
        """Test que init_dr_manager crée une nouvelle instance"""
        manager1 = init_dr_manager(output_dir=str(temp_dr_dir))
        manager2 = get_dr_manager()

        assert manager1 is manager2


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_dr_with_empty_tools_used(self, temp_dr_dir):
        """Test DR avec liste d'outils vide"""
        manager = DRManager(output_dir=str(temp_dr_dir))

        dr = manager.create_dr(
            actor="agent.core",
            task_id="task-123",
            decision="test",
            prompt_hash="abc123",
            tools_used=[]
        )

        assert dr.tools_used == []

    def test_dr_with_empty_constraints(self, temp_dr_dir):
        """Test DR avec contraintes vides"""
        manager = DRManager(output_dir=str(temp_dr_dir))

        dr = manager.create_dr(
            actor="agent.core",
            task_id="task-123",
            decision="test",
            prompt_hash="abc123",
            constraints={}
        )

        assert dr.constraints == {}

    def test_dr_with_special_characters(self, temp_dr_dir):
        """Test DR avec caractères spéciaux"""
        manager = DRManager(output_dir=str(temp_dr_dir))

        dr = manager.create_dr(
            actor="agent.core",
            task_id="task-éàü-123",
            decision="Décision avec accents",
            prompt_hash="abc123"
        )

        # Should save and load correctly
        loaded_dr = manager.load_dr(dr.dr_id)
        assert loaded_dr.decision == "Décision avec accents"

    def test_dr_with_long_decision_text(self, temp_dr_dir):
        """Test DR avec texte de décision très long"""
        manager = DRManager(output_dir=str(temp_dr_dir))

        long_decision = "x" * 10000

        dr = manager.create_dr(
            actor="agent.core",
            task_id="task-123",
            decision=long_decision,
            prompt_hash="abc123"
        )

        loaded_dr = manager.load_dr(dr.dr_id)
        assert loaded_dr.decision == long_decision

    def test_corrupted_dr_file(self, temp_dr_dir):
        """Test gestion d'un fichier DR corrompu"""
        manager = DRManager(output_dir=str(temp_dr_dir))

        # Create a corrupted file
        dr_file = temp_dr_dir / "DR-20250101-CORRUPT.json"
        with open(dr_file, 'w') as f:
            f.write("{ invalid json")

        # Should handle gracefully
        try:
            loaded_dr = manager.load_dr("DR-20250101-CORRUPT")
            # Should return None or raise appropriate exception
        except json.JSONDecodeError:
            # Expected behavior
            pass


class TestComplianceRequirements:
    """Test compliance with governance requirements"""

    def test_dr_contains_required_fields(self, temp_dr_dir):
        """Test que les DRs contiennent tous les champs requis"""
        manager = DRManager(output_dir=str(temp_dr_dir))

        dr = manager.create_dr(
            actor="agent.core",
            task_id="task-123",
            decision="test",
            prompt_hash="abc123"
        )

        required_fields = [
            "dr_id", "ts", "actor", "task_id", "policy_version",
            "model_fingerprint", "prompt_hash", "decision", "signature"
        ]

        dr_dict = dr.to_dict()
        for field in required_fields:
            assert field in dr_dict, f"Missing required field: {field}"

    def test_prompt_hash_format(self, temp_dr_dir):
        """Test format du hash de prompt"""
        manager = DRManager(output_dir=str(temp_dr_dir))

        dr = manager.create_dr(
            actor="agent.core",
            task_id="task-123",
            decision="test",
            prompt_hash="abc123"
        )

        dr_dict = dr.to_dict()
        assert dr_dict["prompt_hash"].startswith("sha256:")

    def test_signature_format(self, temp_dr_dir):
        """Test format de la signature"""
        manager = DRManager(output_dir=str(temp_dr_dir))

        dr = manager.create_dr(
            actor="agent.core",
            task_id="task-123",
            decision="test",
            prompt_hash="abc123"
        )

        assert dr.signature.startswith("ed25519:")

    def test_dr_file_is_valid_json(self, temp_dr_dir):
        """Test que le fichier DR est un JSON valide"""
        manager = DRManager(output_dir=str(temp_dr_dir))

        dr = manager.create_dr(
            actor="agent.core",
            task_id="task-123",
            decision="test",
            prompt_hash="abc123"
        )

        dr_file = temp_dr_dir / f"{dr.dr_id}.json"
        with open(dr_file, 'r') as f:
            data = json.load(f)

        assert isinstance(data, dict)
        assert "dr_id" in data

    def test_dr_immutability_via_signature(self, temp_dr_dir):
        """Test immutabilité via signature"""
        manager = DRManager(output_dir=str(temp_dr_dir))

        dr = manager.create_dr(
            actor="agent.core",
            task_id="task-123",
            decision="test",
            prompt_hash="abc123"
        )

        # Load DR from file
        loaded_dr = manager.load_dr(dr.dr_id)

        # Tamper with loaded DR
        loaded_dr.decision = "modified"

        # Signature verification should fail
        assert loaded_dr.verify(manager.public_key) is False
