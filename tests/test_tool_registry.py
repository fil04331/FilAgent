"""
Tests pour le registre d'outils (tools/registry.py)

Tests de:
- Enregistrement d'outils
- Recherche d'outils
- Gestion des doublons
- Validation des schémas
- Sérialisation du registre
"""

import pytest
import sys
from pathlib import Path
from typing import Dict, Any, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.registry import ToolRegistry, get_registry, reload_registry
from tools.base import BaseTool, ToolResult, ToolStatus
from tools.calculator import CalculatorTool
from tools.python_sandbox import PythonSandboxTool
from tools.file_reader import FileReaderTool

# ============================================================================
# Mock Tools for Testing
# ============================================================================


class MockTool(BaseTool):
    """Outil mock pour les tests"""

    def __init__(self, name: str = "mock_tool", description: str = "Mock tool for testing"):
        super().__init__(name=name, description=description)

    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """Exécution mock"""
        return ToolResult(
            status=ToolStatus.SUCCESS, output=f"Mock execution with args: {arguments}"
        )

    def validate_arguments(self, arguments: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validation mock - accepte tout"""
        return True, None

    def _get_parameters_schema(self) -> Dict[str, Any]:
        """Schéma mock"""
        return {
            "type": "object",
            "properties": {"param": {"type": "string", "description": "Test parameter"}},
            "required": ["param"],
        }


class CustomToolA(BaseTool):
    """Outil custom A pour tester les multiples outils"""

    def __init__(self):
        super().__init__(name="custom_tool_a", description="Custom tool A")

    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        return ToolResult(status=ToolStatus.SUCCESS, output="Tool A output")

    def validate_arguments(self, arguments: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        return True, None

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}}


class CustomToolB(BaseTool):
    """Outil custom B pour tester les multiples outils"""

    def __init__(self):
        super().__init__(name="custom_tool_b", description="Custom tool B")

    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        return ToolResult(status=ToolStatus.SUCCESS, output="Tool B output")

    def validate_arguments(self, arguments: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        return True, None

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}}


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def empty_registry():
    """Fixture pour un registre vide (sans outils par défaut)"""
    registry = ToolRegistry.__new__(ToolRegistry)
    registry._tools = {}
    return registry


@pytest.fixture
def registry_with_mock():
    """Fixture pour un registre avec un outil mock"""
    registry = ToolRegistry.__new__(ToolRegistry)
    registry._tools = {}
    mock_tool = MockTool()
    registry.register(mock_tool)
    return registry


# ============================================================================
# Tests: Enregistrement d'outils
# ============================================================================


@pytest.mark.unit
def test_register_single_tool(empty_registry):
    """Test enregistrement d'un seul outil"""
    tool = MockTool(name="test_tool", description="Test tool")

    # Enregistrer l'outil
    empty_registry.register(tool)

    # Vérifier qu'il est dans le registre
    assert "test_tool" in empty_registry._tools
    assert empty_registry._tools["test_tool"] is tool


@pytest.mark.unit
def test_register_multiple_tools(empty_registry):
    """Test enregistrement de plusieurs outils"""
    tool_a = CustomToolA()
    tool_b = CustomToolB()

    # Enregistrer les outils
    empty_registry.register(tool_a)
    empty_registry.register(tool_b)

    # Vérifier qu'ils sont tous dans le registre
    assert len(empty_registry._tools) == 2
    assert "custom_tool_a" in empty_registry._tools
    assert "custom_tool_b" in empty_registry._tools


@pytest.mark.unit
def test_register_duplicate_tool_overwrites(empty_registry):
    """Test que l'enregistrement d'un outil dupliqué écrase l'ancien"""
    tool_v1 = MockTool(name="same_name", description="Version 1")
    tool_v2 = MockTool(name="same_name", description="Version 2")

    # Enregistrer la première version
    empty_registry.register(tool_v1)
    assert empty_registry._tools["same_name"].description == "Version 1"

    # Enregistrer la deuxième version (doit écraser)
    empty_registry.register(tool_v2)
    assert empty_registry._tools["same_name"].description == "Version 2"
    assert empty_registry._tools["same_name"] is tool_v2

    # Vérifier qu'il n'y a qu'une seule instance
    assert len(empty_registry._tools) == 1


@pytest.mark.unit
def test_default_tools_registered():
    """Test que les outils par défaut sont enregistrés automatiquement"""
    registry = ToolRegistry()

    # Vérifier que les outils par défaut sont présents
    assert "python_sandbox" in registry._tools
    assert "file_read" in registry._tools
    assert "math_calculator" in registry._tools

    # Vérifier qu'ils sont des instances correctes
    assert isinstance(registry._tools["python_sandbox"], PythonSandboxTool)
    assert isinstance(registry._tools["file_read"], FileReaderTool)
    assert isinstance(registry._tools["math_calculator"], CalculatorTool)


# ============================================================================
# Tests: Recherche d'outils (get method)
# ============================================================================


@pytest.mark.unit
def test_get_existing_tool(registry_with_mock):
    """Test récupération d'un outil existant"""
    tool = registry_with_mock.get("mock_tool")

    assert tool is not None
    assert isinstance(tool, MockTool)
    assert tool.name == "mock_tool"


@pytest.mark.unit
def test_get_nonexistent_tool(empty_registry):
    """Test récupération d'un outil inexistant"""
    tool = empty_registry.get("nonexistent_tool")

    assert tool is None


@pytest.mark.unit
def test_get_tool_alias(registry_with_mock):
    """Test de l'alias get_tool (compatibilité)"""
    # get_tool doit être équivalent à get
    tool_via_get = registry_with_mock.get("mock_tool")
    tool_via_alias = registry_with_mock.get_tool("mock_tool")

    assert tool_via_get is tool_via_alias
    assert tool_via_alias is not None


@pytest.mark.unit
def test_get_tool_after_multiple_registrations(empty_registry):
    """Test récupération après plusieurs enregistrements"""
    tool_a = CustomToolA()
    tool_b = CustomToolB()

    empty_registry.register(tool_a)
    empty_registry.register(tool_b)

    # Récupérer chaque outil individuellement
    retrieved_a = empty_registry.get("custom_tool_a")
    retrieved_b = empty_registry.get("custom_tool_b")

    assert retrieved_a is tool_a
    assert retrieved_b is tool_b


# ============================================================================
# Tests: Listage des outils (list_all)
# ============================================================================


@pytest.mark.unit
def test_list_all_empty_registry(empty_registry):
    """Test listage d'un registre vide"""
    tools = empty_registry.list_all()

    assert isinstance(tools, dict)
    assert len(tools) == 0


@pytest.mark.unit
def test_list_all_with_tools(empty_registry):
    """Test listage avec plusieurs outils"""
    tool_a = CustomToolA()
    tool_b = CustomToolB()

    empty_registry.register(tool_a)
    empty_registry.register(tool_b)

    tools = empty_registry.list_all()

    assert len(tools) == 2
    assert "custom_tool_a" in tools
    assert "custom_tool_b" in tools
    assert tools["custom_tool_a"] is tool_a
    assert tools["custom_tool_b"] is tool_b


@pytest.mark.unit
def test_list_all_returns_copy(registry_with_mock):
    """Test que list_all retourne une copie (pas la référence originale)"""
    tools_copy = registry_with_mock.list_all()

    # Modifier la copie ne doit pas affecter le registre
    tools_copy["fake_tool"] = MockTool(name="fake_tool")

    # Vérifier que le registre original n'est pas modifié
    assert "fake_tool" not in registry_with_mock._tools
    assert registry_with_mock.get("fake_tool") is None


@pytest.mark.unit
def test_list_all_default_tools():
    """Test listage des outils par défaut"""
    registry = ToolRegistry()
    tools = registry.list_all()

    # Vérifier le nombre d'outils par défaut
    assert len(tools) >= 3

    # Vérifier les noms
    tool_names = list(tools.keys())
    assert "python_sandbox" in tool_names
    assert "file_read" in tool_names
    assert "math_calculator" in tool_names


# ============================================================================
# Tests: Schémas des outils (get_schemas)
# ============================================================================


@pytest.mark.unit
def test_get_schemas_empty_registry(empty_registry):
    """Test obtention des schémas d'un registre vide"""
    schemas = empty_registry.get_schemas()

    assert isinstance(schemas, dict)
    assert len(schemas) == 0


@pytest.mark.unit
def test_get_schemas_with_tools(empty_registry):
    """Test obtention des schémas avec plusieurs outils"""
    tool_a = CustomToolA()
    tool_b = CustomToolB()

    empty_registry.register(tool_a)
    empty_registry.register(tool_b)

    schemas = empty_registry.get_schemas()

    # Vérifier la structure
    assert len(schemas) == 2
    assert "custom_tool_a" in schemas
    assert "custom_tool_b" in schemas

    # Vérifier le schéma de tool_a
    schema_a = schemas["custom_tool_a"]
    assert "name" in schema_a
    assert "description" in schema_a
    assert "parameters" in schema_a
    assert schema_a["name"] == "custom_tool_a"


@pytest.mark.unit
def test_get_schemas_structure(registry_with_mock):
    """Test de la structure des schémas"""
    schemas = registry_with_mock.get_schemas()

    schema = schemas["mock_tool"]

    # Vérifier les champs requis
    assert "name" in schema
    assert "description" in schema
    assert "parameters" in schema

    # Vérifier les valeurs
    assert schema["name"] == "mock_tool"
    assert schema["description"] == "Mock tool for testing"

    # Vérifier la structure des paramètres
    params = schema["parameters"]
    assert "type" in params
    assert params["type"] == "object"
    assert "properties" in params


@pytest.mark.unit
def test_get_schemas_default_tools():
    """Test des schémas des outils par défaut"""
    registry = ToolRegistry()
    schemas = registry.get_schemas()

    # Vérifier que chaque outil par défaut a un schéma valide
    for tool_name in ["python_sandbox", "file_read", "math_calculator"]:
        assert tool_name in schemas

        schema = schemas[tool_name]
        assert "name" in schema
        assert "description" in schema
        assert "parameters" in schema

        # Vérifier que les paramètres sont bien formés
        params = schema["parameters"]
        assert isinstance(params, dict)
        assert "type" in params


# ============================================================================
# Tests: Singleton pattern (get_registry)
# ============================================================================


@pytest.mark.unit
def test_get_registry_singleton():
    """Test que get_registry retourne toujours la même instance"""
    registry1 = get_registry()
    registry2 = get_registry()

    # Les deux appels doivent retourner la même instance
    assert registry1 is registry2


@pytest.mark.unit
def test_get_registry_returns_toolregistry():
    """Test que get_registry retourne bien un ToolRegistry"""
    registry = get_registry()

    assert isinstance(registry, ToolRegistry)


@pytest.mark.unit
def test_get_registry_has_default_tools():
    """Test que le singleton global a les outils par défaut"""
    registry = get_registry()

    # Vérifier les outils par défaut
    assert registry.get("python_sandbox") is not None
    assert registry.get("file_read") is not None
    assert registry.get("math_calculator") is not None


# ============================================================================
# Tests: Reload registry (reload_registry)
# ============================================================================


@pytest.mark.unit
def test_reload_registry_creates_new_instance():
    """Test que reload_registry crée une nouvelle instance"""
    # Obtenir l'instance actuelle
    old_registry = get_registry()

    # Recharger
    new_registry = reload_registry()

    # Les instances doivent être différentes
    assert new_registry is not old_registry


@pytest.mark.unit
def test_reload_registry_resets_custom_tools():
    """Test que reload_registry supprime les outils custom"""
    # Obtenir le registre et ajouter un outil custom
    registry = get_registry()
    custom_tool = MockTool(name="custom_test_tool")
    registry.register(custom_tool)

    # Vérifier qu'il est là
    assert registry.get("custom_test_tool") is not None

    # Recharger
    reload_registry()

    # Le nouvel appel à get_registry doit avoir un registre sans l'outil custom
    new_registry = get_registry()
    assert new_registry.get("custom_test_tool") is None


@pytest.mark.unit
def test_reload_registry_restores_default_tools():
    """Test que reload_registry restaure les outils par défaut"""
    # Recharger
    registry = reload_registry()

    # Vérifier que les outils par défaut sont présents
    assert registry.get("python_sandbox") is not None
    assert registry.get("file_read") is not None
    assert registry.get("math_calculator") is not None


@pytest.mark.unit
def test_reload_registry_subsequent_get_registry_calls():
    """Test que les appels à get_registry après reload utilisent la nouvelle instance"""
    # Premier registre
    old_registry = get_registry()

    # Recharger
    reloaded_registry = reload_registry()

    # Nouvel appel à get_registry
    current_registry = get_registry()

    # current_registry doit être la même que reloaded_registry (pas old_registry)
    assert current_registry is reloaded_registry
    assert current_registry is not old_registry


# ============================================================================
# Tests: Intégration et cas complexes
# ============================================================================


@pytest.mark.integration
def test_full_workflow():
    """Test du workflow complet: enregistrement, recherche, listage, schémas"""
    # 1. Créer un registre vide
    registry = ToolRegistry.__new__(ToolRegistry)
    registry._tools = {}

    # 2. Enregistrer des outils
    tool_a = CustomToolA()
    tool_b = CustomToolB()
    registry.register(tool_a)
    registry.register(tool_b)

    # 3. Rechercher un outil
    found_tool = registry.get("custom_tool_a")
    assert found_tool is tool_a

    # 4. Lister tous les outils
    all_tools = registry.list_all()
    assert len(all_tools) == 2

    # 5. Obtenir les schémas
    schemas = registry.get_schemas()
    assert len(schemas) == 2
    assert "custom_tool_a" in schemas


@pytest.mark.integration
def test_registry_persistence_across_operations():
    """Test que le registre conserve son état à travers plusieurs opérations"""
    registry = ToolRegistry.__new__(ToolRegistry)
    registry._tools = {}

    # Enregistrer plusieurs outils en séquence
    for i in range(5):
        tool = MockTool(name=f"tool_{i}", description=f"Tool {i}")
        registry.register(tool)

        # Vérifier que tous les outils précédents sont toujours là
        for j in range(i + 1):
            assert registry.get(f"tool_{j}") is not None

    # Vérifier le total
    assert len(registry.list_all()) == 5


@pytest.mark.unit
def test_tool_execution_through_registry():
    """Test de l'exécution d'un outil récupéré depuis le registre"""
    registry = ToolRegistry.__new__(ToolRegistry)
    registry._tools = {}

    # Enregistrer un outil
    tool = MockTool()
    registry.register(tool)

    # Récupérer et exécuter
    retrieved_tool = registry.get("mock_tool")
    result = retrieved_tool.execute({"param": "test_value"})

    assert result.is_success()
    assert "test_value" in result.output


@pytest.mark.unit
def test_schema_validation_for_registered_tools():
    """Test que tous les outils enregistrés ont des schémas valides"""
    registry = ToolRegistry()
    schemas = registry.get_schemas()

    # Vérifier que chaque schéma est bien formé
    for tool_name, schema in schemas.items():
        # Champs requis
        assert "name" in schema, f"Tool {tool_name} missing 'name' in schema"
        assert "description" in schema, f"Tool {tool_name} missing 'description' in schema"
        assert "parameters" in schema, f"Tool {tool_name} missing 'parameters' in schema"

        # Type des paramètres
        params = schema["parameters"]
        assert isinstance(params, dict), f"Tool {tool_name} parameters not a dict"
        assert "type" in params, f"Tool {tool_name} parameters missing 'type'"


# ============================================================================
# Tests: Edge cases et robustesse
# ============================================================================


@pytest.mark.unit
def test_register_tool_with_special_characters_in_name():
    """Test enregistrement d'un outil avec caractères spéciaux dans le nom"""
    registry = ToolRegistry.__new__(ToolRegistry)
    registry._tools = {}

    # Nom avec underscores, tirets
    tool = MockTool(name="tool_with-special.chars", description="Special tool")
    registry.register(tool)

    # Doit être récupérable
    assert registry.get("tool_with-special.chars") is tool


@pytest.mark.unit
def test_register_tool_with_empty_description():
    """Test enregistrement d'un outil avec description vide"""
    registry = ToolRegistry.__new__(ToolRegistry)
    registry._tools = {}

    tool = MockTool(name="no_desc_tool", description="")
    registry.register(tool)

    # Doit être enregistré sans problème
    assert registry.get("no_desc_tool") is tool


@pytest.mark.unit
def test_get_with_none_name():
    """Test récupération avec None comme nom (devrait retourner None)"""
    registry = ToolRegistry()

    # get() avec None devrait retourner None (pas de crash)
    result = registry.get(None)
    assert result is None


@pytest.mark.unit
def test_list_all_immutability():
    """Test que la modification de list_all() ne modifie pas le registre interne"""
    registry = ToolRegistry.__new__(ToolRegistry)
    registry._tools = {}

    tool = MockTool()
    registry.register(tool)

    # Obtenir la liste
    tools_list = registry.list_all()
    original_count = len(tools_list)

    # Essayer de modifier la copie
    tools_list.clear()

    # Le registre original doit être intact
    assert len(registry._tools) == 1
    assert len(registry.list_all()) == original_count
