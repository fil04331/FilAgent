# CLAUDE.md - FilAgent

**Version**: 3.0.0 | **Stack**: Python 3.10+, FastAPI, Pydantic V2

## Quick Reference

```bash
# Setup
pdm install              # ou: pip install -r requirements.txt

# Run
pdm run server           # API → localhost:8000
pdm run mcp              # MCP server

# Test
pdm run test             # All tests
pytest -m unit           # Unit only
pytest -m compliance     # Compliance only

# Quality
pdm run format && pdm run lint && pdm run typecheck
```

## Architecture

```
runtime/
├── agent.py          # Agent principal + HTN
├── server.py         # FastAPI (OpenAI-compatible)
├── config.py         # Config singleton: get_config()
└── middleware/       # Tous singletons: get_*()
    ├── logging.py    # JSONL events
    ├── audittrail.py # Decision Records (EdDSA)
    └── provenance.py # W3C PROV-JSON

planner/              # HTN Planning
├── planner.py        # Décomposition tâches
├── executor.py       # Parallel/Sequential/Adaptive
└── verifier.py       # Validation résultats

tools/                # Outils agent
├── base.py           # BaseTool, ToolResult
├── math_calculator.py
├── file_read.py
├── python_sandbox.py
└── document_analyzer_pme.py
```

## Standards Obligatoires

### Typage Strict (Pydantic V2)
```python
# ✅ REQUIS
def process(self, data: InputModel) -> OutputModel:
    ...

# ❌ INTERDIT: Any, object, dict sans typage
```

### Middleware Pattern (Singleton + Fallback)
```python
from runtime.middleware.logging import get_logger

logger = get_logger()  # Singleton
if logger:
    logger.log_event(actor="agent", event="action")
```

### Tests (pytest markers)
```python
@pytest.mark.unit         # Rapide, isolé
@pytest.mark.integration  # Avec dépendances
@pytest.mark.compliance   # Loi 25, RGPD
@pytest.mark.htn          # HTN planning
```

## Compliance (Loi 25 / PIPEDA)

**Requis pour toute action:**
1. **Decision Record** → `logs/decisions/DR-*.json`
2. **Provenance** → `logs/traces/` (W3C PROV-JSON)
3. **PII Redaction** → `redact_pii()` sur tous les logs

```python
from runtime.middleware.audittrail import get_dr_manager
from runtime.middleware.redaction import redact_pii

dr_manager = get_dr_manager()
dr = dr_manager.create_dr(
    actor="agent.core",
    decision="execute_tool",
    reasoning="User request"
)
```

## Config

**Fichier principal**: `config/agent.yaml`

```python
from runtime.config import get_config
config = get_config()
# config.model.backend → "perplexity" | "llama.cpp"
# config.htn_planning.enabled → bool
```

## Ajouter un Outil

```python
# tools/my_tool.py
from tools.base import BaseTool, ToolResult, ToolStatus

class MyTool(BaseTool):
    def __init__(self):
        super().__init__(name="my_tool", description="...")
    
    def execute(self, args: dict) -> ToolResult:
        is_valid, err = self.validate_arguments(args)
        if not is_valid:
            return ToolResult(status=ToolStatus.ERROR, error=err)
        return ToolResult(status=ToolStatus.SUCCESS, output="...")
```

## Git Commits

```bash
feat: Add feature    fix: Bug fix
docs: Documentation  test: Tests
refactor: Refactor   chore: Maintenance
```

## Docs Clés

- `README.md` - Vue d'ensemble
- `AGENTS.md` - Guidelines agent
- `docs/COMPLIANCE_GUARDIAN.md` - Compliance
- `config/agent.yaml` - Configuration

---
*Full documentation: CLAUDE.md.backup.full*
