# Security Monitoring & Alerting Guide
## FilAgent Production Security Monitoring

**Date**: 2025-11-23
**Version**: 1.0
**Purpose**: Real-time detection and response to security incidents

---

## PART 1: SECURITY METRICS & KPIs

### Key Security Metrics

#### 1. Vulnerability Metrics
```prometheus
# Critical vulnerabilities
filagent_vulnerabilities_critical_total
filagent_vulnerabilities_high_total
filagent_vulnerabilities_medium_total

# Dependency vulnerabilities
filagent_dependency_vulnerabilities_count{severity="CRITICAL"}

# Time to remediation
filagent_vulnerability_ttf_days{severity="CRITICAL"}  # Time to fix
```

#### 2. Attack Detection Metrics
```prometheus
# Log injection attempts
filagent_security_log_injection_attempts_total{status="blocked"}
filagent_security_log_injection_attempts_total{status="detected"}

# Path traversal attempts
filagent_security_path_traversal_attempts_total{status="blocked"}

# Rate limit violations
filagent_rate_limit_violations_total{endpoint="/chat"}

# Failed authentication attempts
filagent_auth_failures_total{reason="invalid_token"}
filagent_auth_failures_total{reason="missing_token"}
```

#### 3. Audit Trail Metrics
```prometheus
# WORM logging integrity
filagent_worm_integrity_check_total{status="pass"}
filagent_worm_integrity_check_total{status="fail"}

# Decision Record generation
filagent_decision_records_created_total
filagent_decision_records_verified_total{status="valid"}

# Log sanitization
filagent_logs_sanitized_total
filagent_logs_injection_attempts_sanitized_total
```

#### 4. Compliance Metrics
```prometheus
# PII handling
filagent_pii_detected_total
filagent_pii_redacted_total

# Retention policy enforcement
filagent_data_purged_total{reason="retention_expired"}

# Loi 25 compliance
filagent_loi25_violations_total
```

#### 5. Availability Metrics
```prometheus
# Server uptime
filagent_uptime_seconds

# Error rates
filagent_errors_total{type="security"}
filagent_errors_total{type="authorization"}

# Response times
filagent_request_duration_seconds
```

---

## PART 2: ALERTING RULES

### Critical Alerts (Immediate Notification)

#### Alert 1: Log Injection Attack Detected
```yaml
alert: SecurityLogInjectionDetected
expr: increase(filagent_security_log_injection_attempts_total{status="blocked"}[1m]) > 0
for: 1m
severity: CRITICAL
annotations:
  summary: "Log injection attack detected and blocked"
  description: "{{ $value }} injection attempts in last minute"
  action: |
    1. Check source IP: {{ $labels.source_ip }}
    2. Review attempted payloads in logs
    3. Block IP if pattern continues
    4. Notify security team immediately
  runbook: "docs/runbooks/log_injection_response.md"
```

#### Alert 2: Path Traversal Attack Detected
```yaml
alert: SecurityPathTraversalDetected
expr: increase(filagent_security_path_traversal_attempts_total{status="blocked"}[1m]) > 0
for: 1m
severity: CRITICAL
annotations:
  summary: "Path traversal attack detected and blocked"
  description: "{{ $value }} traversal attempts in last minute"
  action: |
    1. Identify target files (from logs)
    2. Check if access was successful
    3. Review file permissions
    4. Block attacker IP
  runbook: "docs/runbooks/path_traversal_response.md"
```

#### Alert 3: Audit Trail Integrity Violation
```yaml
alert: AuditTrailCompromised
expr: increase(filagent_worm_integrity_check_total{status="fail"}[5m]) > 0
for: 1m
severity: CRITICAL
annotations:
  summary: "Audit trail integrity check failed - possible tampering"
  description: "WORM logging integrity validation failed"
  action: |
    1. IMMEDIATELY isolate system
    2. Review all logs from failure point
    3. Check for forged Decision Records
    4. Activate incident response team
    5. Preserve forensic evidence
  runbook: "docs/runbooks/audit_trail_incident.md"
```

#### Alert 4: Unauthorized File Access
```yaml
alert: UnauthorizedFileAccessAttempt
expr: increase(filagent_errors_total{type="permission_denied"}[5m]) > 5
for: 1m
severity: HIGH
annotations:
  summary: "Multiple unauthorized file access attempts"
  description: "{{ $value }} permission denied errors in 5 minutes"
  action: |
    1. Identify user account: {{ $labels.user_id }}
    2. Check file access attempts
    3. Review user role/permissions
    4. Revoke access if compromised account suspected
  runbook: "docs/runbooks/unauthorized_access.md"
```

#### Alert 5: Rate Limit Exceeded
```yaml
alert: RateLimitExceeded
expr: rate(filagent_rate_limit_violations_total[5m]) > 0.5
for: 1m
severity: HIGH
annotations:
  summary: "Rate limiting triggered"
  description: "{{ $value }} rate limit violations from {{ $labels.client_ip }}"
  action: |
    1. Check if legitimate spike in usage
    2. If attack pattern: block IP
    3. Review endpoint: {{ $labels.endpoint }}
    4. Increase limit if legitimate need
```

### High Priority Alerts (Email + Slack)

#### Alert 6: Critical Vulnerability Detected
```yaml
alert: CriticalVulnerabilityDetected
expr: filagent_vulnerabilities_critical_total > 0
for: 15m
severity: HIGH
annotations:
  summary: "Critical vulnerability detected in codebase"
  description: "CVE: {{ $labels.cve_id }}"
  action: |
    1. Review vulnerability details
    2. Assess impact on FilAgent
    3. Create security patch
    4. Deploy patch to prod within 24 hours
```

#### Alert 7: Authentication Failures Spike
```yaml
alert: AuthenticationFailureSpike
expr: rate(filagent_auth_failures_total[5m]) > 10
for: 5m
severity: HIGH
annotations:
  summary: "Spike in authentication failures"
  description: "{{ $value }} auth failures per second"
  action: |
    1. Check for brute force attack
    2. Review failed login attempts
    3. Block attacker IP
    4. Notify users if needed
```

#### Alert 8: Data Breach Detection
```yaml
alert: PossibleDataBreach
expr: |
  (increase(filagent_pii_detected_total[1m]) > 0) and
  (filagent_pii_redacted_total == 0)
for: 1m
severity: CRITICAL
annotations:
  summary: "PII detected but NOT redacted - possible data breach"
  description: "PII patterns detected without redaction"
  action: |
    1. IMMEDIATELY stop all operations
    2. Isolate affected system
    3. Notify compliance officer
    4. Begin incident investigation
    5. Prepare breach notification (Loi 25)
```

### Medium Priority Alerts (Email)

#### Alert 9: Certificate Expiration Warning
```yaml
alert: CertificateExpirationWarning
expr: ssl_certificate_expires_in_seconds < 2592000  # 30 days
for: 1h
severity: MEDIUM
annotations:
  summary: "SSL certificate expires in {{ $value | humanizeDuration }}"
  action: "Renew certificate before expiration"
```

#### Alert 10: Backup Failure
```yaml
alert: AuditLogBackupFailed
expr: increase(filagent_backup_failures_total[1h]) > 0
for: 1h
severity: MEDIUM
annotations:
  summary: "Audit log backup failed"
  description: "Cannot backup audit logs to secure storage"
  action: |
    1. Check backup storage connectivity
    2. Verify disk space
    3. Restart backup job
    4. Monitor for next successful backup
```

---

## PART 3: INCIDENT DETECTION PATTERNS

### Log Patterns for Manual Investigation

```bash
# Search for log injection attempts
grep -E "\\\\n|\\\\r|\[INFO\]|\[ERROR\].*UTC" /path/to/logs/*.jsonl | \
  grep -v "\"timestamp\"" | \
  wc -l

# Search for path traversal attempts
grep -E "\\.\\./|%2e%2e|\\\\\\.\\\\" /path/to/logs/*.jsonl | \
  jq 'select(.event == "path.access")'

# Search for failed authentication
grep "auth_failure\|unauthorized\|401\|403" /path/to/logs/*.jsonl | \
  jq -s 'group_by(.source_ip) | map({ip: .[0].source_ip, count: length}) | sort_by(.count)'

# Search for suspicious tool usage
grep "tool.call" /path/to/logs/*.jsonl | \
  jq 'select(.tool_name == "file_delete" or .tool_name == "system_command")'

# Search for PII leakage
grep -iE "[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}|[0-9]{3}-[0-9]{2}-[0-9]{4}" /path/to/logs/*.jsonl | \
  grep -v "\\[EMAIL_REDACTED\\]" | \
  head -20
```

---

## PART 4: DASHBOARD CONFIGURATION

### Grafana Dashboard JSON

**File**: `config/grafana_security_dashboard.json`

```json
{
  "dashboard": {
    "title": "FilAgent Security Monitoring",
    "description": "Real-time security monitoring dashboard",
    "timezone": "UTC",
    "refresh": "30s",
    "panels": [
      {
        "title": "Security Alerts (Last 24h)",
        "type": "stat",
        "targets": [
          {
            "expr": "increase(filagent_security_log_injection_attempts_total{status='blocked'}[24h])"
          }
        ]
      },
      {
        "title": "Attack Timeline",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(filagent_security_attacks_total[5m])"
          }
        ]
      },
      {
        "title": "Critical Vulnerabilities",
        "type": "table",
        "targets": [
          {
            "expr": "filagent_vulnerabilities_critical_total"
          }
        ]
      },
      {
        "title": "Audit Trail Integrity",
        "type": "gauge",
        "targets": [
          {
            "expr": "filagent_worm_integrity_check_total{status='pass'} / (filagent_worm_integrity_check_total{status='pass'} + filagent_worm_integrity_check_total{status='fail'})"
          }
        ],
        "min": 0,
        "max": 1,
        "thresholds": {
          "mode": "absolute",
          "steps": [
            {"color": "red", "value": null},
            {"color": "yellow", "value": 0.95},
            {"color": "green", "value": 0.99}
          ]
        }
      },
      {
        "title": "PII Protection Status",
        "type": "pie",
        "targets": [
          {
            "expr": "filagent_pii_redacted_total",
            "legendFormat": "Redacted"
          },
          {
            "expr": "filagent_pii_detected_total - filagent_pii_redacted_total",
            "legendFormat": "Unredacted (ERROR)"
          }
        ]
      }
    ]
  }
}
```

---

## PART 5: NOTIFICATION CHANNELS

### Email Configuration

```yaml
# File: config/alerting_channels.yaml
channels:
  email:
    enabled: true
    smtp_server: "smtp.company.com"
    smtp_port: 587
    from_address: "security-alerts@filagent.ai"
    recipients:
      critical: ["security-team@company.com", "ciso@company.com"]
      high: ["security-team@company.com"]
      medium: ["security-ops@company.com"]

  slack:
    enabled: true
    webhook_url: "${SLACK_WEBHOOK_URL}"
    channels:
      critical: "#security-critical"
      high: "#security-alerts"
      medium: "#security-warnings"

  pagerduty:
    enabled: true
    integration_key: "${PAGERDUTY_KEY}"
    severity_mapping:
      critical: "critical"
      high: "high"
      medium: "medium"

  siem:
    enabled: true
    type: "kafka"
    broker: "kafka.company.com:9092"
    topic: "security_events"
```

### Slack Message Template

```json
{
  "text": "🚨 CRITICAL SECURITY ALERT",
  "blocks": [
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*Alert*: {{ alert_name }}\n*Severity*: {{ severity }}\n*Time*: {{ alert_time }}"
      }
    },
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "{{ description }}"
      }
    },
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*Action Required*:\n{{ action }}"
      }
    },
    {
      "type": "actions",
      "elements": [
        {
          "type": "button",
          "text": "View Incident",
          "url": "{{ dashboard_url }}"
        },
        {
          "type": "button",
          "text": "View Logs",
          "url": "{{ logs_url }}"
        }
      ]
    }
  ]
}
```

---

## PART 6: INCIDENT RESPONSE AUTOMATION

### Auto-Response Actions

```python
# File: runtime/middleware/incident_auto_response.py

class AutoResponseHandler:
    """Automatically respond to detected security incidents"""

    async def handle_log_injection(self, attack_info: dict):
        """Auto-response for log injection attacks"""
        # 1. Block attacker IP
        await self.firewall.block_ip(attack_info['source_ip'], duration_hours=24)

        # 2. Create incident ticket
        await self.ticketing.create_incident(
            title="Log Injection Attack Detected",
            severity="CRITICAL",
            description=f"Attack from {attack_info['source_ip']}: {attack_info['payload']}"
        )

        # 3. Notify security team
        await self.notify_team("critical", incident_id=incident.id)

        # 4. Begin forensic data collection
        await self.forensics.collect_evidence(
            start_time=attack_info['timestamp'],
            duration_minutes=60
        )

    async def handle_path_traversal(self, attack_info: dict):
        """Auto-response for path traversal attacks"""
        # 1. Block attacker IP
        await self.firewall.block_ip(attack_info['source_ip'])

        # 2. Check file access logs
        suspicious_files = await self.audit.find_accessed_files(
            user=attack_info['user_id'],
            start_time=attack_info['timestamp'] - timedelta(minutes=10)
        )

        if suspicious_files:
            # 3. Revoke user session
            await self.auth.revoke_session(attack_info['session_id'])

            # 4. Escalate to critical
            await self.notify_team("critical",
                incident_type="path_traversal_successful"
            )

    async def handle_audit_trail_compromise(self):
        """Auto-response for audit trail tampering"""
        # 1. IMMEDIATE isolation
        await self.system.isolate()

        # 2. Alert all personnel
        await self.notify_team("critical",
            message="AUDIT TRAIL COMPROMISED - SYSTEM ISOLATED"
        )

        # 3. Disable all external access
        await self.firewall.deny_all_outbound()

        # 4. Preserve forensic evidence
        await self.forensics.create_memory_dump()
        await self.forensics.preserve_logs()
```

---

## PART 7: COMPLIANCE MONITORING

### Loi 25 Compliance Monitoring

```python
# File: runtime/middleware/compliance_monitoring.py

class Loi25Monitor:
    """Monitor Loi 25 compliance in real-time"""

    async def check_audit_trail_integrity(self):
        """Verify audit trail has not been tampered with"""
        result = await self.worm_logger.verify_integrity()
        if not result.valid:
            await self.alert("CRITICAL", "Audit trail integrity compromised")

    async def check_pii_redaction(self):
        """Verify all PII is properly redacted in logs"""
        unredacted_pii = await self.scan_logs_for_unredacted_pii()
        if unredacted_pii:
            count = len(unredacted_pii)
            await self.alert("CRITICAL",
                f"Found {count} unredacted PII entries - possible breach")

    async def check_retention_policy(self):
        """Verify data retention policies are being enforced"""
        expired_data = await self.find_expired_data()
        if expired_data and not await self.verify_purged():
            await self.alert("HIGH", "Expired data not purged - retention violation")

    async def check_breach_notification_log(self):
        """Verify breaches are being properly logged for notification"""
        # If PII breach detected but no notification logged
        breaches = await self.find_unnotified_breaches()
        if breaches:
            await self.alert("CRITICAL",
                f"Found {len(breaches)} unnotified breaches - legal violation")

    async def run_compliance_check(self):
        """Run all Loi 25 checks"""
        checks = [
            self.check_audit_trail_integrity(),
            self.check_pii_redaction(),
            self.check_retention_policy(),
            self.check_breach_notification_log(),
        ]

        results = await asyncio.gather(*checks, return_exceptions=True)
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "framework": "Loi25",
            "results": results,
            "compliant": all(r.compliant for r in results if hasattr(r, 'compliant'))
        }
```

---

## PART 8: OPERATIONAL RUNBOOKS

### Runbook 1: Log Injection Attack Response

**File**: `docs/runbooks/log_injection_response.md`

```markdown
# Log Injection Attack Response

## Detection
- Alert: `SecurityLogInjectionDetected`
- Typical source: Web application input (Gradio interface, API)

## Immediate Actions (0-5 minutes)
1. Note attack timestamp and source IP
2. Pull raw logs around incident time
3. Search for forged entries:
   ```bash
   grep -E "\[CRITICAL\]|\[EMERGENCY\]|\[ALERT\]" logs/ | grep -v "^{" | head -20
   ```
4. Check WORM integrity:
   ```bash
   python scripts/verify_worm_integrity.py
   ```

## Investigation (5-30 minutes)
1. Determine what was attacked (logs, DRs, audit trail)
2. Check if forged entries affect compliance
3. Identify attacker motivation
4. Search for similar patterns in past logs

## Remediation (30-60 minutes)
1. Apply log injection fixes (see SECURITY_HARDENING_IMPLEMENTATION.md)
2. Redeploy with sanitized logger
3. Verify fix with test payloads
4. Run full test suite

## Post-Incident (1-24 hours)
1. Update WAF rules to block payloads
2. Block attacker IP permanently
3. Audit user account if internal
4. Document incident in compliance records
5. Schedule architecture review

## Escalation Criteria
- ESCALATE if: Forged Decision Records created
- ESCALATE if: Audit trail integrity compromised
- ESCALATE if: Multiple coordinated attacks detected
```

---

## PART 9: SECURITY METRICS COLLECTION

### Prometheus Exporter Configuration

```python
# File: runtime/middleware/security_metrics.py

from prometheus_client import Counter, Gauge, Histogram

# Attack detection metrics
log_injection_attempts = Counter(
    'filagent_security_log_injection_attempts_total',
    'Log injection attempts detected',
    ['status', 'source_ip']  # status: blocked, detected
)

path_traversal_attempts = Counter(
    'filagent_security_path_traversal_attempts_total',
    'Path traversal attempts',
    ['status', 'source_ip']
)

# Audit trail metrics
worm_integrity_checks = Counter(
    'filagent_worm_integrity_check_total',
    'WORM integrity check results',
    ['status']  # status: pass, fail
)

decision_records_created = Counter(
    'filagent_decision_records_created_total',
    'Decision Records created'
)

# Vulnerability metrics
critical_vulnerabilities = Gauge(
    'filagent_vulnerabilities_critical_total',
    'Number of critical vulnerabilities'
)

# PII metrics
pii_detected = Counter(
    'filagent_pii_detected_total',
    'PII patterns detected in logs'
)

pii_redacted = Counter(
    'filagent_pii_redacted_total',
    'PII successfully redacted'
)
```

---

## DEPLOYMENT MONITORING CHECKLIST

- [ ] Prometheus scraping metrics correctly
- [ ] Grafana dashboard displaying all metrics
- [ ] Alert rules loaded and active
- [ ] Email notifications configured and tested
- [ ] Slack integration active
- [ ] PagerDuty escalation configured
- [ ] Log aggregation (ELK/Splunk) receiving logs
- [ ] SIEM integration receiving events
- [ ] Auto-response rules configured
- [ ] Incident detection patterns loaded
- [ ] Compliance monitoring queries active
- [ ] Backup verification scripts running

---

**Next Steps**: Configure monitoring infrastructure, deploy to staging, validate alerts, then production rollout.

