# Inventaire Complet des Workflows GitHub Actions

**Date de dernière mise à jour:** 2024-12-28  
**État:** Post-optimisation

---

## 📊 Vue d'Ensemble

**Total workflows actifs:** 8  
**Coût mensuel estimé:** ~$3.50/mois  
**Économies réalisées:** ~$2.20/mois (39% de réduction)

---

## Workflows Principaux

### 1. testing.yml - Tests & Quality (Loi 25) ⭐⭐⭐⭐⭐
**Statut:** ✅ Optimisé  
**Déclencheurs:** Push/PR vers main  
**Durée:** ~3m (optimisé de 4m)  
**Jobs:** 5 (lint, security, test, compliance, quality-gate)  
**Coût estimé:** $2.00/mois  

**Optimisations:**
- Matrice Python 3.11-3.12 (était 3.10-3.12)
- Caching PDM agressif

### 2. testing-compliance.yml - Tests & Conformité ⭐⭐⭐⭐
**Statut:** ✅ Existant (complémentaire)  
**Déclencheurs:** Push main/develop, PR main, Hebdomadaire (lundi 8h)  
**Durée:** ~4m  
**Jobs:** 5 (test-core, code-quality, compliance-tests, openapi-validation, performance-tests)  
**Coût estimé:** $0.80/mois  

**Note:** Complémentaire à testing.yml, se concentre sur conformité et performance

### 3. codeql.yml - CodeQL Security Analysis ⭐⭐⭐⭐⭐
**Statut:** ✅ Optimisé (renommé de codeql-advanced.yml)  
**Déclencheurs:** Push/PR vers main (*.py), Dimanche 6h UTC  
**Durée:** ~2.5m  
**Jobs:** 1 (analyze)  
**Coût estimé:** $0.24/mois  

**Optimisations:**
- Queries security-and-quality activées
- Paths filters ajoutés (*.py)
- Timeout 30 minutes

### 4. codeql-security.yml - CodeQL + Custom Checks ⭐⭐⭐⭐
**Statut:** ⚠️ À fusionner avec codeql.yml (Phase 4)  
**Déclencheurs:** Push/PR vers main, Dimanche 3h UTC  
**Durée:** ~2.5m  
**Jobs:** 1 (analyze + custom checks)  
**Coût estimé:** $0.24/mois  

**Spécificités:**
- Détection secrets hardcodés
- Validation sandbox sécurisé
- Vérifications FilAgent spécifiques

### 5. dependencies.yml - Dependency Security ⭐⭐⭐⭐
**Statut:** ✅ Optimisé  
**Déclencheurs:** Push/PR (deps), Mensuel (1er du mois 9h), Manuel  
**Durée:** ~2m  
**Jobs:** 4 (validate-lock-file, security-audit, dependency-review, update-requirements)  
**Coût estimé:** $0.12/mois  

**Optimisations:**
- Fréquence hebdomadaire → mensuelle
- Outdated check intégré dans security-audit
- update-requirements uniquement sur schedule/manual

### 6. benchmarks.yml - Performance Benchmarks ⭐⭐⭐
**Statut:** ✅ Optimisé  
**Déclencheurs:** Mensuel (1er du mois 2h), Manuel, Push fichiers critiques  
**Durée:** Variable (max 2h)  
**Jobs:** 2 (run-benchmarks, publish-results)  
**Coût estimé:** $0.16/mois  

**Optimisations:**
- Fréquence hebdomadaire → mensuelle
- Paths filters stricts (eval/, runtime/agent.py, runtime/model_interface.py, planner/)

### 7. claude-code-review.yml - AI Code Review ⭐⭐⭐
**Statut:** ✅ Optimisé  
**Déclencheurs:** PR (opened, synchronize) avec conditions  
**Durée:** ~1.5m  
**Jobs:** 1 (claude-review)  
**Coût estimé:** $0.10/mois + API Claude  

**Optimisations:**
- Filtrage: FIRST_TIME_CONTRIBUTOR, CONTRIBUTOR, ou label needs-review
- Paths filters (*.py, runtime/, planner/, tools/, memory/, policy/)

**Conditions:**
```yaml
if: |
  github.event.pull_request.author_association == 'FIRST_TIME_CONTRIBUTOR' ||
  github.event.pull_request.author_association == 'CONTRIBUTOR' ||
  contains(github.event.pull_request.labels.*.name, 'needs-review')
```

### 8. deploy.yml - Déploiement FilAgent ⭐⭐⭐⭐
**Statut:** ✅ Existant (production)  
**Déclencheurs:** Release published, Manuel (staging/production)  
**Durée:** ~5m  
**Jobs:** 3 (validate, deploy-staging/production)  
**Coût estimé:** $0.08/mois (rare)  

**Note:** Workflow de production, exécuté uniquement lors des releases

---

## Workflows Supprimés

### ❌ linter.yml
**Raison:** Doublon du job lint dans testing.yml  
**Économie:** $1.20/mois

### ❌ codeql.yml (ancien)
**Raison:** Doublon de codeql-advanced.yml  
**Économie:** $0.24/mois

### ❌ documentation.yml
**Raison:** 0% succès, outils non disponibles  
**Économie:** $0.15/mois

### ❌ claude.yml
**Raison:** 0% succès, redondant avec claude-code-review.yml  
**Économie:** $0.02/mois

### ❌ security-pypdf-upgrade.yml
**Raison:** Fichier malformé, non valide  
**Économie:** N/A (n'était pas exécuté)

---

## Configuration Dependabot

**Fichier:** `.github/dependabot.yml`  
**Statut:** ✅ Optimisé

### Python Dependencies
- **Fréquence:** Mensuelle (était hebdomadaire)
- **Limite PRs:** 3 (était 5)
- **Groupement:** Toutes mises à jour mineures/patch ensemble

### GitHub Actions
- **Fréquence:** Mensuelle (était hebdomadaire)
- **Limite PRs:** 2 (était 3)
- **Groupement:** Toutes actions ensemble

**Impact:** Réduction de ~75% du volume de PRs Dependabot

---

## Récapitulatif des Coûts

| Workflow | Exécutions/mois | Coût unitaire | Coût mensuel |
|----------|-----------------|---------------|--------------|
| testing.yml | 40 | $0.05 | $2.00 |
| testing-compliance.yml | 20 | $0.04 | $0.80 |
| codeql.yml | 8 | $0.03 | $0.24 |
| codeql-security.yml | 8 | $0.03 | $0.24 |
| dependencies.yml | 3 | $0.04 | $0.12 |
| benchmarks.yml | 2 | $0.08 | $0.16 |
| claude-code-review.yml | 5 | $0.02 | $0.10 |
| deploy.yml | 1 | $0.08 | $0.08 |
| **TOTAL OPTIMISÉ** | | | **$3.74/mois** |
| | | | |
| **Avant optimisation** | | | **$5.94/mois** |
| **Économies** | | | **$2.20/mois (37%)** |

**Économie annuelle:** ~$26

---

## Matrice de Déclenchement

| Workflow | Push main | PR | Schedule | Release | Manuel |
|----------|-----------|----|----|---------|--------|
| testing.yml | ✅ | ✅ | - | - | ✅ |
| testing-compliance.yml | ✅ | ✅ | Hebdo | - | ✅ |
| codeql.yml | ✅ (*.py) | ✅ (*.py) | Hebdo | - | ✅ |
| codeql-security.yml | ✅ | ✅ | Hebdo | - | ✅ |
| dependencies.yml | ✅ (deps) | ✅ (deps) | Mensuel | - | ✅ |
| benchmarks.yml | ✅ (critical) | - | Mensuel | - | ✅ |
| claude-code-review.yml | - | ✅ (cond) | - | - | - |
| deploy.yml | - | - | - | ✅ | ✅ |

---

## Niveaux de Priorité

### Critique (⭐⭐⭐⭐⭐) - Ne JAMAIS désactiver
- `testing.yml` - Qualité du code
- `codeql.yml` - Sécurité

### Important (⭐⭐⭐⭐) - Désactivation temporaire possible
- `testing-compliance.yml` - Conformité réglementaire
- `codeql-security.yml` - Sécurité avancée
- `dependencies.yml` - Sécurité dépendances
- `deploy.yml` - Déploiement production

### Utile (⭐⭐⭐) - Peut être désactivé si nécessaire
- `benchmarks.yml` - Tracking performance
- `claude-code-review.yml` - Revue automatique

---

## Commandes de Gestion

### Lister tous les workflows
```bash
gh workflow list
```

### Activer/Désactiver un workflow
```bash
gh workflow enable <workflow-name>
gh workflow disable <workflow-name>
```

### Voir les runs récents
```bash
gh run list --workflow=testing.yml --limit 10
```

### Déclencher manuellement
```bash
gh workflow run testing.yml
gh workflow run benchmarks.yml
```

---

## Prochaines Optimisations (Phase 4)

1. **Fusionner codeql.yml et codeql-security.yml**
   - Économie: $0.24/mois
   - Délai: 1-2 mois

2. **Évaluer redondance testing.yml vs testing-compliance.yml**
   - Potentiel de consolidation
   - Délai: 2-3 mois

3. **Implémenter caching inter-workflows**
   - Réduction temps: 20-30%
   - Délai: 3-6 mois

---

## Documentation

- **Guide complet:** `.github/WORKFLOWS.md`
- **Rapport d'optimisation:** `.github/WORKFLOW_OPTIMIZATION_REPORT.md`
- **Référence rapide:** `.github/WORKFLOWS_QUICK_REFERENCE.md`
- **Cet inventaire:** `.github/WORKFLOWS_INVENTORY.md`

---

**Maintenu par:** @fil04331  
**Dernière révision:** 2024-12-28
