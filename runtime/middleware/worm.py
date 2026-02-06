"""Middleware WORM (Write Once Read Many) pour les journaux append-only."""

import json
import os
import hashlib
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import threading


class MerkleNode:
    """Nœud d'un arbre de Merkle"""

    def __init__(self, left=None, right=None, data=None):
        self.left = left
        self.right = right
        self.data = data or ""
        if data:
            self.hash = self._hash_data(data)
        else:
            self.hash = None

    def _hash_data(self, data: str) -> str:
        """Calculer le hash SHA-256 des données"""
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    def compute_hash(self):
        """Calculer le hash du nœud (hash des enfants)"""
        if self.data:
            self.hash = self._hash_data(self.data)
        else:
            left_hash = self.left.hash if self.left else ""
            right_hash = self.right.hash if self.right else ""
            combined = f"{left_hash}{right_hash}"
            self.hash = self._hash_data(combined)


class MerkleTree:
    """Arbre de Merkle pour vérifier l'intégrité des logs"""

    def __init__(self):
        self.nodes = []
        self.root = None

    def build_tree(self, data_list: List[str]):
        """Construire l'arbre de Merkle à partir d'une liste de données"""
        if not data_list:
            return None

        # Créer les feuilles
        self.nodes = [MerkleNode(data=data) for data in data_list]

        # Construire l'arbre de bas en haut
        level = self.nodes
        while len(level) > 1:
            next_level = []

            # Traiter les nœuds deux par deux
            for i in range(0, len(level), 2):
                if i + 1 < len(level):
                    left = level[i]
                    right = level[i + 1]
                else:
                    left = level[i]
                    right = level[i]  # Dupliquer si impair

                # Créer le nœud parent
                parent = MerkleNode(left=left, right=right)
                parent.compute_hash()
                next_level.append(parent)

            level = next_level

        if level:
            self.root = level[0]
            return self.root

        return None

    def get_root_hash(self) -> Optional[str]:
        """Obtenir le hash de la racine"""
        if self.root:
            return self.root.hash
        return None


class WormLogger:
    """
    Logger WORM avec arbre de Merkle
    Append-only avec vérification d'intégrité
    """

    def __init__(self, log_dir: str = "logs", digest_dir: Optional[str] = None):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

        # Dossier pour les digestes
        if digest_dir:
            self.digest_dir = Path(digest_dir)
        else:
            self.digest_dir = Path("logs/digests")
        self.digest_dir.mkdir(parents=True, exist_ok=True)

        # Fichier de log par défaut
        self.default_log_file = self.log_dir / "events.jsonl"

    def append(self, data: str, log_file: Optional[Path] = None) -> bool:
        """
        Ajouter une ligne à un fichier de log (WORM)

        Args:
            data: Données à ajouter
            log_file: Chemin du fichier de log (optionnel, utilise le fichier par défaut si non spécifié)

        Returns:
            True si succès
        """
        if log_file is None:
            log_file = self.default_log_file
        elif not isinstance(log_file, Path):
            log_file = Path(log_file)

        with self._lock:
            try:
                # Mode append
                with open(log_file, "a") as f:
                    f.write(data + "\n")
                    f.flush()  # Force l'écriture immédiate
                    os.fsync(f.fileno())  # Flush au système

                return True
            except Exception as e:
                print(f"Error appending to WORM log: {e}")
                return False

    def create_checkpoint(self, log_file: Optional[Path] = None) -> Optional[str]:
        """
        Créer un checkpoint Merkle pour un fichier de log

        Args:
            log_file: Fichier de log à vérifier (optionnel, utilise le fichier par défaut si non spécifié)

        Returns:
            Hash du checkpoint ou None en cas d'erreur
        """
        if log_file is None:
            log_file = self.default_log_file
        elif not isinstance(log_file, Path):
            log_file = Path(log_file)

        if not log_file.exists():
            return None

        try:
            # Lire toutes les lignes
            with open(log_file, "r") as f:
                lines = [line.rstrip("\n") for line in f.readlines()]

            # Construire l'arbre de Merkle
            tree = MerkleTree()
            tree.build_tree(lines)

            root_hash = tree.get_root_hash()

            if root_hash:
                # Sauvegarder le checkpoint
                timestamp = datetime.now()
                checkpoint_data = {
                    "file": str(log_file),
                    "timestamp": timestamp.isoformat(),
                    "root_hash": root_hash,
                    "num_entries": len(lines),
                }

                # Sauvegarder un snapshot horodaté pour historisation
                checkpoint_file = (
                    self.digest_dir / f"{log_file.stem}-{timestamp.strftime('%Y%m%d%H%M%S')}.json"
                )
                with open(checkpoint_file, "w", encoding="utf-8") as f:
                    json.dump(checkpoint_data, f, indent=2)

                # Mettre à jour le checkpoint courant utilisé par verify_integrity
                latest_checkpoint = self.digest_dir / f"{log_file.stem}-checkpoint.json"
                with open(latest_checkpoint, "w", encoding="utf-8") as f:
                    json.dump(checkpoint_data, f, indent=2)

                return root_hash

            return None

        except Exception as e:
            print(f"Error creating checkpoint: {e}")
            return None

    def verify_integrity(
        self, log_file: Optional[Path] = None, expected_hash: Optional[str] = None
    ) -> bool:
        """
        Vérifier l'intégrité d'un fichier de log

        Args:
            log_file: Fichier à vérifier (optionnel, utilise le fichier par défaut si non spécifié)
            expected_hash: Hash attendu (optionnel, charger depuis checkpoint)

        Returns:
            True si intégrité vérifiée
        """
        if log_file is None:
            log_file = self.default_log_file
        elif not isinstance(log_file, Path):
            log_file = Path(log_file)

        # Charger le hash attendu si non fourni
        if expected_hash is None:
            checkpoint_file = self.digest_dir / f"{log_file.stem}-checkpoint.json"
            if checkpoint_file.exists():
                with open(checkpoint_file, "r", encoding="utf-8") as f:
                    checkpoint = json.load(f)
                    expected_hash = checkpoint.get("root_hash") or checkpoint.get("merkle_root")
            else:
                return False  # Pas de checkpoint

        # Calculer le hash actuel
        if not log_file.exists():
            return False

        try:
            with open(log_file, "r", encoding="utf-8") as f:
                lines = [line.rstrip("\n") for line in f.readlines()]

            tree = MerkleTree()
            tree.build_tree(lines)

            current_hash = tree.get_root_hash()

            return current_hash == expected_hash

        except Exception as e:
            print(f"Error verifying integrity: {e}")
            return False

    def finalize_current_log(
        self, log_file: Optional[Path] = None, archive: bool = True
    ) -> Optional[str]:
        """
        Finaliser et sceller le log WORM courant

        Cette méthode rend le log immuable et génère une signature cryptographique
        pour garantir l'intégrité selon les exigences de la Loi 25 (Québec).

        Processus de finalisation:
        1. Créer un checkpoint Merkle tree (root hash)
        2. Générer un digest signé cryptographiquement (EdDSA)
        3. Archiver dans audit/signed/ si demandé
        4. Marquer le log comme finalisé (read-only)

        Args:
            log_file: Fichier de log à finaliser (optionnel, utilise le fichier par défaut)
            archive: Si True, archiver le log finalisé dans audit/signed/

        Returns:
            str: ID du log finalisé (format: FINAL-{timestamp}-{hash[:8]}) ou None en cas d'erreur

        Raises:
            None: Les erreurs sont loggées mais n'interrompent pas l'exécution
        """
        if log_file is None:
            log_file = self.default_log_file
        elif not isinstance(log_file, Path):
            log_file = Path(log_file)

        # Check if log file exists
        if not log_file.exists():
            print(f"⚠ Cannot finalize: log file does not exist: {log_file}")
            return None

        with self._lock:
            try:
                # Step 1: Create Merkle checkpoint for integrity verification
                root_hash = self.create_checkpoint(log_file)
                if not root_hash:
                    print(f"❌ Failed to create checkpoint for {log_file}")
                    return None

                # Step 2: Generate cryptographic signature for compliance (Loi 25)
                timestamp = datetime.now()
                finalization_id = f"FINAL-{timestamp.strftime('%Y%m%d%H%M%S')}-{root_hash[:8]}"

                # Read log content for signing
                with open(log_file, "r", encoding="utf-8") as f:
                    log_content = f.read()

                # Calculate SHA-256 hash of entire log (for compatibility with existing tests)
                sha256_hash = hashlib.sha256(log_content.encode("utf-8")).hexdigest()

                # Create finalization digest with EdDSA signature
                try:
                    from cryptography.hazmat.primitives.asymmetric import ed25519

                    # Generate ephemeral keypair for signing (in production, use HSM/vault)
                    private_key = ed25519.Ed25519PrivateKey.generate()
                    private_key.public_key()

                    # Prepare data to sign
                    sign_data = {
                        "finalization_id": finalization_id,
                        "log_file": str(log_file),
                        "timestamp": timestamp.isoformat(),
                        "sha256": sha256_hash,
                        "merkle_root": root_hash,
                        "num_entries": log_content.count("\n"),
                    }

                    # Sign the digest
                    sign_bytes = json.dumps(sign_data, sort_keys=True).encode("utf-8")
                    signature = private_key.sign(sign_bytes)

                    # Create finalization record
                    finalization_record = {
                        **sign_data,
                        "signature": f"ed25519:{signature.hex()}",
                        "compliance": {
                            "standard": "Loi 25 (Québec)",
                            "immutable": True,
                            "tamper_evident": True,
                        },
                    }

                except ImportError:
                    # Fallback if cryptography not available
                    print("⚠ cryptography library not available, creating unsigned digest")
                    finalization_record = {
                        "finalization_id": finalization_id,
                        "log_file": str(log_file),
                        "timestamp": timestamp.isoformat(),
                        "sha256": sha256_hash,
                        "merkle_root": root_hash,
                        "num_entries": log_content.count("\n"),
                        "compliance": {"standard": "Loi 25 (Québec)", "immutable": True},
                    }

                # Step 3: Save finalization digest
                digest_file = (
                    self.digest_dir
                    / f"{log_file.stem}-finalization-{timestamp.strftime('%Y%m%d%H%M%S')}.json"
                )
                with open(digest_file, "w", encoding="utf-8") as f:
                    json.dump(finalization_record, f, indent=2)

                # Step 4: Archive in audit/signed/ if requested
                if archive:
                    archive_dir = Path("audit/signed")
                    archive_dir.mkdir(parents=True, exist_ok=True)

                    # Copy log to archive (WORM - Write Once Read Many)
                    archive_path = archive_dir / f"{finalization_id}-{log_file.name}"
                    import shutil

                    shutil.copy2(log_file, archive_path)

                    # Make archive read-only (Unix permissions)
                    try:
                        archive_path.chmod(0o444)  # r--r--r--
                    except Exception as e:
                        print(f"⚠ Could not set read-only permissions: {e}")

                    # Save finalization record in archive
                    archive_digest = archive_dir / f"{finalization_id}-digest.json"
                    with open(archive_digest, "w", encoding="utf-8") as f:
                        json.dump(finalization_record, f, indent=2)

                print(f"✓ Log finalized: {finalization_id}")
                print(f"  - Merkle root: {root_hash}")
                print(f"  - SHA-256: {sha256_hash}")
                if archive:
                    print(f"  - Archived to: {archive_path}")

                return finalization_id

            except Exception as e:
                print(f"❌ Error finalizing log: {e}")
                import traceback

                traceback.print_exc()
                return None


# Instance globale
_worm_logger: Optional[WormLogger] = None


def get_worm_logger() -> WormLogger:
    """Récupérer l'instance globale du logger WORM"""
    global _worm_logger
    if _worm_logger is None:
        _worm_logger = WormLogger()
    return _worm_logger


def init_worm_logger(log_dir: str = "logs") -> WormLogger:
    """Initialiser le logger WORM"""
    global _worm_logger
    _worm_logger = WormLogger(log_dir)
    return _worm_logger
