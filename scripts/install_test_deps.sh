#!/bin/bash
# Script pour installer les dépendances de test pour FilAgent

set -e  # Exit on error

echo "================================================"
echo "Installation des dépendances de test FilAgent"
echo "================================================"
echo ""

# Couleurs pour output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Vérifier si pip est disponible
if ! command -v pip &> /dev/null; then
    echo -e "${RED}❌ pip n'est pas installé${NC}"
    exit 1
fi

echo -e "${YELLOW}📦 Installation des dépendances de test...${NC}"
echo ""

# Core testing framework
echo "→ pytest et plugins..."
pip install -q pytest pytest-cov pytest-asyncio pytest-mock

# FastAPI testing
echo "→ FastAPI et dépendances..."
pip install -q fastapi uvicorn httpx

# Core dependencies
echo "→ Core dependencies..."
pip install -q pyyaml pydantic structlog aiosqlite

# Cryptography
echo "→ Cryptography..."
pip install -q cryptography cffi

# Optional but recommended
echo "→ Optional dependencies..."
pip install -q pytest-xdist  # Parallel test execution

echo ""
echo -e "${GREEN}✅ Toutes les dépendances sont installées${NC}"
echo ""

# Vérifier l'installation
echo "Vérification de l'installation..."
python -c "import pytest; print(f'  pytest {pytest.__version__}')"
python -c "import fastapi; print(f'  fastapi {fastapi.__version__}')"
python -c "import cryptography; print(f'  cryptography {cryptography.__version__}')"

echo ""
echo -e "${GREEN}✅ Installation terminée avec succès${NC}"
echo ""
echo "Pour exécuter les tests:"
echo "  ./scripts/run_tests.sh"
echo "  ou: make test"
