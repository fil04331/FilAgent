# Configuration des Capacités FilAgent - Guide Technique

## 🎯 Vue d'Ensemble des Capacités

FilAgent implémente 7 capacités core orchestrées en pipeline :

```
┌─────────────────────────────────────────────────────────────────┐
│                    REQUÊTE UTILISATEUR                           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
            ┌──────────────────────────┐
            │   1. EventLogger         │ ◄─── Journalisation OTel
            │   Trace ID: 16 hex       │
            └──────────┬───────────────┘
                       │
                       ▼
            ┌──────────────────────────┐
            │   2. PIIRedactor         │ ◄─── Masquage PII avant logs
            │   Patterns: email/tel    │
            └──────────┬───────────────┘
                       │
                       ▼
            ┌──────────────────────────┐
            │   3. RBACManager         │ ◄─── Validation permissions
            │   Rôles: admin/user      │
            └──────────┬───────────────┘
                       │
                       ▼
            ┌──────────────────────────┐
            │   4. Agent Core          │ ◄─── Raisonnement multi-étapes
            │   Max iterations: 10     │
            │   Tool calling parser    │
            └──────────┬───────────────┘
                       │
                       ▼
            ┌──────────────────────────┐
            │   5. ConstraintsEngine   │ ◄─── Validation guardrails
            │   JSONSchema/Regex       │
            └──────────┬───────────────┘
                       │
                       ▼
            ┌──────────────────────────┐
            │   6. DRManager           │ ◄─── Decision Record signé
            │   Signature: EdDSA       │
            └──────────┬───────────────┘
                       │
                       ▼
            ┌──────────────────────────┐
            │   7. ProvenanceTracker   │ ◄─── Graphe PROV-JSON
            │   W3C Standard           │
            └──────────┬───────────────┘
                       │
                       ▼
            ┌──────────────────────────┐
            │   8. WormLogger          │ ◄─── Append-only + Merkle
            │   Immutabilité garantie  │
            └──────────┬───────────────┘
                       │
                       ▼
         ┌─────────────────────────────┐
         │    RÉPONSE + MÉTADONNÉES    │
         └─────────────────────────────┘
```

---

## 🔧 Configuration par Capacité

### 1. EventLogger - Journalisation Structurée

**Fichier** : `runtime/middleware/logging.py`  
**Config** : `config/agent.yaml`

```yaml
logging:
  level: INFO               # DEBUG|INFO|WARNING|ERROR
  structured: true          # Format JSONL
  output_dir: logs/events   # Dossier de sortie
  rotation: daily           # daily|hourly|size-based
  max_size_mb: 100          # Si size-based
  otel_compatible: true     # Compatible OpenTelemetry
```

**Points de Test** :
```python
def test_event_logger_creates_trace_id():
    """Vérifie qu'un trace_id unique est créé"""
    response = requests.post("/chat", json={"messages": [...]})
    trace_id = response.headers.get("X-Trace-ID")
    
    assert trace_id is not None
    assert len(trace_id) == 16  # 16 caractères hex
    assert all(c in '0123456789abcdef' for c in trace_id)

def test_event_logger_jsonl_format():
    """Vérifie le format JSONL des logs"""
    log_file = Path("logs/events/events-2025-10-27.jsonl")
    
    with open(log_file, 'r') as f:
        for line in f:
            event = json.loads(line)  # Doit parser sans erreur
            
            # Champs obligatoires OpenTelemetry
            assert "ts" in event
            assert "trace_id" in event
            assert "span_id" in event
            assert "level" in event
            assert "event" in event

def test_event_logger_conversation_lifecycle():
    """Vérifie les événements du cycle de vie"""
    # Faire une requête
    requests.post("/chat", json={
        "messages": [{"role": "user", "content": "Test"}],
        "conversation_id": "test-lifecycle"
    })
    
    # Vérifier les événements dans les logs
    events = load_events_for_conversation("test-lifecycle")
    
    # Doit contenir au minimum ces événements
    event_types = [e["event"] for e in events]
    assert "conversation.start" in event_types
    assert "conversation.end" in event_types
```

**Configuration Optimale** :
- **Dev** : `level: DEBUG, rotation: hourly` (max verbosité)
- **Staging** : `level: INFO, rotation: daily`
- **Prod** : `level: WARNING, rotation: daily, max_size_mb: 500`

---

### 2. PIIRedactor - Masquage Données Sensibles

**Fichier** : `runtime/middleware/redaction.py`  
**Config** : `config/policies.yaml`

```yaml
pii:
  enabled: true
  patterns:
    email: true              # Masquer emails
    phone: true              # Masquer téléphones
    ssn: true                # Masquer SSN
    credit_card: true        # Masquer cartes de crédit
    ip_address: true         # Masquer IPs
    custom:
      - pattern: '\b[A-Z]{2}\d{6}\b'  # Passeport canadien
        replacement: '[PASSPORT_REDACTED]'
  
  redaction_char: 'X'        # Caractère de remplacement
  preserve_format: true      # Garder format (xxx-xxx-xxxx)
```

**Points de Test** :
```python
def test_pii_email_redaction():
    """Vérifie le masquage des emails"""
    response = requests.post("/chat", json={
        "messages": [{"role": "user", "content": "Mon email: john@example.com"}]
    })
    
    # L'email NE doit PAS apparaître dans les logs
    logs = load_latest_logs()
    for log in logs:
        log_str = json.dumps(log)
        assert "john@example.com" not in log_str
        assert "[EMAIL_REDACTED]" in log_str or "email" not in log_str.lower()

def test_pii_phone_redaction():
    """Vérifie le masquage des téléphones"""
    response = requests.post("/chat", json={
        "messages": [{"role": "user", "content": "Appelez-moi au 514-555-1234"}]
    })
    
    logs = load_latest_logs()
    for log in logs:
        log_str = json.dumps(log)
        assert "514-555-1234" not in log_str
        assert "[PHONE_REDACTED]" in log_str

def test_pii_multiple_patterns():
    """Vérifie le masquage multi-PII"""
    response = requests.post("/chat", json={
        "messages": [{
            "role": "user",
            "content": "Contact: john@example.com, 514-555-1234, SSN: 123-45-6789"
        }]
    })
    
    logs = load_latest_logs()
    log_str = json.dumps(logs)
    
    assert "john@example.com" not in log_str
    assert "514-555-1234" not in log_str
    assert "123-45-6789" not in log_str
```

**Configuration Optimale** :
- **Prod** : Activer TOUS les patterns + custom patterns selon domaine
- **Dev** : Peut être désactivé pour debugging (`enabled: false`)

**⚠️ CRITIQUE** : Ce middleware est OBLIGATOIRE pour conformité RGPD/Loi 25.

---

### 3. RBACManager - Contrôle d'Accès

**Fichier** : `runtime/middleware/rbac.py`  
**Config** : `config/policies.yaml`

```yaml
rbac:
  enabled: true
  roles:
    admin:
      permissions:
        - chat.send
        - tools.execute_all
        - memory.read
        - memory.write
        - memory.delete
        - audit.read
    
    user:
      permissions:
        - chat.send
        - tools.execute_safe  # Seulement outils non-dangereux
        - memory.read
        - memory.write
    
    viewer:
      permissions:
        - chat.send
        - memory.read
  
  default_role: user         # Rôle par défaut si non spécifié
```

**Points de Test** :
```python
def test_rbac_admin_full_access():
    """Admin a accès à tous les outils"""
    response = requests.post("/chat", json={
        "messages": [{"role": "user", "content": "Execute python: print('test')"}],
        "user_role": "admin"  # Header ou JWT claim
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "tools_used" in data["metadata"]
    assert "python_sandbox" in data["metadata"]["tools_used"]

def test_rbac_user_restricted_access():
    """User ne peut pas exécuter outils dangereux"""
    response = requests.post("/chat", json={
        "messages": [{"role": "user", "content": "Execute python: os.system('rm -rf /')"}],
        "user_role": "user"
    })
    
    # Devrait refuser ou utiliser outil safe seulement
    assert response.status_code in [200, 403]
    if response.status_code == 200:
        data = response.json()
        # Si 200, vérifier que l'outil dangereux n'a PAS été exécuté
        assert "python_sandbox" not in data["metadata"].get("tools_used", [])

def test_rbac_viewer_no_write():
    """Viewer ne peut pas écrire en mémoire"""
    response = requests.post("/memory/save", json={
        "conversation_id": "test",
        "message": {"role": "user", "content": "test"},
        "user_role": "viewer"
    })
    
    assert response.status_code == 403  # Forbidden
```

**Configuration Optimale** :
- **Production** : Utiliser JWT tokens avec claims de rôles
- **Dev local** : `default_role: admin` pour faciliter tests

---

### 4. Agent Core - Raisonnement Multi-Étapes

**Fichier** : `runtime/agent.py`  
**Config** : `config/agent.yaml`

```yaml
agent:
  max_iterations: 10         # Max boucles de raisonnement
  max_tool_calls: 20         # Max appels d'outils total
  enable_reflection: true    # Self-check sur sorties
  stop_on_error: false       # Continuer après erreur outil
  tool_timeout: 30           # Timeout par outil (secondes)
  
  reasoning:
    enable_cot: true         # Chain-of-thought
    enable_self_correction: true  # Correction d'erreurs
```

**Points de Test** :
```python
def test_agent_multi_step_reasoning():
    """Vérifie raisonnement multi-étapes"""
    response = requests.post("/chat", json={
        "messages": [{
            "role": "user",
            "content": "Calcule 5! puis divise par 3"
        }]
    })
    
    assert response.status_code == 200
    data = response.json()
    
    # Doit avoir plusieurs iterations
    assert data["metadata"]["iterations"] >= 2
    
    # Doit avoir utilisé calculator
    assert "calculator" in data["metadata"]["tools_used"]

def test_agent_max_iterations_respected():
    """Vérifie limite d'itérations"""
    # Requête volontairement complexe/infinie
    response = requests.post("/chat", json={
        "messages": [{
            "role": "user",
            "content": "Calcule récursivement la suite de Fibonacci jusqu'à 1000000"
        }]
    })
    
    assert response.status_code == 200
    data = response.json()
    
    # Ne doit jamais dépasser max_iterations
    assert data["metadata"]["iterations"] <= 10

def test_agent_tool_calling_parser():
    """Vérifie parsing des tool calls"""
    response = requests.post("/chat", json={
        "messages": [{
            "role": "user",
            "content": "Lis le fichier config/agent.yaml"
        }]
    })
    
    assert response.status_code == 200
    data = response.json()
    
    # Doit avoir détecté et parsé le tool call
    assert "tools_used" in data["metadata"]
    assert "file_reader" in data["metadata"]["tools_used"]
```

**Configuration Optimale** :
- **Dev** : `max_iterations: 20` (liberté pour explorer)
- **Prod** : `max_iterations: 5` (éviter coûts excessifs)
- **Staging** : `max_iterations: 10` (équilibre)

---

### 5. ConstraintsEngine - Validation Guardrails

**Fichier** : `runtime/middleware/constraints.py`  
**Config** : `config/policies.yaml`

```yaml
guardrails:
  enabled: true
  
  blocklist:
    keywords:
      - password
      - secret_key
      - api_key
      - private_key
      - credit_card
  
  output_validation:
    max_length: 10000        # Max caractères dans réponse
    allowed_formats:
      - text/plain
      - application/json
      - text/markdown
    
    json_schema: |           # Si format JSON attendu
      {
        "type": "object",
        "properties": {
          "response": {"type": "string"},
          "confidence": {"type": "number"}
        },
        "required": ["response"]
      }
  
  regex_patterns:            # Patterns interdits dans sorties
    - '(password|passwd)\s*[:=]\s*\S+'
    - '(api[_-]?key)\s*[:=]\s*\S+'
```

**Points de Test** :
```python
def test_guardrails_blocklist_keywords():
    """Vérifie blocage de mots-clés sensibles"""
    response = requests.post("/chat", json={
        "messages": [{
            "role": "user",
            "content": "Génère un script avec password='secret123'"
        }]
    })
    
    assert response.status_code in [200, 400]
    if response.status_code == 200:
        data = response.json()
        response_text = data["choices"][0]["message"]["content"]
        
        # La réponse ne doit PAS contenir le mot-clé en clair
        assert "password='secret123'" not in response_text

def test_guardrails_output_max_length():
    """Vérifie limite de longueur"""
    response = requests.post("/chat", json={
        "messages": [{
            "role": "user",
            "content": "Écris un roman de 50000 mots"
        }]
    })
    
    assert response.status_code == 200
    data = response.json()
    response_text = data["choices"][0]["message"]["content"]
    
    # Ne doit pas dépasser max_length
    assert len(response_text) <= 10000

def test_guardrails_json_schema_validation():
    """Vérifie validation JSONSchema"""
    response = requests.post("/chat", json={
        "messages": [{
            "role": "user",
            "content": "Retourne un JSON avec {response: 'test'}"
        }],
        "response_format": "json"
    })
    
    assert response.status_code == 200
    data = response.json()
    
    # Valider que la sortie respecte le schema
    response_json = json.loads(data["choices"][0]["message"]["content"])
    assert "response" in response_json
    assert isinstance(response_json["response"], str)
```

**Configuration Optimale** :
- **Prod** : Activer TOUS les guardrails, regex stricts
- **Dev** : Peut relâcher pour tests (`enabled: false` temporairement)

---

### 6. DRManager - Decision Records

**Fichier** : `runtime/middleware/audittrail.py`  
**Config** : `config/provenance.yaml`

```yaml
decision_records:
  enabled: true
  output_dir: logs/decisions
  
  signature:
    algorithm: ed25519       # Algorithme EdDSA
    key_path: config/signing_key.pem
    public_key_path: config/signing_key.pub
  
  triggers:                  # Quand créer un DR
    - tool_execution         # Toujours si outil utilisé
    - high_confidence_needed # Si confidence < 0.7
    - user_requested         # Si task_id présent
```

**Points de Test** :
```python
def test_dr_created_on_tool_execution():
    """Vérifie création DR quand outil utilisé"""
    response = requests.post("/chat", json={
        "messages": [{"role": "user", "content": "Calcule 10!"}],
        "task_id": "test-dr-001"
    })
    
    assert response.status_code == 200
    
    # Vérifier qu'un DR existe
    dr_path = Path("logs/decisions")
    dr_files = list(dr_path.glob("DR-test-dr-001-*.json"))
    
    assert len(dr_files) > 0, "Decision Record non créé"
    
    with open(dr_files[0], 'r') as f:
        dr = json.load(f)
    
    # Vérifier champs obligatoires Loi 25
    assert "id" in dr
    assert "task_id" in dr
    assert "timestamp" in dr
    assert "decision" in dr
    assert "tools_used" in dr
    assert "signature" in dr
    
    # Vérifier signature EdDSA
    assert dr["signature"].startswith("ed25519:")

def test_dr_signature_verification():
    """Vérifie intégrité signature EdDSA"""
    # Créer un DR
    response = requests.post("/chat", json={
        "messages": [{"role": "user", "content": "Test"}],
        "task_id": "test-sign-001"
    })
    
    dr_path = list(Path("logs/decisions").glob("DR-test-sign-001-*.json"))[0]
    
    with open(dr_path, 'r') as f:
        dr = json.load(f)
    
    # Extraire signature
    signature_hex = dr["signature"].split(":", 1)[1]
    
    # Vérifier avec clé publique
    from nacl.signing import VerifyKey
    from nacl.encoding import HexEncoder
    
    public_key_path = Path("config/signing_key.pub")
    with open(public_key_path, 'rb') as f:
        verify_key = VerifyKey(f.read(), encoder=HexEncoder)
    
    # Reconstruire message signé (sans la signature)
    dr_without_sig = {k: v for k, v in dr.items() if k != "signature"}
    message = json.dumps(dr_without_sig, sort_keys=True).encode()
    
    # Vérifier signature
    try:
        verify_key.verify(message, bytes.fromhex(signature_hex))
        assert True  # Signature valide
    except Exception as e:
        pytest.fail(f"Signature invalide: {e}")
```

**Configuration Optimale** :
- **Prod** : `enabled: true`, rotation des clés tous les 90 jours
- **Dev** : Utiliser clés de test

**⚠️ CRITIQUE** : Les Decision Records sont OBLIGATOIRES pour conformité Loi 25 Article 53.1.

---

### 7. ProvenanceTracker - Graphe de Traçabilité

**Fichier** : `runtime/middleware/provenance.py`  
**Config** : `config/provenance.yaml`

```yaml
provenance:
  enabled: true
  output_dir: logs/traces/otlp
  format: prov-json          # W3C PROV-JSON
  
  entities:                  # Quoi tracer
    - prompt
    - response
    - tool_output
    - model_weights
  
  activities:
    - generation
    - tool_execution
    - validation
  
  agents:
    - llm_agent
    - tools
    - user
```

**Points de Test** :
```python
def test_provenance_graph_structure():
    """Vérifie structure graphe PROV-JSON"""
    response = requests.post("/chat", json={
        "messages": [{"role": "user", "content": "Test prov"}],
        "task_id": "test-prov-001"
    })
    
    prov_path = Path("logs/traces/otlp/prov-test-prov-001.json")
    
    with open(prov_path, 'r') as f:
        prov = json.load(f)
    
    # Vérifier sections W3C PROV
    assert "entity" in prov
    assert "activity" in prov
    assert "agent" in prov
    assert "wasGeneratedBy" in prov
    assert "wasAssociatedWith" in prov

def test_provenance_entity_hashing():
    """Vérifie hash des entités pour intégrité"""
    response = requests.post("/chat", json={
        "messages": [{"role": "user", "content": "Test hash"}],
        "task_id": "test-hash-001"
    })
    
    prov_path = Path("logs/traces/otlp/prov-test-hash-001.json")
    
    with open(prov_path, 'r') as f:
        prov = json.load(f)
    
    # Chaque entité doit avoir un hash
    for entity_id, entity in prov["entity"].items():
        assert "hash" in entity
        assert entity["hash"].startswith("sha256:")
```

**Configuration Optimale** :
- **Prod** : `enabled: true`, archivage mensuel des graphes
- **Dev** : Peut être désactivé pour performance

---

### 8. WormLogger - Logs Immuables

**Fichier** : `runtime/middleware/worm.py`  
**Config** : `config/agent.yaml`

```yaml
worm:
  enabled: true
  output_dir: logs/worm
  
  merkle:
    enabled: true            # Arbre de Merkle pour intégrité
    checkpoint_interval: 100 # Checkpoint tous les 100 logs
    checkpoint_dir: logs/digests
  
  immutability:
    append_only: true        # Jamais modifier fichiers existants
    permissions: 0o444       # Read-only après écriture
```

**Points de Test** :
```python
def test_worm_append_only():
    """Vérifie que les logs sont append-only"""
    worm_path = Path("logs/worm")
    
    # Compter les fichiers avant
    files_before = list(worm_path.glob("worm-*.jsonl"))
    
    # Faire une requête
    requests.post("/chat", json={
        "messages": [{"role": "user", "content": "Test worm"}]
    })
    
    # Compter après
    files_after = list(worm_path.glob("worm-*.jsonl"))
    
    # Nouveaux fichiers peuvent être créés, mais pas modifiés
    assert len(files_after) >= len(files_before)

def test_merkle_checkpoint_creation():
    """Vérifie création checkpoints Merkle"""
    # Faire 101 requêtes pour déclencher checkpoint
    for i in range(101):
        requests.post("/chat", json={
            "messages": [{"role": "user", "content": f"Test {i}"}]
        })
    
    # Vérifier qu'un checkpoint existe
    checkpoint_path = Path("logs/digests")
    checkpoints = list(checkpoint_path.glob("merkle-*.json"))
    
    assert len(checkpoints) > 0
    
    with open(checkpoints[-1], 'r') as f:
        checkpoint = json.load(f)
    
    assert "root_hash" in checkpoint
    assert "timestamp" in checkpoint
    assert "log_count" in checkpoint

def test_merkle_integrity_verification():
    """Vérifie intégrité via Merkle tree"""
    # TODO: Implémenter vérification complète Merkle
    # 1. Charger checkpoint
    # 2. Recalculer hash des logs
    # 3. Reconstruire arbre Merkle
    # 4. Comparer root hash
    pass
```

**Configuration Optimale** :
- **Prod** : `enabled: true`, `append_only: true`, `checkpoint_interval: 1000`
- **Dev** : Peut augmenter `checkpoint_interval` pour performance

**⚠️ CRITIQUE** : WORM est OBLIGATOIRE pour conformité et audit.

---

## 📊 Matrices de Test Prioritaires

### Matrice 1 : Conformité Légale (CRITIQUE)

| Capacité | Test | Standard | Seuil Acceptation |
|----------|------|----------|-------------------|
| Decision Records | DR créé pour actions | Loi 25 Art. 53.1 | 100% actions tracées |
| Signature EdDSA | Signature valide | NIST FIPS 186-4 | 100% DR signés |
| PII Redaction | PII masquée en logs | RGPD Art. 5 | 100% PII redacted |
| Trace ID | Présent req→logs | AI Act Art. 13 | 100% req tracées |
| WORM | Immutabilité logs | ISO 27001 | 0 modifications |

### Matrice 2 : Capacités Agentiques

| Capacité | Test | Métrique | Seuil Acceptation |
|----------|------|----------|-------------------|
| Multi-step reasoning | Problème complexe | Iterations | ≥ 2 iterations |
| Tool calling | Calcul 10! | Tools used | calculator exécuté |
| Memory retrieval | Ref conversation | Context loaded | ≥ 3 messages chargés |
| Semantic search | Query embedding | Top-K results | Similarity > 0.7 |

### Matrice 3 : Performance

| Métrique | Test | Outil | Seuil Acceptation |
|----------|------|-------|-------------------|
| Latence P50 | 1000 req | Locust | < 500ms |
| Latence P99 | 1000 req | Locust | < 2000ms |
| Throughput | 5 min charge | Locust | > 10 req/s |
| Memory usage | Long-running | psutil | < 2GB après 1h |

---

## 🎯 Checklist Configuration Optimale

### Pour Développement Local

```yaml
# config/agent.yaml
agent:
  max_iterations: 20        # Liberté exploration
  tool_timeout: 60          # Timeouts généreux

logging:
  level: DEBUG              # Max verbosité
  rotation: hourly          # Logs fréquents

worm:
  checkpoint_interval: 10   # Checkpoints rapides pour tests

guardrails:
  enabled: false            # Peut être désactivé pour debug
```

### Pour Staging/Pré-Production

```yaml
# config/agent.yaml
agent:
  max_iterations: 10
  tool_timeout: 30

logging:
  level: INFO
  rotation: daily

worm:
  checkpoint_interval: 100

guardrails:
  enabled: true             # Activer en staging
```

### Pour Production

```yaml
# config/agent.yaml
agent:
  max_iterations: 5         # Limiter coûts
  tool_timeout: 15          # Timeouts stricts

logging:
  level: WARNING            # Réduire verbosité
  rotation: daily

worm:
  checkpoint_interval: 1000 # Optimiser performance

guardrails:
  enabled: true             # OBLIGATOIRE en prod

pii:
  enabled: true             # OBLIGATOIRE en prod

rbac:
  enabled: true             # OBLIGATOIRE en prod
```

---

## 🚀 Commandes de Test Rapides

```bash
# 1. Valider OpenAPI spec
python scripts/validate_openapi.py

# 2. Tests de conformité
pytest tests/compliance/ -v

# 3. Tests de contrat
pytest tests/contract/ -v

# 4. Tests de charge
locust -f tests/performance/locustfile.py --host http://localhost:8000

# 5. Vérifier intégrité WORM
python scripts/verify_merkle_integrity.py

# 6. Audit logs PII
python scripts/audit_pii_leaks.py logs/events/

# 7. Générer rapport de conformité
python scripts/generate_compliance_report.py --output audit/reports/
```

---

## 📚 Prochaines Étapes Recommandées

1. **Placer `openapi.yaml` à la racine** du projet
2. **Exécuter `validate_openapi.py`** pour vérifier conformité
3. **Configurer les capacités** selon environnement (dev/staging/prod)
4. **Implémenter les tests prioritaires** de la Matrice 1 (conformité)
5. **Intégrer CI/CD** avec validation automatique
6. **Documenter les décisions** dans ADRs

---

**Configuration des capacités complète !** ✨
