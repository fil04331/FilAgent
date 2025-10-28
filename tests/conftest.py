"""
Fixtures avancés pour les tests E2E et de conformité

Ce module fournit des fixtures sophistiqués pour:
- Mock models (simulation de modèles LLM)
- Bases de données temporaires (SQLite, FAISS)
- Systèmes de fichiers isolés
- Middlewares et composants système
"""

import os
import sys
import json
import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from unittest.mock import MagicMock, patch
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.model_interface import GenerationResult, GenerationConfig
from runtime.config import AgentConfig
from tools.base import ToolResult, ToolStatus


# ============================================================================
# FIXTURES: Mock Models
# ============================================================================

@dataclass
class MockGenerationResult:
    """Mock result for generation"""
    text: str
    finish_reason: str = "stop"
    tokens_generated: int = 100
    prompt_tokens: int = 50
    total_tokens: int = 150
    tool_calls: Optional[List[Dict]] = None


class MockModelInterface:
    """Mock LLM interface pour les tests"""

    def __init__(self, responses: Optional[List[str]] = None):
        """
        Args:
            responses: Liste de réponses prédéfinies (cycle automatiquement)
        """
        self.responses = responses or [
            "I'll help with that task.",
            "Let me analyze the information.",
            "Here is the final response."
        ]
        self.call_count = 0
        self.calls_history = []
        self._loaded = True

    def load(self, model_path: str, config: Dict) -> bool:
        """Simule le chargement du modèle"""
        self._loaded = True
        return True

    def generate(
        self,
        prompt: str,
        config: GenerationConfig,
        system_prompt: Optional[str] = None
    ) -> GenerationResult:
        """Simule la génération de texte"""
        # Enregistrer l'appel
        self.calls_history.append({
            'prompt': prompt,
            'config': config,
            'system_prompt': system_prompt,
            'timestamp': datetime.utcnow().isoformat()
        })

        # Retourner la réponse suivante (cycle)
        response_text = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1

        return GenerationResult(
            text=response_text,
            finish_reason="stop",
            tokens_generated=len(response_text.split()),
            prompt_tokens=len(prompt.split()),
            total_tokens=len(prompt.split()) + len(response_text.split()),
            tool_calls=None
        )

    def unload(self):
        """Simule le déchargement du modèle"""
        self._loaded = False

    def is_loaded(self) -> bool:
        """Vérifie si le modèle est chargé"""
        return self._loaded


class MockToolCallModel(MockModelInterface):
    """Mock model qui simule des appels d'outils"""

    def __init__(self, tool_sequence: Optional[List[Dict]] = None):
        """
        Args:
            tool_sequence: Séquence d'outils à appeler
        """
        super().__init__()
        self.tool_sequence = tool_sequence or [
            {
                'name': 'python_sandbox',
                'arguments': {'code': 'print("test")'}
            }
        ]
        self.tool_index = 0

    def generate(
        self,
        prompt: str,
        config: GenerationConfig,
        system_prompt: Optional[str] = None
    ) -> GenerationResult:
        """Simule génération avec appels d'outils"""
        self.calls_history.append({
            'prompt': prompt,
            'config': config,
            'system_prompt': system_prompt
        })

        # Premier appel: retourner un tool call
        if self.tool_index < len(self.tool_sequence):
            tool_call = self.tool_sequence[self.tool_index]
            self.tool_index += 1

            response = f"I need to use the {tool_call['name']} tool."

            return GenerationResult(
                text=response,
                finish_reason="tool_calls",
                tokens_generated=50,
                prompt_tokens=100,
                total_tokens=150,
                tool_calls=[tool_call]
            )

        # Appels suivants: réponse normale
        return super().generate(prompt, config, system_prompt)


@pytest.fixture
def mock_model():
    """Fixture pour un mock model de base"""
    return MockModelInterface()


@pytest.fixture
def mock_tool_model():
    """Fixture pour un mock model avec appels d'outils"""
    return MockToolCallModel()


@pytest.fixture
def mock_model_with_responses():
    """Factory fixture pour créer des mock models avec réponses personnalisées"""
    def _create_mock(responses: List[str]):
        return MockModelInterface(responses=responses)
    return _create_mock


# ============================================================================
# FIXTURES: Temporary Databases
# ============================================================================

@pytest.fixture
def temp_db(tmp_path):
    """
    Fixture pour une base de données SQLite temporaire isolée

    Returns:
        Path: Chemin vers la base de données temporaire
    """
    db_path = tmp_path / "test_episodic.db"

    # Créer le schéma de base
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Schéma conversations
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            task_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            status TEXT DEFAULT 'active'
        )
    """)

    # Schéma messages
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            task_id TEXT,
            FOREIGN KEY (conversation_id) REFERENCES conversations (id)
        )
    """)

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup (automatique avec tmp_path)


@pytest.fixture
def temp_faiss(tmp_path):
    """
    Fixture pour un index FAISS temporaire isolé

    Returns:
        Path: Répertoire pour les index FAISS
    """
    faiss_dir = tmp_path / "semantic"
    faiss_dir.mkdir(parents=True, exist_ok=True)

    yield faiss_dir

    # Cleanup (automatique avec tmp_path)


# ============================================================================
# FIXTURES: Isolated File Systems
# ============================================================================

@pytest.fixture
def isolated_fs(tmp_path):
    """
    Fixture pour un système de fichiers complètement isolé

    Crée une structure de répertoires mimant l'environnement réel:
    - logs/events/
    - logs/decisions/
    - logs/digests/
    - memory/
    - config/

    Returns:
        Dict[str, Path]: Dictionnaire de chemins isolés
    """
    structure = {
        'root': tmp_path,
        'logs': tmp_path / "logs",
        'logs_events': tmp_path / "logs" / "events",
        'logs_decisions': tmp_path / "logs" / "decisions",
        'logs_digests': tmp_path / "logs" / "digests",
        'memory': tmp_path / "memory",
        'config': tmp_path / "config",
    }

    # Créer tous les répertoires
    for path in structure.values():
        if isinstance(path, Path):
            path.mkdir(parents=True, exist_ok=True)

    yield structure

    # Cleanup (automatique avec tmp_path)


@pytest.fixture
def isolated_logging(isolated_fs):
    """
    Fixture pour logging isolé avec structure WORM

    Returns:
        Dict: Configuration de logging isolé
    """
    from runtime.middleware.logging import EventLogger
    from runtime.middleware.worm import WormLogger

    # Créer logger isolé
    event_logger = EventLogger(
        log_dir=str(isolated_fs['logs_events'])
    )

    worm_logger = WormLogger(
        log_dir=str(isolated_fs['logs_events'])
    )

    return {
        'event_logger': event_logger,
        'worm_logger': worm_logger,
        'event_log_dir': isolated_fs['logs_events'],
        'digest_dir': isolated_fs['logs_digests']
    }


# ============================================================================
# FIXTURES: Configuration & Middleware
# ============================================================================

@pytest.fixture
def test_config(tmp_path):
    """
    Fixture pour une configuration de test isolée

    Returns:
        AgentConfig: Configuration de test
    """
    from runtime.config import AgentConfig

    # Créer une configuration mock
    config = AgentConfig()

    # Override avec des valeurs de test
    config.model.backend = "mock"
    config.model.path = str(tmp_path / "mock_model")
    config.model.context_size = 2048

    config.agent.max_iterations = 5
    config.agent.timeout = 30

    return config


@pytest.fixture
def patched_middlewares(isolated_fs, isolated_logging):
    """
    Fixture pour patcher tous les middlewares avec des versions isolées

    Utilise unittest.mock.patch pour remplacer les singletons
    """
    patches = []

    # Patcher le logger
    logger_patch = patch(
        'runtime.middleware.logging.get_logger',
        return_value=isolated_logging['event_logger']
    )
    patches.append(logger_patch)
    logger_patch.start()

    # Patcher WORM logger
    worm_patch = patch(
        'runtime.middleware.worm.get_worm_logger',
        return_value=isolated_logging['worm_logger']
    )
    patches.append(worm_patch)
    worm_patch.start()

    # Patcher DR manager
    from runtime.middleware.audittrail import DRManager
    dr_manager = DRManager(
        dr_dir=str(isolated_fs['logs_decisions'])
    )
    dr_patch = patch(
        'runtime.middleware.audittrail.get_dr_manager',
        return_value=dr_manager
    )
    patches.append(dr_patch)
    dr_patch.start()

    # Patcher Provenance tracker
    from runtime.middleware.provenance import ProvenanceTracker
    tracker = ProvenanceTracker(
        output_dir=str(isolated_fs['logs'])
    )
    tracker_patch = patch(
        'runtime.middleware.provenance.get_tracker',
        return_value=tracker
    )
    patches.append(tracker_patch)
    tracker_patch.start()

    yield {
        'event_logger': isolated_logging['event_logger'],
        'worm_logger': isolated_logging['worm_logger'],
        'dr_manager': dr_manager,
        'tracker': tracker,
        'isolated_fs': isolated_fs
    }

    # Cleanup: arrêter tous les patches
    for p in patches:
        p.stop()


# ============================================================================
# FIXTURES: FastAPI Test Client
# ============================================================================

@pytest.fixture
def api_client(mock_model, temp_db, patched_middlewares):
    """
    Fixture pour un client API FastAPI complet avec tous les mocks

    Returns:
        TestClient: Client de test FastAPI configuré
    """
    from runtime.server import app

    # Patcher le modèle
    with patch('runtime.agent.init_model', return_value=mock_model):
        # Patcher la DB
        with patch('memory.episodic.DB_PATH', str(temp_db)):
            client = TestClient(app)
            yield client


@pytest.fixture
def api_client_with_tool_model(mock_tool_model, temp_db, patched_middlewares):
    """
    Fixture pour un client API avec mock model supportant les outils
    """
    from runtime.server import app

    with patch('runtime.agent.init_model', return_value=mock_tool_model):
        with patch('memory.episodic.DB_PATH', str(temp_db)):
            client = TestClient(app)
            yield client


# ============================================================================
# FIXTURES: Tool Mocks
# ============================================================================

@pytest.fixture
def mock_tool_success():
    """Fixture pour un outil qui réussit toujours"""
    def _execute(params: Dict) -> ToolResult:
        return ToolResult(
            status=ToolStatus.SUCCESS,
            output=f"Tool executed successfully with params: {params}",
            metadata={'execution_time': 0.1}
        )

    mock = MagicMock()
    mock.execute = _execute
    mock.name = "mock_tool"
    mock.get_schema.return_value = {
        'name': 'mock_tool',
        'description': 'Mock tool for testing',
        'parameters': {'type': 'object', 'properties': {}}
    }

    return mock


@pytest.fixture
def mock_tool_failure():
    """Fixture pour un outil qui échoue toujours"""
    def _execute(params: Dict) -> ToolResult:
        return ToolResult(
            status=ToolStatus.ERROR,
            output="Tool execution failed",
            error_message="Simulated failure"
        )

    mock = MagicMock()
    mock.execute = _execute
    mock.name = "failing_tool"
    mock.get_schema.return_value = {
        'name': 'failing_tool',
        'description': 'Tool that always fails',
        'parameters': {'type': 'object', 'properties': {}}
    }

    return mock


# ============================================================================
# FIXTURES: Utility Helpers
# ============================================================================

@pytest.fixture
def conversation_factory(temp_db):
    """
    Factory fixture pour créer des conversations de test

    Returns:
        Callable: Fonction pour créer des conversations
    """
    def _create_conversation(
        conversation_id: str,
        messages: List[Dict[str, str]],
        task_id: Optional[str] = None
    ):
        """
        Créer une conversation avec des messages

        Args:
            conversation_id: ID de la conversation
            messages: Liste de messages {'role': str, 'content': str}
            task_id: ID de tâche optionnel
        """
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()

        # Créer la conversation
        cursor.execute("""
            INSERT INTO conversations (id, task_id, created_at, updated_at)
            VALUES (?, ?, ?, ?)
        """, (
            conversation_id,
            task_id,
            datetime.utcnow().isoformat(),
            datetime.utcnow().isoformat()
        ))

        # Ajouter les messages
        for msg in messages:
            cursor.execute("""
                INSERT INTO messages (conversation_id, role, content, timestamp, task_id)
                VALUES (?, ?, ?, ?, ?)
            """, (
                conversation_id,
                msg['role'],
                msg['content'],
                datetime.utcnow().isoformat(),
                task_id
            ))

        conn.commit()
        conn.close()

        return conversation_id

    return _create_conversation


@pytest.fixture
def assert_file_contains():
    """Helper fixture pour asserter le contenu de fichiers"""
    def _assert_contains(file_path: Path, expected_content: str):
        """Vérifie qu'un fichier contient le contenu attendu"""
        assert file_path.exists(), f"File {file_path} does not exist"
        content = file_path.read_text()
        assert expected_content in content, \
            f"Expected '{expected_content}' not found in {file_path}"

    return _assert_contains


@pytest.fixture
def assert_json_file_valid():
    """Helper fixture pour valider des fichiers JSON"""
    def _assert_valid(file_path: Path, schema: Optional[Dict] = None):
        """Vérifie qu'un fichier est un JSON valide"""
        assert file_path.exists(), f"File {file_path} does not exist"

        with open(file_path, 'r') as f:
            data = json.load(f)

        if schema:
            # Validation basique du schéma
            for key in schema:
                assert key in data, f"Missing key '{key}' in JSON"

        return data

    return _assert_valid


# ============================================================================
# FIXTURES: Markers & Configuration
# ============================================================================

def pytest_configure(config):
    """Configuration pytest personnalisée"""
    config.addinivalue_line(
        "markers", "e2e: Tests end-to-end complets"
    )
    config.addinivalue_line(
        "markers", "compliance: Tests de conformité et validation"
    )
    config.addinivalue_line(
        "markers", "resilience: Tests de résilience et fallbacks"
    )
    config.addinivalue_line(
        "markers", "slow: Tests lents (> 1 seconde)"
    )


# ============================================================================
# FIXTURES: Cleanup & Teardown
# ============================================================================

@pytest.fixture(autouse=True)
def reset_singletons():
    """
    Auto-fixture pour réinitialiser tous les singletons entre les tests

    Important pour éviter les effets de bord entre tests
    """
    # Avant le test: rien à faire
    yield

    # Après le test: réinitialiser les singletons
    # (Les patches sont déjà nettoyés par leurs propres fixtures)
    pass
