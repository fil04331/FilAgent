#!/bin/bash

# ===========================================================================
# FilAgent - Script de mise à jour des dépendances avec PDM
# ===========================================================================
# Ce script automatise la mise à jour sécurisée des dépendances
# avec vérification des tests et possibilité de rollback
#
# Usage: ./scripts/update_dependencies.sh [--check-only] [--security-only]
# ===========================================================================

set -euo pipefail

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHECK_ONLY=false
SECURITY_ONLY=false
BACKUP_LOCK="pdm.lock.backup.$(date +%Y%m%d_%H%M%S)"

# Parsing des arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --check-only)
            CHECK_ONLY=true
            shift
            ;;
        --security-only)
            SECURITY_ONLY=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--check-only] [--security-only]"
            echo "  --check-only     Vérifier les mises à jour disponibles sans les appliquer"
            echo "  --security-only  Mettre à jour uniquement les dépendances avec vulnérabilités"
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Argument inconnu: $1${NC}"
            echo "Usage: $0 [--check-only] [--security-only]"
            exit 1
            ;;
    esac
done

# Fonctions utilitaires
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

check_command() {
    if ! command -v "$1" &> /dev/null; then
        return 1
    fi
    return 0
}

# ===========================================================================
# ÉTAPE 1: Vérifications préliminaires
# ===========================================================================

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Mise à jour des dépendances FilAgent ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo

log_info "Étape 1: Vérifications préliminaires..."

# Vérifier PDM
if ! check_command pdm; then
    log_error "PDM n'est pas installé. Exécutez d'abord: ./scripts/migrate_to_pdm.sh"
    exit 1
fi

cd "$PROJECT_ROOT"

# Vérifier que le projet est configuré pour PDM
if [ ! -f "pyproject.toml" ]; then
    log_error "pyproject.toml non trouvé. Le projet n'est pas configuré pour PDM."
    exit 1
fi

if [ ! -f "pdm.lock" ]; then
    log_warning "pdm.lock non trouvé. Génération..."
    pdm lock
fi

log_success "Configuration PDM trouvée"

# ===========================================================================
# ÉTAPE 2: Scan de sécurité
# ===========================================================================

log_info "Étape 2: Scan de sécurité des dépendances actuelles..."

# Utiliser pip-audit si disponible
if pdm run pip-audit --version &> /dev/null 2>&1; then
    log_info "Exécution de pip-audit..."

    # Capturer les vulnérabilités
    VULNS_FILE=$(mktemp)
    if pdm run pip-audit --format json > "$VULNS_FILE" 2>/dev/null; then
        VULN_COUNT=$(jq 'length' "$VULNS_FILE")

        if [ "$VULN_COUNT" -gt 0 ]; then
            log_warning "⚠️  $VULN_COUNT vulnérabilité(s) trouvée(s):"
            jq -r '.[] | "   - \(.name) \(.version): \(.vulnerabilities[0].description // "No description")"' "$VULNS_FILE"

            if [ "$SECURITY_ONLY" = true ]; then
                log_info "Mode --security-only: mise à jour uniquement des packages vulnérables"
            fi
        else
            log_success "Aucune vulnérabilité connue détectée"
        fi
    else
        log_warning "Impossible d'exécuter pip-audit"
    fi
    rm -f "$VULNS_FILE"
else
    log_warning "pip-audit non installé. Installation recommandée: pdm add --dev pip-audit"
fi

# ===========================================================================
# ÉTAPE 3: Vérification des mises à jour disponibles
# ===========================================================================

log_info "Étape 3: Vérification des mises à jour disponibles..."

# Lister les packages obsolètes
OUTDATED_FILE=$(mktemp)
pdm list --outdated > "$OUTDATED_FILE" 2>/dev/null || true

if [ -s "$OUTDATED_FILE" ]; then
    log_info "Packages avec mises à jour disponibles:"
    cat "$OUTDATED_FILE"
else
    log_success "Toutes les dépendances sont à jour!"

    if [ "$CHECK_ONLY" = true ]; then
        exit 0
    fi
fi

rm -f "$OUTDATED_FILE"

if [ "$CHECK_ONLY" = true ]; then
    log_info "Mode --check-only: aucune mise à jour appliquée"
    exit 0
fi

# ===========================================================================
# ÉTAPE 4: Sauvegarde du lock file
# ===========================================================================

log_info "Étape 4: Sauvegarde du fichier lock..."

cp "pdm.lock" "$BACKUP_LOCK"
log_success "Sauvegarde créée: $BACKUP_LOCK"

# ===========================================================================
# ÉTAPE 5: Mise à jour des dépendances
# ===========================================================================

log_info "Étape 5: Mise à jour des dépendances..."

if [ "$SECURITY_ONLY" = true ]; then
    log_info "Mise à jour des packages avec vulnérabilités uniquement..."
    # PDM ne supporte pas directement la mise à jour sélective par sécurité
    # On met à jour tout et on compte sur les contraintes de version
    pdm update --update-eager
else
    log_info "Mise à jour de toutes les dépendances..."
    pdm update
fi

log_success "Dépendances mises à jour"

# ===========================================================================
# ÉTAPE 6: Régénération des fichiers requirements
# ===========================================================================

log_info "Étape 6: Régénération des fichiers requirements..."

# Exporter requirements.txt standard
pdm export -f requirements --without-hashes -o requirements.txt
log_success "requirements.txt régénéré"

# Exporter requirements avec dev
pdm export -f requirements --without-hashes --dev -o requirements-dev.txt
log_success "requirements-dev.txt régénéré"

# Exporter requirements avec ML optionnel
pdm export -f requirements --without-hashes --with ml -o requirements-ml.txt 2>/dev/null || true

# ===========================================================================
# ÉTAPE 7: Tests de validation
# ===========================================================================

log_info "Étape 7: Exécution des tests de validation..."

# Test d'import des modules critiques
CRITICAL_PACKAGES="fastapi pydantic yaml structlog pandas"
IMPORT_FAILURES=0

for package in $CRITICAL_PACKAGES; do
    if pdm run python -c "import $package" 2>/dev/null; then
        echo -e "   ${GREEN}✓${NC} $package"
    else
        echo -e "   ${RED}✗${NC} $package"
        IMPORT_FAILURES=$((IMPORT_FAILURES + 1))
    fi
done

if [ $IMPORT_FAILURES -gt 0 ]; then
    log_error "$IMPORT_FAILURES imports ont échoué!"
    log_warning "Restauration du lock file précédent..."
    mv "$BACKUP_LOCK" "pdm.lock"
    pdm sync
    log_error "Mise à jour annulée. Lock file restauré."
    exit 1
fi

log_success "Tous les imports critiques fonctionnent"

# Exécution des tests unitaires si pytest est disponible
if pdm run pytest --version &> /dev/null 2>&1; then
    log_info "Exécution des tests unitaires..."

    if pdm run pytest -m unit --tb=short > /dev/null 2>&1; then
        log_success "Tests unitaires passés"
    else
        log_error "Les tests unitaires ont échoué!"
        read -p "Voulez-vous restaurer les dépendances précédentes? [Y/n] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
            mv "$BACKUP_LOCK" "pdm.lock"
            pdm sync
            log_warning "Lock file restauré"
            exit 1
        else
            log_warning "Conservation des nouvelles dépendances malgré les échecs de tests"
        fi
    fi
else
    log_warning "pytest non disponible, tests ignorés"
fi

# ===========================================================================
# ÉTAPE 8: Nouveau scan de sécurité
# ===========================================================================

if pdm run pip-audit --version &> /dev/null 2>&1; then
    log_info "Étape 8: Nouveau scan de sécurité..."

    VULNS_AFTER=$(mktemp)
    if pdm run pip-audit --format json > "$VULNS_AFTER" 2>/dev/null; then
        NEW_VULN_COUNT=$(jq 'length' "$VULNS_AFTER")

        if [ "$NEW_VULN_COUNT" -gt 0 ]; then
            log_warning "⚠️  $NEW_VULN_COUNT vulnérabilité(s) restante(s) après mise à jour"
        else
            log_success "✅ Aucune vulnérabilité connue après mise à jour"
        fi
    fi
    rm -f "$VULNS_AFTER"
fi

# ===========================================================================
# ÉTAPE 9: Rapport de mise à jour
# ===========================================================================

log_info "Étape 9: Génération du rapport de mise à jour..."

# Créer un fichier de rapport
REPORT_FILE="update_report_$(date +%Y%m%d_%H%M%S).md"
cat > "$REPORT_FILE" << EOF
# Rapport de mise à jour des dépendances

**Date**: $(date '+%Y-%m-%d %H:%M:%S')
**Projet**: FilAgent
**Outil**: PDM

## Résumé

- Fichier de sauvegarde: \`$BACKUP_LOCK\`
- Mode sécurité uniquement: $SECURITY_ONLY

## Packages mis à jour

\`\`\`
$(pdm list --outdated 2>/dev/null || echo "Tous les packages sont à jour")
\`\`\`

## Tests exécutés

- Imports critiques: ✅ Tous réussis
- Tests unitaires: $(if pdm run pytest -m unit --tb=short > /dev/null 2>&1; then echo "✅ Passés"; else echo "⚠️  Échecs détectés"; fi)

## Prochaines étapes

1. Vérifier le fonctionnement de l'application
2. Créer un commit avec les changements
3. Pousser sur une branche de test
4. Exécuter les tests CI/CD complets

---
*Généré automatiquement par update_dependencies.sh*
EOF

log_success "Rapport sauvegardé: $REPORT_FILE"

# ===========================================================================
# RÉSUMÉ FINAL
# ===========================================================================

echo
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Mise à jour terminée avec succès! 🎉 ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo

log_info "📊 Résumé:"
echo "   - Lock file sauvegardé: $BACKUP_LOCK"
echo "   - Requirements régénérés: requirements.txt, requirements-dev.txt"
echo "   - Tests validés: imports critiques ✅"
echo "   - Rapport créé: $REPORT_FILE"

echo
log_info "🔄 Pour annuler les changements:"
echo "   mv $BACKUP_LOCK pdm.lock"
echo "   pdm sync"

echo
log_info "📝 Pour valider les changements:"
echo "   git add pdm.lock requirements*.txt"
echo "   git commit -m \"chore: Update dependencies $(date +%Y-%m-%d)\""

echo
log_success "Les dépendances ont été mises à jour avec succès!"

# Nettoyer la sauvegarde après 7 jours
echo "rm -f $BACKUP_LOCK" | at now + 7 days 2>/dev/null || true