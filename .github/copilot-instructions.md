---
title: "GitHub Copilot Instructions for FilAgent"
description: "Backend MCP/HTN agent with strong governance and compliance"
version: "1.1.0"
role: "Ingénieur Backend MCP & Agent System Developer"
format: "system-prompt"
language: "en/fr"
---

# GitHub Copilot Instructions for FilAgent

FilAgent is a Python 3.10+ LLM agent with hard governance, traceability, and HTN planning. Documentation is largely in French; code, comments, and docstrings stay in English.

## Quick Workflow

- Install: `pdm install --dev` (alt: `pip install -r requirements.txt` + `requirements-dev.txt`).
- Run API: `pdm run server-dev` (hot reload) or `pdm run server` (prod-like) from [runtime/server.py](runtime/server.py); OpenAI-compatible at <http://localhost:8000/docs>.
- Run MCP: `pdm run mcp` (see [mcp_server.py](mcp_server.py)).
- Tests: `pdm run test` or targeted `pdm run test-unit|test-integration|test-compliance|test-e2e|test-performance`; markers in [tests/README.md](tests/README.md).
- Format/lint/typecheck: `pdm run format && pdm run lint && pdm run typecheck`; `pdm run check` bundles them.

## Architecture Landmarks

- Runtime: [runtime/agent.py](runtime/agent.py) orchestration, [runtime/server.py](runtime/server.py) FastAPI surface, `runtime/middleware/*` singletons (`get_logger`, `get_dr_manager`, `get_provenance_tracker`), [runtime/config.py](runtime/config.py) `get_config()` singleton.
- Planning: HTN in [planner/](planner/README.md) with `HierarchicalPlanner`, `TaskExecutor`, `TaskVerifier`, state machine in [planner/state_machine.yaml](planner/state_machine.yaml).
- Governance: policy gate in [policy/engine.py](policy/engine.py), PII in [policy/pii.py](policy/pii.py), audit/provenance in [provenance/](provenance/logger.py) + WORM chain in [provenance/worm.py](provenance/worm.py), decision records in [provenance/decision.py](provenance/decision.py).
- Memory: SQLite episodic store in [memory/episodic.py](memory/episodic.py); retention logic in [memory/retention.py](memory/retention.py).
- Tools: registry in [tools/registry.py](tools/registry.py); sandboxed execution in [tools/sandbox.py](tools/sandbox.py); follow BaseTool pattern from [tools/base.py](tools/base.py).
- Config: YAML in [config/](config/); avoid hardcoding, always pull via `get_config()`.

## Required Practices (governance first)

- No secrets in code; use `.env.example` patterns. Respect RBAC/allowlists in [config/policies.yaml](config/policies.yaml) before any file or network access.
- All tool calls and risky actions must pass `policy/engine` and be logged: emit decision records (provenance), redact PII, and keep WORM integrity.
- Use middleware singletons (do not instantiate directly) to ensure shared audit/provenance state.
- Code execution must route through sandboxed tools; never run arbitrary code paths outside [tools/sandbox.py](tools/sandbox.py).
- Preserve reproducibility: include model version, seed, and temperature in model-facing changes.

## Patterns to Follow

- Keep async I/O; avoid blocking in FastAPI handlers and planners. Use semaphores/backpressure when launching concurrent tasks (see `TaskExecutor` strategies in [planner/executor.py](planner/executor.py)).
- When adding a tool: register in [tools/registry.py](tools/registry.py), validate inputs, enforce policy checks, and log provenance + decision record. Tests live next to `tests/test_tools*.py`.
- When touching planning: keep HTN graphs acyclic, honor `state_machine.yaml` limits (timeouts, retries, circuit breakers), and validate with `TaskVerifier`.
- When changing middleware or policy paths, update/consult coverage at `htmlcov/index.html` and relevant docs in [docs/COMPLIANCE_GUARDIAN.md](docs/COMPLIANCE_GUARDIAN.md).

## Testing Expectations

- Prefer pytest markers `unit`, `integration`, `compliance`, `e2e`, `performance` (see [tests/README.md](tests/README.md)).
- Reuse fixtures in [tests/conftest.py](tests/conftest.py) and generators in [tests/utils/test_data_generators.py](tests/utils/test_data_generators.py); avoid bespoke setup.

## Documentation Pointers

- High-level repo guidance in [AGENTS.md](AGENTS.md) and [CLAUDE.md](CLAUDE.md); French overview in [README.md](README.md); planner details in [planner/README.md](planner/README.md).

## When unsure

- Default to governance-safe choice: validate inputs, route through policy/middleware, log provenance, and keep operations sandboxed. Ask before skipping any of these.

```bash
# Install test dependencies if not already installed
pip install -r requirements.txt

# Run all tests (using PDM - recommended)
pdm run pytest

# Fallback: Run tests directly with pytest
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

### Security Constraints
1. **No secrets in code**: Never commit API keys, passwords, or credentials
2. **PII protection**: All personally identifiable information must be masked/redacted
3. **Sandbox isolation**: All code execution must go through the sandbox
4. **Input validation**: Validate all user inputs and tool parameters

### Governance Requirements
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
- HumanEval pass@1: >= 0.65
- MBPP: >= 0.60
- SWE-bench lite: 50% on 50 tasks
- Agentic scenarios: >= 0.75
- Decision record coverage: >= 95%
- Zero critical violations per 1000 tasks

## References

- Main README: `README.md` (French)
- Setup guide: `README_SETUP.md`
- Documentation index: `docs/INDEX.md`
- Documentation structure: `docs/DOCUMENTATION_STRUCTURE.md`
- Architecture Decision Records: `docs/ADRs/`
- Historical documentation: `docs/archive/` (includes archived phase reports and implementation summaries)

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

### Common Anti-Patterns to Avoid

**DON'T:**
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
