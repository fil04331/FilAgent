#!/usr/bin/env bash
#
# FilAgent - Developer Environment Setup Script
#
# Ce script configure automatiquement l'environnement de développement :
# - Crée et active venv
# - Installe dépendances
# - Configure pre-commit hooks
# - Vérifie le setup
#
# Usage:
#   ./scripts/setup-dev.sh
#
# Options:
#   --skip-venv     : Skip création venv (utilise env existant)
#   --skip-hooks    : Skip installation pre-commit hooks
#   --quick         : Installation rapide (dev uniquement, pas test)
#   --help          : Affiche ce message

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Couleurs pour output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Flags
SKIP_VENV=false
SKIP_HOOKS=false
QUICK_INSTALL=false

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

print_header() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║         FilAgent - Developer Setup Script                ║"
    echo "║                                                           ║"
    echo "║  Configuration automatique environnement développement    ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo ""
}

show_help() {
    cat << EOF
FilAgent Developer Setup Script

Usage:
  ./scripts/setup-dev.sh [OPTIONS]

Options:
  --skip-venv     Skip création environnement virtuel
  --skip-hooks    Skip installation pre-commit hooks
  --quick         Installation rapide (dev seulement)
  --help          Affiche ce message

Exemples:
  ./scripts/setup-dev.sh                  # Setup complet
  ./scripts/setup-dev.sh --quick          # Installation rapide
  ./scripts/setup-dev.sh --skip-venv      # Utilise env existant

EOF
    exit 0
}

# Parser arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-venv)
            SKIP_VENV=true
            shift
            ;;
        --skip-hooks)
            SKIP_HOOKS=true
            shift
            ;;
        --quick)
            QUICK_INSTALL=true
            shift
            ;;
        --help|-h)
            show_help
            ;;
        *)
            log_error "Option inconnue: $1"
            show_help
            ;;
    esac
done

# Vérifier OS
check_os() {
    log_info "Détection du système d'exploitation..."

    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="Linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macOS"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        OS="Windows"
    else
        OS="Unknown"
    fi

    log_success "OS détecté: $OS"
}

# Vérifier Python version
check_python() {
    log_info "Vérification de Python..."

    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 n'est pas installé !"
        log_info "Installez Python 3.10+ depuis https://www.python.org/"
        exit 1
    fi

    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [[ $PYTHON_MAJOR -lt 3 ]] || [[ $PYTHON_MAJOR -eq 3 && $PYTHON_MINOR -lt 10 ]]; then
        log_error "Python 3.10+ requis, version actuelle: $PYTHON_VERSION"
        exit 1
    fi

    log_success "Python $PYTHON_VERSION OK"
}

# Créer environnement virtuel
setup_venv() {
    if [[ "$SKIP_VENV" == true ]]; then
        log_warning "Skip création venv (--skip-venv)"
        return
    fi

    log_info "Création de l'environnement virtuel..."

    if [[ -d "venv" ]]; then
        log_warning "Environnement virtuel existe déjà"
        read -p "Supprimer et recréer ? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf venv
            python3 -m venv venv
            log_success "Environnement virtuel recréé"
        else
            log_info "Utilisation de l'environnement existant"
        fi
    else
        python3 -m venv venv
        log_success "Environnement virtuel créé"
    fi
}

# Activer environnement virtuel
activate_venv() {
    if [[ "$SKIP_VENV" == true ]]; then
        return
    fi

    log_info "Activation de l'environnement virtuel..."

    if [[ -f "venv/bin/activate" ]]; then
        source venv/bin/activate
        log_success "Environnement virtuel activé"
    elif [[ -f "venv/Scripts/activate" ]]; then
        source venv/Scripts/activate
        log_success "Environnement virtuel activé (Windows)"
    else
        log_error "Impossible de trouver venv/bin/activate"
        exit 1
    fi
}

# Installer dépendances
install_dependencies() {
    log_info "Installation des dépendances..."

    # Upgrade pip
    python -m pip install --upgrade pip setuptools wheel

    if [[ "$QUICK_INSTALL" == true ]]; then
        log_info "Installation rapide (dev uniquement)..."
        pip install -e ".[dev]"
    else
        log_info "Installation complète (dev + test)..."
        pip install -e ".[dev,test]"
    fi

    log_success "Dépendances installées"
}

# Installer pre-commit hooks
setup_precommit() {
    if [[ "$SKIP_HOOKS" == true ]]; then
        log_warning "Skip installation pre-commit hooks (--skip-hooks)"
        return
    fi

    log_info "Configuration des pre-commit hooks..."

    if ! command -v pre-commit &> /dev/null; then
        log_warning "pre-commit n'est pas installé, installation..."
        pip install pre-commit
    fi

    # Installer hooks
    pre-commit install
    pre-commit install --hook-type commit-msg

    log_success "Pre-commit hooks installés"

    # Optionnel : exécuter sur tous les fichiers
    read -p "Exécuter pre-commit sur tous les fichiers ? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Exécution de pre-commit (peut prendre quelques minutes)..."
        pre-commit run --all-files || true
        log_success "Pre-commit exécuté"
    fi
}

# Vérifier installation
verify_setup() {
    log_info "Vérification de l'installation..."

    local errors=0

    # Test imports
    echo ""
    echo "Test des imports Python..."

    if python -c "import runtime; print('  ✅ runtime')"; then
        : # Success
    else
        log_error "  ❌ runtime"
        ((errors++))
    fi

    if python -c "import planner; print('  ✅ planner')"; then
        : # Success
    else
        log_error "  ❌ planner"
        ((errors++))
    fi

    if python -c "import memory; print('  ✅ memory')"; then
        : # Success
    else
        log_error "  ❌ memory"
        ((errors++))
    fi

    if python -c "import tools; print('  ✅ tools')"; then
        : # Success
    else
        log_error "  ❌ tools"
        ((errors++))
    fi

    # Vérifier outils de développement
    echo ""
    echo "Vérification des outils..."

    local tools=("black" "isort" "flake8" "pytest" "mypy")
    for tool in "${tools[@]}"; do
        if command -v $tool &> /dev/null; then
            echo "  ✅ $tool"
        else
            log_warning "  ⚠️  $tool non trouvé"
        fi
    done

    if [[ $errors -gt 0 ]]; then
        log_error "Erreurs détectées pendant la vérification"
        return 1
    else
        log_success "Vérification réussie !"
        return 0
    fi
}

# Afficher next steps
show_next_steps() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                  Setup Terminé ! 🎉                       ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo ""
    echo "Prochaines étapes :"
    echo ""
    echo "1. Activer l'environnement virtuel :"
    if [[ "$OS" == "Windows" ]]; then
        echo "   ${BLUE}venv\\Scripts\\activate${NC}"
    else
        echo "   ${BLUE}source venv/bin/activate${NC}"
    fi
    echo ""
    echo "2. Vérifier que tout fonctionne :"
    echo "   ${BLUE}pytest tests/ -v${NC}"
    echo ""
    echo "3. Formater le code :"
    echo "   ${BLUE}black .${NC}"
    echo "   ${BLUE}isort .${NC}"
    echo ""
    echo "4. Lancer le serveur :"
    echo "   ${BLUE}python runtime/server.py${NC}"
    echo ""
    echo "5. Lire la documentation :"
    echo "   ${BLUE}docs/CONTRIBUTING.md${NC}"
    echo ""
    echo "📚 Ressources :"
    echo "   - README.md           : Vue d'ensemble du projet"
    echo "   - INSTALLATION.md     : Guide d'installation"
    echo "   - docs/CONTRIBUTING.md : Guide de contribution"
    echo ""
    echo "🆘 Besoin d'aide ?"
    echo "   - GitHub Issues : https://github.com/fil04331/FilAgent/issues"
    echo "   - Documentation : https://github.com/fil04331/FilAgent"
    echo ""
}

# ========================================
# Main Script
# ========================================

main() {
    print_header

    # Checks préliminaires
    check_os
    check_python

    # Setup
    setup_venv
    activate_venv
    install_dependencies
    setup_precommit

    # Vérification
    if verify_setup; then
        show_next_steps
        exit 0
    else
        log_error "Setup incomplet, vérifiez les erreurs ci-dessus"
        exit 1
    fi
}

# Exécuter main
main "$@"
