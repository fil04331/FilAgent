#!/bin/bash
# Script pour exécuter les tests E2E et de conformité FilAgent

set -e  # Exit on error

# Couleurs pour output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "================================================"
echo "      Tests E2E et Conformité FilAgent"
echo "================================================"
echo ""

# Vérifier que pytest est installé
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}❌ pytest n'est pas installé${NC}"
    echo "Exécutez: ./scripts/install_test_deps.sh"
    exit 1
fi

# Parse arguments
TEST_TYPE="${1:-all}"
VERBOSE="${2:--v}"

echo -e "${BLUE}📋 Configuration:${NC}"
echo "  Test type: $TEST_TYPE"
echo "  Verbosity: $VERBOSE"
echo ""

# Function to run tests
run_test_suite() {
    local name=$1
    local pattern=$2
    local marker=$3

    echo -e "${YELLOW}🧪 Running $name...${NC}"

    if [ -n "$marker" ]; then
        pytest "$pattern" -m "$marker" "$VERBOSE" --tb=short
    else
        pytest "$pattern" "$VERBOSE" --tb=short
    fi

    local result=$?

    if [ $result -eq 0 ]; then
        echo -e "${GREEN}✅ $name: PASSED${NC}"
        echo ""
        return 0
    else
        echo -e "${RED}❌ $name: FAILED${NC}"
        echo ""
        return 1
    fi
}

# Track results
declare -i TOTAL_PASSED=0
declare -i TOTAL_FAILED=0

# Execute tests based on type
case $TEST_TYPE in
    "all")
        echo -e "${BLUE}📦 Exécution de TOUS les tests${NC}"
        echo ""

        # E2E tests
        if run_test_suite "E2E Tests" "tests/test_integration_e2e.py" ""; then
            ((TOTAL_PASSED++))
        else
            ((TOTAL_FAILED++))
        fi

        # Compliance tests
        if run_test_suite "Compliance Tests" "tests/test_compliance_flow.py" ""; then
            ((TOTAL_PASSED++))
        else
            ((TOTAL_FAILED++))
        fi

        # Existing tests
        if run_test_suite "Unit Tests" "tests/test_tools.py tests/test_memory.py" ""; then
            ((TOTAL_PASSED++))
        else
            ((TOTAL_FAILED++))
        fi
        ;;

    "e2e")
        echo -e "${BLUE}📦 Exécution des tests E2E${NC}"
        echo ""
        if run_test_suite "E2E Tests" "tests/test_integration_e2e.py" "e2e"; then
            ((TOTAL_PASSED++))
        else
            ((TOTAL_FAILED++))
        fi
        ;;

    "compliance")
        echo -e "${BLUE}📦 Exécution des tests de Conformité${NC}"
        echo ""
        if run_test_suite "Compliance Tests" "tests/test_compliance_flow.py" "compliance"; then
            ((TOTAL_PASSED++))
        else
            ((TOTAL_FAILED++))
        fi
        ;;

    "resilience")
        echo -e "${BLUE}📦 Exécution des tests de Résilience${NC}"
        echo ""
        if run_test_suite "Resilience Tests" "tests/test_integration_e2e.py" "resilience"; then
            ((TOTAL_PASSED++))
        else
            ((TOTAL_FAILED++))
        fi
        ;;

    "quick")
        echo -e "${BLUE}📦 Exécution des tests rapides (sans slow)${NC}"
        echo ""
        if pytest tests/ -m "not slow" "$VERBOSE" --tb=short; then
            echo -e "${GREEN}✅ Quick tests: PASSED${NC}"
            ((TOTAL_PASSED++))
        else
            echo -e "${RED}❌ Quick tests: FAILED${NC}"
            ((TOTAL_FAILED++))
        fi
        ;;

    "coverage")
        echo -e "${BLUE}📦 Exécution avec couverture de code${NC}"
        echo ""
        pytest tests/ \
            --cov=runtime \
            --cov=tools \
            --cov=memory \
            --cov-report=html \
            --cov-report=term-missing \
            "$VERBOSE"

        echo ""
        echo -e "${GREEN}📊 Rapport de couverture généré: htmlcov/index.html${NC}"
        exit 0
        ;;

    *)
        echo -e "${RED}❌ Type de test invalide: $TEST_TYPE${NC}"
        echo ""
        echo "Usage: $0 [type] [verbosity]"
        echo ""
        echo "Types disponibles:"
        echo "  all         - Tous les tests (défaut)"
        echo "  e2e         - Tests E2E seulement"
        echo "  compliance  - Tests de conformité seulement"
        echo "  resilience  - Tests de résilience seulement"
        echo "  quick       - Tests rapides (sans @slow)"
        echo "  coverage    - Tests avec rapport de couverture"
        echo ""
        echo "Verbosity:"
        echo "  -v          - Verbose (défaut)"
        echo "  -vv         - Very verbose"
        echo "  -q          - Quiet"
        exit 1
        ;;
esac

# Summary
echo ""
echo "================================================"
echo "                  RÉSUMÉ"
echo "================================================"
echo -e "Suites passées:  ${GREEN}$TOTAL_PASSED${NC}"
echo -e "Suites échouées: ${RED}$TOTAL_FAILED${NC}"
echo ""

if [ $TOTAL_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ TOUS LES TESTS SONT PASSÉS${NC}"
    exit 0
else
    echo -e "${RED}❌ CERTAINS TESTS ONT ÉCHOUÉ${NC}"
    exit 1
fi
