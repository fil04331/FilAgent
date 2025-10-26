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

## Notes for Copilot

- **Language**: Code, inline comments, and docstrings in English; high-level documentation files in French
- **Minimal changes**: Make surgical, targeted changes only
- **Test coverage**: Maintain or improve existing test coverage
- **Governance first**: Security and compliance are top priorities
- **Local-first**: This system is designed to run entirely locally
- **Regulatory compliance**: Respect Québec Law 25 and EU AI Act requirements
