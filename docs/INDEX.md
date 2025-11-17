# FilAgent Documentation Index

**Version**: 1.0.0
**Last Updated**: 2025-11-16

This index provides a comprehensive overview of all documentation available for FilAgent.

---

## Core Documentation

### Getting Started

- [README.md](/README.md) - Project overview, quick start, and installation
- [QUICK_TEST.md](/QUICK_TEST.md) - **NEW** Quick testing guide post-installation (2025-11-16)
- [README_DEPLOYMENT.md](/README_DEPLOYMENT.md) - **NEW** Production deployment guide (2025-11-16)
- [CLAUDE.md](/CLAUDE.md) - Comprehensive guide for AI assistants
- [GUIDE_COMPLET_FILAGENT.md](/GUIDE_COMPLET_FILAGENT.md) - Complete user guide (French)

### Configuration & Setup

- [.env.example](/.env.example) - Environment variables template (Updated 2025-11-16)
- [models/weights/README.md](/models/weights/README.md) - Model download guide (Updated 2025-11-16)
- [CONFIGURATION_CAPACITES.md](/docs/CONFIGURATION_CAPACITES.md) - Detailed configuration options
- [DEPENDENCY_MANAGEMENT.md](/docs/DEPENDENCY_MANAGEMENT.md) - PDM and dependency setup
- [PDM_QUICK_REFERENCE.md](/docs/PDM_QUICK_REFERENCE.md) - Quick reference for PDM commands

---

## Feature Documentation

### LLM Integration

- [PERPLEXITY_INTEGRATION.md](/docs/PERPLEXITY_INTEGRATION.md) - Perplexity API setup and usage
- [runtime/model_interface.py](/runtime/model_interface.py) - Model interface implementation

**Available Backends**:
- llama.cpp (local inference)
- Perplexity API (cloud inference with web search)

### Compliance & Governance

- [COMPLIANCE_GUARDIAN.md](/docs/COMPLIANCE_GUARDIAN.md) - Compliance module documentation
- [config/policies.yaml](/config/policies.yaml) - RBAC, PII masking, guardrails
- [config/retention.yaml](/config/retention.yaml) - Data retention policies
- [config/compliance_rules.yaml](/config/compliance_rules.yaml) - Compliance rules

### Monitoring & Observability

- [PROMETHEUS_SETUP.md](/docs/PROMETHEUS_SETUP.md) - Prometheus monitoring setup
- [PROMETHEUS_QUICKSTART.md](/docs/PROMETHEUS_QUICKSTART.md) - Quick start guide
- [PROMETHEUS_DASHBOARD.md](/docs/PROMETHEUS_DASHBOARD.md) - Dashboard configuration
- [PROMETHEUS_PROMQL_EXAMPLES.md](/docs/PROMETHEUS_PROMQL_EXAMPLES.md) - PromQL query examples

### Performance & Benchmarks

- [BENCHMARKS.md](/docs/BENCHMARKS.md) - Benchmark suite and performance targets
- [config/eval_targets.yaml](/config/eval_targets.yaml) - Evaluation thresholds

---

## Architecture Documentation

### Architecture Decision Records (ADRs)

- [ADR-001: Initial Architecture](/docs/ADRs/001-initial-architecture.md)
- [ADR-002: Decision Records](/docs/ADRs/002-decision-records.md)
- [ADR-003: OpenAPI Placement](/docs/ADRs/003-openapi-placement.md)

### API Documentation

- [INTEGRATION_OPENAPI.md](/docs/INTEGRATION_OPENAPI.md) - OpenAPI integration guide
- [OPENAPI_INTEGRATION_SUMMARY.md](/docs/OPENAPI_INTEGRATION_SUMMARY.md) - Integration summary
- [openapi.yaml](/openapi.yaml) - OpenAPI specification

---

## CI/CD & Quality

### Continuous Integration

- [CODEQL_VERIFICATION.md](/docs/CODEQL_VERIFICATION.md) - CodeQL setup verification
- [CODEQL_WORKFLOWS.md](/docs/CODEQL_WORKFLOWS.md) - CodeQL workflow documentation
- [CODEQL_VERIFICATION_SUMMARY.md](/docs/CODEQL_VERIFICATION_SUMMARY.md) - Verification summary
- [CI_FIX_DOCUMENTATION.md](/docs/CI_FIX_DOCUMENTATION.md) - CI troubleshooting

### Documentation Updates

- [DOCUMENTATION_UPDATE_2025-11-16.md](/docs/DOCUMENTATION_UPDATE_2025-11-16.md) - **NEW** Documentation update report (2025-11-16)

### Testing

- [tests/](/tests/) - Test suite
- [pytest.ini](/pytest.ini) - Pytest configuration
- [.flake8](/.flake8) - Linting configuration

---

## Standard Operating Procedures (SOPs)

Located in [docs/SOPs/](/docs/SOPs/):

- Incident response procedures
- Deployment procedures
- Backup and recovery procedures
- Security incident handling

---

## Configuration Files Reference

### Main Configuration

- [config/agent.yaml](/config/agent.yaml) - Main agent configuration
- [config/agent.perplexity.yaml](/config/agent.perplexity.yaml) - Perplexity-specific configuration

### Policy Configuration

- [config/policies.yaml](/config/policies.yaml) - RBAC, PII, guardrails
- [config/compliance_rules.yaml](/config/compliance_rules.yaml) - Compliance rules
- [config/retention.yaml](/config/retention.yaml) - Data retention policies
- [config/provenance.yaml](/config/provenance.yaml) - Traceability configuration

### Monitoring Configuration

- [config/prometheus.yml](/config/prometheus.yml) - Prometheus configuration
- [grafana/](/grafana/) - Grafana dashboards

---

## Examples

- [examples/perplexity_example.py](/examples/perplexity_example.py) - Perplexity API usage example
- [examples/](/examples/) - Additional usage examples

---

## Quick Links by Role

### For Developers

1. [CLAUDE.md](/CLAUDE.md) - Complete development guide
2. [DEPENDENCY_MANAGEMENT.md](/docs/DEPENDENCY_MANAGEMENT.md) - Dependency setup
3. [BENCHMARKS.md](/docs/BENCHMARKS.md) - Performance testing
4. [runtime/model_interface.py](/runtime/model_interface.py) - Model interface

### For Operations

1. [PROMETHEUS_SETUP.md](/docs/PROMETHEUS_SETUP.md) - Monitoring setup
2. [docs/SOPs/](/docs/SOPs/) - Operational procedures
3. [COMPLIANCE_GUARDIAN.md](/docs/COMPLIANCE_GUARDIAN.md) - Compliance module
4. [config/retention.yaml](/config/retention.yaml) - Data retention

### For Compliance/Legal

1. [COMPLIANCE_GUARDIAN.md](/docs/COMPLIANCE_GUARDIAN.md) - Compliance framework
2. [docs/ADRs/](/docs/ADRs/) - Architecture decisions
3. [config/policies.yaml](/config/policies.yaml) - Access policies
4. [config/compliance_rules.yaml](/config/compliance_rules.yaml) - Compliance rules

### For End Users

1. [README.md](/README.md) - Getting started
2. [QUICK_TEST.md](/QUICK_TEST.md) - **NEW** Quick testing guide
3. [README_DEPLOYMENT.md](/README_DEPLOYMENT.md) - **NEW** Deployment guide
4. [GUIDE_COMPLET_FILAGENT.md](/GUIDE_COMPLET_FILAGENT.md) - Complete guide
5. [PERPLEXITY_INTEGRATION.md](/docs/PERPLEXITY_INTEGRATION.md) - Perplexity setup
6. [.env.example](/.env.example) - Configuration template

---

## Contributing to Documentation

When adding new documentation:

1. Follow the existing format and style
2. Include version and last updated date
3. Add entry to this index
4. Use consistent terminology
5. Include code examples where applicable
6. Cross-reference related documents

### Documentation Standards

- **Language**: French for user-facing docs, English for technical docs
- **Format**: Markdown (.md)
- **Style**: Clear, concise, professional
- **Structure**: Headers, code blocks, tables, lists
- **Examples**: Practical, tested examples

---

## Support

**Questions or Issues?**
- GitHub Issues: https://github.com/fil04331/FilAgent/issues
- Security: security@filagent.ai
- Governance: governance@filagent.ai

---

**Last Updated**: 2025-11-16
**Maintainer**: FilAgent Technical Writing Team
