"""
Tests for the analytics module and user feedback system
"""
import pytest
import sys
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from memory.analytics import (
    create_tables,
    add_interaction_log,
    get_interaction_logs,
    get_feedback_stats,
    compute_hash,
    get_connection
)


@pytest.fixture
def temp_analytics_db(tmp_path):
    """Create a temporary analytics database for testing"""
    temp_db = tmp_path / "test_analytics.sqlite"
    
    # Patch DB_PATH to use our temp database
    with patch('memory.analytics.DB_PATH', temp_db):
        create_tables()
        yield temp_db


@pytest.mark.unit
def test_create_analytics_tables(temp_analytics_db):
    """Test that analytics tables are created correctly"""
    assert temp_analytics_db.exists()
    
    # Verify tables exist
    conn = sqlite3.connect(str(temp_analytics_db))
    cursor = conn.cursor()
    
    # Check interaction_logs table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='interaction_logs'")
    assert cursor.fetchone() is not None
    
    # Check indexes exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_conversation_id'")
    assert cursor.fetchone() is not None
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_feedback_score'")
    assert cursor.fetchone() is not None
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_created_at'")
    assert cursor.fetchone() is not None
    
    conn.close()


@pytest.mark.unit
def test_compute_hash():
    """Test hash computation for telemetry"""
    content = "Hello, world!"
    hash1 = compute_hash(content)
    hash2 = compute_hash(content)
    
    # Same content should produce same hash
    assert hash1 == hash2
    
    # Different content should produce different hash
    hash3 = compute_hash("Different content")
    assert hash1 != hash3
    
    # Hash should be SHA256 (64 hex characters)
    assert len(hash1) == 64
    assert all(c in '0123456789abcdef' for c in hash1)


@pytest.mark.unit
def test_add_interaction_log(temp_analytics_db):
    """Test adding an interaction log with feedback"""
    with patch('memory.analytics.DB_PATH', temp_analytics_db):
        add_interaction_log(
            conversation_id="test-conv-1",
            user_feedback_score=5,
            user_feedback_text="Excellent response!",
            input_hash="input123",
            output_hash="output456",
            latency_ms=150.5,
            tokens_used=250
        )
        
        # Retrieve and verify
        logs = get_interaction_logs(conversation_id="test-conv-1")
        assert len(logs) == 1
        
        log = logs[0]
        assert log['conversation_id'] == "test-conv-1"
        assert log['user_feedback_score'] == 5
        assert log['user_feedback_text'] == "Excellent response!"
        assert log['input_hash'] == "input123"
        assert log['output_hash'] == "output456"
        assert log['latency_ms'] == 150.5
        assert log['tokens_used'] == 250


@pytest.mark.unit
def test_add_interaction_log_minimal(temp_analytics_db):
    """Test adding interaction log with minimal required fields"""
    with patch('memory.analytics.DB_PATH', temp_analytics_db):
        add_interaction_log(
            conversation_id="test-conv-2",
            user_feedback_score=3
        )
        
        logs = get_interaction_logs(conversation_id="test-conv-2")
        assert len(logs) == 1
        assert logs[0]['user_feedback_score'] == 3
        assert logs[0]['user_feedback_text'] is None


@pytest.mark.unit
def test_add_interaction_log_invalid_score(temp_analytics_db):
    """Test that invalid feedback scores are rejected"""
    with patch('memory.analytics.DB_PATH', temp_analytics_db):
        # Score too low
        with pytest.raises(ValueError, match="must be between 1 and 5"):
            add_interaction_log(
                conversation_id="test-conv-3",
                user_feedback_score=0
            )
        
        # Score too high
        with pytest.raises(ValueError, match="must be between 1 and 5"):
            add_interaction_log(
                conversation_id="test-conv-3",
                user_feedback_score=6
            )


@pytest.mark.unit
def test_get_interaction_logs_filtering(temp_analytics_db):
    """Test filtering interaction logs by various criteria"""
    with patch('memory.analytics.DB_PATH', temp_analytics_db):
        # Add multiple logs with different scores
        add_interaction_log("conv-1", user_feedback_score=5)
        add_interaction_log("conv-1", user_feedback_score=4)
        add_interaction_log("conv-2", user_feedback_score=2)
        add_interaction_log("conv-2", user_feedback_score=1)
        
        # Filter by conversation
        logs_conv1 = get_interaction_logs(conversation_id="conv-1")
        assert len(logs_conv1) == 2
        
        # Filter by min score
        logs_good = get_interaction_logs(min_score=4)
        assert len(logs_good) == 2
        assert all(log['user_feedback_score'] >= 4 for log in logs_good)
        
        # Filter by max score
        logs_bad = get_interaction_logs(max_score=2)
        assert len(logs_bad) == 2
        assert all(log['user_feedback_score'] <= 2 for log in logs_bad)
        
        # Filter by range
        logs_mid = get_interaction_logs(min_score=2, max_score=4)
        assert len(logs_mid) == 2


@pytest.mark.unit
def test_get_interaction_logs_limit(temp_analytics_db):
    """Test pagination limit on interaction logs"""
    with patch('memory.analytics.DB_PATH', temp_analytics_db):
        # Add 10 logs
        for i in range(10):
            add_interaction_log(f"conv-{i}", user_feedback_score=5)
        
        # Retrieve with limit
        logs = get_interaction_logs(limit=5)
        assert len(logs) == 5


@pytest.mark.unit
def test_get_feedback_stats(temp_analytics_db):
    """Test aggregated feedback statistics"""
    with patch('memory.analytics.DB_PATH', temp_analytics_db):
        # Add various feedback entries
        add_interaction_log("conv-1", user_feedback_score=5, latency_ms=100, tokens_used=200)
        add_interaction_log("conv-1", user_feedback_score=4, latency_ms=150, tokens_used=250)
        add_interaction_log("conv-2", user_feedback_score=3, latency_ms=200, tokens_used=300)
        add_interaction_log("conv-2", user_feedback_score=2, latency_ms=250, tokens_used=350)
        add_interaction_log("conv-3", user_feedback_score=1, latency_ms=300, tokens_used=400)
        
        # Get overall stats
        stats = get_feedback_stats()
        assert stats['total_count'] == 5
        assert stats['avg_score'] == 3.0  # (5+4+3+2+1)/5
        assert stats['score_5'] == 1
        assert stats['score_4'] == 1
        assert stats['score_3'] == 1
        assert stats['score_2'] == 1
        assert stats['score_1'] == 1
        assert stats['avg_latency_ms'] == 200.0  # (100+150+200+250+300)/5
        assert stats['avg_tokens'] == 300.0  # (200+250+300+350+400)/5
        
        # Get stats for specific conversation
        stats_conv1 = get_feedback_stats(conversation_id="conv-1")
        assert stats_conv1['total_count'] == 2
        assert stats_conv1['avg_score'] == 4.5  # (5+4)/2


@pytest.mark.unit
def test_interaction_log_metadata(temp_analytics_db):
    """Test storing and retrieving metadata"""
    with patch('memory.analytics.DB_PATH', temp_analytics_db):
        metadata = {
            "user_agent": "Mozilla/5.0",
            "session_id": "sess-123",
            "experiment": "A/B test variant A"
        }
        
        add_interaction_log(
            conversation_id="conv-meta",
            user_feedback_score=5,
            metadata=metadata
        )
        
        logs = get_interaction_logs(conversation_id="conv-meta")
        assert logs[0]['metadata'] == metadata


@pytest.mark.unit
def test_interaction_log_ordering(temp_analytics_db):
    """Test that logs can be retrieved with proper ordering"""
    with patch('memory.analytics.DB_PATH', temp_analytics_db):
        # Add logs in sequence
        add_interaction_log("conv-order", user_feedback_score=1, user_feedback_text="First")
        add_interaction_log("conv-order", user_feedback_score=2, user_feedback_text="Second")  
        add_interaction_log("conv-order", user_feedback_score=3, user_feedback_text="Third")
        
        # Get all logs
        logs = get_interaction_logs(conversation_id="conv-order", limit=100)
        
        # Verify we have 3 logs
        assert len(logs) == 3
        
        # Verify all scores are present
        scores = [log['user_feedback_score'] for log in logs]
        assert set(scores) == {1, 2, 3}
        
        # Verify all IDs are present and unique
        ids = [log['id'] for log in logs]
        assert len(ids) == len(set(ids))  # All unique
        
        # Verify text content
        texts = [log['user_feedback_text'] for log in logs]
        assert "First" in texts
        assert "Second" in texts
        assert "Third" in texts
