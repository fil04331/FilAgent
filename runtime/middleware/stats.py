# -*- coding: utf-8 -*-
"""
Middleware Statistics Manager

Production-grade metrics system with atomic persistence.
Follows Pro AI Labs standards from docs/metrics_system.py.

Standards Applied:
- StrictInt/StrictFloat for type safety
- Atomic writes (tempfile + shutil.move)
- Audit-first corrupt file recovery
- Pydantic V2 with field_validator
"""
from __future__ import annotations

import json
import shutil
import tempfile
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator


__all__ = [
    "DailyMiddlewareStats",
    "SessionStats",
    "GlobalMiddlewareMetrics",
    "MiddlewareStatsManager",
    "get_stats_manager",
    "reset_stats_manager",
]


# --- CONFIGURATION ---
STATS_FILE = Path("data/middleware_stats.json")


# --- PYDANTIC V2 MODELS (Strictly Typed) ---


class DailyMiddlewareStats(BaseModel):
    """
    Métriques agrégées pour une journée spécifique.
    Strictly typed pour éviter les dérives de données.
    """
    date_ref: str = Field(..., description="Date de référence au format ISO YYYY-MM-DD")
    total_operations: StrictInt = Field(default=0, ge=0)
    total_errors: StrictInt = Field(default=0, ge=0)

    # Per-component breakdown
    logging_ops: StrictInt = Field(default=0, ge=0)
    audit_ops: StrictInt = Field(default=0, ge=0)
    provenance_ops: StrictInt = Field(default=0, ge=0)
    retention_ops: StrictInt = Field(default=0, ge=0)
    rbac_checks: StrictInt = Field(default=0, ge=0)
    pii_scans: StrictInt = Field(default=0, ge=0)
    worm_writes: StrictInt = Field(default=0, ge=0)
    constraints_checks: StrictInt = Field(default=0, ge=0)

    model_config = ConfigDict(frozen=False, validate_assignment=True)


class SessionStats(BaseModel):
    """
    Métriques volatiles de la session en cours.
    Réinitialisées à chaque redémarrage.
    """
    start_time: datetime = Field(default_factory=datetime.now)
    uptime_seconds: float = Field(default=0.0)
    active_middleware: StrictInt = Field(default=0)


class GlobalMiddlewareMetrics(BaseModel):
    """
    Agrégat racine pour la persistance.
    Contient l'historique et l'état actuel.
    """
    last_updated: datetime = Field(default_factory=datetime.now)
    version: str = Field(default="1.0.0")
    history: Dict[str, DailyMiddlewareStats] = Field(default_factory=dict)

    @field_validator('history')
    @classmethod
    def validate_history_keys(
        cls, v: Dict[str, DailyMiddlewareStats]
    ) -> Dict[str, DailyMiddlewareStats]:
        """Vérifie que les clés correspondent au format de date."""
        for key in v.keys():
            try:
                datetime.strptime(key, "%Y-%m-%d")
            except ValueError:
                raise ValueError(f"Clé d'historique invalide: {key}. Format attendu YYYY-MM-DD")
        return v


# --- STATS MANAGER (Atomic Persistence) ---


class MiddlewareStatsManager:
    """
    Gestionnaire de métriques middleware avec persistance atomique.

    Features:
    - Atomic writes (tempfile + shutil.move) to prevent corruption
    - Corrupt file recovery (rename to .corrupt.{timestamp}.json)
    - Singleton pattern via get_stats_manager()
    - Loi 25/PIPEDA compliant (JSON serializable for audit)
    """

    def __init__(self, storage_path: Path = STATS_FILE):
        """
        Initialise le gestionnaire de statistiques.

        Args:
            storage_path: Chemin vers le fichier de persistance JSON.
        """
        self.storage_path = storage_path
        self.session = SessionStats()
        self.data = self._load_or_init()

    def _load_or_init(self) -> GlobalMiddlewareMetrics:
        """
        Charge les données existantes ou initialise une structure vide.

        AUDIT-FIRST: Les fichiers corrompus sont sauvegardés, jamais supprimés.
        """
        if not self.storage_path.exists():
            return GlobalMiddlewareMetrics()

        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            return GlobalMiddlewareMetrics(**raw_data)
        except (json.JSONDecodeError, ValueError) as e:
            # AUDIT-FIRST: Never delete silently - backup for post-mortem analysis
            backup_path = self.storage_path.with_suffix(
                f".corrupt.{datetime.now().timestamp()}.json"
            )
            if self.storage_path.exists():
                shutil.move(str(self.storage_path), str(backup_path))
            print(f"[WARN] Stats corrupted. Moved to {backup_path}. Error: {e}")
            return GlobalMiddlewareMetrics()

    def record_operation(
        self,
        component: str,
        is_error: bool = False,
        persist: bool = True
    ) -> None:
        """
        Enregistre une opération pour un composant middleware.

        Args:
            component: Nom du composant (logging, audit, provenance, etc.)
            is_error: True si l'opération a échoué
            persist: True pour persister immédiatement (défaut)
        """
        today_key = date.today().isoformat()

        # Création du bucket journalier si nécessaire
        if today_key not in self.data.history:
            self.data.history[today_key] = DailyMiddlewareStats(date_ref=today_key)

        daily = self.data.history[today_key]

        # Mise à jour des compteurs globaux
        daily.total_operations += 1
        if is_error:
            daily.total_errors += 1

        # Mise à jour du compteur spécifique au composant
        component_attr_map = {
            'logging': 'logging_ops',
            'audit': 'audit_ops',
            'provenance': 'provenance_ops',
            'retention': 'retention_ops',
            'rbac': 'rbac_checks',
            'pii': 'pii_scans',
            'worm': 'worm_writes',
            'constraints': 'constraints_checks',
        }

        attr = component_attr_map.get(component)
        if attr and hasattr(daily, attr):
            current_value = getattr(daily, attr)
            setattr(daily, attr, current_value + 1)

        self.data.last_updated = datetime.now()

        if persist:
            self._persist()

    def _persist(self) -> None:
        """
        Écriture atomique sur disque.

        Utilise tempfile + shutil.move pour éviter la corruption
        en cas de crash pendant l'écriture.
        """
        # Création du répertoire parent si nécessaire
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Création d'un fichier temporaire dans le même dossier
        temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            dir=self.storage_path.parent,
            delete=False,
            encoding='utf-8',
            suffix='.tmp'
        )

        try:
            # Sérialisation Pydantic V2
            json_str = self.data.model_dump_json(indent=2)
            temp_file.write(json_str)
            temp_file.flush()
            temp_file.close()

            # Remplacement atomique
            shutil.move(temp_file.name, str(self.storage_path))
        except Exception as e:
            # Nettoyage du fichier temporaire en cas d'erreur
            Path(temp_file.name).unlink(missing_ok=True)
            raise RuntimeError(f"Critical: Failed to persist middleware stats. {e}")

    def get_summary(self) -> Dict[str, Any]:
        """
        Retourne un résumé pour l'API/Dashboard.

        Returns:
            Dict avec status, session uptime, stats du jour, et historique.
        """
        today = date.today().isoformat()
        today_stats = self.data.history.get(today, DailyMiddlewareStats(date_ref=today))

        return {
            "status": "healthy",
            "last_updated": self.data.last_updated.isoformat(),
            "session_uptime": (datetime.now() - self.session.start_time).total_seconds(),
            "today": today_stats.model_dump(),
            "days_tracked": len(self.data.history),
        }

    def get_component_stats(self, component: str) -> Dict[str, Any]:
        """
        Retourne les statistiques pour un composant spécifique.

        Args:
            component: Nom du composant middleware.

        Returns:
            Dict avec le nom du composant et ses métriques.
        """
        today = date.today().isoformat()
        today_stats = self.data.history.get(today, DailyMiddlewareStats(date_ref=today))

        component_attr_map = {
            'logging': 'logging_ops',
            'audit': 'audit_ops',
            'provenance': 'provenance_ops',
            'retention': 'retention_ops',
            'rbac': 'rbac_checks',
            'pii': 'pii_scans',
            'worm': 'worm_writes',
            'constraints': 'constraints_checks',
        }

        attr = component_attr_map.get(component, f'{component}_ops')
        ops_count = getattr(today_stats, attr, 0) if hasattr(today_stats, attr) else 0

        return {
            "component": component,
            "operations_today": ops_count,
            "total_operations": today_stats.total_operations,
            "total_errors": today_stats.total_errors,
        }


# --- SINGLETON PATTERN ---

_stats_manager: Optional[MiddlewareStatsManager] = None


def get_stats_manager(storage_path: Optional[Path] = None) -> MiddlewareStatsManager:
    """
    Récupère l'instance globale du gestionnaire de statistiques.

    Args:
        storage_path: Chemin optionnel pour le fichier de persistance.

    Returns:
        Instance singleton de MiddlewareStatsManager.
    """
    global _stats_manager
    if _stats_manager is None:
        if storage_path:
            _stats_manager = MiddlewareStatsManager(storage_path=storage_path)
        else:
            _stats_manager = MiddlewareStatsManager()
    return _stats_manager


def init_stats_manager(storage_path: Path = STATS_FILE) -> MiddlewareStatsManager:
    """
    Initialise ou réinitialise le gestionnaire de statistiques.

    Args:
        storage_path: Chemin vers le fichier de persistance.

    Returns:
        Nouvelle instance de MiddlewareStatsManager.
    """
    global _stats_manager
    _stats_manager = MiddlewareStatsManager(storage_path=storage_path)
    return _stats_manager


def reset_stats_manager() -> None:
    """
    Réinitialise le singleton pour les tests.
    """
    global _stats_manager
    _stats_manager = None
