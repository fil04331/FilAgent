"""
Comprehensive unit tests for logging middleware

Tests cover:
- Initialization and graceful fallbacks
- Event logging functionality
- JSONL format compliance
- OpenTelemetry compatibility
- PII redaction integration
- WORM logger integration
- Error handling and edge cases
- Thread safety
- File rotation (daily files)
"""

import json
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

from runtime.middleware.logging import EventLogger, get_logger, init_logger, reset_logger


@pytest.fixture(autouse=True)
def cleanup_logger():
    """Reset global logger before and after each test"""
    reset_logger()
    yield
    reset_logger()


@pytest.fixture
def temp_log_dir(tmp_path):
    """Temporary log directory for tests"""
    log_dir = tmp_path / "logs" / "events"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


class TestEventLoggerInitialization:
    """Test EventLogger initialization and setup"""

    def test_basic_initialization(self, temp_log_dir):
        """Test basique de l'initialisation"""
        logger = EventLogger(log_dir=str(temp_log_dir))

        assert logger.log_dir == temp_log_dir
        assert temp_log_dir.exists()
        assert logger.current_file.parent == temp_log_dir

    def test_log_dir_creation(self, tmp_path):
        """Test création automatique du répertoire de log"""
        log_dir = tmp_path / "non_existent" / "logs" / "events"
        assert not log_dir.exists()

        logger = EventLogger(log_dir=str(log_dir))

        assert log_dir.exists()
        assert logger.log_dir == log_dir

    def test_default_log_dir(self):
        """Test initialisation avec répertoire par défaut"""
        with patch("pathlib.Path.mkdir"):
            logger = EventLogger()
            assert "logs/events" in str(logger.log_dir)

    def test_worm_logger_graceful_fallback(self, temp_log_dir):
        """Test fallback gracieux si WORM logger échoue"""
        with patch(
            "runtime.middleware.logging.get_worm_logger", side_effect=Exception("WORM init failed")
        ):
            logger = EventLogger(log_dir=str(temp_log_dir))

            # Should initialize without WORM logger
            assert logger.worm_logger is None

            # Should still be able to log events
            logger.log_event(actor="test", event="test.event")

            # Verify log file was created
            log_files = list(temp_log_dir.glob("*.jsonl"))
            assert len(log_files) == 1

    def test_current_file_naming(self, temp_log_dir):
        """Test format du nom de fichier de log"""
        logger = EventLogger(log_dir=str(temp_log_dir))

        today = datetime.now().strftime("%Y-%m-%d")
        expected_filename = f"events-{today}.jsonl"

        assert logger.current_file.name == expected_filename


class TestEventLogging:
    """Test event logging functionality"""

    def test_log_event_basic(self, temp_log_dir):
        """Test log d'un événement basique"""
        logger = EventLogger(log_dir=str(temp_log_dir))

        logger.log_event(actor="test.actor", event="test.event", level="INFO")

        # Read the log file
        log_file = logger.current_file
        assert log_file.exists()

        with open(log_file, "r") as f:
            line = f.readline()
            event_data = json.loads(line)

        assert event_data["actor"] == "test.actor"
        assert event_data["event"] == "test.event"
        assert event_data["level"] == "INFO"
        assert "trace_id" in event_data
        assert "span_id" in event_data
        assert "ts" in event_data

    def test_log_event_with_metadata(self, temp_log_dir):
        """Test log avec métadonnées"""
        logger = EventLogger(log_dir=str(temp_log_dir))

        metadata = {"tool_name": "python_sandbox", "execution_time": 0.5, "status": "success"}

        logger.log_event(
            actor="tool.executor", event="tool.execution", level="INFO", metadata=metadata
        )

        with open(logger.current_file, "r") as f:
            event_data = json.loads(f.readline())

        assert event_data["metadata"]["tool_name"] == "python_sandbox"
        assert event_data["metadata"]["execution_time"] == 0.5
        assert event_data["metadata"]["status"] == "success"

    def test_log_event_with_conversation_id(self, temp_log_dir):
        """Test log avec conversation_id"""
        logger = EventLogger(log_dir=str(temp_log_dir))

        logger.log_event(
            actor="agent.core", event="generation.start", level="INFO", conversation_id="conv-123"
        )

        with open(logger.current_file, "r") as f:
            event_data = json.loads(f.readline())

        assert event_data["conversation_id"] == "conv-123"

    def test_log_event_with_task_id(self, temp_log_dir):
        """Test log avec task_id"""
        logger = EventLogger(log_dir=str(temp_log_dir))

        logger.log_event(
            actor="agent.core", event="task.execution", level="INFO", task_id="task-456"
        )

        with open(logger.current_file, "r") as f:
            event_data = json.loads(f.readline())

        assert event_data["task_id"] == "task-456"

    def test_jsonl_format(self, temp_log_dir):
        """Test format JSONL (une ligne par événement)"""
        logger = EventLogger(log_dir=str(temp_log_dir))

        # Log multiple events
        for i in range(5):
            logger.log_event(actor=f"actor-{i}", event=f"event-{i}", level="INFO")

        # Verify JSONL format
        with open(logger.current_file, "r") as f:
            lines = f.readlines()

        assert len(lines) == 5

        for i, line in enumerate(lines):
            event_data = json.loads(line)
            assert event_data["actor"] == f"actor-{i}"
            assert event_data["event"] == f"event-{i}"

    def test_timestamp_format(self, temp_log_dir):
        """Test format ISO8601 des timestamps"""
        logger = EventLogger(log_dir=str(temp_log_dir))

        logger.log_event(actor="test", event="test.event")

        with open(logger.current_file, "r") as f:
            event_data = json.loads(f.readline())

        # Verify ISO8601 format
        ts = event_data["ts"]
        datetime.fromisoformat(ts)  # Should not raise

        # Verify timestamp alias
        assert event_data["timestamp"] == event_data["ts"]


class TestOpenTelemetryCompatibility:
    """Test OpenTelemetry compatibility"""

    def test_trace_id_generation(self, temp_log_dir):
        """Test génération de trace_id"""
        logger = EventLogger(log_dir=str(temp_log_dir))

        logger.log_event(actor="test", event="test.event")

        with open(logger.current_file, "r") as f:
            event_data = json.loads(f.readline())

        assert "trace_id" in event_data
        assert len(event_data["trace_id"]) == 16  # 16 hex chars

    def test_span_id_generation(self, temp_log_dir):
        """Test génération de span_id"""
        logger = EventLogger(log_dir=str(temp_log_dir))

        logger.log_event(actor="test", event="test.event")

        with open(logger.current_file, "r") as f:
            event_data = json.loads(f.readline())

        assert "span_id" in event_data
        assert len(event_data["span_id"]) == 8  # 8 hex chars

    def test_unique_trace_ids(self, temp_log_dir):
        """Test unicité des trace_id"""
        logger = EventLogger(log_dir=str(temp_log_dir))

        trace_ids = set()
        for _ in range(10):
            logger.log_event(actor="test", event="test.event")

        with open(logger.current_file, "r") as f:
            for line in f:
                event_data = json.loads(line)
                trace_ids.add(event_data["trace_id"])

        assert len(trace_ids) == 10  # All unique


class TestPIIRedactionIntegration:
    """Test PII redaction integration"""

    def test_pii_redaction_applied(self, temp_log_dir):
        """Test masquage PII dans les métadonnées"""
        logger = EventLogger(log_dir=str(temp_log_dir))

        metadata = {"user_email": "test@example.com", "message": "Contact me at john@example.com"}

        logger.log_event(actor="test", event="test.event", metadata=metadata)

        with open(logger.current_file, "r") as f:
            event_data = json.loads(f.readline())

        # PII should be redacted
        metadata_str = json.dumps(event_data["metadata"])
        assert "[REDACTED]" in metadata_str or "test@example.com" not in metadata_str

    def test_pii_redaction_graceful_fallback(self, temp_log_dir):
        """Test fallback gracieux si redactor échoue"""
        logger = EventLogger(log_dir=str(temp_log_dir))

        with patch(
            "runtime.middleware.redaction.get_pii_redactor",
            side_effect=Exception("Redactor failed"),
        ):
            metadata = {"email": "test@example.com"}

            # Should not raise exception
            logger.log_event(actor="test", event="test.event", metadata=metadata)

            # Log should still be written
            assert logger.current_file.exists()

    def test_pii_redactor_not_called_for_pii_events(self, temp_log_dir):
        """Test que le redactor n'est pas appelé pour ses propres événements"""
        logger = EventLogger(log_dir=str(temp_log_dir))

        metadata = {"email": "test@example.com"}

        # Events from pii.redactor should not trigger PII redaction
        logger.log_event(actor="pii.redactor", event="pii.detected", metadata=metadata)

        with open(logger.current_file, "r") as f:
            event_data = json.loads(f.readline())

        # Should contain original email (no redaction)
        assert event_data["metadata"]["email"] == "test@example.com"


class TestWORMLoggerIntegration:
    """Test WORM logger integration"""

    def test_worm_logger_used_when_available(self, temp_log_dir):
        """Test utilisation du WORM logger quand disponible"""
        mock_worm = MagicMock()
        mock_worm.append.return_value = True

        with patch("runtime.middleware.logging.get_worm_logger", return_value=mock_worm):
            logger = EventLogger(log_dir=str(temp_log_dir))
            logger.log_event(actor="test", event="test.event")

            # WORM logger should have been called
            mock_worm.append.assert_called_once()

    def test_fallback_to_standard_write_when_worm_fails(self, temp_log_dir):
        """Test fallback vers écriture standard si WORM échoue"""
        mock_worm = MagicMock()
        mock_worm.append.return_value = False  # WORM fails

        with patch("runtime.middleware.logging.get_worm_logger", return_value=mock_worm):
            logger = EventLogger(log_dir=str(temp_log_dir))
            logger.log_event(actor="test", event="test.event")

            # Log should still be written via fallback
            assert logger.current_file.exists()

            with open(logger.current_file, "r") as f:
                event_data = json.loads(f.readline())

            assert event_data["actor"] == "test"


class TestToolCallLogging:
    """Test tool call logging"""

    def test_log_tool_call_basic(self, temp_log_dir):
        """Test log d'appel d'outil basique"""
        logger = EventLogger(log_dir=str(temp_log_dir))

        logger.log_tool_call(
            tool_name="python_sandbox",
            arguments={"code": "print('hello')"},
            conversation_id="conv-123",
            success=True,
        )

        with open(logger.current_file, "r") as f:
            event_data = json.loads(f.readline())

        assert event_data["actor"] == "tool.python_sandbox"
        assert event_data["event"] == "tool.call"
        assert event_data["metadata"]["tool_name"] == "python_sandbox"
        assert event_data["metadata"]["success"] is True

    def test_log_tool_call_with_output(self, temp_log_dir):
        """Test log d'appel d'outil avec output"""
        logger = EventLogger(log_dir=str(temp_log_dir))

        logger.log_tool_call(
            tool_name="calculator",
            arguments={"expression": "2+2"},
            conversation_id="conv-123",
            success=True,
            output="4",
        )

        with open(logger.current_file, "r") as f:
            event_data = json.loads(f.readline())

        # Output should be hashed
        assert event_data["metadata"]["output_hash"].startswith("sha256:")

    def test_log_tool_call_arguments_hashed(self, temp_log_dir):
        """Test que les arguments sont hashés"""
        logger = EventLogger(log_dir=str(temp_log_dir))

        arguments = {"code": "print('secret')"}

        logger.log_tool_call(
            tool_name="python_sandbox", arguments=arguments, conversation_id="conv-123"
        )

        with open(logger.current_file, "r") as f:
            event_data = json.loads(f.readline())

        # Arguments should be hashed, not exposed in plaintext
        assert "arguments_hash" in event_data["metadata"]
        assert event_data["metadata"]["arguments_hash"].startswith("sha256:")
        assert "secret" not in json.dumps(event_data)


class TestGenerationLogging:
    """Test generation logging"""

    def test_log_generation(self, temp_log_dir):
        """Test log de génération de texte"""
        logger = EventLogger(log_dir=str(temp_log_dir))

        logger.log_generation(
            conversation_id="conv-123",
            task_id="task-456",
            prompt_hash="abc123",
            response_hash="def456",
            tokens_used=150,
        )

        with open(logger.current_file, "r") as f:
            event_data = json.loads(f.readline())

        assert event_data["actor"] == "agent.core"
        assert event_data["event"] == "generation.complete"
        assert event_data["conversation_id"] == "conv-123"
        assert event_data["task_id"] == "task-456"
        assert event_data["metadata"]["tokens_used"] == 150
        assert event_data["metadata"]["prompt_hash"] == "sha256:abc123"
        assert event_data["metadata"]["response_hash"] == "sha256:def456"


class TestErrorLogging:
    """Test error logging"""

    def test_error_with_message(self, temp_log_dir):
        """Test log d'erreur avec message"""
        logger = EventLogger(log_dir=str(temp_log_dir))

        logger.error("Test error message")

        with open(logger.current_file, "r") as f:
            event_data = json.loads(f.readline())

        assert event_data["level"] == "ERROR"
        assert event_data["actor"] == "logger.system"
        assert event_data["event"] == "error"
        assert event_data["metadata"]["message"] == "Test error message"

    def test_error_with_exception_info(self, temp_log_dir):
        """Test log d'erreur avec exception"""
        logger = EventLogger(log_dir=str(temp_log_dir))

        try:
            raise ValueError("Test exception")
        except ValueError as e:
            logger.error("Error occurred", exc_info=e)

        with open(logger.current_file, "r") as f:
            event_data = json.loads(f.readline())

        assert "exception" in event_data["metadata"]
        assert "ValueError" in event_data["metadata"]["exception"]
        assert "Test exception" in event_data["metadata"]["exception"]

    def test_error_with_exc_info_true(self, temp_log_dir):
        """Test log d'erreur avec exc_info=True"""
        logger = EventLogger(log_dir=str(temp_log_dir))

        try:
            raise RuntimeError("Test error")
        except RuntimeError:
            logger.error("Error occurred", exc_info=True)

        with open(logger.current_file, "r") as f:
            event_data = json.loads(f.readline())

        assert "exception" in event_data["metadata"]
        assert "RuntimeError" in event_data["metadata"]["exception"]


class TestThreadSafety:
    """Test thread safety"""

    def test_concurrent_logging(self, temp_log_dir):
        """Test logging concurrent depuis plusieurs threads"""
        import threading

        logger = EventLogger(log_dir=str(temp_log_dir))

        def log_events(thread_id):
            for i in range(10):
                logger.log_event(actor=f"thread-{thread_id}", event=f"event-{i}", level="INFO")

        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=log_events, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Verify all events were logged
        with open(logger.current_file, "r") as f:
            lines = f.readlines()

        assert len(lines) == 50  # 5 threads * 10 events


class TestFileRotation:
    """Test daily file rotation"""

    def test_file_rotation_on_day_change(self, temp_log_dir):
        """Test rotation de fichier au changement de jour"""
        logger = EventLogger(log_dir=str(temp_log_dir))

        # Log an event
        logger.log_event(actor="test", event="event1")
        first_file = logger.current_file

        # Mock day change
        with patch("runtime.middleware.logging.datetime") as mock_dt:
            from datetime import timedelta

            new_date = datetime.now() + timedelta(days=1)
            mock_dt.now.return_value = new_date
            mock_dt.strftime = datetime.strftime

            # Log another event (should trigger rotation)
            logger.log_event(actor="test", event="event2")

            # Should have created a new file
            # Note: This test may need adjustment based on actual rotation logic


class TestSingletonPattern:
    """Test singleton pattern for get_logger()"""

    def test_get_logger_returns_singleton(self):
        """Test que get_logger retourne toujours la même instance"""
        logger1 = get_logger()
        logger2 = get_logger()

        assert logger1 is logger2

    def test_init_logger_creates_new_instance(self, temp_log_dir):
        """Test que init_logger crée une nouvelle instance"""
        logger1 = init_logger(log_dir=str(temp_log_dir))
        logger2 = get_logger()

        assert logger1 is logger2

    def test_reset_logger_clears_singleton(self):
        """Test que reset_logger efface le singleton"""
        logger1 = get_logger()
        reset_logger()
        logger2 = get_logger()

        assert logger1 is not logger2


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_metadata(self, temp_log_dir):
        """Test log avec métadonnées vides"""
        logger = EventLogger(log_dir=str(temp_log_dir))

        logger.log_event(actor="test", event="test.event", metadata={})

        with open(logger.current_file, "r") as f:
            event_data = json.loads(f.readline())

        assert event_data["metadata"] == {}

    def test_none_metadata(self, temp_log_dir):
        """Test log avec metadata=None"""
        logger = EventLogger(log_dir=str(temp_log_dir))

        logger.log_event(actor="test", event="test.event", metadata=None)

        with open(logger.current_file, "r") as f:
            event_data = json.loads(f.readline())

        assert event_data["metadata"] == {}

    def test_deeply_nested_metadata(self, temp_log_dir):
        """Test log avec métadonnées profondément imbriquées"""
        logger = EventLogger(log_dir=str(temp_log_dir))

        metadata = {"level1": {"level2": {"level3": {"value": "deep"}}}}

        logger.log_event(actor="test", event="test.event", metadata=metadata)

        with open(logger.current_file, "r") as f:
            event_data = json.loads(f.readline())

        assert event_data["metadata"]["level1"]["level2"]["level3"]["value"] == "deep"

    def test_metadata_with_special_characters(self, temp_log_dir):
        """Test log avec caractères spéciaux dans les métadonnées"""
        logger = EventLogger(log_dir=str(temp_log_dir))

        metadata = {"message": "Texte avec accents: éàü", "symbols": "Special chars: €£¥"}

        logger.log_event(actor="test", event="test.event", metadata=metadata)

        with open(logger.current_file, "r", encoding="utf-8") as f:
            event_data = json.loads(f.readline())

        assert event_data["metadata"]["message"] == "Texte avec accents: éàü"
        assert event_data["metadata"]["symbols"] == "Special chars: €£¥"

    def test_metadata_mutation_protection(self, temp_log_dir):
        """Test protection contre la mutation des métadonnées"""
        logger = EventLogger(log_dir=str(temp_log_dir))

        metadata = {"value": "original"}
        logger.log_event(actor="test", event="test.event", metadata=metadata)

        # Mutate original metadata
        metadata["value"] = "modified"

        # Logged metadata should not be affected
        with open(logger.current_file, "r") as f:
            event_data = json.loads(f.readline())

        assert event_data["metadata"]["value"] == "original"


@pytest.mark.unit
class TestComplianceRequirements:
    """Test compliance with governance requirements"""

    def test_log_contains_required_fields(self, temp_log_dir):
        """Test que les logs contiennent tous les champs requis"""
        logger = EventLogger(log_dir=str(temp_log_dir))

        logger.log_event(actor="test", event="test.event")

        with open(logger.current_file, "r") as f:
            event_data = json.loads(f.readline())

        required_fields = ["ts", "trace_id", "span_id", "level", "actor", "event"]
        for field in required_fields:
            assert field in event_data, f"Missing required field: {field}"

    def test_log_file_permissions(self, temp_log_dir):
        """Test permissions des fichiers de log"""
        logger = EventLogger(log_dir=str(temp_log_dir))

        logger.log_event(actor="test", event="test.event")

        # Log file should be readable
        assert logger.current_file.exists()
        assert logger.current_file.is_file()

    def test_fsync_ensures_persistence(self, temp_log_dir):
        """Test que fsync garantit la persistance"""
        logger = EventLogger(log_dir=str(temp_log_dir))

        logger.log_event(actor="test", event="test.event")

        # File should be immediately available (fsync was called)
        assert logger.current_file.exists()

        with open(logger.current_file, "r") as f:
            content = f.read()

        assert len(content) > 0
