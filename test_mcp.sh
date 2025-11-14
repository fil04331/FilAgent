#!/bin/bash

# Script de test du serveur MCP FilAgent
# Auteur: Fil - PME Québec

echo "=================================="
echo "Test du serveur MCP FilAgent"
echo "=================================="

# Test 1: Import Python
echo -e "\n📋 Test 1: Import du module MCP"
python3 -c "import mcp_server; print('✅ Module importable')" 2>&1

# Test 2: Test d'initialisation
echo -e "\n📋 Test 2: Test d'initialisation"
python3 << 'EOF'
import asyncio
import sys
import os
sys.path.insert(0, '/Users/felixlefebvre/FilAgent')
os.chdir('/Users/felixlefebvre/FilAgent')

from mcp_server import FilAgentMCPServer

async def test():
    server = FilAgentMCPServer()
    result = await server.initialize()
    if "error" not in result:
        print("✅ Initialisation réussie")
        print(f"   Version: {result.get('version', 'N/A')}")
    else:
        print(f"❌ Erreur: {result['error']}")
    
    # Test des outils
    tools = server.tools
    print(f"✅ {len(tools)} outils disponibles:")
    for tool in tools:
        print(f"   - {tool}")

asyncio.run(test())
EOF

# Test 3: Configuration Claude
echo -e "\n📋 Test 3: Vérification configuration Claude"
if [ -f "/Users/felixlefebvre/.claude/mcp_config.json" ]; then
    echo "✅ Configuration MCP trouvée:"
    cat /Users/felixlefebvre/.claude/mcp_config.json | python3 -m json.tool | head -10
else
    echo "❌ Configuration MCP non trouvée"
fi

# Test 4: Environnement virtuel
echo -e "\n📋 Test 4: Environnement virtuel"
if [ -d "/Users/felixlefebvre/FilAgent/.venv" ]; then
    echo "✅ Environnement virtuel .venv trouvé"
elif [ -d "/Users/felixlefebvre/FilAgent/venv" ]; then
    echo "✅ Environnement virtuel venv trouvé"
else
    echo "⚠️  Aucun environnement virtuel trouvé"
fi

echo -e "\n=================================="
echo "✅ Tests terminés"
echo "=================================="
echo ""
echo "Pour activer le MCP dans Claude:"
echo "1. Fermez complètement Claude Desktop"
echo "2. Rouvrez Claude Desktop"
echo "3. Les outils FilAgent seront disponibles"
echo ""
echo "Outils disponibles:"
echo "- analyze_document: Analyse conformité Loi 25/RGPD"
echo "- calculate_taxes_quebec: Calcul TPS/TVQ"
echo "- generate_decision_record: Génération DR signé"
echo "- audit_trail: Consultation traces d'audit"
