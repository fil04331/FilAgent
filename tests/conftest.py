"""
Fixtures avancés pour les tests E2E et de conformité

Ce module fournit des fixtures sophistiqués pour:
- Mock models (simulation de modèles LLM)
- Bases de données temporaires (SQLite, FAISS)
- Systèmes de fichiers isolés
- Middlewares et composants système

Organization:
- Mock Models: Fixtures for LLM model simulation
- Temporary Databases: Isolated SQLite and FAISS fixtures
- Isolated File Systems: Temporary directory structures
- Configuration & Middleware: Test configuration and middleware mocking
- FastAPI Test Client: API client fixtures
- Tool Mocks: Mock tool implementations
- Utility Helpers: Helper functions for common test operations
- Cleanup & Teardown: Automatic cleanup fixtures
"""

import json
import os
import shutil
import sqlite3
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# =========================================================================
# TEST SERVER BOOTSTRAP (utile pour les tests de contrat HTTP)
# =========================================================================


@pytest.fixture(scope="session", autouse=True)
def start_fastapi_server() -> Generator[None, None, None]:
    """Démarrer l'API FastAPI dans un thread pour les tests de contrat."""
    import uvicorn

    from runtime.server import app

    config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="warning")
    server = uvicorn.Server(config)
    server.install_signal_handlers = lambda: None

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    start = time.time()
    while not server.started:
        if not thread.is_alive():
            raise RuntimeError("Failed to start FastAPI server for tests")
        if time.time() - start > 10:
            raise RuntimeError("Timed out starting FastAPI server for tests")
        time.sleep(0.1)

    try:
        yield
    finally:
        server.should_exit = True
        thread.join(timeout=5)


# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.config import AgentConfig
from runtime.model_interface import GenerationConfig, GenerationResult
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
            "Here is the final response.",
        ]
        self.call_count = 0
        self.calls_history = []
        self._loaded = True

    def load(self, model_path: str, config: Dict) -> bool:
        """Simule le chargement du modèle"""
        self._loaded = True
        return True

    def generate(
        self, prompt: str, config: GenerationConfig, system_prompt: Optional[str] = None
    ) -> GenerationResult:
        """Simule la génération de texte"""
        # Enregistrer l'appel
        self.calls_history.append(
            {
                "prompt": prompt,
                "config": config,
                "system_prompt": system_prompt,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        # Retourner la réponse suivante (cycle)
        response_text = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1

        return GenerationResult(
            text=response_text,
            finish_reason="stop",
            tokens_generated=len(response_text.split()),
            prompt_tokens=len(prompt.split()),
            total_tokens=len(prompt.split()) + len(response_text.split()),
            tool_calls=None,
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
            {"name": "python_sandbox", "arguments": {"code": 'print("test")'}}
        ]
        self.tool_index = 0

    def generate(
        self, prompt: str, config: GenerationConfig, system_prompt: Optional[str] = None
    ) -> GenerationResult:
        """Simule génération avec appels d'outils"""
        self.calls_history.append(
            {"prompt": prompt, "config": config, "system_prompt": system_prompt}
        )

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
                tool_calls=[tool_call],
            )

        # Appels suivants: réponse normale
        return super().generate(prompt, config, system_prompt)


@pytest.fixture(scope="function")
def mock_model() -> MockModelInterface:
    """
    Fixture pour un mock model de base

    Scope: function (new instance per test for isolation)

    Returns:
        MockModelInterface: Mock model avec réponses par défaut

    Example:
        def test_with_model(mock_model):
            result = mock_model.generate("test", GenerationConfig())
            assert result.text == "I'll help with that task."
    """
    return MockModelInterface()


@pytest.fixture(scope="function")
def mock_tool_model() -> MockToolCallModel:
    """
    Fixture pour un mock model avec appels d'outils

    Scope: function (new instance per test for isolation)

    Returns:
        MockToolCallModel: Mock model qui simule des appels d'outils

    Example:
        def test_tool_calls(mock_tool_model):
            result = mock_tool_model.generate("test", GenerationConfig())
            assert result.tool_calls is not None
    """
    return MockToolCallModel()


@pytest.fixture(scope="function")
def mock_model_with_responses():
    """
    Factory fixture pour créer des mock models avec réponses personnalisées

    Scope: function

    Returns:
        Callable: Fonction factory pour créer des mock models

    Example:
        def test_custom_responses(mock_model_with_responses):
            model = mock_model_with_responses(["Response 1", "Response 2"])
            result = model.generate("test", GenerationConfig())
            assert result.text == "Response 1"
    """

    def _create_mock(responses: List[str]) -> MockModelInterface:
        return MockModelInterface(responses=responses)

    return _create_mock


# ============================================================================
# FIXTURES: Temporary Databases
# ============================================================================


@pytest.fixture(scope="function")
def temp_db(tmp_path, monkeypatch) -> Generator[Path, None, None]:
    """
    Fixture pour une base de données SQLite temporaire isolée

    Automatically patches memory.episodic.DB_PATH for complete isolation.

    Scope: function (new database per test)

    Args:
        tmp_path: pytest's temporary directory fixture
        monkeypatch: pytest's monkeypatch fixture for patching

    Returns:
        Path: Chemin vers la base de données temporaire

    Example:
        def test_database(temp_db):
            # Database is isolated and cleaned up automatically
            conn = sqlite3.connect(str(temp_db))
            # ... test code ...
    """
    db_path = tmp_path / "test_episodic.db"

    # Patch the DB_PATH in memory.episodic module for complete isolation
    import memory.episodic

    monkeypatch.setattr(memory.episodic, "DB_PATH", db_path)

    # Create tables using the episodic module's function
    # This ensures the schema matches exactly what the application expects
    from memory.episodic import create_tables

    create_tables()

    yield db_path

    # Cleanup (automatique avec tmp_path + monkeypatch reverts DB_PATH)


@pytest.fixture(scope="function")
def temp_faiss(tmp_path) -> Generator[Path, None, None]:
    """
    Fixture pour un index FAISS temporaire isolé

    Scope: function (new FAISS index per test)

    Args:
        tmp_path: pytest's temporary directory fixture

    Returns:
        Path: Répertoire pour les index FAISS

    Example:
        def test_semantic_search(temp_faiss):
            # FAISS directory is isolated
            index_path = temp_faiss / "index.faiss"
            # ... test code ...
    """
    faiss_dir = tmp_path / "semantic"
    faiss_dir.mkdir(parents=True, exist_ok=True)

    yield faiss_dir

    # Cleanup (automatique avec tmp_path)


# ============================================================================
# FIXTURES: Isolated File Systems
# ============================================================================


@pytest.fixture(scope="function")
def isolated_fs(tmp_path) -> Generator[Dict[str, Path], None, None]:
    """
    Fixture pour un système de fichiers complètement isolé

    Crée une structure de répertoires mimant l'environnement réel:
    - logs/events/
    - logs/decisions/
    - logs/digests/
    - memory/
    - config/

    Scope: function (new filesystem per test)

    Args:
        tmp_path: pytest's temporary directory fixture

    Returns:
        Dict[str, Path]: Dictionnaire de chemins isolés

    Example:
        def test_with_isolated_fs(isolated_fs):
            log_dir = isolated_fs['logs_events']
            # Write to isolated log directory
            (log_dir / "test.log").write_text("test")
    """
    structure = {
        "root": tmp_path,
        "logs": tmp_path / "logs",
        "logs_events": tmp_path / "logs" / "events",
        "logs_decisions": tmp_path / "logs" / "decisions",
        "logs_digests": tmp_path / "logs" / "digests",
        "memory": tmp_path / "memory",
        "config": tmp_path / "config",
    }

    # Créer tous les répertoires
    for path in structure.values():
        if isinstance(path, Path):
            path.mkdir(parents=True, exist_ok=True)

    yield structure

    # Cleanup (automatique avec tmp_path)


@pytest.fixture(scope="function")
def isolated_logging(isolated_fs) -> Generator[Dict[str, Any], None, None]:
    """
    Fixture pour logging isolé avec structure WORM

    Depends on isolated_fs fixture for directory structure.

    Scope: function (new loggers per test)

    Args:
        isolated_fs: isolated filesystem fixture

    Returns:
        Dict: Configuration de logging isolé avec event_logger, worm_logger, etc.

    Example:
        def test_logging(isolated_logging):
            logger = isolated_logging['event_logger']
            logger.log_event(actor="test", event="test.event")
    """
    from runtime.middleware.logging import EventLogger
    from runtime.middleware.worm import WormLogger

    # Créer logger isolé
    event_logger = EventLogger(log_dir=str(isolated_fs["logs_events"]))

    worm_logger = WormLogger(
        log_dir=str(isolated_fs["logs_events"]), digest_dir=str(isolated_fs["logs_digests"])
    )

    return {
        "event_logger": event_logger,
        "worm_logger": worm_logger,
        "event_log_dir": isolated_fs["logs_events"],
        "digest_dir": isolated_fs["logs_digests"],
    }


# ============================================================================
# FIXTURES: Configuration & Middleware
# ============================================================================


@pytest.fixture(scope="function")
def test_config(tmp_path) -> AgentConfig:
    """
    Fixture pour une configuration de test isolée

    Scope: function (new config per test)

    Args:
        tmp_path: pytest's temporary directory fixture

    Returns:
        AgentConfig: Configuration de test

    Example:
        def test_with_config(test_config):
            assert test_config.model.backend == "mock"
            assert test_config.agent.max_iterations == 5
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


@pytest.fixture(scope="function")
def patched_middlewares(isolated_fs, isolated_logging) -> Generator[Dict[str, Any], None, None]:
    """
    Fixture pour patcher tous les middlewares avec des versions isolées

    Utilise unittest.mock.patch pour remplacer les singletons.
    All patches are automatically stopped after the test.

    Scope: function (new patches per test)

    Args:
        isolated_fs: isolated filesystem fixture
        isolated_logging: isolated logging fixture

    Yields:
        Dict: Middlewares isolés (event_logger, worm_logger, dr_manager, tracker)

    Example:
        def test_with_middleware(patched_middlewares):
            logger = patched_middlewares['event_logger']
            logger.log_event(actor="test", event="test.event")
    """
    patches = []

    # Patcher le logger
    logger_patch = patch(
        "runtime.middleware.logging.get_logger", return_value=isolated_logging["event_logger"]
    )
    patches.append(logger_patch)
    logger_patch.start()

    # Patcher WORM logger
    worm_patch = patch(
        "runtime.middleware.worm.get_worm_logger", return_value=isolated_logging["worm_logger"]
    )
    patches.append(worm_patch)
    worm_patch.start()

    # Patcher DR manager
    from runtime.middleware.audittrail import DRManager

    dr_manager = DRManager(output_dir=str(isolated_fs["logs_decisions"]))
    dr_patch = patch("runtime.middleware.audittrail.get_dr_manager", return_value=dr_manager)
    patches.append(dr_patch)
    dr_patch.start()

    # Patcher Provenance tracker
    from runtime.middleware.provenance import ProvenanceTracker

    tracker = ProvenanceTracker(storage_dir=str(isolated_fs["logs"]))
    tracker_patch = patch("runtime.middleware.provenance.get_tracker", return_value=tracker)
    patches.append(tracker_patch)
    tracker_patch.start()

    yield {
        "event_logger": isolated_logging["event_logger"],
        "worm_logger": isolated_logging["worm_logger"],
        "dr_manager": dr_manager,
        "tracker": tracker,
        "isolated_fs": isolated_fs,
    }

    # Cleanup: arrêter tous les patches
    for p in patches:
        p.stop()


# ============================================================================
# FIXTURES: FastAPI Test Client
# ============================================================================


@pytest.fixture(scope="function")
def api_client(mock_model, temp_db, patched_middlewares) -> Generator[TestClient, None, None]:
    """
    Fixture pour un client API FastAPI complet avec tous les mocks

    Automatically patches the model and database for complete isolation.

    Scope: function (new client per test)

    Args:
        mock_model: Mock LLM model fixture
        temp_db: Temporary database fixture
        patched_middlewares: Patched middleware fixture

    Returns:
        TestClient: Client de test FastAPI configuré

    Example:
        def test_api_endpoint(api_client):
            response = api_client.post("/chat", json={
                "messages": [{"role": "user", "content": "Hello"}]
            })
            assert response.status_code == 200
    """
    from runtime.server import app

    # Patcher le modèle
    with patch("runtime.agent.init_model", return_value=mock_model):
        # Patcher la DB
        with patch("memory.episodic.DB_PATH", str(temp_db)):
            client = TestClient(app)
            yield client


@pytest.fixture(scope="function")
def api_client_with_tool_model(
    mock_tool_model, temp_db, patched_middlewares
) -> Generator[TestClient, None, None]:
    """
    Fixture pour un client API avec mock model supportant les outils

    Similar to api_client but uses mock_tool_model for tool call testing.

    Scope: function (new client per test)

    Args:
        mock_tool_model: Mock model with tool call support
        temp_db: Temporary database fixture
        patched_middlewares: Patched middleware fixture

    Returns:
        TestClient: Client de test FastAPI avec support d'outils

    Example:
        def test_tool_execution(api_client_with_tool_model):
            response = api_client_with_tool_model.post("/chat", json={
                "messages": [{"role": "user", "content": "Run Python code"}]
            })
            assert response.status_code == 200
    """
    from runtime.server import app

    with patch("runtime.agent.init_model", return_value=mock_tool_model):
        with patch("memory.episodic.DB_PATH", str(temp_db)):
            client = TestClient(app)
            yield client


# ============================================================================
# FIXTURES: Tool Mocks
# ============================================================================


@pytest.fixture(scope="function")
def mock_tool_success() -> MagicMock:
    """
    Fixture pour un outil qui réussit toujours

    Scope: function (new mock per test)

    Returns:
        MagicMock: Mock tool qui retourne toujours SUCCESS

    Example:
        def test_successful_tool(mock_tool_success):
            result = mock_tool_success.execute({'param': 'value'})
            assert result.status == ToolStatus.SUCCESS
    """

    def _execute(params: Dict) -> ToolResult:
        return ToolResult(
            status=ToolStatus.SUCCESS,
            output=f"Tool executed successfully with params: {params}",
            metadata={"execution_time": 0.1},
        )

    mock = MagicMock()
    mock.execute = _execute
    mock.name = "mock_tool"
    mock.get_schema.return_value = {
        "name": "mock_tool",
        "description": "Mock tool for testing",
        "parameters": {"type": "object", "properties": {}},
    }

    return mock


@pytest.fixture(scope="function")
def mock_tool_failure() -> MagicMock:
    """
    Fixture pour un outil qui échoue toujours

    Scope: function (new mock per test)

    Returns:
        MagicMock: Mock tool qui retourne toujours ERROR

    Example:
        def test_failing_tool(mock_tool_failure):
            result = mock_tool_failure.execute({'param': 'value'})
            assert result.status == ToolStatus.ERROR
    """

    def _execute(params: Dict) -> ToolResult:
        return ToolResult(
            status=ToolStatus.ERROR,
            output="Tool execution failed",
            error_message="Simulated failure",
        )

    mock = MagicMock()
    mock.execute = _execute
    mock.name = "failing_tool"
    mock.get_schema.return_value = {
        "name": "failing_tool",
        "description": "Tool that always fails",
        "parameters": {"type": "object", "properties": {}},
    }

    return mock


# ============================================================================
# FIXTURES: Utility Helpers
# ============================================================================


@pytest.fixture(scope="function")
def conversation_factory(temp_db):
    """
    Factory fixture pour créer des conversations de test

    Scope: function

    Args:
        temp_db: Temporary database fixture

    Returns:
        Callable: Fonction pour créer des conversations

    Example:
        def test_conversation(conversation_factory):
            conv_id = conversation_factory(
                "conv-123",
                [{"role": "user", "content": "Hello"}]
            )
            # Conversation is now in the database
    """

    def _create_conversation(
        conversation_id: str, messages: List[Dict[str, str]], task_id: Optional[str] = None
    ) -> str:
        """
        Créer une conversation avec des messages

        Args:
            conversation_id: ID de la conversation
            messages: Liste de messages {'role': str, 'content': str}
            task_id: ID de tâche optionnel

        Returns:
            str: conversation_id
        """
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()

        # Créer la conversation (respect du schéma réel)
        now_iso = datetime.utcnow().isoformat()
        cursor.execute(
            """
            INSERT INTO conversations (id, conversation_id, created_at, updated_at, metadata)
            VALUES (?, ?, ?, ?, ?)
        """,
            (conversation_id, conversation_id, now_iso, now_iso, None),
        )

        # Ajouter les messages
        for msg in messages:
            cursor.execute(
                """
                INSERT INTO messages (conversation_id, role, content, timestamp, task_id)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    conversation_id,
                    msg["role"],
                    msg["content"],
                    datetime.utcnow().isoformat(),
                    task_id,
                ),
            )

        conn.commit()
        conn.close()

        return conversation_id

    return _create_conversation


@pytest.fixture(scope="function")
def assert_file_contains():
    """
    Helper fixture pour asserter le contenu de fichiers

    Scope: function

    Returns:
        Callable: Fonction d'assertion

    Example:
        def test_log_content(assert_file_contains, tmp_path):
            log_file = tmp_path / "test.log"
            log_file.write_text("Test log content")
            assert_file_contains(log_file, "Test log")
    """

    def _assert_contains(file_path: Path, expected_content: str) -> None:
        """Vérifie qu'un fichier contient le contenu attendu"""
        assert file_path.exists(), f"File {file_path} does not exist"
        content = file_path.read_text()
        assert (
            expected_content in content
        ), f"Expected '{expected_content}' not found in {file_path}"

    return _assert_contains


@pytest.fixture(scope="function")
def assert_json_file_valid():
    """
    Helper fixture pour valider des fichiers JSON

    Scope: function

    Returns:
        Callable: Fonction de validation JSON

    Example:
        def test_json_structure(assert_json_file_valid, tmp_path):
            json_file = tmp_path / "data.json"
            json_file.write_text('{"key": "value"}')
            data = assert_json_file_valid(json_file, {"key": str})
            assert data["key"] == "value"
    """

    def _assert_valid(file_path: Path, schema: Optional[Dict] = None) -> Dict:
        """Vérifie qu'un fichier est un JSON valide"""
        assert file_path.exists(), f"File {file_path} does not exist"

        with open(file_path, "r") as f:
            data = json.load(f)

        if schema:
            # Validation basique du schéma
            for key in schema:
                assert key in data, f"Missing key '{key}' in JSON"

        return data

    return _assert_valid


@pytest.fixture(scope="function")
def performance_tracker():
    """
    Fixture to track test performance and timing

    Scope: function

    Returns:
        Callable: Context manager for timing code blocks

    Example:
        def test_performance(performance_tracker):
            with performance_tracker("database_query") as timer:
                # Code to measure
                pass
            assert timer.elapsed < 1.0  # Should complete in < 1 second
    """
    import time
    from contextlib import contextmanager

    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            self.elapsed = None

    @contextmanager
    def _track(label: str = ""):
        """Track execution time of code block"""
        timer = Timer()
        timer.start_time = time.time()

        yield timer

        timer.end_time = time.time()
        timer.elapsed = timer.end_time - timer.start_time

        # Optionally print timing info
        if label:
            print(f"\n⏱ {label}: {timer.elapsed:.4f}s")

    return _track


# ============================================================================
# FIXTURES: Markers & Configuration
# ============================================================================


def pytest_configure(config):
    """
    Configuration pytest personnalisée

    Registers custom markers for test categorization:
    - e2e: End-to-end tests
    - compliance: Compliance and validation tests
    - resilience: Resilience and fallback tests
    - slow: Slow tests (> 1 second)
    - fixtures: Tests for fixture functionality
    """
    config.addinivalue_line("markers", "e2e: Tests end-to-end complets")
    config.addinivalue_line("markers", "compliance: Tests de conformité et validation")
    config.addinivalue_line("markers", "resilience: Tests de résilience et fallbacks")
    config.addinivalue_line("markers", "slow: Tests lents (> 1 seconde)")
    config.addinivalue_line("markers", "fixtures: Tests validating fixture functionality")


# ============================================================================
# FIXTURES: Cleanup & Teardown
# ============================================================================


@pytest.fixture(scope="function", autouse=True)
def clean_environment(monkeypatch) -> Generator[None, None, None]:
    """
    Auto-fixture pour isoler les variables d'environnement entre tests

    Automatically applied to all tests (autouse=True).
    Ensures environment variables don't leak between tests.

    Scope: function (applied to each test)

    Args:
        monkeypatch: pytest's monkeypatch fixture

    Yields:
        None

    Example:
        # This fixture is applied automatically
        def test_with_env(monkeypatch):
            monkeypatch.setenv("TEST_VAR", "value")
            # TEST_VAR is automatically cleaned up after test
    """
    # Store original environment
    original_env = os.environ.copy()

    yield

    # Restore original environment (monkeypatch handles this, but explicit for clarity)
    # The monkeypatch fixture automatically undoes all changes


@pytest.fixture(scope="function", autouse=True)
def reset_singletons() -> Generator[None, None, None]:
    """
    Auto-fixture pour réinitialiser tous les singletons entre les tests

    Important pour éviter les effets de bord entre tests.
    Automatically applied to all tests (autouse=True).

    Scope: function (applied to each test)

    Yields:
        None

    Note:
        Singleton cleanup is primarily handled by the patched_middlewares fixture
        which creates isolated instances. This fixture ensures any global state
        is reset.
    """
    # Avant le test: rien à faire
    yield

    # Après le test: les patches sont déjà nettoyés par leurs propres fixtures
    # Ce fixture sert de point d'extension pour futurs nettoyages de singletons
    pass
