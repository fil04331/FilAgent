# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Version**: 2.3.0
**Last Updated**: 2025-11-18
**Project**: FilAgent - LLM Agent with Governance & Traceability

---

## Project Overview

FilAgent is an LLM-based agent system with **fundamental emphasis on governance, legal traceability, security, and reproducibility**. The architecture is designed to run locally while meeting strict compliance standards (Quebec's Loi 25, EU AI Act, NIST AI RMF).

**Core Principles:**
1. **Governance First** - Compliance and traceability built-in from design
2. **Safety by Design** - Secure defaults, fail-safe mechanisms
3. **Reproducibility** - Deterministic outputs with version control
4. **Local-First** - Privacy-preserving local execution
5. **Modular Architecture** - Separation of concerns, testable components

**Technology Stack:**
- Python 3.10-3.14, FastAPI 0.121+, Uvicorn 0.38+
- LLM: llama.cpp (local) or Perplexity API (cloud)
- Database: SQLite (episodic), FAISS (semantic)
- Testing: pytest with markers (unit, integration, compliance, e2e, htn, performance)
- Package Management: PDM (preferred) or pip with requirements.txt
- Monitoring: Prometheus, Grafana
- Document Processing: PyPDF2, python-docx, openpyxl

---

## Licensing

**Current License**: Dual Proprietary License (see LICENSE file)

- **Personal/Educational**: Free use, modification allowed for personal/research/educational purposes
- **Commercial**: Requires commercial license and royalties

**Dependency Policy** (from .github/workflows/dependencies.yml):
- Allowed: MIT, Apache-2.0, BSD-3-Clause, BSD-2-Clause, ISC, Python-2.0
- Denied: GPL-3.0, AGPL-3.0

---

## Essential Commands

### Package Management (PDM)

```bash
# Install all dependencies
pdm install

# Install with optional dependencies
pdm install -G ml        # ML/LLM dependencies (llama-cpp-python, faiss, sentence-transformers)
pdm install -G dev       # Development tools (pytest, black, flake8, mypy)
pdm install -G benchmark # Benchmarking (humaneval, mbpp)
pdm install -G gpu       # GPU support (faiss-gpu)
pdm install -G ui        # UI dependencies (gradio)

# Sync dependencies (ensures exact versions from pdm.lock)
pdm sync

# Update dependencies
pdm update

# Check outdated packages
pdm list --outdated

# Alternative: Using pip (if PDM unavailable)
pip install -r requirements.txt  # Core dependencies only
```

### Running the Server

```bash
# Production mode
pdm run server
# OR: python runtime/server.py

# Development mode (auto-reload)
pdm run server-dev
# OR: uvicorn runtime.server:app --reload

# MCP server (Model Context Protocol)
pdm run mcp
# OR: python mcp_server.py

# Server accessible at http://localhost:8000
# API docs at http://localhost:8000/docs
```

### Testing

```bash
# Run all tests
pdm run test
# OR: pytest

# Run with coverage
pdm run test-cov
# OR: pytest --cov=. --cov-branch --cov-report=html --cov-report=term
# Coverage report will be in htmlcov/index.html

# Run specific test categories
pdm run test-unit           # Unit tests only
pdm run test-integration    # Integration tests
pdm run test-compliance     # Compliance tests
pdm run test-e2e           # End-to-end tests
pdm run test-performance   # Performance tests

# Run specific test file
pytest tests/test_agent.py
pytest tests/test_planner/test_executor.py

# Run with specific markers
pytest -m "unit and not slow"
pytest -m htn  # HTN planning tests
pytest -m resilience  # Resilience and fallback tests
pytest -m fixtures  # Fixture validation tests

# Skip tests requiring optional dependencies
pytest -m "not requires_llama_cpp"  # Skip tests needing llama-cpp-python
```

### Code Quality

```bash
# Format code (Black - 100 char line length)
pdm run format
# OR: black .

# Lint code (flake8)
pdm run lint
# OR: flake8 .

# Type check (mypy)
pdm run typecheck
# OR: mypy .

# Run all checks (format + lint + typecheck)
pdm run check

# Security scanning
pdm run security  # pip-audit (dependency vulnerabilities)
pdm run bandit    # Bandit security scan (code patterns)

# Sort imports (isort with Black profile)
isort .
```

### Documentation

```bash
# Serve documentation locally
pdm run docs

# Build documentation
pdm run docs-build
```

---

## Architecture Overview

### Core Components

```
runtime/
├── agent.py            # Main Agent class with HTN integration
├── server.py           # FastAPI server (OpenAI-compatible API)
├── config.py           # Configuration singleton (get_config())
├── model_interface.py  # LLM abstraction (llama.cpp + Perplexity)
└── middleware/         # Compliance middlewares (singleton pattern)
    ├── logging.py      # Structured JSONL logging (OTel-compatible)
    ├── audittrail.py   # Decision Records with EdDSA signatures
    ├── provenance.py   # W3C PROV-JSON tracking
    ├── worm.py         # Write-Once-Read-Many logging
    ├── redaction.py    # PII masking
    ├── constraints.py  # Output validation
    └── rbac.py         # Role-based access control
```

### HTN Planning System

```
planner/
├── planner.py              # HierarchicalPlanner (task decomposition)
├── task_graph.py           # DAG (Directed Acyclic Graph) management
├── executor.py             # TaskExecutor (parallel/sequential/adaptive)
├── verifier.py             # TaskVerifier (result validation)
├── compliance_guardian.py  # Compliance integration
├── metrics.py              # HTN performance metrics
├── plan_cache.py           # Plan caching for performance
└── work_stealing.py        # Work-stealing scheduler
```

**HTN Activation Logic** (runtime/agent.py):
- Triggered by multi-step queries (keywords: "puis", "ensuite", "après")
- Or queries with 2+ action verbs ("lis", "analyse", "génère", "crée")
- Execution flow: Plan → Execute → Verify → Format (or fallback to simple loop)
- Can be controlled via `config/agent.yaml` → `htn_planning.enabled`

**Key HTN Classes:**
- `HierarchicalPlanner`: Decomposes complex queries into task graphs
- `TaskExecutor`: Orchestrates parallel/sequential execution
- `TaskVerifier`: Validates task results against expected outcomes
- `ExecutionStrategy`: SEQUENTIAL, PARALLEL, or ADAPTIVE execution modes

### Model Interface

Supports two backends (transparent to user):

**1. Perplexity API (Cloud)** - Current default
```python
model = init_model(
    backend="perplexity",
    model_path="llama-3.1-sonar-large-128k-online",
    config={}  # Uses PERPLEXITY_API_KEY from .env
)
```

**2. llama.cpp (Local)**
```python
model = init_model(
    backend="llama.cpp",
    model_path="models/weights/base.gguf",
    config={"context_size": 4096, "n_gpu_layers": 35}
)
```

Both backends provide the same interface and compliance guarantees.

### Sélection de Modèles Perplexity

FilAgent supporte 5 modèles Perplexity avec sélection dynamique selon la difficulté:

**Modèles disponibles**:
- **sonar-small-128k-online**: Rapide (<300ms), questions simples, coût $
- **sonar-large-128k-online**: Équilibré (<500ms), recommandé par défaut, coût $$
- **sonar-huge-128k-online**: Maximum qualité (<1s), raisonnement complexe, coût $$$
- **8b-instruct**: Économique (<200ms), sans recherche web, coût $
- **70b-instruct**: Puissant (<800ms), sans recherche web, coût $$

**Outils de sélection**:
- **Interface interactive**: `python gradio_app_model_selector.py` (port 7861)
- **Benchmark complet**: `scripts/benchmark_perplexity_models.py`
- **Démo rapide**: `scripts/demo_model_comparison.py`

**Recommandations par difficulté**:
- **Faible** (FAQ, calculs): sonar-small ou 8b-instruct
- **Moyen** (analyse): sonar-large (défaut)
- **Élevé** (juridique, décisions): sonar-huge ou 70b-instruct

Voir `docs/GUIDE_SELECTION_MODELES_PERPLEXITY.md` pour documentation complète.

### Tool System

```python
from tools.base import BaseTool, ToolResult, ToolStatus

class MyTool(BaseTool):
    def __init__(self):
        super().__init__(name="my_tool", description="...")

    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        # 1. Validate
        is_valid, error = self.validate_arguments(arguments)
        if not is_valid:
            return ToolResult(status=ToolStatus.ERROR, error=error)

        # 2. Execute with error handling
        try:
            result = self._safe_execute(arguments)
            return ToolResult(status=ToolStatus.SUCCESS, output=result)
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    def validate_arguments(self, arguments: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        # Implement validation logic
        return True, None

    def _get_parameters_schema(self) -> Dict[str, Any]:
        # Return JSON schema for parameters
        return {"type": "object", "properties": {...}}
```

**Tool Registry**: Auto-registration via `tools/registry.py::get_registry()`

**Available Tools:**
- `calculator`: Mathematical expressions
- `file_reader`: Read files with encoding support
- `python_sandbox`: Execute Python code in isolated environment
- `document_analyzer_pme`: **Comprehensive document analysis for Quebec SMEs**
  - **Supported formats**: PDF, DOCX, XLSX (50 MB max)
  - **Analysis types**: Invoice, extract, financial, contract, report
  - **Features**:
    - Real-time document preview (PDF, Excel, Word)
    - Multi-format export (JSON with EdDSA signature, CSV UTF-8, Excel)
    - "Download All" ZIP package generator
    - Comprehensive error handling (10+ validation checks)
    - PII redaction in all outputs (Loi 25/PIPEDA compliant)
    - Decision Records for all analyses
    - Quebec tax calculations (TPS 5%, TVQ 9.975%)
  - **Validation**: Extension, size, corruption, permissions, disk space
  - **Security**: Timeout protection (30s), cleanup guarantees, no info leaks
  - **Testing**: 21 unit tests + 18 compliance tests (100% regulatory compliance)
  - **Interface**: Available in Gradio app (port 7860) and Agent tool registry

### Memory System

- **Episodic** (SQLite): `memory/episodic.py` - Conversation history
- **Semantic** (FAISS): `memory/semantic/` - Embedding-based retrieval
- **Retention**: Managed by `config/retention.yaml`

---

## Coding Conventions

### Type Hints (MANDATORY)

```python
# ✅ GOOD
def chat(self, message: str, conversation_id: str,
         task_id: Optional[str] = None) -> Dict[str, Any]:
    ...

# ❌ BAD
def chat(self, message, conversation_id, task_id=None):
    ...
```

### Docstrings & Comments

```python
def track_generation(self, conversation_id: str, input_message: str) -> str:
    """
    Tracer une génération complète avec graphe PROV-JSON

    Crée des entités, activités et relations selon standard W3C.
    Sauvegarde dans logs/traces/otlp/

    Args:
        conversation_id: Identifiant unique de la conversation
        input_message: Message utilisateur original

    Returns:
        str: Identifiant du graphe PROV créé

    Raises:
        ValueError: Si conversation_id est invalide
    """
    # Calculate hash for integrity check (English comments)
    prompt_hash = hashlib.sha256(input_message.encode()).hexdigest()
```

**Convention**: Docstrings in French, inline comments in English.

### Naming & Error Handling

```python
# Variables & functions: snake_case
conversation_id = "conv-123"

# Classes: PascalCase
class AgentConfig: ...

# Constants: UPPER_SNAKE_CASE
MAX_ITERATIONS = 10

# Middleware pattern: Graceful fallback with singleton
try:
    self.logger = get_logger()  # Singleton pattern
except Exception as e:
    print(f"⚠ Failed to initialize logger: {e}")
    self.logger = None

# Usage with null-safety
if self.logger:
    self.logger.log_event(...)
```

### Middleware Singleton Pattern

**IMPORTANT**: All middlewares follow a singleton pattern for consistency:

```python
# In runtime/middleware/my_middleware.py
_instance: Optional[MyMiddleware] = None

def get_my_middleware() -> MyMiddleware:
    """Get singleton instance of MyMiddleware"""
    global _instance
    if _instance is None:
        _instance = MyMiddleware()
    return _instance
```

**Why Singletons:**
- Ensures single source of truth for configuration
- Enables middleware mocking in tests
- Allows runtime patching for agent refresh
- Prevents duplicate resource initialization (files, connections)

**Testing Pattern:**
```python
# Tests can patch the singleton
from runtime.middleware import logging as logging_mw

def test_with_mock_logger(monkeypatch):
    mock_logger = MockLogger()
    monkeypatch.setattr(logging_mw, '_instance', mock_logger)
    # Test code using mocked logger
```

### Logging Standards

```python
# ✅ GOOD - Clear logs with emojis
print("✓ Model initialized")
print("⚠ Warning: Using CPU, generation will be slow")
print("❌ Error: Failed to load config")

# ❌ BAD - Cryptic
print("Model OK")
```

---

## Configuration Management

**Main Config**: `config/agent.yaml`

```yaml
agent:
  name: "FilAgent-PME-Quebec"
  language: "fr-CA"

model:
  backend: "perplexity"  # or "llama.cpp"
  path: "sonar"

generation:
  temperature: 0.7
  max_tokens: 2048
  seed: 42  # Reproducibility

htn_planning:
  enabled: true

compliance:
  loi25:
    enabled: true
    pii_redaction: true
    decision_records: true
```

**Loading Config**:

```python
from runtime.config import get_config

config = get_config()  # Singleton
if config.htn_planning.enabled:
    # HTN is enabled
```

**Other Configs**:
- `config/policies.yaml` - RBAC, guardrails
- `config/retention.yaml` - Data retention policies
- `config/compliance_rules.yaml` - Compliance validation
- `config/eval_targets.yaml` - Benchmark thresholds

---

## Compliance & Governance

### Decision Records (DR)

**REQUIRED** for all significant decisions:

```python
from runtime.middleware.audittrail import get_dr_manager

dr_manager = get_dr_manager()
dr = dr_manager.create_dr(
    actor="agent.core",
    task_id="task-123",
    decision="execute_python",
    tools_used=["python_sandbox"],
    reasoning="User requested data analysis"
)
```

Generates `logs/decisions/DR-*.json` with EdDSA signature.

### Provenance Tracking

W3C PROV-JSON for all artifacts:

```python
from runtime.middleware.provenance import get_tracker

tracker = get_tracker()
trace_id = tracker.track_generation(
    conversation_id="conv-123",
    input_message="Analyze data.csv"
)
```

### Event Logging

```python
from runtime.middleware.logging import get_logger

logger = get_logger()
logger.log_event(
    actor="agent.core",
    event="tool.call",
    level="INFO",
    conversation_id="conv-123",
    task_id="task-456"
)
```

Outputs JSONL to `logs/events/*.jsonl` (OTel-compatible).

### PII Redaction

```python
from runtime.middleware.redaction import redact_pii

safe_text = redact_pii("My email is john@example.com")
# Result: "My email is [EMAIL_REDACTED]"
```

### WORM Logging (Write-Once-Read-Many)

The project uses Merkle trees for cryptographic integrity verification:

```python
from runtime.middleware.worm import get_worm_logger

worm_logger = get_worm_logger()
worm_logger.append_event({
    "actor": "agent.core",
    "event": "decision.made",
    "timestamp": datetime.utcnow().isoformat()
})

# Verify integrity
root_hash = worm_logger.get_root_hash()  # Merkle root
is_valid = worm_logger.verify_integrity()  # Validate chain
```

**Key Features:**
- **Append-only**: Events cannot be modified once written
- **Merkle Tree**: SHA-256 hash chain for integrity verification
- **Tamper Detection**: Any modification breaks the hash chain
- **Thread-safe**: Uses locks for concurrent access

### Compliance Requirements

1. **Decision Records** - ALL actionable decisions must have DR
2. **Provenance** - ALL artifacts must have PROV-JSON metadata
3. **PII Masking** - ALL logs must have PII redacted
4. **WORM Logging** - Audit logs must be append-only, immutable with Merkle verification
5. **Reproducibility** - Model version, seed, config must be logged
6. **Retention** - Follow `config/retention.yaml` policies (7 years for audit logs)

---

## Testing Strategy

### Test Markers (pytest.ini)

```python
@pytest.mark.unit           # Fast, isolated unit tests
@pytest.mark.integration    # Integration tests (slower)
@pytest.mark.compliance     # Compliance/conformity tests
@pytest.mark.e2e           # End-to-end tests (slowest)
@pytest.mark.htn           # HTN planning tests
@pytest.mark.performance   # Performance/load tests
@pytest.mark.slow          # Tests >5 seconds
@pytest.mark.memory        # Memory-related tests
@pytest.mark.tools         # Tool-related tests
@pytest.mark.resilience    # Resilience and fallback tests
@pytest.mark.fixtures      # Fixture validation tests
@pytest.mark.requires_llama_cpp  # Requires optional ml dependency
```

### Fixtures (conftest.py)

```python
@pytest.fixture
def isolated_fs(tmp_path):
    """Isolated filesystem for tests"""
    structure = {
        'root': tmp_path,
        'logs': tmp_path / 'logs',
        'logs_events': tmp_path / 'logs' / 'events',
    }
    for path in structure.values():
        if isinstance(path, Path):
            path.mkdir(parents=True, exist_ok=True)
    return structure

@pytest.fixture
def mock_model():
    """Mock model for tests"""
    class MockModel:
        def generate(self, prompt, config):
            return GenerationResult(text="Mock response", usage={"total_tokens": 10})
    return MockModel()
```

### Writing Tests

```python
def test_python_sandbox_basic():
    """Test basique du sandbox"""
    tool = PythonSandboxTool()
    result = tool.execute({"code": "print('Hello')"})

    assert result.is_success()
    assert "Hello" in result.output

@pytest.mark.parametrize("code,expected", [
    ("2 + 2", "4"),
    ("'hello'.upper()", "HELLO"),
])
def test_python_sandbox_expressions(code, expected):
    """Test avec paramètres multiples"""
    tool = PythonSandboxTool()
    result = tool.execute({"code": f"print({code})"})
    assert expected in result.output
```

---

## Common Tasks

### Adding a New Tool

1. **Create tool class** in `tools/my_tool.py`:
```python
from tools.base import BaseTool, ToolResult, ToolStatus
from typing import Dict, Any, Optional

class MyTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="my_tool",
            description="Clear description for LLM prompting"
        )

    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        # 1. Validate arguments
        is_valid, error = self.validate_arguments(arguments)
        if not is_valid:
            return ToolResult(status=ToolStatus.ERROR, error=error)

        # 2. Execute with error handling
        try:
            result = self._do_work(arguments)
            return ToolResult(status=ToolStatus.SUCCESS, output=result)
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    def validate_arguments(self, arguments: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        # Validate required parameters
        if "required_param" not in arguments:
            return False, "Missing required_param"
        return True, None

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "required_param": {"type": "string", "description": "..."}
            },
            "required": ["required_param"]
        }
```

2. **Register** (auto-registered via `get_registry()` - no manual registration needed)

3. **Add tests** in `tests/test_tools.py`:
```python
@pytest.mark.tools
def test_my_tool_basic():
    tool = MyTool()
    result = tool.execute({"required_param": "test"})
    assert result.is_success()
```

4. **Enable in config** (`config/agent.yaml`):
```yaml
tools:
  enabled:
    - my_tool
```

### Adding a New Middleware

1. **Create middleware** in `runtime/middleware/my_middleware.py`:
```python
class MyMiddleware:
    """My middleware description"""
    def __init__(self):
        pass

    def process(self, data):
        return data

# Singleton pattern
_instance: Optional[MyMiddleware] = None

def get_my_middleware() -> MyMiddleware:
    global _instance
    if _instance is None:
        _instance = MyMiddleware()
    return _instance
```

2. **Integrate in agent** (`runtime/agent.py`):
```python
try:
    self.my_middleware = get_my_middleware()
except Exception as e:
    print(f"⚠ Failed to initialize my_middleware: {e}")
    self.my_middleware = None
```

### Adding Configuration Parameter

1. **Update YAML** (`config/agent.yaml`):
```yaml
my_feature:
  enabled: true
  param1: "value"
```

2. **Update Pydantic model** (`runtime/config.py`):
```python
class MyFeatureConfig(BaseModel):
    enabled: bool = True
    param1: str = "value"

class AgentConfig(BaseModel):
    my_feature: MyFeatureConfig
```

3. **Use in code**:
```python
config = get_config()
if config.my_feature.enabled:
    value = config.my_feature.param1
```

---

## Git Workflow

### Commit Standards

```bash
git commit -m "feat: Add HTN planning integration"
git commit -m "fix: Resolve PII masking in event logger"
git commit -m "docs: Update CLAUDE.md"
git commit -m "test: Add unit tests for TaskVerifier"

# Format: <type>: <description>
# Types: feat, fix, docs, test, refactor, style, chore
```

### Pre-Push Checklist

- [ ] Tests passing (`pdm run test`)
- [ ] Code formatted (`pdm run format`)
- [ ] Linting clean (`pdm run lint`)
- [ ] Type check passes (`pdm run typecheck`)
- [ ] No secrets in code
- [ ] Decision Records for major changes
- [ ] Documentation updated

---

## Key Documents

### Essential Reading
- **README.md** - Project overview (French)
- **AGENTS.md** - Agent system documentation (French: "Repository Guidelines")
- **SYNTHESE_HTN.md** - HTN planning overview
- **.github/copilot-instructions.md** - GitHub Copilot guide
- **QUICK_TEST.md** - Post-installation test guide
- **README_DEPLOYMENT.md** - Production deployment guide

### Architecture Decisions
- **docs/ADRs/** - Architecture Decision Records
  - `001-initial-architecture.md` - Initial system design
  - `002-decision-records.md` - DR format and signing
  - `003-openapi-placement.md` - API schema location

### Compliance
- **docs/COMPLIANCE_GUARDIAN.md** - Compliance module docs
- **config/compliance_rules.yaml** - Validation rules
- **config/retention.yaml** - Retention policies (7 years for audit)
- **SECURITY.md** - Security guidelines
- **audit/reports/** - Compliance validation reports

### Development Guides
- **docs/PERPLEXITY_INTEGRATION.md** - Perplexity API setup
- **docs/INDEX.md** - Documentation index
- **models/weights/README.md** - Model download instructions

---

## FAQ

**Q: When is HTN planning used vs simple loop?**
A: HTN is auto-triggered for multi-step queries (keywords like "puis", "ensuite" or 2+ action verbs). Single actions use simple loop.

**Q: How do I switch between Perplexity and llama.cpp?**
A: Update `config/agent.yaml` → `model.backend` to "perplexity" or "llama.cpp". Both backends share the same interface.

**Q: What if a middleware fails to initialize?**
A: All middlewares have graceful fallbacks. If initialization fails, the agent continues but that middleware is disabled.

**Q: Where are logs stored?**
A: `logs/events/` (events), `logs/decisions/` (DRs), `logs/prompts/` (prompts), `logs/safeties/` (blocked actions).

**Q: How do I run specific tests?**
A: Use markers: `pytest -m unit`, `pytest -m compliance`, `pytest -m htn`, etc.

**Q: Why PDM instead of pip?**
A: PDM provides better dependency resolution, lockfiles, and PEP 582 support. Use `pdm install` instead of `pip install -r requirements.txt`.

**Q: What Python versions are supported?**
A: Python 3.10 through 3.14 are officially supported. The project uses modern type hints (e.g., `tuple[bool, str]` instead of `Tuple[bool, str]`).

**Q: How do I run a single test?**
A: `pytest tests/test_agent.py::test_function_name` or `pytest tests/test_planner/test_executor.py -k "test_parallel"`

**Q: What's the difference between resilience and fixtures markers?**
A: `@pytest.mark.resilience` tests error handling and fallback mechanisms. `@pytest.mark.fixtures` validates that test fixtures themselves work correctly.

---

## Evaluation & Benchmarking

### Running Benchmarks

```bash
# Install benchmark dependencies
pdm install -G benchmark

# Run evaluation suite
python -m eval.runner

# Run specific benchmarks
python -m eval.humaneval  # HumanEval coding tasks
python -m eval.mbpp       # MBPP programming problems
```

### Benchmark Structure

```
eval/
├── base.py              # Generic evaluation harness
├── runner.py            # Benchmark orchestration
├── metrics.py           # Performance metrics
├── humaneval.py         # HumanEval implementation
├── mbpp.py             # MBPP implementation
└── benchmarks/
    ├── custom/
    │   ├── compliance/        # Compliance test harness
    │   ├── htn_planning/      # HTN planning benchmarks
    │   └── tool_orchestration/  # Tool usage benchmarks
    └── swe_bench/            # SWE-bench lite
```

### Custom Benchmark Harnesses

The project includes Quebec SME-specific benchmarks:
- **Compliance**: Validates Loi 25, GDPR, AI Act conformance
- **HTN Planning**: Tests task decomposition and execution
- **Tool Orchestration**: Measures tool selection and chaining

---

## Performance Considerations

### Optimization Targets (from `config/eval_targets.yaml`)
- HumanEval pass@1: ≥ 0.65
- MBPP: ≥ 0.60
- SWE-bench lite: 50% on 50 tasks
- Agentic scenarios: ≥ 0.75
- Decision record coverage: ≥ 95%
- Zero critical violations per 1000 tasks

### Execution Strategies
- **Sequential**: Default for safety, one task at a time
- **Parallel**: For independent tasks, uses `ThreadPoolExecutor`
- **Adaptive**: Dynamically switches based on resource availability

---

**Remember**: This is a compliance-first, governance-focused project. Always prioritize traceability, security, and reproducibility.

---

## Gradio Interfaces

FilAgent provides three web-based interfaces for different use cases:

### 1. Production Interface (Port 7860)

**File**: `gradio_app_production.py`

**Launch**: `pdm run python gradio_app_production.py`

**Features**:
- Multi-turn conversations with context retention
- Document Analyzer tool with real-time preview
- Model configuration (dynamic switching between Perplexity models)
- Export results in multiple formats (JSON, CSV, Excel)
- Download All as ZIP package

**Document Analyzer Tab**:
- Upload files (PDF, DOCX, XLSX - max 50 MB)
- Select analysis type (invoice, extract, financial, contract, report)
- Real-time preview rendering
- Export analysis results (JSON with EdDSA signature, CSV UTF-8, Excel)
- Download entire analysis package as ZIP
- Comprehensive validation (extension, size, corruption, permissions, disk space)
- Error messages with clear solutions (10+ standardized messages)
- PII redaction in all outputs (Loi 25/PIPEDA compliant)
- Decision Records for audit trail
- Timeout protection (30s max processing time)
- Automatic cleanup of temporary files

### 2. Model Selector Interface (Port 7861)

**File**: `gradio_app_model_selector.py`

**Launch**: `pdm run python gradio_app_model_selector.py`

**Features**:
- Interactive model comparison (5 Perplexity models)
- Difficulty-based recommendations (Low, Medium, High)
- Cost and latency estimation
- Example queries with results
- Model selection guide

See `docs/GUIDE_SELECTION_MODELES_PERPLEXITY.md` for detailed documentation.

### 3. FastAPI Server (Port 8000)

**File**: `runtime/server.py`

**Launch**: `pdm run server` or `python runtime/server.py`

**Features**:
- OpenAI-compatible API endpoints
- RESTful architecture
- API documentation at `/docs`
- WebSocket support for streaming
- Health checks and monitoring

**API Endpoints**:
- `POST /chat` - Send chat messages
- `GET /health` - Server health status
- `GET /docs` - Interactive API documentation (Swagger UI)

---

**Version**: 2.3.0
**Last Updated**: 2025-11-18
**Maintainer**: FilAgent Team

**Notes**:
- Update this file every time a major change is made to avoid outdated information
- Development platform: macOS
- All Document Analyzer features implemented as of v2.3.0 (Phases 1-6 complete)