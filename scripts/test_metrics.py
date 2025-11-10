#!/usr/bin/env python3
"""
Script de test pour l'endpoint métriques Prometheus

Usage:
    python3 scripts/test_metrics.py
"""

import sys
import os
from pathlib import Path
import argparse

try:
    from importlib import metadata as importlib_metadata
except ImportError:  # pragma: no cover
    import importlib_metadata as importlib_metadata  # type: ignore

# Import requests (optionnel, avec message d'erreur clair)
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("❌ Module 'requests' non disponible.")
    print("   Installez avec: pip install requests")
    print("   Ou: pip install -r requirements.txt")
    sys.exit(1)


def _get_package_version(package: str) -> str:
    try:
        return importlib_metadata.version(package)
    except importlib_metadata.PackageNotFoundError:
        return "unknown"
    except Exception:
        return "unknown"


requests_version = getattr(requests, "__version__", None) or _get_package_version("requests")
print(f"✅ Module 'requests' disponible (version: {requests_version})\n")

# Ajouter le répertoire racine au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_metrics_endpoint(host="localhost", port=8000):
    """Test l'endpoint /metrics"""
    url = f"http://{host}:{port}/metrics"
    
    print(f"🔍 Test de l'endpoint métriques...")
    print(f"   URL: {url}\n")
    
    try:
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            print(f"✅ Endpoint accessible (code {response.status_code})")
            print(f"   Content-Type: {response.headers.get('Content-Type', 'unknown')}")
            print(f"   Taille: {len(response.text)} bytes\n")
            
            # Vérifier présence métriques HTN
            content = response.text
            htn_metrics = [
                "htn_requests_total",
                "htn_planning_duration_seconds",
                "htn_execution_duration_seconds",
                "htn_tasks_completed_total",
                "htn_tasks_failed_total",
                "htn_verifications_total",
            ]
            
            found_metrics = []
            for metric in htn_metrics:
                if metric in content:
                    found_metrics.append(metric)
            
            if found_metrics:
                print(f"✅ Métriques HTN trouvées ({len(found_metrics)}/{len(htn_metrics)}):")
                for metric in found_metrics:
                    print(f"   ✓ {metric}")
            else:
                print("❌ Aucune métrique HTN trouvée. Exécutez au moins une requête HTN pour les générer.")

            # Afficher quelques lignes d'exemple
            print("\n📋 Exemple de métriques (premières lignes):")
            lines = content.split("\n")[:20]
            for line in lines:
                if line and not line.startswith("#"):
                    print(f"   {line}")

            return bool(found_metrics)
            
        else:
            print(f"❌ Endpoint retourne code {response.status_code}")
            print(f"   Réponse: {response.text[:200]}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Impossible de se connecter à {url}")
        print("   Le serveur FilAgent n'est probablement pas démarré.")
        print("   Démarrez-le avec: python3 -m runtime.server")
        return False
        
    except requests.exceptions.Timeout:
        print(f"❌ Timeout lors de la connexion à {url}")
        return False
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_prometheus_client():
    """Test que prometheus-client est installé"""
    print("🔍 Vérification de prometheus-client...\n")
    
    try:
        import prometheus_client
        version = getattr(prometheus_client, "__version__", None) or _get_package_version("prometheus-client")
        print(f"✅ prometheus-client installé (version: {version})")
        return True
    except ImportError:
        print("❌ prometheus-client non installé")
        print("   Installez avec: pip install prometheus-client")
        return False


def main():
    """Exécute tous les tests"""
    parser = argparse.ArgumentParser(
        description="Teste la configuration Prometheus de FilAgent"
    )
    parser.add_argument(
        "--allow-success",
        action="store_true",
        help="Retourner un code 0 si toutes les vérifications réussissent",
    )
    args = parser.parse_args()

    print("\n" + "="*70)
    print("TEST DE L'ENDPOINT MÉTRIQUES PROMETHEUS")
    print("="*70 + "\n")
    
    # Test 1: prometheus-client installé
    client_ok = test_prometheus_client()
    print()
    
    # Test 2: Endpoint métriques
    endpoint_ok = test_metrics_endpoint()
    
    # Résumé
    print("\n" + "="*70)
    print("RÉSUMÉ")
    print("="*70)
    
    all_checks_ok = client_ok and endpoint_ok

    if all_checks_ok:
        print("✅ Tous les tests ont réussi!")
        print("\n📊 Prochaines étapes:")
        print("   1. Vérifier les métriques dans Prometheus")
        print("   2. Configurer Prometheus (voir docs/PROMETHEUS_SETUP.md)")
        print("   3. Créer dashboard Grafana (voir docs/PROMETHEUS_DASHBOARD.md)")
        if not args.allow_success:
            print("\n⚠️  Exécutez avec --allow-success après validation manuelle pour retourner un code 0.")
            return 1
        return 0
    else:
        print("⚠️  Certains tests ont échoué")
        if not client_ok:
            print("   - Installez prometheus-client")
        if not endpoint_ok:
            print("   - Démarrez le serveur FilAgent")
        return 1


if __name__ == "__main__":
    sys.exit(main())

