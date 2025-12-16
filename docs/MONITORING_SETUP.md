# Monitoring Setup Guide

## Quick Start

### Prerequisites
- Python 3.10+
- Prometheus 2.0+
- Grafana 9.0+ (optional, for dashboards)

### 1. Install FilAgent with Monitoring

```bash
# Install dependencies
pip install -r requirements.txt

# Verify prometheus-client is installed
pip show prometheus-client
```

### 2. Start FilAgent Server

```bash
# Development mode
python runtime/server.py

# Production mode (with uvicorn)
uvicorn runtime.server:app --host 0.0.0.0 --port 8000
```

**Verify metrics endpoint:**
```bash
curl http://localhost:8000/metrics
```

You should see output like:
```
# HELP filagent_tool_execution_seconds Time spent executing tools
# TYPE filagent_tool_execution_seconds histogram
filagent_tool_execution_seconds_bucket{tool_name="calculator",status="success",le="0.01"} 5.0
...
```

### 3. Configure Prometheus

**Option A: Local Development (Static Configuration)**

Use the default configuration:
```bash
prometheus --config.file=config/prometheus.yml
```

**Option B: Docker/K8s (Dynamic Configuration)**

Generate target configuration:
```bash
# Docker
FILAGENT_HOST=filagent-api ENVIRONMENT=docker \
python scripts/generate_prometheus_targets.py

# Kubernetes
FILAGENT_HOST=filagent-service.filagent.svc.cluster.local ENVIRONMENT=k8s \
python scripts/generate_prometheus_targets.py
```

### 4. Access Prometheus

Open Prometheus UI: `http://localhost:9090`

**Test queries:**
```promql
# All FilAgent metrics
{__name__=~"filagent_.*"}

# Compliance rejections
filagent_compliance_rejection_total

# Tool execution rate
rate(filagent_tool_execution_total[5m])
```

### 5. Import Grafana Dashboards

1. Open Grafana: `http://localhost:3000`
2. Go to Dashboards → Import
3. Upload dashboard JSON files:
   - `grafana/dashboard_security_observability.json`
   - `grafana/dashboard_htn.json`

## Environment-Specific Setup

### Local Development

**1. Edit Prometheus configuration:**
```yaml
# config/prometheus.yml
scrape_configs:
  - job_name: 'filagent'
    static_configs:
      - targets: ['localhost:8000']
```

**2. Start services:**
```bash
# Terminal 1: FilAgent
python runtime/server.py

# Terminal 2: Prometheus
prometheus --config.file=config/prometheus.yml

# Terminal 3: Grafana (if installed)
grafana-server
```

### Docker Deployment

**1. Update docker-compose.yml:**
```yaml
version: '3.8'

services:
  filagent:
    build: .
    ports:
      - "8000:8000"
    labels:
      - "prometheus.scrape=true"
      - "prometheus.port=8000"
      - "prometheus.path=/metrics"
  
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./config/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./config/prometheus_targets_docker.json:/etc/prometheus/targets/filagent.json:ro
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
  
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - ./grafana:/etc/grafana/provisioning/dashboards:ro
```

**2. Generate Docker targets:**
```bash
FILAGENT_HOST=filagent ENVIRONMENT=docker \
OUTPUT_FILE=config/prometheus_targets_docker.json \
python scripts/generate_prometheus_targets.py
```

**3. Start stack:**
```bash
docker-compose up -d
```

### Kubernetes Deployment

**1. Deploy FilAgent:**
```yaml
# filagent-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: filagent
  namespace: filagent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: filagent
  template:
    metadata:
      labels:
        app: filagent
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      containers:
      - name: filagent
        image: filagent:latest
        ports:
        - containerPort: 8000
          name: http
---
apiVersion: v1
kind: Service
metadata:
  name: filagent-service
  namespace: filagent
spec:
  selector:
    app: filagent
  ports:
  - port: 8000
    targetPort: 8000
    name: http
```

**2. Configure Prometheus with K8s service discovery:**

Already configured in `config/prometheus.yml`:
```yaml
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

**3. Deploy:**
```bash
kubectl apply -f filagent-deployment.yaml
```

## Verification

### Check Metrics Collection

**1. Verify endpoint:**
```bash
curl http://localhost:8000/metrics | grep filagent_
```

**2. Check Prometheus targets:**
Open `http://localhost:9090/targets` and verify FilAgent target is UP.

**3. Query metrics:**
```promql
# Count of metrics
count({__name__=~"filagent_.*"})

# Last scrape success
up{job="filagent"}
```

### Generate Test Data

**Run a test conversation:**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Calculate 2 + 2"}
    ]
  }'
```

**Check metrics were recorded:**
```bash
# Tool execution metrics
curl -s http://localhost:8000/metrics | grep filagent_tool_execution

# Conversation metrics
curl -s http://localhost:8000/metrics | grep filagent_conversations
```

## Alerting Setup

### Prometheus Alerts

**1. Create alert rules file:**
```yaml
# config/prometheus_alerts.yml
groups:
  - name: filagent_alerts
    rules:
      - alert: HighComplianceRejectionRate
        expr: rate(filagent_compliance_rejection_total[5m]) > 1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High compliance rejection rate"
      
      - alert: SuspiciousPatternDetection
        expr: rate(filagent_security_suspicious_pattern_total[5m]) > 0.1
        for: 1m
        labels:
          severity: high
        annotations:
          summary: "Suspicious patterns detected"
```

**2. Update Prometheus configuration:**
```yaml
# config/prometheus.yml
rule_files:
  - 'prometheus_alerts.yml'
```

**3. Configure Alertmanager (optional):**
```yaml
# alertmanager.yml
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'severity']
  receiver: 'default'

receivers:
  - name: 'default'
    slack_configs:
      - api_url: 'YOUR_SLACK_WEBHOOK'
        channel: '#alerts'
```

### Grafana Alerts

**1. Configure alert channels:**
- Go to Alerting → Notification channels
- Add channels: Email, Slack, PagerDuty, etc.

**2. Enable alerts on dashboards:**
- Open Security & Observability dashboard
- Edit "Suspicious Patterns Detected" panel
- Configure alert threshold (default: 0.1 req/sec)

## Troubleshooting

### Metrics Not Appearing

**Problem:** `/metrics` endpoint returns empty or minimal data.

**Solutions:**
1. Check if `prometheus-client` is installed:
   ```bash
   pip show prometheus-client
   ```

2. Verify metrics are being recorded:
   ```python
   # Test in Python console
   from runtime.metrics import get_agent_metrics
   metrics = get_agent_metrics()
   metrics.record_tool_execution("test", 0.1, "success")
   ```

3. Check server logs for errors

### Prometheus Can't Scrape Target

**Problem:** Target shows as DOWN in Prometheus.

**Solutions:**
1. Verify FilAgent is running:
   ```bash
   curl http://localhost:8000/health
   ```

2. Check network connectivity:
   ```bash
   # From Prometheus container/pod
   curl http://filagent:8000/metrics
   ```

3. Verify target configuration:
   ```bash
   # Check targets file
   cat config/prometheus_targets.json
   ```

4. Check Prometheus logs:
   ```bash
   docker logs prometheus
   # or
   kubectl logs -n monitoring prometheus-xxx
   ```

### High Cardinality Warning

**Problem:** Prometheus warns about high cardinality.

**Solutions:**
1. Check metric cardinality:
   ```promql
   topk(10, count by (__name__, job)({__name__=~"filagent_.*"}))
   ```

2. Verify no dynamic labels:
   ```bash
   # Should only see categorical labels
   curl http://localhost:8000/metrics | grep filagent_tool_execution_seconds
   ```

3. Review label usage in code (should be categorical only)

### Grafana Dashboard Not Working

**Problem:** Dashboard shows "No data" or errors.

**Solutions:**
1. Verify Prometheus data source:
   - Configuration → Data Sources
   - Test connection to Prometheus

2. Check queries in dashboard:
   - Edit panel → Query tab
   - Verify metric names and labels

3. Verify data exists:
   ```promql
   # In Prometheus
   {__name__=~"filagent_.*"}
   ```

## Performance Tuning

### Reduce Scrape Interval

For high-traffic environments, reduce scrape interval:
```yaml
global:
  scrape_interval: 10s  # default: 15s
```

### Increase Retention

For compliance requirements, increase retention:
```bash
prometheus \
  --config.file=/etc/prometheus/prometheus.yml \
  --storage.tsdb.retention.time=90d \
  --storage.tsdb.retention.size=50GB
```

### Optimize Queries

Use recording rules for expensive queries:
```yaml
groups:
  - name: filagent_recording
    interval: 30s
    rules:
      - record: filagent:tool_success_rate:5m
        expr: |
          sum(rate(filagent_tool_execution_total{status="success"}[5m])) by (tool_name) /
          sum(rate(filagent_tool_execution_total[5m])) by (tool_name)
```

## Next Steps

1. **Set up alerts:** Configure Alertmanager for critical events
2. **Create runbooks:** Document response procedures for alerts
3. **Regular reviews:** Schedule weekly metric reviews
4. **Tune thresholds:** Adjust alert thresholds based on baseline
5. **Extend dashboards:** Add custom panels for specific needs

## Resources

- [Monitoring Architecture](./MONITORING_ARCHITECTURE.md)
- [Security Enhancements](./SECURITY_ENHANCEMENTS.md)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review logs: `logs/` directory
3. Open issue on GitHub
4. Contact: See `README.md` for contact information
