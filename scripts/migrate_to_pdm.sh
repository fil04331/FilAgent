#!/bin/bash

# ===========================================================================
# FilAgent - Script de migration vers PDM
# ===========================================================================
# Ce script automatise la migration de pip/requirements.txt vers PDM
# Il sauvegarde l'environnement existant et configure PDM pour le projet
#
# Usage: ./scripts/migrate_to_pdm.sh [--no-backup]
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
BACKUP_DIR="$PROJECT_ROOT/.migration_backup_$(date +%Y%m%d_%H%M%S)"
PYTHON_VERSION="3.12"
SKIP_BACKUP=false

# Parsing des arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-backup)
            SKIP_BACKUP=true
            shift
            ;;
        *)
            echo -e "${RED}❌ Argument inconnu: $1${NC}"
            echo "Usage: $0 [--no-backup]"
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
# ÉTAPE 1: Vérification des prérequis
# ===========================================================================

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Migration FilAgent vers PDM          ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo

log_info "Étape 1: Vérification des prérequis..."

# Vérifier Python
if ! check_command python3; then
    log_error "Python 3 n'est pas installé"
    exit 1
fi

PYTHON_CURRENT=$(python3 --version | cut -d' ' -f2)
log_success "Python trouvé: $PYTHON_CURRENT"

# Vérifier pip
if ! check_command pip3; then
    log_error "pip n'est pas installé"
    exit 1
fi
log_success "pip trouvé"

# Vérifier pipx (pour installer PDM)
if ! check_command pipx; then
    log_warning "pipx n'est pas installé. Installation..."
    python3 -m pip install --user pipx
    python3 -m pipx ensurepath

    # Recharger le PATH
    export PATH="$HOME/.local/bin:$PATH"

    if ! check_command pipx; then
        log_error "Impossible d'installer pipx"
        exit 1
    fi
fi
log_success "pipx trouvé"

# ===========================================================================
# ÉTAPE 2: Sauvegarde de l'environnement existant
# ===========================================================================

if [ "$SKIP_BACKUP" = false ]; then
    log_info "Étape 2: Sauvegarde de l'environnement existant..."

    mkdir -p "$BACKUP_DIR"

    # Sauvegarder requirements.txt
    if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
        cp "$PROJECT_ROOT/requirements.txt" "$BACKUP_DIR/"
        log_success "requirements.txt sauvegardé"
    fi

    if [ -f "$PROJECT_ROOT/requirements-optional.txt" ]; then
        cp "$PROJECT_ROOT/requirements-optional.txt" "$BACKUP_DIR/"
        log_success "requirements-optional.txt sauvegardé"
    fi

    # Sauvegarder la liste des packages installés
    if [ -d "$PROJECT_ROOT/venv" ]; then
        source "$PROJECT_ROOT/venv/bin/activate"
        pip freeze > "$BACKUP_DIR/pip_freeze.txt"
        deactivate
        log_success "Liste des packages actuels sauvegardée"
    fi

    # Créer un fichier de restauration
    cat > "$BACKUP_DIR/restore.sh" << 'EOF'
#!/bin/bash
# Script de restauration de l'environnement
echo "Restauration de l'environnement précédent..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
    cp "$SCRIPT_DIR/requirements.txt" "$PROJECT_ROOT/"
fi

if [ -f "$SCRIPT_DIR/requirements-optional.txt" ]; then
    cp "$SCRIPT_DIR/requirements-optional.txt" "$PROJECT_ROOT/"
fi

echo "Fichiers restaurés. Pour recréer l'environnement:"
echo "  python3 -m venv venv"
echo "  source venv/bin/activate"
echo "  pip install -r requirements.txt"
EOF
    chmod +x "$BACKUP_DIR/restore.sh"

    log_success "Sauvegarde complète dans: $BACKUP_DIR"
else
    log_warning "Sauvegarde ignorée (--no-backup)"
fi

# ===========================================================================
# ÉTAPE 3: Installation de PDM
# ===========================================================================

log_info "Étape 3: Installation de PDM..."

if ! check_command pdm; then
    log_info "Installation de PDM via pipx..."
    pipx install pdm

    # Recharger le PATH
    export PATH="$HOME/.local/bin:$PATH"

    if ! check_command pdm; then
        log_error "Impossible d'installer PDM"
        exit 1
    fi
else
    log_info "PDM déjà installé, mise à jour..."
    pipx upgrade pdm || true
fi

PDM_VERSION=$(pdm --version | cut -d' ' -f2)
log_success "PDM installé: version $PDM_VERSION"

# ===========================================================================
# ÉTAPE 4: Configuration de PDM
# ===========================================================================

log_info "Étape 4: Configuration de PDM pour le projet..."

cd "$PROJECT_ROOT"

# Configurer PDM pour utiliser Python 3.12
log_info "Configuration de Python $PYTHON_VERSION..."
pdm use -f "$PYTHON_VERSION" || {
    log_warning "Python $PYTHON_VERSION non trouvé, utilisation de la version système"
    pdm use -f python3
}

# Installer les dépendances
log_info "Installation des dépendances avec PDM..."
pdm install

# Générer les fichiers lock
log_info "Génération des fichiers lock..."
pdm lock

# ===========================================================================
# ÉTAPE 5: Export des requirements pour compatibilité
# ===========================================================================

log_info "Étape 5: Export des requirements pour compatibilité..."

# Exporter requirements.txt standard
pdm export -f requirements --without-hashes -o requirements.txt
log_success "requirements.txt généré"

# Exporter requirements avec dev
pdm export -f requirements --without-hashes --dev -o requirements-dev.txt
log_success "requirements-dev.txt généré"

# Exporter requirements avec ML optionnel
pdm export -f requirements --without-hashes --with ml -o requirements-ml.txt
log_success "requirements-ml.txt généré"

# ===========================================================================
# ÉTAPE 6: Vérification
# ===========================================================================

log_info "Étape 6: Vérification de l'installation..."

# Vérifier que l'environnement PDM fonctionne
if pdm run python -c "import sys; print(f'Python {sys.version}')" &> /dev/null; then
    log_success "Environnement PDM fonctionnel"
else
    log_error "Problème avec l'environnement PDM"
    exit 1
fi

# Vérifier les imports critiques
CRITICAL_PACKAGES="fastapi pydantic yaml structlog pandas"
FAILED_IMPORTS=""

for package in $CRITICAL_PACKAGES; do
    if pdm run python -c "import $package" 2> /dev/null; then
        log_success "✓ $package importé avec succès"
    else
        log_warning "✗ $package non disponible"
        FAILED_IMPORTS="$FAILED_IMPORTS $package"
    fi
done

if [ -n "$FAILED_IMPORTS" ]; then
    log_warning "Certains packages ne sont pas disponibles: $FAILED_IMPORTS"
    log_info "Essayez: pdm install --dev"
fi

# ===========================================================================
# RÉSUMÉ ET INSTRUCTIONS
# ===========================================================================

echo
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Migration terminée avec succès! 🎉   ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo

log_info "📁 Fichiers créés/modifiés:"
echo "   - pyproject.toml (configuration PDM)"
echo "   - pdm.lock (versions verrouillées)"
echo "   - .pdm-python (version Python fixée)"
echo "   - requirements.txt (compatibilité)"
echo "   - requirements-dev.txt (avec outils dev)"
echo "   - requirements-ml.txt (avec ML optionnel)"

if [ "$SKIP_BACKUP" = false ]; then
    echo
    log_info "💾 Sauvegarde disponible:"
    echo "   $BACKUP_DIR"
    echo "   Pour restaurer: $BACKUP_DIR/restore.sh"
fi

echo
log_info "🚀 Commandes PDM utiles:"
echo "   pdm install          # Installer les dépendances"
echo "   pdm add <package>    # Ajouter une dépendance"
echo "   pdm update           # Mettre à jour les dépendances"
echo "   pdm sync             # Synchroniser l'environnement"
echo "   pdm run python       # Exécuter Python dans l'env PDM"
echo "   pdm run pytest       # Exécuter les tests"
echo "   pdm run server       # Lancer le serveur"

echo
log_info "📝 Pour utiliser PDM dans votre workflow:"
echo "   1. Activez l'environnement: eval \$(pdm venv activate)"
echo "   2. Ou préfixez les commandes: pdm run <commande>"

echo
log_success "La migration vers PDM est complète! 🎉"
log_info "Documentation complète: docs/DEPENDENCY_MANAGEMENT.md"