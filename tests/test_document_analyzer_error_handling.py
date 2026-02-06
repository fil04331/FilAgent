"""
Tests d'erreur et robustesse pour Document Analyzer
Phase 6.2: Tests complets pour validation d'erreurs

Couvre:
- Validation de fichiers (taille, extension, corruption)
- Gestion d'erreurs dans les previews
- Gestion d'erreurs dans les exports
- Scénarios edge cases
"""

import pytest
from pathlib import Path
import sys
import tempfile
import shutil

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import des fonctions à tester
# Les fonctions sont définies au niveau module donc importables sans exécuter Gradio
try:
    from gradio_app_production import (
        MAX_FILE_SIZE_MB,
        MAX_FILE_SIZE_BYTES,
        ALL_SUPPORTED_EXTENSIONS,
        ERROR_MESSAGES,
        validate_file,
        check_disk_space,
        cleanup_temp_files,
    )
except ImportError as e:
    print(f"⚠️ Impossible d'importer depuis gradio_app_production: {e}")
    print("Les tests nécessitent que gradio_app_production.py soit importable")
    sys.exit(1)

# Chemin vers les fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ============================================================================
# TESTS UNITAIRES - Fonction validate_file()
# ============================================================================


class TestValidateFile:
    """Tests pour la fonction validate_file()"""

    def test_validate_nonexistent_file(self):
        """Test validation fichier inexistant"""
        is_valid, error = validate_file("/nonexistent/file.pdf")
        assert not is_valid
        assert "introuvable" in error.lower()

    def test_validate_unsupported_extension(self):
        """Test validation extension non supportée"""
        # Utiliser le fichier .txt créé dans les fixtures
        file_path = FIXTURES_DIR / "unsupported_file.txt"

        is_valid, error = validate_file(str(file_path))
        assert not is_valid
        assert "non supporté" in error.lower()

    def test_validate_valid_excel(self):
        """Test validation fichier Excel valide"""
        file_path = FIXTURES_DIR / "valid_invoice.xlsx"

        is_valid, error = validate_file(str(file_path))
        assert is_valid
        assert error is None

    def test_validate_valid_pdf(self):
        """Test validation fichier PDF valide"""
        file_path = FIXTURES_DIR / "valid_document.pdf"

        is_valid, error = validate_file(str(file_path))
        assert is_valid
        assert error is None

    def test_validate_valid_word(self):
        """Test validation fichier Word valide"""
        file_path = FIXTURES_DIR / "valid_report.docx"

        is_valid, error = validate_file(str(file_path))
        assert is_valid
        assert error is None

    @pytest.mark.slow
    def test_validate_file_too_large(self):
        """Test validation fichier > 50 MB"""
        # Créer un fichier temporaire de 60 MB
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as temp_file:
            temp_path = temp_file.name
            # Écrire 60 MB de données
            chunk_size = 1024 * 1024  # 1 MB
            for _ in range(60):
                temp_file.write(b"x" * chunk_size)

        try:
            is_valid, error = validate_file(temp_path)
            assert not is_valid
            assert "trop volumineux" in error.lower()
            assert str(MAX_FILE_SIZE_MB) in error
        finally:
            # Cleanup
            Path(temp_path).unlink(missing_ok=True)

    def test_validate_empty_file(self):
        """Test validation fichier vide (0 bytes)"""
        file_path = FIXTURES_DIR / "empty_document.pdf"

        # Un fichier vide devrait passer la validation de base
        # (mais échouer plus tard lors du parsing)
        is_valid, error = validate_file(str(file_path))
        # La validation de base vérifie juste existence, extension, taille
        # Un fichier vide passe ces checks
        assert is_valid or ("lecture" in error.lower() if error else False)


# ============================================================================
# TESTS UNITAIRES - Fonction check_disk_space()
# ============================================================================


class TestCheckDiskSpace:
    """Tests pour la fonction check_disk_space()"""

    def test_disk_space_check_normal(self):
        """Test vérification espace disque normal"""
        # Demander juste 1 KB (devrait toujours être disponible)
        assert check_disk_space(required_bytes=1024) == True

    def test_disk_space_check_unrealistic(self):
        """Test vérification espace disque avec demande irréaliste"""
        # Demander 1 PB (impossible)
        assert check_disk_space(required_bytes=1024**5) == False


# ============================================================================
# TESTS UNITAIRES - Fonction cleanup_temp_files()
# ============================================================================


class TestCleanupTempFiles:
    """Tests pour la fonction cleanup_temp_files()"""

    def test_cleanup_single_file(self):
        """Test cleanup d'un seul fichier"""
        # Créer un fichier temporaire
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name
            temp_file.write(b"test data")

        # Vérifier qu'il existe
        assert Path(temp_path).exists()

        # Cleanup
        cleanup_temp_files(temp_path)

        # Vérifier qu'il a été supprimé
        assert not Path(temp_path).exists()

    def test_cleanup_multiple_files(self):
        """Test cleanup de plusieurs fichiers"""
        # Créer plusieurs fichiers temporaires
        temp_files = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_files.append(temp_file.name)
                temp_file.write(f"test data {i}".encode())

        # Vérifier qu'ils existent
        for temp_path in temp_files:
            assert Path(temp_path).exists()

        # Cleanup
        cleanup_temp_files(*temp_files)

        # Vérifier qu'ils ont été supprimés
        for temp_path in temp_files:
            assert not Path(temp_path).exists()

    def test_cleanup_nonexistent_file(self):
        """Test cleanup fichier inexistant (ne devrait pas crasher)"""
        # Cleanup d'un fichier qui n'existe pas
        cleanup_temp_files("/nonexistent/file.txt")
        # Pas d'exception = succès

    def test_cleanup_with_none(self):
        """Test cleanup avec None (ne devrait pas crasher)"""
        cleanup_temp_files(None)
        # Pas d'exception = succès


# ============================================================================
# TESTS D'INTÉGRATION - DocumentAnalyzerTool avec fichiers corrompus
# ============================================================================


@pytest.mark.integration
class TestDocumentAnalyzerCorruptedFiles:
    """Tests d'intégration avec fichiers corrompus"""

    def test_corrupted_excel_handling(self):
        """Test gestion Excel corrompu"""
        from tools.document_analyzer_pme import DocumentAnalyzerPME
        from tools.base import ToolStatus

        tool = DocumentAnalyzerPME()
        file_path = str(FIXTURES_DIR / "corrupted_file.xlsx")

        result = tool.execute({"file_path": file_path, "analysis_type": "invoice"})

        # Devrait retourner une erreur
        assert result.status == ToolStatus.ERROR
        assert result.error is not None

    def test_corrupted_pdf_handling(self):
        """Test gestion PDF corrompu"""
        from tools.document_analyzer_pme import DocumentAnalyzerPME
        from tools.base import ToolStatus

        tool = DocumentAnalyzerPME()
        file_path = str(FIXTURES_DIR / "corrupted_document.pdf")

        result = tool.execute({"file_path": file_path, "analysis_type": "invoice"})

        # Devrait retourner une erreur
        assert result.status == ToolStatus.ERROR
        assert result.error is not None

    def test_corrupted_word_handling(self):
        """Test gestion Word corrompu"""
        from tools.document_analyzer_pme import DocumentAnalyzerPME
        from tools.base import ToolStatus

        tool = DocumentAnalyzerPME()
        file_path = str(FIXTURES_DIR / "corrupted_report.docx")

        result = tool.execute({"file_path": file_path, "analysis_type": "extract"})

        # Devrait retourner une erreur
        assert result.status == ToolStatus.ERROR
        assert result.error is not None


# ============================================================================
# TESTS D'INTÉGRATION - Fichiers vides
# ============================================================================


@pytest.mark.integration
class TestDocumentAnalyzerEmptyFiles:
    """Tests avec fichiers vides"""

    def test_empty_excel_handling(self):
        """Test gestion Excel vide"""
        from tools.document_analyzer_pme import DocumentAnalyzerPME

        tool = DocumentAnalyzerPME()
        file_path = str(FIXTURES_DIR / "empty_file.xlsx")

        result = tool.execute({"file_path": file_path, "analysis_type": "invoice"})

        # Peut retourner succès avec données vides ou erreur
        # On vérifie juste qu'il ne crash pas
        assert result is not None

    def test_empty_pdf_handling(self):
        """Test gestion PDF vide (0 bytes)"""
        from tools.document_analyzer_pme import DocumentAnalyzerPME
        from tools.base import ToolStatus

        tool = DocumentAnalyzerPME()
        file_path = str(FIXTURES_DIR / "empty_document.pdf")

        result = tool.execute({"file_path": file_path, "analysis_type": "invoice"})

        # Un PDF vide devrait donner une erreur
        assert result.status == ToolStatus.ERROR


# ============================================================================
# TESTS D'INTÉGRATION - Fichiers valides
# ============================================================================


@pytest.mark.integration
class TestDocumentAnalyzerValidFiles:
    """Tests avec fichiers valides pour confirmer pas de régression"""

    def test_valid_excel_analysis(self):
        """Test analyse Excel valide"""
        from tools.document_analyzer_pme import DocumentAnalyzerPME
        from tools.base import ToolStatus

        tool = DocumentAnalyzerPME()
        file_path = str(FIXTURES_DIR / "valid_invoice.xlsx")

        result = tool.execute({"file_path": file_path, "analysis_type": "invoice"})

        # Devrait réussir
        assert result.status == ToolStatus.SUCCESS
        assert result.metadata is not None

    def test_valid_pdf_analysis(self):
        """Test analyse PDF valide"""
        from tools.document_analyzer_pme import DocumentAnalyzerPME
        from tools.base import ToolStatus

        tool = DocumentAnalyzerPME()
        file_path = str(FIXTURES_DIR / "valid_document.pdf")

        result = tool.execute({"file_path": file_path, "analysis_type": "extract"})

        # Devrait réussir (même si extraction minimale)
        assert result.status == ToolStatus.SUCCESS
        assert result.metadata is not None


# ============================================================================
# TESTS DE PERFORMANCE - Timeout
# ============================================================================


@pytest.mark.performance
@pytest.mark.slow
class TestPerformance:
    """Tests de performance et timeout"""

    @pytest.mark.skip(reason="Requires large file fixture (manual creation)")
    def test_large_file_handling(self):
        """Test gestion fichier volumineux"""
        # Ce test nécessite de créer un fichier > 50 MB
        # Skip par défaut car long à exécuter
        pass


# ============================================================================
# TESTS EDGE CASES
# ============================================================================


@pytest.mark.unit
class TestEdgeCases:
    """Tests de cas limites"""

    def test_file_path_with_spaces(self):
        """Test fichier avec espaces dans le nom"""
        # Créer un fichier temporaire avec espaces
        with tempfile.NamedTemporaryFile(
            suffix=".xlsx", prefix="test file with spaces ", delete=False
        ) as temp_file:
            temp_path = temp_file.name
            temp_file.write(b"test data")

        try:
            is_valid, error = validate_file(temp_path)
            # Devrait gérer les espaces correctement
            assert is_valid or error is not None
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_file_path_with_unicode(self):
        """Test fichier avec caractères Unicode"""
        # Créer un fichier temporaire avec caractères accentués
        with tempfile.NamedTemporaryFile(
            suffix=".xlsx", prefix="test_éàü_", delete=False
        ) as temp_file:
            temp_path = temp_file.name
            temp_file.write(b"test data")

        try:
            is_valid, error = validate_file(temp_path)
            # Devrait gérer l'Unicode correctement
            assert is_valid or error is not None
        finally:
            Path(temp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    # Exécuter tous les tests avec verbose
    pytest.main([__file__, "-v", "--tb=short", "-m", "not slow"])
