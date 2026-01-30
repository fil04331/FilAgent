# FilAgent - Features de Conformité

> **Document validé le 2025-01-29**  
> Basé sur l'audit du code source réel, pas sur la documentation existante.

Ce document décrit les capacités de conformité **réellement implémentées** dans FilAgent. Ces features positionnent FilAgent comme une solution enterprise-grade pour les PME québécoises soumises à la Loi 25, PIPEDA, et potentiellement au RGPD.

---

## Table des Matières

1. [WORM Logging avec Merkle Tree](#1-worm-logging-avec-merkle-tree)
2. [Signatures Cryptographiques EdDSA](#2-signatures-cryptographiques-eddsa)
3. [Redaction PII Automatique](#3-redaction-pii-automatique)
4. [Decision Records (Audit Trail)](#4-decision-records-audit-trail)
5. [Provenance Tracking W3C PROV](#5-provenance-tracking-w3c-prov)
6. [Sandbox Python Sécurisé](#6-sandbox-python-sécurisé)
7. [Planification HTN Traçable](#7-planification-htn-traçable)
8. [Serveur MCP avec Gouvernance](#8-serveur-mcp-avec-gouvernance)

---

## 1. WORM Logging avec Merkle Tree

**Fichier source:** `runtime/middleware/worm.py`

### Description

FilAgent implémente un système de journalisation WORM (Write-Once-Read-Many) avec vérification d'intégrité par arbre de Merkle. Ce système garantit que les logs ne peuvent pas être modifiés après écriture, une exigence clé pour la conformité légale.

### Capacités

| Capacité | Implémentation |
|----------|----------------|
| Append-only logging | Thread-safe avec `threading.Lock` |
| Intégrité cryptographique | Arbre de Merkle SHA-256 |
| Checkpoints vérifiables | Hash racine stocké séparément |
| Finalisation légale | Archivage read-only (chmod 0o444) |

### Exemple d'utilisation

```python
from runtime.middleware.worm import get_worm_logger

logger = get_worm_logger()

# Ajouter une entrée (append-only)
logger.append('{"event": "user_login", "timestamp": "2025-01-29T10:00:00Z"}')

# Créer un checkpoint pour vérification future
root_hash = logger.create_checkpoint()
# Retourne: "a3f2b8c9d4e5f6..."

# Vérifier l'intégrité du log
is_valid = logger.verify_integrity()
# Retourne: True si aucune modification

# Finaliser et sceller le log (conformité Loi 25)
finalization_id = logger.finalize_current_log(archive=True)
# Retourne: "FINAL-20250129143022-a3f2b8c9"
```

### Architecture Merkle Tree

```
                    [Root Hash]
                    /          \
            [Hash AB]          [Hash CD]
            /      \            /      \
      [Hash A]  [Hash B]  [Hash C]  [Hash D]
         |         |         |         |
      Log 1     Log 2     Log 3     Log 4
```

Toute modification d'une entrée invalide la chaîne complète jusqu'à la racine.

---

## 2. Signatures Cryptographiques EdDSA

**Fichiers sources:** `runtime/middleware/worm.py`, `runtime/middleware/audittrail.py`

### Description

FilAgent utilise l'algorithme EdDSA (Edwards-curve Digital Signature Algorithm) via la bibliothèque `cryptography` pour signer cryptographiquement les logs finalisés et les Decision Records.

### Pourquoi EdDSA ?

- **Performance:** 3x plus rapide que ECDSA
- **Sécurité:** Résistant aux attaques par canaux auxiliaires
- **Déterminisme:** Signatures reproductibles (pas de nonce aléatoire)
- **Taille:** Signatures compactes (64 bytes)

### Implémentation

```python
from cryptography.hazmat.primitives.asymmetric import ed25519

# Génération de clés (au démarrage du serveur)
private_key = ed25519.Ed25519PrivateKey.generate()
public_key = private_key.public_key()

# Signature d'un digest
sign_data = {
    "finalization_id": "FINAL-20250129-a3f2b8c9",
    "merkle_root": "a3f2b8c9d4e5f6...",
    "timestamp": "2025-01-29T14:30:22Z"
}
sign_bytes = json.dumps(sign_data, sort_keys=True).encode("utf-8")
signature = private_key.sign(sign_bytes)

# Format stocké
record["signature"] = f"ed25519:{signature.hex()}"
```

### Stockage des Clés

Les clés sont stockées dans `provenance/signatures/`:
- `private_key.pem` - Clé privée (à sécuriser en production via HSM/Vault)
- `public_key.pem` - Clé publique pour vérification

---

## 3. Redaction PII Automatique

**Fichier source:** `runtime/middleware/redaction.py`

### Description

FilAgent détecte et masque automatiquement 6 types de données personnelles identifiables (PII) avant logging ou transmission.

### Types de PII Détectés

| Type | Pattern Regex | Exemple |
|------|--------------|---------|
| Email | `[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}` | `jean@example.com` → `[REDACTED]` |
| Téléphone | `(\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})` | `514-555-1234` → `[REDACTED]` |
| NAS/SSN | `\d{3}-\d{2}-\d{4}` | `123-45-6789` → `[REDACTED]` |
| Carte de crédit | `(?:\d{4}[-\s]?){3}\d{4}` | `4111-1111-1111-1111` → `[REDACTED]` |
| Adresse IP | `(?:\d{1,3}\.){3}\d{1,3}` | `192.168.1.1` → `[REDACTED]` |
| Adresse MAC | `([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})` | `00:1A:2B:3C:4D:5E` → `[REDACTED]` |

### Exemple d'utilisation

```python
from runtime.middleware.redaction import get_pii_redactor

redactor = get_pii_redactor()

# Redaction automatique
text = "Contact: jean.dupont@gmail.com, tel: 514-555-1234"
safe_text = redactor.redact(text)
# Retourne: "Contact: [REDACTED], tel: [REDACTED]"

# Scan et log (avec alerting)
result = redactor.scan_and_log(text, context={"source": "user_input"})
# Retourne: {
#   "has_pii": True,
#   "pii_count": 2,
#   "types_found": ["email", "phone"]
# }
```

### Configuration

La configuration se fait via `config/policies.yaml`:

```yaml
policies:
  pii:
    enabled: true
    replacement_pattern: "[REDACTED]"
    fields_to_mask:
      - email
      - phone
      - ssn
      - credit_card
      - ip_address
      - mac_address
    scan_before_logging: true
```

---

## 4. Decision Records (Audit Trail)

**Fichier source:** `runtime/middleware/audittrail.py`

### Description

Chaque décision automatisée de FilAgent génère un Decision Record (DR) signé cryptographiquement, conforme aux exigences de traçabilité de la Loi 25 et de l'AI Act européen.

### Structure d'un Decision Record

```json
{
  "dr_id": "DR-20250129-a3f2b8",
  "ts": "2025-01-29T14:30:22.123456",
  "actor": "filagent.planner",
  "task_id": "task-uuid-1234",
  "policy_version": "policies@0.1.0",
  "model_fingerprint": "llama3:8b@sha256:abc123",
  "prompt_hash": "sha256:def456...",
  "reasoning_markers": ["rule_matched", "confidence_high"],
  "tools_used": ["file_reader", "calculator"],
  "alternatives_considered": ["strategy_A", "strategy_B"],
  "decision": "Exécuter analyse financière",
  "constraints": {
    "max_tokens": 1000,
    "timeout_seconds": 30
  },
  "expected_risk": ["data_exposure_low"],
  "signature": "ed25519:abc123def456..."
}
```

### Exemple d'utilisation

```python
from runtime.middleware.audittrail import get_dr_manager

dr_manager = get_dr_manager()

# Créer un Decision Record signé
dr = dr_manager.create_dr(
    actor="filagent.agent",
    task_id="task-12345",
    decision="Analyser le document fiscal Q3",
    prompt_hash="sha256:abc123...",
    tools_used=["document_analyzer_pme", "calculator"],
    alternatives_considered=["skip_analysis", "partial_analysis"],
    constraints={"max_file_size_mb": 10},
    expected_risk=["pii_exposure_medium"]
)

# Le DR est automatiquement signé et sauvegardé
print(dr.dr_id)  # "DR-20250129-a3f2b8"

# Vérifier la signature
is_valid = dr.verify(dr_manager.public_key)
# Retourne: True
```

### Stockage

Les Decision Records sont stockés dans `logs/decisions/` au format JSON, un fichier par décision.

---

## 5. Provenance Tracking W3C PROV

**Fichier source:** `runtime/middleware/provenance.py`

### Description

FilAgent implémente le standard W3C PROV-JSON pour la traçabilité complète des artefacts générés. Ce standard permet de répondre à la question "D'où vient ce résultat ?" de manière vérifiable.

### Concepts PROV

| Concept | Description | Exemple FilAgent |
|---------|-------------|------------------|
| **Entity** | Artefact (donnée, fichier) | Rapport généré, fichier analysé |
| **Activity** | Processus de transformation | Analyse de document, calcul |
| **Agent** | Responsable de l'activité | FilAgent v1.0, modèle LLM |

### Relations PROV

```
[Entity: rapport.pdf]
      │
      │ wasGeneratedBy
      ▼
[Activity: analyse_fiscale]
      │
      │ wasAssociatedWith
      ▼
[Agent: filagent/v1.0.0]
      │
      │ used
      ▼
[Entity: factures_q3.xlsx]
```

### Exemple d'utilisation

```python
from runtime.middleware.provenance import ProvBuilder

builder = ProvBuilder()

# Définir les entités
builder.add_entity("entity:input", "Factures Q3", {"hash": "sha256:abc..."})
builder.add_entity("entity:output", "Rapport Fiscal", {"hash": "sha256:def..."})

# Définir l'activité
builder.add_activity("activity:analyse", "2025-01-29T10:00:00Z", "2025-01-29T10:05:00Z")

# Définir l'agent
builder.add_agent("agent:filagent", "softwareAgent", version="1.0.0")

# Lier les relations
builder.link_used("activity:analyse", "entity:input")
builder.link_generated("entity:output", "activity:analyse")
builder.link_associated("activity:analyse", "agent:filagent")
builder.link_derived("entity:output", "entity:input")

# Exporter en PROV-JSON
prov_document = builder.to_prov_json()
```

### Sortie PROV-JSON

```json
{
  "entity": {
    "entity:input": {"prov:label": "Factures Q3", "hash": "sha256:abc..."},
    "entity:output": {"prov:label": "Rapport Fiscal", "hash": "sha256:def..."}
  },
  "activity": {
    "activity:analyse": {
      "prov:type": "Activity",
      "prov:startTime": "2025-01-29T10:00:00Z",
      "prov:endTime": "2025-01-29T10:05:00Z"
    }
  },
  "agent": {
    "agent:filagent": {"prov:type": "softwareAgent", "version": "1.0.0"}
  },
  "wasGeneratedBy": [{"prov:entity": "entity:output", "prov:activity": "activity:analyse"}],
  "used": [{"prov:activity": "activity:analyse", "prov:entity": "entity:input"}],
  "wasDerivedFrom": [{"prov:generatedEntity": "entity:output", "prov:usedEntity": "entity:input"}]
}
```

---

## 6. Sandbox Python Sécurisé

**Fichier source:** `tools/python_sandbox.py`

### Description

FilAgent exécute le code Python utilisateur dans un sandbox isolé avec validation AST (Abstract Syntax Tree) et limites de ressources strictes.

### Limites de Ressources

| Ressource | Limite | Justification |
|-----------|--------|---------------|
| Mémoire RAM | 512 MB | Prévient les attaques DoS |
| Temps CPU | 30 secondes | Empêche les boucles infinies |
| Taille fichier | 10 MB | Limite l'écriture disque |
| Fichiers ouverts | 10 | Prévient l'exhaustion de descripteurs |
| Processus fils | 1 | Bloque les fork bombs |

### Opérations Bloquées par AST

**Fonctions dangereuses (35+):**
```python
dangerous_names = {
    'eval', 'exec', 'compile', '__import__', 'open', 'file',
    'input', 'raw_input', 'execfile', 'reload', 'vars', 'globals',
    'locals', 'dir', 'getattr', 'setattr', 'delattr', 'hasattr',
    '__builtins__', '__dict__', '__class__', '__bases__', '__subclasses__'
}
```

**Modules dangereux (15+):**
```python
dangerous_modules = {
    'os', 'sys', 'subprocess', 'multiprocessing', 'threading',
    'socket', 'urllib', 'requests', 'pickle', 'shelve', 'marshal',
    'ctypes', 'imp', 'importlib', 'pty', 'commands'
}
```

### Validation AST

```python
def _validate_ast(self, code: str) -> tuple[bool, Optional[str]]:
    tree = ast.parse(code)
    
    for node in ast.walk(tree):
        # Bloquer les imports dangereux
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in dangerous_modules:
                    return False, f"Import bloqué: {alias.name}"
        
        # Bloquer les appels dangereux
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in dangerous_names:
                    return False, f"Fonction bloquée: {node.func.id}"
    
    return True, None
```

### Exemple de Rejet

```python
# Code soumis par l'utilisateur
code = """
import os
os.system('rm -rf /')
"""

# Résultat
{
    "status": "ERROR",
    "error": "Import of dangerous module blocked: os"
}
```

---

## 7. Planification HTN Traçable

**Fichier source:** `planner/planner.py`

### Description

Le planificateur HTN (Hierarchical Task Network) décompose les requêtes complexes en sous-tâches atomiques avec traçabilité complète pour conformité.

### Stratégies Disponibles

| Stratégie | Description | Cas d'usage |
|-----------|-------------|-------------|
| `RULE_BASED` | Patterns regex prédéfinis | Requêtes standardisées, rapide |
| `LLM_BASED` | Décomposition via LLM | Requêtes complexes, flexible |
| `HYBRID` | Rules d'abord, LLM si confiance < 0.7 | Équilibre performance/flexibilité |

### Traçabilité Intégrée

Chaque planification génère des métadonnées de conformité:

```python
result = planner.plan(
    query="Analyse data.csv, génère stats, crée rapport PDF",
    strategy=PlanningStrategy.HYBRID
)

# Métadonnées de traçabilité
print(result.metadata)
# {
#   "query": "Analyse data.csv...",
#   "strategy": "hybrid",
#   "started_at": "2025-01-29T10:00:00Z",
#   "completed_at": "2025-01-29T10:00:01Z",
#   "validation_passed": True,
#   "llm_response": "..." (si LLM utilisé)
# }
```

### Conformité Documentée

Le module inclut une documentation de conformité explicite:

```python
"""
Conformité:
- Traçabilité de chaque décision de décomposition (Loi 25)
- Justification des choix de planification (AI Act)
- Logs structurés pour auditabilité (RGPD)
"""
```

---

## 8. Serveur MCP avec Gouvernance

**Fichier source:** `mcp_server.py`

### Description

FilAgent expose un serveur MCP (Model Context Protocol) complet avec gouvernance intégrée pour l'intégration avec des clients comme Claude Desktop.

### Outils MCP Disponibles

| Outil | Description | Conformité |
|-------|-------------|------------|
| `analyze_document` | Analyse selon Loi 25/RGPD | Génère Decision Record |
| `calculate_taxes_quebec` | Calcul TPS (5%) + TVQ (9.975%) | Audit automatique |
| `generate_decision_record` | Crée DR signé | EdDSA + PROV |
| `audit_trail` | Consulte les logs WORM | Lecture seule |

### Exemple de Requête MCP

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "calculate_taxes_quebec",
    "arguments": {
      "amount": 100.00,
      "include_gst": true,
      "include_qst": true
    }
  },
  "id": 1
}
```

### Réponse

```json
{
  "jsonrpc": "2.0",
  "result": {
    "subtotal": 100.00,
    "gst": 5.00,
    "qst": 9.98,
    "total": 114.98,
    "calculation_date": "2025-01-29T14:30:22Z"
  },
  "id": 1
}
```

### Logging de Conformité

Chaque appel d'outil est loggé avec les informations de conformité:

```python
def _log_tool_execution(self, tool: str, arguments: ToolArguments) -> None:
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "tool": tool,
        "arguments_hash": hash(json.dumps(arguments, sort_keys=True)),
        "compliance_checked": True,
        "pii_redacted": True
    }
    logger.info(f"Audit log: {json.dumps(log_entry)}")
```

---

## Résumé des Features de Conformité

| Feature | Loi 25 | PIPEDA | RGPD | AI Act |
|---------|--------|--------|------|--------|
| WORM Logging | ✅ | ✅ | ✅ | ✅ |
| Signatures EdDSA | ✅ | ✅ | ✅ | ✅ |
| PII Redaction | ✅ | ✅ | ✅ | - |
| Decision Records | ✅ | - | ✅ | ✅ |
| Provenance W3C | ✅ | - | ✅ | ✅ |
| Sandbox Sécurisé | ✅ | ✅ | ✅ | ✅ |
| HTN Traçable | ✅ | - | ✅ | ✅ |

---

## Contact et Contributions

**Auteur:** Fil - DataML Consulting  
**Philosophie:** Safety by Design  
**Mission:** Éveiller les données dormantes, une PME à la fois

Pour signaler une issue de conformité: ouvrir un ticket avec le label `compliance`.
