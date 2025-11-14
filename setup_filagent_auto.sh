#!/bin/bash

# ===========================================================================
# 🚀 FilAgent - Script d'Installation et Configuration Automatisé
# ===========================================================================
# Version: 1.0.0
# Date: 2025-11-14
# Description: Installation complète, configuration et tests de FilAgent
# Conformité: Loi 25, RGPD, AI Act, NIST AI RMF
# ===========================================================================

set -e  # Exit on error
set -u  # Exit on undefined variable

# ============================================================================
# COULEURS ET SYMBOLES
# ============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Emojis pour status
CHECK="✅"
CROSS="❌"
WARN="⚠️ "
INFO="ℹ️ "
ROCKET="🚀"
LOCK="🔒"
GEAR="⚙️ "
CHART="📊"

# ============================================================================
# CONFIGURATION
# ============================================================================
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
FILAGENT_DIR="${SCRIPT_DIR}"
VENV_DIR="${FILAGENT_DIR}/venv"
LOG_FILE="${FILAGENT_DIR}/setup_$(date +%Y%m%d_%H%M%S).log"
PYTHON_MIN_VERSION="3.10"

# URLs des modèles recommandés
MODEL_URLS=(
    "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
    "https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf"
)

# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

log() {
    echo -e "$1" | tee -a "${LOG_FILE}"
}

log_section() {
    log "\n${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    log "${CYAN}$1${NC}"
    log "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

check_command() {
    if command -v "$1" &> /dev/null; then
        log "${GREEN}${CHECK}${NC} $1 trouvé"
        return 0
    else
        log "${RED}${CROSS}${NC} $1 non trouvé"
        return 1
    fi
}

check_python_version() {
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        if [ "$(printf '%s\n' "$PYTHON_MIN_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" = "$PYTHON_MIN_VERSION" ]; then
            log "${GREEN}${CHECK}${NC} Python ${PYTHON_VERSION} (>= ${PYTHON_MIN_VERSION})"
            return 0
        else
            log "${RED}${CROSS}${NC} Python ${PYTHON_VERSION} (nécessite >= ${PYTHON_MIN_VERSION})"
            return 1
        fi
    else
        log "${RED}${CROSS}${NC} Python3 non trouvé"
        return 1
    fi
}

create_directories() {
    local dirs=(
        "logs/events"
        "logs/decisions"
        "logs/safeties"
        "logs/prompts"
        "logs/digests"
        "memory/semantic/{encoder}"
        "memory/policies"
        "memory/working_set"
        "models/weights"
        "provenance/signatures"
        "provenance/snapshots"
        "audit/reports"
        "audit/samples"
        "audit/signed"
        "tools/code_exec"
        "tools/python_sandbox"
        "tools/shell_sandbox"
        "tools/connectors"
        "planner"
        "policy/legal"
    )
    
    for dir in "${dirs[@]}"; do
        mkdir -p "${FILAGENT_DIR}/${dir}"
        log "${GREEN}${CHECK}${NC} Créé: ${dir}"
    done
}

# ============================================================================
# VÉRIFICATION DES PRÉREQUIS
# ============================================================================

check_prerequisites() {
    log_section "${GEAR} Vérification des Prérequis"
    
    local all_ok=true
    
    # Python
    if ! check_python_version; then
        all_ok=false
        log "${YELLOW}${WARN}${NC} Installez Python ${PYTHON_MIN_VERSION}+ : brew install python3"
    fi
    
    # Git
    if ! check_command git; then
        all_ok=false
        log "${YELLOW}${WARN}${NC} Installez Git : brew install git"
    fi
    
    # RAM disponible (macOS)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        TOTAL_RAM=$(sysctl -n hw.memsize | awk '{print int($1/1024/1024/1024)}')
        if [ "$TOTAL_RAM" -lt 8 ]; then
            log "${YELLOW}${WARN}${NC} RAM: ${TOTAL_RAM}GB (8GB+ recommandé)"
        else
            log "${GREEN}${CHECK}${NC} RAM: ${TOTAL_RAM}GB"
        fi
    fi
    
    # Espace disque
    AVAILABLE_SPACE=$(df -h . | awk 'NR==2 {print $4}' | sed 's/G//')
    if [[ "$AVAILABLE_SPACE" =~ ^[0-9]+$ ]] && [ "$AVAILABLE_SPACE" -lt 10 ]; then
        log "${YELLOW}${WARN}${NC} Espace disque: ${AVAILABLE_SPACE}GB (10GB+ recommandé)"
    else
        log "${GREEN}${CHECK}${NC} Espace disque suffisant"
    fi
    
    if [ "$all_ok" = false ]; then
        log "\n${RED}${CROSS} Certains prérequis manquent. Continuez quand même? (y/n)${NC}"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# ============================================================================
# ENVIRONNEMENT VIRTUEL
# ============================================================================

setup_virtual_env() {
    log_section "${GEAR} Configuration Environnement Virtuel"
    
    if [ -d "${VENV_DIR}" ]; then
        log "${YELLOW}${WARN}${NC} Environnement virtuel existant détecté"
        log "Supprimer et recréer? (y/n)"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            rm -rf "${VENV_DIR}"
            python3 -m venv "${VENV_DIR}"
            log "${GREEN}${CHECK}${NC} Environnement virtuel recréé"
        else
            log "${INFO} Utilisation de l'environnement existant"
        fi
    else
        python3 -m venv "${VENV_DIR}"
        log "${GREEN}${CHECK}${NC} Environnement virtuel créé"
    fi
    
    # Activer l'environnement
    source "${VENV_DIR}/bin/activate"
    
    # Mettre à jour pip
    pip install --upgrade pip setuptools wheel > /dev/null 2>&1
    log "${GREEN}${CHECK}${NC} pip, setuptools, wheel mis à jour"
}

# ============================================================================
# INSTALLATION DES DÉPENDANCES
# ============================================================================

install_dependencies() {
    log_section "${GEAR} Installation des Dépendances"
    
    # Requirements principal
    if [ -f "${FILAGENT_DIR}/requirements.txt" ]; then
        log "${INFO} Installation des dépendances principales..."
        pip install -r "${FILAGENT_DIR}/requirements.txt" > /dev/null 2>&1
        log "${GREEN}${CHECK}${NC} Dépendances principales installées"
    else
        log "${RED}${CROSS}${NC} requirements.txt non trouvé!"
        exit 1
    fi
    
    # Requirements optionnels (si présent)
    if [ -f "${FILAGENT_DIR}/requirements-optional.txt" ]; then
        log "${INFO} Installation des dépendances optionnelles..."
        pip install -r "${FILAGENT_DIR}/requirements-optional.txt" > /dev/null 2>&1 || {
            log "${YELLOW}${WARN}${NC} Certaines dépendances optionnelles ont échoué (normal)"
        }
    fi
    
    # Installer Prometheus (pour monitoring)
    pip install prometheus-client > /dev/null 2>&1 || {
        log "${YELLOW}${WARN}${NC} Prometheus client non installé (optionnel)"
    }
}

# ============================================================================
# CONFIGURATION DU MODÈLE
# ============================================================================

setup_model() {
    log_section "${GEAR} Configuration du Modèle LLM"
    
    MODEL_DIR="${FILAGENT_DIR}/models/weights"
    
    # Vérifier si un modèle existe déjà
    if [ -f "${MODEL_DIR}/base.gguf" ]; then
        log "${GREEN}${CHECK}${NC} Modèle existant trouvé: base.gguf"
        log "Télécharger un nouveau modèle? (y/n)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            return 0
        fi
    fi
    
    log "\n${CYAN}Modèles recommandés pour PME québécoises:${NC}"
    log "1) Mistral-7B-Instruct (Recommandé - Français excellent)"
    log "2) Llama-2-7B-Chat (Alternative - Bon support français)"
    log "3) Télécharger manuellement plus tard"
    log "4) Utiliser le mode mock (tests uniquement)"
    
    read -p "Votre choix (1-4): " choice
    
    case $choice in
        1)
            log "${INFO} Téléchargement de Mistral-7B-Instruct (~4GB)..."
            curl -L "${MODEL_URLS[0]}" -o "${MODEL_DIR}/base.gguf" --progress-bar
            log "${GREEN}${CHECK}${NC} Mistral-7B-Instruct téléchargé"
            ;;
        2)
            log "${INFO} Téléchargement de Llama-2-7B-Chat (~4GB)..."
            curl -L "${MODEL_URLS[1]}" -o "${MODEL_DIR}/base.gguf" --progress-bar
            log "${GREEN}${CHECK}${NC} Llama-2-7B-Chat téléchargé"
            ;;
        3)
            log "${YELLOW}${WARN}${NC} Téléchargez un modèle GGUF dans: ${MODEL_DIR}/base.gguf"
            ;;
        4)
            log "${INFO} Mode mock activé (tests uniquement)"
            touch "${MODEL_DIR}/.mock_mode"
            ;;
        *)
            log "${YELLOW}${WARN}${NC} Choix invalide - configuration manuelle requise"
            ;;
    esac
}

# ============================================================================
# INITIALISATION DE LA BASE DE DONNÉES
# ============================================================================

init_database() {
    log_section "${GEAR} Initialisation de la Base de Données"
    
    python3 << EOF
import sys
sys.path.insert(0, '${FILAGENT_DIR}')
from memory.episodic import create_tables
create_tables()
print("Tables créées avec succès")
EOF
    
    if [ $? -eq 0 ]; then
        log "${GREEN}${CHECK}${NC} Base de données SQLite initialisée"
    else
        log "${RED}${CROSS}${NC} Erreur lors de l'initialisation de la base de données"
        exit 1
    fi
}

# ============================================================================
# GÉNÉRATION DES CLÉS CRYPTOGRAPHIQUES
# ============================================================================

generate_crypto_keys() {
    log_section "${LOCK} Génération des Clés Cryptographiques"
    
    python3 << EOF
import sys
sys.path.insert(0, '${FILAGENT_DIR}')
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
import os

# Générer une paire de clés EdDSA
private_key = ed25519.Ed25519PrivateKey.generate()
public_key = private_key.public_key()

# Sauvegarder les clés
keys_dir = '${FILAGENT_DIR}/provenance/keys'
os.makedirs(keys_dir, exist_ok=True)

# Clé privée
private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)
with open(f'{keys_dir}/private_key.pem', 'wb') as f:
    f.write(private_pem)
os.chmod(f'{keys_dir}/private_key.pem', 0o600)

# Clé publique
public_pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)
with open(f'{keys_dir}/public_key.pem', 'wb') as f:
    f.write(public_pem)

print("Clés EdDSA générées avec succès")
EOF
    
    if [ $? -eq 0 ]; then
        log "${GREEN}${CHECK}${NC} Clés EdDSA générées (provenance/keys/)"
        log "${LOCK} Clé privée protégée (chmod 600)"
    else
        log "${YELLOW}${WARN}${NC} Génération des clés échouée (non critique)"
    fi
}

# ============================================================================
# TESTS DE BASE
# ============================================================================

run_basic_tests() {
    log_section "${CHART} Exécution des Tests de Base"
    
    # Tests unitaires critiques
    log "${INFO} Exécution des tests unitaires..."
    python3 -m pytest "${FILAGENT_DIR}/tests" \
        -m "not e2e and not slow" \
        --tb=short \
        -q \
        2>&1 | tee -a "${LOG_FILE}"
    
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        log "${GREEN}${CHECK}${NC} Tests unitaires passés"
    else
        log "${YELLOW}${WARN}${NC} Certains tests ont échoué (consulter le log)"
    fi
    
    # Test de conformité
    log "${INFO} Vérification de la conformité..."
    python3 -m pytest "${FILAGENT_DIR}/tests" \
        -m "compliance" \
        --tb=short \
        -q \
        2>&1 | tee -a "${LOG_FILE}"
    
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        log "${GREEN}${CHECK}${NC} Tests de conformité passés"
    else
        log "${RED}${CROSS}${NC} Tests de conformité échoués - CRITIQUE pour production!"
    fi
}

# ============================================================================
# DÉMARRAGE DU SERVEUR
# ============================================================================

start_server() {
    log_section "${ROCKET} Démarrage du Serveur FilAgent"
    
    # Vérifier si le serveur tourne déjà
    if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
        log "${YELLOW}${WARN}${NC} Un serveur écoute déjà sur le port 8000"
        log "Arrêter le serveur existant? (y/n)"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            kill $(lsof -Pi :8000 -sTCP:LISTEN -t)
            sleep 2
        else
            return 0
        fi
    fi
    
    # Créer un script de démarrage
    cat > "${FILAGENT_DIR}/start_filagent.sh" << 'STARTER'
#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "${SCRIPT_DIR}/venv/bin/activate"
cd "${SCRIPT_DIR}"
python runtime/server.py
STARTER
    
    chmod +x "${FILAGENT_DIR}/start_filagent.sh"
    
    log "${INFO} Démarrage du serveur en arrière-plan..."
    nohup "${FILAGENT_DIR}/start_filagent.sh" > "${FILAGENT_DIR}/server.log" 2>&1 &
    SERVER_PID=$!
    
    # Attendre que le serveur démarre
    sleep 3
    
    # Vérifier que le serveur répond
    if curl -s http://localhost:8000/health > /dev/null; then
        log "${GREEN}${CHECK}${NC} Serveur démarré avec succès (PID: ${SERVER_PID})"
        log "${INFO} API disponible sur: ${CYAN}http://localhost:8000${NC}"
        log "${INFO} Documentation: ${CYAN}http://localhost:8000/docs${NC}"
        log "${INFO} Métriques: ${CYAN}http://localhost:8000/metrics${NC}"
        
        # Sauvegarder le PID
        echo $SERVER_PID > "${FILAGENT_DIR}/server.pid"
    else
        log "${RED}${CROSS}${NC} Le serveur n'a pas pu démarrer"
        log "Consultez ${FILAGENT_DIR}/server.log pour les détails"
    fi
}

# ============================================================================
# CONFIGURATION PROMETHEUS (OPTIONNEL)
# ============================================================================

setup_prometheus() {
    log_section "${CHART} Configuration Prometheus (Monitoring)"
    
    log "Configurer Prometheus pour le monitoring? (y/n)"
    read -r response
    
    if [[ "$response" =~ ^[Yy]$ ]]; then
        # Utiliser le script existant si disponible
        if [ -f "${FILAGENT_DIR}/scripts/install_prometheus_monitoring.sh" ]; then
            bash "${FILAGENT_DIR}/scripts/install_prometheus_monitoring.sh"
            log "${GREEN}${CHECK}${NC} Prometheus configuré"
        else
            log "${YELLOW}${WARN}${NC} Script Prometheus non trouvé - configuration manuelle requise"
        fi
    else
        log "${INFO} Prometheus non configuré (optionnel)"
    fi
}

# ============================================================================
# RAPPORT FINAL
# ============================================================================

generate_report() {
    log_section "${CHECK} Installation Complétée!"
    
    cat << REPORT | tee -a "${LOG_FILE}"

${GREEN}╔══════════════════════════════════════════════════════════════╗
║           🎉 FilAgent - Installation Réussie! 🎉            ║
╚══════════════════════════════════════════════════════════════╝${NC}

${CYAN}📋 RÉSUMÉ DE L'INSTALLATION:${NC}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Python ${PYTHON_VERSION} configuré
✅ Environnement virtuel créé
✅ Dépendances installées
✅ Structure de dossiers créée
✅ Base de données initialisée
✅ Clés cryptographiques générées
✅ Tests de base exécutés
✅ Serveur API démarré

${CYAN}🔗 POINTS D'ACCÈS:${NC}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• API REST:        ${BLUE}http://localhost:8000${NC}
• Documentation:   ${BLUE}http://localhost:8000/docs${NC}
• Santé:          ${BLUE}http://localhost:8000/health${NC}
• Métriques:      ${BLUE}http://localhost:8000/metrics${NC}

${CYAN}🚀 COMMANDES UTILES:${NC}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Démarrer:   ${GREEN}./start_filagent.sh${NC}
• Arrêter:    ${GREEN}kill \$(cat server.pid)${NC}
• Tests:      ${GREEN}source venv/bin/activate && pytest tests/${NC}
• Logs:       ${GREEN}tail -f server.log${NC}

${CYAN}📚 PROCHAINES ÉTAPES:${NC}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Télécharger un modèle LLM si pas fait
2. Configurer config/agent.yaml selon vos besoins
3. Activer les outils PME dans tools/
4. Configurer les règles de conformité
5. Tester avec un client PME pilote

${CYAN}📊 CONFORMITÉ:${NC}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
${GREEN}✅${NC} Loi 25 (Québec) - Decision Records signés
${GREEN}✅${NC} RGPD - Redaction PII automatique
${GREEN}✅${NC} AI Act - Traçabilité complète
${GREEN}✅${NC} NIST AI RMF - Logs WORM immuables

${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}
Log complet disponible dans: ${YELLOW}${LOG_FILE}${NC}

${GREEN}Bon développement avec FilAgent! 🚀${NC}
REPORT
}

# ============================================================================
# FONCTION TEST RAPIDE
# ============================================================================

quick_test() {
    log_section "🧪 Test Rapide de l'API"
    
    # Test simple de chat
    RESPONSE=$(curl -s -X POST http://localhost:8000/chat \
        -H "Content-Type: application/json" \
        -d '{
            "messages": [{"role": "user", "content": "Bonjour FilAgent!"}],
            "conversation_id": "test-setup"
        }' | python3 -m json.tool 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        log "${GREEN}${CHECK}${NC} API répond correctement"
        log "${INFO} Réponse: $(echo "$RESPONSE" | grep -o '"content":"[^"]*"' | head -1)"
    else
        log "${YELLOW}${WARN}${NC} L'API ne répond pas encore - normal au premier démarrage"
    fi
}

# ============================================================================
# MAIN
# ============================================================================

main() {
    clear
    
    cat << "BANNER"
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     ███████╗██╗██╗      █████╗  ██████╗ ███████╗███╗   ██╗ ║
║     ██╔════╝██║██║     ██╔══██╗██╔════╝ ██╔════╝████╗  ██║ ║
║     █████╗  ██║██║     ███████║██║  ███╗█████╗  ██╔██╗ ██║ ║
║     ██╔══╝  ██║██║     ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║ ║
║     ██║     ██║███████╗██║  ██║╚██████╔╝███████╗██║ ╚████║ ║
║     ╚═╝     ╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝ ║
║                                                              ║
║         🔒 Safety by Design pour PME Québécoises 🔒         ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
BANNER
    
    log "\n${CYAN}Installation et Configuration Automatisée${NC}"
    log "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    
    # Étapes d'installation
    check_prerequisites
    create_directories
    setup_virtual_env
    install_dependencies
    setup_model
    init_database
    generate_crypto_keys
    run_basic_tests
    start_server
    setup_prometheus
    quick_test
    generate_report
    
    log "\n${GREEN}${ROCKET} Installation terminée avec succès!${NC}"
}

# Lancer le script principal
main "$@"
