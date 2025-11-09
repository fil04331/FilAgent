"""
Policy Loader - Chargement et validation des politiques HTN

Implémente:
- Chargement des politiques depuis config/policies.yaml
- Validation des actions contre blocked_actions
- Validation des limites d'exécution
- Cache des politiques pour performance

Conformité:
- Loi 25: Traçabilité des politiques appliquées
- AI Act: Transparence des restrictions
- NIST AI RMF: Gestion des risques via politiques
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set
from pathlib import Path
import yaml
import threading
from datetime import datetime


@dataclass
class HTNPolicies:
    """
    Politiques HTN chargées depuis la configuration

    Attributes:
        max_tasks_per_plan: Nombre maximum de tâches par plan
        max_execution_time_sec: Temps d'exécution maximum (secondes)
        allowed_actions: Liste des actions autorisées
        blocked_actions: Liste des actions interdites
        retry_policies: Configuration des retry
    """
    max_tasks_per_plan: int = 50
    max_execution_time_sec: int = 300
    allowed_actions: List[str] = field(default_factory=list)
    blocked_actions: List[str] = field(default_factory=list)
    retry_policies: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Sérialise pour logging"""
        return {
            "max_tasks_per_plan": self.max_tasks_per_plan,
            "max_execution_time_sec": self.max_execution_time_sec,
            "allowed_actions": self.allowed_actions,
            "blocked_actions": self.blocked_actions,
            "retry_policies": self.retry_policies,
        }


class PolicyValidationError(Exception):
    """Erreur de validation de politique"""
    pass


class PolicyLoader:
    """
    Chargeur de politiques HTN

    Responsabilités:
        - Charger les politiques depuis config/policies.yaml
        - Valider les actions contre les politiques
        - Fournir un cache pour performance
        - Tracer les violations de politiques

    Usage:
        loader = PolicyLoader()
        policies = loader.load_policies()
        loader.validate_action("read_file")  # OK
        loader.validate_action("delete_system_file")  # Raises PolicyValidationError
    """

    def __init__(self, config_path: str = "config/policies.yaml"):
        """
        Initialise le chargeur de politiques

        Args:
            config_path: Chemin vers le fichier de configuration
        """
        self.config_path = config_path
        self._policies_cache: Optional[HTNPolicies] = None
        self._cache_timestamp: Optional[datetime] = None

    def load_policies(self, force_reload: bool = False) -> HTNPolicies:
        """
        Charge les politiques HTN depuis la configuration

        Args:
            force_reload: Force le rechargement même si en cache

        Returns:
            HTNPolicies avec les politiques chargées

        Raises:
            FileNotFoundError: Si le fichier de configuration n'existe pas
            ValueError: Si la configuration est invalide
        """
        # Utiliser le cache si disponible et pas de force reload
        if not force_reload and self._policies_cache is not None:
            return self._policies_cache

        config_path = Path(self.config_path)
        if not config_path.exists():
            # Retourner des politiques par défaut si le fichier n'existe pas
            return HTNPolicies()

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            # Extraire les politiques HTN
            htn_policies_config = config.get('htn_policies', {})

            policies = HTNPolicies(
                max_tasks_per_plan=htn_policies_config.get('max_tasks_per_plan', 50),
                max_execution_time_sec=htn_policies_config.get('max_execution_time_sec', 300),
                allowed_actions=htn_policies_config.get('allowed_actions', []),
                blocked_actions=htn_policies_config.get('blocked_actions', []),
                retry_policies=htn_policies_config.get('retry_policies', {}),
            )

            # Mettre en cache
            self._policies_cache = policies
            self._cache_timestamp = datetime.utcnow()

            return policies

        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {config_path}: {str(e)}") from e
        except Exception as e:
            raise ValueError(f"Failed to load policies from {config_path}: {str(e)}") from e

    def validate_action(self, action: str) -> None:
        """
        Valide qu'une action est autorisée selon les politiques

        Args:
            action: Nom de l'action à valider

        Raises:
            PolicyValidationError: Si l'action est interdite
        """
        policies = self.load_policies()

        # Vérifier si l'action est dans la liste des actions bloquées
        if action in policies.blocked_actions:
            raise PolicyValidationError(
                f"Action '{action}' is forbidden by policy (blocked_actions)"
            )

        # Si allowed_actions est défini et non vide, vérifier que l'action y est
        if policies.allowed_actions and action not in policies.allowed_actions:
            # Autoriser generic_execute comme action de fallback
            if action != "generic_execute":
                raise PolicyValidationError(
                    f"Action '{action}' is not in allowed_actions list"
                )

    def validate_plan(self, task_count: int, actions: List[str]) -> None:
        """
        Valide un plan complet contre les politiques

        Args:
            task_count: Nombre de tâches dans le plan
            actions: Liste des actions utilisées dans le plan

        Raises:
            PolicyValidationError: Si le plan viole les politiques
        """
        policies = self.load_policies()

        # Vérifier le nombre de tâches
        if task_count > policies.max_tasks_per_plan:
            raise PolicyValidationError(
                f"Plan exceeds maximum tasks: {task_count} > {policies.max_tasks_per_plan}"
            )

        # Valider chaque action
        for action in set(actions):
            self.validate_action(action)

    def get_blocked_actions(self) -> Set[str]:
        """
        Retourne l'ensemble des actions interdites

        Returns:
            Set contenant les noms des actions interdites
        """
        policies = self.load_policies()
        return set(policies.blocked_actions)

    def get_allowed_actions(self) -> List[str]:
        """
        Retourne la liste des actions autorisées

        Returns:
            Liste des actions autorisées (vide si toutes autorisées)
        """
        policies = self.load_policies()
        return policies.allowed_actions.copy()

    def is_action_allowed(self, action: str) -> bool:
        """
        Vérifie si une action est autorisée (sans lever d'exception)

        Args:
            action: Nom de l'action

        Returns:
            True si l'action est autorisée, False sinon
        """
        try:
            self.validate_action(action)
            return True
        except PolicyValidationError:
            return False


# Instance globale pour singleton pattern
_policy_loader: Optional[PolicyLoader] = None
_policy_loader_lock = threading.Lock()


def get_policy_loader(config_path: str = "config/policies.yaml") -> PolicyLoader:
    """
    Récupère l'instance globale du PolicyLoader (singleton)

    Args:
        config_path: Chemin vers le fichier de configuration

    Returns:
        Instance du PolicyLoader
    """
    global _policy_loader
    if _policy_loader is None:
        with _policy_loader_lock:
            if _policy_loader is None:
                _policy_loader = PolicyLoader(config_path)
    return _policy_loader


def init_policy_loader(config_path: str = "config/policies.yaml") -> PolicyLoader:
    """
    Initialise et retourne une nouvelle instance du PolicyLoader

    Args:
        config_path: Chemin vers le fichier de configuration

    Returns:
        Nouvelle instance du PolicyLoader
    """
    global _policy_loader
    _policy_loader = PolicyLoader(config_path)
    return _policy_loader
