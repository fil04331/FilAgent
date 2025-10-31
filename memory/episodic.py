"""Mémoire épisodique : stockage des conversations et contexte à court terme."""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional


DB_PATH = Path("memory/episodic.sqlite")


def get_connection():
    """Obtenir une connexion à la base de données"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    """Créer les tables nécessaires si elles n'existent pas"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            task_id TEXT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            message_type TEXT DEFAULT 'text',
            metadata TEXT,
            FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
        )
    """)
    
    # Index pour performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversation_id ON messages(conversation_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON messages(timestamp)")
    
    conn.commit()
    conn.close()
    print(f"Tables créées dans {DB_PATH}")


def add_message(conversation_id: str, role: str, content: str, 
                task_id: Optional[str] = None, 
                message_type: str = "text",
                metadata: Optional[Dict] = None):
    """Ajouter un message à une conversation"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        # Créer la conversation si elle n'existe pas
        cursor.execute("""
            INSERT OR IGNORE INTO conversations (conversation_id, updated_at)
            VALUES (?, CURRENT_TIMESTAMP)
        """, (conversation_id,))
        
        # Ajouter le message
        metadata_json = json.dumps(metadata) if metadata else None
        cursor.execute("""
            INSERT INTO messages (conversation_id, task_id, role, content, message_type, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (conversation_id, task_id, role, content, message_type, metadata_json))
        
        # Mettre à jour le timestamp de la conversation
        cursor.execute("""
            UPDATE conversations
            SET updated_at = CURRENT_TIMESTAMP
            WHERE conversation_id = ?
        """, (conversation_id,))
        
        conn.commit()
    finally:
        conn.close()


def get_messages(conversation_id: str, limit: int = 100) -> List[Dict]:
    """Récupérer les messages d'une conversation"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT role, content, task_id, timestamp, message_type, metadata
            FROM messages
            WHERE conversation_id = ?
            ORDER BY timestamp ASC
            LIMIT ?
        """, (conversation_id, limit))
        
        messages = []
        for row in cursor.fetchall():
            msg = dict(row)
            if msg['metadata']:
                try:
                    msg['metadata'] = json.loads(msg['metadata'])
                except (json.JSONDecodeError, TypeError):
                    # Si le JSON est invalide, garder None
                    msg['metadata'] = None
            messages.append(msg)
        
        return messages
    finally:
        conn.close()


def cleanup_old_conversations(ttl_days: int = 30):
    """Supprimer les conversations plus anciennes que ttl_days"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        
        cutoff_date = datetime.now() - timedelta(days=ttl_days)
        
        # Supprimer les messages  
        cursor.execute("""
            DELETE FROM messages
            WHERE conversation_id IN (
                SELECT conversation_id FROM conversations
                WHERE updated_at < ?
            )
        """, (cutoff_date,))
        
        # Supprimer les conversations
        cursor.execute("""
            DELETE FROM conversations
            WHERE updated_at < ?
        """, (cutoff_date,))
        
        deleted = cursor.rowcount
        conn.commit()
        return deleted
    finally:
        conn.close()


if __name__ == "__main__":
    # Test : créer les tables
    create_tables()
