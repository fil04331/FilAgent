"""
Tests for OpenTelemetry telemetry integration.

This module tests:
1. Telemetry configuration loading
2. TracerProvider initialization
3. Tracer instance retrieval
4. Trace context extraction
5. No-op behavior when OpenTelemetry is not available
"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


def test_telemetry_config_loading():
    """Test that telemetry configuration loads correctly."""
    from runtime.telemetry import TelemetryManager

    manager = TelemetryManager()
    config = manager.load_config()

    # Verify default configuration structure
    assert config is not None
    assert config.service is not None
    assert config.service["name"] == "filagent"
    assert config.tracing is not None
    assert config.tracing.get("enabled", True) is True
    assert config.exporter is not None


def test_telemetry_config_from_file():
    """Test that telemetry configuration loads from file."""
    from runtime.telemetry import TelemetryManager

    manager = TelemetryManager()

    # Load from the actual config file
    project_root = Path(__file__).parent.parent
    config_path = project_root / "config" / "telemetry.yaml"

    if config_path.exists():
        config = manager.load_config(str(config_path))

        # Verify key fields from config/telemetry.yaml
        assert config.service["name"] == "filagent"
        assert config.service["version"] == "2.0.0"
        assert config.exporter.get("type") in ["jaeger", "otlp_http", "otlp_grpc", "console"]
        assert config.tracing.get("enabled", True) is True


def test_telemetry_initialization():
    """Test that telemetry manager initializes correctly."""
    from runtime.telemetry import TelemetryManager, OTEL_AVAILABLE

    if not OTEL_AVAILABLE:
        pytest.skip("OpenTelemetry not available, skipping initialization test")

    manager = TelemetryManager()

    # Initialize should succeed
    result = manager.initialize()

    # Should return True if OpenTelemetry is available
    assert isinstance(result, bool)


def test_get_tracer():
    """Test that tracer instances can be retrieved."""
    from runtime.telemetry import get_tracer, OTEL_AVAILABLE

    tracer = get_tracer("test.component")

    # Tracer should always be returned (no-op if OpenTelemetry unavailable)
    assert tracer is not None

    # Tracer should have start_as_current_span method
    assert hasattr(tracer, "start_as_current_span")


def test_get_trace_context():
    """Test that trace context can be extracted."""
    from runtime.telemetry import get_trace_context

    trace_ctx = get_trace_context()

    # Should return a dictionary (may be empty if no active span)
    assert isinstance(trace_ctx, dict)

    # If there's trace context, it should have trace_id and span_id
    if trace_ctx:
        assert "trace_id" in trace_ctx or "span_id" in trace_ctx


def test_tracer_span_context_manager():
    """Test that tracer spans work as context managers."""
    from runtime.telemetry import get_tracer

    tracer = get_tracer("test.component")

    # Should work as a context manager
    try:
        with tracer.start_as_current_span("test.operation") as span:
            # Span may be None for no-op tracer, which is fine
            pass
    except Exception as e:
        pytest.fail(f"Span context manager failed: {e}")


def test_telemetry_manager_singleton():
    """Test that TelemetryManager is a singleton."""
    from runtime.telemetry import TelemetryManager, get_telemetry_manager

    manager1 = TelemetryManager()
    manager2 = TelemetryManager()
    manager3 = get_telemetry_manager()

    # All instances should be the same object
    assert manager1 is manager2
    assert manager1 is manager3


def test_noop_tracer_when_otel_unavailable():
    """Test that no-op tracer works when OpenTelemetry is unavailable."""
    from runtime.telemetry import NoOpTracer

    tracer = NoOpTracer()

    # Should work as a context manager without errors
    with tracer.start_as_current_span("test.operation") as span:
        # Span should be None
        assert span is None


def test_telemetry_privacy_config():
    """Test that privacy settings are configured."""
    from runtime.telemetry import TelemetryManager

    manager = TelemetryManager()
    config = manager.load_config()

    # Verify privacy settings exist
    assert "privacy" in config.__dict__
    privacy = config.privacy
    assert privacy.get("mask_pii") is True
    assert privacy.get("hash_user_ids") is True


def test_telemetry_exporter_configuration():
    """Test that exporter configuration is valid."""
    from runtime.telemetry import TelemetryManager

    manager = TelemetryManager()
    config = manager.load_config()

    # Verify exporter configuration
    exporter = config.exporter
    assert exporter.get("type") in ["jaeger", "otlp_http", "otlp_grpc", "console"]

    # Check that appropriate config exists for the exporter type
    exporter_type = exporter.get("type")
    if exporter_type == "jaeger":
        assert "jaeger" in exporter
        jaeger_config = exporter["jaeger"]
        assert "agent_host" in jaeger_config
        assert "agent_port" in jaeger_config
    elif exporter_type == "otlp_http":
        assert "otlp_http" in exporter
        otlp_config = exporter["otlp_http"]
        assert "endpoint" in otlp_config


def test_telemetry_propagation_config():
    """Test that trace propagation is configured."""
    from runtime.telemetry import TelemetryManager

    manager = TelemetryManager()
    config = manager.load_config()

    # Verify propagation settings
    assert "propagation" in config.__dict__
    propagation = config.propagation
    assert propagation.get("format") in ["w3c", "b3", "jaeger", "xray"]

    # Verify structlog integration is configured
    structlog_integration = propagation.get("structlog_integration", {})
    assert structlog_integration.get("enabled") is True
    assert "trace_id_field" in structlog_integration
    assert "span_id_field" in structlog_integration


def test_fastapi_instrumentation():
    """Test that FastAPI instrumentation can be called."""
    from runtime.telemetry import TelemetryManager
    from fastapi import FastAPI

    manager = TelemetryManager()
    app = FastAPI()

    # Should not raise an error
    try:
        manager.instrument_fastapi(app)
    except Exception as e:
        # If OpenTelemetry is not available, it should log a warning but not crash
        assert "not available" in str(e).lower() or "cannot instrument" in str(e).lower()


@pytest.mark.integration
def test_trace_context_in_span():
    """Integration test: Verify trace context is available within a span."""
    from runtime.telemetry import get_tracer, get_trace_context, OTEL_AVAILABLE

    if not OTEL_AVAILABLE:
        pytest.skip("OpenTelemetry not available, skipping integration test")

    tracer = get_tracer("test.integration")

    with tracer.start_as_current_span("test.operation") as span:
        # Try to get trace context within the span
        trace_ctx = get_trace_context()

        # Context should be available (unless using no-op tracer)
        # For no-op tracer, this will be empty, which is acceptable
        assert isinstance(trace_ctx, dict)


@pytest.mark.integration
def test_agent_has_tracer():
    """Integration test: Verify Agent has tracer attribute."""
    try:
        from runtime.agent import Agent, TELEMETRY_AVAILABLE

        # Create agent instance
        agent = Agent()

        # Agent should have tracer attribute
        assert hasattr(agent, "tracer")
        assert agent.tracer is not None

        # Tracer should have start_as_current_span method
        assert hasattr(agent.tracer, "start_as_current_span")

    except Exception as e:
        # If agent initialization fails due to missing dependencies, that's ok
        if "model" in str(e).lower():
            pytest.skip("Model not available for agent initialization")
        else:
            raise


@pytest.mark.integration
def test_tool_executor_has_tracer():
    """Integration test: Verify ToolExecutor has tracer attribute."""
    from runtime.tool_executor import ToolExecutor
    from tools.registry import get_registry

    # Create tool executor
    registry = get_registry()
    executor = ToolExecutor(tool_registry=registry)

    # Executor should have tracer attribute
    assert hasattr(executor, "tracer")
    assert executor.tracer is not None

    # Tracer should have start_as_current_span method
    assert hasattr(executor.tracer, "start_as_current_span")
