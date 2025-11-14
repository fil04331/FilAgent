#!/usr/bin/env python3
"""
Script de Diagnostic et Test Complet pour FilAgent
==================================================
Ce script teste toutes les capacités de FilAgent et génère un rapport détaillé
"""

import os
import sys
import json
import yaml
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import importlib.util

# Configuration
PROJECT_ROOT = Path(__file__).parent
VENV_PATH = PROJECT_ROOT / "venv"
LOGS_DIR = PROJECT_ROOT / "logs"
CONFIG_DIR = PROJECT_ROOT / "config"
MODELS_DIR = PROJECT_ROOT / "models" / "weights"

# Couleurs pour l'affichage
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color

class FilAgentDiagnostic:
    """Classe principale pour le diagnostic de FilAgent"""
    
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "tests": {},
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "warnings": 0
            }
        }
        
    def print_header(self, title: str):
        """Affiche un en-tête formaté"""
        print(f"\n{Colors.PURPLE}{'='*70}{Colors.NC}")
        print(f"{Colors.CYAN}{title}{Colors.NC}")
        print(f"{Colors.PURPLE}{'='*70}{Colors.NC}\n")
        
    def print_success(self, message: str):
        """Affiche un message de succès"""
        print(f"{Colors.GREEN}✅ {message}{Colors.NC}")
        
    def print_error(self, message: str):
        """Affiche un message d'erreur"""
        print(f"{Colors.RED}❌ {message}{Colors.NC}")
        
    def print_warning(self, message: str):
        """Affiche un avertissement"""
        print(f"{Colors.YELLOW}⚠️  {message}{Colors.NC}")
        
    def print_info(self, message: str):
        """Affiche une information"""
        print(f"{Colors.BLUE}ℹ️  {message}{Colors.NC}")
        
    def test_environment(self) -> Dict[str, Any]:
        """Test de l'environnement système"""
        self.print_header("🔍 TEST DE L'ENVIRONNEMENT")
        
        test_result = {
            "status": "passed",
            "details": {}
        }
        
        # Python version
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        test_result["details"]["python_version"] = python_version
        
        if sys.version_info.major >= 3 and sys.version_info.minor >= 10:
            self.print_success(f"Python version: {python_version}")
        else:
            self.print_error(f"Python version {python_version} (3.10+ requis)")
            test_result["status"] = "failed"
            
        # Environnement virtuel
        if VENV_PATH.exists():
            self.print_success(f"Environnement virtuel trouvé: {VENV_PATH}")
            test_result["details"]["venv"] = str(VENV_PATH)
        else:
            self.print_warning("Environnement virtuel non trouvé")
            test_result["status"] = "warning"
            
        # Espace disque
        stat = os.statvfs(PROJECT_ROOT)
        free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
        test_result["details"]["free_space_gb"] = round(free_gb, 2)
        
        if free_gb >= 5:
            self.print_success(f"Espace disque disponible: {free_gb:.2f} GB")
        else:
            self.print_warning(f"Espace disque faible: {free_gb:.2f} GB")
            
        return test_result
        
    def test_dependencies(self) -> Dict[str, Any]:
        """Test des dépendances Python"""
        self.print_header("📦 TEST DES DÉPENDANCES")
        
        test_result = {
            "status": "passed",
            "details": {
                "core": {},
                "optional": {}
            }
        }
        
        # Dépendances principales
        core_deps = [
            "fastapi", "pydantic", "yaml", "structlog",
            "prometheus_client", "cryptography", "jsonschema",
            "pytest", "pandas"
        ]
        
        for dep in core_deps:
            try:
                module = importlib.import_module(dep)
                version = getattr(module, "__version__", "unknown")
                test_result["details"]["core"][dep] = version
                self.print_success(f"{dep}: {version}")
            except ImportError:
                test_result["details"]["core"][dep] = "missing"
                self.print_error(f"{dep}: NON INSTALLÉ")
                test_result["status"] = "failed"
                
        # Dépendances optionnelles
        optional_deps = ["gradio", "faiss", "sentence_transformers", "llama_cpp"]
        
        for dep in optional_deps:
            try:
                if dep == "faiss":
                    import faiss
                    version = faiss.__version__ if hasattr(faiss, "__version__") else "installed"
                elif dep == "llama_cpp":
                    import llama_cpp
                    version = "installed"
                else:
                    module = importlib.import_module(dep)
                    version = getattr(module, "__version__", "unknown")
                    
                test_result["details"]["optional"][dep] = version
                self.print_info(f"{dep}: {version}")
            except ImportError:
                test_result["details"]["optional"][dep] = "not installed"
                self.print_warning(f"{dep}: Non installé (optionnel)")
                
        return test_result
        
    def test_configuration(self) -> Dict[str, Any]:
        """Test des fichiers de configuration"""
        self.print_header("⚙️ TEST DE LA CONFIGURATION")
        
        test_result = {
            "status": "passed",
            "details": {}
        }
        
        config_files = [
            "agent.yaml",
            "policies.yaml",
            "compliance_rules.yaml",
            "retention.yaml",
            "provenance.yaml",
            "eval_targets.yaml"
        ]
        
        for config_file in config_files:
            config_path = CONFIG_DIR / config_file
            if config_path.exists():
                try:
                    with open(config_path, 'r') as f:
                        config = yaml.safe_load(f)
                    test_result["details"][config_file] = "valid"
                    self.print_success(f"{config_file}: Valide")
                except Exception as e:
                    test_result["details"][config_file] = f"error: {str(e)}"
                    self.print_error(f"{config_file}: Erreur de parsing")
                    test_result["status"] = "failed"
            else:
                test_result["details"][config_file] = "missing"
                self.print_warning(f"{config_file}: Manquant")
                
        return test_result
        
    def test_directories(self) -> Dict[str, Any]:
        """Test de la structure des répertoires"""
        self.print_header("📁 TEST DE LA STRUCTURE")
        
        test_result = {
            "status": "passed",
            "details": {}
        }
        
        required_dirs = [
            "logs/decisions",
            "logs/events",
            "logs/traces/otlp",
            "logs/digests",
            "memory/policies",
            "memory/working_set",
            "provenance/signatures",
            "provenance/snapshots",
            "tools/python_sandbox",
            "tools/shell_sandbox",
            "audit/reports"
        ]
        
        for dir_path in required_dirs:
            full_path = PROJECT_ROOT / dir_path
            if full_path.exists():
                test_result["details"][dir_path] = "exists"
                self.print_success(f"{dir_path}: ✓")
            else:
                test_result["details"][dir_path] = "missing"
                self.print_warning(f"{dir_path}: Manquant")
                # Créer le répertoire manquant
                full_path.mkdir(parents=True, exist_ok=True)
                self.print_info(f"  → Créé automatiquement")
                
        return test_result
        
    def test_database(self) -> Dict[str, Any]:
        """Test de la base de données"""
        self.print_header("🗄️ TEST DE LA BASE DE DONNÉES")
        
        test_result = {
            "status": "passed",
            "details": {}
        }
        
        try:
            # Import local des modules
            sys.path.insert(0, str(PROJECT_ROOT))
            from memory.episodic import get_connection, create_tables
            
            # Test de connexion
            with get_connection() as conn:
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                test_result["details"]["tables"] = [t[0] for t in tables]
                
            if tables:
                self.print_success(f"Base de données OK: {len(tables)} tables")
                for table in tables:
                    self.print_info(f"  - Table: {table[0]}")
            else:
                self.print_warning("Aucune table trouvée, création...")
                create_tables()
                self.print_success("Tables créées")
                
        except Exception as e:
            test_result["status"] = "failed"
            test_result["details"]["error"] = str(e)
            self.print_error(f"Erreur base de données: {e}")
            
        return test_result
        
    def test_model(self) -> Dict[str, Any]:
        """Test de la disponibilité du modèle"""
        self.print_header("🧠 TEST DU MODÈLE LLM")
        
        test_result = {
            "status": "passed",
            "details": {}
        }
        
        model_path = MODELS_DIR / "base.gguf"
        
        if model_path.exists():
            size_gb = model_path.stat().st_size / (1024**3)
            test_result["details"]["model_path"] = str(model_path)
            test_result["details"]["size_gb"] = round(size_gb, 2)
            self.print_success(f"Modèle trouvé: {model_path.name} ({size_gb:.2f} GB)")
        else:
            test_result["status"] = "warning"
            test_result["details"]["model_path"] = "not found"
            self.print_warning("Aucun modèle trouvé (mode stub activé)")
            self.print_info(f"  → Télécharger dans: {MODELS_DIR}")
            
        return test_result
        
    def test_api_server(self) -> Dict[str, Any]:
        """Test du serveur API"""
        self.print_header("🚀 TEST DU SERVEUR API")
        
        test_result = {
            "status": "passed",
            "details": {}
        }
        
        try:
            import requests
            
            # Essayer de démarrer le serveur
            self.print_info("Test de connexion au serveur...")
            
            try:
                response = requests.get("http://localhost:8000/health", timeout=2)
                if response.status_code == 200:
                    health = response.json()
                    test_result["details"]["health"] = health
                    self.print_success("Serveur API actif")
                    for component, status in health.get("components", {}).items():
                        status_symbol = "✓" if status else "✗"
                        self.print_info(f"  - {component}: {status_symbol}")
                else:
                    test_result["status"] = "warning"
                    self.print_warning("Serveur répond mais avec erreur")
            except:
                test_result["status"] = "warning"
                test_result["details"]["server"] = "not running"
                self.print_warning("Serveur non accessible (normal si pas démarré)")
                
        except ImportError:
            test_result["status"] = "failed"
            self.print_error("Module requests non installé")
            
        return test_result
        
    def test_compliance_features(self) -> Dict[str, Any]:
        """Test des fonctionnalités de conformité"""
        self.print_header("🔒 TEST DES FONCTIONNALITÉS DE CONFORMITÉ")
        
        test_result = {
            "status": "passed",
            "details": {}
        }
        
        try:
            sys.path.insert(0, str(PROJECT_ROOT))
            
            # Test EventLogger
            try:
                from runtime.middleware.logging import get_logger
                logger = get_logger()
                test_result["details"]["event_logger"] = "ok"
                self.print_success("EventLogger: Fonctionnel")
            except:
                test_result["details"]["event_logger"] = "error"
                self.print_warning("EventLogger: Non disponible")
                
            # Test PIIRedactor
            try:
                from runtime.middleware.redaction import PIIRedactor
                redactor = PIIRedactor()
                test_text = "Mon email est john@example.com"
                redacted = redactor.redact(test_text)
                if "@" not in redacted:
                    test_result["details"]["pii_redactor"] = "ok"
                    self.print_success("PIIRedactor: Fonctionnel")
                else:
                    test_result["details"]["pii_redactor"] = "not working"
                    self.print_warning("PIIRedactor: Ne masque pas les PII")
            except:
                test_result["details"]["pii_redactor"] = "error"
                self.print_warning("PIIRedactor: Non disponible")
                
            # Test WormLogger
            try:
                from runtime.middleware.worm import get_worm_logger
                worm = get_worm_logger()
                test_result["details"]["worm_logger"] = "ok"
                self.print_success("WormLogger: Fonctionnel")
            except:
                test_result["details"]["worm_logger"] = "error"
                self.print_warning("WormLogger: Non disponible")
                
            # Test Signatures EdDSA
            try:
                from cryptography.hazmat.primitives.asymmetric import ed25519
                private_key = ed25519.Ed25519PrivateKey.generate()
                message = b"test"
                signature = private_key.sign(message)
                test_result["details"]["eddsa_signatures"] = "ok"
                self.print_success("Signatures EdDSA: Fonctionnelles")
            except:
                test_result["details"]["eddsa_signatures"] = "error"
                self.print_warning("Signatures EdDSA: Non disponibles")
                
        except Exception as e:
            test_result["status"] = "failed"
            test_result["details"]["error"] = str(e)
            self.print_error(f"Erreur test conformité: {e}")
            
        return test_result
        
    def test_mcp_integration(self) -> Dict[str, Any]:
        """Test de l'intégration Claude MCP"""
        self.print_header("🤖 TEST INTÉGRATION CLAUDE MCP")
        
        test_result = {
            "status": "passed",
            "details": {}
        }
        
        # Vérifier la configuration MCP
        mcp_config_path = Path.home() / ".claude" / "claude_desktop_config.json"
        
        if mcp_config_path.exists():
            try:
                with open(mcp_config_path, 'r') as f:
                    config = json.load(f)
                    
                if "filagent" in config.get("mcpServers", {}):
                    test_result["details"]["config"] = "configured"
                    self.print_success("Configuration MCP trouvée")
                    
                    filagent_config = config["mcpServers"]["filagent"]
                    self.print_info(f"  - Command: {filagent_config.get('command')}")
                    self.print_info(f"  - Working dir: {filagent_config.get('cwd')}")
                else:
                    test_result["status"] = "warning"
                    test_result["details"]["config"] = "not configured"
                    self.print_warning("FilAgent non configuré dans MCP")
            except Exception as e:
                test_result["status"] = "warning"
                test_result["details"]["error"] = str(e)
                self.print_warning(f"Erreur lecture config MCP: {e}")
        else:
            test_result["status"] = "warning"
            test_result["details"]["config"] = "not found"
            self.print_warning("Configuration MCP non trouvée")
            self.print_info(f"  → Créer: {mcp_config_path}")
            
        # Vérifier le serveur MCP
        mcp_server_path = PROJECT_ROOT / "filagent_mcp_server.py"
        if mcp_server_path.exists():
            test_result["details"]["server"] = "exists"
            self.print_success("Serveur MCP FilAgent trouvé")
        else:
            test_result["status"] = "warning"
            test_result["details"]["server"] = "not found"
            self.print_warning("Serveur MCP non trouvé")
            
        return test_result
        
    def generate_report(self):
        """Génère le rapport final"""
        self.print_header("📊 RAPPORT DE DIAGNOSTIC")
        
        # Calculer le résumé
        for test_name, test_result in self.results["tests"].items():
            self.results["summary"]["total"] += 1
            if test_result["status"] == "passed":
                self.results["summary"]["passed"] += 1
            elif test_result["status"] == "failed":
                self.results["summary"]["failed"] += 1
            else:
                self.results["summary"]["warnings"] += 1
                
        # Afficher le résumé
        summary = self.results["summary"]
        print(f"\n{Colors.CYAN}Résultats:{Colors.NC}")
        print(f"  • Total: {summary['total']} tests")
        print(f"  • {Colors.GREEN}Réussis: {summary['passed']}{Colors.NC}")
        print(f"  • {Colors.RED}Échoués: {summary['failed']}{Colors.NC}")
        print(f"  • {Colors.YELLOW}Avertissements: {summary['warnings']}{Colors.NC}")
        
        # Score global
        if summary['failed'] == 0:
            if summary['warnings'] == 0:
                print(f"\n{Colors.GREEN}✅ DIAGNOSTIC PARFAIT - FilAgent est prêt!{Colors.NC}")
            else:
                print(f"\n{Colors.YELLOW}⚠️ DIAGNOSTIC OK - Quelques optimisations possibles{Colors.NC}")
        else:
            print(f"\n{Colors.RED}❌ DIAGNOSTIC ÉCHOUÉ - Corrections requises{Colors.NC}")
            
        # Sauvegarder le rapport
        report_path = PROJECT_ROOT / "diagnostic_report.json"
        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n{Colors.BLUE}📄 Rapport sauvegardé: {report_path}{Colors.NC}")
        
    def run_all_tests(self):
        """Exécute tous les tests"""
        print(f"{Colors.CYAN}")
        print("╔══════════════════════════════════════════════════════════════════╗")
        print("║            DIAGNOSTIC COMPLET DE FILAGENT                       ║")
        print("╚══════════════════════════════════════════════════════════════════╝")
        print(f"{Colors.NC}")
        
        # Exécuter chaque test
        tests = [
            ("environment", self.test_environment),
            ("dependencies", self.test_dependencies),
            ("configuration", self.test_configuration),
            ("directories", self.test_directories),
            ("database", self.test_database),
            ("model", self.test_model),
            ("api_server", self.test_api_server),
            ("compliance", self.test_compliance_features),
            ("mcp_integration", self.test_mcp_integration)
        ]
        
        for test_name, test_func in tests:
            try:
                self.results["tests"][test_name] = test_func()
            except Exception as e:
                self.results["tests"][test_name] = {
                    "status": "failed",
                    "details": {"error": str(e)}
                }
                self.print_error(f"Erreur lors du test {test_name}: {e}")
                
        # Générer le rapport
        self.generate_report()
        
        # Recommandations finales
        self.print_header("💡 RECOMMANDATIONS")
        
        if self.results["tests"].get("model", {}).get("status") == "warning":
            print("• Télécharger un modèle LLM pour activer toutes les fonctionnalités")
            print(f"  {Colors.BLUE}wget https://huggingface.co/TheBloke/Llama-3-8B-Instruct-GGUF/resolve/main/llama-3-8b-instruct.Q4_K_M.gguf -O {MODELS_DIR}/base.gguf{Colors.NC}")
            
        if self.results["tests"].get("mcp_integration", {}).get("status") == "warning":
            print("• Configurer Claude MCP pour l'intégration avec Claude Desktop")
            print(f"  {Colors.BLUE}./setup_filagent_mcp_complete.sh{Colors.NC}")
            
        if self.results["tests"].get("api_server", {}).get("status") == "warning":
            print("• Démarrer le serveur API pour les tests complets")
            print(f"  {Colors.BLUE}./start_server.sh{Colors.NC}")

if __name__ == "__main__":
    diagnostic = FilAgentDiagnostic()
    diagnostic.run_all_tests()
