# 🚀 Guide Complet FilAgent - Configuration & Capacités Optimales

## 📋 Table des Matières

1. [Vue d'Ensemble](#vue-densemble)
2. [Installation Rapide](#installation-rapide)
3. [Configuration Claude MCP](#configuration-claude-mcp)
4. [Capacités Principales](#capacités-principales)
5. [Tests et Validation](#tests-et-validation)
6. [Cas d'Usage PME Québec](#cas-dusage-pme-québec)
7. [Optimisations Recommandées](#optimisations-recommandées)
8. [Dépannage](#dépannage)

---

## 🎯 Vue d'Ensemble

**FilAgent** est un agent IA local avec gouvernance complète, conçu spécifiquement pour les PME québécoises avec une philosophie **"Safety by Design"**.

### Architecture de Conformité (8 couches)

```
┌─────────────────────────────────────┐
│         Interface Utilisateur        │ ← Gradio UI / API REST
├─────────────────────────────────────┤
│         EventLogger (OTLP)          │ ← Journalisation structurée
├─────────────────────────────────────┤
│         PIIRedactor                 │ ← Masquage automatique PII
├─────────────────────────────────────┤
│         RBACManager                 │ ← Contrôle d'accès
├─────────────────────────────────────┤
│         Agent Core (LLM)            │ ← Raisonnement
├─────────────────────────────────────┤
│         ConstraintsEngine           │ ← Validation sorties
├─────────────────────────────────────┤
│         DRManager (EdDSA)           │ ← Decision Records signés
├─────────────────────────────────────┤
│    ProvenanceTracker (W3C PROV)    │ ← Graphes de traçabilité
├─────────────────────────────────────┤
│      WormLogger (Merkle Tree)      │ ← Logs immuables
└─────────────────────────────────────┘
```

### Conformité Garantie

- ✅ **Loi 25 (Québec)** - Transparence ADM
- ✅ **RGPD (Europe)** - Protection données
- ✅ **AI Act (Europe)** - Traçabilité IA
- ✅ **NIST AI RMF** - Gestion risques
- ✅ **ISO 27001** - Sécurité information

---

## ⚡ Installation Rapide

### Option 1: Script Automatique (Recommandé)

```bash
# 1. Cloner le projet
cd /Users/felixlefebvre/FilAgent

# 2. Lancer l'installation automatique
./setup_filagent_mcp_complete.sh

# 3. Suivre les instructions interactives
```

### Option 2: Installation Manuelle

```bash
# 1. Environnement virtuel
python3 -m venv venv
source venv/bin/activate

# 2. Dépendances
pip install -r requirements.txt
pip install gradio==4.7.1

# 3. Base de données
python -c "from memory.episodic import create_tables; create_tables()"

# 4. Modèle LLM (optionnel)
cd models/weights
wget https://huggingface.co/TheBloke/Llama-3-8B-Instruct-GGUF/resolve/main/llama-3-8b-instruct.Q4_K_M.gguf -O base.gguf
cd ../..
```

---

## 🤖 Configuration Claude MCP

### 1. Configuration Automatique

Le script `setup_filagent_mcp_complete.sh` configure automatiquement MCP.

### 2. Configuration Manuelle

Créer/éditer `~/.claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "filagent": {
      "command": "python3",
      "args": [
        "/Users/felixlefebvre/FilAgent/mcp_server.py"
      ],
      "env": {
        "PYTHONPATH": "/Users/felixlefebvre/FilAgent",
        "FILAGENT_MODE": "mcp",
        "FILAGENT_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

### 3. Redémarrer Claude Desktop

Les outils FilAgent seront disponibles après redémarrage.

---

## 🛠️ Capacités Principales

### 1. Outils de Conformité

#### `filagent_analyze_compliance`
Analyse la conformité selon Loi 25, RGPD ou AI Act
```
Exemple: "Analyse la conformité Loi 25 de notre politique de confidentialité"
```

#### `filagent_generate_decision_record`
Génère un Decision Record signé cryptographiquement
```
Exemple: "Génère un DR pour la décision d'approuver ce crédit"
```

#### `filagent_audit_trail`
Consulte la trace d'audit avec vérification Merkle
```
Exemple: "Montre l'audit trail des 7 derniers jours"
```

#### `filagent_redact_pii`
Masque automatiquement les données personnelles
```
Exemple: "Masque les PII dans ce document"
```

### 2. Outils PME Québec

#### `filagent_calculate_quebec_taxes`
Calcule TPS/TVQ pour facturation
```
Exemple: "Calcule les taxes sur 1000$ avec TPS et TVQ"
```

### 3. Outils Techniques

- **Python Sandbox**: Exécution sécurisée de code
- **File Reader**: Lecture avec masquage PII
- **Calculator**: Calculs mathématiques

---

## 🧪 Tests et Validation

### 1. Diagnostic Complet

```bash
python diagnostic_filagent.py
```

Vérifie:
- ✅ Environnement Python
- ✅ Dépendances
- ✅ Configuration
- ✅ Structure répertoires
- ✅ Base de données
- ✅ Modèle LLM
- ✅ Serveur API
- ✅ Conformité
- ✅ Intégration MCP

### 2. Test des Capacités

```bash
# Démarrer le serveur d'abord
./start_server.sh &

# Lancer les tests
python test_capabilities.py
```

Tests automatiques:
- API Health
- Chat Endpoint
- Compliance Middleware
- WORM Logging
- Provenance Tracking
- Tools Execution
- Memory System
- Quebec Features
- Gradio Interface
- Prometheus Metrics

### 3. Validation Manuelle

```bash
# Test API
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Test"}]}'

# Vérifier les logs
ls -la logs/decisions/
ls -la logs/events/
ls -la logs/digests/
```

---

## 💼 Cas d'Usage PME Québec

### 1. Conformité Loi 25

```python
# Analyse automatique
"Vérifie la conformité Loi 25 de notre formulaire de collecte d'emails"

# Points vérifiés:
- Article 53.1: Transparence décisions automatisées
- Article 3: Minimisation données
- Article 8: Droit d'accès
- Article 23: Conservation limitée
```

### 2. Facturation avec Taxes

```python
# Calcul automatique TPS/TVQ
"Calcule le total avec taxes pour une facture de 2500$"

# Résultat:
- Montant: 2500.00$
- TPS (5%): 125.00$
- TVQ (9.975%): 249.38$
- Total: 2874.38$
```

### 3. Audit Trail pour Vérification

```python
# Export pour auditeur
"Génère le rapport d'audit complet du mois dernier"

# Inclut:
- Decision Records signés
- Graphes de provenance
- Logs WORM vérifiés
- Métriques de conformité
```

### 4. Protection Données Clients

```python
# Masquage automatique
"Prépare ce document pour partage externe en masquant les PII"

# Masque:
- Emails
- Téléphones
- NAS
- Adresses
- Données financières
```

---

## ⚙️ Optimisations Recommandées

### 1. Performance

```yaml
# config/agent.yaml
model:
  name: "llama-3-8b"
  max_workers: 4
  batch_size: 8
  cache_size: 1000
```

### 2. Sécurité

```yaml
# config/policies.yaml
security:
  encryption: "AES-256"
  key_rotation: "monthly"
  audit_level: "verbose"
  pii_detection: "aggressive"
```

### 3. Conformité

```yaml
# config/compliance_rules.yaml
frameworks:
  - loi25:
      articles: [3, 8, 23, 53.1]
      verification: "automatic"
  - rgpd:
      articles: [5, 6, 15, 17, 22]
      verification: "on_demand"
```

### 4. Rétention

```yaml
# config/retention.yaml
retention_policies:
  decision_records: 365  # jours
  audit_logs: 730       # jours
  pii_data: 90         # jours
  provenance: 365      # jours
```

---

## 🔧 Dépannage

### Problème: Serveur API ne démarre pas

```bash
# Vérifier les ports
lsof -i :8000

# Vérifier les logs
tail -f logs/events/*.jsonl

# Mode debug
FILAGENT_LOG_LEVEL=DEBUG python runtime/server.py
```

### Problème: Modèle non trouvé

```bash
# Vérifier le chemin
ls -la models/weights/

# Mode stub (sans modèle)
# FilAgent fonctionne en mode limité
```

### Problème: MCP non reconnu dans Claude

```bash
# Vérifier la config
cat ~/.claude/claude_desktop_config.json

# Redémarrer Claude Desktop
# Quit and restart Claude Desktop app
```

### Problème: Erreurs de dépendances

```bash
# Réinstaller
pip install --upgrade -r requirements.txt

# Vérifier les versions
pip list | grep -E "fastapi|pydantic|cryptography"
```

---

## 📊 Métriques et Monitoring

### Prometheus

```bash
# Accès métriques
curl http://localhost:8000/metrics

# Métriques disponibles:
- filagent_requests_total
- filagent_request_duration_seconds
- filagent_tokens_used_total
- filagent_compliance_checks_total
- filagent_pii_redacted_total
```

### Grafana Dashboard

```bash
# Importer le dashboard
grafana/dashboard_htn.json

# Visualisations:
- Requests/sec
- Token usage
- Compliance checks
- Error rates
- Response times
```

---

## 🚀 Commandes Rapides

```bash
# Tout lancer
./start_all.sh

# API seulement
./start_server.sh

# Interface seulement
./start_ui.sh

# Diagnostic
python diagnostic_filagent.py

# Tests capacités
python test_capabilities.py

# URLs
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
# UI: http://localhost:7860
```

---

## 📞 Support

- **Documentation complète**: DOCUMENTATION_FILAGENT.md
- **Diagnostic**: `python diagnostic_filagent.py`
- **Tests**: `python test_capabilities.py`
- **GitHub**: https://github.com/fil/FilAgent

---

## ✅ Checklist de Déploiement

- [ ] Python 3.10+ installé
- [ ] Environnement virtuel créé
- [ ] Dépendances installées
- [ ] Base de données initialisée
- [ ] Modèle LLM téléchargé (optionnel)
- [ ] Configuration MCP ajoutée
- [ ] Claude Desktop redémarré
- [ ] Serveur API démarré
- [ ] Interface Gradio lancée
- [ ] Tests de validation passés
- [ ] Diagnostic complet OK
- [ ] Métriques Prometheus actives
- [ ] Decision Records générés
- [ ] Logs WORM vérifiés
- [ ] Conformité validée

---

*FilAgent v0.1.0 - Agent IA avec Gouvernance Complète pour PME Québécoises*
*Safety by Design - Conformité Garantie - Données au Québec*
