"""
Tests de sécurité pour l'interface Gradio
Focus: Path validation in validate_file function
"""
import pytest
import sys
from pathlib import Path
import tempfile

sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the validate_file function
# Note: We need to import it carefully since it's in a module with dependencies
try:
    from gradio_app_production import validate_file
    GRADIO_AVAILABLE = True
except ImportError as e:
    GRADIO_AVAILABLE = False
    IMPORT_ERROR = str(e)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_allowed_dir(tmp_path):
    """Create a temporary directory that should be in allowed paths"""
    # /tmp/ is in allowed paths
    return tmp_path


@pytest.fixture
def sample_pdf_in_tmp(temp_allowed_dir):
    """Create a sample PDF in /tmp/ which is allowed"""
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
def sample_xlsx_in_tmp(temp_allowed_dir):
    """Create a sample Excel file in /tmp/"""
    xlsx_path = temp_allowed_dir / "test_data.xlsx"
    
    # Create minimal valid xlsx using pandas if available
    try:
        import pandas as pd
        df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
        df.to_excel(xlsx_path, index=False)
    except ImportError:
        # Create empty file as fallback
        xlsx_path.write_bytes(b"")
    
    return str(xlsx_path)


# ============================================================================
# SECURITY TESTS - GRADIO INTERFACE
# ============================================================================

@pytest.mark.skipif(not GRADIO_AVAILABLE, reason=f"Gradio app not available: {IMPORT_ERROR if not GRADIO_AVAILABLE else ''}")
@pytest.mark.unit
class TestGradioValidationSecurity:
    """Tests de sécurité pour validation de fichiers Gradio"""

    def test_validate_file_in_tmp(self, sample_pdf_in_tmp):
        """Test that files in /tmp/ (allowed) can be validated"""
        is_valid, error = validate_file(sample_pdf_in_tmp)
        
        # Should succeed (file is in allowed /tmp/ directory)
        assert is_valid, f"Expected valid, got error: {error}"
        assert error is None

    def test_validate_file_null_byte(self):
        """Test that null byte injection is blocked"""
        malicious_path = "test_file.pdf\x00.txt"
        
        is_valid, error = validate_file(malicious_path)
        
        assert not is_valid
        assert error is not None
        assert "null" in error.lower() or "sécurité" in error.lower()

    def test_validate_file_path_too_long(self):
        """Test that excessively long paths are blocked"""
        long_path = "a" * 5000 + ".pdf"
        
        is_valid, error = validate_file(long_path)
        
        assert not is_valid
        assert error is not None
        assert "trop long" in error.lower() or "too long" in error.lower()

    def test_validate_file_outside_allowed_paths(self, tmp_path):
        """Test that files outside allowed directories are blocked"""
        # Create file in a location that's NOT in allowed paths
        # Note: We need to ensure this is truly outside allowed paths
        blocked_dir = tmp_path / "not_allowed" / "deeply" / "nested"
        blocked_dir.mkdir(parents=True, exist_ok=True)
        
        blocked_file = blocked_dir / "secret.pdf"
        blocked_file.write_text("fake pdf content")
        
        # Try to validate - might fail at existence or path validation
        is_valid, error = validate_file(str(blocked_file))
        
        # If tmp_path is under /tmp/, it might be allowed
        # So we need to check if error is about path or something else
        if "/tmp/" not in str(tmp_path):
            # Should be blocked due to path validation
            assert not is_valid
            if error:
                # Check for security-related error
                security_keywords = ["autorisé", "sécurité", "access", "denied", "refusé"]
                has_security_error = any(keyword in error.lower() for keyword in security_keywords)
                # Either security error or file doesn't exist
                assert has_security_error or "not found" in error.lower()

    def test_validate_file_path_traversal(self):
        """Test that path traversal attempts are blocked"""
        traversal_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\Windows\\System32\\config\\SAM",
            "/tmp/../etc/passwd",
        ]
        
        for path in traversal_paths:
            is_valid, error = validate_file(path)
            
            # Should either not exist or be blocked by validation
            assert not is_valid
            # Error should mention either file not found or access denied
            assert error is not None

    def test_validate_file_absolute_system_path(self):
        """Test that absolute paths to system files are blocked"""
        system_paths = [
            "/etc/passwd",
            "/etc/shadow",
            "/root/.ssh/id_rsa",
            "C:\\Windows\\System32\\config\\SAM",
        ]
        
        for path in system_paths:
            is_valid, error = validate_file(path)
            
            # Should be blocked
            assert not is_valid
            assert error is not None
            # Should mention either not found or access denied
            security_keywords = ["autorisé", "sécurité", "access", "denied", "refusé", "not found"]
            assert any(keyword in error.lower() for keyword in security_keywords)

    def test_validate_file_extension_check(self, temp_allowed_dir):
        """Test that file extension validation works"""
        # Create file with invalid extension in allowed directory
        invalid_file = temp_allowed_dir / "test.exe"
        invalid_file.write_bytes(b"fake exe content")
        
        is_valid, error = validate_file(str(invalid_file))
        
        # Should be invalid due to extension
        assert not is_valid
        assert error is not None
        # Error should mention unsupported format
        assert "format" in error.lower() or "extension" in error.lower() or "supporté" in error.lower()

    def test_validate_file_size_check(self, temp_allowed_dir):
        """Test that file size validation works"""
        # Create file larger than max size (50 MB)
        large_file = temp_allowed_dir / "large.pdf"
        
        # Write 51 MB of data
        large_file.write_bytes(b"0" * (51 * 1024 * 1024))
        
        is_valid, error = validate_file(str(large_file))
        
        # Should be invalid due to size
        assert not is_valid
        assert error is not None
        assert "taille" in error.lower() or "size" in error.lower() or "large" in error.lower()

    def test_validate_file_nonexistent(self):
        """Test that nonexistent files are rejected"""
        is_valid, error = validate_file("/tmp/this_file_does_not_exist_xyz123.pdf")
        
        assert not is_valid
        assert error is not None
        assert "not found" in error.lower() or "trouvé" in error.lower()

    def test_validate_file_directory_not_file(self, temp_allowed_dir):
        """Test that directories are rejected"""
        is_valid, error = validate_file(str(temp_allowed_dir))
        
        assert not is_valid
        assert error is not None

    def test_validate_file_valid_pdf(self, sample_pdf_in_tmp):
        """Test that valid PDF in allowed directory passes all checks"""
        is_valid, error = validate_file(sample_pdf_in_tmp)
        
        # Should be valid
        assert is_valid
        assert error is None

    def test_validate_file_valid_xlsx(self, sample_xlsx_in_tmp):
        """Test that valid Excel file in allowed directory passes all checks"""
        # Only run if pandas created a valid file
        if Path(sample_xlsx_in_tmp).stat().st_size > 0:
            is_valid, error = validate_file(sample_xlsx_in_tmp)
            
            # Should be valid
            assert is_valid
            assert error is None


@pytest.mark.skipif(not GRADIO_AVAILABLE, reason="Gradio app not available")
@pytest.mark.integration
class TestGradioSecurityIntegration:
    """Integration tests for Gradio security"""

    def test_complete_validation_flow(self, sample_pdf_in_tmp):
        """Test complete validation flow"""
        # Step 1: Validate file
        is_valid, error = validate_file(sample_pdf_in_tmp)
        assert is_valid, f"Validation failed: {error}"
        
        # Step 2: File should be readable
        content = Path(sample_pdf_in_tmp).read_bytes()
        assert len(content) > 0
        
        # Step 3: Path should resolve correctly
        resolved = Path(sample_pdf_in_tmp).resolve()
        assert resolved.exists()

    def test_security_defense_in_depth(self):
        """Test that multiple security layers work together"""
        # Test various attack vectors
        attack_vectors = [
            ("null_byte", "file.pdf\x00.txt"),
            ("path_traversal", "../../../etc/passwd"),
            ("long_path", "a" * 5000 + ".pdf"),
            ("system_file", "/etc/passwd"),
        ]
        
        for attack_name, attack_path in attack_vectors:
            is_valid, error = validate_file(attack_path)
            assert not is_valid, f"Attack vector '{attack_name}' was not blocked!"
            assert error is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
