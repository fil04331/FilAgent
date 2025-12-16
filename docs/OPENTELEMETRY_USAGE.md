# OpenTelemetry Usage Guide

## Overview

FilAgent is instrumented with OpenTelemetry for distributed tracing, enabling you to visualize and analyze request flows across all components. This guide explains how to configure, deploy, and use the tracing infrastructure.

## Architecture

```
Request → FastAPI Server → Agent → Router → Planner/Tool Executor → Tools
   ↓           ↓              ↓       ↓           ↓                    ↓
   └─────────── OpenTelemetry Spans with Trace Context ───────────────┘
                              ↓
                         Jaeger/OTLP
                              ↓
                         Jaeger UI
```

### Components with Tracing

1. **FastAPI Server** (`runtime/server.py`)
   - Auto-instrumented with `opentelemetry-instrumentation-fastapi`
   - Traces all HTTP requests to `/chat`, `/health`, etc.
   - Adds `X-Trace-ID` header to responses

2. **Agent** (`runtime/agent.py`)
   - Manual spans for `_run_with_htn` (HTN planning execution)
   - Manual spans for `_run_simple` (simple execution mode)
   - Child spans for planning, execution, verification phases

3. **Tool Executor** (`runtime/tool_executor.py`)
   - Spans for each tool execution: `tool.execute.{tool_name}`
   - Attributes: tool name, success status, duration, errors

4. **Trace Context Propagation**
   - `trace_id` and `span_id` automatically added to structlog logs
   - Enables correlation between traces and logs

## Configuration

### Telemetry Configuration File

Located at `config/telemetry.yaml`. Key sections:

```yaml
service:
  name: "filagent"
  version: "2.0.0"
  namespace: "production"
  environment: "production"  # Override with FILAGENT_ENV

tracing:
  enabled: true
  sampler:
    type: "always_on"  # Sample all traces
    ratio: 1.0

exporter:
  type: "jaeger"  # Options: jaeger, otlp_http, otlp_grpc, console
  jaeger:
    agent_host: "localhost"
    agent_port: 6831
```

### Exporter Options

#### 1. Jaeger (Default)

```yaml
exporter:
  type: "jaeger"
  jaeger:
    agent_host: "localhost"
    agent_port: 6831
    collector_endpoint: "http://localhost:14268/api/traces"
```

#### 2. OTLP HTTP (OpenTelemetry Protocol)

```yaml
exporter:
  type: "otlp_http"
  otlp_http:
    endpoint: "http://localhost:4318/v1/traces"
    timeout: 10
    compression: "gzip"
    headers:
      authorization: "Bearer YOUR_TOKEN"
```

#### 3. OTLP gRPC

```yaml
exporter:
  type: "otlp_grpc"
  otlp_grpc:
    endpoint: "localhost:4317"
    timeout: 10
```

#### 4. Console (Debugging)

```yaml
exporter:
  type: "console"
```

### Privacy Settings

```yaml
privacy:
  mask_pii: true  # Automatically mask PII in span attributes
  hash_user_ids: true  # Hash user IDs instead of plaintext
  excluded_fields:
    - "password"
    - "token"
    - "api_key"
    - "email"
```

## Deployment

### Local Development with Docker Compose

The easiest way to get started is using Docker Compose with Jaeger:

```bash
# Start FilAgent with Jaeger
docker compose up -d

# Access services:
# - FilAgent API: http://localhost:8000
# - Gradio UI: http://localhost:7860
# - Jaeger UI: http://localhost:16686
```

The `docker-compose.override.yml` file automatically adds:
- Jaeger all-in-one container
- Network connectivity between services
- Environment variables for OpenTelemetry

### Manual Configuration

If not using Docker Compose, configure the exporter endpoint:

```bash
# For Jaeger
export OTEL_EXPORTER_JAEGER_AGENT_HOST=jaeger-host
export OTEL_EXPORTER_JAEGER_AGENT_PORT=6831

# For OTLP
export OTEL_EXPORTER_OTLP_ENDPOINT=http://otlp-collector:4318
```

## Usage

### Viewing Traces in Jaeger

1. Open Jaeger UI: http://localhost:16686
2. Select **Service**: `filagent`
3. Click **Find Traces**
4. Select a trace to view the waterfall diagram

### Understanding Trace Structure

A typical trace for `/chat` request:

```
filagent: POST /chat                               [500ms total]
├─ agent.run_simple                               [480ms]
│  ├─ tool.execute.calculator                     [50ms]
│  │  └─ attributes: tool.name=calculator, success=true
│  ├─ tool.execute.file_read                      [30ms]
│  └─ tool.execute.web_search                     [200ms]
└─ attributes: conversation_id, task_id, execution_mode=simple
```

### Trace Attributes

Each span includes structured attributes:

| Attribute | Description | Example |
|-----------|-------------|---------|
| `conversation_id` | Unique conversation identifier | `conv-abc123` |
| `task_id` | Optional task identifier | `task-xyz789` |
| `execution_mode` | Agent execution mode | `simple` or `htn` |
| `tool.name` | Name of tool being executed | `calculator` |
| `tool.execution.success` | Whether tool succeeded | `true` |
| `tool.duration_ms` | Tool execution time | `45.2` |
| `planning.strategy` | HTN planning strategy | `hybrid` |
| `planning.confidence` | Planning confidence score | `0.85` |

### Correlating Traces with Logs

Logs automatically include `trace_id` and `span_id`:

```json
{
  "timestamp": "2024-12-16T10:30:45Z",
  "level": "INFO",
  "event": "tool.execution",
  "tool_name": "calculator",
  "trace_id": "1234567890abcdef1234567890abcdef",
  "span_id": "abcdef1234567890",
  "conversation_id": "conv-abc123"
}
```

Use the `trace_id` to find the corresponding trace in Jaeger.

## Sampling Strategies

Control which requests are traced:

### Always On (Development)

```yaml
tracing:
  sampler:
    type: "always_on"
    ratio: 1.0  # 100% of requests
```

### Probabilistic (Production)

```yaml
tracing:
  sampler:
    type: "trace_id_ratio"
    ratio: 0.1  # 10% of requests
```

### Always Off (Disable Tracing)

```yaml
tracing:
  sampler:
    type: "always_off"
```

## Performance Considerations

### Overhead

OpenTelemetry adds minimal overhead:
- **CPU**: < 1% per request (with batching)
- **Memory**: ~10MB for span buffer
- **Network**: Asynchronous export every 5 seconds

### Optimization Tips

1. **Use Batch Processor** (enabled by default):
   ```yaml
   batch_processor:
     enabled: true
     schedule_delay_millis: 5000  # Export every 5s
     max_export_batch_size: 512
   ```

2. **Exclude Health Checks**:
   ```yaml
   performance:
     excluded_urls:
       - "/health"
       - "/metrics"
   ```

3. **Adjust Sampling in Production**:
   ```yaml
   tracing:
     sampler:
       type: "trace_id_ratio"
       ratio: 0.1  # Sample 10% of requests
   ```

## Troubleshooting

### Traces Not Appearing in Jaeger

**Problem**: No traces visible in Jaeger UI

**Solutions**:
1. Check Jaeger is running: `docker ps | grep jaeger`
2. Verify exporter configuration in `config/telemetry.yaml`
3. Check logs for errors: `docker logs filagent-api`
4. Test connectivity: `curl http://localhost:16686`

### OpenTelemetry Import Errors

**Problem**: `ModuleNotFoundError: No module named 'opentelemetry'`

**Solutions**:
1. Install dependencies: `pip install -r requirements.txt`
2. Regenerate requirements: `make export-requirements`
3. Check virtual environment is activated

### High Memory Usage

**Problem**: Tracing causing high memory consumption

**Solutions**:
1. Reduce batch queue size:
   ```yaml
   batch_processor:
     max_queue_size: 512  # Default: 2048
   ```

2. Reduce sampling ratio:
   ```yaml
   tracing:
     sampler:
       ratio: 0.01  # 1% of requests
   ```

3. Disable tracing temporarily:
   ```yaml
   tracing:
     enabled: false
   ```

## Integration with Other Tools

### Prometheus + Jaeger

Combine metrics and traces for full observability:

1. **Metrics** (Prometheus): System-level performance (CPU, memory, request count)
2. **Traces** (Jaeger): Request-level performance (latency, errors, spans)
3. **Logs** (structlog): Event-level details (errors, debug info)

Correlation:
- Use `trace_id` in logs to link to Jaeger traces
- Use `conversation_id` to group related metrics/traces/logs

### Grafana Integration

Add Jaeger as a data source in Grafana:

```yaml
datasources:
  - name: Jaeger
    type: jaeger
    url: http://jaeger:16686
    access: proxy
```

Then create dashboards combining:
- Prometheus metrics (gauges, histograms)
- Jaeger traces (waterfall view)
- Log panels with `trace_id` links

## Best Practices

1. **Use Descriptive Span Names**
   - ✅ Good: `tool.execute.calculator`, `agent.htn.planning`
   - ❌ Bad: `execute`, `process`

2. **Add Relevant Attributes**
   - Include: tool name, success status, IDs
   - Exclude: PII, credentials, content

3. **Keep Spans Focused**
   - One span = one logical operation
   - Avoid deeply nested spans (> 10 levels)

4. **Sample Appropriately**
   - Development: 100% sampling
   - Staging: 50% sampling
   - Production: 5-10% sampling (adjust based on traffic)

5. **Monitor Exporter Health**
   - Check batch processor metrics
   - Monitor dropped spans
   - Alert on exporter failures

## API Reference

### Python API

```python
from runtime.telemetry import get_tracer, get_trace_context

# Get a tracer instance
tracer = get_tracer("my.component")

# Create a span
with tracer.start_as_current_span("my.operation") as span:
    # Add attributes
    span.set_attribute("key", "value")
    span.set_attribute("user_id_hash", hash(user_id))
    
    # Do work
    result = do_work()
    
    # Record success
    span.set_attribute("success", True)

# Get current trace context for logging
trace_ctx = get_trace_context()
# Returns: {"trace_id": "...", "span_id": "..."}
```

### Configuration API

```python
from runtime.telemetry import initialize_telemetry, get_telemetry_manager

# Initialize with custom config
initialize_telemetry("/path/to/telemetry.yaml")

# Get manager
manager = get_telemetry_manager()

# Instrument FastAPI app
manager.instrument_fastapi(app)
```

## References

- [OpenTelemetry Python Documentation](https://opentelemetry.io/docs/languages/python/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [W3C Trace Context Specification](https://www.w3.org/TR/trace-context/)
- [FilAgent Monitoring Architecture](./MONITORING_ARCHITECTURE.md)
