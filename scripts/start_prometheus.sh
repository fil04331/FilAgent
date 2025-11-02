#!/bin/bash
# Script pour démarrer Prometheus avec la configuration FilAgent
#
# Usage:
#   chmod +x scripts/start_prometheus.sh
#   ./scripts/start_prometheus.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROMETHEUS_CONFIG="$PROJECT_ROOT/config/prometheus.yml"
PROMETHEUS_DATA="$PROJECT_ROOT/prometheus_data"

echo "🚀 Démarrage de Prometheus pour FilAgent HTN Monitoring"
echo ""

# Vérifier que la configuration existe
if [ ! -f "$PROMETHEUS_CONFIG" ]; then
    echo "❌ Configuration Prometheus non trouvée: $PROMETHEUS_CONFIG"
    exit 1
fi

# Créer le répertoire de données si nécessaire
mkdir -p "$PROMETHEUS_DATA"

echo "📋 Configuration:"
echo "   Config: $PROMETHEUS_CONFIG"
echo "   Data: $PROMETHEUS_DATA"
echo ""

# Vérifier que Prometheus est installé
if ! command -v prometheus &> /dev/null; then
    echo "❌ Prometheus n'est pas installé"
    echo ""
    echo "Installation:"
    echo "   macOS: brew install prometheus"
    echo "   Linux: sudo apt-get install prometheus"
    echo "   Ou télécharger: https://prometheus.io/download/"
    exit 1
fi

# Vérifier la version
PROMETHEUS_VERSION=$(prometheus --version 2>&1 | head -1)
echo "✅ $PROMETHEUS_VERSION"
echo ""

# Démarrer Prometheus
echo "▶️  Démarrage de Prometheus..."
echo "   Interface: http://localhost:9090"
echo "   Targets: http://localhost:8000/metrics"
echo "   Arrêter: Ctrl+C"
echo ""

cd "$PROJECT_ROOT"

prometheus \
    --config.file="$PROMETHEUS_CONFIG" \
    --storage.tsdb.path="$PROMETHEUS_DATA" \
    --web.console.libraries=/usr/share/prometheus/console_libraries \
    --web.console.templates=/usr/share/prometheus/consoles \
    --web.enable-lifecycle

