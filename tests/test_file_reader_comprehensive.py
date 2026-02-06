"""
Comprehensive tests for FileReaderTool

Tests cover:
- Basic file reading
- Path validation and allowlist enforcement
- Symlink protection
- File size limits
- Error handling
- Edge cases
"""

import pytest
from pathlib import Path
from tools.file_reader import FileReaderTool
from tools.base import ToolStatus


@pytest.fixture
def file_reader():
    """Create FileReaderTool instance"""
    return FileReaderTool()


@pytest.fixture
def temp_allowed_dir(tmp_path):
    """Create temporary allowed directory"""
    allowed_dir = tmp_path / "working_set"
    allowed_dir.mkdir(parents=True, exist_ok=True)
    return allowed_dir


@pytest.fixture
def file_reader_with_temp(file_reader, temp_allowed_dir):
    """FileReaderTool with temp directory in allowed paths"""
    file_reader.allowed_paths = [str(temp_allowed_dir) + "/"]
    return file_reader


class TestBasicFileReading:
    """Test basic file reading functionality"""

    def test_read_simple_file(self, file_reader_with_temp, temp_allowed_dir):
        """Test reading a simple text file"""
        test_file = temp_allowed_dir / "test.txt"
        test_content = "Hello, World!"
        test_file.write_text(test_content)

        result = file_reader_with_temp.execute({"file_path": str(test_file)})

        assert result.status == ToolStatus.SUCCESS
        assert result.output == test_content
        assert result.metadata["file_size"] == len(test_content)

    def test_read_multiline_file(self, file_reader_with_temp, temp_allowed_dir):
        """Test reading a file with multiple lines"""
        test_file = temp_allowed_dir / "multiline.txt"
        test_content = "Line 1\nLine 2\nLine 3"
        test_file.write_text(test_content)

        result = file_reader_with_temp.execute({"file_path": str(test_file)})

        assert result.status == ToolStatus.SUCCESS
        assert "Line 1" in result.output
        assert "Line 2" in result.output
        assert "Line 3" in result.output

    def test_read_empty_file(self, file_reader_with_temp, temp_allowed_dir):
        """Test reading an empty file"""
        test_file = temp_allowed_dir / "empty.txt"
        test_file.write_text("")

        result = file_reader_with_temp.execute({"file_path": str(test_file)})

        assert result.status == ToolStatus.SUCCESS
        assert result.output == ""
        assert result.metadata["file_size"] == 0

    def test_read_file_with_unicode(self, file_reader_with_temp, temp_allowed_dir):
        """Test reading a file with Unicode characters"""
        test_file = temp_allowed_dir / "unicode.txt"
        test_content = "Héllo, Wörld! 你好世界"
        test_file.write_text(test_content, encoding="utf-8")

        result = file_reader_with_temp.execute({"file_path": str(test_file)})

        assert result.status == ToolStatus.SUCCESS
        assert result.output == test_content


class TestArgumentValidation:
    """Test argument validation"""

    def test_missing_file_path_argument(self, file_reader):
        """Test that missing file_path argument is caught"""
        result = file_reader.execute({})

        assert result.status == ToolStatus.BLOCKED
        assert "file_path" in result.error

    def test_invalid_argument_type(self, file_reader):
        """Test that non-dict arguments are rejected"""
        is_valid, error = file_reader.validate_arguments("not_a_dict")

        assert is_valid is False
        assert "dictionary" in error

    def test_file_path_not_string(self, file_reader):
        """Test that non-string file_path is rejected"""
        result = file_reader.execute({"file_path": 123})

        assert result.status == ToolStatus.BLOCKED
        assert "string" in result.error

    def test_empty_file_path(self, file_reader):
        """Test that empty file_path is rejected"""
        result = file_reader.execute({"file_path": ""})

        assert result.status == ToolStatus.BLOCKED
        assert "empty" in result.error

    def test_file_path_too_long(self, file_reader):
        """Test that extremely long file paths are rejected"""
        long_path = "a" * 5000
        result = file_reader.execute({"file_path": long_path})

        assert result.status == ToolStatus.BLOCKED
        assert "too long" in result.error

    def test_null_byte_in_path(self, file_reader):
        """Test that null bytes in path are detected"""
        result = file_reader.execute({"file_path": "test\0file.txt"})

        assert result.status == ToolStatus.BLOCKED
        assert "Null byte" in result.error


class TestPathAllowlist:
    """Test path allowlist enforcement"""

    def test_path_not_in_allowlist(self, file_reader_with_temp, tmp_path):
        """Test that paths outside allowlist are blocked"""
        forbidden_dir = tmp_path / "forbidden"
        forbidden_dir.mkdir()
        test_file = forbidden_dir / "test.txt"
        test_file.write_text("Should not be readable")

        result = file_reader_with_temp.execute({"file_path": str(test_file)})

        assert result.status == ToolStatus.BLOCKED
        assert "not allowed" in result.error

    def test_path_in_allowlist(self, file_reader_with_temp, temp_allowed_dir):
        """Test that paths in allowlist are allowed"""
        test_file = temp_allowed_dir / "test.txt"
        test_file.write_text("Content")

        result = file_reader_with_temp.execute({"file_path": str(test_file)})

        assert result.status == ToolStatus.SUCCESS

    def test_subdirectory_in_allowlist(self, file_reader_with_temp, temp_allowed_dir):
        """Test that subdirectories in allowlist are allowed"""
        subdir = temp_allowed_dir / "subdir"
        subdir.mkdir()
        test_file = subdir / "test.txt"
        test_file.write_text("Content")

        result = file_reader_with_temp.execute({"file_path": str(test_file)})

        assert result.status == ToolStatus.SUCCESS


class TestFileValidation:
    """Test file existence and type validation"""

    def test_file_not_found(self, file_reader_with_temp, temp_allowed_dir):
        """Test reading non-existent file"""
        nonexistent_file = temp_allowed_dir / "nonexistent.txt"

        result = file_reader_with_temp.execute({"file_path": str(nonexistent_file)})

        # Path checking happens first, so non-existent files get BLOCKED
        assert result.status == ToolStatus.BLOCKED
        assert "not allowed" in result.error

    def test_path_is_directory(self, file_reader_with_temp, temp_allowed_dir):
        """Test that directories are rejected"""
        result = file_reader_with_temp.execute({"file_path": str(temp_allowed_dir)})

        assert result.status == ToolStatus.ERROR
        assert "not a file" in result.error


class TestFileSizeLimit:
    """Test file size limit enforcement"""

    def test_file_within_size_limit(self, file_reader_with_temp, temp_allowed_dir):
        """Test reading file within size limit"""
        test_file = temp_allowed_dir / "normal.txt"
        test_content = "a" * 1000  # 1KB
        test_file.write_text(test_content)

        result = file_reader_with_temp.execute({"file_path": str(test_file)})

        assert result.status == ToolStatus.SUCCESS

    def test_file_exceeds_size_limit(self, file_reader_with_temp, temp_allowed_dir):
        """Test that files exceeding size limit are blocked"""
        # Temporarily reduce max size for testing
        original_max = file_reader_with_temp.max_file_size
        file_reader_with_temp.max_file_size = 100  # 100 bytes

        test_file = temp_allowed_dir / "large.txt"
        test_content = "a" * 200  # 200 bytes
        test_file.write_text(test_content)

        result = file_reader_with_temp.execute({"file_path": str(test_file)})

        assert result.status == ToolStatus.BLOCKED
        assert "too large" in result.error

        # Restore original max size
        file_reader_with_temp.max_file_size = original_max


class TestSymlinkProtection:
    """Test symlink protection"""

    @pytest.mark.skipif(
        not hasattr(Path, "symlink_to"), reason="Symlinks not supported on this platform"
    )
    def test_symlink_within_allowlist(self, file_reader_with_temp, temp_allowed_dir):
        """Test that symlinks within allowlist are handled"""
        target_file = temp_allowed_dir / "target.txt"
        target_file.write_text("Target content")

        symlink_file = temp_allowed_dir / "link.txt"
        try:
            symlink_file.symlink_to(target_file)

            result = file_reader_with_temp.execute({"file_path": str(symlink_file)})

            # Behavior depends on symlink handling
            # Should either read successfully or block
            assert result.status in [ToolStatus.SUCCESS, ToolStatus.BLOCKED]
        except OSError:
            # Skip if symlink creation fails (e.g., permissions)
            pytest.skip("Cannot create symlinks")


class TestErrorHandling:
    """Test error handling"""

    def test_binary_file_decode_error(self, file_reader_with_temp, temp_allowed_dir):
        """Test handling of binary files that can't be decoded as UTF-8"""
        # Create a binary file with invalid UTF-8
        test_file = temp_allowed_dir / "binary.bin"
        test_file.write_bytes(b"\x80\x81\x82\x83")  # Invalid UTF-8

        result = file_reader_with_temp.execute({"file_path": str(test_file)})

        # Should get an error trying to decode as UTF-8
        assert result.status == ToolStatus.ERROR
        assert "Failed to read file" in result.error


class TestMetadata:
    """Test metadata in results"""

    def test_metadata_contains_file_path(self, file_reader_with_temp, temp_allowed_dir):
        """Test that metadata contains file path"""
        test_file = temp_allowed_dir / "test.txt"
        test_file.write_text("Content")

        result = file_reader_with_temp.execute({"file_path": str(test_file)})

        assert result.status == ToolStatus.SUCCESS
        assert "file_path" in result.metadata
        assert str(test_file) in result.metadata["file_path"]

    def test_metadata_contains_file_size(self, file_reader_with_temp, temp_allowed_dir):
        """Test that metadata contains file size"""
        test_file = temp_allowed_dir / "test.txt"
        test_content = "Test content"
        test_file.write_text(test_content)

        result = file_reader_with_temp.execute({"file_path": str(test_file)})

        assert result.status == ToolStatus.SUCCESS
        assert "file_size" in result.metadata
        assert result.metadata["file_size"] == len(test_content)


class TestDefaultAllowedPaths:
    """Test default allowed paths"""

    def test_default_allowed_paths_set(self):
        """Test that default allowed paths are configured"""
        tool = FileReaderTool()

        assert len(tool.allowed_paths) > 0
        assert "working_set/" in tool.allowed_paths

    def test_default_max_file_size_set(self):
        """Test that default max file size is set"""
        tool = FileReaderTool()

        assert tool.max_file_size > 0
        assert tool.max_file_size == 10 * 1024 * 1024  # 10 MB


class TestParametersSchema:
    """Test parameters schema"""

    def test_get_parameters_schema(self, file_reader):
        """Test that parameters schema is properly defined"""
        schema = file_reader._get_parameters_schema()

        assert schema["type"] == "object"
        assert "file_path" in schema["properties"]
        assert "file_path" in schema["required"]


class TestEdgeCases:
    """Test edge cases"""

    def test_file_with_special_characters_in_name(self, file_reader_with_temp, temp_allowed_dir):
        """Test reading file with special characters"""
        test_file = temp_allowed_dir / "file-with_special.chars.txt"
        test_file.write_text("Content")

        result = file_reader_with_temp.execute({"file_path": str(test_file)})

        assert result.status == ToolStatus.SUCCESS

    def test_file_with_spaces_in_name(self, file_reader_with_temp, temp_allowed_dir):
        """Test reading file with spaces in name"""
        test_file = temp_allowed_dir / "file with spaces.txt"
        test_file.write_text("Content")

        result = file_reader_with_temp.execute({"file_path": str(test_file)})

        assert result.status == ToolStatus.SUCCESS

    def test_deeply_nested_file(self, file_reader_with_temp, temp_allowed_dir):
        """Test reading deeply nested file"""
        nested_dir = temp_allowed_dir / "a" / "b" / "c" / "d"
        nested_dir.mkdir(parents=True)
        test_file = nested_dir / "test.txt"
        test_file.write_text("Content")

        result = file_reader_with_temp.execute({"file_path": str(test_file)})

        assert result.status == ToolStatus.SUCCESS

    def test_file_with_newlines_in_content(self, file_reader_with_temp, temp_allowed_dir):
        """Test file with various newline formats"""
        test_file = temp_allowed_dir / "newlines.txt"
        test_content = "Line1\nLine2\r\nLine3\rLine4"
        test_file.write_text(test_content)

        result = file_reader_with_temp.execute({"file_path": str(test_file)})

        assert result.status == ToolStatus.SUCCESS
        assert "Line1" in result.output
        assert "Line4" in result.output
