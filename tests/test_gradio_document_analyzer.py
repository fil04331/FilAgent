"""
Tests d'intégration pour le Document Analyzer dans l'interface Gradio
"""
import pytest
from pathlib import Path
import sys

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.document_analyzer_pme import DocumentAnalyzerPME
from tools.base import ToolStatus


@pytest.mark.integration
class TestGradioDocumentAnalyzer:
    """Tests d'intégration pour le Document Analyzer dans Gradio"""

    def test_tool_instantiation(self):
        """Test que l'outil peut être instancié correctement"""
        tool = DocumentAnalyzerPME()
        assert tool is not None
        assert tool.name == "document_analyzer_pme"
        assert tool.description is not None

    def test_tool_validates_arguments(self):
        """Test que l'outil valide correctement les arguments"""
        tool = DocumentAnalyzerPME()

        # Test sans file_path
        is_valid, error = tool.validate_arguments({})
        assert not is_valid
        assert "file_path" in error

        # Test avec file_path invalide (type incorrect)
        is_valid, error = tool.validate_arguments({'file_path': 123})
        assert not is_valid
        assert "string" in error.lower()

        # Test avec extension non supportée
        is_valid, error = tool.validate_arguments({'file_path': 'test.txt'})
        assert not is_valid
        assert "Unsupported" in error

        # Test avec arguments valides
        is_valid, error = tool.validate_arguments({'file_path': 'test.pdf'})
        assert is_valid
        assert error is None

    @pytest.mark.skipif(
        not Path("/Users/felixlefebvre/FilAgent/tests/fixtures").exists(),
        reason="Fixtures directory not found"
    )
    def test_tool_execution_with_fixture(self):
        """Test l'exécution de l'outil avec un fichier fixture (si disponible)"""
        tool = DocumentAnalyzerPME()

        # Chercher un fichier de test
        fixtures_dir = Path("/Users/felixlefebvre/FilAgent/tests/fixtures")
        pdf_files = list(fixtures_dir.glob("*.pdf"))
        excel_files = list(fixtures_dir.glob("*.xlsx"))

        if pdf_files:
            result = tool.execute({
                'file_path': str(pdf_files[0]),
                'analysis_type': 'invoice'
            })
            # Vérifier que l'exécution ne plante pas
            assert result is not None
            assert hasattr(result, 'status')

        if excel_files:
            result = tool.execute({
                'file_path': str(excel_files[0]),
                'analysis_type': 'extract'
            })
            assert result is not None
            assert hasattr(result, 'status')

    def test_tool_handles_missing_file(self):
        """Test que l'outil gère correctement un fichier manquant"""
        tool = DocumentAnalyzerPME()

        result = tool.execute({
            'file_path': '/path/to/nonexistent/file.pdf',
            'analysis_type': 'invoice'
        })

        assert result.status == ToolStatus.ERROR
        assert "not found" in result.error.lower()

    def test_tool_schema(self):
        """Test que le schéma de paramètres est correct"""
        tool = DocumentAnalyzerPME()
        schema = tool.get_parameters_schema()

        assert 'type' in schema
        assert schema['type'] == 'object'
        assert 'properties' in schema
        assert 'file_path' in schema['properties']
        assert 'analysis_type' in schema['properties']
        assert 'required' in schema
        assert 'file_path' in schema['required']


@pytest.mark.unit
class TestDocumentAnalyzerToolWrapper:
    """Tests unitaires pour le wrapper Gradio de DocumentAnalyzerTool"""

    def test_wrapper_initialization(self):
        """Test l'initialisation du wrapper"""
        # Note: On ne peut pas facilement tester la classe DocumentAnalyzerTool
        # de gradio_app_production.py car elle dépend de tout le contexte Gradio
        # Ces tests seraient mieux faits en tests E2E avec Gradio running
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
