"""
Tests for the server API health check endpoint
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient

from runtime.server import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


def test_health_endpoint_does_not_create_directories(client, tmp_path):
    """
    Test that the health check endpoint does not create directories
    as a side effect. Health checks should be read-only.
    """
    # Create mock paths that don't exist
    non_existent_log_dir = tmp_path / "logs_that_dont_exist"
    non_existent_digest_dir = tmp_path / "digests_that_dont_exist"

    # Ensure they don't exist
    assert not non_existent_log_dir.exists()
    assert not non_existent_digest_dir.exists()

    # Mock the logger to return our test paths
    mock_logger = MagicMock()
    mock_logger.current_file = non_existent_log_dir / "test.log"

    mock_worm_logger = MagicMock()
    mock_worm_logger.digest_dir = non_existent_digest_dir

    with (
        patch("runtime.server.get_logger", return_value=mock_logger),
        patch("runtime.server.get_worm_logger", return_value=mock_worm_logger),
    ):

        # Call the health endpoint
        response = client.get("/health")

        # Health check should succeed or fail, but not create directories
        assert response.status_code == 200

        # Verify directories were NOT created
        assert not non_existent_log_dir.exists(), "Health check should not create log directory"
        assert (
            not non_existent_digest_dir.exists()
        ), "Health check should not create digest directory"

        # Verify the response structure
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "components" in data
        assert "logging" in data["components"]

        # Since directories don't exist, logging component should be False
        assert data["components"]["logging"] is False


def test_health_endpoint_detects_existing_directories(client, tmp_path):
    """
    Test that the health check correctly detects when directories exist
    """
    # Create mock paths that DO exist
    existing_log_dir = tmp_path / "logs_that_exist"
    existing_digest_dir = tmp_path / "digests_that_exist"

    # Create the directories
    existing_log_dir.mkdir(parents=True)
    existing_digest_dir.mkdir(parents=True)

    # Ensure they exist
    assert existing_log_dir.exists()
    assert existing_digest_dir.exists()

    # Mock the logger to return our test paths
    mock_logger = MagicMock()
    mock_logger.current_file = existing_log_dir / "test.log"

    mock_worm_logger = MagicMock()
    mock_worm_logger.digest_dir = existing_digest_dir

    with (
        patch("runtime.server.get_logger", return_value=mock_logger),
        patch("runtime.server.get_worm_logger", return_value=mock_worm_logger),
    ):

        # Call the health endpoint
        response = client.get("/health")

        assert response.status_code == 200

        # Verify the response
        data = response.json()
        assert "components" in data
        assert "logging" in data["components"]

        # Since directories exist, logging component should be True
        assert data["components"]["logging"] is True


def test_health_endpoint_basic_structure(client):
    """
    Test the basic structure of the health endpoint response
    """
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()

    # Check required fields
    assert "status" in data
    assert "timestamp" in data
    assert "components" in data

    # Check component checks
    components = data["components"]
    assert "model" in components
    assert "database" in components
    assert "logging" in components

    # All values should be boolean
    assert isinstance(components["model"], bool)
    assert isinstance(components["database"], bool)
    assert isinstance(components["logging"], bool)
