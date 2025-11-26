"""
Tests d'intégration pour DocumentAnalyzerPME dans le registre
Vérifie que l'agent peut utiliser l'outil via le registre
"""
import pytest
from pathlib import Path
import sys

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.registry import get_registry, reload_registry
from tools.document_analyzer_pme import DocumentAnalyzerPME
from tools.base import ToolStatus


@pytest.mark.integration
class TestDocumentAnalyzerRegistry:
    """Tests d'intégration pour le Document Analyzer dans le registre"""

    def setup_method(self):
        """Setup avant chaque test"""
        # Recharger le registre pour avoir un état propre
        reload_registry()
        self.registry = get_registry()

    def test_document_analyzer_is_registered(self):
        """Test que DocumentAnalyzerPME est enregistré dans le registre"""
        # Vérifier que l'outil est dans le registre
        tool = self.registry.get('document_analyzer_pme')
        assert tool is not None, "DocumentAnalyzerPME devrait être dans le registre"
        assert isinstance(tool, DocumentAnalyzerPME)

    def test_registry_lists_document_analyzer(self):
        """Test que l'outil apparaît dans la liste de tous les outils"""
        all_tools = self.registry.list_all()
        assert 'document_analyzer_pme' in all_tools
        assert isinstance(all_tools['document_analyzer_pme'], DocumentAnalyzerPME)

    def test_registry_get_all_includes_document_analyzer(self):
        """Test que get_all() inclut l'outil"""
        all_tools_list = self.registry.get_all()
        tool_names = [tool.name for tool in all_tools_list]
        assert 'document_analyzer_pme' in tool_names

    def test_document_analyzer_schema_in_registry(self):
        """Test que le schéma de l'outil est accessible via le registre"""
        schemas = self.registry.get_schemas()
        assert 'document_analyzer_pme' in schemas

        schema = schemas['document_analyzer_pme']
        # Le schéma retourné a 'name', 'description', 'parameters'
        assert 'parameters' in schema
        params = schema['parameters']
        assert 'type' in params
        assert params['type'] == 'object'
        assert 'properties' in params
        assert 'file_path' in params['properties']

    def test_tool_execution_via_registry(self):
        """Test l'exécution de l'outil via le registre"""
        tool = self.registry.get('document_analyzer_pme')
        assert tool is not None

        # Test avec fichier manquant (devrait retourner erreur)
        result = tool.execute({
            'file_path': '/nonexistent/file.pdf',
            'analysis_type': 'invoice'
        })

        assert result is not None
        assert hasattr(result, 'status')
        assert result.status == ToolStatus.ERROR
        assert 'not found' in result.error.lower()

    def test_multiple_tools_coexist(self):
        """Test que DocumentAnalyzerPME coexiste avec les autres outils"""
        all_tools = self.registry.list_all()

        # Vérifier que les outils standards sont présents
        # Note: Les noms réels peuvent différer des noms de classes
        expected_tools = [
            'python_sandbox',
            'file_read',  # FileReaderTool s'enregistre comme 'file_read'
            'math_calculator',  # CalculatorTool s'enregistre comme 'math_calculator'
            'document_analyzer_pme'  # Notre nouvel outil
        ]

        for tool_name in expected_tools:
            assert tool_name in all_tools, f"{tool_name} devrait être dans le registre"

        # Vérifier qu'on a bien 4 outils au minimum
        assert len(all_tools) >= 4


@pytest.mark.integration
class TestAgentWithDocumentAnalyzer:
    """Tests d'intégration Agent + DocumentAnalyzer"""

    def test_agent_can_access_tool(self):
        """Test que l'agent peut accéder à l'outil via son registre"""
        try:
            from runtime.agent import Agent
        except ImportError:
            pytest.skip("Agent not importable (missing dependencies)")
            return

        # Créer un agent
        agent = Agent()

        # Vérifier que l'agent a le registre
        assert hasattr(agent, 'tool_registry')

        # Vérifier que l'outil est accessible
        tool = agent.tool_registry.get('document_analyzer_pme')
        assert tool is not None
        assert isinstance(tool, DocumentAnalyzerPME)

    def test_agent_tool_registry_consistency(self):
        """Test que le registre de l'agent est le même que le registre global"""
        try:
            from runtime.agent import Agent
        except ImportError:
            pytest.skip("Agent not importable")
            return

        agent = Agent()
        global_registry = get_registry()

        # Les deux registres devraient avoir les mêmes outils
        agent_tools = set(agent.tool_registry.list_all().keys())
        global_tools = set(global_registry.list_all().keys())

        assert agent_tools == global_tools


@pytest.mark.unit
class TestRegistryReload:
    """Tests pour la fonctionnalité de rechargement du registre"""

    def test_reload_registry_recreates_tools(self):
        """Test que reload_registry() recrée bien tous les outils"""
        # Premier chargement
        registry1 = get_registry()
        tool1 = registry1.get('document_analyzer_pme')

        # Recharger
        registry2 = reload_registry()
        tool2 = registry2.get('document_analyzer_pme')

        # Ce sont des instances différentes
        assert tool1 is not tool2

        # Mais de la même classe
        assert type(tool1) == type(tool2)
        assert isinstance(tool2, DocumentAnalyzerPME)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
