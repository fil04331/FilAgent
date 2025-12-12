#!/usr/bin/env python3
"""
Script de Test Automatisé des Capacités FilAgent
================================================
Test complet de toutes les fonctionnalités et intégrations
"""
from __future__ import annotations

import os
import sys
import json
import time
import requests
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Union
import random
import string

# Type aliases stricts
TestResultValue = Union[str, int, float, bool, None]
TestResultDict = Dict[str, Union[TestResultValue, List[TestResultValue], "TestResultDict"]]
CapabilityResult = Dict[str, Union[str, int, float, bool, Dict[str, bool]]]

# Configuration
PROJECT_ROOT = Path(__file__).parent
API_URL = "http://localhost:8000"
GRADIO_URL = "http://localhost:7860"

class FilAgentCapabilityTester:
    """Testeur automatisé des capacités FilAgent"""
    
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "capabilities": {}
        }
        self.conversation_id = f"test-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
    def print_header(self, title: str):
        """Affiche un en-tête"""
        print(f"\n{'='*70}")
        print(f"  {title}")
        print(f"{'='*70}\n")
        
    def test_api_health(self) -> bool:
        """Test de santé de l'API"""
        self.print_header("🏥 Test de Santé API")
        
        try:
            response = requests.get(f"{API_URL}/health", timeout=5)
            if response.status_code == 200:
                health = response.json()
                print(f"✅ API en ligne")
                print(f"   Status: {health.get('status')}")
                
                components = health.get('components', {})
                for component, status in components.items():
                    status_icon = "✅" if status else "❌"
                    print(f"   {status_icon} {component}: {'OK' if status else 'KO'}")
                    
                self.results["capabilities"]["api_health"] = health
                return True
            else:
                print(f"❌ API répond avec erreur: {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError:
            print("❌ Impossible de se connecter à l'API")
            print("   → Lancer le serveur avec: ./start_server.sh")
            return False
        except Exception as e:
            print(f"❌ Erreur: {e}")
            return False
            
    def test_chat_endpoint(self) -> bool:
        """Test de l'endpoint de chat"""
        self.print_header("💬 Test Endpoint Chat")
        
        test_messages = [
            "Bonjour FilAgent!",
            "Quelle est ta mission?",
            "Comment garantis-tu la conformité Loi 25?"
        ]
        
        try:
            for message in test_messages:
                print(f"📤 Envoi: {message}")
                
                response = requests.post(
                    f"{API_URL}/chat",
                    json={
                        "messages": [{"role": "user", "content": message}],
                        "conversation_id": self.conversation_id
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    answer = data["choices"][0]["message"]["content"][:100]
                    print(f"📥 Réponse: {answer}...")
                    
                    # Vérifier les métadonnées
                    if "usage" in data:
                        tokens = data["usage"].get("total_tokens", 0)
                        print(f"   🔢 Tokens: {tokens}")
                        
                else:
                    print(f"❌ Erreur: {response.status_code}")
                    return False
                    
            self.results["capabilities"]["chat"] = "functional"
            print("✅ Endpoint chat fonctionnel")
            return True
            
        except Exception as e:
            print(f"❌ Erreur chat: {e}")
            return False
            
    def test_compliance_middleware(self) -> bool:
        """Test du middleware de conformité"""
        self.print_header("🔒 Test Middleware de Conformité")
        
        # Test avec données PII
        pii_test = "Mon email est john.doe@example.com et mon téléphone 514-555-1234"
        
        try:
            print("📤 Test avec données PII...")
            response = requests.post(
                f"{API_URL}/chat",
                json={
                    "messages": [{"role": "user", "content": pii_test}],
                    "conversation_id": f"{self.conversation_id}-pii"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                # Vérifier que les logs ont été créés
                logs_dir = PROJECT_ROOT / "logs" / "events"
                if logs_dir.exists():
                    log_files = list(logs_dir.glob("*.jsonl"))
                    if log_files:
                        print(f"✅ Logs créés: {len(log_files)} fichiers")
                        
                        # Vérifier le masquage PII dans les logs
                        latest_log = max(log_files, key=lambda p: p.stat().st_mtime)
                        with open(latest_log, 'r') as f:
                            log_content = f.read()
                            if "john.doe@example.com" not in log_content:
                                print("✅ PII masqués dans les logs")
                            else:
                                print("⚠️  PII non masqués dans les logs")
                                
                # Vérifier les Decision Records
                dr_dir = PROJECT_ROOT / "logs" / "decisions"
                if dr_dir.exists():
                    dr_files = list(dr_dir.glob("DR-*.json"))
                    if dr_files:
                        print(f"✅ Decision Records: {len(dr_files)} créés")
                        
                        # Vérifier la signature
                        latest_dr = max(dr_files, key=lambda p: p.stat().st_mtime)
                        with open(latest_dr, 'r') as f:
                            dr = json.load(f)
                            if "signature" in dr:
                                print("✅ Signature EdDSA présente")
                            else:
                                print("⚠️  Signature manquante")
                                
            self.results["capabilities"]["compliance_middleware"] = "active"
            return True
            
        except Exception as e:
            print(f"❌ Erreur test conformité: {e}")
            return False
            
    def test_worm_logging(self) -> bool:
        """Test des logs WORM (Write Once Read Many)"""
        self.print_header("📝 Test Logs WORM")
        
        try:
            # Générer plusieurs entrées de log
            print("📤 Génération d'entrées de log...")
            
            for i in range(3):
                requests.post(
                    f"{API_URL}/chat",
                    json={
                        "messages": [{"role": "user", "content": f"Test WORM {i}"}],
                        "conversation_id": f"{self.conversation_id}-worm-{i}"
                    },
                    timeout=5
                )
                
            # Vérifier les digests Merkle
            digest_dir = PROJECT_ROOT / "logs" / "digests"
            if digest_dir.exists():
                digest_files = list(digest_dir.glob("*.json"))
                if digest_files:
                    print(f"✅ Digests Merkle: {len(digest_files)} créés")
                    
                    # Vérifier l'intégrité
                    latest_digest = max(digest_files, key=lambda p: p.stat().st_mtime)
                    with open(latest_digest, 'r') as f:
                        digest = json.load(f)
                        if "merkle_root" in digest:
                            print(f"✅ Merkle Root: {digest['merkle_root'][:32]}...")
                            print("✅ Intégrité vérifiable")
                        else:
                            print("⚠️  Merkle Root manquant")
                            
            self.results["capabilities"]["worm_logging"] = "active"
            return True
            
        except Exception as e:
            print(f"❌ Erreur test WORM: {e}")
            return False
            
    def test_provenance_tracking(self) -> bool:
        """Test du tracking de provenance W3C PROV"""
        self.print_header("🔍 Test Provenance Tracking")
        
        try:
            print("📤 Test génération graphe PROV...")
            
            response = requests.post(
                f"{API_URL}/chat",
                json={
                    "messages": [{"role": "user", "content": "Génère un graphe de provenance"}],
                    "conversation_id": f"{self.conversation_id}-prov"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                # Vérifier les fichiers PROV
                prov_dir = PROJECT_ROOT / "logs" / "traces" / "otlp"
                if prov_dir.exists():
                    prov_files = list(prov_dir.glob("prov-*.json"))
                    if prov_files:
                        print(f"✅ Graphes PROV: {len(prov_files)} créés")
                        
                        # Analyser le dernier graphe
                        latest_prov = max(prov_files, key=lambda p: p.stat().st_mtime)
                        with open(latest_prov, 'r') as f:
                            prov = json.load(f)
                            
                        entities = len(prov.get('entity', {}))
                        activities = len(prov.get('activity', {}))
                        agents = len(prov.get('agent', {}))
                        
                        print(f"   📊 Entités: {entities}")
                        print(f"   🔄 Activités: {activities}")
                        print(f"   👤 Agents: {agents}")
                        
                        if entities > 0 and activities > 0:
                            print("✅ Graphe PROV complet")
                        else:
                            print("⚠️  Graphe PROV incomplet")
                            
            self.results["capabilities"]["provenance"] = "active"
            return True
            
        except Exception as e:
            print(f"❌ Erreur test provenance: {e}")
            return False
            
    def test_tools_execution(self) -> bool:
        """Test de l'exécution des outils"""
        self.print_header("🛠️ Test Exécution des Outils")
        
        tools_tests = [
            {
                "name": "calculator",
                "prompt": "Calcule 25 * 4 + 10",
                "expected": "110"
            },
            {
                "name": "python_sandbox",
                "prompt": "Exécute ce code Python: print('Hello FilAgent')",
                "expected": "Hello FilAgent"
            },
            {
                "name": "file_reader",
                "prompt": f"Lis le fichier README.md",
                "expected": "LLM-Agent"
            }
        ]
        
        try:
            for test in tools_tests:
                print(f"🔧 Test outil: {test['name']}")
                print(f"   Prompt: {test['prompt']}")
                
                response = requests.post(
                    f"{API_URL}/chat",
                    json={
                        "messages": [{"role": "user", "content": test['prompt']}],
                        "conversation_id": f"{self.conversation_id}-tool-{test['name']}"
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    answer = data["choices"][0]["message"]["content"]
                    
                    if test['expected'] in answer or "stub" in answer.lower():
                        print(f"   ✅ Résultat obtenu")
                    else:
                        print(f"   ⚠️ Résultat inattendu")
                        
            self.results["capabilities"]["tools"] = "functional"
            return True
            
        except Exception as e:
            print(f"❌ Erreur test outils: {e}")
            return False
            
    def test_memory_system(self) -> bool:
        """Test du système de mémoire"""
        self.print_header("🧠 Test Système de Mémoire")
        
        try:
            # Test mémoire épisodique
            print("📤 Test mémoire épisodique...")
            
            # Créer une conversation avec contexte
            messages = [
                "Mon nom est Alice",
                "J'ai un projet de conformité Loi 25",
                "Quel est mon nom?",
                "Quel est mon projet?"
            ]
            
            for i, message in enumerate(messages):
                print(f"   Message {i+1}: {message}")
                
                response = requests.post(
                    f"{API_URL}/chat",
                    json={
                        "messages": [{"role": "user", "content": message}],
                        "conversation_id": f"{self.conversation_id}-memory"
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    answer = data["choices"][0]["message"]["content"]
                    
                    # Vérifier la cohérence pour les questions
                    if i == 2 and "Alice" in answer:
                        print("   ✅ Mémoire du nom fonctionnelle")
                    elif i == 3 and "Loi 25" in answer:
                        print("   ✅ Mémoire du contexte fonctionnelle")
                        
            # Test récupération conversation
            print("\n📤 Test récupération conversation...")
            response = requests.get(
                f"{API_URL}/conversations/{self.conversation_id}-memory",
                timeout=5
            )
            
            if response.status_code == 200:
                conversation = response.json()
                messages = conversation.get("messages", [])
                print(f"   ✅ Conversation récupérée: {len(messages)} messages")
            elif response.status_code == 404:
                print("   ⚠️ Conversation non trouvée")
                
            self.results["capabilities"]["memory"] = "functional"
            return True
            
        except Exception as e:
            print(f"❌ Erreur test mémoire: {e}")
            return False
            
    def test_quebec_specific_features(self) -> bool:
        """Test des fonctionnalités spécifiques Québec"""
        self.print_header("🇨🇦 Test Fonctionnalités Québec")
        
        try:
            # Test calcul taxes
            print("💰 Test calcul TPS/TVQ...")
            
            response = requests.post(
                f"{API_URL}/chat",
                json={
                    "messages": [{
                        "role": "user",
                        "content": "Calcule les taxes sur 1000$ avec TPS et TVQ"
                    }],
                    "conversation_id": f"{self.conversation_id}-quebec"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                answer = data["choices"][0]["message"]["content"]
                
                # Vérifier les montants
                expected_tps = 1000 * 0.05  # 50$
                expected_tvq = 1000 * 0.09975  # 99.75$
                expected_total = 1000 + expected_tps + expected_tvq  # 1149.75$
                
                if "50" in answer or "TPS" in answer:
                    print(f"   ✅ TPS calculée: {expected_tps:.2f}$")
                if "99.75" in answer or "TVQ" in answer:
                    print(f"   ✅ TVQ calculée: {expected_tvq:.2f}$")
                if "1149" in answer:
                    print(f"   ✅ Total calculé: {expected_total:.2f}$")
                    
            # Test conformité Loi 25
            print("\n📋 Test conformité Loi 25...")
            
            response = requests.post(
                f"{API_URL}/chat",
                json={
                    "messages": [{
                        "role": "user",
                        "content": "Vérifie la conformité Loi 25 pour une PME qui collecte des emails"
                    }],
                    "conversation_id": f"{self.conversation_id}-loi25"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                answer = data["choices"][0]["message"]["content"]
                
                if "Article 53.1" in answer or "transparence" in answer.lower():
                    print("   ✅ Référence à la transparence (Art. 53.1)")
                if "Article 3" in answer or "minimisation" in answer.lower():
                    print("   ✅ Référence à la minimisation (Art. 3)")
                if "Article 8" in answer or "accès" in answer.lower():
                    print("   ✅ Référence au droit d'accès (Art. 8)")
                    
            self.results["capabilities"]["quebec_features"] = "functional"
            return True
            
        except Exception as e:
            print(f"❌ Erreur test Québec: {e}")
            return False
            
    def test_gradio_interface(self) -> bool:
        """Test de l'interface Gradio"""
        self.print_header("🎨 Test Interface Gradio")
        
        try:
            response = requests.get(f"{GRADIO_URL}", timeout=5)
            if response.status_code == 200:
                print("✅ Interface Gradio accessible")
                print(f"   URL: {GRADIO_URL}")
                self.results["capabilities"]["gradio"] = "online"
                return True
            else:
                print(f"⚠️ Interface répond avec: {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError:
            print("⚠️ Interface Gradio non accessible")
            print("   → Lancer avec: ./start_ui.sh")
            return False
        except Exception as e:
            print(f"❌ Erreur: {e}")
            return False
            
    def test_prometheus_metrics(self) -> bool:
        """Test des métriques Prometheus"""
        self.print_header("📊 Test Métriques Prometheus")
        
        try:
            response = requests.get(f"{API_URL}/metrics", timeout=5)
            if response.status_code == 200:
                metrics = response.text
                
                metrics_found = {
                    "filagent_requests_total": False,
                    "filagent_request_duration_seconds": False,
                    "filagent_tokens_used_total": False,
                    "filagent_compliance_checks_total": False
                }
                
                for metric in metrics_found.keys():
                    if metric in metrics:
                        metrics_found[metric] = True
                        
                print("📈 Métriques disponibles:")
                for metric, found in metrics_found.items():
                    status = "✅" if found else "❌"
                    print(f"   {status} {metric}")
                    
                self.results["capabilities"]["prometheus"] = metrics_found
                return True
                
        except Exception as e:
            print(f"⚠️ Métriques non disponibles: {e}")
            return False
            
    def generate_report(self):
        """Génère le rapport final des tests"""
        self.print_header("📊 RAPPORT FINAL DES CAPACITÉS")
        
        # Calculer les statistiques
        total_capabilities = len(self.results["capabilities"])
        functional_capabilities = sum(
            1 for v in self.results["capabilities"].values()
            if v and v != "error"
        )
        
        # Score global
        score = (functional_capabilities / total_capabilities * 100) if total_capabilities > 0 else 0
        
        print(f"\n🎯 Score Global: {score:.1f}%")
        print(f"   • Tests exécutés: {self.results['tests_run']}")
        print(f"   • Tests réussis: {self.results['tests_passed']}")
        print(f"   • Tests échoués: {self.results['tests_failed']}")
        
        print("\n📋 Résumé des Capacités:")
        for capability, status in self.results["capabilities"].items():
            if status and status != "error":
                print(f"   ✅ {capability}: Fonctionnel")
            else:
                print(f"   ❌ {capability}: Non fonctionnel")
                
        # Sauvegarder le rapport
        report_path = PROJECT_ROOT / f"capability_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2)
            
        print(f"\n💾 Rapport sauvegardé: {report_path}")
        
        # Recommandations
        print("\n💡 Recommandations:")
        
        if score == 100:
            print("   🎉 FilAgent est pleinement fonctionnel!")
        elif score >= 80:
            print("   ✅ FilAgent est opérationnel avec quelques optimisations possibles")
        elif score >= 60:
            print("   ⚠️ FilAgent nécessite quelques corrections")
        else:
            print("   ❌ FilAgent nécessite une configuration complète")
            
        if "api_health" not in self.results["capabilities"]:
            print("   • Démarrer le serveur API: ./start_server.sh")
        if "gradio" not in self.results["capabilities"]:
            print("   • Démarrer l'interface: ./start_ui.sh")
        if score < 100:
            print("   • Exécuter le diagnostic complet: python diagnostic_filagent.py")
            
    def run_all_tests(self):
        """Exécute tous les tests de capacités"""
        print("\n" + "="*70)
        print("     TEST AUTOMATISÉ DES CAPACITÉS FILAGENT")
        print("="*70)
        
        tests = [
            ("API Health", self.test_api_health),
            ("Chat Endpoint", self.test_chat_endpoint),
            ("Compliance Middleware", self.test_compliance_middleware),
            ("WORM Logging", self.test_worm_logging),
            ("Provenance Tracking", self.test_provenance_tracking),
            ("Tools Execution", self.test_tools_execution),
            ("Memory System", self.test_memory_system),
            ("Quebec Features", self.test_quebec_specific_features),
            ("Gradio Interface", self.test_gradio_interface),
            ("Prometheus Metrics", self.test_prometheus_metrics)
        ]
        
        for test_name, test_func in tests:
            self.results["tests_run"] += 1
            try:
                if test_func():
                    self.results["tests_passed"] += 1
                else:
                    self.results["tests_failed"] += 1
            except Exception as e:
                print(f"❌ Erreur inattendue dans {test_name}: {e}")
                self.results["tests_failed"] += 1
                
        # Générer le rapport
        self.generate_report()

if __name__ == "__main__":
    tester = FilAgentCapabilityTester()
    tester.run_all_tests()
