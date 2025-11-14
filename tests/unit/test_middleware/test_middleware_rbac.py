"""
Comprehensive unit tests for RBAC middleware (Role-Based Access Control)

Tests cover:
- Role and Permission dataclass functionality
- RBACManager initialization and configuration
- Role loading from policies.yaml
- Permission checking and enforcement
- Error handling and edge cases
- Graceful fallbacks
- Compliance with access control requirements
"""

import pytest
from pathlib import Path
import yaml
from dataclasses import dataclass

from runtime.middleware.rbac import (
    Permission,
    Role,
    RBACManager,
    get_rbac_manager,
    init_rbac_manager
)


@pytest.fixture
def temp_config_file(tmp_path):
    """Create temporary config file"""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "policies.yaml"

    config = {
        "policies": {
            "rbac": {
                "roles": [
                    {
                        "name": "admin",
                        "description": "Administrator role",
                        "permissions": [
                            "execute_code",
                            "read_files",
                            "write_files",
                            "manage_users"
                        ]
                    },
                    {
                        "name": "user",
                        "description": "Standard user role",
                        "permissions": [
                            "execute_code",
                            "read_files"
                        ]
                    },
                    {
                        "name": "readonly",
                        "description": "Read-only role",
                        "permissions": [
                            "read_files"
                        ]
                    }
                ]
            }
        }
    }

    with open(config_file, 'w') as f:
        yaml.dump(config, f)

    return config_file


class TestPermissionDataclass:
    """Test Permission dataclass"""

    def test_create_permission(self):
        """Test création d'une permission"""
        perm = Permission(name="read_files", description="Permission to read files")

        assert perm.name == "read_files"
        assert perm.description == "Permission to read files"

    def test_create_permission_without_description(self):
        """Test création sans description"""
        perm = Permission(name="write_files")

        assert perm.name == "write_files"
        assert perm.description == ""


class TestRoleDataclass:
    """Test Role dataclass"""

    def test_create_role(self):
        """Test création d'un rôle"""
        role = Role(
            name="admin",
            permissions=["read", "write", "execute"],
            description="Admin role"
        )

        assert role.name == "admin"
        assert len(role.permissions) == 3
        assert role.description == "Admin role"

    def test_create_role_without_description(self):
        """Test création sans description"""
        role = Role(
            name="user",
            permissions=["read"]
        )

        assert role.name == "user"
        assert role.description == ""

    def test_has_permission_true(self):
        """Test has_permission avec permission présente"""
        role = Role(
            name="admin",
            permissions=["read", "write", "execute"]
        )

        assert role.has_permission("read") is True
        assert role.has_permission("write") is True
        assert role.has_permission("execute") is True

    def test_has_permission_false(self):
        """Test has_permission avec permission absente"""
        role = Role(
            name="user",
            permissions=["read"]
        )

        assert role.has_permission("write") is False
        assert role.has_permission("execute") is False

    def test_has_permission_case_sensitive(self):
        """Test que has_permission est case-sensitive"""
        role = Role(
            name="admin",
            permissions=["read"]
        )

        assert role.has_permission("read") is True
        assert role.has_permission("READ") is False


class TestRBACManagerInitialization:
    """Test RBACManager initialization"""

    def test_basic_initialization(self, temp_config_file):
        """Test initialisation basique"""
        manager = RBACManager(config_path=str(temp_config_file))

        assert manager.config_path == Path(temp_config_file)
        assert isinstance(manager.roles, dict)
        assert isinstance(manager.permissions, dict)

    def test_initialization_with_nonexistent_config(self):
        """Test initialisation avec config inexistant"""
        manager = RBACManager(config_path="/nonexistent/config.yaml")

        # Should initialize without errors
        assert isinstance(manager.roles, dict)
        assert isinstance(manager.permissions, dict)

    def test_roles_loaded_from_config(self, temp_config_file):
        """Test chargement des rôles depuis config"""
        manager = RBACManager(config_path=str(temp_config_file))

        assert "admin" in manager.roles
        assert "user" in manager.roles
        assert "readonly" in manager.roles

    def test_permissions_registered_from_roles(self, temp_config_file):
        """Test enregistrement des permissions depuis les rôles"""
        manager = RBACManager(config_path=str(temp_config_file))

        # Permissions should be registered
        assert "execute_code" in manager.permissions
        assert "read_files" in manager.permissions
        assert "write_files" in manager.permissions
        assert "manage_users" in manager.permissions


class TestRoleRetrieval:
    """Test role retrieval"""

    def test_get_role_existing(self, temp_config_file):
        """Test récupération d'un rôle existant"""
        manager = RBACManager(config_path=str(temp_config_file))

        role = manager.get_role("admin")

        assert role is not None
        assert role.name == "admin"
        assert len(role.permissions) > 0

    def test_get_role_nonexistent(self, temp_config_file):
        """Test récupération d'un rôle inexistant"""
        manager = RBACManager(config_path=str(temp_config_file))

        role = manager.get_role("nonexistent")

        assert role is None

    def test_get_role_returns_correct_permissions(self, temp_config_file):
        """Test que get_role retourne les bonnes permissions"""
        manager = RBACManager(config_path=str(temp_config_file))

        admin_role = manager.get_role("admin")
        user_role = manager.get_role("user")

        assert "manage_users" in admin_role.permissions
        assert "manage_users" not in user_role.permissions


class TestPermissionChecking:
    """Test permission checking"""

    def test_has_permission_true(self, temp_config_file):
        """Test has_permission avec permission présente"""
        manager = RBACManager(config_path=str(temp_config_file))

        assert manager.has_permission("admin", "execute_code") is True
        assert manager.has_permission("admin", "read_files") is True
        assert manager.has_permission("user", "read_files") is True

    def test_has_permission_false(self, temp_config_file):
        """Test has_permission avec permission absente"""
        manager = RBACManager(config_path=str(temp_config_file))

        assert manager.has_permission("user", "write_files") is False
        assert manager.has_permission("readonly", "execute_code") is False

    def test_has_permission_nonexistent_role(self, temp_config_file):
        """Test has_permission avec rôle inexistant"""
        manager = RBACManager(config_path=str(temp_config_file))

        assert manager.has_permission("nonexistent", "read_files") is False

    def test_has_permission_nonexistent_permission(self, temp_config_file):
        """Test has_permission avec permission inexistante"""
        manager = RBACManager(config_path=str(temp_config_file))

        assert manager.has_permission("admin", "nonexistent_permission") is False


class TestRequirePermission:
    """Test require_permission enforcement"""

    def test_require_permission_success(self, temp_config_file):
        """Test require_permission avec permission présente"""
        manager = RBACManager(config_path=str(temp_config_file))

        # Should not raise
        result = manager.require_permission("admin", "execute_code")

        assert result is True

    def test_require_permission_failure(self, temp_config_file):
        """Test require_permission avec permission absente"""
        manager = RBACManager(config_path=str(temp_config_file))

        # Should raise PermissionError
        with pytest.raises(PermissionError) as exc_info:
            manager.require_permission("user", "write_files")

        assert "does not have permission" in str(exc_info.value)

    def test_require_permission_nonexistent_role(self, temp_config_file):
        """Test require_permission avec rôle inexistant"""
        manager = RBACManager(config_path=str(temp_config_file))

        with pytest.raises(PermissionError):
            manager.require_permission("nonexistent", "read_files")

    def test_require_permission_error_message(self, temp_config_file):
        """Test message d'erreur de require_permission"""
        manager = RBACManager(config_path=str(temp_config_file))

        with pytest.raises(PermissionError) as exc_info:
            manager.require_permission("readonly", "write_files")

        error_msg = str(exc_info.value)
        assert "readonly" in error_msg
        assert "write_files" in error_msg


class TestRoleListing:
    """Test role listing functionality"""

    def test_list_roles(self, temp_config_file):
        """Test liste de tous les rôles"""
        manager = RBACManager(config_path=str(temp_config_file))

        roles = manager.list_roles()

        assert isinstance(roles, list)
        assert "admin" in roles
        assert "user" in roles
        assert "readonly" in roles
        assert len(roles) == 3

    def test_list_permissions_for_role(self, temp_config_file):
        """Test liste des permissions d'un rôle"""
        manager = RBACManager(config_path=str(temp_config_file))

        admin_perms = manager.list_permissions("admin")

        assert isinstance(admin_perms, list)
        assert "execute_code" in admin_perms
        assert "read_files" in admin_perms
        assert "write_files" in admin_perms
        assert "manage_users" in admin_perms

    def test_list_permissions_nonexistent_role(self, temp_config_file):
        """Test liste des permissions pour rôle inexistant"""
        manager = RBACManager(config_path=str(temp_config_file))

        perms = manager.list_permissions("nonexistent")

        assert perms == []

    def test_list_permissions_readonly_role(self, temp_config_file):
        """Test liste des permissions pour rôle readonly"""
        manager = RBACManager(config_path=str(temp_config_file))

        perms = manager.list_permissions("readonly")

        assert len(perms) == 1
        assert "read_files" in perms


class TestPermissionHierarchy:
    """Test permission hierarchy and role differences"""

    def test_admin_has_more_permissions_than_user(self, temp_config_file):
        """Test que admin a plus de permissions que user"""
        manager = RBACManager(config_path=str(temp_config_file))

        admin_perms = set(manager.list_permissions("admin"))
        user_perms = set(manager.list_permissions("user"))

        assert len(admin_perms) > len(user_perms)
        assert user_perms.issubset(admin_perms)

    def test_user_has_more_permissions_than_readonly(self, temp_config_file):
        """Test que user a plus de permissions que readonly"""
        manager = RBACManager(config_path=str(temp_config_file))

        user_perms = set(manager.list_permissions("user"))
        readonly_perms = set(manager.list_permissions("readonly"))

        assert len(user_perms) >= len(readonly_perms)
        assert readonly_perms.issubset(user_perms)

    def test_admin_exclusive_permissions(self, temp_config_file):
        """Test permissions exclusives à admin"""
        manager = RBACManager(config_path=str(temp_config_file))

        admin_perms = set(manager.list_permissions("admin"))
        user_perms = set(manager.list_permissions("user"))

        admin_exclusive = admin_perms - user_perms

        assert "write_files" in admin_exclusive
        assert "manage_users" in admin_exclusive


class TestSingletonPattern:
    """Test singleton pattern"""

    def test_get_rbac_manager_returns_singleton(self):
        """Test que get_rbac_manager retourne toujours la même instance"""
        manager1 = get_rbac_manager()
        manager2 = get_rbac_manager()

        assert manager1 is manager2

    def test_init_rbac_manager_creates_new_instance(self, temp_config_file):
        """Test que init_rbac_manager crée une nouvelle instance"""
        manager1 = init_rbac_manager(config_path=str(temp_config_file))
        manager2 = get_rbac_manager()

        assert manager1 is manager2


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_role_with_empty_permissions(self, tmp_path):
        """Test rôle avec liste de permissions vide"""
        config_file = tmp_path / "config" / "policies.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)

        config = {
            "policies": {
                "rbac": {
                    "roles": [
                        {
                            "name": "empty_role",
                            "permissions": []
                        }
                    ]
                }
            }
        }

        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        manager = RBACManager(config_path=str(config_file))

        role = manager.get_role("empty_role")
        assert role is not None
        assert len(role.permissions) == 0

    def test_empty_roles_list(self, tmp_path):
        """Test liste de rôles vide"""
        config_file = tmp_path / "config" / "policies.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)

        config = {
            "policies": {
                "rbac": {
                    "roles": []
                }
            }
        }

        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        manager = RBACManager(config_path=str(config_file))

        assert len(manager.roles) == 0
        assert len(manager.list_roles()) == 0

    def test_role_without_permissions_key(self, tmp_path):
        """Test rôle sans clé permissions"""
        config_file = tmp_path / "config" / "policies.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)

        config = {
            "policies": {
                "rbac": {
                    "roles": [
                        {
                            "name": "incomplete_role"
                        }
                    ]
                }
            }
        }

        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        manager = RBACManager(config_path=str(config_file))

        role = manager.get_role("incomplete_role")
        assert role is not None
        assert role.permissions == []

    def test_duplicate_permissions_in_role(self, tmp_path):
        """Test rôle avec permissions dupliquées"""
        config_file = tmp_path / "config" / "policies.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)

        config = {
            "policies": {
                "rbac": {
                    "roles": [
                        {
                            "name": "duplicate_role",
                            "permissions": ["read", "read", "write"]
                        }
                    ]
                }
            }
        }

        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        manager = RBACManager(config_path=str(config_file))

        role = manager.get_role("duplicate_role")
        # Should handle duplicates
        assert role is not None


class TestGracefulFallbacks:
    """Test graceful fallbacks and error handling"""

    def test_invalid_config_file(self, tmp_path):
        """Test gestion de fichier de config invalide"""
        config_file = tmp_path / "config" / "policies.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)

        # Invalid YAML
        with open(config_file, 'w') as f:
            f.write("{ invalid yaml")

        # Should handle gracefully
        try:
            manager = RBACManager(config_path=str(config_file))
            # Should initialize with no roles
            assert isinstance(manager.roles, dict)
        except yaml.YAMLError:
            # Expected behavior
            pass

    def test_missing_rbac_section(self, tmp_path):
        """Test config sans section RBAC"""
        config_file = tmp_path / "config" / "policies.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)

        config = {
            "policies": {
                "other_section": {}
            }
        }

        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        manager = RBACManager(config_path=str(config_file))

        # Should initialize with no roles
        assert len(manager.roles) == 0

    def test_malformed_role_entry(self, tmp_path):
        """Test gestion d'entrée de rôle mal formée"""
        config_file = tmp_path / "config" / "policies.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)

        config = {
            "policies": {
                "rbac": {
                    "roles": [
                        {
                            "name": "valid_role",
                            "permissions": ["read"]
                        },
                        "invalid_entry"  # Not a dict
                    ]
                }
            }
        }

        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        # Should handle gracefully
        try:
            manager = RBACManager(config_path=str(config_file))
            # Should have loaded valid role
            assert "valid_role" in manager.roles
        except (TypeError, KeyError):
            # Expected behavior
            pass


class TestComplianceRequirements:
    """Test compliance with RBAC requirements"""

    def test_permission_enforcement(self, temp_config_file):
        """Test application des permissions"""
        manager = RBACManager(config_path=str(temp_config_file))

        # Admin should have all permissions
        admin_perms = ["execute_code", "read_files", "write_files", "manage_users"]
        for perm in admin_perms:
            assert manager.has_permission("admin", perm) is True

        # User should have limited permissions
        assert manager.has_permission("user", "execute_code") is True
        assert manager.has_permission("user", "read_files") is True
        assert manager.has_permission("user", "write_files") is False

    def test_role_separation(self, temp_config_file):
        """Test séparation des rôles"""
        manager = RBACManager(config_path=str(temp_config_file))

        admin_role = manager.get_role("admin")
        user_role = manager.get_role("user")
        readonly_role = manager.get_role("readonly")

        # Each role should be distinct
        assert admin_role != user_role
        assert user_role != readonly_role
        assert admin_role != readonly_role

    def test_permission_denied_error_clear(self, temp_config_file):
        """Test que les erreurs de permission sont claires"""
        manager = RBACManager(config_path=str(temp_config_file))

        with pytest.raises(PermissionError) as exc_info:
            manager.require_permission("user", "manage_users")

        error_msg = str(exc_info.value)
        # Error should be clear and actionable
        assert "user" in error_msg.lower()
        assert "manage_users" in error_msg

    def test_all_roles_have_names(self, temp_config_file):
        """Test que tous les rôles ont des noms"""
        manager = RBACManager(config_path=str(temp_config_file))

        for role_name in manager.list_roles():
            role = manager.get_role(role_name)
            assert role.name is not None
            assert len(role.name) > 0

    def test_permissions_registered_correctly(self, temp_config_file):
        """Test enregistrement correct des permissions"""
        manager = RBACManager(config_path=str(temp_config_file))

        # All permissions from all roles should be registered
        expected_permissions = [
            "execute_code", "read_files", "write_files", "manage_users"
        ]

        for perm in expected_permissions:
            assert perm in manager.permissions
