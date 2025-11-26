# Guide de Déploiement FilAgent - Production

**Version**: 1.0.0
**Dernière mise à jour**: 2025-11-16
**Auteur**: Équipe FilAgent

---

## Table des Matières

1. [Vue d'ensemble](#vue-densemble)
2. [Prérequis système](#prérequis-système)
3. [Configuration Backend LLM](#configuration-backend-llm)
4. [Déploiement avec Perplexity API](#déploiement-avec-perplexity-api)
5. [Déploiement avec Modèle Local](#déploiement-avec-modèle-local)
6. [Configuration de Production](#configuration-de-production)
7. [Monitoring et Observabilité](#monitoring-et-observabilité)
8. [Résolution de Problèmes](#résolution-de-problèmes)
9. [Checklist de Déploiement](#checklist-de-déploiement)

---

## Vue d'ensemble

FilAgent peut être déployé avec deux backends LLM différents selon vos exigences de confidentialité, performance et infrastructure :

| Critère | Perplexity API | Modèle Local |
|---------|----------------|--------------|
| **Confidentialité** | Données envoyées au cloud | 100% local |
| **Setup** | Rapide (< 5 min) | Moyen (téléchargement requis) |
| **Infrastructure** | Minimale | GPU recommandé |
| **Coûts** | Pay-per-use | Infrastructure uniquement |
| **Recherche Web** | Oui (modèles Sonar) | Non |
| **Conformité** | GDPR/Loi 25 (avec middlewares) | GDPR/Loi 25 (isolation totale) |

**Configuration actuelle détectée** : Perplexity API (backend fonctionnel)

---

## Prérequis système

### Minimum

- **OS** : Linux, macOS, Windows (WSL2 recommandé)
- **Python** : 3.10 ou supérieur (3.11 recommandé)
- **RAM** : 4 GB minimum
- **Stockage** : 2 GB (sans modèle local), 10+ GB (avec modèle local)
- **Réseau** : Connexion stable pour Perplexity API

### Recommandé (Production)

- **OS** : Linux (Ubuntu 22.04 LTS ou plus récent)
- **Python** : 3.11.13
- **RAM** : 16 GB
- **CPU** : 4+ cœurs
- **GPU** : NVIDIA avec 8+ GB VRAM (pour modèle local)
- **Stockage** : SSD 50+ GB
- **Réseau** : Connexion redondante

---

## Configuration Backend LLM

Le choix du backend se configure dans le fichier `.env` :

```bash
# Backend selection
LLM_BACKEND=perplexity  # ou "llama.cpp" pour modèle local
```

### Variables d'environnement communes

```bash
# Serveur
SERVER_HOST=0.0.0.0
SERVER_PORT=8000

# Compliance
ENABLE_AUDIT_TRAIL=true
ENABLE_PII_REDACTION=true
ENABLE_WORM_LOGGING=true
```

---

## Déploiement avec Perplexity API

### 1. Obtenir une Clé API

1. Créer un compte sur [Perplexity AI](https://www.perplexity.ai)
2. Accéder aux paramètres API : https://www.perplexity.ai/settings/api
3. Générer une nouvelle clé API
4. Copier la clé (commence par `pplx-`)

### 2. Configuration

Créer ou éditer `.env` :

```bash
# Backend LLM
LLM_BACKEND=perplexity

# Perplexity Configuration
PERPLEXITY_API_KEY=pplx-votre-cle-api-ici
PERPLEXITY_MODEL=llama-3.1-sonar-large-128k-online

# Modèles disponibles :
# Sonar (avec recherche web) :
#   - llama-3.1-sonar-small-128k-online   (rapide, économique)
#   - llama-3.1-sonar-large-128k-online   (équilibré - RECOMMANDÉ)
#   - llama-3.1-sonar-huge-128k-online    (meilleure qualité)
# Chat (sans recherche web) :
#   - llama-3.1-8b-instruct               (rapide)
#   - llama-3.1-70b-instruct              (haute qualité)
```

### 3. Installation

```bash
# Cloner le projet
git clone https://github.com/votre-org/FilAgent.git
cd FilAgent

# Environnement virtuel
python3.11 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Installation des dépendances
pip install -r requirements.txt

# Initialiser la base de données
python -c "from memory.episodic import create_tables; create_tables()"

# IMPORTANT: Vérifier que .env contient votre clé API
cat .env | grep PERPLEXITY_API_KEY
```

### 4. Lancement

```bash
# Mode développement
python runtime/server.py

# Mode production (avec Gunicorn)
gunicorn -w 4 -k uvicorn.workers.UvicornWorker runtime.server:app \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --access-logfile logs/access.log \
  --error-logfile logs/error.log
```

### 5. Validation

```bash
# Test de santé
curl http://localhost:8000/health

# Test de génération
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Test de connexion Perplexity"}],
    "conversation_id": "prod-test-001"
  }'
```

**Attendu** : Réponse JSON avec `status: "success"` et contenu généré.

### 6. Considérations de Production

**Sécurité** :
- Ne JAMAIS committer `.env` dans Git (déjà dans `.gitignore`)
- Utiliser un gestionnaire de secrets (Vault, AWS Secrets Manager)
- Renouveler les clés API périodiquement

**Rate Limiting** :
- Vérifier les limites de votre plan Perplexity
- Implémenter un rate limiter côté application si nécessaire
- Monitorer l'usage via tableau de bord Perplexity

**Coûts** :
- Modèles Sonar : ~$1-5 par million de tokens
- Surveiller les métriques d'usage dans `logs/events/`
- Alertes si seuil de coûts dépassé

---

## Déploiement avec Modèle Local

### 1. Choix du Modèle

**Recommandation par défaut** : Llama 3 8B Instruct (Q4_K_M quantization)

- **Taille** : ~4.6 GB
- **RAM requise** : 8 GB
- **Performance** : Bonne qualité, vitesse acceptable
- **Licence** : Llama 3 Community License (usage commercial autorisé)

**Alternatives** :

| Modèle | Taille | RAM | Cas d'usage |
|--------|--------|-----|-------------|
| Llama 3 8B (Q4_K_M) | 4.6 GB | 8 GB | Défaut, bon équilibre |
| Llama 3 8B (Q8_0) | 8.5 GB | 12 GB | Haute qualité |
| Mistral 7B | 4.1 GB | 8 GB | Excellent français |
| CodeLlama 7B | 3.8 GB | 8 GB | Spécialisé code |
| Qwen 7B | 4.2 GB | 8 GB | Multilangue performant |

### 2. Téléchargement du Modèle

```bash
# Créer le répertoire
mkdir -p models/weights
cd models/weights

# Télécharger Llama 3 8B Instruct (recommandé)
wget https://huggingface.co/TheBloke/Llama-3-8B-Instruct-GGUF/resolve/main/llama-3-8b-instruct.Q4_K_M.gguf \
  -O base.gguf

# Vérifier le téléchargement
ls -lh base.gguf
# Attendu : ~4.6 GB

# Retour au répertoire racine
cd ../..
```

**Note** : Le téléchargement peut prendre 5-30 minutes selon votre connexion.

### 3. Configuration

Créer ou éditer `.env` :

```bash
# Backend LLM
LLM_BACKEND=llama.cpp

# Configuration llama.cpp
MODEL_PATH=models/weights/base.gguf
CONTEXT_SIZE=4096              # Fenêtre de contexte (2048-8192)
N_GPU_LAYERS=35               # Couches GPU (0 pour CPU uniquement)

# Si CPU uniquement (pas de GPU)
# N_GPU_LAYERS=0
# Génération sera plus lente mais fonctionnelle
```

### 4. Vérification GPU (optionnel)

```bash
# Vérifier NVIDIA GPU disponible
nvidia-smi

# Vérifier CUDA
nvcc --version

# Si pas de GPU : configuration CPU fonctionnera (plus lent)
```

### 5. Installation

```bash
# Même procédure que Perplexity
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Installer llama-cpp-python avec support GPU (si disponible)
CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python --force-reinstall --no-cache-dir

# Sans GPU (CPU uniquement)
# pip install llama-cpp-python
```

### 6. Lancement

```bash
# Mode développement
python runtime/server.py

# Le modèle sera chargé au démarrage (peut prendre 10-30 secondes)
# Surveillez les logs pour confirmation :
# "✓ Model loaded successfully"
```

### 7. Validation

```bash
# Test de génération
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Bonjour, peux-tu te présenter ?"}],
    "conversation_id": "local-test-001"
  }'
```

**Attendu** : Réponse JSON avec génération du modèle local.

### 8. Optimisation Performance

**Pour GPU** :

```bash
# Augmenter les couches GPU (config/agent.yaml ou .env)
N_GPU_LAYERS=35  # Ajuster selon VRAM disponible

# Vérifier utilisation GPU
nvidia-smi -l 1  # Rafraîchir chaque seconde pendant génération
```

**Pour CPU** :

```bash
# Réduire context_size pour moins de RAM
CONTEXT_SIZE=2048

# Limiter max_tokens pour accélérer
# Dans config/agent.yaml
model:
  max_tokens: 512  # Au lieu de 2048
```

---

## Configuration de Production

### 1. Fichiers de Configuration

**Structure recommandée** :

```
config/
├── agent.yaml              # Configuration agent principale
├── policies.yaml           # RBAC, guardrails, PII
├── retention.yaml          # Rétention des données
├── provenance.yaml         # Traçabilité
└── prometheus.yml          # Monitoring
```

### 2. Ajustements Production

**config/agent.yaml** :

```yaml
agent:
  mode: "production"  # Au lieu de "development"

model:
  temperature: 0.2    # Plus déterministe en prod
  seed: 42            # Reproductibilité

logging:
  level: "INFO"       # Pas "DEBUG" en prod
  rotation: "daily"   # Rotation des logs
```

### 3. Sécurité

```bash
# Générer une clé secrète
openssl rand -hex 32 > .secret_key

# Dans .env
SECRET_KEY=$(cat .secret_key)

# Permissions restrictives
chmod 600 .env
chmod 600 .secret_key
```

### 4. Base de Données

```bash
# Backup régulier
crontab -e
# Ajouter :
# 0 2 * * * /path/to/FilAgent/scripts/backup_db.sh

# Script de backup (créer scripts/backup_db.sh)
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
cp data/filagent.db backups/filagent_${DATE}.db
find backups/ -mtime +7 -delete  # Garder 7 jours
```

---

## Monitoring et Observabilité

### 1. Logs Structurés

Tous les logs sont au format JSONL dans `logs/` :

```bash
# Événements système
tail -f logs/events/events_YYYYMMDD.jsonl

# Décisions de l'agent
tail -f logs/decisions/DR-*.json

# Actions bloquées
tail -f logs/safeties/blocked_YYYYMMDD.jsonl
```

### 2. Prometheus

```bash
# Démarrer Prometheus
prometheus --config.file=config/prometheus.yml

# Accès : http://localhost:9090
```

**Métriques clés** :
- `filagent_requests_total` - Total requêtes
- `filagent_request_duration_seconds` - Latence
- `filagent_model_tokens_total` - Tokens utilisés
- `filagent_errors_total` - Erreurs

### 3. Alertes

Configurer des alertes pour :
- Erreurs > 5% des requêtes
- Latence p95 > 10 secondes
- Usage tokens > seuil quotidien (pour Perplexity)
- Disk usage > 80%

### 4. Dashboards Grafana

```bash
# Importer dashboard pré-configuré
# Voir grafana/dashboards/filagent.json
```

---

## Problèmes Connus et Limitations

### Script start_all.sh - Référence obsolète (ligne 21)

**Problème identifié par l'expert MLOps** :

Le script `start_all.sh` contient une référence à un fichier qui n'existe pas :

```bash
# Ligne 21 dans start_all.sh (OBSOLÈTE)
nohup python gradio_app.py > logs/gradio.log 2>&1 &
```

**Fichier réel** : `gradio_app_production.py`

**Impact** :
- Le script `start_all.sh` échouera au lancement de l'interface Gradio
- L'API FastAPI (port 8000) fonctionnera correctement via ce script
- Interface Gradio (port 7860) ne démarrera pas

**Solution de contournement recommandée** :
```bash
# NE PAS utiliser start_all.sh pour le moment

# Option 1 : Lancer uniquement le serveur FastAPI (RECOMMANDÉ)
python runtime/server.py

# Option 2 : Avec uvicorn directement
python -m uvicorn runtime.server:app --host 0.0.0.0 --port 8000

# L'interface Gradio est optionnelle pour l'usage normal
```

**Pour utiliser Gradio** (si nécessaire) :
```bash
# Lancer manuellement avec le bon fichier
python gradio_app_production.py
# Interface disponible sur http://localhost:7860
```

**Note** : Ce problème sera corrigé dans une version future. Le serveur FastAPI seul est suffisant pour toutes les opérations standard.

---

## Résolution de Problèmes

### Problème : Serveur ne démarre pas

**Symptômes** :
```
Error: Failed to initialize model
```

**Solutions** :

1. **Perplexity** : Vérifier clé API
   ```bash
   echo $PERPLEXITY_API_KEY
   # Doit afficher : pplx-...
   ```

2. **Modèle local** : Vérifier fichier existe
   ```bash
   ls -lh models/weights/base.gguf
   # Doit afficher le fichier (~4-8 GB)
   ```

3. **Vérifier .env** :
   ```bash
   cat .env | grep LLM_BACKEND
   # Doit correspondre à votre configuration
   ```

### Problème : Génération très lente (modèle local)

**Causes possibles** :

1. **CPU uniquement** (pas de GPU)
   ```bash
   # Vérifier dans .env
   N_GPU_LAYERS=0  # CPU seulement

   # Solution : Activer GPU si disponible
   N_GPU_LAYERS=35
   ```

2. **Modèle trop grand pour RAM**
   ```bash
   # Vérifier RAM disponible
   free -h

   # Solution : Utiliser quantisation plus agressive
   wget https://huggingface.co/TheBloke/Llama-3-8B-Instruct-GGUF/resolve/main/llama-3-8b-instruct.Q4_0.gguf
   ```

3. **Context size trop grand**
   ```bash
   # Réduire dans .env
   CONTEXT_SIZE=2048  # Au lieu de 4096
   ```

### Problème : Erreurs API Perplexity

**Symptômes** :
```json
{"error": "API rate limit exceeded"}
```

**Solutions** :

1. **Vérifier limites** : Consulter dashboard Perplexity
2. **Implémenter retry avec backoff** (déjà dans `runtime/model_interface.py`)
3. **Upgrade plan** si usage élevé

### Problème : gradio_app.py introuvable

**Symptômes** :
```
FileNotFoundError: gradio_app.py
```

**Cause** : Référence obsolète dans `start_all.sh` (ligne 21)

**Solution** :
```bash
# Le fichier correct est gradio_app_production.py
# Mais n'est pas utilisé en production normale
# Ignorer cette erreur si vous utilisez runtime/server.py
```

### Problème : Logs de décision vides

**Vérifications** :

1. **Middleware activé** :
   ```bash
   cat .env | grep ENABLE_AUDIT_TRAIL
   # Doit être : true
   ```

2. **Répertoire logs existe** :
   ```bash
   ls -la logs/decisions/
   ```

3. **Permissions** :
   ```bash
   chmod -R 755 logs/
   ```

---

## Checklist de Déploiement

### Pré-déploiement

- [ ] Backend LLM choisi (Perplexity ou Local)
- [ ] Fichier `.env` configuré et sécurisé
- [ ] Clé API Perplexity obtenue (si applicable)
- [ ] Modèle local téléchargé (si applicable)
- [ ] Python 3.10+ installé
- [ ] Environnement virtuel créé
- [ ] Dépendances installées (`requirements.txt`)
- [ ] Base de données initialisée

### Déploiement

- [ ] Variables d'environnement validées
- [ ] Serveur démarre sans erreur
- [ ] Test de santé réussi (`/health`)
- [ ] Test de génération réussi (`/chat`)
- [ ] Logs structurés fonctionnels
- [ ] Decision Records générés
- [ ] PII redaction activée

### Post-déploiement

- [ ] Monitoring Prometheus configuré
- [ ] Dashboards Grafana importés
- [ ] Alertes configurées
- [ ] Backup base de données planifié
- [ ] Documentation équipe mise à jour
- [ ] Procédure rollback documentée

### Sécurité

- [ ] `.env` non commité (vérifié dans `.gitignore`)
- [ ] Permissions fichiers restrictives (`chmod 600 .env`)
- [ ] Secret key générée aléatoirement
- [ ] Clés API stockées de manière sécurisée
- [ ] Audit trail activé
- [ ] WORM logging fonctionnel

### Conformité

- [ ] Politiques RBAC configurées (`config/policies.yaml`)
- [ ] Rétention données définie (`config/retention.yaml`)
- [ ] Provenance tracking activé
- [ ] Decision Records validés (signature EdDSA)
- [ ] DPIA complété si nécessaire
- [ ] Documentation conformité à jour

---

## Support et Ressources

**Documentation** :
- [README.md](README.md) - Vue d'ensemble projet
- [QUICK_TEST.md](QUICK_TEST.md) - Guide de tests
- [docs/PERPLEXITY_INTEGRATION.md](docs/PERPLEXITY_INTEGRATION.md) - Configuration Perplexity détaillée
- [CLAUDE.md](CLAUDE.md) - Guide technique complet

**Monitoring** :
- Prometheus : http://localhost:9090
- Grafana : http://localhost:3000
- API Docs : http://localhost:8000/docs

**Logs** :
- Événements : `logs/events/`
- Décisions : `logs/decisions/`
- Blocages : `logs/safeties/`

**Contact** :
- Issues GitHub : https://github.com/votre-org/FilAgent/issues
- Email support : support@filagent.ai
- Gouvernance : governance@filagent.ai

---

**Version** : 1.0.0
**Maintenu par** : Équipe FilAgent
**Licence** : MIT (voir LICENSE)
