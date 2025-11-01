# 📘 Normes de Codage FilAgent - Guide de Référence Rapide

**Date** : 1 novembre 2025  
**Projet** : FilAgent  
**Usage** : Document de référence pour maintenir la cohérence du style de code

---

## 🎯 STYLE PYTHON

### Version & Imports
```python
# Python 3.10+ obligatoire
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime
import hashlib
import json

# Ordre des imports:
# 1. Standard library
# 2. Third-party (pydantic, fastapi, etc.)
# 3. Local modules
```

### Type Hints (OBLIGATOIRE)
```python
# ✅ BON
def chat(self, message: str, conversation_id: str, task_id: Optional[str] = None) -> Dict[str, Any]:
    ...

# ✅ BON - Union types avec |
def get_config(self) -> AgentConfig | None:
    ...

# ❌ MAUVAIS - Pas de types
def chat(self, message, conversation_id, task_id=None):
    ...
```

### Docstrings (Format Français)
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
    ...
```

### Comments (Format Anglais)
```python
# Calculate hash for integrity check
prompt_hash = hashlib.sha256(message.encode()).hexdigest()

# Execute tool with timeout protection
result = self._execute_tool_with_timeout(tool_call, timeout=30)
```

---

## 🏗️ PATTERNS ARCHITECTURAUX

### 1. Singleton Pattern
```python
# Pour: Configuration, Registres, Middlewares
_instance: Optional[MyClass] = None

def get_instance() -> MyClass:
    """Récupérer l'instance singleton"""
    global _instance
    if _instance is None:
        _instance = MyClass()
    return _instance

def reload_instance():
    """Recharger l'instance (utile pour tests)"""
    global _instance
    _instance = MyClass()
    return _instance
```

**Utilisation** :
- ✅ Configuration (`runtime/config.py`)
- ✅ Registre d'outils (`tools/registry.py`)
- ✅ Middlewares (`runtime/middleware/*`)

### 2. Factory Pattern
```python
def create_model(backend: str, **kwargs) -> ModelInterface:
    """Factory pour créer des modèles"""
    if backend == "llama.cpp":
        return LlamaCppInterface(**kwargs)
    elif backend == "vllm":
        return VllmInterface(**kwargs)
    else:
        raise ValueError(f"Unknown backend: {backend}")
```

**Utilisation** :
- ✅ Création de modèles (`runtime/model_interface.py`)
- ✅ Création d'outils (futur)

### 3. Strategy Pattern (Interface + Implémentations)
```python
# Interface abstraite
from abc import ABC, abstractmethod

class BaseTool(ABC):
    """Interface pour tous les outils"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    @abstractmethod
    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """Exécuter l'outil"""
        pass
    
    def validate_arguments(self, arguments: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Valider les arguments"""
        return True, None

# Implémentation concrète
class PythonSandboxTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="python_sandbox",
            description="Exécuter du code Python en sandbox"
        )
    
    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        # Implémentation
        ...
```

**Utilisation** :
- ✅ Outils (`tools/base.py` + implémentations)
- ✅ Middlewares (futur)

### 4. Middleware Pattern
```python
# Dans agent.py
if self.logger:
    self.logger.log_event(
        actor="agent.core",
        event="conversation.start",
        level="INFO",
        conversation_id=conversation_id
    )

# Plus tard
if self.dr_manager and tools_used:
    dr = self.dr_manager.create_dr(
        actor="agent.core",
        task_id=task_id,
        decision="tool_execution",
        tools_used=tools_used
    )
```

**Principes** :
- ✅ Optionnel (if middleware:)
- ✅ Non-bloquant (try/except)
- ✅ Logs clairs si fail

---

## 🔒 SÉCURITÉ & VALIDATION

### Validation d'Inputs
```python
def execute(self, arguments: Dict[str, Any]) -> ToolResult:
    """Exécuter avec validation stricte"""
    
    # 1. Valider structure
    is_valid, error = self.validate_arguments(arguments)
    if not is_valid:
        return ToolResult(
            status=ToolStatus.ERROR,
            output="",
            error=f"Invalid arguments: {error}"
        )
    
    # 2. Valider contenu
    code = arguments['code']
    if len(code) > 50000:
        return ToolResult(
            status=ToolStatus.ERROR,
            output="",
            error="Code too long (max 50000 characters)"
        )
    
    # 3. Bloquer patterns dangereux
    dangerous_patterns = ['__import__', 'eval(', 'exec(']
    for pattern in dangerous_patterns:
        if pattern in code.lower():
            return ToolResult(
                status=ToolStatus.BLOCKED,
                output="",
                error=f"Blocked dangerous operation: {pattern}"
            )
    
    # 4. Exécuter
    try:
        result = self._execute_safe(code)
        return ToolResult(status=ToolStatus.SUCCESS, output=result)
    except Exception as e:
        return ToolResult(
            status=ToolStatus.ERROR,
            output="",
            error=str(e)
        )
```

### Paths Sécurisés
```python
from pathlib import Path

def read_file(self, file_path: str) -> str:
    """Lire fichier avec validation chemin"""
    
    # 1. Résoudre path absolu
    path = Path(file_path).resolve()
    
    # 2. Vérifier allowlist
    allowed_prefixes = [
        Path("working_set").resolve(),
        Path("temp").resolve(),
        Path("memory/working_set").resolve()
    ]
    
    if not any(str(path).startswith(str(prefix)) for prefix in allowed_prefixes):
        raise ValueError(f"Path not in allowlist: {file_path}")
    
    # 3. Vérifier existence
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # 4. Lire
    return path.read_text()
```

---

## 📊 CONFIGURATION (YAML + PYDANTIC)

### Structure YAML
```yaml
# config/agent.yaml
agent:
  name: llmagenta
  version: 0.2.0
  
generation:
  temperature: 0.2        # Déterministe
  top_p: 0.9
  max_tokens: 800
  seed: 42               # Reproductibilité
  
model:
  backend: "llama.cpp"
  path: "models/weights/base.gguf"
  context_size: 4096
  n_gpu_layers: 0        # CPU-only
  
memory:
  episodic:
    enabled: true
    ttl_days: 30
    backend: "sqlite"
    db_path: "memory/episodic.db"
```

### Validation Pydantic
```python
from pydantic import BaseModel, Field

class GenerationConfig(BaseModel):
    """Configuration de génération"""
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    max_tokens: int = Field(default=800, ge=1, le=4096)
    seed: int = 42

class AgentConfig(BaseModel):
    """Configuration complète de l'agent"""
    name: str
    version: str
    generation: GenerationConfig
    model: ModelConfig
    memory: MemoryConfig
    
    @classmethod
    def load(cls, config_path: str = "config/agent.yaml") -> "AgentConfig":
        """Charger depuis YAML"""
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)
        return cls(**data)
```

**Avantages** :
- ✅ Validation automatique des types
- ✅ Valeurs par défaut
- ✅ Limites (ge, le, regex)
- ✅ Documentation auto-générée

---

## 🧪 TESTS (PYTEST)

### Structure des Tests
```python
# tests/test_tools.py
import pytest
from tools.python_sandbox import PythonSandboxTool

def test_python_sandbox_basic():
    """Test basique du sandbox"""
    tool = PythonSandboxTool()
    result = tool.execute({"code": "print('Hello')"})
    
    assert result.is_success()
    assert "Hello" in result.output

@pytest.mark.parametrize("code,expected", [
    ("2 + 2", "4"),
    ("'hello'.upper()", "HELLO"),
    ("len([1, 2, 3])", "3")
])
def test_python_sandbox_expressions(code, expected):
    """Test avec paramètres multiples"""
    tool = PythonSandboxTool()
    result = tool.execute({"code": f"print({code})"})
    
    assert expected in result.output
```

### Fixtures Réutilisables
```python
# tests/conftest.py
import pytest
from pathlib import Path

@pytest.fixture
def isolated_fs(tmp_path):
    """Système de fichiers temporaire isolé"""
    structure = {
        'root': tmp_path,
        'logs': tmp_path / 'logs',
        'logs_events': tmp_path / 'logs' / 'events',
        'logs_decisions': tmp_path / 'logs' / 'decisions'
    }
    
    for path in structure.values():
        if isinstance(path, Path):
            path.mkdir(parents=True, exist_ok=True)
    
    return structure

@pytest.fixture
def mock_model():
    """Modèle mocké pour tests"""
    class MockModel:
        def generate(self, prompt, config):
            return GenerationResult(
                text="Mock response",
                usage={"total_tokens": 10}
            )
    return MockModel()
```

### Markers
```python
# pytest.ini
[pytest]
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (slower)
    compliance: Compliance/conformity tests
    e2e: End-to-end tests (slowest)

# Usage
@pytest.mark.unit
def test_config_loading():
    ...

@pytest.mark.compliance
def test_dr_signature_valid():
    ...
```

**Commandes** :
```bash
# Tous les tests
pytest

# Tests rapides seulement
pytest -m unit

# Tests de conformité
pytest -m compliance

# Avec coverage
pytest --cov=. --cov-report=html
```

---

## 🚨 GESTION D'ERREURS

### Fallbacks Gracieux
```python
# Pattern général pour middlewares
try:
    self.logger = get_logger()
except Exception as e:
    print(f"⚠ Failed to initialize logger: {e}")
    self.logger = None

# Plus tard dans le code
if self.logger:
    self.logger.log_event(...)
# Continue même si logger fail
```

### Codes de Statut Explicites
```python
class ToolStatus(str, Enum):
    """Statuts d'exécution d'un outil"""
    SUCCESS = "success"
    ERROR = "error"
    BLOCKED = "blocked"      # Bloqué par policy
    TIMEOUT = "timeout"

class ToolResult:
    """Résultat d'exécution d'un outil"""
    status: ToolStatus
    output: str
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}
    
    def is_success(self) -> bool:
        return self.status == ToolStatus.SUCCESS
```

### Logs Clairs avec Emojis
```python
# ✅ BON - Logs visibles et utiles
print("✓ Model initialized")
print("⚠ Warning: Using CPU, generation will be slow")
print("❌ Error: Failed to load config")
print(f"ℹ Processing {len(messages)} messages")

# ❌ MAUVAIS - Logs cryptiques
print("Model OK")
print("WARN: CPU")
print("ERROR")
```

---

## 📝 CONVENTIONS DE NOMMAGE

### Variables & Fonctions
```python
# snake_case pour tout
conversation_id = "conv-123"
task_id = "task-456"
prompt_hash = "abc123..."

def create_decision_record(task_id: str) -> DecisionRecord:
    ...

def is_valid_path(path: Path) -> bool:
    ...
```

### Classes
```python
# PascalCase
class AgentConfig:
    ...

class ToolRegistry:
    ...

class DecisionRecord:
    ...
```

### Constantes
```python
# UPPER_SNAKE_CASE
MAX_ITERATIONS = 10
DEFAULT_TIMEOUT = 30
LOG_DIR = Path("logs")
```

### Fichiers
```python
# snake_case.py
agent.py
model_interface.py
python_sandbox.py
audittrail.py
```

---

## 🔧 OUTILS & DÉPENDANCES

### Core Dependencies
```txt
# requirements.txt
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.0.0
pyyaml>=6.0
sqlite3  # Built-in

# LLM
llama-cpp-python>=0.2.0

# Compliance
cryptography>=41.0.0
```

### Dev Dependencies
```txt
pytest>=7.4.0
pytest-cov>=4.1.0
black>=23.0.0
flake8>=6.1.0
mypy>=1.5.0
```

### Commandes Utiles
```bash
# Format code
python -m black .

# Lint
python -m flake8 .

# Type check
python -m mypy .

# Tests avec coverage
python -m pytest --cov=. --cov-report=html
```

---

## 📂 ORGANISATION DES FICHIERS

### Modules Python
```
runtime/
├── __init__.py         # Vide ou imports principaux
├── agent.py            # Agent core
├── server.py           # API FastAPI
├── config.py           # Configuration
└── middleware/
    ├── __init__.py
    ├── logging.py
    ├── worm.py
    ├── audittrail.py
    └── provenance.py
```

### Configuration
```
config/
├── agent.yaml          # Config principale
├── policies.yaml       # RBAC, PII, guardrails
├── retention.yaml      # Durées de conservation
├── provenance.yaml     # Signatures, PROV
└── eval_targets.yaml   # Seuils benchmarks
```

### Tests
```
tests/
├── conftest.py         # Fixtures globales
├── test_agent.py
├── test_tools.py
├── test_memory.py
├── test_compliance_flow.py
└── test_integration_e2e.py
```

---

## 🎯 CHECKLIST CODE REVIEW

Avant chaque commit :

- [ ] **Type hints partout**
- [ ] **Docstrings en français**
- [ ] **Comments en anglais**
- [ ] **Validation inputs stricte**
- [ ] **Gestion erreurs avec fallback**
- [ ] **Tests unitaires créés**
- [ ] **Logs clairs avec emojis**
- [ ] **Pas de secrets en dur**
- [ ] **Conformité patterns existants**
- [ ] **Black + flake8 passent**

---

## 📚 RÉFÉRENCES RAPIDES

### Charger Config
```python
from runtime.config import get_config
config = get_config()
```

### Utiliser Registre Outils
```python
from tools.registry import get_registry
registry = get_registry()
tool = registry.get("python_sandbox")
```

### Logger un Événement
```python
from runtime.middleware.logging import get_logger
logger = get_logger()
logger.log_event("agent.core", "tool.call", "INFO", 
                 conversation_id="conv-123")
```

### Créer Decision Record
```python
from runtime.middleware.audittrail import get_dr_manager
dr_manager = get_dr_manager()
dr = dr_manager.create_dr(
    actor="agent.core",
    task_id="task-123",
    decision="execute_python",
    tools_used=["python_sandbox"]
)
```

---

**Ce guide doit être votre référence pour maintenir la cohérence du code FilAgent.**

*Dernière mise à jour : 1 novembre 2025*
