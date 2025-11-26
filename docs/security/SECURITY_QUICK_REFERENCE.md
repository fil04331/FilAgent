# FilAgent Security Quick Reference
## Developer Cheat Sheet

**Last Updated**: 2025-11-23
**Critical Status**: 🔴 NOT PRODUCTION READY

---

## THE THREE CRITICAL FIXES

### 1. LOG INJECTION (Lines: 1654, 1717, 1728, 1769, 2487, 2509, 2552, 2563)

**What's Wrong**:
```python
# ❌ VULNERABLE
logger.info(f"User input: {user_input}")  # Newlines create forged log entries
```

**How to Fix**:
```python
# ✅ SECURE - Option A: Parameterized logging
logger.info("User input: %s", user_input)

# ✅ SECURE - Option B: Use sanitized wrapper
from runtime.middleware.sanitized_logging import LogSanitizer
safe_input = LogSanitizer.sanitize(user_input)
logger.info(f"User input: {safe_input}")
```

**Why**: Attackers inject `\n[FAKE] 2025-11-23 INFO - unauthorized_action` to forge audit entries

**Impact**: Violates Loi 25 audit trail integrity

**File to Modify**: `/Users/felixlefebvre/FilAgent/gradio_app_production.py`

---

### 2. PATH TRAVERSAL (7 instances)

**What's Wrong**:
```python
# ❌ VULNERABLE
file_path = os.path.join(upload_dir, user_filename)
with open(file_path, 'rb') as f:
    content = f.read()
```

**How to Fix**:
```python
# ✅ SECURE
from runtime.middleware.path_validator import PathValidator

file_path = PathValidator.validate_path(upload_dir, user_filename)
with open(file_path, 'rb') as f:
    content = f.read()
```

**Why**: Attackers use `../../../etc/passwd` to access restricted files

**Impact**: Data breach, compliance violation

**Files to Modify**:
- `/Users/felixlefebvre/FilAgent/gradio_app_production.py` (document analyzer)
- Any file operation accepting user paths

---

### 3. PYTHON-JOSE VULNERABILITY (CVE-2024-23342)

**What's Wrong**:
```bash
# ❌ VULNERABLE - Indirect ecdsa dependency
pip list | grep python-jose  # Pulls in python-ecdsa
```

**How to Fix**:
```bash
cd /Users/felixlefebvre/FilAgent
pdm remove python-jose
pdm add "pyjwt[crypto]>=2.10.1"
```

**Why**: Minerva timing attack on ECDSA P-256 curve

**Impact**: Potential signature bypass (though Ed25519 used for critical ops)

---

## IMMEDIATE CHECKLIST (This Week)

- [ ] Day 1: Read COMPREHENSIVE_SECURITY_ANALYSIS.md (executive summary)
- [ ] Day 2-3: Implement log injection fixes (8 hours)
- [ ] Day 3-4: Implement path traversal fixes (4 hours)
- [ ] Day 4-5: Update dependencies, migrate to PyJWT (6 hours)
- [ ] Day 5: Run tests, verify no regressions

**Total Time**: 18 hours
**Estimated Completion**: Friday EOD (3 business days)

---

## CODE TEMPLATES

### Template 1: Secure Logging

```python
from runtime.middleware.sanitized_logging import LogSanitizer, get_sanitized_logger

# Get sanitized logger
logger = get_sanitized_logger(__name__)

# Safe way to log user input
user_input = request.form.get("query")
logger.info("User query: %s", user_input)  # Parameterized - safe

# OR with explicit sanitization
safe_input = LogSanitizer.sanitize(user_input, "query")
logger.info(f"User query: {safe_input}")
```

### Template 2: Secure File Operations

```python
from runtime.middleware.path_validator import PathValidator

# Validate path before opening
base_dir = "/var/uploads"
user_filename = request.form.get("file")

try:
    safe_path = PathValidator.validate_path(base_dir, user_filename)
    with open(safe_path, 'rb') as f:
        content = f.read()
except ValueError as e:
    logger.error("Path validation failed: %s", e)
    raise HTTPException(status_code=400, detail="Invalid file path")
```

### Template 3: Secure Filename Validation

```python
from runtime.middleware.path_validator import PathValidator

user_filename = request.form.get("filename")

if not PathValidator.is_safe_filename(user_filename):
    raise HTTPException(status_code=400, detail="Invalid filename")

# Safe to use now
new_path = os.path.join(safe_dir, user_filename)
```

---

## TEST EXAMPLES

### Testing Log Injection Prevention

```bash
# Run log injection tests
pytest tests/test_security_log_injection.py -v

# Manual test
python -c "
from runtime.middleware.sanitized_logging import LogSanitizer
payload = 'query\n[CRITICAL] INJECTED'
sanitized = LogSanitizer.sanitize(payload)
assert '\n' not in sanitized
print('✓ Log injection blocked')
"
```

### Testing Path Traversal Prevention

```bash
# Run path traversal tests
pytest tests/test_security_path_traversal.py -v

# Manual test
python -c "
from runtime.middleware.path_validator import PathValidator
import tempfile
with tempfile.TemporaryDirectory() as tmpdir:
    try:
        PathValidator.validate_path(tmpdir, '../../../etc/passwd')
        print('✗ Path traversal NOT blocked')
    except ValueError:
        print('✓ Path traversal blocked')
"
```

---

## SECURITY HEADERS TO ADD

**File**: `runtime/server.py`

```python
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)

    # Prevent MIME type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"

    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"

    # Enable XSS protection
    response.headers["X-XSS-Protection"] = "1; mode=block"

    # Enforce HTTPS
    response.headers["Strict-Transport-Security"] = "max-age=31536000"

    # Content Security Policy
    response.headers["Content-Security-Policy"] = "default-src 'self'"

    return response
```

---

## COMMON MISTAKES TO AVOID

### ❌ DON'T DO THIS

```python
# 1. F-string with user input in logs
logger.info(f"User said: {user_input}")  # Log injection risk

# 2. Direct file path concatenation
file_path = os.path.join(upload_dir, user_filename)  # Path traversal risk

# 3. Trusting user input for file operations
open(request.form.get("filepath"))  # Obvious vulnerability

# 4. Logging secrets
logger.info(f"API key: {os.getenv('API_KEY')}")  # Credential leak

# 5. HTML injection in logs
logger.info(f"Result: {html_response.text}")  # XSS risk
```

### ✅ DO THIS INSTEAD

```python
# 1. Parameterized logging
logger.info("User said: %s", user_input)

# 2. Validated file paths
safe_path = PathValidator.validate_path(upload_dir, user_filename)

# 3. Never trust user input directly
validated_path = PathValidator.validate_path(upload_dir, user_input)

# 4. Never log secrets
logger.info("API key configured (value redacted)")

# 5. Sanitize before logging
safe_html = LogSanitizer.sanitize(html_response.text)
logger.info("Result: %s", safe_html)
```

---

## COMPLIANCE CHECKLIST

### Before Each Commit

- [ ] No `logger.info(f"... {user_input} ...")` patterns
- [ ] All file operations use `PathValidator.validate_path()`
- [ ] No hardcoded credentials or secrets
- [ ] Tests passing: `pdm run test`
- [ ] Type hints complete: `pdm run typecheck`
- [ ] No new dependencies without CVE check

### Before Deploying

- [ ] Security tests passing: `pytest -m security`
- [ ] Compliance tests passing: `pytest -m compliance`
- [ ] No CRITICAL/HIGH CVEs: `pdm run security`
- [ ] Code review approved
- [ ] Decision Record created

---

## WHERE TO FIND THINGS

| What | Where |
|------|-------|
| **Architecture docs** | COMPREHENSIVE_SECURITY_ANALYSIS.md |
| **Implementation guide** | SECURITY_HARDENING_IMPLEMENTATION.md |
| **Monitoring setup** | SECURITY_MONITORING_ALERTING.md |
| **Executive summary** | SECURITY_EXECUTIVE_SUMMARY.md |
| **ECDSA vulnerability** | SECURITY_ADVISORY_ECDSA.md |
| **Investigation report** | SECURITY_INVESTIGATION_REPORT.md |
| **Log sanitization code** | runtime/middleware/sanitized_logging.py (create) |
| **Path validation code** | runtime/middleware/path_validator.py (create) |
| **Log injection tests** | tests/test_security_log_injection.py (create) |
| **Path traversal tests** | tests/test_security_path_traversal.py (create) |

---

## QUICK LINKS

**Critical Documents** (Read FIRST):
1. SECURITY_EXECUTIVE_SUMMARY.md (11 KB, 10 min read)
2. COMPREHENSIVE_SECURITY_ANALYSIS.md (33 KB, 45 min read)

**Implementation Documents** (For coding):
3. SECURITY_HARDENING_IMPLEMENTATION.md (36 KB, hands-on guide)
4. This quick reference card

**Operations Documents** (For DevOps):
5. SECURITY_MONITORING_ALERTING.md (19 KB, setup guide)

---

## CONTACT & ESCALATION

**Questions?**
- First: Check COMPREHENSIVE_SECURITY_ANALYSIS.md section on your question
- Then: Review SECURITY_HARDENING_IMPLEMENTATION.md code templates
- Finally: Ask DevSecOps Security Guardian

**Blocking Issue?**
- Document the problem with example code
- Include error message and traceback
- Reference the security doc section
- Escalate to security team lead

**Production Incident?**
- STOP. Do not deploy.
- Page on-call security engineer
- Follow incident response procedure (see comprehensive analysis)
- Document everything for audit trail

---

## TIMELINE

```
Week 1 (THIS WEEK):
  Mon-Tue: Log injection fixes (8h)
  Wed:     Path traversal fixes (4h)
  Thu:     Dependency updates (6h)
  Fri:     Testing & verification (4h)
  ✓ CRITICAL FIXES COMPLETE

Week 2:
  Security testing & hardening (22h)
  ✓ HARDENING COMPLETE

Week 3:
  Compliance certification (22h)
  ✓ PRODUCTION READY

Total: 62 hours = 3 weeks at 20h/week
```

---

## SUCCESS CRITERIA

### Week 1 Completion (CRITICAL FIXES)
```bash
# Run this command - ALL should pass
pytest tests/test_security_log_injection.py \
       tests/test_security_path_traversal.py -v

# Security scan - should show IMPROVEMENTS
pdm run security | grep CRITICAL  # Should be near 0
pdm run bandit   | grep HIGH      # Should be near 0
```

### Week 3 Completion (PRODUCTION READY)
```bash
# Run full security audit
pytest -m compliance -v  # All pass
pytest -m security -v    # All pass
pdm run security         # No CRITICAL vulns
pdm run bandit          # No HIGH issues
```

---

**Last Updated**: 2025-11-23
**Status**: 🔴 Action Required
**Target Completion**: 2025-12-06 (3 weeks)

---
