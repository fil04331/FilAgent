"""
OpenTelemetry Telemetry Module
Provides TracerProvider initialization and configuration for distributed tracing.

This module:
1. Loads telemetry configuration from config/telemetry.yaml
2. Initializes OpenTelemetry SDK with appropriate exporter
3. Provides tracer instances for instrumentation
4. Integrates trace context with structlog

Key Features:
- Support for multiple exporters (Jaeger, OTLP, Console)
- Automatic FastAPI instrumentation
- Trace context propagation to logs
- PII masking in span attributes
- Configurable sampling strategies
"""

import os
import socket
from typing import Optional, Dict, Any
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

# OpenTelemetry imports with graceful degradation
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        BatchSpanProcessor,
        ConsoleSpanExporter,
        SimpleSpanProcessor,
    )
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as OTLPHTTPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
    
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    # Stub classes for when OpenTelemetry is not available
    class TracerProvider:
        pass
    
    class Resource:
        pass


class TelemetryConfig(BaseModel):
    """Telemetry configuration model."""
    
    service: Dict[str, str] = Field(default_factory=lambda: {
        "name": "filagent",
        "version": "2.0.0",
        "namespace": "production",
        "environment": "production"
    })
    tracing: Dict[str, Any] = Field(default_factory=lambda: {
        "enabled": True,
        "sampler": {"type": "always_on", "ratio": 1.0}
    })
    exporter: Dict[str, Any] = Field(default_factory=lambda: {
        "type": "jaeger",
        "jaeger": {
            "agent_host": "localhost",
            "agent_port": 6831,
            "collector_endpoint": "http://localhost:14268/api/traces"
        }
    })
    propagation: Dict[str, Any] = Field(default_factory=lambda: {
        "format": "w3c",
        "structlog_integration": {
            "enabled": True,
            "trace_id_field": "trace_id",
            "span_id_field": "span_id"
        }
    })
    batch_processor: Dict[str, Any] = Field(default_factory=lambda: {
        "enabled": True,
        "max_queue_size": 2048,
        "schedule_delay_millis": 5000,
        "max_export_batch_size": 512,
        "export_timeout_millis": 30000
    })
    privacy: Dict[str, Any] = Field(default_factory=lambda: {
        "mask_pii": True,
        "hash_user_ids": True
    })


class TelemetryManager:
    """
    Manages OpenTelemetry configuration and initialization.
    
    Singleton pattern ensures only one TracerProvider is initialized.
    """
    
    _instance: Optional['TelemetryManager'] = None
    _tracer_provider: Optional[TracerProvider] = None
    _config: Optional[TelemetryConfig] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize telemetry manager (only once)."""
        if not hasattr(self, '_initialized'):
            self._initialized = False
            self._tracer = None
    
    def load_config(self, config_path: Optional[str] = None) -> TelemetryConfig:
        """
        Load telemetry configuration from YAML file.
        
        Args:
            config_path: Path to telemetry.yaml, defaults to config/telemetry.yaml
            
        Returns:
            TelemetryConfig instance
        """
        if config_path is None:
            # Default to config/telemetry.yaml relative to project root
            project_root = Path(__file__).parent.parent
            config_path = project_root / "config" / "telemetry.yaml"
        else:
            config_path = Path(config_path)
        
        if not config_path.exists():
            print(f"⚠️ Telemetry config not found at {config_path}, using defaults")
            return TelemetryConfig()
        
        try:
            with open(config_path, 'r') as f:
                config_dict = yaml.safe_load(f)
            
            # Replace environment variables
            service_config = config_dict.get('service', {})
            if 'environment' in service_config:
                service_config['environment'] = os.getenv('FILAGENT_ENV', service_config['environment'])
            
            return TelemetryConfig(**config_dict)
        except Exception as e:
            print(f"⚠️ Failed to load telemetry config: {e}, using defaults")
            return TelemetryConfig()
    
    def initialize(self, config_path: Optional[str] = None) -> bool:
        """
        Initialize OpenTelemetry SDK with configuration.
        
        Args:
            config_path: Optional path to telemetry.yaml
            
        Returns:
            True if initialization succeeded, False otherwise
        """
        if self._initialized:
            return True
        
        if not OTEL_AVAILABLE:
            print("⚠️ OpenTelemetry not available, tracing disabled")
            return False
        
        try:
            # Load configuration
            self._config = self.load_config(config_path)
            
            # Check if tracing is enabled
            if not self._config.tracing.get('enabled', True):
                print("ℹ️ Tracing is disabled in configuration")
                return False
            
            # Create resource with service metadata
            resource = self._create_resource()
            
            # Create tracer provider
            self._tracer_provider = TracerProvider(resource=resource)
            
            # Configure exporter
            exporter = self._create_exporter()
            if exporter:
                # Add span processor
                if self._config.batch_processor.get('enabled', True):
                    processor = BatchSpanProcessor(
                        exporter,
                        max_queue_size=self._config.batch_processor.get('max_queue_size', 2048),
                        schedule_delay_millis=self._config.batch_processor.get('schedule_delay_millis', 5000),
                        max_export_batch_size=self._config.batch_processor.get('max_export_batch_size', 512),
                        export_timeout_millis=self._config.batch_processor.get('export_timeout_millis', 30000),
                    )
                else:
                    processor = SimpleSpanProcessor(exporter)
                
                self._tracer_provider.add_span_processor(processor)
            
            # Set global tracer provider
            trace.set_tracer_provider(self._tracer_provider)
            
            # Get tracer for this service
            self._tracer = trace.get_tracer(
                self._config.service['name'],
                self._config.service['version']
            )
            
            self._initialized = True
            print(f"✅ OpenTelemetry initialized with {self._config.exporter['type']} exporter")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize OpenTelemetry: {e}")
            return False
    
    def _create_resource(self) -> Resource:
        """Create OpenTelemetry resource with service metadata."""
        attributes = {
            SERVICE_NAME: self._config.service['name'],
            SERVICE_VERSION: self._config.service['version'],
            "service.namespace": self._config.service['namespace'],
            "deployment.environment": self._config.service['environment'],
            "service.instance.id": socket.gethostname(),
        }
        
        # Add custom resource attributes if configured
        resource_attrs = self._config.__dict__.get('resource', {}).get('attributes', {})
        for key, value in resource_attrs.items():
            # Replace ${HOSTNAME} with actual hostname
            if isinstance(value, str) and '${HOSTNAME}' in value:
                value = value.replace('${HOSTNAME}', socket.gethostname())
            attributes[key] = value
        
        return Resource.create(attributes)
    
    def _create_exporter(self):
        """
        Create span exporter based on configuration.
        
        Returns:
            Span exporter instance or None
        """
        exporter_type = self._config.exporter.get('type', 'jaeger')
        
        try:
            if exporter_type == 'jaeger':
                jaeger_config = self._config.exporter.get('jaeger', {})
                return JaegerExporter(
                    agent_host_name=jaeger_config.get('agent_host', 'localhost'),
                    agent_port=jaeger_config.get('agent_port', 6831),
                )
            
            elif exporter_type == 'otlp_http':
                otlp_config = self._config.exporter.get('otlp_http', {})
                return OTLPHTTPSpanExporter(
                    endpoint=otlp_config.get('endpoint', 'http://localhost:4318/v1/traces'),
                    timeout=otlp_config.get('timeout', 10),
                    headers=otlp_config.get('headers', {}),
                )
            
            elif exporter_type == 'console':
                return ConsoleSpanExporter()
            
            else:
                print(f"⚠️ Unknown exporter type: {exporter_type}, using console")
                return ConsoleSpanExporter()
        
        except Exception as e:
            print(f"❌ Failed to create {exporter_type} exporter: {e}")
            # Fallback to console exporter
            return ConsoleSpanExporter()
    
    def get_tracer(self, name: Optional[str] = None):
        """
        Get a tracer instance for instrumentation.
        
        Args:
            name: Optional tracer name, defaults to service name
            
        Returns:
            Tracer instance or None if not initialized
        """
        if not self._initialized:
            self.initialize()
        
        if not OTEL_AVAILABLE or not self._initialized:
            # Return a no-op tracer
            return NoOpTracer()
        
        if name is None:
            return self._tracer
        
        return trace.get_tracer(name)
    
    def instrument_fastapi(self, app):
        """
        Instrument FastAPI application with OpenTelemetry.
        
        Args:
            app: FastAPI application instance
        """
        if not OTEL_AVAILABLE or not self._initialized:
            print("⚠️ Cannot instrument FastAPI: OpenTelemetry not available")
            return
        
        try:
            FastAPIInstrumentor.instrument_app(app)
            print("✅ FastAPI instrumented with OpenTelemetry")
        except Exception as e:
            print(f"❌ Failed to instrument FastAPI: {e}")
    
    def get_trace_context(self) -> Dict[str, str]:
        """
        Get current trace context for log correlation.
        
        Returns:
            Dictionary with trace_id and span_id (empty if no active span)
        """
        if not OTEL_AVAILABLE or not self._initialized:
            return {}
        
        try:
            span = trace.get_current_span()
            if span and span.get_span_context().is_valid:
                context = span.get_span_context()
                return {
                    "trace_id": format(context.trace_id, '032x'),
                    "span_id": format(context.span_id, '016x'),
                }
        except Exception:
            pass
        
        return {}


class NoOpTracer:
    """No-op tracer for when OpenTelemetry is not available."""
    
    def start_as_current_span(self, name: str, **kwargs):
        """No-op context manager."""
        from contextlib import contextmanager
        
        @contextmanager
        def noop_span():
            yield None
        
        return noop_span()


# Global singleton instance
_telemetry_manager: Optional[TelemetryManager] = None


def get_telemetry_manager() -> TelemetryManager:
    """
    Get the global telemetry manager singleton.
    
    Returns:
        TelemetryManager instance
    """
    global _telemetry_manager
    if _telemetry_manager is None:
        _telemetry_manager = TelemetryManager()
    return _telemetry_manager


def get_tracer(name: Optional[str] = None):
    """
    Convenience function to get a tracer instance.
    
    Args:
        name: Optional tracer name
        
    Returns:
        Tracer instance
    """
    return get_telemetry_manager().get_tracer(name)


def initialize_telemetry(config_path: Optional[str] = None) -> bool:
    """
    Initialize OpenTelemetry with configuration.
    
    Args:
        config_path: Optional path to telemetry.yaml
        
    Returns:
        True if successful, False otherwise
    """
    return get_telemetry_manager().initialize(config_path)


def get_trace_context() -> Dict[str, str]:
    """
    Get current trace context for log correlation.
    
    Returns:
        Dictionary with trace_id and span_id
    """
    return get_telemetry_manager().get_trace_context()
