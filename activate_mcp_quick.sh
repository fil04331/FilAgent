#!/bin/bash

# ============================================================================
# ACTIVATION RAPIDE MCP FILAGENT
# Pour PME Québec - Safety by Design
# ============================================================================

echo "🚀 Activation rapide de FilAgent MCP"

# Activer l'environnement virtuel si nécessaire
if [ -d "/Users/felixlefebvre/FilAgent/.venv" ]; then
    source /Users/felixlefebvre/FilAgent/.venv/bin/activate
    echo "✅ Environnement virtuel activé"
fi

# Installer les dépendances manquantes minimales pour MCP
echo "📦 Installation des dépendances minimales..."
pip install -q pyyaml structlog 2>/dev/null

# Test rapide
echo "🧪 Test du serveur MCP..."
python3 -c "
import sys
sys.path.insert(0, '/Users/felixlefebvre/FilAgent')
from mcp_server import FilAgentMCPServer
print('✅ Serveur MCP prêt!')
"

echo ""
echo "================================"
echo "✅ FilAgent MCP est configuré!"
echo "================================"
echo ""
echo "🔄 Pour activer dans Claude:"
echo "   1. Fermez Claude Desktop complètement (Cmd+Q)"
echo "   2. Rouvrez Claude Desktop"
echo ""
echo "🛠️ Outils disponibles dans Claude:"
echo "   • analyze_document - Conformité Loi 25/RGPD"
echo "   • calculate_taxes_quebec - Calculs TPS/TVQ"
echo "   • generate_decision_record - Decision Records signés"
echo "   • audit_trail - Traces d'audit complètes"
echo ""
echo "📚 Usage dans Claude:"
echo '   "Utilise FilAgent pour analyser ce document"'
echo '   "Calcule les taxes québécoises sur 1000$"'
echo '   "Génère un decision record pour cette décision"'
