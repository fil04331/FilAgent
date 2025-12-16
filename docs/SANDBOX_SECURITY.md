# Python Sandbox Security

## Overview

The Python sandbox (`tools/python_sandbox.py`) has been completely refactored to use Docker container-based isolation instead of subprocess-based execution. This implements a Zero Trust security model where all code is considered potentially malicious.

## Security Architecture

### Multi-Layer Defense

1. **AST Validation (Pre-execution)**
   - Parses code into Abstract Syntax Tree before execution
   - Blocks dangerous imports: `os`, `sys`, `subprocess`, `socket`, `pickle`, etc.
   - Blocks dangerous functions: `eval`, `exec`, `open`, `__import__`, etc.
   - Blocks introspection: `__class__`, `__dict__`, `__builtins__`, etc.

2. **Docker Container Isolation**
   - Ephemeral containers (created and destroyed per execution)
   - Base image: `python:3.12-slim`
   - Container auto-removed after execution

3. **Resource Limits**
   - **Memory**: 512MB hard limit
   - **CPU**: 0.5 CPU (50% of one core)
   - **Timeout**: 5 seconds strict enforcement
   - **Filesystem**: 10MB tmpfs for `/tmp`

4. **User Isolation**
   - Runs as `nobody:nogroup` (UID/GID 65534:65534)
   - Non-root user prevents privilege escalation
   - No sudo or capability to change user

5. **Network Isolation**
   - `network_mode='none'` - complete network disconnection
   - No internet access, no DNS resolution
   - Cannot communicate with other containers or host

6. **Filesystem Restrictions**
   - Root filesystem: read-only
   - Code directory: read-only mount
   - Only `/tmp` writable (10MB limit)
   - No access to host filesystem

7. **Capability Restrictions**
   - All Linux capabilities dropped (`cap_drop: ALL`)
   - No new privileges allowed (`security_opt: no-new-privileges`)
   - Cannot access raw sockets, kernel modules, etc.

## Threat Model

### Threats Mitigated

| Threat | Mitigation |
|--------|-----------|
| Remote Code Execution (RCE) | Docker isolation + AST validation |
| File system access | Read-only mount + tmpfs-only writes |
| Network exfiltration | Network mode 'none' |
| Resource exhaustion (CPU) | CPU quota (0.5 core) |
| Resource exhaustion (RAM) | Memory limit (512MB) |
| Resource exhaustion (Time) | 5-second timeout |
| Privilege escalation | Non-root user + no-new-privileges |
| Container escape | Dropped capabilities + read-only FS |
| Fork bombs | Docker resource limits |

### Attack Scenarios Tested

All scenarios tested in `tests/test_sandbox_security.py`:

1. ✅ **OS Command Injection**: `os.system('rm -rf /')` → Blocked by AST
2. ✅ **Subprocess Execution**: `subprocess.run(['ls', '/'])` → Blocked by AST
3. ✅ **Code Evaluation**: `eval('malicious_code')` → Blocked by AST
4. ✅ **File Access**: `open('/etc/passwd', 'r')` → Blocked by AST
5. ✅ **Network Access**: `socket.connect()` → Blocked by AST + no network
6. ✅ **Deserialization**: `pickle.loads()` → Blocked by AST
7. ✅ **Introspection**: `().__class__.__bases__` → Blocked by AST
8. ✅ **Infinite Loop**: `while True: pass` → Killed by timeout
9. ✅ **Memory Bomb**: Large allocations → Killed by memory limit

## Usage

```python
from tools.python_sandbox import PythonSandboxTool

# Create sandbox instance
sandbox = PythonSandboxTool()

# Execute safe code
result = sandbox.execute({"code": "print('Hello World')"})
assert result.is_success()
print(result.output)  # "Hello World"

# Dangerous code is blocked
result = sandbox.execute({"code": "import os; os.system('ls')"})
assert result.status == ToolStatus.ERROR
print(result.error)  # "Import of dangerous module blocked: os"
```

## Configuration

All parameters are configurable via constructor:

```python
sandbox = PythonSandboxTool(
    docker_image="python:3.12-slim",  # Docker image to use
    dangerous_patterns=None  # Optional: custom dangerous patterns
)
```

Internal configuration (modify in class):
- `max_memory_mb`: 512 (default)
- `cpu_quota`: 50000 (0.5 CPU)
- `timeout`: 5 seconds

## Performance

- **Overhead**: ~100-200ms per execution (Docker container creation)
- **Throughput**: ~5-10 executions/second (sequential)
- **Suitable for**: Agent tool calls, user-submitted code, untrusted scripts
- **Not suitable for**: High-frequency bulk processing (use subprocess version for trusted code)

## Dependencies

- **Python Package**: `docker>=7.0.0`
- **System**: Docker daemon must be running and accessible
- **Image**: `python:3.12-slim` must be pulled (auto-pulls on first use)

```bash
# Install Python SDK
pip install docker>=7.0.0

# Pull base image
docker pull python:3.12-slim
```

## Monitoring & Observability

All executions include metadata:
```python
result.metadata = {
    "elapsed_time": 0.15,  # seconds
    "timeout": False,
    "isolation": "docker",
    "memory_limit_mb": 512,
    "exit_code": 0  # on error
}
```

## Limitations

1. **Docker Required**: Requires Docker daemon (not available in all environments)
2. **Performance**: ~100-200ms overhead per execution
3. **Image Pull**: First execution requires downloading ~150MB image
4. **No GPU**: GPU access not available in sandbox
5. **No Persistence**: Each execution is isolated (no state between runs)

## Migration from Subprocess Version

The interface remains compatible:

```python
# Old subprocess version
sandbox = PythonSandboxTool()
result = sandbox.execute({"code": "print(42)"})

# New Docker version - same interface!
sandbox = PythonSandboxTool()
result = sandbox.execute({"code": "print(42)"})
```

Changes:
- ✅ Same `execute()` interface
- ✅ Same `validate_arguments()` interface
- ✅ Same `ToolResult` return type
- ⚠️ Requires Docker SDK installed
- ⚠️ Timeout reduced from 30s to 5s (configurable)

## Future Enhancements

1. **MicroVM Support**: Integrate Firecracker or E2B for even stronger isolation
2. **Image Caching**: Pre-warmed container pool for reduced latency
3. **Custom Images**: Support for language-specific images (Node.js, Go, etc.)
4. **Network Allowlist**: Selective network access to approved domains
5. **Disk Quotas**: More granular filesystem limits

## References

- Docker SDK: https://docker-py.readthedocs.io/
- Firecracker: https://firecracker-microvm.github.io/
- E2B: https://e2b.dev/
- OWASP Secure Coding: https://owasp.org/www-project-secure-coding-practices-quick-reference-guide/

## Security Contact

For security issues or vulnerabilities, please contact: [security contact]
