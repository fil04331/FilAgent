# Guide de Référence Rapide - GitHub Actions Workflows

## Workflows Actifs (6)

### 1. testing.yml - Tests & Qualité ⭐⭐⭐⭐⭐
**Déclenché:** Push/PR vers main  
**Durée:** ~3m  
**Jobs:** lint → security → test (3.11-3.12) → compliance → quality-gate  
**Commande locale:** `pdm run pytest --cov`

### 2. codeql.yml - Analyse Sécurité CodeQL ⭐⭐⭐⭐⭐
**Déclenché:** Push/PR (*.py), Dimanche 6h UTC  
**Durée:** ~2.5m  
**Queries:** security-and-quality  
**Résultats:** GitHub Security tab

### 3. codeql-security.yml - CodeQL + Checks Custom ⭐⭐⭐⭐
**Déclenché:** Push/PR, Dimanche 3h UTC  
**Durée:** ~2.5m  
**Spécificités:** Détection secrets, validation sandbox  
**Note:** À fusionner avec codeql.yml (Phase 4)

### 4. dependencies.yml - Sécurité Dépendances ⭐⭐⭐⭐
**Déclenché:** Push/PR (deps), 1er du mois 9h UTC, Manuel  
**Durée:** ~2m  
**Jobs:** validate-lock-file → security-audit → dependency-review → update-requirements  
**Commande locale:** `pdm list --outdated`

### 5. claude-code-review.yml - Revue AI ⭐⭐⭐
**Déclenché:** PR externes, Label needs-review  
**Durée:** ~1.5m  
**Conditions:** FIRST_TIME_CONTRIBUTOR, CONTRIBUTOR, ou label  
**Note:** Peut être désactivé si coûts API élevés

### 6. benchmarks.yml - Performance ⭐⭐⭐
**Déclenché:** 1er du mois 2h UTC, Manuel, Push fichiers critiques  
**Durée:** variable (max 2h)  
**Benchmarks:** HumanEval, MBPP, SWE-bench, Compliance  
**Commande locale:** `pdm run python eval/runner.py --benchmark humaneval`

---

## Commandes Utiles

### Tester localement avant push
```bash
# Linting complet
pdm run black --check .
pdm run flake8 .
pdm run mypy runtime/ planner/ tools/

# Tests avec couverture
pdm run pytest --cov=runtime --cov=planner --cov=tools --cov-fail-under=80

# Sécurité
pdm run bandit -r runtime/ planner/ tools/
pdm run pip-audit
pdm run safety check

# Benchmarks (local)
pdm run python eval/runner.py --benchmark humaneval --num-tasks 5
```

### Déclencher manuellement un workflow
```bash
# Via GitHub CLI
gh workflow run benchmarks.yml
gh workflow run dependencies.yml

# Via interface web
Actions tab → Select workflow → Run workflow
```

### Vérifier le statut des workflows
```bash
# Liste des workflows
gh workflow list

# Runs récents
gh run list --limit 10

# Logs d'un run
gh run view <run-id> --log
```

---

## Dépannage

### Workflow échoue sur lint
**Cause:** Code non formaté  
**Solution:** `pdm run black .`

### Workflow échoue sur tests
**Cause:** Tests cassés ou couverture < 80%  
**Solution:** Corriger tests, augmenter couverture

### Workflow échoue sur security
**Cause:** Vulnérabilités détectées  
**Solution:** `pdm update` puis vérifier pip-audit

### Workflow échoue sur dependencies
**Cause:** pdm.lock non synchronisé  
**Solution:** `pdm lock` puis commit

### Skip un workflow temporairement
**Solution:** Ajouter `[skip ci]` dans le message de commit

---

## Badges à Ajouter au README

```markdown
[![Tests](https://github.com/fil04331/FilAgent/actions/workflows/testing.yml/badge.svg)](https://github.com/fil04331/FilAgent/actions/workflows/testing.yml)
[![CodeQL](https://github.com/fil04331/FilAgent/actions/workflows/codeql.yml/badge.svg)](https://github.com/fil04331/FilAgent/actions/workflows/codeql.yml)
[![Dependencies](https://github.com/fil04331/FilAgent/actions/workflows/dependencies.yml/badge.svg)](https://github.com/fil04331/FilAgent/actions/workflows/dependencies.yml)
```

---

## Fréquences d'Exécution

| Workflow | Push/PR | Scheduled | Manuel |
|----------|---------|-----------|--------|
| testing.yml | ✅ Toujours | - | ✅ |
| codeql.yml | ✅ (*.py) | Dimanche 6h | ✅ |
| codeql-security.yml | ✅ | Dimanche 3h | ✅ |
| dependencies.yml | ✅ (deps) | 1er du mois | ✅ |
| claude-code-review.yml | ✅ (conditions) | - | - |
| benchmarks.yml | ✅ (critical) | 1er du mois | ✅ |

---

## Coûts Estimés (GitHub Actions Minutes)

| Workflow | Minutes/mois | Coût* |
|----------|--------------|-------|
| testing.yml | 120 | $2.00 |
| codeql.yml | 20 | $0.24 |
| codeql-security.yml | 20 | $0.24 |
| dependencies.yml | 6 | $0.12 |
| claude-code-review.yml | 7 | $0.10 |
| benchmarks.yml | 10 | $0.16 |
| **TOTAL** | **183** | **$2.86** |

*Basé sur $0.008 par minute (ubuntu-latest)

---

## Contact

**Mainteneur:** @fil04331  
**Documentation complète:** `.github/WORKFLOWS.md`  
**Rapport d'optimisation:** `.github/WORKFLOW_OPTIMIZATION_REPORT.md`

**Dernière mise à jour:** 2024-12-28
