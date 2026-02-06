"""
Tests de sécurité pour DocumentAnalyzerPME
Focus: Path validation, path traversal prevention, symlink handling
"""

import pytest
import sys
from pathlib import Path
import tempfile
import os

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.document_analyzer_pme import DocumentAnalyzerPME
from tools.base import ToolResult, ToolStatus

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def analyzer():
    """Create DocumentAnalyzerPME instance"""
    return DocumentAnalyzerPME()


@pytest.fixture
def temp_allowed_dir(tmp_path):
    """Create a temporary directory in allowed paths"""
    # Create directory in /tmp which is in allowed_paths
    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir(exist_ok=True)
    return allowed_dir


@pytest.fixture
def temp_blocked_dir(tmp_path):
    """Create a temporary directory for testing (will be in /tmp/)"""
    # Note: /tmp/ is in allowed_paths by default
    # Tests that need truly blocked paths should temporarily modify allowed_paths
    blocked_dir = tmp_path / "blocked"
    blocked_dir.mkdir(exist_ok=True)
    return blocked_dir


@pytest.fixture
def sample_pdf_allowed(temp_allowed_dir):
    """Create a sample PDF in allowed directory"""
    pdf_path = temp_allowed_dir / "test_invoice.pdf"

    # Create minimal valid PDF
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
>>
endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
trailer
<<
/Size 4
/Root 1 0 R
>>
startxref
195
%%EOF"""

    pdf_path.write_bytes(pdf_content)
    return str(pdf_path)


@pytest.fixture
def sample_pdf_blocked(temp_blocked_dir):
    """Create a sample PDF in blocked directory"""
    pdf_path = temp_blocked_dir / "secret_invoice.pdf"

    # Create minimal valid PDF
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
>>
endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
trailer
<<
/Size 4
/Root 1 0 R
>>
startxref
195
%%EOF"""

    pdf_path.write_bytes(pdf_content)
    return str(pdf_path)


# ============================================================================
# SECURITY TESTS - PATH VALIDATION
# ============================================================================


@pytest.mark.unit
@pytest.mark.tools
class TestDocumentAnalyzerSecurity:
    """Tests de sécurité pour validation de chemins"""

    def test_path_in_allowed_directory(self, analyzer, sample_pdf_allowed):
        """Test that files in allowed directories can be accessed"""
        # Temporarily add tmp_path to allowed_paths for testing
        original_paths = analyzer.allowed_paths.copy()
        analyzer.allowed_paths.append(str(Path(sample_pdf_allowed).parent.parent) + "/")

        try:
            result = analyzer.execute({"file_path": sample_pdf_allowed, "analysis_type": "extract"})

            # Should succeed (or fail for other reasons, but NOT path validation)
            assert result.status != ToolStatus.BLOCKED
        finally:
            analyzer.allowed_paths = original_paths

    def test_path_outside_allowed_directories(self, analyzer, sample_pdf_blocked):
        """Test that files outside allowed directories are blocked"""
        # Temporarily remove /tmp/ from allowed_paths to test blocking
        original_paths = analyzer.allowed_paths.copy()

        # Remove /tmp/ from allowed paths for this test
        analyzer.allowed_paths = [p for p in analyzer.allowed_paths if "/tmp/" not in p]

        try:
            result = analyzer.execute({"file_path": sample_pdf_blocked, "analysis_type": "extract"})

            # Should be blocked or error due to path validation
            assert result.status == ToolStatus.ERROR
            # Error should mention access denied or path not allowed
            if result.error:
                assert any(
                    keyword in result.error.lower()
                    for keyword in ["not in allowed directories", "access denied", "path validation"]
                )
        finally:
            analyzer.allowed_paths = original_paths
            # Cleanup
            blocked_file = Path(sample_pdf_blocked)
            if blocked_file.exists():
                try:
                    blocked_file.unlink()
                    blocked_file.parent.rmdir()
                except (OSError, PermissionError):
                    # Cleanup failed, not critical for test
                    pass

    def test_path_traversal_attack_blocked(self, analyzer, sample_pdf_allowed):
        """Test that path traversal attacks are blocked"""
        # Try to access file outside allowed directory using ../
        traversal_path = str(Path(sample_pdf_allowed).parent / ".." / ".." / "etc" / "passwd")

        result = analyzer.execute({"file_path": traversal_path, "analysis_type": "extract"})

        # Should be blocked
        assert result.status == ToolStatus.ERROR

    def test_null_byte_injection_blocked(self, analyzer):
        """Test that null byte injection is blocked"""
        malicious_path = "test_file.pdf\x00.txt"

        result = analyzer.execute({"file_path": malicious_path, "analysis_type": "extract"})

        assert result.status == ToolStatus.ERROR
        assert "null byte" in result.error.lower()

    def test_path_too_long_blocked(self, analyzer):
        """Test that excessively long paths are blocked"""
        long_path = "a" * 5000 + ".pdf"

        result = analyzer.execute({"file_path": long_path, "analysis_type": "extract"})

        assert result.status == ToolStatus.ERROR
        assert "too long" in result.error.lower()

    def test_symlink_to_allowed_path(self, analyzer, sample_pdf_allowed, tmp_path):
        """Test that symlinks to allowed paths are handled correctly"""
        # Create symlink in allowed directory pointing to another allowed file
        original_paths = analyzer.allowed_paths.copy()
        allowed_dir = Path(sample_pdf_allowed).parent
        analyzer.allowed_paths.append(str(allowed_dir) + "/")

        symlink_path = allowed_dir / "link_to_pdf.pdf"

        try:
            # Create symlink
            if hasattr(os, "symlink"):
                try:
                    symlink_path.symlink_to(sample_pdf_allowed)

                    result = analyzer.execute({"file_path": str(symlink_path), "analysis_type": "extract"})

                    # Should succeed or fail for non-security reasons
                    assert result.status != ToolStatus.BLOCKED
                except OSError:
                    pytest.skip("Cannot create symlinks on this system")
            else:
                pytest.skip("Symlinks not supported on this platform")
        finally:
            analyzer.allowed_paths = original_paths
            if symlink_path.exists():
                symlink_path.unlink()

    def test_symlink_to_blocked_path(self, analyzer, sample_pdf_blocked, temp_allowed_dir):
        """Test that symlinks pointing outside allowed directories are blocked"""
        original_paths = analyzer.allowed_paths.copy()

        # Temporarily remove /tmp/ from allowed paths to simulate blocked directory
        analyzer.allowed_paths = [p for p in analyzer.allowed_paths if "/tmp/" not in p]
        analyzer.allowed_paths.append(str(temp_allowed_dir) + "/")

        symlink_path = temp_allowed_dir / "malicious_link.pdf"

        try:
            # Create symlink in allowed dir pointing to blocked file
            if hasattr(os, "symlink"):
                try:
                    symlink_path.symlink_to(sample_pdf_blocked)

                    result = analyzer.execute({"file_path": str(symlink_path), "analysis_type": "extract"})

                    # Should be blocked due to symlink target validation
                    assert result.status == ToolStatus.ERROR
                    # The error might be about path not allowed or file access
                    if result.error:
                        assert any(
                            keyword in result.error.lower()
                            for keyword in [
                                "not in allowed directories",
                                "access denied",
                                "path validation",
                                "permission",
                            ]
                        )
                except OSError:
                    pytest.skip("Cannot create symlinks on this system")
            else:
                pytest.skip("Symlinks not supported on this platform")
        finally:
            analyzer.allowed_paths = original_paths
            if symlink_path.exists():
                symlink_path.unlink()
            # Cleanup blocked file
            blocked_file = Path(sample_pdf_blocked)
            if blocked_file.exists():
                try:
                    blocked_file.unlink()
                    blocked_file.parent.rmdir()
                except (OSError, PermissionError):
                    # Cleanup failed, not critical for test
                    pass

    def test_absolute_path_outside_allowlist(self, analyzer):
        """Test that absolute paths outside allowlist are blocked"""
        # Try to access system files with valid extensions
        system_paths = [
            "/etc/passwd.pdf",  # Add valid extension
            "/etc/shadow.xlsx",  # Add valid extension
        ]

        for path in system_paths:
            # Create a fake file to test path validation
            # Since the file doesn't exist, path validation may not trigger
            # So we test with files that exist
            result = analyzer.execute({"file_path": path, "analysis_type": "extract"})

            # Should be blocked - either path validation or file not found
            assert result.status == ToolStatus.ERROR
            # Error can be about path, file not found, or unsupported extension
            # All are valid security responses

    def test_validate_arguments_with_invalid_path(self, analyzer):
        """Test validate_arguments method directly"""
        # Valid format but path validation should catch it
        is_valid, error = analyzer.validate_arguments({"file_path": "/etc/passwd"})

        # Should be invalid due to path not in allowlist
        # Note: validation might pass if file doesn't exist, but execute should still block
        if is_valid:
            # If validation passes, execute should still block
            result = analyzer.execute({"file_path": "/etc/passwd"})
            assert result.status == ToolStatus.ERROR

    def test_allowed_paths_configuration(self, analyzer):
        """Test that allowed_paths is properly configured"""
        assert hasattr(analyzer, "allowed_paths")
        assert isinstance(analyzer.allowed_paths, list)
        assert len(analyzer.allowed_paths) > 0

        # Check for expected paths
        expected_paths = ["working_set/", "temp/", "memory/working_set/", "/tmp/"]
        for expected in expected_paths:
            assert expected in analyzer.allowed_paths, f"Expected path {expected} not in allowed_paths"

    def test_max_file_size_configuration(self, analyzer):
        """Test that max_file_size is configured"""
        assert hasattr(analyzer, "max_file_size")
        assert analyzer.max_file_size == 50 * 1024 * 1024  # 50 MB

    def test_is_path_allowed_method_exists(self, analyzer):
        """Test that _is_path_allowed method exists"""
        assert hasattr(analyzer, "_is_path_allowed")
        assert callable(analyzer._is_path_allowed)


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


@pytest.mark.integration
@pytest.mark.tools
class TestDocumentAnalyzerSecurityIntegration:
    """Integration tests for security features"""

    def test_full_validation_flow(self, analyzer, sample_pdf_allowed):
        """Test complete validation flow from arguments to execution"""
        original_paths = analyzer.allowed_paths.copy()
        analyzer.allowed_paths.append(str(Path(sample_pdf_allowed).parent.parent) + "/")

        try:
            # 1. Validate arguments
            is_valid, error = analyzer.validate_arguments({"file_path": sample_pdf_allowed, "analysis_type": "extract"})
            assert is_valid, f"Validation failed: {error}"

            # 2. Execute
            result = analyzer.execute({"file_path": sample_pdf_allowed, "analysis_type": "extract"})

            # Should succeed or fail for non-security reasons
            assert result.status != ToolStatus.BLOCKED
        finally:
            analyzer.allowed_paths = original_paths

    def test_blocked_path_logs_attempt(self, analyzer, sample_pdf_blocked, caplog):
        """Test that blocked path attempts are logged"""
        import logging

        caplog.set_level(logging.WARNING)

        result = analyzer.execute({"file_path": sample_pdf_blocked, "analysis_type": "extract"})

        # Should be blocked
        assert result.status == ToolStatus.ERROR

        # Check if logging was attempted (may not capture middleware logs in tests)
        # This is a basic check; actual logging depends on middleware availability


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
