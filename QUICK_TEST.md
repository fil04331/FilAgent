# Guide de Tests Rapides FilAgent

**Version**: 1.0.0
**Dernière mise à jour**: 2025-11-16

---

## Vue d'ensemble

Ce guide vous permet de valider rapidement que votre installation FilAgent fonctionne correctement, quel que soit le backend LLM utilisé (Perplexity API ou modèle local).

**Temps estimé** : 5-10 minutes

---

## Prérequis

Avant de commencer les tests :

- [ ] Installation complétée (voir [README.md](README.md))
- [ ] Backend LLM configuré (.env avec Perplexity OU modèle local téléchargé)
- [ ] Base de données initialisée
- [ ] Environnement virtuel activé

---

## Test 1 : Vérification de l'environnement

### Vérifier Python et dépendances

```bash
# Depuis le répertoire FilAgent, environnement virtuel activé

# Vérifier version Python
python --version
# Attendu : Python 3.10.x ou supérieur (3.11.13 recommandé)

# Vérifier installation packages critiques
python -c "import fastapi, pydantic, sqlite3; print('✓ Dépendances OK')"
# Attendu : "✓ Dépendances OK"
```

### Vérifier configuration backend

```bash
# Afficher backend configuré
cat .env | grep LLM_BACKEND
# Attendu : "LLM_BACKEND=perplexity" OU "LLM_BACKEND=llama.cpp"
```

**Si Perplexity** :
```bash
# Vérifier clé API présente
cat .env | grep PERPLEXITY_API_KEY
# Attendu : "PERPLEXITY_API_KEY=pplx-..." (commence par pplx-)

# Vérifier modèle sélectionné
cat .env | grep PERPLEXITY_MODEL
# Attendu : "PERPLEXITY_MODEL=llama-3.1-sonar-large-128k-online" (ou autre modèle)
```

**Si Modèle Local** :
```bash
# Vérifier modèle téléchargé
ls -lh models/weights/base.gguf
# Attendu : Fichier existant, ~4-8 GB selon quantification

# Vérifier configuration
cat .env | grep MODEL_PATH
# Attendu : "MODEL_PATH=models/weights/base.gguf"
```

**Résultat attendu** : Toutes les vérifications passent sans erreur.

---

## Test 2 : Démarrage du serveur

### Lancer le serveur

```bash
# Terminal 1 : Lancer le serveur
python runtime/server.py
```

**Logs attendus** :

Pour **Perplexity** :
```
INFO:     Started server process
ℹ Initializing FilAgent with Perplexity backend...
✓ Perplexity API client initialized
✓ Model interface ready: llama-3.1-sonar-large-128k-online
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

Pour **Modèle Local** :
```
INFO:     Started server process
ℹ Loading model from models/weights/base.gguf...
ℹ This may take 10-30 seconds...
✓ Model loaded successfully
✓ Model interface ready: llama.cpp
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Problèmes potentiels** :

| Erreur | Cause | Solution |
|--------|-------|----------|
| `Failed to initialize model` | Clé API invalide OU modèle manquant | Vérifier .env |
| `FileNotFoundError: base.gguf` | Modèle local non téléchargé | Télécharger modèle (voir models/weights/README.md) |
| `Port 8000 already in use` | Serveur déjà lancé | Arrêter processus existant : `lsof -ti:8000 \| xargs kill -9` |
| `ModuleNotFoundError` | Dépendances manquantes | `pip install -r requirements.txt` |

### Vérifier endpoint de santé

```bash
# Terminal 2 (nouveau terminal)
curl http://localhost:8000/health
```

**Réponse attendue** :
```json
{
  "status": "healthy",
  "backend": "perplexity",
  "version": "1.0.0",
  "timestamp": "2025-11-16T12:00:00Z"
}
```

**Si erreur** :
- `Connection refused` : Serveur pas démarré, vérifier Terminal 1
- Timeout : Vérifier port 8000 disponible

---

## Test 3 : Génération simple

### Test de chat basique

```bash
# Test simple : salutation
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Bonjour ! Peux-tu me dire quelle est la capitale de la France ?"}],
    "conversation_id": "test-simple-001"
  }'
```

**Réponse attendue** :
```json
{
  "status": "success",
  "response": "Bonjour ! La capitale de la France est Paris.",
  "conversation_id": "test-simple-001",
  "metadata": {
    "model": "llama-3.1-sonar-large-128k-online",
    "backend": "perplexity",
    "tokens_used": 45,
    "duration_ms": 1234
  }
}
```

**Critères de validation** :
- ✓ Statut = "success"
- ✓ Réponse contient "Paris"
- ✓ conversation_id correspond
- ✓ Temps de réponse < 10 secondes

### Test avec recherche web (Perplexity uniquement)

```bash
# Test recherche temps réel (si modèle Sonar)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Quelle est la météo actuelle à Montréal ?"}],
    "conversation_id": "test-web-search-001"
  }'
```

**Réponse attendue** :
- ✓ Contient des informations météo récentes
- ✓ Mentionne sources (si modèle Sonar)
- ✓ Temps de réponse < 15 secondes

**Note** : Ce test échouera avec modèle local ou modèles Perplexity non-Sonar (normal).

---

## Test 4 : Compliance et gouvernance

### Vérifier Decision Records (DR)

```bash
# Lister les Decision Records générés
ls -lt logs/decisions/ | head -5
```

**Attendu** :
```
-rw-r--r--  1 user  staff  2048 Nov 16 12:05 DR-20251116-001.json
-rw-r--r--  1 user  staff  2134 Nov 16 12:04 DR-20251116-002.json
```

**Vérifier contenu d'un DR** :
```bash
# Lire le DR le plus récent
cat $(ls -t logs/decisions/DR-*.json | head -1) | python -m json.tool
```

**Contenu attendu** :
```json
{
  "dr_id": "DR-20251116-001",
  "ts": "2025-11-16T12:05:00.000-05:00",
  "actor": "agent.core",
  "task_id": "T-20251116-001",
  "policy_version": "policies@abc123",
  "model_fingerprint": "perplexity:llama-3.1-sonar-large-128k-online",
  "reasoning_markers": ["simple_chat"],
  "tools_used": [],
  "decision": "generate_response",
  "signature": "eddsa:..."
}
```

**Critères de validation** :
- ✓ Fichier JSON valide
- ✓ Contient tous les champs requis
- ✓ Signature EdDSA présente

### Vérifier Event Logs

```bash
# Lister les logs d'événements
ls -lt logs/events/ | head -3
```

**Attendu** :
```
-rw-r--r--  1 user  staff  45678 Nov 16 12:05 events_20251116.jsonl
```

**Lire derniers événements** :
```bash
tail -5 logs/events/events_$(date +%Y%m%d).jsonl | python -m json.tool
```

**Contenu attendu** :
```json
{
  "ts": "2025-11-16T12:05:00.000-05:00",
  "trace_id": "abc123...",
  "level": "INFO",
  "actor": "agent.core",
  "event": "chat.request",
  "conversation_id": "test-simple-001",
  "pii_redacted": true
}
```

**Critères de validation** :
- ✓ Format JSONL (une ligne = un JSON)
- ✓ Tous événements ont timestamp
- ✓ `pii_redacted: true` présent

### Vérifier PII Redaction

```bash
# Test avec données sensibles
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Mon email est john.doe@example.com et mon téléphone est 514-555-1234"}],
    "conversation_id": "test-pii-001"
  }'
```

**Vérification dans les logs** :
```bash
# Chercher dans les logs - NE DEVRAIT PAS trouver l'email
grep -r "john.doe@example.com" logs/events/
# Attendu : Aucun résultat (vide)

# Devrait trouver des versions masquées
grep -r "EMAIL_REDACTED" logs/events/
# Attendu : Résultats trouvés
```

**Critères de validation** :
- ✓ Email original PAS trouvé dans logs
- ✓ Placeholder `[EMAIL_REDACTED]` trouvé dans logs
- ✓ Téléphone masqué (si applicable)

---

## Test 5 : Performance et charge

### Test de latence

```bash
# Mesurer temps de réponse
time curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Explique-moi brièvement ce qu'\''est FilAgent"}],
    "conversation_id": "test-perf-001"
  }'
```

**Seuils attendus** :

| Backend | Première requête | Requêtes suivantes |
|---------|------------------|-------------------|
| **Perplexity API** | < 5 secondes | < 3 secondes |
| **Modèle Local (GPU)** | < 3 secondes | < 2 secondes |
| **Modèle Local (CPU)** | < 15 secondes | < 10 secondes |

**Note** : Première requête peut être plus lente (cold start).

### Test de requêtes multiples

```bash
# Envoyer 5 requêtes en parallèle
for i in {1..5}; do
  curl -X POST http://localhost:8000/chat \
    -H "Content-Type: application/json" \
    -d "{
      \"messages\": [{\"role\": \"user\", \"content\": \"Test parallèle $i\"}],
      \"conversation_id\": \"test-parallel-$i\"
    }" &
done
wait
```

**Critères de validation** :
- ✓ Toutes les 5 requêtes réussissent
- ✓ Pas d'erreurs dans logs serveur
- ✓ Temps total < 30 secondes

---

## Test 6 : Documentation API

### Accéder à la documentation interactive

Ouvrir dans navigateur :
```
http://localhost:8000/docs
```

**Vérifications** :
- ✓ Page Swagger UI s'affiche
- ✓ Endpoints visibles : `/health`, `/chat`, `/conversation/{id}`
- ✓ Possibilité de tester directement depuis l'interface

### Tester depuis Swagger UI

1. Cliquer sur `POST /chat`
2. Cliquer sur "Try it out"
3. Remplir le body :
   ```json
   {
     "messages": [{"role": "user", "content": "Test depuis Swagger"}],
     "conversation_id": "swagger-test-001"
   }
   ```
4. Cliquer "Execute"

**Résultat attendu** :
- ✓ Code 200 OK
- ✓ Réponse JSON valide avec champ `response`

---

## Checklist de validation complète

### Installation et Configuration
- [ ] Python 3.10+ installé et vérifié
- [ ] Environnement virtuel créé et activé
- [ ] Dépendances installées sans erreur
- [ ] Fichier .env configuré avec backend choisi
- [ ] Clé API Perplexity valide (si backend Perplexity)
- [ ] Modèle local téléchargé et présent (si backend local)

### Serveur
- [ ] Serveur démarre sans erreur
- [ ] Endpoint `/health` retourne status "healthy"
- [ ] Logs serveur propres (pas d'erreurs)
- [ ] Port 8000 accessible

### Fonctionnalités de base
- [ ] Génération simple fonctionne
- [ ] Réponse cohérente et pertinente
- [ ] Temps de réponse acceptable
- [ ] conversation_id correctement géré

### Compliance et Gouvernance
- [ ] Decision Records générés dans `logs/decisions/`
- [ ] Decision Records contiennent signature EdDSA
- [ ] Event logs générés dans `logs/events/`
- [ ] Format JSONL valide
- [ ] PII correctement masqué dans logs
- [ ] `pii_redacted: true` dans tous les événements

### Performance
- [ ] Latence < seuils définis
- [ ] Requêtes parallèles supportées
- [ ] Pas de memory leaks observés
- [ ] Logs rotés correctement

### Documentation
- [ ] Swagger UI accessible
- [ ] Tous endpoints documentés
- [ ] Tests possibles depuis Swagger

---

## Note importante sur start_all.sh

Le script `start_all.sh` contient actuellement une référence obsolète (ligne 21) à `gradio_app.py` qui n'existe pas. Le fichier correct est `gradio_app_production.py`.

**Recommandation** : Ne pas utiliser `start_all.sh` pour le moment. Lancer le serveur directement :

```bash
python runtime/server.py
```

Voir [README_DEPLOYMENT.md](README_DEPLOYMENT.md#problèmes-connus-et-limitations) pour plus de détails.

---

## Résolution de problèmes courants

### Problème : Génération échoue systématiquement

**Symptômes** :
```json
{"status": "error", "error": "Generation failed"}
```

**Diagnostic** :

1. **Vérifier logs serveur** (Terminal 1) :
   ```
   # Chercher erreurs récentes
   ```

2. **Perplexity** : Vérifier clé API :
   ```bash
   # Tester manuellement
   curl https://api.perplexity.ai/chat/completions \
     -H "Authorization: Bearer $PERPLEXITY_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"model":"llama-3.1-sonar-small-128k-online","messages":[{"role":"user","content":"test"}]}'
   ```

3. **Modèle Local** : Vérifier chargement :
   ```bash
   # Dans logs serveur, chercher :
   # "✓ Model loaded successfully"
   ```

### Problème : Logs vides

**Causes possibles** :
- Middlewares non initialisés
- Permissions fichiers
- Répertoires logs manquants

**Solutions** :
```bash
# Créer répertoires si manquants
mkdir -p logs/events logs/decisions logs/safeties

# Vérifier permissions
chmod -R 755 logs/

# Vérifier .env
cat .env | grep ENABLE_AUDIT_TRAIL
# Doit être : ENABLE_AUDIT_TRAIL=true
```

### Problème : Lenteur excessive (modèle local)

**Si > 30 secondes par requête** :

1. **Vérifier GPU utilisé** :
   ```bash
   # Pendant génération
   nvidia-smi
   # Doit montrer utilisation GPU
   ```

2. **Si pas de GPU** : Activer si disponible :
   ```bash
   # Dans .env
   N_GPU_LAYERS=35
   # Redémarrer serveur
   ```

3. **Réduire context** :
   ```bash
   # Dans .env
   CONTEXT_SIZE=2048
   ```

---

## Prochaines étapes

Une fois tous les tests passés :

1. **Production** : Consulter [README_DEPLOYMENT.md](README_DEPLOYMENT.md)
2. **Monitoring** : Configurer Prometheus (voir docs/PROMETHEUS_SETUP.md)
3. **Benchmarks** : Exécuter évaluations complètes (voir eval/)
4. **Personnalisation** : Ajuster configurations dans `config/`

---

## Support

**Documentation** :
- [README.md](README.md) - Vue d'ensemble
- [README_DEPLOYMENT.md](README_DEPLOYMENT.md) - Déploiement production
- [docs/PERPLEXITY_INTEGRATION.md](docs/PERPLEXITY_INTEGRATION.md) - Configuration Perplexity
- [models/weights/README.md](models/weights/README.md) - Configuration modèles locaux

**Issues** : https://github.com/votre-org/FilAgent/issues

**Contact** : support@filagent.ai

---

**Version** : 1.0.0
**Dernière révision** : 2025-11-16
**Mainteneur** : Équipe FilAgent
