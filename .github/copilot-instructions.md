---
title: "GitHub Copilot Instructions for FilAgent"
description: "Expert en développement backend haute performance (MCP), systèmes massivement concurrents à faible latence"
version: "1.0.0"
role: "Ingénieur Backend MCP & Agent System Developer"
format: "system-prompt"
language: "en/fr"
---

# GitHub Copilot Instructions for FilAgent

## Project Overview

FilAgent is an LLM-based agent system with a fundamental focus on governance, legal traceability, security, and reproducibility of decisions. The architecture is designed to run locally while complying with strict regulatory standards (Québec Law 25, EU AI Act, NIST AI RMF).

This is a **Python-based project** with French documentation and English code/comments.

## Getting Started

### Prerequisites
- Python 3.10 or higher
- Git
- 8+ GB RAM (16GB recommended)

### Initial Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python -c "from memory.episodic import create_tables; create_tables()"
```

### Running the Server

```bash
# Start the API server
python runtime/server.py

# Server will be accessible at http://localhost:8000
# API documentation at http://localhost:8000/docs
```

## Build and Test Commands

### Testing

```bash
# Install test dependencies if not already installed
pip install -r requirements.txt

# Run all tests
python -m pytest

# Run specific test categories
python -m pytest -m unit        # Unit tests only
python -m pytest -m integration # Integration tests only
python -m pytest -m memory      # Memory-related tests
python -m pytest -m tools       # Tool-related tests

# Run with coverage
python -m pytest --cov=. --cov-report=html
```

### Linting and Code Quality

```bash
# Format code with Black
python -m black .

# Check code style with flake8
python -m flake8 .

# Type checking with mypy
python -m mypy .
```

## Project Structure

```
FilAgent/
├── config/          # YAML configuration files
│   ├── agent.yaml   # Agent parameters (temperature, max_tokens, timeouts)
│   ├── policies.yaml # Usage rules, RBAC, guardrails
│   ├── retention.yaml # Data retention policies
│   ├── provenance.yaml # Traceability configuration
│   └── eval_targets.yaml # Evaluation thresholds
├── runtime/         # Server and agent runtime
│   ├── server.py    # FastAPI application
│   ├── agent.py     # Core agent logic
│   └── config.py    # Config loader
├── memory/          # Memory management
│   ├── episodic.py  # SQLite-based conversation storage
│   └── retention.py # Retention policy enforcement
├── tools/           # Tool implementations
│   ├── registry.py  # Tool registry
│   ├── sandbox.py   # Python code sandbox
│   └── file_ops.py  # File operations
├── policy/          # Policy enforcement
│   ├── engine.py    # Policy engine
│   └── pii.py       # PII detection/masking
├── provenance/      # Traceability and audit
│   ├── logger.py    # JSONL logging
│   ├── decision.py  # Decision records
│   ├── tracker.py   # PROV-JSON tracking
│   └── worm.py      # WORM (Write-Once-Read-Many) logs
├── eval/            # Evaluation and benchmarking
│   ├── base.py      # Generic evaluation harness
│   └── reports/     # Evaluation reports
├── models/          # Model configurations
│   └── weights/     # Model files (GGUF format)
├── logs/            # Log storage
├── audit/           # Audit logs (7-year retention)
└── tests/           # Test suite
```

## Coding Standards and Conventions

### Code Style
- **Python version**: 3.10+
- **Code formatting**: Use Black (line length 88)
- **Type hints**: Use type hints where appropriate
- **Docstrings and Comments**: Use English for inline code comments and docstrings (note: some existing documentation files are in French)
- **Async patterns**: Use async/await for I/O operations (FastAPI, SQLite)

### Configuration
- All configurations are in YAML files under `config/`
- Use `runtime/config.py` singleton `get_config()` to access configuration
- Never hardcode values that should be configurable

### Testing
- Use pytest for all tests
- Mark tests appropriately: `@pytest.mark.unit`, `@pytest.mark.integration`, etc.
- Test files must start with `test_`
- Keep tests isolated and independent

## Critical Security and Governance Requirements

### ⚠️ Security Constraints
1. **No secrets in code**: Never commit API keys, passwords, or credentials
2. **PII protection**: All personally identifiable information must be masked/redacted
3. **Sandbox isolation**: All code execution must go through the sandbox
4. **Input validation**: Validate all user inputs and tool parameters

### 🔒 Governance Requirements
1. **Traceability**: Every action must be logged with provenance metadata
2. **Decision records**: Generate signed decision records for critical actions
3. **WORM logging**: All audit logs are append-only and cryptographically verified
4. **Reproducibility**: Include version, seed, temperature in all model calls

### Data Retention
- Conversations: 30 days (configurable in `retention.yaml`)
- Decision records: 365 days
- Audit logs: 7 years (legal requirement)
- Events: 90 days

### Policy Engine
- All tool calls must pass through `policy/engine.py` for authorization
- Check allowlists for file paths: `working_set/`, `temp/`, `memory/working_set/`
- Respect RBAC rules defined in `config/policies.yaml`

## Working with Specific Components

### Adding New Tools
1. Create tool implementation in `tools/`
2. Register in `tools/registry.py` using `register()`
3. Include tool description for LLM prompting
4. Add security validation for inputs
5. Log all tool executions with provenance

### Modifying the Agent
- Core agent logic is in `runtime/agent.py`
- Agent uses a reasoning loop (max 10 iterations)
- Parse `<tool_call>` tags from LLM output
- Store all messages in episodic memory
- Generate decision records for tool usage

### Memory Management
- Short-term: SQLite database (`memory/episodic.py`)
- Long-term: FAISS/Parquet for semantic search (future Phase 3)
- Use `RetentionManager` for cleanup according to policies

### API Development
- FastAPI server in `runtime/server.py`
- OpenAI-compatible response format
- Include conversation_id for memory tracking
- Return usage metrics (tokens)

## Common Tasks

### Adding a New Configuration Parameter
1. Update the appropriate YAML file in `config/`
2. Update the Pydantic model in `runtime/config.py`
3. Document the parameter's purpose and default value
4. Update tests if behavior changes

### Implementing a New Evaluation Benchmark
1. Create benchmark loader in `eval/`
2. Define acceptance criteria in `config/eval_targets.yaml`
3. Use the generic harness from `eval/base.py`
4. Save reports to `eval/reports/`

### Troubleshooting

#### Server won't start
- Check that dependencies are installed: `pip install -r requirements.txt`
- Verify database is initialized (see "Initial Setup" section above)
- Check logs in `logs/` directory

#### Tests failing
- Ensure virtual environment is activated
- Install test dependencies: `pip install -r requirements.txt`
- Check for missing test markers in `pytest.ini`

## Performance Targets

Based on `config/eval_targets.yaml`:
- HumanEval pass@1: ≥ 0.65
- MBPP: ≥ 0.60
- SWE-bench lite: 50% on 50 tasks
- Agentic scenarios: ≥ 0.75
- Decision record coverage: ≥ 95%
- Zero critical violations per 1000 tasks

## References

- Main README: `README.md` (French)
- Setup guide: `README_SETUP.md`
- Agent documentation: `AGENT.md`
- Project phases: `STATUS_PHASE*.md` files

## Backend MCP Development (High-Performance Concurrent Systems)

### When to Apply MCP Backend Expertise

Apply high-performance backend patterns when:
- **Throughput**: > 500 requests/second required
- **Latency**: < 10ms P95 response time required (sub-10ms for most requests)
- **Concurrency**: > 1000 simultaneous connections
- **Use Cases**: WebSockets, gRPC, real-time systems, MCP servers

### MCP (Model Context Protocol) Server Development

**Core Principles:**
1. **Protocol Compliance**: Follow MCP specification for tool registration, request/response format
2. **Async by Default**: All I/O operations must be non-blocking (async/await)
3. **Connection Pooling**: Reuse connections, implement proper lifecycle management
4. **Backpressure Handling**: Implement flow control to prevent memory overflow
5. **Graceful Degradation**: System must remain operational under high load

**MCP Server Architecture:**
```python
# Conceptual architecture pattern based on mcp_server.py
# This is a design template - see mcp_server.py for full working implementation
# Method bodies use 'pass' as this shows structure, not complete code
class FilAgentMCPServer:
    async def initialize(self) -> Dict[str, Any]:
        """Initialize server components with dependency injection"""
        self.agent = get_agent()
        self.config = get_config()
        self.tool_registry = get_tool_registry()
        self._register_base_tools()
        return {
            "name": "filagent",
            "version": "1.0.0",
            "protocolVersion": "1.0.0",
            "capabilities": {"tools": {}, "prompts": {}}
        }
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP request with validation and timeout
        
        Args:
            request: MCP request dictionary with method, params, and id
            
        Returns:
            MCP response dictionary with result or error
        """
        # 1. Validate request schema with Pydantic
        # 2. Apply policy engine checks (RBAC, PII masking)
        # 3. Execute tool with asyncio.wait_for(timeout=30s)
        # 4. Log to provenance tracker with decision record
        # 5. Return structured response with usage metrics
        pass
    
    async def shutdown(self):
        """Graceful shutdown with connection draining"""
        # 1. Stop accepting new requests (set shutdown flag)
        # 2. Wait for pending requests with timeout
        # 3. Close database connection pools
        # 4. Flush logs and metrics to disk
        pass
```

### Performance Optimization Techniques

**1. Concurrency Patterns:**
- Use `asyncio.gather()` for parallel operations
- Implement semaphores for resource limiting: `asyncio.Semaphore(max_concurrent)`
- Use connection pools (asyncpg, aioredis) instead of per-request connections
- Prefer `asyncio.create_task()` over `await` for fire-and-forget operations

**2. Memory Management:**
- Stream large responses instead of buffering: `async for chunk in stream`
- Implement object pooling for frequently created objects
- Use `__slots__` in Python classes to reduce memory overhead
- Monitor memory with prometheus metrics

**3. Database Optimization:**
- Use prepared statements and query caching
- Implement read replicas for read-heavy workloads
- Use database connection pooling (asyncpg pool size: 10-50)
- Add appropriate indexes before deploying

**4. Caching Strategy:**
- L1: In-memory LRU cache (functools.lru_cache, cachetools)
- L2: Redis with TTL for distributed cache
- Cache invalidation: Time-based or event-driven
- Cache warming for predictable patterns

### Language-Specific Guidance

**Python (Current Backend):**
- FastAPI for HTTP APIs with async support
- asyncio for concurrency, avoid threading unless CPU-bound
- uvloop for 2-4x performance boost: `uvloop.install()`
- Pydantic V2 for validation (10x faster than V1)
- Use `asyncpg` over `psycopg2` for PostgreSQL

**Go (Future Performance-Critical Paths):**
- Goroutines for concurrency with channel-based communication
- Context for cancellation and timeout propagation
- Sync.Pool for object reuse
- pprof for profiling CPU and memory

**Rust (Future Ultra-Low-Latency):**
- Tokio for async runtime
- Zero-copy serialization with serde
- Arc<Mutex<T>> for shared state
- Avoid allocations in hot paths

### Monitoring & Observability

**Required Metrics:**
```python
# Prometheus metrics for MCP server
# Install: pip install prometheus-client
# Note: In production, wrap metric usage in conditionals or use a metrics facade
import logging

try:
    from prometheus_client import Counter, Histogram, Gauge
    
    mcp_requests_total = Counter('mcp_requests_total', 'Total MCP requests', ['method', 'status'])
    mcp_request_duration = Histogram('mcp_request_duration_seconds', 'MCP request duration', ['method'])
    mcp_active_connections = Gauge('mcp_active_connections', 'Active MCP connections')
    mcp_errors_total = Counter('mcp_errors_total', 'Total MCP errors', ['type'])
    METRICS_ENABLED = True
except ImportError:
    # Metrics disabled if prometheus-client not installed
    logging.warning("prometheus-client not available, metrics disabled")
    METRICS_ENABLED = False
```

**Performance Targets:**
- P50 latency: < 5ms
- P95 latency: < 10ms
- P99 latency: < 50ms
- Error rate: < 0.1%
- Throughput: > 500 req/s per instance

### Load Testing & Benchmarking

**Before deploying performance-critical changes:**
```bash
# Load test with wrk
wrk -t12 -c400 -d30s http://localhost:8000/endpoint

# Profile with py-spy
py-spy record -o profile.svg -- python runtime/server.py

# Memory profiling
python -m memory_profiler runtime/server.py
```

### Common Anti-Patterns to Avoid

❌ **DON'T:**
- Synchronous I/O in async functions (blocking operations)
- Creating new connections per request
- Unbounded queues or buffers
- Missing timeouts on external calls
- Ignoring backpressure signals
- Using global locks for frequently accessed data

✅ **DO:**
- Use connection pooling and keep-alive
- Implement circuit breakers for external services
- Set timeouts on all I/O operations (default: 30s)
- Use semaphores to limit concurrency
- Profile before optimizing (measure, don't guess)
- Load test before production deployment

### MCP Server Checklist

Before merging MCP server changes:
- [ ] All handlers are async with proper error handling
- [ ] Timeouts configured on all external calls
- [ ] Connection pooling implemented and tested
- [ ] Prometheus metrics exported
- [ ] Load tested at 2x expected traffic
- [ ] Memory profiling shows no leaks
- [ ] Graceful shutdown drains connections
- [ ] Health check endpoint responds < 5ms
- [ ] Documentation updated with performance characteristics

## Notes for Copilot

- **Language**: Code, inline comments, and docstrings in English; high-level documentation files in French
- **Minimal changes**: Make surgical, targeted changes only
- **Test coverage**: Maintain or improve existing test coverage
- **Governance first**: Security and compliance are top priorities
- **Local-first**: This system is designed to run entirely locally
- **Regulatory compliance**: Respect Québec Law 25 and EU AI Act requirements
- **Performance**: For high-throughput/low-latency requirements (>500 req/s, <10ms), apply MCP Backend guidance above
