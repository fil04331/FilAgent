"""
Middleware RBAC (Role-Based Access Control)
Gestion des rôles et permissions selon config/policies.yaml
"""

import yaml
from typing import Dict, List, Optional
from pathlib import Path
from dataclasses import dataclass


@dataclass
class Permission:
    """Permission"""

    name: str
    description: str = ""


@dataclass
class Role:
    """Rôle avec permissions"""

    name: str
    permissions: List[str]
    description: str = ""

    def has_permission(self, permission: str) -> bool:
        """Vérifier si le rôle a une permission"""
        return permission in self.permissions


class RBACManager:
    """
    Gestionnaire RBAC
    Gère les rôles, permissions et vérifications d'accès
    """

    def __init__(self, config_path: str = "config/policies.yaml"):
        self.config_path = Path(config_path)
        self.roles: Dict[str, Role] = {}
        self.permissions: Dict[str, Permission] = {}

        self._load_config()

    def _load_config(self):
        """Charger la configuration depuis policies.yaml"""
        if not self.config_path.exists():
            return

        with open(self.config_path, "r") as f:
            config = yaml.safe_load(f)

        policies = config.get("policies", {})
        rbac_config = policies.get("rbac", {})

        # Charger les rôles
        roles_config = rbac_config.get("roles", [])
        for role_config in roles_config:
            role = Role(
                name=role_config["name"],
                permissions=role_config.get("permissions", []),
                description=role_config.get("description", ""),
            )
            self.roles[role.name] = role

            # Enregistrer les permissions
            for perm in role.permissions:
                if perm not in self.permissions:
                    self.permissions[perm] = Permission(name=perm, description=f"Permission for {perm}")

    def get_role(self, role_name: str) -> Optional[Role]:
        """Récupérer un rôle par nom"""
        return self.roles.get(role_name)

    def has_permission(self, role_name: str, permission: str) -> bool:
        """
        Vérifier si un rôle a une permission

        Args:
            role_name: Nom du rôle
            permission: Nom de la permission

        Returns:
            True si le rôle a la permission
        """
        role = self.get_role(role_name)
        if not role:
            return False
        return role.has_permission(permission)

    def require_permission(self, role_name: str, permission: str) -> bool:
        """
        Exiger une permission (lève une exception si absente)

        Returns:
            True si la permission est présente

        Raises:
            PermissionError si la permission est absente
        """
        if not self.has_permission(role_name, permission):
            raise PermissionError(f"Role '{role_name}' does not have permission '{permission}'")
        return True

    def list_roles(self) -> List[str]:
        """Lister tous les rôles"""
        return list(self.roles.keys())

    def list_permissions(self, role_name: str) -> List[str]:
        """Lister les permissions d'un rôle"""
        role = self.get_role(role_name)
        if not role:
            return []
        return role.permissions


# Instance globale
_rbac_manager: Optional[RBACManager] = None


def get_rbac_manager() -> RBACManager:
    """Récupérer l'instance globale"""
    global _rbac_manager
    if _rbac_manager is None:
        _rbac_manager = RBACManager()
    return _rbac_manager


def init_rbac_manager(config_path: str = "config/policies.yaml") -> RBACManager:
    """Initialiser le gestionnaire RBAC"""
    global _rbac_manager
    _rbac_manager = RBACManager(config_path)
    return _rbac_manager
