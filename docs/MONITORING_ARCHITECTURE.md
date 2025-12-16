# FilAgent Monitoring Architecture

## Overview

FilAgent implements comprehensive observability with Prometheus metrics, focusing on security, compliance, and operational visibility. The monitoring architecture is designed to be **PII-safe**, **dynamically configurable**, and **production-ready** for containerized environments (Docker/Kubernetes).

## Architecture Components

### 1. Metrics Collection (`runtime/metrics.py`)

The `AgentMetrics` class provides centralized metrics collection with **OpenMetrics standard** compliance.

#### Key Metrics

**Compliance Metrics:**
- `filagent_compliance_rejection_total`: Counter of compliance rejections by reason and risk level
- `filagent_compliance_validation_total`: Counter of validation events (passed/rejected/warning)
- `filagent_compliance_validation_seconds`: Histogram of validation duration

**Tool Execution Metrics:**
- `filagent_tool_execution_seconds`: Histogram of tool execution duration by tool name and status
- `filagent_tool_execution_total`: Counter of tool executions
- `filagent_tool_validation_failure_total`: Counter of validation failures

**Security Metrics:**
- `filagent_security_suspicious_pattern_total`: Counter of suspicious patterns (injection attempts)
- `filagent_security_pii_detected_total`: Counter of PII detection events

**Agent Operation Metrics:**
- `filagent_conversations_total`: Counter of conversations by status
- `filagent_conversation_duration_seconds`: Histogram of conversation duration
- `filagent_active_conversations`: Gauge of active conversations
- `filagent_reasoning_iterations_total`: Counter of reasoning loop iterations
- `filagent_tokens_total`: Counter of token usage (prompt/completion)
- `filagent_generation_duration_seconds`: Histogram of LLM generation duration

### 2. Instrumentation Points

**ComplianceGuardian (`planner/compliance_guardian.py`):**
- Records rejection metrics when validation fails
- Tracks PII detection events with categorization
- Records suspicious pattern detections
- Measures validation performance

**ToolExecutor (`runtime/tool_executor.py`):**
- Records tool execution duration and status
- Tracks validation failures with error types
- Monitors tool performance and reliability

**Agent (`runtime/agent.py`):**
- Tracks conversation lifecycle and outcomes
- Records token usage for cost monitoring
- Measures generation performance
- Monitors reasoning loop iterations

### 3. Prometheus Configuration

#### Static Configuration (Development)

```yaml
scrape_configs:
  - job_name: 'filagent'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

#### Dynamic Configuration (Production)

**File-based Service Discovery:**
```yaml
scrape_configs:
  - job_name: 'filagent'
    file_sd_configs:
      - files:
          - '/etc/prometheus/targets/filagent.json'
        refresh_interval: 30s
```

**Kubernetes Service Discovery:**
```yaml
scrape_configs:
  - job_name: 'filagent-k8s'
    kubernetes_sd_configs:
      - role: pod
        namespaces:
          names:
            - filagent
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        action: keep
        regex: filagent
```

### 4. Target Generation Script

`scripts/generate_prometheus_targets.py` generates target configuration dynamically:

```bash
# Local development
python scripts/generate_prometheus_targets.py

# Docker environment
FILAGENT_HOST=filagent-api ENVIRONMENT=docker python scripts/generate_prometheus_targets.py

# Kubernetes environment
FILAGENT_HOST=filagent-service.filagent.svc.cluster.local ENVIRONMENT=k8s python scripts/generate_prometheus_targets.py
```

**Environment Variables:**
- `FILAGENT_HOST`: Hostname/IP of FilAgent API (default: localhost)
- `FILAGENT_PORT`: Port of FilAgent API (default: 8000)
- `ENVIRONMENT`: Environment name (default: development)
- `OUTPUT_FILE`: Output file path (default: config/prometheus_targets.json)

## Security and Privacy

### PII Protection

**User ID Hashing:**
```python
# User IDs are hashed before being used as labels
user_id_hash = hashlib.sha256(user_id.encode()).hexdigest()[:16]
```

**No Content in Labels:**
- Query content is **never** included in metric labels
- Tool arguments are **never** included in metric labels
- Only categorical data (tool names, status codes, error types) in labels

**PII Detection Categories:**
- PII types are categorical (`email`, `ssn`, `health_insurance`)
- Actual PII values are **never** exposed in metrics

### Security Monitoring

**Injection Detection:**
```promql
# Alert on suspicious patterns
rate(filagent_security_suspicious_pattern_total[5m]) > 0.1
```

**Compliance Violations:**
```promql
# Monitor high-risk rejections
sum(rate(filagent_compliance_rejection_total{risk_level="HIGH"}[5m]))
```

## Deployment Scenarios

### Local Development

1. Start FilAgent server:
   ```bash
   python runtime/server.py
   ```

2. Metrics available at: `http://localhost:8000/metrics`

3. Start Prometheus:
   ```bash
   prometheus --config.file=config/prometheus.yml
   ```

### Docker Deployment

1. Generate Docker targets:
   ```bash
   FILAGENT_HOST=filagent-api ENVIRONMENT=docker \
   OUTPUT_FILE=/etc/prometheus/targets/filagent.json \
   python scripts/generate_prometheus_targets.py
   ```

2. Mount targets file in Prometheus container:
   ```yaml
   volumes:
     - ./config/prometheus_targets_docker.json:/etc/prometheus/targets/filagent.json:ro
   ```

3. Start with docker-compose:
   ```bash
   docker-compose up
   ```

### Kubernetes Deployment

1. Use Kubernetes service discovery in `prometheus.yml`

2. Deploy FilAgent with appropriate labels:
   ```yaml
   metadata:
     labels:
       app: filagent
   ```

3. Prometheus will automatically discover pods

## Grafana Dashboards

### Security & Observability Dashboard

Location: `grafana/dashboard_security_observability.json`

**Panels:**
1. **Compliance Monitoring:**
   - Compliance rejections by reason and risk level
   - Validation status breakdown

2. **Tool Execution:**
   - P95 execution duration by tool
   - Success rate trends

3. **Security:**
   - Suspicious pattern detection (with alerts)
   - PII detection events

4. **Agent Performance:**
   - Conversation duration
   - Active conversations
   - Token usage rate

5. **Top Issues:**
   - Most common compliance rejection reasons
   - Frequent tool validation failures

### HTN Planning Dashboard

Location: `grafana/dashboard_htn.json`

Monitors HTN (Hierarchical Task Network) planning performance.

## PromQL Queries

### Compliance

```promql
# Compliance rejection rate by reason
sum(rate(filagent_compliance_rejection_total[5m])) by (reason)

# High-risk compliance validations
sum(rate(filagent_compliance_validation_total{risk_level="HIGH"}[5m]))

# Compliance validation duration P95
histogram_quantile(0.95, rate(filagent_compliance_validation_seconds_bucket[5m]))
```

### Tool Execution

```promql
# Tool execution P95 latency
histogram_quantile(0.95, sum(rate(filagent_tool_execution_seconds_bucket[5m])) by (tool_name, le))

# Tool success rate
sum(rate(filagent_tool_execution_total{status="success"}[5m])) by (tool_name) /
sum(rate(filagent_tool_execution_total[5m])) by (tool_name)

# Most used tools
topk(10, sum(increase(filagent_tool_execution_total[1h])) by (tool_name))
```

### Security

```promql
# Injection attempt rate
sum(rate(filagent_security_suspicious_pattern_total[5m])) by (pattern_type)

# PII detection by type
sum(rate(filagent_security_pii_detected_total[5m])) by (pii_type)

# Blocked security events
sum(rate(filagent_security_suspicious_pattern_total{action_taken="blocked"}[5m]))
```

### Performance

```promql
# Conversation throughput
sum(rate(filagent_conversations_total[5m]))

# Average conversation duration
rate(filagent_conversation_duration_seconds_sum[5m]) /
rate(filagent_conversation_duration_seconds_count[5m])

# Token consumption rate
sum(rate(filagent_tokens_total[5m])) by (token_type)

# Generation P95 latency
histogram_quantile(0.95, rate(filagent_generation_duration_seconds_bucket[5m]))
```

## Alerting Rules

### Critical Alerts

```yaml
groups:
  - name: filagent_critical
    interval: 30s
    rules:
      - alert: HighComplianceRejectionRate
        expr: rate(filagent_compliance_rejection_total[5m]) > 1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High compliance rejection rate"
          description: "Compliance rejections exceed 1/sec for 5 minutes"
      
      - alert: SuspiciousPatternDetection
        expr: rate(filagent_security_suspicious_pattern_total[5m]) > 0.1
        for: 1m
        labels:
          severity: high
        annotations:
          summary: "Suspicious patterns detected"
          description: "Potential injection attempts detected"
      
      - alert: ToolExecutionFailureSpike
        expr: rate(filagent_tool_execution_total{status="error"}[5m]) > 0.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High tool execution failure rate"
```

## Performance Considerations

### Cardinality Management

**Low Cardinality Labels:**
- Tool names (limited set)
- Status codes (success/error/timeout)
- Risk levels (LOW/MEDIUM/HIGH/CRITICAL)
- Error types (categorical)

**Avoided High Cardinality:**
- No user IDs (hashed to 16-char string)
- No conversation IDs
- No timestamps in labels
- No query content

### Resource Usage

**Typical Metrics Count:** ~50 time series per FilAgent instance

**Scrape Interval:** 15 seconds (default)

**Retention:** Recommended 30 days minimum for compliance auditing

## Troubleshooting

### Metrics Not Appearing

1. Check `/metrics` endpoint:
   ```bash
   curl http://localhost:8000/metrics
   ```

2. Verify Prometheus can reach target:
   ```bash
   curl http://localhost:9090/api/v1/targets
   ```

3. Check Prometheus logs for scrape errors

### High Memory Usage

- Review metric cardinality: `topk(10, count by (__name__)({__name__=~"filagent_.*"}))`
- Reduce retention period if needed
- Check for label explosion

### Missing Metrics After Code Changes

- Ensure imports are correct: `from runtime.metrics import get_agent_metrics`
- Verify `prometheus-client` is installed
- Check for exceptions in metric recording (logged but not raised)

## References

- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [OpenMetrics Specification](https://openmetrics.io/)
- [Grafana Dashboard Best Practices](https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/best-practices/)
- [Loi 25 Compliance Requirements](https://www.quebec.ca/en/government/policy/digital/data-protection)
