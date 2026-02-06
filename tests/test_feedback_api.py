"""
Tests for the feedback API endpoint
"""

import pytest
import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.server import app
from memory.episodic import add_message, get_connection
from memory.analytics import get_interaction_logs


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def setup_conversation(temp_db, temp_analytics_db):
    """Set up a test conversation with messages"""
    conversation_id = "test-feedback-conv"

    # Add messages to the conversation
    with patch("memory.episodic.DB_PATH", temp_db):
        add_message(conversation_id, "user", "What is 2+2?")
        add_message(conversation_id, "assistant", "2+2 equals 4")

    return conversation_id


@pytest.mark.integration
def test_submit_feedback_success(client, temp_db, temp_analytics_db, setup_conversation):
    """Test successfully submitting feedback"""
    conversation_id = setup_conversation

    with (
        patch("memory.episodic.DB_PATH", temp_db),
        patch("memory.analytics.DB_PATH", temp_analytics_db),
    ):

        response = client.post(
            f"/api/v1/feedback/{conversation_id}",
            json={"score": 5, "text": "Great response!", "latency_ms": 150.5, "tokens_used": 250},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert data["conversation_id"] == conversation_id
        assert data["feedback_score"] == 5

        # Wait a bit for background task to complete
        time.sleep(0.1)

        # Verify feedback was stored
        logs = get_interaction_logs(conversation_id=conversation_id)
        assert len(logs) == 1
        assert logs[0]["user_feedback_score"] == 5
        assert logs[0]["user_feedback_text"] == "Great response!"
        assert logs[0]["latency_ms"] == 150.5
        assert logs[0]["tokens_used"] == 250


@pytest.mark.integration
def test_submit_feedback_minimal(client, temp_db, temp_analytics_db, setup_conversation):
    """Test submitting feedback with only required fields"""
    conversation_id = setup_conversation

    with (
        patch("memory.episodic.DB_PATH", temp_db),
        patch("memory.analytics.DB_PATH", temp_analytics_db),
    ):

        response = client.post(f"/api/v1/feedback/{conversation_id}", json={"score": 3})

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert data["feedback_score"] == 3

        # Wait for background task
        time.sleep(0.1)

        logs = get_interaction_logs(conversation_id=conversation_id)
        assert len(logs) == 1
        assert logs[0]["user_feedback_score"] == 3


@pytest.mark.integration
def test_submit_feedback_nonexistent_conversation(client, temp_db, temp_analytics_db):
    """Test submitting feedback for a conversation that doesn't exist"""
    with (
        patch("memory.episodic.DB_PATH", temp_db),
        patch("memory.analytics.DB_PATH", temp_analytics_db),
    ):

        response = client.post("/api/v1/feedback/nonexistent-conv", json={"score": 5})

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


@pytest.mark.integration
def test_submit_feedback_invalid_score(client, temp_db, temp_analytics_db, setup_conversation):
    """Test submitting feedback with invalid score"""
    conversation_id = setup_conversation

    with (
        patch("memory.episodic.DB_PATH", temp_db),
        patch("memory.analytics.DB_PATH", temp_analytics_db),
    ):

        # Score too low
        response = client.post(f"/api/v1/feedback/{conversation_id}", json={"score": 0})
        assert response.status_code == 422  # Validation error

        # Score too high
        response = client.post(f"/api/v1/feedback/{conversation_id}", json={"score": 6})
        assert response.status_code == 422


@pytest.mark.integration
def test_submit_feedback_invalid_conversation_id(client, temp_db, temp_analytics_db):
    """Test submitting feedback with invalid conversation ID format"""
    with (
        patch("memory.episodic.DB_PATH", temp_db),
        patch("memory.analytics.DB_PATH", temp_analytics_db),
    ):

        # Invalid characters
        response = client.post("/api/v1/feedback/invalid@conv!", json={"score": 5})
        assert response.status_code == 422  # Path validation error

        # Too long (>128 chars)
        long_id = "a" * 129
        response = client.post(f"/api/v1/feedback/{long_id}", json={"score": 5})
        assert response.status_code == 422


@pytest.mark.integration
def test_submit_feedback_text_too_long(client, temp_db, temp_analytics_db, setup_conversation):
    """Test submitting feedback with text exceeding max length"""
    conversation_id = setup_conversation

    with (
        patch("memory.episodic.DB_PATH", temp_db),
        patch("memory.analytics.DB_PATH", temp_analytics_db),
    ):

        # Text too long (>2000 chars)
        long_text = "a" * 2001
        response = client.post(
            f"/api/v1/feedback/{conversation_id}", json={"score": 5, "text": long_text}
        )
        assert response.status_code == 422


@pytest.mark.integration
def test_submit_feedback_negative_metrics(client, temp_db, temp_analytics_db, setup_conversation):
    """Test submitting feedback with negative metrics"""
    conversation_id = setup_conversation

    with (
        patch("memory.episodic.DB_PATH", temp_db),
        patch("memory.analytics.DB_PATH", temp_analytics_db),
    ):

        # Negative latency
        response = client.post(
            f"/api/v1/feedback/{conversation_id}", json={"score": 5, "latency_ms": -10}
        )
        assert response.status_code == 422

        # Negative tokens
        response = client.post(
            f"/api/v1/feedback/{conversation_id}", json={"score": 5, "tokens_used": -100}
        )
        assert response.status_code == 422


@pytest.mark.integration
def test_submit_feedback_with_hashes(client, temp_db, temp_analytics_db, setup_conversation):
    """Test that input/output hashes are computed correctly"""
    conversation_id = setup_conversation

    with (
        patch("memory.episodic.DB_PATH", temp_db),
        patch("memory.analytics.DB_PATH", temp_analytics_db),
    ):

        response = client.post(f"/api/v1/feedback/{conversation_id}", json={"score": 5})

        assert response.status_code == 200

        # Wait for background task
        time.sleep(0.1)

        logs = get_interaction_logs(conversation_id=conversation_id)
        assert len(logs) == 1

        # Verify hashes were computed
        assert logs[0]["input_hash"] is not None
        assert logs[0]["output_hash"] is not None
        assert len(logs[0]["input_hash"]) == 64  # SHA256
        assert len(logs[0]["output_hash"]) == 64


@pytest.mark.integration
def test_submit_feedback_metadata_added(client, temp_db, temp_analytics_db, setup_conversation):
    """Test that metadata is added automatically"""
    conversation_id = setup_conversation

    with (
        patch("memory.episodic.DB_PATH", temp_db),
        patch("memory.analytics.DB_PATH", temp_analytics_db),
    ):

        response = client.post(f"/api/v1/feedback/{conversation_id}", json={"score": 4})

        assert response.status_code == 200

        # Wait for background task
        time.sleep(0.1)

        logs = get_interaction_logs(conversation_id=conversation_id)
        assert len(logs) == 1

        # Verify metadata was added
        assert logs[0]["metadata"] is not None
        assert "submitted_at" in logs[0]["metadata"]
        assert "message_count" in logs[0]["metadata"]
        assert logs[0]["metadata"]["message_count"] == 2  # user + assistant


@pytest.mark.integration
def test_submit_multiple_feedback_same_conversation(
    client, temp_db, temp_analytics_db, setup_conversation
):
    """Test submitting multiple feedback entries for the same conversation"""
    conversation_id = setup_conversation

    with (
        patch("memory.episodic.DB_PATH", temp_db),
        patch("memory.analytics.DB_PATH", temp_analytics_db),
    ):

        # Submit first feedback
        response1 = client.post(
            f"/api/v1/feedback/{conversation_id}", json={"score": 4, "text": "Good"}
        )
        assert response1.status_code == 200

        # Submit second feedback
        response2 = client.post(
            f"/api/v1/feedback/{conversation_id}",
            json={"score": 5, "text": "Even better after clarification"},
        )
        assert response2.status_code == 200

        # Wait for background tasks
        time.sleep(0.2)

        # Both should be stored
        logs = get_interaction_logs(conversation_id=conversation_id)
        assert len(logs) == 2


@pytest.mark.integration
def test_submit_feedback_background_task_failure(
    client, temp_db, temp_analytics_db, setup_conversation
):
    """Test that feedback endpoint succeeds even if background storage fails"""
    conversation_id = setup_conversation

    with (
        patch("memory.episodic.DB_PATH", temp_db),
        patch("memory.analytics.DB_PATH", temp_analytics_db),
        patch("memory.analytics.add_interaction_log", side_effect=Exception("Storage failed")),
    ):

        # Should still return 200 even though storage will fail
        response = client.post(f"/api/v1/feedback/{conversation_id}", json={"score": 5})

        assert response.status_code == 200
        assert response.json()["status"] == "success"
