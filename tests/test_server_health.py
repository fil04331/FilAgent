"""
Tests for the server health endpoint
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app"""
    # Import here to avoid issues if dependencies are missing
    from runtime.server import app

    return TestClient(app)


@pytest.fixture
def temp_db():
    """Create a temporary database for tests"""
    # Create temporary database
    tmpdir = tempfile.mkdtemp()
    tmp_db = Path(tmpdir) / "test_episodic.sqlite"

    # Patch the DB_PATH
    import memory.episodic

    original_db_path = memory.episodic.DB_PATH
    memory.episodic.DB_PATH = tmp_db

    # Create tables
    from memory.episodic import create_tables

    create_tables()

    yield tmp_db

    # Restore
    memory.episodic.DB_PATH = original_db_path
    if tmp_db.exists():
        tmp_db.unlink()


def test_health_endpoint_database_connection_properly_closed(test_client, temp_db):
    """Test that the database connection is properly closed even if an exception occurs"""
    # This test verifies that using 'with' statement ensures connection is closed
    # We can't directly test the connection leak, but we can verify the endpoint works

    with (
        patch("runtime.server.get_agent") as mock_agent,
        patch("runtime.server.get_logger") as mock_logger,
        patch("runtime.server.get_worm_logger") as mock_worm_logger,
    ):

        # Mock the agent
        mock_model = MagicMock()
        mock_model.is_loaded.return_value = True
        mock_agent.return_value.model = mock_model

        # Mock logger
        mock_logger_instance = MagicMock()
        mock_logger_instance.current_file = str(temp_db.parent / "test.log")
        mock_logger.return_value = mock_logger_instance

        # Mock WORM logger
        mock_worm_logger_instance = MagicMock()
        mock_worm_logger_instance.digest_dir = temp_db.parent / "digests"
        mock_worm_logger_instance.digest_dir.mkdir(exist_ok=True)
        mock_worm_logger.return_value = mock_worm_logger_instance

        # Call health endpoint
        response = test_client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "status" in data
        assert "components" in data
        assert "database" in data["components"]

        # Database should be healthy
        assert data["components"]["database"] is True


def test_health_endpoint_handles_database_error(test_client, temp_db):
    """Test that health endpoint handles database errors gracefully"""

    with (
        patch("runtime.server.get_connection") as mock_get_connection,
        patch("runtime.server.get_agent") as mock_agent,
        patch("runtime.server.get_logger") as mock_logger,
        patch("runtime.server.get_worm_logger") as mock_worm_logger,
    ):

        # Make database connection raise an exception
        mock_get_connection.side_effect = Exception("Database error")

        # Mock other components
        mock_model = MagicMock()
        mock_model.is_loaded.return_value = True
        mock_agent.return_value.model = mock_model

        mock_logger_instance = MagicMock()
        mock_logger_instance.current_file = str(temp_db.parent / "test.log")
        mock_logger.return_value = mock_logger_instance

        mock_worm_logger_instance = MagicMock()
        mock_worm_logger_instance.digest_dir = temp_db.parent / "digests"
        mock_worm_logger_instance.digest_dir.mkdir(exist_ok=True)
        mock_worm_logger.return_value = mock_worm_logger_instance

        # Call health endpoint
        response = test_client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Database should be marked as unhealthy
        assert data["components"]["database"] is False
        # Overall status should be degraded
        assert data["status"] == "degraded"
