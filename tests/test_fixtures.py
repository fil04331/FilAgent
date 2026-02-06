"""
Tests for validating fixture functionality and isolation

This module tests that fixtures properly:
- Isolate state between tests
- Clean up resources
- Provide correct types and interfaces
"""

import pytest
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

from runtime.model_interface import GenerationConfig
from tools.base import ToolStatus

# Mark all tests in this module as fixture tests
pytestmark = pytest.mark.fixtures


class TestFixtureIsolation:
    """Test that fixtures properly isolate state between tests"""

    def test_temp_db_isolation_first(self, temp_db):
        """First test to verify temp_db isolation"""
        # Write to database
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO conversations (id, conversation_id, task_id, created_at, updated_at)
            VALUES ('test-1', 'test-1', 'task-1', '2024-01-01', '2024-01-01')
        """)
        conn.commit()
        conn.close()

        # Verify data exists
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM conversations")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 1

    def test_temp_db_isolation_second(self, temp_db):
        """Second test to verify temp_db is clean (isolated from first test)"""
        # Database should be empty (new instance)
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM conversations")
        count = cursor.fetchone()[0]
        conn.close()

        # Should be 0 if properly isolated
        assert count == 0


class TestMockModelFixtures:
    """Test mock model fixtures"""

    def test_mock_model_basic(self, mock_model):
        """Test basic mock model fixture"""
        result = mock_model.generate("test prompt", GenerationConfig())

        assert result.text == "I'll help with that task."
        assert result.finish_reason == "stop"
        assert result.tokens_generated > 0
        assert result.tool_calls is None

    def test_mock_model_with_custom_responses(self, mock_model_with_responses):
        """Test factory fixture for custom responses"""
        custom_model = mock_model_with_responses(["First response", "Second response"])

        result1 = custom_model.generate("prompt 1", GenerationConfig())
        result2 = custom_model.generate("prompt 2", GenerationConfig())

        assert result1.text == "First response"
        assert result2.text == "Second response"

    def test_mock_tool_model(self, mock_tool_model):
        """Test mock model with tool calls"""
        result = mock_tool_model.generate("test", GenerationConfig())

        assert result.tool_calls is not None
        assert len(result.tool_calls) > 0
        assert "name" in result.tool_calls[0]


class TestToolMockFixtures:
    """Test tool mock fixtures"""

    def test_mock_tool_success(self, mock_tool_success):
        """Test successful tool mock"""
        result = mock_tool_success.execute({"param": "value"})

        assert result.status == ToolStatus.SUCCESS
        assert "successfully" in result.output
        assert "metadata" in result.__dict__

    def test_mock_tool_failure(self, mock_tool_failure):
        """Test failing tool mock"""
        result = mock_tool_failure.execute({"param": "value"})

        assert result.status == ToolStatus.ERROR
        assert result.error_message == "Simulated failure"


class TestUtilityFixtures:
    """Test utility helper fixtures"""

    def test_assert_file_contains(self, assert_file_contains, tmp_path):
        """Test file content assertion helper"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("This is test content")

        # Should not raise
        assert_file_contains(test_file, "test content")

        # Should raise
        with pytest.raises(AssertionError):
            assert_file_contains(test_file, "missing content")

    def test_assert_json_file_valid(self, assert_json_file_valid, tmp_path):
        """Test JSON validation helper"""
        json_file = tmp_path / "test.json"
        json_file.write_text('{"key1": "value1", "key2": 123}')

        data = assert_json_file_valid(json_file, {"key1": str, "key2": int})

        assert data["key1"] == "value1"
        assert data["key2"] == 123

    def test_conversation_factory(self, conversation_factory, temp_db):
        """Test conversation factory fixture"""
        conv_id = conversation_factory(
            "test-conv",
            [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi there"}],
            task_id="test-task",
        )

        assert conv_id == "test-conv"

        # Verify in database
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM messages WHERE conversation_id = ?", (conv_id,))
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 2


class TestIsolatedFileSystemFixtures:
    """Test isolated filesystem fixtures"""

    def test_isolated_fs_structure(self, isolated_fs):
        """Test isolated filesystem has correct structure"""
        assert "root" in isolated_fs
        assert "logs" in isolated_fs
        assert "logs_events" in isolated_fs
        assert "logs_decisions" in isolated_fs
        assert "logs_digests" in isolated_fs
        assert "memory" in isolated_fs
        assert "config" in isolated_fs

        # All paths should exist
        for key, path in isolated_fs.items():
            if isinstance(path, Path):
                assert path.exists(), f"{key} path does not exist"

    def test_isolated_logging(self, isolated_logging):
        """Test isolated logging fixture"""
        assert "event_logger" in isolated_logging
        assert "worm_logger" in isolated_logging
        assert "event_log_dir" in isolated_logging
        assert "digest_dir" in isolated_logging

        # Directories should exist
        assert isolated_logging["event_log_dir"].exists()
        assert isolated_logging["digest_dir"].exists()


class TestEnvironmentIsolation:
    """Test environment variable isolation"""

    def test_env_isolation_first(self, monkeypatch):
        """Set an environment variable in first test"""
        monkeypatch.setenv("TEST_FIXTURE_VAR", "value1")
        import os

        assert os.environ.get("TEST_FIXTURE_VAR") == "value1"

    def test_env_isolation_second(self):
        """Verify environment variable doesn't leak to second test"""
        import os

        # Should not exist due to clean_environment autouse fixture
        assert os.environ.get("TEST_FIXTURE_VAR") is None


class TestConfigFixture:
    """Test configuration fixture"""

    def test_test_config(self, test_config):
        """Test configuration fixture"""
        assert test_config.model.backend == "mock"
        assert test_config.model.context_size == 2048
        assert test_config.agent.max_iterations == 5
        assert test_config.agent.timeout == 30
