# FilAgent - Comprehensive Guide for AI Assistants

**Version**: 2.0.0
**Last Updated**: 2025-11-14
**Project**: FilAgent - LLM Agent with Governance & Traceability
**Purpose**: Complete reference guide for AI assistants working on this codebase

---

## 📑 Table of Contents

1. [Project Overview](#project-overview)
2. [Repository Structure](#repository-structure)
3. [Core Architecture](#core-architecture)
4. [Development Workflows](#development-workflows)
5. [Coding Conventions](#coding-conventions)
6. [Testing Strategy](#testing-strategy)
7. [Compliance & Governance](#compliance--governance)
8. [HTN Planning System](#htn-planning-system)
9. [Configuration Management](#configuration-management)
10. [Common Tasks](#common-tasks)
11. [Git Workflows](#git-workflows)

---

## 🎯 Project Overview

### Mission

FilAgent is an LLM-based agent system with **fundamental emphasis on governance, legal traceability, security, and reproducibility**. The architecture is designed to be executable locally while meeting strict compliance standards (Quebec's Loi 25, EU AI Act, NIST AI RMF).

### Core Principles

1. **Governance First** - Compliance and traceability built-in from design
2. **Safety by Design** - Secure defaults, fail-safe mechanisms
3. **Reproducibility** - Deterministic outputs with version control
4. **Local-First** - Privacy-preserving local execution
5. **Modular Architecture** - Separation of concerns, testable components

### Key Capabilities

- **Hierarchical Task Network (HTN) Planning** - Complex multi-step task decomposition
- **Tool Execution** - Sandboxed code execution with safety guarantees
- **Memory Management** - Episodic (SQLite) + Semantic (FAISS) memory
- **Policy Engine** - RBAC, PII masking, guardrails
- **Audit Trail** - WORM logging, Decision Records, provenance tracking
- **Compliance** - ISO/IEC 42001, NIST AI RMF, Loi 25, GDPR, AI Act

### Technology Stack

- **Language**: Python 3.10+
- **LLM Runtime**: llama.cpp (local inference)
- **API Framework**: FastAPI + Uvicorn
- **Database**: SQLite (episodic), FAISS (semantic)
- **Testing**: pytest, pytest-asyncio, pytest-cov
- **Validation**: Pydantic, OpenAPI
- **Monitoring**: Prometheus, Grafana
- **Security**: cryptography (EdDSA signatures)

---

## 📂 Repository Structure

```
FilAgent/
├── config/                      # Configuration files (YAML)
│   ├── agent.yaml              # Main agent configuration (HTN, features)
│   ├── policies.yaml           # RBAC, PII, guardrails
│   ├── retention.yaml          # Data retention policies
│   ├── provenance.yaml         # Traceability configuration
│   ├── compliance_rules.yaml   # Compliance validation rules
│   ├── eval_targets.yaml       # Benchmark thresholds
│   └── prometheus.yml          # Monitoring configuration
│
├── runtime/                     # Core agent runtime
│   ├── agent.py                # Main Agent class (964 lines)
│   ├── server.py               # FastAPI server
│   ├── config.py               # Configuration loader
│   ├── model_interface.py      # LLM abstraction layer
│   └── middleware/             # Compliance middleware
│       ├── logging.py          # Structured logging (JSONL, OTel)
│       ├── audittrail.py       # Decision Records (DR)
│       ├── provenance.py       # W3C PROV-JSON tracking
│       ├── worm.py             # Write-Once-Read-Many logging
│       ├── redaction.py        # PII masking
│       ├── constraints.py      # Output validation
│       └── rbac.py             # Role-based access control
│
├── planner/                     # HTN Planning system
│   ├── planner.py              # HierarchicalPlanner (487 lines)
│   ├── task_graph.py           # Task DAG management
│   ├── executor.py             # TaskExecutor (parallel/sequential)
│   ├── verifier.py             # TaskVerifier (validation)
│   ├── compliance_guardian.py  # Compliance integration
│   ├── plan_cache.py           # Plan caching
│   ├── work_stealing.py        # Work stealing scheduler
│   ├── metrics.py              # HTN metrics
│   └── state_machine.yaml      # State transitions
│
├── tools/                       # Tool execution framework
│   ├── base.py                 # BaseTool abstract class
│   ├── registry.py             # Tool registry (68 lines)
│   ├── calculator.py           # Example: calculator tool
│   ├── file_reader.py          # Example: file reader tool
│   ├── python_sandbox/         # Python code sandbox
│   ├── shell_sandbox/          # Bash sandbox
│   ├── code_exec/              # Test runner (pytest, etc.)
│   └── connectors/             # Local DB connectors
│
├── memory/                      # Memory management
│   ├── episodic.py             # SQLite episodic memory
│   ├── semantic/               # FAISS semantic memory
│   ├── working_set/            # Active context (TTL)
│   └── policies/               # Memory policies
│
├── policy/                      # Policy definitions
│   └── legal/                  # Legal templates
│
├── provenance/                  # Provenance tracking
│   ├── signatures/             # Cryptographic signatures
│   └── snapshots/              # Version snapshots
│
├── logs/                        # Structured logging
│   ├── events/                 # JSONL event logs
│   ├── decisions/              # Decision Records (DR-*.json)
│   ├── prompts/                # Prompts/responses (hashed)
│   └── safeties/               # Blocked actions
│
├── audit/                       # Audit & compliance
│   ├── reports/                # Monthly reports, DPIA
│   ├── samples/                # Verifiable samples
│   └── signed/                 # WORM sealed archives
│
├── eval/                        # Evaluation & benchmarks
│   ├── benchmarks/             # HumanEval, MBPP, SWE-bench
│   ├── runs/                   # Evaluation runs
│   └── reports/                # Benchmark reports
│
├── tests/                       # Test suite
│   ├── conftest.py             # Pytest fixtures
│   ├── test_agent.py           # Agent tests
│   ├── test_compliance_flow.py # Compliance tests
│   ├── test_integration_e2e.py # E2E tests
│   ├── test_planner/           # HTN planner tests
│   │   ├── test_task_graph.py
│   │   ├── test_planner.py
│   │   ├── test_executor.py
│   │   └── test_verifier.py
│   └── contract/               # Contract tests (OpenAPI)
│
├── docs/                        # Documentation
│   ├── ADRs/                   # Architecture Decision Records
│   │   ├── 001-initial-architecture.md
│   │   ├── 002-decision-records.md
│   │   └── 003-openapi-placement.md
│   ├── SOPs/                   # Standard Operating Procedures
│   ├── COMPLIANCE_GUARDIAN.md  # Compliance module docs
│   ├── INTEGRATION_OPENAPI.md  # OpenAPI integration
│   └── PROMETHEUS_SETUP.md     # Monitoring setup
│
├── examples/                    # Usage examples
├── scripts/                     # Utility scripts
├── grafana/                     # Grafana dashboards
├── models/weights/              # LLM model weights
├── openapi.yaml                # OpenAPI specification
├── requirements.txt            # Python dependencies
├── pytest.ini                  # Pytest configuration
├── .flake8                     # Linting configuration
└── README.md                   # Project README
```

---

## 🏗️ Core Architecture

### 1. Agent Core (`runtime/agent.py`)

The main `Agent` class orchestrates all components:

```python
class Agent:
    def __init__(self, config=None):
        self.config = get_config()          # Configuration
        self.model = None                   # LLM interface
        self.tool_registry = get_registry() # Tools

        # Compliance middlewares (with fallbacks)
        self.logger = get_logger()          # Structured logging
        self.dr_manager = get_dr_manager()  # Decision Records
        self.tracker = get_tracker()        # Provenance

        # HTN Planning components
        self.planner = HierarchicalPlanner(...)
        self.executor = TaskExecutor(...)
        self.verifier = TaskVerifier(...)
```

**Key Methods**:
- `run(user_query)` - Main execution loop
- `_requires_planning(query)` - Detect if HTN needed
- `_run_with_htn(query)` - HTN-based execution
- `_run_simple(query)` - Simple loop execution

### 2. Middleware System

All middlewares follow the **singleton pattern** with graceful fallbacks:

```python
# Pattern for all middlewares
try:
    self.logger = get_logger()
except Exception as e:
    print(f"⚠ Failed to initialize logger: {e}")
    self.logger = None

# Usage with null-safety
if self.logger:
    self.logger.log_event(...)
```

**Available Middlewares**:
- `logging.py` - JSONL structured logging (OTel-compatible)
- `audittrail.py` - Decision Records (DR) with EdDSA signatures
- `provenance.py` - W3C PROV-JSON tracking
- `worm.py` - Write-Once-Read-Many audit logs
- `redaction.py` - PII masking
- `constraints.py` - Output validation (JSONSchema, regex)
- `rbac.py` - Role-based access control

### 3. HTN Planning System

**Components**:

```python
# 1. Planner - Decomposes queries into task graphs
planner = HierarchicalPlanner(
    model_interface=model,
    tools_registry=registry,
    max_decomposition_depth=3,
    enable_tracing=True
)

# 2. Executor - Executes tasks (parallel/sequential/adaptive)
executor = TaskExecutor(
    action_registry=actions,
    strategy=ExecutionStrategy.ADAPTIVE,
    max_workers=4,
    timeout_per_task_sec=60
)

# 3. Verifier - Validates results
verifier = TaskVerifier(
    default_level=VerificationLevel.STRICT,
    enable_tracing=True
)
```

**Execution Flow**:

```
User Query
    ↓
Does it need HTN? → NO → Simple Loop (max 10 iterations)
    ↓ YES
Plan (decompose to DAG)
    ↓
Execute (parallel/sequential)
    ↓
Verify (validate results)
    ↓
Success? → YES → Format response
    ↓ NO
Fallback to simple loop
```

### 4. Tool System

All tools inherit from `BaseTool`:

```python
from tools.base import BaseTool, ToolResult, ToolStatus

class MyTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="my_tool",
            description="Tool description"
        )

    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        # 1. Validate
        is_valid, error = self.validate_arguments(arguments)
        if not is_valid:
            return ToolResult(status=ToolStatus.ERROR, error=error)

        # 2. Execute safely
        try:
            result = self._safe_execute(arguments)
            return ToolResult(status=ToolStatus.SUCCESS, output=result)
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))
```

**Tool Registry**:

```python
from tools.registry import get_registry

registry = get_registry()
tool = registry.get("python_sandbox")
result = tool.execute({"code": "print('hello')"})
```

### 5. Memory System

**Episodic Memory** (SQLite):
```python
from memory.episodic import add_message, get_messages

add_message(conversation_id, role, content)
messages = get_messages(conversation_id, limit=10)
```

**Semantic Memory** (FAISS):
- Located in `memory/semantic/`
- Embedding-based retrieval
- LRU eviction policy

### 6. Configuration System

**Loading Configuration**:

```python
from runtime.config import get_config

config = get_config()  # Loads config/agent.yaml
```

**Configuration Structure**:
- `features` - Feature flags (HTN, debug, etc.)
- `planner` - HTN planner configuration
- `executor` - Task executor configuration
- `verifier` - Verifier configuration
- `logging` - Logging configuration
- `policies` - Policy engine configuration

---

## 🔧 Development Workflows

### Initial Setup

```bash
# 1. Clone repository
git clone https://github.com/fil04331/FilAgent.git
cd FilAgent

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Download model (example)
mkdir -p models/weights
cd models/weights
# Download your GGUF model here
cd ../..

# 5. Initialize database
python -c "from memory.episodic import create_tables; create_tables()"

# 6. Run tests
pytest
```

### Running the Server

```bash
# Development mode
python runtime/server.py

# Server runs on http://localhost:8000
# API docs: http://localhost:8000/docs
```

### Running Tests

```bash
# All tests
pytest

# Specific markers
pytest -m unit              # Unit tests only
pytest -m integration       # Integration tests
pytest -m compliance        # Compliance tests
pytest -m e2e              # End-to-end tests

# With coverage
pytest --cov=. --cov-report=html

# Specific module
pytest tests/test_planner/
```

### Code Quality

```bash
# Format code
python -m black .

# Lint
python -m flake8 .

# Type check
python -m mypy .
```

---

## 📝 Coding Conventions

### Python Version & Imports

```python
# Python 3.10+ REQUIRED
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime

# Import order:
# 1. Standard library
# 2. Third-party (pydantic, fastapi, etc.)
# 3. Local modules
```

### Type Hints (MANDATORY)

```python
# ✅ GOOD
def chat(self, message: str, conversation_id: str,
         task_id: Optional[str] = None) -> Dict[str, Any]:
    ...

# ❌ BAD - No types
def chat(self, message, conversation_id, task_id=None):
    ...
```

### Docstrings (French) & Comments (English)

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
    # Calculate hash for integrity check
    prompt_hash = hashlib.sha256(input_message.encode()).hexdigest()

    # Execute tool with timeout protection
    result = self._execute_tool_with_timeout(tool_call, timeout=30)
```

### Naming Conventions

```python
# Variables & functions: snake_case
conversation_id = "conv-123"
def create_decision_record(task_id: str) -> DecisionRecord:
    ...

# Classes: PascalCase
class AgentConfig:
    ...

# Constants: UPPER_SNAKE_CASE
MAX_ITERATIONS = 10
DEFAULT_TIMEOUT = 30
```

### Error Handling

```python
# Pattern for middlewares: graceful fallback
try:
    self.logger = get_logger()
except Exception as e:
    print(f"⚠ Failed to initialize logger: {e}")
    self.logger = None

# Usage with null-safety
if self.logger:
    self.logger.log_event(...)

# Explicit status codes
class ToolStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    BLOCKED = "blocked"  # Blocked by policy
    TIMEOUT = "timeout"
```

### Logging Standards

```python
# ✅ GOOD - Clear logs with emojis
print("✓ Model initialized")
print("⚠ Warning: Using CPU, generation will be slow")
print("❌ Error: Failed to load config")
print(f"ℹ Processing {len(messages)} messages")

# ❌ BAD - Cryptic logs
print("Model OK")
print("WARN: CPU")
```

---

## 🧪 Testing Strategy

### Test Organization

```
tests/
├── conftest.py                    # Shared fixtures
├── test_agent.py                  # Agent core tests
├── test_tools.py                  # Tool tests
├── test_memory.py                 # Memory tests
├── test_compliance_flow.py        # Compliance tests
├── test_integration_e2e.py        # E2E tests
└── test_planner/                  # HTN planner tests
    ├── test_task_graph.py
    ├── test_planner.py
    ├── test_executor.py
    └── test_verifier.py
```

### Test Markers

```python
# pytest.ini
[pytest]
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (slower)
    compliance: Compliance/conformity tests
    e2e: End-to-end tests (slowest)

# Usage in tests
@pytest.mark.unit
def test_config_loading():
    ...

@pytest.mark.compliance
def test_dr_signature_valid():
    ...
```

### Fixtures (`conftest.py`)

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

## ⚖️ Compliance & Governance

### Decision Records (DR)

Every significant decision MUST generate a Decision Record:

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

**DR Structure** (`logs/decisions/DR-*.json`):

```json
{
  "dr_id": "DR-20250820-0007",
  "ts": "2025-08-20T15:13:12.002-04:00",
  "actor": "agent.core",
  "task_id": "T-20250820-0012",
  "policy_version": "policies@a1b2c3d",
  "model_fingerprint": "weights/base.gguf@sha256:abc...",
  "prompt_hash": "sha256:...",
  "reasoning_markers": ["plan:3-steps"],
  "tools_used": ["python_sandbox@v0.3"],
  "alternatives_considered": ["do_nothing", "ask_clarification"],
  "decision": "proceed_generate_code",
  "signature": "eddsa:..."
}
```

### Provenance Tracking

W3C PROV-JSON tracking for all artifacts:

```python
from runtime.middleware.provenance import get_tracker

tracker = get_tracker()
trace_id = tracker.track_generation(
    conversation_id="conv-123",
    input_message="Analyze data.csv"
)
```

### Event Logging

JSONL structured logging (OTel-compatible):

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

**Event Structure** (`logs/events/*.jsonl`):

```json
{
  "ts": "2025-08-20T15:12:05.431-04:00",
  "trace_id": "9b1d1f...",
  "span_id": "e21a...",
  "level": "INFO",
  "actor": "agent.core",
  "event": "tool.call",
  "task_id": "T-20250820-0012",
  "conversation_id": "C-1a2b3c",
  "pii_redacted": true
}
```

### PII Redaction

Automatic PII masking before logging:

```python
from runtime.middleware.redaction import redact_pii

safe_text = redact_pii("My email is john@example.com")
# Result: "My email is [EMAIL_REDACTED]"
```

### Compliance Requirements

1. **Decision Records** - ALL actionable decisions must have DR
2. **Provenance** - ALL artifacts must have PROV-JSON metadata
3. **PII Masking** - ALL logs must have PII redacted
4. **WORM Logging** - Audit logs must be append-only, immutable
5. **Reproducibility** - Model version, seed, config must be logged
6. **Retention** - Follow retention policies in `config/retention.yaml`

---

## 🔄 HTN Planning System

### When HTN is Used

HTN Planning is triggered when query is detected as multi-step:

```python
def _requires_planning(self, query: str) -> bool:
    """Detect if HTN is needed"""
    keywords = ["puis", "ensuite", "après", "finalement", "et"]
    action_verbs = ["lis", "analyse", "génère", "crée", "calcule"]

    has_multi_step = any(kw in query.lower() for kw in keywords)
    num_actions = sum(1 for verb in action_verbs if verb in query.lower())

    return has_multi_step or num_actions >= 2
```

**Examples**:
- ❌ "Lis data.csv" → Simple loop (single action)
- ✅ "Lis data.csv puis analyse les données" → HTN (multi-step)
- ✅ "Lis file1.csv, file2.csv, file3.csv et analyse" → HTN (parallel tasks)

### HTN Execution Flow

```python
def _run_with_htn(self, user_query: str) -> Dict[str, Any]:
    """HTN-based execution"""

    # 1. Plan - Decompose to task graph
    plan_result = self.planner.plan(
        query=user_query,
        strategy=PlanningStrategy.HYBRID,
        context={"conversation_id": self.conversation_id}
    )

    # 2. Record decision (Loi 25 compliance)
    self.dr_manager.record_decision(
        decision_type="planning",
        input_data={"query": user_query},
        output_data={"plan": plan_result.to_dict()},
        reasoning=plan_result.reasoning
    )

    # 3. Execute - Parallel/sequential based on DAG
    exec_result = self.executor.execute(
        graph=plan_result.graph,
        context={"conversation_id": self.conversation_id}
    )

    # 4. Verify - Validate all results
    verifications = self.verifier.verify_graph_results(
        graph=plan_result.graph,
        level=VerificationLevel.STRICT
    )

    # 5. Format response or fallback
    if exec_result.success:
        return self._format_htn_response(plan_result, exec_result, verifications)
    else:
        # Critical failure: fallback to simple loop
        return self._run_simple(user_query)
```

### Planning Strategies

```python
class PlanningStrategy(str, Enum):
    LLM_BASED = "llm_based"      # LLM decomposes query (flexible)
    RULE_BASED = "rule_based"    # Predefined rules (fast, deterministic)
    HYBRID = "hybrid"            # Combination (recommended)
```

**Configuration** (`config/agent.yaml`):

```yaml
planner:
  default_strategy: "hybrid"
  max_decomposition_depth: 3
  max_retry_attempts: 2
  planning_timeout_sec: 30
```

### Execution Strategies

```python
class ExecutionStrategy(str, Enum):
    SEQUENTIAL = "sequential"    # One task at a time
    PARALLEL = "parallel"        # All independent tasks in parallel
    ADAPTIVE = "adaptive"        # Decide based on resources (recommended)
```

**Configuration**:

```yaml
executor:
  default_strategy: "adaptive"
  max_parallel_workers: 4
  task_timeout_sec: 60
  enable_work_stealing: true
```

### Verification Levels

```python
class VerificationLevel(str, Enum):
    BASIC = "basic"          # Check task completed
    STRICT = "strict"        # Validate outputs (recommended)
    PARANOID = "paranoid"    # Full validation + self-checks
```

### Task Graph

Task graphs are DAGs (Directed Acyclic Graphs):

```python
from planner.task_graph import TaskGraph, TaskNode, TaskStatus

# Create graph
graph = TaskGraph()

# Add tasks
task1 = TaskNode(task_id="t1", name="Read file", action="read_file")
task2 = TaskNode(task_id="t2", name="Analyze data", action="analyze")
task3 = TaskNode(task_id="t3", name="Generate report", action="generate")

# Add dependencies
graph.add_task(task1)
graph.add_task(task2, depends_on=["t1"])
graph.add_task(task3, depends_on=["t2"])

# Execution order: t1 → t2 → t3
```

---

## ⚙️ Configuration Management

### Configuration Files

All configuration in `config/`:

```yaml
# config/agent.yaml - Main configuration
features:
  htn_enabled: false          # Enable HTN planning
  debug_mode: false           # Debug logging
  parallel_execution: true    # Parallel task execution
  strict_validation: true     # Strict result validation
  decision_records: true      # Decision Record generation

planner:
  default_strategy: "hybrid"
  max_decomposition_depth: 3
  max_retry_attempts: 2

executor:
  default_strategy: "adaptive"
  max_parallel_workers: 4
  task_timeout_sec: 60

verifier:
  default_level: "strict"
  enable_self_checks: true
```

### Loading Configuration

```python
from runtime.config import get_config

# Singleton pattern
config = get_config()  # Loads config/agent.yaml

# Access values
if config.features.htn_enabled:
    # HTN is enabled
    ...
```

### Environment-Specific Configs

```bash
# Development
config/agent.yaml           # Default config
config/agent.dev.yaml       # Dev overrides (optional)

# Production
config/agent.prod.yaml      # Prod overrides (optional)
```

### Validation with Pydantic

```python
from pydantic import BaseModel, Field

class GenerationConfig(BaseModel):
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    max_tokens: int = Field(default=800, ge=1, le=4096)
    seed: int = 42

# Automatic validation on load
config = GenerationConfig(temperature=0.5)  # OK
config = GenerationConfig(temperature=3.0)  # ValidationError
```

---

## 🛠️ Common Tasks

### Adding a New Tool

1. Create tool class:

```python
# tools/my_tool.py
from tools.base import BaseTool, ToolResult, ToolStatus
from typing import Dict, Any

class MyTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="my_tool",
            description="Description of what this tool does"
        )

    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        # Validate
        is_valid, error = self.validate_arguments(arguments)
        if not is_valid:
            return ToolResult(status=ToolStatus.ERROR, error=error)

        # Execute
        try:
            result = self._safe_execute(arguments)
            return ToolResult(status=ToolStatus.SUCCESS, output=result)
        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=str(e))

    def validate_arguments(self, arguments: Dict[str, Any]) -> tuple[bool, str | None]:
        # Your validation logic
        if "required_param" not in arguments:
            return False, "Missing required_param"
        return True, None
```

2. Register tool:

```python
# tools/registry.py
from tools.my_tool import MyTool

# Tool is auto-registered via get_registry()
```

3. Add tests:

```python
# tests/test_tools.py
def test_my_tool():
    tool = MyTool()
    result = tool.execute({"required_param": "value"})
    assert result.is_success()
```

### Adding a New Middleware

1. Create middleware:

```python
# runtime/middleware/my_middleware.py
from typing import Optional

class MyMiddleware:
    """My middleware description"""

    def __init__(self):
        # Initialize
        pass

    def process(self, data):
        # Process data
        return data

# Singleton pattern
_instance: Optional[MyMiddleware] = None

def get_my_middleware() -> MyMiddleware:
    global _instance
    if _instance is None:
        _instance = MyMiddleware()
    return _instance
```

2. Integrate in agent:

```python
# runtime/agent.py
from .middleware.my_middleware import get_my_middleware

class Agent:
    def __init__(self):
        try:
            self.my_middleware = get_my_middleware()
        except Exception as e:
            print(f"⚠ Failed to initialize my_middleware: {e}")
            self.my_middleware = None
```

### Adding a New Configuration Parameter

1. Update config file:

```yaml
# config/agent.yaml
my_feature:
  enabled: true
  param1: "value"
  param2: 42
```

2. Update Pydantic model:

```python
# runtime/config.py
class MyFeatureConfig(BaseModel):
    enabled: bool = True
    param1: str = "value"
    param2: int = Field(default=42, ge=0)

class AgentConfig(BaseModel):
    my_feature: MyFeatureConfig
```

3. Use in code:

```python
config = get_config()
if config.my_feature.enabled:
    # Feature is enabled
    value = config.my_feature.param1
```

### Running Benchmarks

```bash
# HumanEval benchmark
python eval/benchmarks/humaneval/run.py

# MBPP benchmark
python eval/benchmarks/mbpp/run.py

# Custom agent tasks
python eval/benchmarks/agent_tasks/run.py

# View reports
cat eval/reports/latest_report.json
```

### Monitoring with Prometheus

```bash
# Start Prometheus
prometheus --config.file=config/prometheus.yml

# View metrics: http://localhost:9090

# Start Grafana
grafana-server --config=grafana/grafana.ini

# View dashboards: http://localhost:3000
```

---

## 🔀 Git Workflows

### Branch Naming

Current branch for this session:
```
claude/claude-md-mhy6ple7vhvbu1yy-01TF47FNiS7br4kCHd677fLb
```

**Pattern**: `claude/<session-id>`

### Commit Standards

```bash
# Clear, descriptive commits
git add .
git commit -m "feat: Add HTN planning integration to agent core"
git commit -m "fix: Resolve PII masking in event logger"
git commit -m "docs: Update CLAUDE.md with HTN documentation"
git commit -m "test: Add unit tests for TaskVerifier"

# Commit message format
<type>: <description>

Types: feat, fix, docs, test, refactor, style, chore
```

### Push with Retries

```bash
# Always use -u origin <branch-name>
git push -u origin claude/claude-md-mhy6ple7vhvbu1yy-01TF47FNiS7br4kCHd677fLb

# If network failure, retry with exponential backoff (2s, 4s, 8s, 16s)
# Up to 4 retries
```

### Pre-Push Checklist

- [ ] All tests passing (`pytest`)
- [ ] Code formatted (`black .`)
- [ ] Linting clean (`flake8 .`)
- [ ] No secrets in code
- [ ] Decision Records for major changes
- [ ] Documentation updated

### Creating Pull Requests

```bash
# Ensure branch is up to date
git fetch origin
git status

# Push to remote
git push -u origin <branch-name>

# Create PR (provide GitHub PR URL to user)
# PR should include:
# - Clear title
# - Summary of changes
# - Test plan
# - Related issues
```

---

## 📋 Checklist for AI Assistants

### Before Making Changes

- [ ] Understand the context from README.md and this CLAUDE.md
- [ ] Review relevant ADRs in `docs/ADRs/`
- [ ] Check existing tests in `tests/`
- [ ] Review coding conventions in NORMES_CODAGE_FILAGENT.md

### During Development

- [ ] Follow coding conventions (type hints, docstrings, etc.)
- [ ] Write tests for new functionality
- [ ] Ensure compliance middlewares are used
- [ ] Generate Decision Records for significant changes
- [ ] Update documentation if needed

### Before Committing

- [ ] Run tests: `pytest`
- [ ] Format code: `black .`
- [ ] Lint code: `flake8 .`
- [ ] Check for secrets: `detect-secrets scan`
- [ ] Update CHANGELOG if applicable

### When Stuck

- [ ] Check `docs/` for documentation
- [ ] Review `examples/` for usage patterns
- [ ] Look at existing tests for similar functionality
- [ ] Check `audit/reports/` for compliance reports

---

## 📚 Key Documents Reference

### Essential Reading

1. **README.md** - Project overview and setup
2. **NORMES_CODAGE_FILAGENT.md** - Detailed coding standards
3. **FilAgent.md** - Architecture specification
4. **AGENT.md** - HTN integration guide (French)

### Architecture Decisions

1. **docs/ADRs/001-initial-architecture.md** - Core architecture
2. **docs/ADRs/002-decision-records.md** - DR system design
3. **docs/ADRs/003-openapi-placement.md** - API design

### Compliance

1. **docs/COMPLIANCE_GUARDIAN.md** - Compliance module
2. **config/compliance_rules.yaml** - Compliance rules
3. **config/retention.yaml** - Data retention policies

### HTN Planning

1. **SYNTHESE_HTN.md** - HTN system overview
2. **config/agent.yaml** - HTN configuration
3. **planner/** - HTN implementation

---

## 🎓 Learning Path for New AI Assistants

### Day 1: Understand the Basics
1. Read README.md
2. Review repository structure
3. Understand the core principles (governance, safety, reproducibility)
4. Run the server and tests locally

### Day 2: Dive into Architecture
1. Study `runtime/agent.py` - understand agent core
2. Review middleware system
3. Understand tool execution framework
4. Read ADR 001 (initial architecture)

### Day 3: Compliance & Governance
1. Study Decision Records system
2. Understand WORM logging
3. Review PII redaction
4. Read compliance documentation

### Day 4: HTN Planning
1. Study `planner/planner.py`
2. Understand task graphs
3. Review execution strategies
4. Read SYNTHESE_HTN.md

### Day 5: Testing & Quality
1. Review test structure
2. Understand fixtures
3. Write a sample test
4. Run benchmarks

---

## ❓ FAQ

### Q: When should I use HTN planning vs simple loop?

A: HTN is automatically triggered for multi-step queries (keywords like "puis", "ensuite" or multiple action verbs). For single actions, simple loop is used.

### Q: How do I add a new tool?

A: Create a class inheriting from `BaseTool`, implement `execute()` method, add to registry. See "Adding a New Tool" section.

### Q: What if a middleware fails to initialize?

A: All middlewares have graceful fallbacks. If initialization fails, the agent continues but that specific middleware is disabled.

### Q: How do I ensure compliance?

A: Always use middlewares (logger, dr_manager, tracker), follow Decision Record requirements, ensure PII is masked, use WORM logging.

### Q: Where are logs stored?

A: `logs/events/` (events), `logs/decisions/` (DRs), `logs/prompts/` (prompts), `logs/safeties/` (blocked actions).

### Q: How do I run specific tests?

A: Use pytest markers: `pytest -m unit`, `pytest -m compliance`, etc.

### Q: What's the branching strategy?

A: Work on branches with pattern `claude/<session-id>`. Current branch for this session is documented in git instructions.

### Q: How do I check code quality?

A: Run `black .` (format), `flake8 .` (lint), `mypy .` (type check), `pytest --cov` (coverage).

---

## 📞 Support & Resources

### Documentation
- `README.md` - Getting started
- `docs/` - All documentation
- `examples/` - Usage examples

### Configuration
- `config/agent.yaml` - Main configuration
- `config/policies.yaml` - Policy configuration

### Monitoring
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000
- API Docs: http://localhost:8000/docs

---

**Remember**: This is a compliance-first, governance-focused project. Always prioritize traceability, security, and reproducibility in your work.

**Version**: 2.0.0
**Last Updated**: 2025-11-14
**Maintainer**: FilAgent Team
