# Guide de Test FilAgent

Ce document explique comment exécuter les tests E2E et de conformité pour FilAgent.

## 🚀 Démarrage rapide

### 1. Installation des dépendances

**Option A: Utiliser le script d'installation**
```bash
./scripts/install_test_deps.sh
```

**Option B: Utiliser Make**
```bash
make install-test-deps
```

**Option C: Installation manuelle**
```bash
pip install pytest pytest-cov pytest-asyncio pytest-mock
pip install fastapi uvicorn httpx pyyaml pydantic structlog aiosqlite cryptography cffi
```

### 2. Exécuter les tests

**Tous les tests:**
```bash
make test
# ou
./scripts/run_tests.sh all
```

**Tests E2E seulement:**
```bash
make test-e2e
# ou
./scripts/run_tests.sh e2e
```

**Tests de conformité seulement:**
```bash
make test-compliance
# ou
./scripts/run_tests.sh compliance
```

**Tests rapides (sans @slow):**
```bash
make test-quick
# ou
./scripts/run_tests.sh quick
```

**Avec couverture de code:**
```bash
make test-coverage
# ou
./scripts/run_tests.sh coverage
```

## 📋 Commandes Make disponibles

```bash
make help                  # Afficher toutes les commandes
make test                  # Tous les tests
make test-e2e              # Tests E2E
make test-compliance       # Tests de conformité
make test-resilience       # Tests de résilience
make test-quick            # Tests rapides
make test-coverage         # Tests avec couverture
make test-unit             # Tests unitaires
make test-parallel         # Tests en parallèle
make clean                 # Nettoyer les fichiers temporaires
make pre-commit            # Vérifications avant commit
```

## 🧪 Suites de tests

### Tests E2E (23 tests)
Fichier: `tests/test_integration_e2e.py`

- **Flux complets** (6 tests): Chat → génération → outils → DR → provenance
- **Résilience** (10 tests): Fallbacks, timeouts, middlewares défaillants
- **Performance** (3 tests): Concurrence, messages volumineux
- **Intégrité** (1 test): Ordre des messages
- **Santé** (3 tests): Health checks, endpoints

**Exécuter:**
```bash
pytest tests/test_integration_e2e.py -v
```

### Tests de Conformité (21 tests)
Fichier: `tests/test_compliance_flow.py`

- **WORM Integrity** (7 tests): Merkle Tree, append-only, digests
- **Signatures EdDSA** (5 tests): Création, vérification, tampering
- **Provenance PROV-JSON** (9 tests): W3C standard, entités, activités

**Exécuter:**
```bash
pytest tests/test_compliance_flow.py -v
```

## 🏷️ Markers pytest

Les tests utilisent des markers pour filtrage:

```bash
# Tests E2E seulement
pytest -m e2e -v

# Tests de conformité seulement
pytest -m compliance -v

# Tests de résilience seulement
pytest -m resilience -v

# Exclure les tests lents
pytest -m "not slow" -v
```

## 📊 Rapport de couverture

Pour générer un rapport de couverture HTML:

```bash
make test-coverage
# Le rapport est dans: htmlcov/index.html
```

Ou manuellement:
```bash
pytest tests/ \
    --cov=runtime \
    --cov=tools \
    --cov=memory \
    --cov-report=html \
    --cov-report=term-missing
```

## 🔧 Scripts disponibles

### `scripts/install_test_deps.sh`
Installe toutes les dépendances nécessaires pour les tests.

```bash
./scripts/install_test_deps.sh
```

### `scripts/run_tests.sh`
Exécute les tests avec différentes options.

```bash
# Syntaxe
./scripts/run_tests.sh [type] [verbosity]

# Exemples
./scripts/run_tests.sh all -v        # Tous les tests
./scripts/run_tests.sh e2e -vv       # E2E verbose
./scripts/run_tests.sh compliance -q # Compliance quiet
./scripts/run_tests.sh quick         # Tests rapides
./scripts/run_tests.sh coverage      # Avec couverture
```

## ⚡ Workflow recommandé

### Avant de commit

```bash
# Option 1: Vérifications rapides
make pre-commit

# Option 2: Tests complets
make test

# Option 3: Tests + couverture
make test-coverage
```

### CI/CD

```bash
# Installation + tests + vérifications
make ci
```

## 📝 Exemples d'utilisation

### Développement quotidien

```bash
# 1. Installer les dépendances (une fois)
make install-test-deps

# 2. Pendant le développement (rapide)
make test-quick

# 3. Avant de commit
make pre-commit
```

### Validation complète

```bash
# 1. Tous les tests
make test

# 2. Avec couverture
make test-coverage

# 3. Vérifier le rapport
open htmlcov/index.html
```

### Debug de tests

```bash
# Tests très verbose
make test-verbose

# Un seul test
pytest tests/test_compliance_flow.py::test_worm_merkle_tree_basic -vv

# Avec traceback complet
pytest tests/test_integration_e2e.py -vv --tb=long

# S'arrêter au premier échec
pytest tests/ -x
```

### Tests en parallèle (plus rapide)

```bash
# Installer pytest-xdist
pip install pytest-xdist

# Exécuter en parallèle
make test-parallel
# ou
pytest tests/ -n auto
```

## 🐛 Troubleshooting

### ImportError: No module named 'fastapi'
```bash
./scripts/install_test_deps.sh
```

### Tests qui échouent avec "API mismatch"
Certains tests nécessitent des ajustements d'API. Voir `tests/README_E2E_COMPLIANCE.md` pour les détails.

### Timeout sur tests lents
```bash
# Augmenter le timeout pytest
pytest tests/ --timeout=300
```

### Erreurs de permissions sur scripts
```bash
chmod +x scripts/*.sh
```

## 📚 Documentation supplémentaire

- **Architecture des tests**: `tests/README_E2E_COMPLIANCE.md`
- **Fixtures avancés**: `tests/conftest.py`
- **Configuration pytest**: `pytest.ini`

## 🎯 Objectifs de couverture

| Composant | Objectif | Actuel |
|-----------|----------|---------|
| Runtime   | 80%      | TBD     |
| Tools     | 90%      | TBD     |
| Memory    | 85%      | TBD     |
| Middleware| 75%      | TBD     |

Pour mesurer:
```bash
make test-coverage
```

## ✅ Checklist avant commit

- [ ] `make install-test-deps` exécuté
- [ ] `make test-quick` passe
- [ ] Nouveaux tests ajoutés si nouvelles fonctionnalités
- [ ] Code formaté (`make format`)
- [ ] Lint passe (`make lint`)
- [ ] Couverture maintenue ou améliorée

## 🚀 Intégration continue

Les tests sont automatiquement exécutés sur:
- Chaque push vers une branche
- Chaque pull request
- Avant merge vers main

Configuration CI dans `.github/workflows/` (à créer).

## 💡 Tips

1. **Utiliser `make help`** pour voir toutes les commandes
2. **Tests rapides pendant développement**: `make test-quick`
3. **Coverage avant PR**: `make test-coverage`
4. **Debug avec `-vv --tb=long`**
5. **Tests parallèles pour gagner du temps**: `make test-parallel`

## 📞 Support

Pour des questions sur les tests:
- Voir la documentation: `tests/README_E2E_COMPLIANCE.md`
- Issues GitHub: https://github.com/fil04331/FilAgent/issues
