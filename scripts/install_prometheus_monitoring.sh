#!/bin/bash
# Script d'installation automatique pour le monitoring Prometheus
#
# Installe:
# - prometheus-client (Python)
# - Prometheus (optionnel, si demandé)
# - Configure les fichiers nécessaires
#
# Usage:
#   chmod +x scripts/install_prometheus_monitoring.sh
#   ./scripts/install_prometheus_monitoring.sh [--install-prometheus]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

INSTALL_PROMETHEUS=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --install-prometheus)
            INSTALL_PROMETHEUS=true
            shift
            ;;
        *)
            echo "Option inconnue: $1"
            echo "Usage: $0 [--install-prometheus]"
            exit 1
            ;;
    esac
done

echo "🚀 Installation du monitoring Prometheus pour FilAgent"
echo ""

# === 1. Installation prometheus-client (Python) ===
echo "📦 1. Installation de prometheus-client (Python)..."
echo ""

if python3 -c "import prometheus_client" 2>/dev/null; then
    VERSION=$(python3 -c "import prometheus_client; print(prometheus_client.__version__)" 2>/dev/null || echo "unknown")
    echo "✅ prometheus-client déjà installé (version: $VERSION)"
else
    echo "   Installation de prometheus-client..."
    
    # Détecter si on est dans un venv
    IN_VENV=false
    if [ -n "$VIRTUAL_ENV" ]; then
        IN_VENV=true
        echo "   Environnement virtuel détecté: $VIRTUAL_ENV"
    fi
    
    # Essayer différentes méthodes d'installation
    INSTALLED=false
    
    # Méthode 1: Installation standard (si venv)
    if [ "$IN_VENV" = true ]; then
        if pip3 install prometheus-client>=0.19.0 --quiet 2>/dev/null; then
            INSTALLED=true
        fi
    fi
    
    # Méthode 2: Installation avec --user (si pas venv)
    if [ "$INSTALLED" = false ] && [ "$IN_VENV" = false ]; then
        echo "   Tentative d'installation avec --user..."
        if pip3 install --user prometheus-client>=0.19.0 --quiet 2>/dev/null; then
            INSTALLED=true
        fi
    fi
    
    # Vérifier l'installation
    if python3 -c "import prometheus_client" 2>/dev/null; then
        VERSION=$(python3 -c "import prometheus_client; print(prometheus_client.__version__)" 2>/dev/null || echo "unknown")
        echo "✅ prometheus-client installé (version: $VERSION)"
    else
        echo "❌ Échec de l'installation de prometheus-client"
        echo ""
        echo "💡 Solutions recommandées:"
        echo "   1. Créer un environnement virtuel:"
        echo "      python3 -m venv venv"
        echo "      source venv/bin/activate"
        echo "      pip install prometheus-client"
        echo ""
        echo "   2. Installation avec --user:"
        echo "      pip3 install --user prometheus-client"
        echo ""
        echo "   3. Installation manuelle:"
        echo "      pip3 install prometheus-client>=0.19.0"
        echo ""
        echo "⚠️  Le script continue mais prometheus-client doit être installé pour le monitoring."
        # Ne pas exit ici, continuer avec le reste des vérifications
    fi
fi

echo ""

# === 2. Vérification des fichiers de configuration ===
echo "📋 2. Vérification des fichiers de configuration..."
echo ""

FILES_TO_CHECK=(
    "config/prometheus.yml"
    "config/prometheus_alerts.yml"
    "planner/metrics.py"
    "runtime/server.py"
)

ALL_EXIST=true
for file in "${FILES_TO_CHECK[@]}"; do
    FILE_PATH="$PROJECT_ROOT/$file"
    if [ -f "$FILE_PATH" ]; then
        echo "   ✅ $file"
    else
        echo "   ❌ $file (manquant)"
        ALL_EXIST=false
    fi
done

if [ "$ALL_EXIST" = false ]; then
    echo ""
    echo "⚠️  Certains fichiers de configuration sont manquants"
    exit 1
fi

echo ""
echo "✅ Tous les fichiers de configuration sont présents"
echo ""

# === 3. Installation Prometheus (optionnel) ===
if [ "$INSTALL_PROMETHEUS" = true ]; then
    echo "📦 3. Installation de Prometheus..."
    echo ""
    
    # Détecter le système d'exploitation
    OS_TYPE=$(uname -s)
    
    if [ "$OS_TYPE" = "Darwin" ]; then
        # macOS
        if command -v brew &> /dev/null; then
            echo "   Installation via Homebrew..."
            if brew install prometheus; then
                echo "✅ Prometheus installé via Homebrew"
            else
                echo "❌ Échec de l'installation via Homebrew"
                echo "   Essayez manuellement: brew install prometheus"
                exit 1
            fi
        else
            echo "⚠️  Homebrew non trouvé"
            echo "   Installez Prometheus manuellement: https://prometheus.io/download/"
        fi
    elif [ "$OS_TYPE" = "Linux" ]; then
        # Linux
        if command -v apt-get &> /dev/null; then
            echo "   Installation via apt-get..."
            sudo apt-get update
            if sudo apt-get install -y prometheus; then
                echo "✅ Prometheus installé via apt-get"
            else
                echo "❌ Échec de l'installation via apt-get"
                exit 1
            fi
        elif command -v yum &> /dev/null; then
            echo "   Installation via yum..."
            if sudo yum install -y prometheus; then
                echo "✅ Prometheus installé via yum"
            else
                echo "❌ Échec de l'installation via yum"
                exit 1
            fi
        else
            echo "⚠️  Gestionnaire de paquets non trouvé"
            echo "   Installez Prometheus manuellement: https://prometheus.io/download/"
        fi
    else
        echo "⚠️  Système d'exploitation non supporté: $OS_TYPE"
        echo "   Installez Prometheus manuellement: https://prometheus.io/download/"
    fi
    
    echo ""
    
    # Vérifier l'installation
    if command -v prometheus &> /dev/null; then
        VERSION=$(prometheus --version 2>&1 | head -1 || echo "unknown")
        echo "✅ $VERSION"
    else
        echo "⚠️  Prometheus non trouvé dans PATH"
        echo "   Vérifiez l'installation manuellement"
    fi
    
    echo ""
fi

# === 4. Création des répertoires nécessaires ===
echo "📁 4. Création des répertoires nécessaires..."
echo ""

REQUIRED_DIRS=(
    "prometheus_data"
    "grafana"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    DIR_PATH="$PROJECT_ROOT/$dir"
    if [ ! -d "$DIR_PATH" ]; then
        mkdir -p "$DIR_PATH"
        echo "   ✅ Créé: $dir/"
    else
        echo "   ✓ Existe déjà: $dir/"
    fi
done

echo ""

# === 5. Vérification finale ===
echo "✅ 5. Vérification finale..."
echo ""

# Test import Python
echo -n "   Test import prometheus_client... "
if python3 -c "import prometheus_client; print('OK')" 2>/dev/null; then
    echo "✅"
else
    echo "❌"
    echo "   ⚠️  prometheus_client non importable"
fi

# Test module metrics
echo -n "   Test module planner.metrics... "
if python3 -c "from planner.metrics import get_metrics; print('OK')" 2>/dev/null; then
    echo "✅"
else
    echo "❌"
    echo "   ⚠️  Module planner.metrics non importable"
fi

echo ""

# === Résumé ===
echo "======================================================================"
echo "INSTALLATION TERMINÉE"
echo "======================================================================"
echo ""
echo "✅ prometheus-client installé et configuré"
if [ "$INSTALL_PROMETHEUS" = true ]; then
    echo "✅ Prometheus installé"
fi
echo "✅ Fichiers de configuration présents"
echo "✅ Répertoires créés"
echo ""
echo "📊 Prochaines étapes:"
echo ""
echo "1. Démarrer FilAgent:"
echo "   python3 -m runtime.server"
echo ""
echo "2. Tester l'endpoint métriques:"
echo "   python3 scripts/test_metrics.py"
echo ""
if [ "$INSTALL_PROMETHEUS" = false ]; then
    echo "3. Installer Prometheus (optionnel):"
    echo "   $0 --install-prometheus"
    echo "   Ou: brew install prometheus (macOS)"
    echo ""
fi
echo "4. Démarrer Prometheus:"
echo "   ./scripts/start_prometheus.sh"
echo ""
echo "5. Générer des métriques de test:"
echo "   python3 scripts/generate_test_metrics.py"
echo ""
echo "✅ Installation complète!"

