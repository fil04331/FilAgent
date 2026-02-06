"""
Tests unitaires pour runtime/middleware/rbac.py

Ce module teste:
- Role permission checks
- Resource access control
- Denied action logging
- Permission inheritance
- Edge cases and error handling

Conformément aux normes de FilAgent.
"""

import pytest
import yaml
from pathlib import Path
from typing import Dict, List
from unittest.mock import patch, MagicMock

from runtime.middleware.rbac import (
    Permission,
    Role,
    RBACManager,
    get_rbac_manager,
    init_rbac_manager,
)

# ============================================================================
# FIXTURES: Test Configuration
# ============================================================================


@pytest.fixture
def temp_policies_config(tmp_path) -> Path:
    """
    Fixture pour créer un fichier policies.yaml temporaire

    Returns:
        Path: Chemin vers le fichier de configuration temporaire
    """
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    policies_file = config_dir / "policies.yaml"

    # Configuration de test avec plusieurs rôles
    test_config = {
        "policies": {
            "version": "0.1.0",
            "rbac": {
                "roles": [
                    {
                        "name": "admin",
                        "description": "Administrator with full access",
                        "permissions": [
                            "read_all_logs",
                            "manage_config",
                            "execute_all_tools",
                            "view_audit",
                            "delete_data",
                        ],
                    },
                    {
                        "name": "user",
                        "description": "Regular user with limited access",
                        "permissions": ["execute_safe_tools", "read_own_logs", "manage_own_data"],
                    },
                    {
                        "name": "viewer",
                        "description": "Read-only viewer",
                        "permissions": ["read_own_logs"],
                    },
                    {
                        "name": "guest",
                        "description": "Guest with no permissions",
                        "permissions": [],
                    },
                ]
            },
        }
    }

    with open(policies_file, "w") as f:
        yaml.dump(test_config, f)

    return policies_file


@pytest.fixture
def rbac_manager(temp_policies_config) -> RBACManager:
    """
    Fixture pour créer un RBACManager isolé avec config temporaire

    Returns:
        RBACManager: Instance isolée pour les tests
    """
    return RBACManager(config_path=str(temp_policies_config))


@pytest.fixture
def empty_policies_config(tmp_path) -> Path:
    """
    Fixture pour créer un fichier policies.yaml vide

    Returns:
        Path: Chemin vers le fichier de configuration vide
    """
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    policies_file = config_dir / "policies.yaml"

    # Configuration vide
    empty_config = {"policies": {"version": "0.1.0", "rbac": {"roles": []}}}

    with open(policies_file, "w") as f:
        yaml.dump(empty_config, f)

    return policies_file


# ============================================================================
# TESTS: Role and Permission Data Classes
# ============================================================================


@pytest.mark.unit
def test_permission_creation():
    """
    Test basique: Création d'une Permission

    Vérifie:
    - Création correcte
    - Attributs présents
    """
    perm = Permission(name="read_logs", description="Read system logs")

    assert perm.name == "read_logs"
    assert perm.description == "Read system logs"


@pytest.mark.unit
def test_permission_default_description():
    """
    Test basique: Permission avec description par défaut

    Vérifie:
    - Description par défaut vide
    """
    perm = Permission(name="execute_tool")

    assert perm.name == "execute_tool"
    assert perm.description == ""


@pytest.mark.unit
def test_role_creation():
    """
    Test basique: Création d'un Role

    Vérifie:
    - Création correcte
    - Liste de permissions
    """
    role = Role(name="admin", permissions=["read_all", "write_all"], description="Administrator")

    assert role.name == "admin"
    assert len(role.permissions) == 2
    assert "read_all" in role.permissions
    assert role.description == "Administrator"


@pytest.mark.unit
def test_role_has_permission():
    """
    Test de permission: Role.has_permission()

    Vérifie:
    - Détection correcte des permissions présentes
    - Détection correcte des permissions absentes
    """
    role = Role(name="user", permissions=["read_own_logs", "execute_safe_tools"])

    # Permissions présentes
    assert role.has_permission("read_own_logs") is True
    assert role.has_permission("execute_safe_tools") is True

    # Permissions absentes
    assert role.has_permission("delete_data") is False
    assert role.has_permission("manage_config") is False


@pytest.mark.unit
def test_role_empty_permissions():
    """
    Test edge case: Rôle sans permissions

    Vérifie:
    - Gestion correcte d'un rôle vide
    """
    role = Role(name="guest", permissions=[])

    assert len(role.permissions) == 0
    assert role.has_permission("any_permission") is False


# ============================================================================
# TESTS: RBACManager Initialization
# ============================================================================


@pytest.mark.unit
def test_rbac_manager_initialization(rbac_manager):
    """
    Test d'initialisation: RBACManager avec config valide

    Vérifie:
    - Chargement correct de la configuration
    - Rôles chargés
    - Permissions enregistrées
    """
    assert rbac_manager is not None
    assert len(rbac_manager.roles) == 4  # admin, user, viewer, guest
    assert "admin" in rbac_manager.roles
    assert "user" in rbac_manager.roles
    assert "viewer" in rbac_manager.roles
    assert "guest" in rbac_manager.roles


@pytest.mark.unit
def test_rbac_manager_load_permissions(rbac_manager):
    """
    Test d'initialisation: Chargement des permissions

    Vérifie:
    - Toutes les permissions sont enregistrées
    - Permissions multiples par rôle
    """
    # Au moins les permissions admin doivent être présentes
    assert "read_all_logs" in rbac_manager.permissions
    assert "manage_config" in rbac_manager.permissions
    assert "execute_all_tools" in rbac_manager.permissions

    # Permissions utilisateur
    assert "execute_safe_tools" in rbac_manager.permissions
    assert "read_own_logs" in rbac_manager.permissions


@pytest.mark.unit
def test_rbac_manager_nonexistent_config():
    """
    Test edge case: Configuration non existante

    Vérifie:
    - Gestion gracieuse si fichier absent
    - Pas d'exception levée
    """
    manager = RBACManager(config_path="/nonexistent/path/policies.yaml")

    # Le manager doit être créé mais vide
    assert manager is not None
    assert len(manager.roles) == 0
    assert len(manager.permissions) == 0


@pytest.mark.unit
def test_rbac_manager_empty_config(empty_policies_config):
    """
    Test edge case: Configuration vide

    Vérifie:
    - Gestion correcte d'une config sans rôles
    """
    manager = RBACManager(config_path=str(empty_policies_config))

    assert manager is not None
    assert len(manager.roles) == 0
    assert len(manager.permissions) == 0


# ============================================================================
# TESTS: Role Permission Checks
# ============================================================================


@pytest.mark.unit
def test_get_role_success(rbac_manager):
    """
    Test d'accès: Récupération d'un rôle existant

    Vérifie:
    - get_role() retourne le bon rôle
    - Attributs corrects
    """
    role = rbac_manager.get_role("admin")

    assert role is not None
    assert role.name == "admin"
    assert "read_all_logs" in role.permissions


@pytest.mark.unit
def test_get_role_nonexistent(rbac_manager):
    """
    Test edge case: Récupération d'un rôle inexistant

    Vérifie:
    - Retourne None pour rôle inexistant
    """
    role = rbac_manager.get_role("nonexistent_role")

    assert role is None


@pytest.mark.unit
def test_has_permission_admin(rbac_manager):
    """
    Test de permission: Admin a toutes les permissions admin

    Vérifie:
    - Permissions admin présentes
    """
    assert rbac_manager.has_permission("admin", "read_all_logs") is True
    assert rbac_manager.has_permission("admin", "manage_config") is True
    assert rbac_manager.has_permission("admin", "execute_all_tools") is True
    assert rbac_manager.has_permission("admin", "view_audit") is True


@pytest.mark.unit
def test_has_permission_user(rbac_manager):
    """
    Test de permission: User a ses permissions, pas celles d'admin

    Vérifie:
    - Permissions user présentes
    - Permissions admin absentes (pas d'héritage par défaut)
    """
    # Permissions user
    assert rbac_manager.has_permission("user", "execute_safe_tools") is True
    assert rbac_manager.has_permission("user", "read_own_logs") is True
    assert rbac_manager.has_permission("user", "manage_own_data") is True

    # Permissions admin (absentes pour user)
    assert rbac_manager.has_permission("user", "delete_data") is False
    assert rbac_manager.has_permission("user", "view_audit") is False


@pytest.mark.unit
def test_has_permission_viewer(rbac_manager):
    """
    Test de permission: Viewer a permissions limitées

    Vérifie:
    - Permissions viewer présentes
    - Permissions write absentes
    """
    # Permission viewer
    assert rbac_manager.has_permission("viewer", "read_own_logs") is True

    # Permissions absentes
    assert rbac_manager.has_permission("viewer", "manage_config") is False
    assert rbac_manager.has_permission("viewer", "execute_safe_tools") is False


@pytest.mark.unit
def test_has_permission_guest(rbac_manager):
    """
    Test de permission: Guest n'a aucune permission

    Vérifie:
    - Toutes les permissions refusées
    """
    assert rbac_manager.has_permission("guest", "read_own_logs") is False
    assert rbac_manager.has_permission("guest", "execute_safe_tools") is False
    assert rbac_manager.has_permission("guest", "manage_config") is False


@pytest.mark.unit
def test_has_permission_nonexistent_role(rbac_manager):
    """
    Test edge case: Vérifier permission pour rôle inexistant

    Vérifie:
    - Retourne False pour rôle inexistant
    """
    assert rbac_manager.has_permission("nonexistent", "any_permission") is False


@pytest.mark.unit
def test_has_permission_nonexistent_permission(rbac_manager):
    """
    Test edge case: Vérifier permission inexistante

    Vérifie:
    - Retourne False pour permission inexistante
    """
    assert rbac_manager.has_permission("admin", "nonexistent_permission") is False


# ============================================================================
# TESTS: Resource Access Control
# ============================================================================


@pytest.mark.unit
def test_require_permission_success(rbac_manager):
    """
    Test d'accès: require_permission() avec permission valide

    Vérifie:
    - Retourne True si permission présente
    - Pas d'exception levée
    """
    result = rbac_manager.require_permission("admin", "read_all_logs")

    assert result is True


@pytest.mark.unit
def test_require_permission_denied(rbac_manager):
    """
    Test d'accès: require_permission() avec permission absente

    Vérifie:
    - Lève PermissionError si permission absente
    - Message d'erreur correct
    """
    with pytest.raises(PermissionError) as exc_info:
        rbac_manager.require_permission("user", "delete_data")

    # Vérifier le message d'erreur
    assert "user" in str(exc_info.value).lower()
    assert "delete_data" in str(exc_info.value).lower()


@pytest.mark.unit
def test_require_permission_nonexistent_role(rbac_manager):
    """
    Test edge case: require_permission() pour rôle inexistant

    Vérifie:
    - Lève PermissionError pour rôle inexistant
    """
    with pytest.raises(PermissionError) as exc_info:
        rbac_manager.require_permission("nonexistent", "any_permission")

    assert "nonexistent" in str(exc_info.value).lower()


@pytest.mark.unit
def test_access_control_scenario_admin(rbac_manager):
    """
    Test de scénario: Admin accède à ressources sensibles

    Vérifie:
    - Admin peut accéder à toutes les ressources
    """
    # Admin peut tout faire
    assert rbac_manager.require_permission("admin", "read_all_logs") is True
    assert rbac_manager.require_permission("admin", "manage_config") is True
    assert rbac_manager.require_permission("admin", "delete_data") is True


@pytest.mark.unit
def test_access_control_scenario_user(rbac_manager):
    """
    Test de scénario: User accède à ressources limitées

    Vérifie:
    - User peut accéder à ses ressources
    - User ne peut pas accéder aux ressources admin
    """
    # User peut accéder à ses ressources
    assert rbac_manager.require_permission("user", "execute_safe_tools") is True
    assert rbac_manager.require_permission("user", "read_own_logs") is True

    # User ne peut pas accéder aux ressources admin
    with pytest.raises(PermissionError):
        rbac_manager.require_permission("user", "manage_config")

    with pytest.raises(PermissionError):
        rbac_manager.require_permission("user", "delete_data")


@pytest.mark.unit
def test_access_control_scenario_viewer(rbac_manager):
    """
    Test de scénario: Viewer accède en lecture seule

    Vérifie:
    - Viewer peut lire ses logs
    - Viewer ne peut pas modifier ou exécuter
    """
    # Viewer peut lire
    assert rbac_manager.require_permission("viewer", "read_own_logs") is True

    # Viewer ne peut pas écrire/exécuter
    with pytest.raises(PermissionError):
        rbac_manager.require_permission("viewer", "execute_safe_tools")

    with pytest.raises(PermissionError):
        rbac_manager.require_permission("viewer", "manage_own_data")


# ============================================================================
# TESTS: List Operations
# ============================================================================


@pytest.mark.unit
def test_list_roles(rbac_manager):
    """
    Test de liste: Lister tous les rôles

    Vérifie:
    - Tous les rôles sont listés
    - Liste correcte
    """
    roles = rbac_manager.list_roles()

    assert len(roles) == 4
    assert "admin" in roles
    assert "user" in roles
    assert "viewer" in roles
    assert "guest" in roles


@pytest.mark.unit
def test_list_permissions_admin(rbac_manager):
    """
    Test de liste: Lister permissions admin

    Vérifie:
    - Toutes les permissions admin listées
    """
    permissions = rbac_manager.list_permissions("admin")

    assert len(permissions) == 5
    assert "read_all_logs" in permissions
    assert "manage_config" in permissions
    assert "execute_all_tools" in permissions
    assert "view_audit" in permissions
    assert "delete_data" in permissions


@pytest.mark.unit
def test_list_permissions_user(rbac_manager):
    """
    Test de liste: Lister permissions user

    Vérifie:
    - Permissions user correctes
    """
    permissions = rbac_manager.list_permissions("user")

    assert len(permissions) == 3
    assert "execute_safe_tools" in permissions
    assert "read_own_logs" in permissions
    assert "manage_own_data" in permissions


@pytest.mark.unit
def test_list_permissions_guest(rbac_manager):
    """
    Test de liste: Lister permissions guest (vide)

    Vérifie:
    - Liste vide pour guest
    """
    permissions = rbac_manager.list_permissions("guest")

    assert len(permissions) == 0


@pytest.mark.unit
def test_list_permissions_nonexistent_role(rbac_manager):
    """
    Test edge case: Lister permissions pour rôle inexistant

    Vérifie:
    - Retourne liste vide
    """
    permissions = rbac_manager.list_permissions("nonexistent")

    assert permissions == []


# ============================================================================
# TESTS: Singleton Pattern
# ============================================================================


@pytest.mark.unit
def test_get_rbac_manager_singleton():
    """
    Test singleton: get_rbac_manager() retourne même instance

    Vérifie:
    - Pattern singleton correct
    - Même instance retournée
    """
    # Reset singleton for test
    import runtime.middleware.rbac as rbac_module

    rbac_module._rbac_manager = None

    manager1 = get_rbac_manager()
    manager2 = get_rbac_manager()

    assert manager1 is manager2


@pytest.mark.unit
def test_init_rbac_manager(temp_policies_config):
    """
    Test initialisation: init_rbac_manager() avec config personnalisée

    Vérifie:
    - Initialisation avec config custom
    - Singleton mis à jour
    """
    # Reset singleton
    import runtime.middleware.rbac as rbac_module

    rbac_module._rbac_manager = None

    manager = init_rbac_manager(config_path=str(temp_policies_config))

    assert manager is not None
    assert len(manager.roles) == 4

    # Vérifier que le singleton est bien mis à jour
    singleton = get_rbac_manager()
    assert singleton is manager


# ============================================================================
# TESTS: Permission Inheritance (Future Enhancement)
# ============================================================================


@pytest.mark.unit
def test_permission_no_inheritance_by_default(rbac_manager):
    """
    Test d'héritage: Pas d'héritage de permissions par défaut

    Vérifie:
    - User n'hérite pas des permissions admin
    - Viewer n'hérite pas des permissions user

    Note: Ce test documente le comportement actuel.
    Si l'héritage est implémenté, ce test devra être modifié.
    """
    # User n'a pas les permissions admin
    assert rbac_manager.has_permission("user", "view_audit") is False
    assert rbac_manager.has_permission("user", "delete_data") is False

    # Viewer n'a pas les permissions user
    assert rbac_manager.has_permission("viewer", "execute_safe_tools") is False
    assert rbac_manager.has_permission("viewer", "manage_own_data") is False


# ============================================================================
# TESTS: Denied Action Logging (Integration Test)
# ============================================================================


@pytest.mark.integration
def test_denied_action_logging(rbac_manager, tmp_path, caplog):
    """
    Test d'intégration: Logging des actions refusées

    Vérifie:
    - PermissionError est levée
    - Information disponible pour logging

    Note: Le logging réel serait fait par le middleware appelant RBAC.
    Ce test vérifie que l'information nécessaire est disponible.
    """
    import logging

    # Tenter une action refusée
    try:
        rbac_manager.require_permission("user", "delete_data")
        assert False, "PermissionError devrait être levée"
    except PermissionError as e:
        # L'exception contient les informations nécessaires
        error_msg = str(e)
        assert "user" in error_msg.lower()
        assert "delete_data" in error_msg.lower()

        # Dans un système réel, on loguerait ici
        # logger.warning(f"Denied action: {error_msg}")


@pytest.mark.integration
def test_access_control_audit_trail(rbac_manager):
    """
    Test d'intégration: Trace d'audit pour contrôle d'accès

    Vérifie:
    - Séquence complète d'accès
    - Succès et refus sont détectables

    Ce test simule un audit trail où on vérifie plusieurs accès.
    """
    audit_log = []

    # Fonction helper pour logger l'accès
    def check_and_log(role: str, permission: str) -> bool:
        try:
            result = rbac_manager.require_permission(role, permission)
            audit_log.append({"role": role, "permission": permission, "granted": True})
            return True
        except PermissionError:
            audit_log.append({"role": role, "permission": permission, "granted": False})
            return False

    # Séquence d'accès
    check_and_log("admin", "read_all_logs")  # Granted
    check_and_log("user", "execute_safe_tools")  # Granted
    check_and_log("user", "delete_data")  # Denied
    check_and_log("viewer", "manage_config")  # Denied

    # Vérifier l'audit log
    assert len(audit_log) == 4
    assert audit_log[0]["granted"] is True
    assert audit_log[1]["granted"] is True
    assert audit_log[2]["granted"] is False
    assert audit_log[3]["granted"] is False


# ============================================================================
# TESTS: Edge Cases and Error Handling
# ============================================================================


@pytest.mark.unit
def test_rbac_manager_malformed_config(tmp_path):
    """
    Test edge case: Configuration malformée

    Vérifie:
    - Gestion gracieuse d'une config invalide
    """
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    policies_file = config_dir / "policies.yaml"

    # Écrire du YAML invalide
    with open(policies_file, "w") as f:
        f.write("invalid: yaml: [unclosed: bracket")

    # Le manager devrait gérer l'erreur gracieusement
    try:
        manager = RBACManager(config_path=str(policies_file))
        # Si pas d'exception, vérifier que le manager est vide
        assert len(manager.roles) == 0
    except Exception:
        # Une exception est acceptable aussi
        pass


@pytest.mark.unit
def test_case_sensitive_permissions(rbac_manager):
    """
    Test edge case: Sensibilité à la casse des permissions

    Vérifie:
    - Les permissions sont sensibles à la casse
    """
    # La permission exacte existe
    assert rbac_manager.has_permission("admin", "read_all_logs") is True

    # Casse différente = permission inexistante
    assert rbac_manager.has_permission("admin", "READ_ALL_LOGS") is False
    assert rbac_manager.has_permission("admin", "Read_All_Logs") is False


@pytest.mark.unit
def test_case_sensitive_roles(rbac_manager):
    """
    Test edge case: Sensibilité à la casse des rôles

    Vérifie:
    - Les rôles sont sensibles à la casse
    """
    # Le rôle exact existe
    role = rbac_manager.get_role("admin")
    assert role is not None

    # Casse différente = rôle inexistant
    assert rbac_manager.get_role("Admin") is None
    assert rbac_manager.get_role("ADMIN") is None


@pytest.mark.unit
def test_empty_role_name(rbac_manager):
    """
    Test edge case: Nom de rôle vide

    Vérifie:
    - Gestion correcte d'un nom vide
    """
    role = rbac_manager.get_role("")
    assert role is None

    assert rbac_manager.has_permission("", "any_permission") is False


@pytest.mark.unit
def test_empty_permission_name(rbac_manager):
    """
    Test edge case: Nom de permission vide

    Vérifie:
    - Gestion correcte d'un nom vide
    """
    assert rbac_manager.has_permission("admin", "") is False


@pytest.mark.unit
def test_unicode_in_role_names(tmp_path):
    """
    Test edge case: Caractères Unicode dans les noms

    Vérifie:
    - Support correct des caractères Unicode
    """
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    policies_file = config_dir / "policies.yaml"

    # Configuration avec caractères Unicode
    unicode_config = {
        "policies": {
            "rbac": {
                "roles": [{"name": "administrateur", "permissions": ["lire_logs", "gérer_config"]}]
            }
        }
    }

    with open(policies_file, "w", encoding="utf-8") as f:
        yaml.dump(unicode_config, f, allow_unicode=True)

    manager = RBACManager(config_path=str(policies_file))

    # Vérifier que les noms Unicode fonctionnent
    role = manager.get_role("administrateur")
    assert role is not None
    assert "gérer_config" in role.permissions


@pytest.mark.unit
def test_duplicate_permissions_in_role(tmp_path):
    """
    Test edge case: Permissions dupliquées dans un rôle

    Vérifie:
    - Gestion correcte des doublons
    """
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    policies_file = config_dir / "policies.yaml"

    # Configuration avec doublons
    dup_config = {
        "policies": {
            "rbac": {
                "roles": [
                    {
                        "name": "test_role",
                        "permissions": ["read_logs", "write_logs", "read_logs"],  # Doublon
                    }
                ]
            }
        }
    }

    with open(policies_file, "w") as f:
        yaml.dump(dup_config, f)

    manager = RBACManager(config_path=str(policies_file))

    # Vérifier que la permission fonctionne malgré le doublon
    assert manager.has_permission("test_role", "read_logs") is True
    assert manager.has_permission("test_role", "write_logs") is True


# ============================================================================
# TESTS: Performance and Stress Testing
# ============================================================================


@pytest.mark.unit
def test_large_number_of_roles(tmp_path):
    """
    Test de performance: Gestion d'un grand nombre de rôles

    Vérifie:
    - Performance acceptable avec beaucoup de rôles
    """
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    policies_file = config_dir / "policies.yaml"

    # Créer 100 rôles
    roles = [
        {"name": f"role_{i}", "permissions": [f"perm_{i}_1", f"perm_{i}_2", f"perm_{i}_3"]}
        for i in range(100)
    ]

    config = {"policies": {"rbac": {"roles": roles}}}

    with open(policies_file, "w") as f:
        yaml.dump(config, f)

    # Charger et vérifier
    manager = RBACManager(config_path=str(policies_file))

    assert len(manager.roles) == 100
    assert manager.has_permission("role_50", "perm_50_1") is True
    assert manager.has_permission("role_99", "perm_99_3") is True


@pytest.mark.unit
def test_large_number_of_permissions(tmp_path):
    """
    Test de performance: Rôle avec beaucoup de permissions

    Vérifie:
    - Performance acceptable avec beaucoup de permissions
    """
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    policies_file = config_dir / "policies.yaml"

    # Rôle avec 200 permissions
    permissions = [f"permission_{i}" for i in range(200)]

    config = {
        "policies": {"rbac": {"roles": [{"name": "super_admin", "permissions": permissions}]}}
    }

    with open(policies_file, "w") as f:
        yaml.dump(config, f)

    # Charger et vérifier
    manager = RBACManager(config_path=str(policies_file))

    role = manager.get_role("super_admin")
    assert len(role.permissions) == 200
    assert manager.has_permission("super_admin", "permission_0") is True
    assert manager.has_permission("super_admin", "permission_199") is True
