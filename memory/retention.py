"""
Gestionnaire de rétention des données
Applique les politiques de TTL et de purge automatique
"""

import yaml
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
import shutil
import json


class RetentionPolicy:
    """Politique de rétention pour un type de données"""

    def __init__(self, ttl_days: int, purpose: str):
        self.ttl_days = ttl_days
        self.purpose = purpose

    def is_expired(self, timestamp: str) -> bool:
        """Vérifier si un timestamp est expiré"""
        try:
            ts = datetime.fromisoformat(timestamp)
            cutoff = datetime.now() - timedelta(days=self.ttl_days)
            return ts < cutoff
        except (ValueError, TypeError):
            # Invalid timestamp format or type
            return False


class RetentionManager:
    """
    Gestionnaire de rétention des données
    Applique les politiques de conservation selon config/retention.yaml
    """

    def __init__(self, config_path: str = "config/retention.yaml"):
        self.config_path = Path(config_path)
        self.policies: Dict[str, RetentionPolicy] = {}
        self._load_config()

    def _load_config(self):
        """Charger la configuration de rétention"""
        if not self.config_path.exists():
            print(f"Warning: Retention config not found at {self.config_path}")
            return

        with open(self.config_path, "r") as f:
            config = yaml.safe_load(f)

        retention = config.get("retention", {})
        durations = retention.get("durations", {})

        for data_type, settings in durations.items():
            self.policies[data_type] = RetentionPolicy(
                ttl_days=settings.get("ttl_days", 30), purpose=settings.get("purpose", "No specific purpose")
            )

    def get_ttl_days(self, data_type: str) -> int:
        """Obtenir la TTL en jours pour un type de données"""
        policy = self.policies.get(data_type)
        if policy:
            return policy.ttl_days
        return 30  # Default

    def cleanup_conversations(self) -> int:
        """Nettoyer les vieilles conversations (mémoire épisodique)"""
        from memory.episodic import cleanup_old_conversations

        ttl_days = self.get_ttl_days("conversations")
        deleted = cleanup_old_conversations(ttl_days)

        if deleted > 0:
            print(f"✓ Cleaned up {deleted} old conversations (TTL: {ttl_days} days)")

        return deleted

    def cleanup_events(self) -> int:
        """Nettoyer les vieux événements de log"""
        deleted = 0
        events_dir = Path("logs/events")

        if not events_dir.exists():
            return 0

        ttl_days = self.get_ttl_days("events")
        cutoff_date = datetime.now() - timedelta(days=ttl_days)

        for log_file in events_dir.glob("*.jsonl"):
            # Extraire la date du nom de fichier
            try:
                # Format: events-YYYY-MM-DD.jsonl
                date_str = log_file.stem.replace("events-", "")
                file_date = datetime.strptime(date_str, "%Y-%m-%d")

                if file_date < cutoff_date:
                    log_file.unlink()
                    deleted += 1
                    print(f"  Deleted old log file: {log_file.name}")
            except (ValueError, OSError) as e:
                # Skip files with invalid date format or permission issues
                continue

        if deleted > 0:
            print(f"✓ Cleaned up {deleted} old event logs")

        return deleted

    def cleanup_decisions(self) -> int:
        """Nettoyer les vieux Decision Records"""
        deleted = 0
        decisions_dir = Path("logs/decisions")

        if not decisions_dir.exists():
            return 0

        ttl_days = self.get_ttl_days("decisions")
        cutoff_date = datetime.now() - timedelta(days=ttl_days)

        for dr_file in decisions_dir.glob("DR-*.json"):
            try:
                with open(dr_file, "r") as f:
                    dr = json.load(f)
                    ts_str = dr.get("ts", "")
                    if ts_str:
                        dr_date = datetime.fromisoformat(ts_str)
                        if dr_date < cutoff_date:
                            dr_file.unlink()
                            deleted += 1
                            print(f"  Deleted old DR: {dr_file.name}")
            except (json.JSONDecodeError, ValueError, OSError, KeyError):
                # Skip files with invalid JSON, timestamp format, or permission issues
                continue

        if deleted > 0:
            print(f"✓ Cleaned up {deleted} old decision records (TTL: {ttl_days} days)")

        return deleted

    def cleanup_provenance(self) -> int:
        """Nettoyer les vieilles traces de provenance"""
        deleted = 0
        provenance_dir = Path("logs/traces/otlp")

        if not provenance_dir.exists():
            return 0

        ttl_days = self.get_ttl_days("provenance")
        cutoff_date = datetime.now() - timedelta(days=ttl_days)

        for prov_file in provenance_dir.glob("*.json"):
            try:
                # Vérifier la date de modification du fichier
                file_mtime = datetime.fromtimestamp(prov_file.stat().st_mtime)
                if file_mtime < cutoff_date:
                    prov_file.unlink()
                    deleted += 1
            except (OSError, ValueError):
                # Skip files with permission issues or invalid timestamps
                continue

        if deleted > 0:
            print(f"✓ Cleaned up {deleted} old provenance traces (TTL: {ttl_days} days)")

        return deleted

    def cleanup_old_conversations(self, days: Optional[int] = None) -> int:
        """
        Nettoyer les vieilles conversations avec override de TTL optionnel.

        Cette méthode permet de spécifier explicitement le nombre de jours
        de rétention, contrairement à cleanup_conversations() qui utilise
        la configuration.

        Args:
            days: TTL en jours. Si None, utilise la valeur de config.

        Returns:
            Nombre de conversations supprimées.
        """
        from memory.episodic import cleanup_old_conversations as _cleanup_conversations

        ttl = days if days is not None else self.get_ttl_days("conversations")
        deleted = _cleanup_conversations(ttl)

        # Record to central stats manager
        try:
            from runtime.middleware.stats import get_stats_manager

            get_stats_manager().record_operation("retention")
        except ImportError:
            pass

        if deleted > 0:
            print(f"✓ Cleaned up {deleted} old conversations (TTL: {ttl} days)")

        return deleted

    def cleanup_semantic_passages(self, days: Optional[int] = None) -> int:
        """
        Nettoyer les passages de mémoire sémantique.

        Args:
            days: TTL en jours. Si None, utilise la valeur de config (ou 30 par défaut).

        Returns:
            Nombre de passages supprimés.
        """
        ttl = days if days is not None else self.get_ttl_days("semantic")

        try:
            from memory.semantic import get_semantic_memory

            mem = get_semantic_memory()
            if mem and hasattr(mem, "cleanup_old_passages"):
                deleted = mem.cleanup_old_passages(ttl)
                if deleted > 0:
                    print(f"✓ Cleaned up {deleted} old semantic passages (TTL: {ttl} days)")
                return deleted
        except (ImportError, AttributeError):
            pass

        return 0

    def get_retention_stats(self) -> Dict[str, Any]:
        """
        Retourne les statistiques de rétention pour audit/monitoring.

        Conforme Loi 25/PIPEDA - toutes les données sont sérialisables JSON.

        Returns:
            Dict avec les TTL configurés, nombre de politiques, et stats globales.
        """
        # Get global stats from central manager if available
        global_stats: Dict[str, Any] = {}
        try:
            from runtime.middleware.stats import get_stats_manager

            global_stats = get_stats_manager().get_summary()
        except ImportError:
            global_stats = {"status": "stats_manager_unavailable"}

        return {
            "conversations_ttl_days": self.get_ttl_days("conversations"),
            "events_ttl_days": self.get_ttl_days("events"),
            "decisions_ttl_days": self.get_ttl_days("decisions"),
            "provenance_ttl_days": self.get_ttl_days("provenance"),
            "semantic_ttl_days": self.get_ttl_days("semantic"),
            "policies_count": len(self.policies),
            "policies": {k: {"ttl_days": v.ttl_days, "purpose": v.purpose} for k, v in self.policies.items()},
            "global_stats": global_stats,
        }

    def run_cleanup(self, dry_run: bool = False) -> Dict[str, int]:
        """
        Exécuter le nettoyage complet selon les politiques

        Args:
            dry_run: Si True, simuler sans supprimer

        Returns:
            Dict avec le nombre d'éléments supprimés par type
        """
        results: Dict[str, int] = {
            "conversations": 0,
            "events": 0,
            "decisions": 0,
            "provenance": 0,
            "semantic": 0,
        }

        if dry_run:
            print("🔍 DRY RUN: Simulation du nettoyage")
            return results

        print("🧹 Running retention cleanup...")

        # Nettoyer chaque type de données
        results["conversations"] = self.cleanup_conversations()
        results["events"] = self.cleanup_events()
        results["decisions"] = self.cleanup_decisions()
        results["provenance"] = self.cleanup_provenance()
        results["semantic"] = self.cleanup_semantic_passages()

        total = sum(results.values())
        print(f"✓ Cleanup complete: {total} items removed")

        return results


# Instance globale
_retention_manager: Optional[RetentionManager] = None


def get_retention_manager() -> RetentionManager:
    """Récupérer l'instance globale du gestionnaire de rétention"""
    global _retention_manager
    if _retention_manager is None:
        _retention_manager = RetentionManager()
    return _retention_manager


def init_retention_manager(config_path: str = "config/retention.yaml") -> RetentionManager:
    """Initialiser le gestionnaire de rétention"""
    global _retention_manager
    _retention_manager = RetentionManager(config_path)
    return _retention_manager
