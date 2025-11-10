# Security Policy

## Supported Versions

The following FilAgent versions are currently supported with security updates:

| Version   | Supported          | Status                    |
| --------- | ------------------ | ------------------------- |
| 0.3.x     | :white_check_mark: | Active development        |
| 0.2.x     | :white_check_mark: | Maintenance mode          |
| 0.1.x     | :x:                | End of life               |
| < 0.1     | :x:                | End of life               |

**Note:** FilAgent is currently in pre-1.0 development. Once version 1.0 is released, we will maintain the latest major version and the previous major version with security updates.

## Reporting a Vulnerability

If you discover a security vulnerability in FilAgent, please report it promptly using the following procedure:

### Contact Information
- **Email:** security@filagent.ai
- **GitHub Security Advisory:** [FilAgent Security Advisories](https://github.com/fil04331/FilAgent/security/advisories)
- **PGP Key:** For sensitive reports, please encrypt using our [public PGP key](https://github.com/fil04331/FilAgent/blob/main/.github/SECURITY_PGP.txt)

### Reporting Procedure
1. Send an email to `security@filagent.ai` with the subject line "Vulnerability Report: [Short Description]".
2. Include the following information:
   - A detailed description of the vulnerability
   - Steps to reproduce the issue
   - Impact assessment (data affected, possible exploit scenarios)
   - Affected versions
   - Your contact information for follow-up
   - Any relevant logs, screenshots, or proof-of-concept code
3. If your report contains sensitive information, please encrypt it using our PGP key.

### Response Times
- **Initial acknowledgment:** Within 2 business days
- **Status update:** Within 7 business days
- **Resolution or mitigation plan:** Within 30 days, depending on severity

### Severity Classification
We use the following severity levels based on CVSS scores:

| Severity | CVSS Score | Response Time |
| -------- | ---------- | ------------- |
| Critical | 9.0-10.0   | 24-48 hours   |
| High     | 7.0-8.9    | 7 days        |
| Medium   | 4.0-6.9    | 14 days       |
| Low      | 0.1-3.9    | 30 days       |

### Escalation Process
- If you do not receive a response within the stated timeframes, you may escalate by contacting the FilAgent Governance Board at **governance@filagent.ai**.
- **Note:** The email address `governance@filagent.ai` is verified to exist and is actively monitored by the FilAgent Governance Board to ensure prompt handling of escalated security issues.
- For urgent security issues affecting production deployments, please mark your email as **[URGENT]** in the subject line.

### Security Disclosure Policy
We follow **responsible disclosure practices**:
- We will acknowledge your report and work with you to understand and verify the issue.
- We will develop and test a fix, keeping you informed of our progress.
- We will coordinate with you on the timing of public disclosure.
- We will credit you in our security advisory (unless you prefer to remain anonymous).

### Traceability & Audit
FilAgent is designed with governance and legal traceability as core principles:

- **All vulnerability reports and communications are retained for 7 years** in accordance with FilAgent's audit and traceability policies.
- **All security fixes are logged with provenance metadata** including decision records (DR) with EdDSA signatures.
- **All security-related decisions are tracked using PROV-JSON** format for complete auditability.
- **Compliance:** Our security processes align with Québec Law 25, EU AI Act, and NIST AI RMF requirements.

### Security Features
FilAgent includes built-in security features:

- **Policy Engine:** Pre-execution validation of all actions with PII masking and RBAC enforcement
- **Sandboxed Execution:** Isolated execution environment for code and tools
- **WORM Logging:** Write-Once-Read-Many audit logs with Merkle tree integrity verification
- **Input Validation:** Comprehensive validation of all user inputs and tool parameters
- **No External Dependencies:** Designed to run entirely locally to prevent data leakage

### Out of Scope
The following are generally considered out of scope:
- Vulnerabilities in third-party dependencies (please report to the respective maintainers)
- Social engineering attacks
- Physical security issues
- Denial of service attacks against local installations

Thank you for helping us keep FilAgent secure and compliant.
