# Guide des Workflows GitHub Actions - FilAgent

## 📋 Vue d'Ensemble

Ce dossier contient 4 workflows GitHub Actions complets pour FilAgent:

### 1️⃣ **testing-compliance.yml** - Tests & Conformité Complète
**Déclencheurs:** push, pull_request, hebdomadaire (lundi 8h)

**Jobs:**
- ✅ **test-core** - Tests unitaires et intégration (Python 3.10 & 3.11)
  - Coverage avec codecov
  - Tests middleware stack
  - Tests mémoire et outils
  
- ✅ **compliance-tests** - Conformité légale
  - WORM Logger (Loi 25)
  - Decision Records (EdDSA signatures)
  - PII Redactor (RGPD)
  - RBAC Manager
  - Génération rapport de conformité

- ✅ **code-quality** - Qualité du code
  - Black formatting
  - Flake8 linting
  - MyPy type checking
  - Bandit security scan

- ✅ **openapi-validation** - Validation API
  - Validation OpenAPI spec
  - Tests endpoints API

- ✅ **performance-tests** - Tests de performance
  - Stress test mémoire (1000 insertions)
  - Tests pipeline middleware

**Artefacts générés:**
- `coverage.xml` - Rapport de couverture
- `compliance_report.txt` - Rapport de conformité
- `bandit_report.json` - Rapport de sécurité

---

### 2️⃣ **codeql-security.yml** - Analyse Sécurité CodeQL
**Déclencheurs:** push sur main, pull_request, hebdomadaire (dimanche 3h)

**Analyses:**
- ✅ CodeQL pour Python avec queries security-and-quality
- ✅ Vérification absence de secrets hardcodés
- ✅ Validation configuration sandbox

**Permissions requises:**
- security-events: write
- contents: read
- actions: read

---

### 3️⃣ **deploy.yml** - Déploiement Automatique
**Déclencheurs:** release published, workflow_dispatch manuel

**Environnements:**
- staging (par défaut)
- production (optionnel)

**Jobs:**
- ✅ **validate** - Validation pré-déploiement
  - Vérification configurations YAML
  - Vérification modules de conformité
  
- ✅ **package** - Création du package
  - Archive tar.gz avec:
    - Code (runtime, tools, memory, config)
    - Script de démarrage
    - Requirements
  
- ✅ **deploy-staging** - Déploiement staging
  - Téléchargement du package
  - Déploiement (à personnaliser selon votre infrastructure)

**Artefacts:**
- `filagent-deployment.tar.gz` - Package de déploiement

---

### 4️⃣ **documentation.yml** - Documentation Automatique
**Déclencheurs:** push sur fichiers Python/Markdown/YAML, workflow_dispatch

**Génère:**
- ✅ **API Documentation** - Extraction docstrings Python
- ✅ **Middleware Documentation** - Architecture 8 couches
- ✅ **Compliance Matrix** - Matrice de conformité (Loi 25, RGPD, EU AI Act, NIST)

**Artefacts:**
- `docs/api/documentation.json` - Documentation API
- `docs/MIDDLEWARE.md` - Guide middleware
- `docs/COMPLIANCE_MATRIX.yaml` - Matrice de conformité

---

## 🚀 Mise en Route

### 1. Activer les workflows
Les workflows sont activés automatiquement dès que vous les pushez dans `.github/workflows/`

### 2. Configurer les secrets (optionnel)
Si vous utilisez des services externes, ajoutez les secrets dans:
`Settings > Secrets and variables > Actions`

Exemples:
- `CODECOV_TOKEN` - Pour upload coverage
- `DEPLOY_KEY` - Pour déploiement SSH
- `DOCKER_TOKEN` - Pour registry Docker

### 3. Configurer les environnements (pour deploy.yml)
`Settings > Environments > New environment`

Créez:
- `staging` - Environnement de test
- `production` - Environnement de production (optionnel)

### 4. Activer Dependabot
Le fichier `.github/dependabot.yml` est configuré pour:
- Mises à jour hebdomadaires des dépendances Python
- Mises à jour des GitHub Actions
- Revue automatique assignée à @fil04331

---

## 📊 Monitoring

### Voir les résultats des workflows
1. Onglet **Actions** dans votre repo GitHub
2. Cliquez sur un workflow pour voir l'historique
3. Cliquez sur un run pour voir les détails

### Télécharger les artefacts
1. Allez dans un run terminé
2. Section **Artifacts** en bas de page
3. Téléchargez les rapports (coverage, compliance, etc.)

### Badges de statut
Voir `.github/BADGES.md` pour ajouter les badges à votre README

---

## 🛠️ Personnalisation

### Modifier les déclencheurs
Exemple pour exécuter uniquement sur main:
```yaml
on:
  push:
    branches: [main]
```

### Ajouter des étapes
Exemple pour ajouter un test:
```yaml
- name: Mon nouveau test
  run: |
    pytest tests/mon_test.py
```

### Changer les versions Python
Dans `testing-compliance.yml`:
```yaml
strategy:
  matrix:
    python-version: ['3.9', '3.10', '3.11', '3.12']
```

---

## ⚠️ Troubleshooting

### Les tests échouent?
1. Vérifiez les logs dans l'onglet Actions
2. Reproduisez localement: `pytest tests/ -v`
3. Vérifiez que `requirements.txt` est à jour

### CodeQL échoue?
1. Assurez-vous que le code compile
2. Vérifiez qu'il n'y a pas de secrets hardcodés

### Déploiement échoue?
1. Vérifiez que tous les fichiers requis existent
2. Configurez vos secrets de déploiement
3. Personnalisez la commande de déploiement dans `deploy-staging`

---

## 📝 Checklist de Validation

Avant de merger une PR, assurez-vous que:
- [ ] ✅ Tous les tests passent (test-core)
- [ ] ✅ Tests de conformité OK (compliance-tests)
- [ ] ✅ CodeQL security scan OK
- [ ] ✅ Pas de secrets détectés
- [ ] ✅ Code formaté (Black)
- [ ] ✅ Pas d'erreurs de linting (Flake8)

---

## 🎯 Métriques de Succès

Ces workflows garantissent:
- **Qualité**: Coverage >80%, linting, type checking
- **Sécurité**: CodeQL, Bandit, secrets scanning
- **Conformité**: Tests Loi 25, RGPD, EU AI Act
- **Performance**: Tests de stress, benchmarks
- **Documentation**: Génération automatique

---

## 📚 Ressources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [CodeQL Documentation](https://codeql.github.com/docs/)
- [Dependabot Documentation](https://docs.github.com/en/code-security/dependabot)
- [Pytest Documentation](https://docs.pytest.org/)

---

**Créé pour FilAgent - Safety by Design**
