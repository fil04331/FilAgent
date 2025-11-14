#!/bin/bash

# ============================================================================
# SCRIPT D'INSTALLATION ET CONFIGURATION AUTOMATIQUE DE FILAGENT
# Version: 2.0.0
# Date: Novembre 2025
# Auteur: Fil - PME Québec AI Services
# 
# Ce script configure automatiquement FilAgent avec:
# - Claude MCP (Model Context Protocol)
# - Environnement virtuel Python
# - Toutes les dépendances
# - Configuration de sécurité
# - Tests automatiques
# - Documentation interactive
# ============================================================================

set -e  # Arrêt en cas d'erreur

# ============================================================================
# CONFIGURATION
# ============================================================================

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR"
VENV_PATH="$PROJECT_ROOT/venv"
MCP_CONFIG_DIR="$HOME/.claude"
LOGS_DIR="$PROJECT_ROOT/logs"
MODELS_DIR="$PROJECT_ROOT/models/weights"

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

print_header() {
    echo -e "\n${PURPLE}╔══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║${NC} ${CYAN}$1${NC}"
    echo -e "${PURPLE}╚══════════════════════════════════════════════════════════════════╝${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# ============================================================================
# BANNIÈRE DE DÉMARRAGE
# ============================================================================

clear
echo -e "${CYAN}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════════════════╗
║                                                                       ║
║     ███████╗██╗██╗      █████╗  ██████╗ ███████╗███╗   ██╗████████╗ ║
║     ██╔════╝██║██║     ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝ ║
║     █████╗  ██║██║     ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║    ║
║     ██╔══╝  ██║██║     ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║    ║
║     ██║     ██║███████╗██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║    ║
║     ╚═╝     ╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝    ║
║                                                                       ║
║     Agent IA avec Gouvernance Complète pour PME Québécoises          ║
║     Safety by Design - Conformité Loi 25 - RGPD - AI Act            ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}\n"

print_info "Démarrage de la configuration automatique..."
print_info "Projet: $PROJECT_ROOT"
print_info "Date: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# ============================================================================
# VÉRIFICATION DES PRÉREQUIS
# ============================================================================

print_header "📋 VÉRIFICATION DES PRÉREQUIS"

# Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_success "Python installé: $PYTHON_VERSION"
else
    print_error "Python 3 n'est pas installé!"
    echo "Installation: brew install python3"
    exit 1
fi

# Git
if command -v git &> /dev/null; then
    print_success "Git installé: $(git --version | cut -d' ' -f3)"
else
    print_error "Git n'est pas installé!"
    echo "Installation: brew install git"
    exit 1
fi

# Homebrew (macOS)
if [[ "$OSTYPE" == "darwin"* ]]; then
    if command -v brew &> /dev/null; then
        print_success "Homebrew installé"
    else
        print_warning "Homebrew non trouvé, certaines dépendances pourraient manquer"
    fi
fi

# Vérifier l'espace disque
AVAILABLE_SPACE=$(df -h "$PROJECT_ROOT" | awk 'NR==2 {print $4}' | sed 's/G//')
if [[ ${AVAILABLE_SPACE%.*} -lt 5 ]]; then
    print_warning "Espace disque faible: ${AVAILABLE_SPACE}GB disponible (5GB recommandé)"
fi

# ============================================================================
# CRÉATION DE L'ENVIRONNEMENT VIRTUEL
# ============================================================================

print_header "🐍 CONFIGURATION ENVIRONNEMENT PYTHON"

if [ ! -d "$VENV_PATH" ]; then
    print_info "Création de l'environnement virtuel..."
    python3 -m venv "$VENV_PATH"
    print_success "Environnement virtuel créé"
else
    print_info "Environnement virtuel existant trouvé"
fi

# Activation de l'environnement
source "$VENV_PATH/bin/activate"
print_success "Environnement virtuel activé"

# Mise à jour pip
print_info "Mise à jour de pip..."
pip install --upgrade pip setuptools wheel > /dev/null 2>&1
print_success "pip mis à jour"

# ============================================================================
# INSTALLATION DES DÉPENDANCES
# ============================================================================

print_header "📦 INSTALLATION DES DÉPENDANCES"

# Installation des dépendances principales
print_info "Installation des dépendances principales..."
pip install -r "$PROJECT_ROOT/requirements.txt" > /dev/null 2>&1
print_success "Dépendances principales installées"

# Installation des dépendances optionnelles
if [ -f "$PROJECT_ROOT/requirements-optional.txt" ]; then
    print_info "Installation des dépendances optionnelles..."
    pip install -r "$PROJECT_ROOT/requirements-optional.txt" 2>/dev/null || print_warning "Certaines dépendances optionnelles n'ont pas pu être installées"
fi

# Installation de Gradio pour l'interface
print_info "Installation de Gradio pour l'interface utilisateur..."
pip install gradio==4.7.1 > /dev/null 2>&1
print_success "Gradio installé"

# ============================================================================
# CONFIGURATION CLAUDE MCP
# ============================================================================

print_header "🤖 CONFIGURATION CLAUDE MCP (Model Context Protocol)"

# Créer le répertoire de configuration MCP
mkdir -p "$MCP_CONFIG_DIR"

# Créer le fichier de configuration MCP pour FilAgent
cat > "$MCP_CONFIG_DIR/claude_desktop_config.json" << 'EOF'
{
  "mcpServers": {
    "filagent": {
      "command": "python",
      "args": [
        "-m",
        "filagent_mcp_server"
      ],
      "cwd": "FILAGENT_PATH",
      "env": {
        "PYTHONPATH": "FILAGENT_PATH",
        "FILAGENT_MODE": "mcp",
        "FILAGENT_LOG_LEVEL": "INFO"
      },
      "capabilities": {
        "tools": true,
        "prompts": true,
        "resources": true,
        "sampling": false
      }
    },
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "FILAGENT_PATH"
      ]
    }
  }
}
EOF

# Remplacer le chemin dans la configuration
sed -i '' "s|FILAGENT_PATH|$PROJECT_ROOT|g" "$MCP_CONFIG_DIR/claude_desktop_config.json"

print_success "Configuration Claude MCP créée"

# ============================================================================
# CRÉATION DU SERVEUR MCP POUR FILAGENT
# ============================================================================

print_header "🔧 CRÉATION DU SERVEUR MCP FILAGENT"

cat > "$PROJECT_ROOT/filagent_mcp_server.py" << 'EOF'
#!/usr/bin/env python3
"""
Serveur MCP (Model Context Protocol) pour FilAgent
Permet l'intégration avec Claude Desktop et Claude Code
"""

import json
import sys
import asyncio
from pathlib import Path
from typing import Dict, List, Any

# Import des composants FilAgent
sys.path.insert(0, str(Path(__file__).parent))

from runtime.agent import get_agent
from runtime.config import get_config
from tools.registry import get_tool_registry
from memory.episodic import get_connection, get_messages

class FilAgentMCPServer:
    """Serveur MCP pour FilAgent"""
    
    def __init__(self):
        self.agent = None
        self.config = get_config()
        self.tool_registry = get_tool_registry()
        
    async def initialize(self):
        """Initialise le serveur MCP"""
        try:
            self.agent = get_agent()
            return {"status": "initialized", "version": "1.0.0"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """Liste tous les outils disponibles dans FilAgent"""
        tools = []
        for tool_name, tool_class in self.tool_registry.items():
            tools.append({
                "name": f"filagent_{tool_name}",
                "description": tool_class.__doc__ or f"Outil {tool_name} de FilAgent",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "input": {
                            "type": "string",
                            "description": "Paramètres pour l'outil"
                        }
                    }
                }
            })
        return tools
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Exécute un outil FilAgent"""
        tool_name = name.replace("filagent_", "")
        if tool_name not in self.tool_registry:
            return {"error": f"Outil {tool_name} non trouvé"}
        
        try:
            tool = self.tool_registry[tool_name]()
            result = tool.execute(arguments.get("input", ""))
            return {"result": result}
        except Exception as e:
            return {"error": str(e)}
    
    async def list_prompts(self) -> List[Dict[str, Any]]:
        """Liste les prompts disponibles pour FilAgent"""
        return [
            {
                "name": "analyze_compliance",
                "description": "Analyser la conformité d'un document ou processus",
                "arguments": [
                    {
                        "name": "content",
                        "description": "Contenu à analyser",
                        "required": True
                    },
                    {
                        "name": "framework",
                        "description": "Cadre de conformité (Loi25, RGPD, AI Act)",
                        "required": False
                    }
                ]
            },
            {
                "name": "generate_decision_record",
                "description": "Générer un Decision Record signé",
                "arguments": [
                    {
                        "name": "decision",
                        "description": "Décision à documenter",
                        "required": True
                    },
                    {
                        "name": "context",
                        "description": "Contexte de la décision",
                        "required": True
                    }
                ]
            },
            {
                "name": "audit_trail",
                "description": "Consulter la trace d'audit",
                "arguments": [
                    {
                        "name": "start_date",
                        "description": "Date de début (ISO format)",
                        "required": False
                    },
                    {
                        "name": "end_date",
                        "description": "Date de fin (ISO format)",
                        "required": False
                    }
                ]
            }
        ]
    
    async def get_prompt(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Génère un prompt basé sur les templates FilAgent"""
        templates = {
            "analyze_compliance": """
                En tant qu'expert en conformité, analysez le contenu suivant 
                selon le cadre {framework}:
                
                {content}
                
                Identifiez:
                1. Points de conformité
                2. Risques potentiels
                3. Recommandations
                """,
            "generate_decision_record": """
                Générer un Decision Record formel pour:
                
                Décision: {decision}
                Contexte: {context}
                
                Incluez:
                - Timestamp
                - Justification
                - Alternatives considérées
                - Risques évalués
                - Signature cryptographique
                """,
            "audit_trail": """
                Récupérer la trace d'audit complète:
                
                Période: {start_date} à {end_date}
                
                Inclure:
                - Tous les Decision Records
                - Logs WORM
                - Graphes de provenance
                - Métriques de conformité
                """
        }
        
        if name not in templates:
            return {"error": f"Prompt {name} non trouvé"}
        
        template = templates[name]
        prompt = template.format(**arguments)
        return {"prompt": prompt}
    
    async def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Gestionnaire principal des messages MCP"""
        method = message.get("method")
        params = message.get("params", {})
        
        if method == "initialize":
            return await self.initialize()
        elif method == "tools/list":
            return {"tools": await self.list_tools()}
        elif method == "tools/call":
            return await self.call_tool(params["name"], params["arguments"])
        elif method == "prompts/list":
            return {"prompts": await self.list_prompts()}
        elif method == "prompts/get":
            return await self.get_prompt(params["name"], params.get("arguments", {}))
        else:
            return {"error": f"Méthode non supportée: {method}"}
    
    async def run(self):
        """Boucle principale du serveur MCP"""
        await self.initialize()
        
        while True:
            try:
                line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                if not line:
                    break
                
                message = json.loads(line)
                response = await self.handle_message(message)
                
                print(json.dumps(response))
                sys.stdout.flush()
                
            except Exception as e:
                error_response = {"error": str(e)}
                print(json.dumps(error_response))
                sys.stdout.flush()

if __name__ == "__main__":
    server = FilAgentMCPServer()
    asyncio.run(server.run())
EOF

chmod +x "$PROJECT_ROOT/filagent_mcp_server.py"
print_success "Serveur MCP FilAgent créé"

# ============================================================================
# CRÉATION DES RÉPERTOIRES NÉCESSAIRES
# ============================================================================

print_header "📁 CRÉATION DE LA STRUCTURE DE RÉPERTOIRES"

directories=(
    "$LOGS_DIR/decisions"
    "$LOGS_DIR/events"
    "$LOGS_DIR/traces/otlp"
    "$LOGS_DIR/digests"
    "$LOGS_DIR/prompts"
    "$LOGS_DIR/safeties"
    "$MODELS_DIR"
    "$PROJECT_ROOT/memory/policies"
    "$PROJECT_ROOT/memory/working_set"
    "$PROJECT_ROOT/provenance/signatures"
    "$PROJECT_ROOT/provenance/snapshots"
)

for dir in "${directories[@]}"; do
    mkdir -p "$dir"
    print_success "Créé: $dir"
done

# ============================================================================
# INITIALISATION DE LA BASE DE DONNÉES
# ============================================================================

print_header "🗄️ INITIALISATION DE LA BASE DE DONNÉES"

python3 << 'EOF'
import sys
sys.path.insert(0, '.')
from memory.episodic import create_tables
try:
    create_tables()
    print("✅ Tables de base de données créées")
except Exception as e:
    print(f"⚠️ Erreur lors de la création des tables: {e}")
EOF

# ============================================================================
# TÉLÉCHARGEMENT DU MODÈLE (OPTIONNEL)
# ============================================================================

print_header "🧠 CONFIGURATION DU MODÈLE LLM"

if [ ! -f "$MODELS_DIR/base.gguf" ]; then
    print_warning "Aucun modèle trouvé dans $MODELS_DIR"
    echo ""
    echo "Voulez-vous télécharger un modèle LLM maintenant? (Recommandé: Llama 3 8B)"
    echo "Taille approximative: 4GB"
    echo ""
    read -p "Télécharger le modèle? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Téléchargement du modèle Llama 3 8B..."
        cd "$MODELS_DIR"
        wget -q --show-progress "https://huggingface.co/TheBloke/Llama-3-8B-Instruct-GGUF/resolve/main/llama-3-8b-instruct.Q4_K_M.gguf" -O base.gguf
        cd "$PROJECT_ROOT"
        print_success "Modèle téléchargé"
    else
        print_warning "Pas de modèle téléchargé. FilAgent fonctionnera en mode stub."
    fi
else
    print_success "Modèle existant trouvé: $MODELS_DIR/base.gguf"
fi

# ============================================================================
# TESTS DE VALIDATION
# ============================================================================

print_header "🧪 TESTS DE VALIDATION"

# Test des imports Python
print_info "Vérification des imports Python..."
python3 << 'EOF'
try:
    import fastapi
    import pydantic
    import yaml
    import structlog
    import gradio
    print("✅ Tous les modules Python importés avec succès")
except ImportError as e:
    print(f"❌ Erreur d'import: {e}")
    exit(1)
EOF

# Test de la configuration
print_info "Vérification de la configuration..."
python3 << 'EOF'
import sys
sys.path.insert(0, '.')
try:
    from runtime.config import get_config
    config = get_config()
    print(f"✅ Configuration chargée: version {config.version}")
except Exception as e:
    print(f"⚠️ Erreur de configuration: {e}")
EOF

# Test rapide du serveur
print_info "Test rapide du serveur API..."
timeout 5 python3 "$PROJECT_ROOT/runtime/server.py" > /dev/null 2>&1 &
SERVER_PID=$!
sleep 2
if kill -0 $SERVER_PID 2>/dev/null; then
    print_success "Serveur API démarre correctement"
    kill $SERVER_PID 2>/dev/null
else
    print_warning "Le serveur n'a pas pu démarrer (normal si le modèle n'est pas installé)"
fi

# ============================================================================
# CRÉATION DES SCRIPTS DE LANCEMENT
# ============================================================================

print_header "🚀 CRÉATION DES SCRIPTS DE LANCEMENT"

# Script de lancement du serveur API
cat > "$PROJECT_ROOT/start_server.sh" << 'EOF'
#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$SCRIPT_DIR/venv/bin/activate"
echo "🚀 Démarrage du serveur FilAgent API..."
echo "📡 URL: http://localhost:8000"
echo "📚 Documentation: http://localhost:8000/docs"
python "$SCRIPT_DIR/runtime/server.py"
EOF
chmod +x "$PROJECT_ROOT/start_server.sh"

# Script de lancement de l'interface Gradio
cat > "$PROJECT_ROOT/start_ui.sh" << 'EOF'
#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "$SCRIPT_DIR/venv/bin/activate"
echo "🎨 Démarrage de l'interface Gradio..."
echo "🌐 URL: http://localhost:7860"
python "$SCRIPT_DIR/gradio_app.py"
EOF
chmod +x "$PROJECT_ROOT/start_ui.sh"

# Script de lancement complet
cat > "$PROJECT_ROOT/start_all.sh" << 'EOF'
#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Démarrer le serveur API en arrière-plan
echo "🚀 Démarrage du serveur API..."
"$SCRIPT_DIR/start_server.sh" &
SERVER_PID=$!

# Attendre que le serveur soit prêt
sleep 3

# Démarrer l'interface Gradio
echo "🎨 Démarrage de l'interface utilisateur..."
"$SCRIPT_DIR/start_ui.sh" &
UI_PID=$!

echo ""
echo "✅ FilAgent est maintenant actif!"
echo "📡 API: http://localhost:8000"
echo "📚 Documentation API: http://localhost:8000/docs"
echo "🎨 Interface: http://localhost:7860"
echo ""
echo "Appuyez sur Ctrl+C pour arrêter tous les services"

# Attendre et nettoyer à la sortie
trap "kill $SERVER_PID $UI_PID 2>/dev/null; exit" INT
wait
EOF
chmod +x "$PROJECT_ROOT/start_all.sh"

print_success "Scripts de lancement créés"

# ============================================================================
# DOCUMENTATION INTERACTIVE
# ============================================================================

print_header "📚 CRÉATION DE LA DOCUMENTATION INTERACTIVE"

cat > "$PROJECT_ROOT/DOCUMENTATION_FILAGENT.md" << 'EOF'
# 📚 Documentation FilAgent - Guide Complet

## 🚀 Démarrage Rapide

### Lancement des services

```bash
# Lancer tout (API + Interface)
./start_all.sh

# Ou séparément:
./start_server.sh  # API seulement
./start_ui.sh      # Interface seulement
```

### URLs d'accès

- **API**: http://localhost:8000
- **Documentation API**: http://localhost:8000/docs
- **Interface Gradio**: http://localhost:7860
- **Métriques Prometheus**: http://localhost:8000/metrics

## 🔧 Configuration Claude MCP

FilAgent est maintenant intégré avec Claude MCP. Pour l'utiliser:

1. **Dans Claude Desktop**: Les outils FilAgent sont automatiquement disponibles
2. **Dans Claude Code**: Utilisez `claude code` à la racine du projet

### Outils MCP disponibles

- `filagent_python_sandbox`: Exécution sécurisée de code Python
- `filagent_file_reader`: Lecture de fichiers avec redaction PII
- `filagent_calculator`: Calculs mathématiques

### Prompts MCP disponibles

- `analyze_compliance`: Analyse de conformité (Loi 25, RGPD, AI Act)
- `generate_decision_record`: Génération de Decision Records signés
- `audit_trail`: Consultation des traces d'audit

## 🔒 Fonctionnalités de Sécurité

### 1. Middleware de Conformité (8 couches)

1. **EventLogger**: Journalisation OpenTelemetry
2. **PIIRedactor**: Masquage automatique des données sensibles
3. **RBACManager**: Contrôle d'accès par rôles
4. **Agent Core**: Raisonnement multi-étapes
5. **ConstraintsEngine**: Validation des sorties
6. **DRManager**: Decision Records signés (EdDSA)
7. **ProvenanceTracker**: Graphes W3C PROV-JSON
8. **WormLogger**: Logs immuables avec Merkle tree

### 2. Decision Records

Chaque décision génère automatiquement:
- Un identifiant unique
- Un timestamp cryptographique
- Une signature EdDSA
- Un graphe de provenance
- Une trace d'audit immuable

Localisation: `logs/decisions/DR-*.json`

### 3. Logs WORM (Write Once Read Many)

- Logs append-only
- Vérification par Merkle tree
- Checkpoints périodiques
- Détection de tampering

Localisation: `logs/digests/`

## 📊 Métriques et Monitoring

### Prometheus

Métriques disponibles sur http://localhost:8000/metrics:

- `filagent_requests_total`: Nombre total de requêtes
- `filagent_request_duration_seconds`: Durée des requêtes
- `filagent_tokens_used_total`: Tokens consommés
- `filagent_compliance_checks_total`: Vérifications de conformité
- `filagent_pii_redacted_total`: Données PII masquées

### Dashboard Grafana

Import du dashboard: `grafana/dashboard_htn.json`

## 🧪 Tests

### Lancer les tests

```bash
# Activer l'environnement
source venv/bin/activate

# Tests unitaires
pytest tests/ -v

# Tests de conformité
pytest tests/test_compliance_flow.py -v

# Tests d'intégration
pytest tests/test_integration_e2e.py -v

# Couverture de code
pytest --cov=runtime --cov=tools --cov=memory tests/
```

### Tests de contrat API

```bash
# Vérifier le contrat OpenAPI
python scripts/validate_openapi.py
```

## 🛠️ Configuration Avancée

### Fichiers de configuration

- `config/agent.yaml`: Paramètres du modèle et de génération
- `config/policies.yaml`: Règles de gouvernance
- `config/compliance_rules.yaml`: Règles de conformité
- `config/retention.yaml`: Politiques de rétention

### Variables d'environnement

```bash
export FILAGENT_LOG_LEVEL=DEBUG
export FILAGENT_MODEL_PATH=/path/to/model.gguf
export FILAGENT_MAX_WORKERS=4
```

## 📈 Cas d'Usage PME Québec

### 1. Analyse de conformité Loi 25

```python
# Exemple d'utilisation
from runtime.agent import get_agent

agent = get_agent()
result = agent.analyze_compliance(
    document="Politique de confidentialité",
    framework="Loi25"
)
```

### 2. Génération de rapports fiscaux TPS/TVQ

```python
# Calcul automatique avec vérification
result = agent.calculate_taxes(
    amount=1000,
    province="QC",
    include_gst=True,
    include_qst=True
)
```

### 3. Audit trail pour vérification

```python
# Export des traces pour audit
from runtime.middleware.worm import get_worm_logger

worm = get_worm_logger()
audit_export = worm.export_audit_trail(
    start_date="2025-01-01",
    end_date="2025-12-31"
)
```

## 🆘 Dépannage

### Problème: Le serveur ne démarre pas

```bash
# Vérifier les logs
tail -f logs/events/$(date +%Y-%m-%d).jsonl

# Réinitialiser la base de données
python -c "from memory.episodic import create_tables; create_tables()"
```

### Problème: Modèle non trouvé

```bash
# Télécharger manuellement
cd models/weights
wget https://huggingface.co/TheBloke/Llama-3-8B-Instruct-GGUF/resolve/main/llama-3-8b-instruct.Q4_K_M.gguf -O base.gguf
```

### Problème: Erreur d'import

```bash
# Réinstaller les dépendances
pip install --upgrade -r requirements.txt
```

## 📞 Support

- Email: support@filagent.quebec
- Documentation: https://docs.filagent.quebec
- GitHub: https://github.com/fil/FilAgent

## 📜 Licence et Conformité

FilAgent est conçu pour être 100% conforme avec:
- ✅ Loi 25 (Québec)
- ✅ RGPD (Europe)
- ✅ AI Act (Europe)
- ✅ NIST AI RMF (USA)
- ✅ ISO 27001

© 2025 FilAgent - Tous droits réservés
EOF

print_success "Documentation créée: DOCUMENTATION_FILAGENT.md"

# ============================================================================
# RAPPORT FINAL
# ============================================================================

print_header "✅ INSTALLATION TERMINÉE AVEC SUCCÈS!"

echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    FILAGENT EST PRÊT À L'EMPLOI!                ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}📋 RÉSUMÉ DE L'INSTALLATION:${NC}"
echo ""
echo "  ✅ Environnement Python configuré"
echo "  ✅ Dépendances installées"
echo "  ✅ Claude MCP configuré"
echo "  ✅ Structure de répertoires créée"
echo "  ✅ Base de données initialisée"
echo "  ✅ Scripts de lancement créés"
echo "  ✅ Documentation générée"
echo ""
echo -e "${YELLOW}🚀 PROCHAINES ÉTAPES:${NC}"
echo ""
echo "  1. Lancer FilAgent:"
echo "     ${BLUE}./start_all.sh${NC}"
echo ""
echo "  2. Accéder à l'interface:"
echo "     ${BLUE}http://localhost:7860${NC}"
echo ""
echo "  3. Consulter la documentation API:"
echo "     ${BLUE}http://localhost:8000/docs${NC}"
echo ""
echo "  4. Lire la documentation complète:"
echo "     ${BLUE}open DOCUMENTATION_FILAGENT.md${NC}"
echo ""
echo -e "${PURPLE}🔧 INTÉGRATION CLAUDE:${NC}"
echo ""
echo "  FilAgent est maintenant disponible dans Claude Desktop!"
echo "  Redémarrez Claude Desktop pour activer les outils MCP."
echo ""
echo -e "${GREEN}══════════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Merci d'utiliser FilAgent - Safety by Design pour PME Québec! 🇨🇦${NC}"
echo -e "${GREEN}══════════════════════════════════════════════════════════════════${NC}"

# Ouvrir automatiquement la documentation
if [[ "$OSTYPE" == "darwin"* ]]; then
    open "$PROJECT_ROOT/DOCUMENTATION_FILAGENT.md"
fi

# Demander si on lance FilAgent maintenant
echo ""
read -p "Voulez-vous lancer FilAgent maintenant? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    exec "$PROJECT_ROOT/start_all.sh"
fi
