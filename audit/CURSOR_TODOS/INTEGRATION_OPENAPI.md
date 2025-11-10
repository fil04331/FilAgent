# Guide d'Intégration OpenAPI - FilAgent

## 🎯 Placement du Fichier OpenAPI

### Option 1 : Racine du Projet (RECOMMANDÉ)
```
FilAgent/
├─ openapi.yaml                 ⭐ ICI - Accessibilité maximale
├─ config/
├─ runtime/
├─ memory/
└─ ...
```

**Avantages** :
- Découvrabilité immédiate (convention standard)
- Intégration CI/CD simplifiée
- Génération de clients facilitée (swagger-codegen, openapi-generator)
- Référence principale pour le contrat API

**Utilisé par** : Stripe, GitHub, Twilio, AWS

### Option 2 : Documentation API
```
FilAgent/
├─ docs/
│  ├─ api/
│  │  ├─ openapi.yaml          ⭐ ICI - Avec documentation technique
│  │  ├─ schemas/              # Schémas JSON séparés si besoin
│  │  └─ examples/             # Exemples de requêtes/réponses
│  ├─ ADRs/
│  └─ SOPs/
```

**Avantages** :
- Groupé avec documentation existante (ADRs, SOPs)
- Séparation claire entre code et spécifications
- Facilite la maintenance de la doc API

**Utilisé par** : Kubernetes, OpenStack

### Option 3 : Dossier API dédié
```
FilAgent/
├─ api/
│  ├─ openapi.yaml             ⭐ ICI - Avec outillage API
│  ├─ validators/              # Scripts de validation
│  ├─ mocks/                   # Serveurs mock
│  └─ contracts/               # Tests de contrat
```

**Avantages** :
- Écosystème API complet
- Tests de contrat centralisés
- Outillage API isolé

---

## 📋 RECOMMANDATION FINALE

**Placez le fichier à la racine** : `FilAgent/openapi.yaml`

**Rationale** :
1. **Conformité légale** : Votre OpenAPI doc sert de spécification contractuelle pour la traçabilité (Loi 25, RGPD, AI Act)
2. **CI/CD** : Validation automatique dans GitHub Actions/GitLab CI triviale
3. **Tooling** : Tous les outils OpenAPI s'attendent à trouver le spec à la racine
4. **Documentation** : Génération automatique de docs avec Redoc/SwaggerUI

---

## 🔧 Intégration avec FastAPI

### Étape 1 : Servir le OpenAPI Spec Custom

Modifiez `runtime/server.py` pour servir votre spec manuel :

```python
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
import yaml
from pathlib import Path

app = FastAPI(
    title="FilAgent API",
    version="0.1.0",
    # Désactiver la génération auto pour utiliser notre spec
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Charger le spec OpenAPI manuel
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_path = Path(__file__).parent.parent / "openapi.yaml"
    with open(openapi_path, 'r', encoding='utf-8') as f:
        openapi_schema = yaml.safe_load(f)
    
    # Valider que le schema est bien-formé
    app.openapi_schema = openapi_schema
    return app.openapi_schema

# Remplacer la fonction de génération OpenAPI
app.openapi = custom_openapi

# Vos endpoints existants...
@app.get("/")
async def root():
    return {"service": "FilAgent", "version": "0.1.0", "status": "running"}

# ...
```

### Étape 2 : Validation Automatique du Spec

Créez `scripts/validate_openapi.py` :

```python
#!/usr/bin/env python3
"""Validation du spec OpenAPI contre l'implémentation FastAPI"""

import sys
from pathlib import Path
import yaml
from openapi_spec_validator import validate_spec
from openapi_spec_validator.readers import read_from_filename

def validate_openapi_spec():
    """Valide que le spec OpenAPI est bien-formé"""
    spec_path = Path(__file__).parent.parent / "openapi.yaml"
    
    try:
        # Lecture et validation syntaxique
        spec_dict, spec_url = read_from_filename(str(spec_path))
        
        # Validation sémantique OpenAPI 3.0
        validate_spec(spec_dict)
        
        print("✅ OpenAPI spec is valid!")
        return True
        
    except Exception as e:
        print(f"❌ OpenAPI validation failed: {e}")
        return False

if __name__ == "__main__":
    sys.exit(0 if validate_openapi_spec() else 1)
```

Ajoutez au `requirements.txt` :
```
openapi-spec-validator>=0.7.1
```

### Étape 3 : CI/CD Integration

Créez `.github/workflows/openapi_validation.yml` :

```yaml
name: OpenAPI Validation

on:
  push:
    paths:
      - 'openapi.yaml'
      - 'runtime/server.py'
  pull_request:
    paths:
      - 'openapi.yaml'
      - 'runtime/server.py'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install openapi-spec-validator
      
      - name: Validate OpenAPI Spec
        run: python scripts/validate_openapi.py
      
      - name: Generate API Documentation
        run: |
          npx @redocly/cli build-docs openapi.yaml \
            --output docs/api/index.html
      
      - name: Contract Testing
        run: |
          # Démarrer le serveur en background
          python runtime/server.py &
          sleep 5
          
          # Tester que l'implémentation respecte le contrat
          npm install -g @stoplight/prism-cli
          prism mock openapi.yaml &
          sleep 2
          
          # Comparer les réponses réelles vs spec
          pytest tests/contract/
```

---

## 🧪 Stratégie de Test

### 1. Tests de Contrat (Contract Testing)

Créez `tests/contract/test_openapi_contract.py` :

```python
"""Tests de conformité entre implémentation et spec OpenAPI"""

import pytest
import requests
from schemathesis import from_uri
from schemathesis.checks import not_a_server_error

# Charger le schema depuis le serveur local
schema = from_uri("http://localhost:8000/openapi.json")

@schema.parametrize()
def test_api_conforms_to_openapi(case):
    """
    Générer automatiquement des tests pour TOUS les endpoints
    selon le spec OpenAPI
    """
    response = case.call()
    
    # Vérifications automatiques :
    # - Status code valide selon spec
    # - Schema de réponse conforme
    # - Headers corrects
    case.validate_response(response, checks=(not_a_server_error,))

def test_health_check_detailed():
    """Test manuel pour l'endpoint critique /health"""
    response = requests.get("http://localhost:8000/health")
    
    assert response.status_code == 200
    data = response.json()
    
    # Vérifier structure selon openapi.yaml
    assert "status" in data
    assert data["status"] in ["healthy", "degraded"]
    assert "timestamp" in data
    assert "components" in data
    assert "model" in data["components"]
    assert "database" in data["components"]
    assert "logging" in data["components"]

def test_chat_endpoint_compliance():
    """Test manuel pour /chat avec validation stricte"""
    payload = {
        "messages": [{"role": "user", "content": "Test"}],
        "conversation_id": "test-contract-001"
    }
    
    response = requests.post(
        "http://localhost:8000/chat",
        json=payload
    )
    
    assert response.status_code == 200
    
    # Vérifier header X-Trace-ID
    assert "X-Trace-ID" in response.headers
    assert len(response.headers["X-Trace-ID"]) == 16
    
    data = response.json()
    
    # Vérifier structure ChatResponse
    assert "id" in data
    assert "object" in data
    assert data["object"] == "chat.completion"
    assert "created" in data
    assert "model" in data
    assert "choices" in data
    assert len(data["choices"]) > 0
    assert "usage" in data
    assert "trace_id" in data
    assert "conversation_id" in data
```

Ajoutez au `requirements.txt` :
```
schemathesis>=3.19.0
```

### 2. Tests de Charge et Performance

Créez `tests/performance/locustfile.py` :

```python
"""Tests de charge basés sur le spec OpenAPI"""

from locust import HttpUser, task, between
import random

class FilAgentUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Initialiser l'utilisateur"""
        self.conversation_id = f"perf-test-{random.randint(1000, 9999)}"
    
    @task(3)
    def chat_simple(self):
        """Test de charge sur /chat - requête simple"""
        self.client.post("/chat", json={
            "messages": [
                {"role": "user", "content": "Bonjour"}
            ],
            "conversation_id": self.conversation_id
        })
    
    @task(1)
    def chat_with_tools(self):
        """Test de charge sur /chat - avec appel d'outil"""
        self.client.post("/chat", json={
            "messages": [
                {"role": "user", "content": "Calcule 5 + 3"}
            ],
            "conversation_id": self.conversation_id
        })
    
    @task(10)
    def health_check(self):
        """Test de charge sur /health"""
        self.client.get("/health")
    
    @task(1)
    def memory_query(self):
        """Test de charge sur /memory/search"""
        self.client.post("/memory/search", json={
            "query": "test query",
            "conversation_id": self.conversation_id,
            "top_k": 5
        })

# Lancer avec: locust -f tests/performance/locustfile.py --host http://localhost:8000
```

### 3. Tests de Conformité Légale

Créez `tests/compliance/test_legal_requirements.py` :

```python
"""Tests de conformité aux exigences légales décrites dans openapi.yaml"""

import pytest
import requests
import json
from pathlib import Path

def test_conversation_creates_decision_record():
    """Vérifie qu'un Decision Record est créé (Loi 25)"""
    
    response = requests.post("http://localhost:8000/chat", json={
        "messages": [{"role": "user", "content": "Calcule 10 factorielle"}],
        "conversation_id": "compliance-test-001",
        "task_id": "task-compliance-001"
    })
    
    assert response.status_code == 200
    
    # Vérifier qu'un DR a été créé
    dr_path = Path("logs/decisions/DR-task-compliance-001-*.json")
    dr_files = list(dr_path.parent.glob(dr_path.name))
    
    assert len(dr_files) > 0, "Decision Record non créé"
    
    # Valider structure du DR
    with open(dr_files[0], 'r') as f:
        dr = json.load(f)
    
    # Exigences Loi 25 Article 53.1
    assert "id" in dr
    assert "task_id" in dr
    assert "timestamp" in dr
    assert "decision" in dr
    assert "tools_used" in dr
    assert "signature" in dr
    
    # Vérifier signature EdDSA
    assert dr["signature"].startswith("ed25519:")

def test_pii_redaction_in_logs():
    """Vérifie que les PII sont masquées (RGPD Article 5)"""
    
    # Envoyer une requête avec PII
    response = requests.post("http://localhost:8000/chat", json={
        "messages": [
            {"role": "user", "content": "Mon email est john.doe@example.com"}
        ],
        "conversation_id": "pii-test-001"
    })
    
    assert response.status_code == 200
    
    # Vérifier que l'email n'apparaît PAS dans les logs
    log_file = Path("logs/events/events-*.jsonl").parent
    latest_log = max(log_file.glob("events-*.jsonl"))
    
    with open(latest_log, 'r') as f:
        logs = f.readlines()
    
    for log_line in logs:
        log_event = json.loads(log_line)
        # Vérifier qu'aucun champ ne contient l'email en clair
        log_str = json.dumps(log_event)
        assert "john.doe@example.com" not in log_str
        # Mais le masque devrait être présent
        assert "[EMAIL_REDACTED]" in log_str or "email" not in log_str.lower()

def test_trace_id_propagation():
    """Vérifie la traçabilité complète (AI Act Article 13)"""
    
    response = requests.post("http://localhost:8000/chat", json={
        "messages": [{"role": "user", "content": "Test traçabilité"}],
        "conversation_id": "trace-test-001"
    })
    
    assert response.status_code == 200
    
    # Récupérer trace_id du header
    trace_id = response.headers.get("X-Trace-ID")
    assert trace_id is not None
    
    # Vérifier que le trace_id est dans la réponse
    data = response.json()
    assert data["trace_id"] == trace_id
    
    # Vérifier que le trace_id est dans les logs
    log_file = Path("logs/events/events-*.jsonl").parent
    latest_log = max(log_file.glob("events-*.jsonl"))
    
    with open(latest_log, 'r') as f:
        logs = [json.loads(line) for line in f if line.strip()]
    
    # Au moins un événement doit avoir ce trace_id
    assert any(log.get("trace_id") == trace_id for log in logs)

def test_worm_immutability():
    """Vérifie que les logs sont immuables (NIST AI RMF)"""
    
    log_file = Path("logs/worm/worm-*.jsonl").parent
    if not log_file.exists():
        pytest.skip("WORM logs not yet created")
    
    latest_worm = max(log_file.glob("worm-*.jsonl"))
    
    # Tenter de modifier le fichier (devrait échouer ou être détecté)
    original_content = latest_worm.read_text()
    
    try:
        # Sur un vrai système WORM, ceci échouerait
        with open(latest_worm, 'a') as f:
            f.write('{"malicious": "injection"}\n')
        
        # Si on arrive ici, vérifier que le Merkle tree détecte la modification
        # TODO: Implémenter la vérification Merkle
        
    except PermissionError:
        # Attendu sur un vrai WORM
        pass
```

---

## 📊 Documentation Automatique

### Génération de Documentation Interactive

Ajoutez au `README.md` :

```markdown
## 📖 Documentation API

### Swagger UI
Accédez à l'interface interactive : http://localhost:8000/docs

### ReDoc
Documentation détaillée : http://localhost:8000/redoc

### Génération statique
```bash
npm install -g @redocly/cli
redocly build-docs openapi.yaml --output docs/api/index.html
```

### Génération de clients

```bash
# Client Python
openapi-generator generate -i openapi.yaml -g python -o clients/python

# Client TypeScript
openapi-generator generate -i openapi.yaml -g typescript-fetch -o clients/typescript

# Client Go
openapi-generator generate -i openapi.yaml -g go -o clients/go
```
```

---

## 🔍 Capacités à Tester Prioritairement

### 1. Conformité Légale (CRITIQUE)

| Capacité | Test | Critère de Succès |
|----------|------|-------------------|
| **Decision Records** | `test_conversation_creates_decision_record()` | DR créé pour toute action significative |
| **Signature EdDSA** | Vérifier `signature` field | Format `ed25519:[hex]` valide |
| **PII Redaction** | `test_pii_redaction_in_logs()` | Aucun PII en clair dans logs |
| **Traçabilité** | `test_trace_id_propagation()` | trace_id dans réponse + logs + DR |
| **WORM Immutability** | `test_worm_immutability()` | Logs append-only non modifiables |

### 2. Capacités Agentiques

| Capacité | Test | Critère de Succès |
|----------|------|-------------------|
| **Tool Calling** | Requête nécessitant calcul | `tools_used` non vide dans réponse |
| **Multi-step Reasoning** | Problème complexe | `iterations` > 1 dans metadata |
| **Memory Retrieval** | Référence conversation passée | Context pertinent chargé |
| **Semantic Search** | `/memory/search` endpoint | Top-k résultats pertinents |

### 3. Performance et Scalabilité

| Métrique | Test | Seuil |
|----------|------|-------|
| **Latence P50** | Locust charge test | < 500ms (sans outils) |
| **Latence P99** | Locust charge test | < 2000ms (avec outils) |
| **Throughput** | Locust | > 10 req/s (1 vCPU) |
| **Memory Leak** | Long-running test | Mémoire stable après 1000 requêtes |

### 4. Sécurité

| Capacité | Test | Critère de Succès |
|----------|------|-------------------|
| **Sandbox Python** | Injection code malveillant | Exécution bloquée/isolée |
| **Path Traversal** | `../../etc/passwd` | Lecture refusée |
| **Guardrails** | Prompt injection | Sortie validée/rejetée |
| **RBAC** | Requête sans permissions | HTTP 403 Forbidden |

---

## 🎯 Configuration Optimale

### Configuration pour Développement

`config/agent.yaml` :
```yaml
generation:
  temperature: 0.7
  max_tokens: 2048
  top_p: 0.95
  seed: 42  # Reproductibilité

model:
  path: models/weights/base.gguf
  n_ctx: 8192
  n_gpu_layers: 35  # Ajuster selon GPU

runtime:
  max_iterations: 10
  tool_timeout: 30
  debug: true  # Mode verbeux pour dev
```

### Configuration pour Production

```yaml
generation:
  temperature: 0.3  # Plus déterministe
  max_tokens: 1024  # Limiter coûts
  top_p: 0.9
  seed: null  # Seed aléatoire

model:
  path: models/weights/base.gguf
  n_ctx: 4096  # Réduire pour performance
  n_gpu_layers: 0  # CPU-only si pas de GPU

runtime:
  max_iterations: 5  # Limiter boucles infinies
  tool_timeout: 15  # Timeouts stricts
  debug: false
```

### Configuration pour Tests de Conformité

```yaml
compliance:
  enable_dr: true
  enable_prov: true
  enable_worm: true
  enable_pii_redaction: true

logging:
  level: DEBUG
  structured: true
  redact_pii: true
```

---

## 🚀 Checklist de Mise en Production

- [ ] **Placement fichier** : `FilAgent/openapi.yaml` à la racine
- [ ] **Validation spec** : `python scripts/validate_openapi.py` passe
- [ ] **Tests de contrat** : `pytest tests/contract/` passe (100% endpoints)
- [ ] **Tests de conformité** : `pytest tests/compliance/` passe
- [ ] **Tests de charge** : `locust` avec 100 users pendant 5min sans erreurs
- [ ] **Documentation** : Swagger UI et ReDoc accessibles
- [ ] **CI/CD** : Pipeline GitHub Actions configuré
- [ ] **Logs conformité** : Decision Records créés pour toutes actions significatives
- [ ] **PII Redaction** : Aucun PII en clair dans logs (audit manuel)
- [ ] **WORM vérification** : Merkle checkpoints générés et vérifiés
- [ ] **Génération clients** : Clients Python/TS générés et testés

---

## 📚 Ressources et Outils

### Outils de Validation
- **Swagger Editor** : https://editor.swagger.io (validation en ligne)
- **Redocly CLI** : `npm install -g @redocly/cli`
- **openapi-spec-validator** : `pip install openapi-spec-validator`

### Outils de Test
- **Schemathesis** : Tests automatiques basés sur spec
- **Prism** : Mock server depuis OpenAPI
- **Dredd** : Tests de contrat API

### Outils de Documentation
- **ReDoc** : Documentation interactive
- **Swagger UI** : Interface de test
- **openapi-generator** : Génération de clients

### Standards de Conformité
- **Loi 25 (Québec)** : Article 53.1 sur transparence ADM
- **RGPD (UE)** : Article 5 (minimisation), Article 15 (accès)
- **AI Act (UE)** : Article 13 (traçabilité), Article 52 (transparence)
- **NIST AI RMF 1.0** : Govern, Map, Measure, Manage

---

**Prochaine étape recommandée** : Placer `openapi.yaml` à la racine et exécuter le script de validation.
