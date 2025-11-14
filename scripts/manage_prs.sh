#!/bin/bash
# Script de gestion des Pull Requests FilAgent
# Usage: ./scripts/manage_prs.sh [--dry-run]

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DRY_RUN=false
if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN=true
    echo -e "${YELLOW}🔍 Mode DRY RUN activé - aucune modification ne sera faite${NC}"
fi

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}❌ GitHub CLI (gh) n'est pas installé${NC}"
    echo "Installation: https://cli.github.com/"
    echo ""
    echo "Alternative: Suivez le plan manuel dans scripts/manage_prs.md"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo -e "${RED}❌ Non authentifié avec GitHub CLI${NC}"
    echo "Exécutez: gh auth login"
    exit 1
fi

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   FilAgent - Gestion des Pull Requests               ║${NC}"
echo -e "${BLUE}║   Ordre: Core → Client-facing → Cosmétique            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to run command with dry-run support
run_cmd() {
    local cmd="$1"
    local description="$2"

    echo -e "${BLUE}▶${NC} $description"

    if [[ "$DRY_RUN" == true ]]; then
        echo -e "${YELLOW}  [DRY RUN] $cmd${NC}"
    else
        eval "$cmd"
        if [[ $? -eq 0 ]]; then
            echo -e "${GREEN}  ✓ Succès${NC}"
        else
            echo -e "${RED}  ✗ Échec${NC}"
            return 1
        fi
    fi
    echo ""
}

# Function to prompt user
prompt_continue() {
    local message="$1"

    if [[ "$DRY_RUN" == true ]]; then
        return 0
    fi

    echo -e "${YELLOW}⚠️  $message${NC}"
    read -p "Continuer? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}❌ Opération annulée${NC}"
        exit 1
    fi
}

# ============================================================================
# PHASE 1: Fusion PR #118 (CRITIQUE)
# ============================================================================

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}PHASE 1: Fusion PR #118 - ComplianceGuardian Fix${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

run_cmd "gh pr view 118" "Afficher PR #118"

echo -e "${BLUE}Vérification des tests CI...${NC}"
run_cmd "gh pr checks 118" "Vérifier tests CI pour PR #118"

prompt_continue "Fusionner PR #118 maintenant?"

run_cmd "gh pr merge 118 --squash --delete-branch" "Fusionner PR #118 (squash + delete branch)"

echo -e "${GREEN}✅ PR #118 fusionnée avec succès${NC}"
echo ""

# ============================================================================
# PHASE 2: Fermeture des PRs Redondantes
# ============================================================================

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}PHASE 2: Fermeture des PRs Redondantes${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

PRS_TO_CLOSE=(114 110 104 117 116 108 107)
CLOSE_REASONS=(
    "Fermée: redondante avec #118 (déjà fusionnée)"
    "Fermée: modifications dépendances dépassées par #118"
    "Fermée: redondante ou dépassée par #118"
    "Fermée: redondante ou dépassée par #118"
    "Fermée: redondante ou dépassée par #118"
    "Fermée: tests/docs à gérer séparément (voir issues créées)"
    "Fermée: tests/docs extraits en issues séparées (voir #XXX)"
)

prompt_continue "Fermer ${#PRS_TO_CLOSE[@]} PRs redondantes?"

for i in "${!PRS_TO_CLOSE[@]}"; do
    pr_num="${PRS_TO_CLOSE[$i]}"
    reason="${CLOSE_REASONS[$i]}"

    echo -e "${BLUE}Fermeture PR #$pr_num${NC}"
    run_cmd "gh pr close $pr_num --comment \"$reason\"" "Fermer PR #$pr_num"
done

echo -e "${GREEN}✅ PRs redondantes fermées${NC}"
echo ""

# ============================================================================
# PHASE 3: Fusion PR #112 (Nettoyage)
# ============================================================================

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}PHASE 3: Fusion PR #112 - Nettoyage Scripts${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

run_cmd "gh pr view 112" "Afficher PR #112"
run_cmd "gh pr checks 112" "Vérifier tests CI pour PR #112"

prompt_continue "Fusionner PR #112 maintenant?"

run_cmd "gh pr merge 112 --squash --delete-branch" "Fusionner PR #112"

echo -e "${GREEN}✅ PR #112 fusionnée${NC}"
echo ""

# ============================================================================
# PHASE 4: Fusion PRs Dependabot
# ============================================================================

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}PHASE 4: Fusion PRs Dependabot${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

DEPENDABOT_PRS=(105 106)

prompt_continue "Fusionner ${#DEPENDABOT_PRS[@]} PRs Dependabot?"

for pr_num in "${DEPENDABOT_PRS[@]}"; do
    echo -e "${BLUE}Fusion PR #$pr_num (Dependabot)${NC}"
    run_cmd "gh pr view $pr_num" "Afficher PR #$pr_num"
    run_cmd "gh pr checks $pr_num" "Vérifier tests CI"
    run_cmd "gh pr merge $pr_num --squash --delete-branch" "Fusionner PR #$pr_num"
done

echo -e "${GREEN}✅ PRs Dependabot fusionnées${NC}"
echo ""

# ============================================================================
# PHASE 5: Création des Issues
# ============================================================================

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}PHASE 5: Création des Issues${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

prompt_continue "Créer les 3 issues pour prochaines étapes?"

# Issue 1: Tests Automatisés
echo -e "${BLUE}Création Issue: Tests Automatisés${NC}"
run_cmd "gh issue create \
    --title 'Ajouter tests automatisés pour renforcer la couverture' \
    --body-file scripts/issue_tests.md \
    --label 'testing,enhancement,good first issue'" \
    "Créer issue tests automatisés"

# Issue 2: Benchmarks
echo -e "${BLUE}Création Issue: Benchmarks${NC}"
run_cmd "gh issue create \
    --title 'Intégrer benchmarks HumanEval, MBPP et SWE-bench' \
    --body-file scripts/issue_benchmarks.md \
    --label 'evaluation,benchmark,enhancement,high priority'" \
    "Créer issue benchmarks"

# Issue 3: Policy Engine
echo -e "${BLUE}Création Issue: Policy Engine${NC}"
run_cmd "gh issue create \
    --title 'Étendre policy engine et RBAC complet' \
    --body-file scripts/issue_policy_engine.md \
    --label 'security,compliance,enhancement,high priority'" \
    "Créer issue policy engine"

echo -e "${GREEN}✅ Issues créées${NC}"
echo ""

# ============================================================================
# RÉSUMÉ FINAL
# ============================================================================

echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║               🎉 OPÉRATION TERMINÉE 🎉                 ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Résumé des actions:${NC}"
echo -e "  ${GREEN}✓${NC} PR #118 fusionnée (ComplianceGuardian fix)"
echo -e "  ${GREEN}✓${NC} 7 PRs redondantes fermées (#114, #110, #104, #117, #116, #108, #107)"
echo -e "  ${GREEN}✓${NC} PR #112 fusionnée (nettoyage scripts)"
echo -e "  ${GREEN}✓${NC} PRs Dependabot fusionnées (#105, #106)"
echo -e "  ${GREEN}✓${NC} 3 issues créées pour prochaines étapes"
echo ""
echo -e "${BLUE}Prochaines étapes:${NC}"
echo -e "  1. Vérifier que main est stable: ${YELLOW}pytest${NC}"
echo -e "  2. Consulter les nouvelles issues créées"
echo -e "  3. Planifier le travail sur tests/benchmarks/policy engine"
echo ""
echo -e "${GREEN}✅ Code base stabilisé et roadmap clarifiée!${NC}"
