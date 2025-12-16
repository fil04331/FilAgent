"""
Analytics module for storing interaction logs and user feedback.

This module captures user feedback and telemetry data to transform
interactions into a data asset for future model improvement.
"""

import json
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


DB_PATH = Path("memory/analytics.sqlite")


def get_connection():
    """Get a connection to the analytics database"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    """Create the necessary tables if they don't exist"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interaction_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            input_hash TEXT,
            output_hash TEXT,
            user_feedback_score INTEGER CHECK(user_feedback_score BETWEEN 1 AND 5),
            user_feedback_text TEXT,
            latency_ms REAL,
            tokens_used INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT
        )
    """)
    
    # Index for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversation_id ON interaction_logs(conversation_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_score ON interaction_logs(user_feedback_score)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON interaction_logs(created_at)")
    
    conn.commit()
    conn.close()
    print(f"Analytics tables created in {DB_PATH}")


def compute_hash(content: str) -> str:
    """Compute SHA256 hash of content for telemetry tracking"""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def add_interaction_log(
    conversation_id: str,
    user_feedback_score: int,
    user_feedback_text: Optional[str] = None,
    input_hash: Optional[str] = None,
    output_hash: Optional[str] = None,
    latency_ms: Optional[float] = None,
    tokens_used: Optional[int] = None,
    metadata: Optional[Dict] = None
):
    """
    Add an interaction log entry with user feedback.
    
    Args:
        conversation_id: Unique identifier for the conversation
        user_feedback_score: Score from 1-5 (1=poor, 5=excellent)
        user_feedback_text: Optional textual feedback from user
        input_hash: SHA256 hash of the input message
        output_hash: SHA256 hash of the output response
        latency_ms: Response latency in milliseconds
        tokens_used: Total tokens used (prompt + completion)
        metadata: Additional metadata as JSON
    """
    if user_feedback_score < 1 or user_feedback_score > 5:
        raise ValueError("user_feedback_score must be between 1 and 5")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    metadata_json = json.dumps(metadata) if metadata else None
    
    cursor.execute("""
        INSERT INTO interaction_logs (
            conversation_id, input_hash, output_hash,
            user_feedback_score, user_feedback_text,
            latency_ms, tokens_used, metadata
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        conversation_id, input_hash, output_hash,
        user_feedback_score, user_feedback_text,
        latency_ms, tokens_used, metadata_json
    ))
    
    conn.commit()
    conn.close()


def get_interaction_logs(
    conversation_id: Optional[str] = None,
    min_score: Optional[int] = None,
    max_score: Optional[int] = None,
    limit: int = 100
) -> List[Dict]:
    """
    Retrieve interaction logs with optional filtering.
    
    Args:
        conversation_id: Filter by specific conversation
        min_score: Minimum feedback score (inclusive)
        max_score: Maximum feedback score (inclusive)
        limit: Maximum number of records to return
    
    Returns:
        List of interaction log records
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM interaction_logs WHERE 1=1"
    params = []
    
    if conversation_id:
        query += " AND conversation_id = ?"
        params.append(conversation_id)
    
    if min_score is not None:
        query += " AND user_feedback_score >= ?"
        params.append(min_score)
    
    if max_score is not None:
        query += " AND user_feedback_score <= ?"
        params.append(max_score)
    
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    
    logs = []
    for row in cursor.fetchall():
        log = dict(row)
        if log['metadata']:
            log['metadata'] = json.loads(log['metadata'])
        logs.append(log)
    
    conn.close()
    return logs


def get_feedback_stats(conversation_id: Optional[str] = None) -> Dict:
    """
    Get aggregated feedback statistics.
    
    Args:
        conversation_id: Optional filter by conversation
    
    Returns:
        Dictionary with count, average score, and score distribution
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT 
            COUNT(*) as total_count,
            AVG(user_feedback_score) as avg_score,
            SUM(CASE WHEN user_feedback_score = 1 THEN 1 ELSE 0 END) as score_1,
            SUM(CASE WHEN user_feedback_score = 2 THEN 1 ELSE 0 END) as score_2,
            SUM(CASE WHEN user_feedback_score = 3 THEN 1 ELSE 0 END) as score_3,
            SUM(CASE WHEN user_feedback_score = 4 THEN 1 ELSE 0 END) as score_4,
            SUM(CASE WHEN user_feedback_score = 5 THEN 1 ELSE 0 END) as score_5,
            AVG(latency_ms) as avg_latency_ms,
            AVG(tokens_used) as avg_tokens
        FROM interaction_logs
    """
    
    params = []
    if conversation_id:
        query += " WHERE conversation_id = ?"
        params.append(conversation_id)
    
    cursor.execute(query, params)
    row = cursor.fetchone()
    
    stats = dict(row) if row else {}
    conn.close()
    
    return stats


if __name__ == "__main__":
    # Test: create tables
    create_tables()
