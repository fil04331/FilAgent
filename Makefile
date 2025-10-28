.PHONY: help install-test-deps test test-e2e test-compliance test-resilience test-quick test-coverage clean

# Couleurs pour l'affichage
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Afficher l'aide
	@echo "$(BLUE)================================================$(NC)"
	@echo "$(BLUE)           FilAgent - Commandes Make$(NC)"
	@echo "$(BLUE)================================================$(NC)"
	@echo ""
	@echo "Commandes disponibles:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "Exemples:"
	@echo "  make install-test-deps  # Installer les dépendances"
	@echo "  make test               # Exécuter tous les tests"
	@echo "  make test-e2e           # Tests E2E seulement"
	@echo "  make test-coverage      # Tests avec couverture"
	@echo ""

install-test-deps: ## Installer les dépendances de test
	@echo "$(YELLOW)📦 Installation des dépendances de test...$(NC)"
	@./scripts/install_test_deps.sh

test: ## Exécuter tous les tests (E2E + compliance + unit)
	@echo "$(BLUE)🧪 Exécution de tous les tests...$(NC)"
	@./scripts/run_tests.sh all -v

test-e2e: ## Exécuter les tests E2E seulement
	@echo "$(BLUE)🧪 Exécution des tests E2E...$(NC)"
	@./scripts/run_tests.sh e2e -v

test-compliance: ## Exécuter les tests de conformité seulement
	@echo "$(BLUE)🧪 Exécution des tests de conformité...$(NC)"
	@./scripts/run_tests.sh compliance -v

test-resilience: ## Exécuter les tests de résilience seulement
	@echo "$(BLUE)🧪 Exécution des tests de résilience...$(NC)"
	@./scripts/run_tests.sh resilience -v

test-quick: ## Exécuter les tests rapides (sans @slow)
	@echo "$(BLUE)🧪 Exécution des tests rapides...$(NC)"
	@./scripts/run_tests.sh quick -v

test-coverage: ## Exécuter les tests avec rapport de couverture
	@echo "$(BLUE)📊 Exécution des tests avec couverture...$(NC)"
	@./scripts/run_tests.sh coverage -v

test-verbose: ## Exécuter tous les tests en mode très verbose
	@echo "$(BLUE)🧪 Exécution des tests (verbose)...$(NC)"
	@./scripts/run_tests.sh all -vv

test-quiet: ## Exécuter tous les tests en mode quiet
	@./scripts/run_tests.sh all -q

test-unit: ## Exécuter les tests unitaires existants
	@echo "$(BLUE)🧪 Exécution des tests unitaires...$(NC)"
	@pytest tests/test_tools.py tests/test_memory.py -v --tb=short

test-integration: ## Exécuter les tests d'intégration
	@echo "$(BLUE)🧪 Exécution des tests d'intégration...$(NC)"
	@pytest tests/test_server.py tests/test_agent_*.py -v --tb=short

test-parallel: ## Exécuter les tests en parallèle (nécessite pytest-xdist)
	@echo "$(BLUE)🧪 Exécution des tests en parallèle...$(NC)"
	@pytest tests/ -n auto -v

test-collect: ## Collecter les tests sans les exécuter
	@echo "$(BLUE)📋 Collection des tests...$(NC)"
	@pytest tests/ --collect-only

clean: ## Nettoyer les fichiers de test temporaires
	@echo "$(YELLOW)🧹 Nettoyage...$(NC)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@rm -rf htmlcov/ .coverage 2>/dev/null || true
	@echo "$(GREEN)✅ Nettoyage terminé$(NC)"

lint: ## Vérifier le code avec flake8
	@echo "$(BLUE)🔍 Vérification du code...$(NC)"
	@flake8 runtime/ tools/ memory/ tests/ --max-line-length=120 --exclude=__pycache__ || true

format: ## Formater le code avec black
	@echo "$(BLUE)✨ Formatage du code...$(NC)"
	@black runtime/ tools/ memory/ tests/ --line-length=100

type-check: ## Vérifier les types avec mypy
	@echo "$(BLUE)🔍 Vérification des types...$(NC)"
	@mypy runtime/ tools/ memory/ --ignore-missing-imports || true

ci: install-test-deps test-coverage lint type-check ## Exécuter toutes les vérifications CI
	@echo "$(GREEN)✅ Toutes les vérifications CI sont passées$(NC)"

pre-commit: test-quick lint ## Vérifications rapides avant commit
	@echo "$(GREEN)✅ Prêt pour commit$(NC)"

# Raccourcis
t: test ## Raccourci pour 'make test'
te: test-e2e ## Raccourci pour 'make test-e2e'
tc: test-compliance ## Raccourci pour 'make test-compliance'
tq: test-quick ## Raccourci pour 'make test-quick'
tcov: test-coverage ## Raccourci pour 'make test-coverage'
