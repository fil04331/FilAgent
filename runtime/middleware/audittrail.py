"""
Middleware pour Decision Records (DR)
Génération de DR signés pour traçabilité décisionnelle
"""

import json
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
import threading
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519


class DecisionRecord:
    """
    Decision Record (DR) pour une décision automatisée
    Format conforme aux spécifications de FilAgent.md
    """

    def __init__(
        self,
        actor: str,
        task_id: str,
        decision: str,
        prompt_hash: str,
        policy_version: str = "policies@0.1.0",
        model_fingerprint: str = "",
        tools_used: Optional[List[str]] = None,
        alternatives_considered: Optional[List[str]] = None,
        constraints: Optional[Dict[str, Any]] = None,
        expected_risk: Optional[List[str]] = None,
        reasoning_markers: Optional[List[str]] = None,
    ):
        self.dr_id = self._generate_dr_id()
        self.timestamp = datetime.now().isoformat()
        self.actor = actor
        self.task_id = task_id
        self.policy_version = policy_version
        self.model_fingerprint = model_fingerprint
        self.prompt_hash = prompt_hash
        self.reasoning_markers = reasoning_markers or []
        self.tools_used = tools_used or []
        self.alternatives_considered = alternatives_considered or []
        self.decision = decision
        self.constraints = constraints or {}
        self.expected_risk = expected_risk or []
        self.signature = None

    def _generate_dr_id(self) -> str:
        """Générer un ID unique pour le DR"""
        timestamp = datetime.now().strftime("%Y%m%d")
        random = hashlib.md5(datetime.now().isoformat().encode()).hexdigest()[:6]
        return f"DR-{timestamp}-{random}"

    def to_dict(self) -> Dict[str, Any]:
        """Convertir en dictionnaire"""
        data = {
            "dr_id": self.dr_id,
            "ts": self.timestamp,
            "actor": self.actor,
            "task_id": self.task_id,
            "policy_version": self.policy_version,
            "model_fingerprint": self.model_fingerprint,
            "prompt_hash": f"sha256:{self.prompt_hash}",
            "reasoning_markers": self.reasoning_markers,
            "tools_used": self.tools_used,
            "alternatives_considered": self.alternatives_considered,
            "decision": self.decision,
            "constraints": self.constraints,
            "expected_risk": self.expected_risk,
        }

        if self.signature:
            data["signature"] = self.signature

        return data

    def sign(self, private_key: ed25519.Ed25519PrivateKey):
        """Signer le DR avec une clé privée EdDSA"""
        # Créer un dictionnaire sans signature
        data = self.to_dict()
        data.pop("signature", None)

        # Sérialiser et signer
        data_bytes = json.dumps(data, sort_keys=True).encode("utf-8")
        signature = private_key.sign(data_bytes)
        self.signature = f"ed25519:{signature.hex()}"

    def verify(self, public_key: ed25519.Ed25519PublicKey) -> bool:
        """Vérifier la signature du DR"""
        if not self.signature:
            return False

        try:
            # Extraire la signature
            sig_hex = self.signature.replace("ed25519:", "")
            signature_bytes = bytes.fromhex(sig_hex)

            # Créer un dictionnaire sans signature
            data = self.to_dict()
            data.pop("signature", None)
            data_bytes = json.dumps(data, sort_keys=True).encode("utf-8")

            # Vérifier
            public_key.verify(signature_bytes, data_bytes)
            return True
        except Exception:
            return False


class DRManager:
    """Gestionnaire de Decision Records"""

    def __init__(self, output_dir: str = "logs/decisions"):
        self.dr_dir = Path(output_dir)
        self.dr_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

        # Clés EdDSA (générer une nouvelle paire au démarrage)
        self.private_key, self.public_key = self._generate_keypair()
        self._save_keys()

    def _generate_keypair(self):
        """Générer une paire de clés EdDSA"""
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        return private_key, public_key

    def _save_keys(self):
        """Sauvegarder les clés (en production, utiliser un vault)"""
        # Sauvegarder la clé privée (chiffrée en production)
        private_pem = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        key_file = Path("provenance/signatures/private_key.pem")
        key_file.parent.mkdir(parents=True, exist_ok=True)

        with open(key_file, "wb") as f:
            f.write(private_pem)

        # Sauvegarder la clé publique
        public_pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        public_key_file = Path("provenance/signatures/public_key.pem")
        with open(public_key_file, "wb") as f:
            f.write(public_pem)

    def create_dr(self, actor: str, task_id: str, decision: str, prompt_hash: str, **kwargs) -> DecisionRecord:
        """
        Créer un nouveau Decision Record

        Returns:
            DecisionRecord signé
        """
        dr = DecisionRecord(actor=actor, task_id=task_id, decision=decision, prompt_hash=prompt_hash, **kwargs)

        # Signer
        dr.sign(self.private_key)

        # Sauvegarder
        self.save_dr(dr)

        return dr

    def create_record(
        self,
        conversation_id: str,
        decision_type: str,
        context: Dict[str, Any],
        rationale: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Créer un Decision Record avec une API simplifiée pour les tests

        Args:
            conversation_id: ID de conversation
            decision_type: Type de décision (e.g., "tool_invocation")
            context: Contexte de la décision
            rationale: Justification de la décision
            metadata: Métadonnées optionnelles

        Returns:
            ID du Decision Record créé
        """
        import base64

        # Générer un ID unique
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        decision_id = f"DR-{conversation_id}-{timestamp}"

        # Construire le record
        record = {
            "decision_id": decision_id,
            "timestamp": datetime.now().isoformat(),
            "conversation_id": conversation_id,
            "decision_type": decision_type,
            "context": context,
            "rationale": rationale,
        }

        if metadata:
            record["metadata"] = metadata

        # Signer le record
        record_bytes = json.dumps(record, sort_keys=True).encode("utf-8")
        signature_bytes = self.private_key.sign(record_bytes)
        public_key_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )

        # Ajouter la signature au record
        record["signature"] = {
            "algorithm": "EdDSA",
            "signature": base64.b64encode(signature_bytes).decode("utf-8"),
            "public_key": base64.b64encode(public_key_bytes).decode("utf-8"),
        }

        # Sauvegarder
        with self._lock:
            filename = f"{decision_id}.json"
            filepath = self.dr_dir / filename

            with open(filepath, "w") as f:
                json.dump(record, f, indent=2)

        return decision_id

    def save_dr(self, dr: DecisionRecord):
        """Sauvegarder un DR dans un fichier JSON"""
        with self._lock:
            filename = f"{dr.dr_id}.json"
            filepath = self.dr_dir / filename

            # Convertir en dict et sauvegarder
            dr_dict = dr.to_dict()
            with open(filepath, "w") as f:
                json.dump(dr_dict, f, indent=2)

    def load_dr(self, dr_id: str) -> Optional[DecisionRecord]:
        """Charger un DR depuis un fichier"""
        filepath = self.dr_dir / f"{dr_id}.json"

        if not filepath.exists():
            return None

        with open(filepath, "r") as f:
            data = json.load(f)

        # Reconstruire le DR
        dr = DecisionRecord(
            actor=data["actor"],
            task_id=data["task_id"],
            decision=data["decision"],
            prompt_hash=data["prompt_hash"].replace("sha256:", ""),
            policy_version=data.get("policy_version", ""),
            model_fingerprint=data.get("model_fingerprint", ""),
            tools_used=data.get("tools_used", []),
            alternatives_considered=data.get("alternatives_considered", []),
            constraints=data.get("constraints", {}),
            expected_risk=data.get("expected_risk", []),
            reasoning_markers=data.get("reasoning_markers", []),
        )
        dr.dr_id = data["dr_id"]
        dr.timestamp = data["ts"]
        dr.signature = data.get("signature")

        return dr


# Instance globale
_dr_manager: Optional[DRManager] = None


def get_dr_manager() -> DRManager:
    """Récupérer l'instance globale du DR manager"""
    global _dr_manager
    if _dr_manager is None:
        _dr_manager = DRManager()
    return _dr_manager


def init_dr_manager(output_dir: str = "logs/decisions") -> DRManager:
    """Initialiser le DR manager"""
    global _dr_manager
    _dr_manager = DRManager(output_dir)
    return _dr_manager
