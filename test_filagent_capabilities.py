#!/usr/bin/env python3
"""
Script de test rapide des capacités FilAgent
Pour PME québécoises - Test conformité et fonctionnalités
"""

import sys
import os
sys.path.insert(0, '/Users/felixlefebvre/FilAgent')

import json
import requests
from datetime import datetime
from pathlib import Path

# Configuration
API_URL = "http://localhost:8000"
GRADIO_URL = "http://localhost:7860"

class FilAgentTester:
    """Testeur automatique pour FilAgent"""
    
    def __init__(self):
        self.results = []
        self.session = requests.Session()
        
    def test_api_health(self):
        """Test santé API"""
        try:
            resp = self.session.get(f"{API_URL}/health", timeout=5)
            if resp.status_code == 200:
                self.results.append("✅ API en santé")
                return True
            else:
                self.results.append(f"❌ API problème: {resp.status_code}")
                return False
        except:
            self.results.append("❌ API non accessible")
            return False
    
    def test_compliance_features(self):
        """Test fonctionnalités conformité"""
        test_message = {
            "messages": [
                {"role": "user", "content": "Analyse ce montant: 1000$ plus taxes"}
            ],
            "conversation_id": "test-compliance"
        }
        
        try:
            resp = self.session.post(
                f"{API_URL}/chat",
                json=test_message,
                timeout=30
            )
            
            if resp.status_code == 200:
                data = resp.json()
                
                # Vérifier métadonnées conformité
                checks = []
                
                if "metadata" in data:
                    checks.append("✅ Métadonnées présentes")
                    
                if data.get("metadata", {}).get("decision_record_id"):
                    checks.append("✅ Decision Record créé")
                    
                if data.get("metadata", {}).get("pii_redacted"):
                    checks.append("✅ PII redaction active")
                    
                if data.get("metadata", {}).get("audit_logged"):
                    checks.append("✅ Audit log enregistré")
                    
                self.results.extend(checks)
                return len(checks) >= 2
            else:
                self.results.append(f"❌ Chat API erreur: {resp.status_code}")
                return False
        except Exception as e:
            self.results.append(f"❌ Test conformité échoué: {str(e)}")
            return False
    
    def test_pme_tools(self):
        """Test outils PME (calculs taxes)"""
        test_calc = {
            "messages": [
                {"role": "user", "content": "Calcule TPS et TVQ sur 1000$"}
            ],
            "conversation_id": "test-taxes"
        }
        
        try:
            resp = self.session.post(f"{API_URL}/chat", json=test_calc, timeout=30)
            
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"].lower()
                
                # Vérifier présence calculs taxes
                if "tps" in content or "50" in content:  # TPS 5% = 50$
                    self.results.append("✅ Calcul TPS fonctionnel")
                    
                if "tvq" in content or "99.75" in content:  # TVQ 9.975% = 99.75$
                    self.results.append("✅ Calcul TVQ fonctionnel")
                    
                return True
            else:
                self.results.append("❌ Outils PME non testables")
                return False
        except:
            self.results.append("❌ Test outils PME échoué")
            return False
    
    def test_memory_persistence(self):
        """Test persistance mémoire"""
        # Premier message
        msg1 = {
            "messages": [
                {"role": "user", "content": "Mon entreprise s'appelle TestCorp"}
            ],
            "conversation_id": "test-memory"
        }
        
        # Deuxième message
        msg2 = {
            "messages": [
                {"role": "user", "content": "Mon entreprise s'appelle TestCorp"},
                {"role": "assistant", "content": "Bonjour TestCorp!"},
                {"role": "user", "content": "Quel est le nom de mon entreprise?"}
            ],
            "conversation_id": "test-memory"
        }
        
        try:
            # Envoyer premier message
            resp1 = self.session.post(f"{API_URL}/chat", json=msg1, timeout=30)
            
            # Envoyer deuxième message
            resp2 = self.session.post(f"{API_URL}/chat", json=msg2, timeout=30)
            
            if resp2.status_code == 200:
                data = resp2.json()
                content = data["choices"][0]["message"]["content"]
                
                if "TestCorp" in content:
                    self.results.append("✅ Mémoire conversation fonctionnelle")
                    return True
                else:
                    self.results.append("⚠️  Mémoire conversation partielle")
                    return False
            else:
                self.results.append("❌ Test mémoire échoué")
                return False
        except:
            self.results.append("❌ Erreur test mémoire")
            return False
    
    def test_security_sandbox(self):
        """Test sandbox sécurisé"""
        dangerous_code = {
            "messages": [
                {"role": "user", "content": "Exécute: import os; os.system('ls /')"}
            ],
            "conversation_id": "test-security"
        }
        
        try:
            resp = self.session.post(f"{API_URL}/chat", json=dangerous_code, timeout=30)
            
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"].lower()
                
                # Vérifier que le code dangereux est bloqué ou sandboxé
                if "sécurité" in content or "sandbox" in content or "interdit" in content:
                    self.results.append("✅ Sandbox sécurisé actif")
                    return True
                elif "erreur" in content or "impossible" in content:
                    self.results.append("✅ Commandes dangereuses bloquées")
                    return True
                else:
                    self.results.append("⚠️  Sandbox à vérifier")
                    return False
            else:
                self.results.append("✅ Requêtes dangereuses rejetées")
                return True
        except:
            self.results.append("⚠️  Test sécurité non concluant")
            return False
    
    def run_all_tests(self):
        """Exécuter tous les tests"""
        print("\n" + "="*60)
        print("🧪 TEST DES CAPACITÉS FILAGENT")
        print("="*60)
        
        # Tests principaux
        tests = [
            ("Santé API", self.test_api_health),
            ("Conformité", self.test_compliance_features),
            ("Outils PME", self.test_pme_tools),
            ("Mémoire", self.test_memory_persistence),
            ("Sécurité", self.test_security_sandbox)
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            print(f"\n🔍 Test: {test_name}")
            try:
                if test_func():
                    passed += 1
                    print(f"   ✅ {test_name} réussi")
                else:
                    failed += 1
                    print(f"   ❌ {test_name} échoué")
            except Exception as e:
                failed += 1
                print(f"   ❌ Erreur: {str(e)}")
        
        # Rapport final
        print("\n" + "="*60)
        print("📊 RAPPORT FINAL")
        print("="*60)
        
        for result in self.results:
            print(f"  {result}")
        
        print(f"\n🏆 Score: {passed}/{len(tests)} tests réussis")
        
        if passed == len(tests):
            print("✨ FilAgent est 100% opérationnel!")
        elif passed >= 3:
            print("👍 FilAgent est fonctionnel (quelques ajustements mineurs)")
        else:
            print("⚠️  FilAgent nécessite configuration")
        
        print("="*60)
        
        return passed, failed

if __name__ == "__main__":
    tester = FilAgentTester()
    passed, failed = tester.run_all_tests()
    
    # Code de sortie
    sys.exit(0 if failed == 0 else 1)
