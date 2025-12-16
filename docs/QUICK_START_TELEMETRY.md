# Quick Start: OpenTelemetry Tracing

## 🚀 Get Started in 5 Minutes

### Prerequisites

- Docker and Docker Compose installed
- FilAgent repository cloned

### Step 1: Start Services

```bash
# Start FilAgent with Jaeger tracing
docker compose up -d

# Verify services are running
docker ps
```

Expected output:
```
CONTAINER ID   IMAGE                          STATUS
abc123def456   filagent-gradio                Up 10 seconds
def456abc789   filagent-api                   Up 10 seconds
789abc123def   jaegertracing/all-in-one:1.52  Up 10 seconds
```

### Step 2: Send a Request

```bash
# Send a test request to the API
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Calculate 42 * 17"}
    ]
  }'
```

### Step 3: View Trace in Jaeger

1. Open Jaeger UI: http://localhost:16686
2. Select **Service**: `filagent`
3. Click **Find Traces**
4. Click on the latest trace to see the waterfall view

You should see:
```
POST /chat
└─ agent.run_simple
   └─ tool.execute.calculator
```

## 🎯 Key Features

### Automatic Instrumentation

FastAPI endpoints are automatically traced - no code changes needed:

- ✅ `/chat` - Full conversation traces
- ✅ `/health` - Health check (excluded by default)
- ✅ `/metrics` - Prometheus metrics (excluded by default)

### Manual Instrumentation

Add custom spans to your code:

```python
from runtime.telemetry import get_tracer

tracer = get_tracer("my.component")

with tracer.start_as_current_span("my_operation") as span:
    span.set_attribute("key", "value")
    # Do work here
```

### Trace-Log Correlation

Logs automatically include `trace_id`:

```python
from runtime.telemetry import get_trace_context

trace_ctx = get_trace_context()
logger.info("Processing request", **trace_ctx)
```

Output:
```json
{
  "message": "Processing request",
  "trace_id": "1234567890abcdef",
  "span_id": "abcdef1234567890"
}
```

## ⚙️ Configuration

### Change Exporter

Edit `config/telemetry.yaml`:

```yaml
exporter:
  type: "jaeger"  # Change to: otlp_http, otlp_grpc, console
```

### Adjust Sampling

```yaml
tracing:
  sampler:
    type: "trace_id_ratio"
    ratio: 0.1  # Sample 10% of requests
```

### Disable Tracing

```yaml
tracing:
  enabled: false
```

## 📊 What You Can See

### 1. Request Latency

See exactly where time is spent:
```
POST /chat: 500ms
├─ agent.run_simple: 480ms
│  ├─ tool.execute.calculator: 50ms
│  ├─ tool.execute.file_read: 30ms
│  └─ tool.execute.web_search: 400ms
```

### 2. Error Tracking

Failed spans are highlighted in red:
```
tool.execute.calculator: ERROR
└─ error: "Division by zero"
```

### 3. Tool Usage Patterns

Analyze which tools are most frequently used:
- Calculator: 45% of requests
- Web Search: 30% of requests
- File Operations: 25% of requests

## 🐛 Troubleshooting

### No traces appearing?

**Check Jaeger is accessible:**
```bash
curl http://localhost:16686
```

**Check FilAgent logs:**
```bash
docker logs filagent-api | grep -i "telemetry"
```

Expected:
```
✅ OpenTelemetry initialized with jaeger exporter
✅ FastAPI application instrumented with OpenTelemetry
```

### Import errors?

**Install dependencies:**
```bash
pip install -r requirements.txt
```

Or in Docker:
```bash
docker compose build --no-cache
docker compose up -d
```

## 📚 Next Steps

- **Full Documentation**: [docs/OPENTELEMETRY_USAGE.md](./OPENTELEMETRY_USAGE.md)
- **Monitoring Architecture**: [docs/MONITORING_ARCHITECTURE.md](./MONITORING_ARCHITECTURE.md)
- **Prometheus Metrics**: [config/prometheus.yml](../config/prometheus.yml)

## 🎓 Learning Resources

- [OpenTelemetry Concepts](https://opentelemetry.io/docs/concepts/)
- [Jaeger Getting Started](https://www.jaegertracing.io/docs/getting-started/)
- [Distributed Tracing Best Practices](https://opentelemetry.io/docs/concepts/signals/traces/)

---

**Need help?** Check [docs/OPENTELEMETRY_USAGE.md](./OPENTELEMETRY_USAGE.md) for detailed troubleshooting.
