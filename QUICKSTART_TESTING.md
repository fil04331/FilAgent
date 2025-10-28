# 🚀 Quick Start - Tests FilAgent

## Installation (une fois)

```bash
# Installer les dépendances de test
make install-test-deps
```

## Exécution des tests

### ⚡ Tests rapides (recommandé pendant développement)
```bash
make test-quick
```

### 🧪 Tous les tests
```bash
make test
```

### 📋 Tests par catégorie

```bash
# Tests E2E seulement
make test-e2e

# Tests de conformité seulement
make test-compliance

# Tests de résilience seulement
make test-resilience
```

### 📊 Tests avec couverture
```bash
make test-coverage
# Voir le rapport: htmlcov/index.html
```

## ✅ Avant de commit

```bash
# Option 1: Vérifications rapides
make pre-commit

# Option 2: Tous les tests
make test
```

## 🔧 Commandes alternatives (sans Make)

```bash
# Installation
./scripts/install_test_deps.sh

# Tous les tests
./scripts/run_tests.sh all

# Tests E2E
./scripts/run_tests.sh e2e

# Tests rapides
./scripts/run_tests.sh quick
```

## 📚 Documentation complète

- **Guide complet**: `TESTING.md`
- **Architecture des tests**: `tests/README_E2E_COMPLIANCE.md`
- **Aide Make**: `make help`

## 🐛 En cas de problème

```bash
# Réinstaller les dépendances
make install-test-deps

# Nettoyer les fichiers temporaires
make clean

# Voir tous les tests disponibles
make test-collect
```

## 💡 Tips

- Utilisez `make test-quick` pendant le développement (plus rapide)
- Exécutez `make test-coverage` avant de faire une PR
- `make help` pour voir toutes les commandes disponibles
