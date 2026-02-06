#!/usr/bin/env python3
"""
Script pour générer des métriques HTN de test

Simule des requêtes HTN pour générer des métriques Prometheus.
Utile pour tester le dashboard Grafana et les alertes Prometheus.

Usage:
    python3 scripts/generate_test_metrics.py [--count N] [--delay D]
"""

import sys
import os
import time
import argparse
from pathlib import Path
from datetime import datetime

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

# Ajouter le répertoire racine au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Requêtes de test qui déclenchent HTN
TEST_QUERIES = [
    # Requêtes multi-étapes (déclenchent HTN)
    "Lis data.csv, analyse les données, crée un rapport",
    "Lis fichier1.csv puis fichier2.csv, analyse tout, génère statistiques",
    "Calcule la moyenne, la médiane, et crée un graphique",
    "Recherche les fichiers, filtre les résultats, génère un rapport PDF",
    "Lis config.yaml, valide les paramètres, génère un document",
    # Requêtes avec plusieurs actions (déclenchent HTN)
    "Lis analyse génère crée",
    "Read file.csv, analyze data, create report",
    "Search files, filter results, generate statistics",
    # Requêtes avec mots-clés multi-étapes
    "Lis data.csv puis analyse les données",
    "Lis fichier.csv ensuite calcule les statistiques",
    "Lis data.csv et après crée un rapport",
]


def send_htn_request(server_url: str, query: str, conversation_id: str = None):
    """
    Envoie une requête au serveur FilAgent qui déclenchera HTN

    Args:
        server_url: URL du serveur FilAgent (ex: http://localhost:8000)
        query: Requête à envoyer
        conversation_id: ID de conversation (optionnel)

    Returns:
        bool: True si la requête a été envoyée avec succès
    """
    url = f"{server_url}/chat"

    payload = {"messages": [{"role": "user", "content": query}]}

    if conversation_id:
        payload["conversation_id"] = conversation_id

    try:
        response = requests.post(url, json=payload, timeout=30)

        if response.status_code == 200:
            return True
        else:
            print(f"⚠️  Requête retournée code {response.status_code}")
            return False

    except requests.exceptions.ConnectionError:
        print(f"❌ Impossible de se connecter à {url}")
        print("   Le serveur FilAgent n'est probablement pas démarré.")
        return False

    except requests.exceptions.Timeout:
        print(f"⚠️  Timeout lors de l'envoi de la requête")
        return False

    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False


def generate_metrics(server_url: str, count: int = 10, delay: float = 2.0):
    """
    Génère des métriques HTN en envoyant des requêtes de test

    Args:
        server_url: URL du serveur FilAgent
        count: Nombre de requêtes à envoyer
        delay: Délai entre les requêtes (secondes)
    """
    print("=" * 70)
    print("GÉNÉRATION DE MÉTRIQUES HTN DE TEST")
    print("=" * 70)
    print(f"\n📍 Serveur: {server_url}")
    print(f"📊 Requêtes: {count}")
    print(f"⏱️  Délai: {delay}s entre chaque requête")
    print()

    # Vérifier que le serveur est accessible
    try:
        response = requests.get(f"{server_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Serveur FilAgent accessible")
        else:
            print(f"⚠️  Serveur retourne code {response.status_code}")
    except Exception as e:
        print(f"❌ Impossible de vérifier le serveur: {e}")
        return False

    print()

    # Envoyer les requêtes
    success_count = 0
    failed_count = 0

    for i in range(count):
        # Choisir une requête aléatoire
        import random

        query = random.choice(TEST_QUERIES)
        conversation_id = f"test-metrics-{i}-{int(time.time())}"

        print(f"[{i+1}/{count}] Envoi requête HTN...")
        print(f"   Query: {query[:60]}...")

        if send_htn_request(server_url, query, conversation_id):
            success_count += 1
            print(f"   ✅ Requête envoyée avec succès")
        else:
            failed_count += 1
            print(f"   ❌ Échec de la requête")

        # Attendre entre les requêtes (sauf la dernière)
        if i < count - 1:
            print(f"   ⏳ Attente {delay}s...\n")
            time.sleep(delay)
        else:
            print()

    # Résumé
    print("=" * 70)
    print("RÉSUMÉ")
    print("=" * 70)
    print(f"✅ Requêtes réussies: {success_count}/{count}")
    print(f"❌ Requêtes échouées: {failed_count}/{count}")
    print()

    if success_count > 0:
        print("📊 Métriques générées!")
        print()
        print("Prochaines étapes:")
        print("   1. Vérifier les métriques dans Prometheus:")
        print(f"      {server_url.replace('/chat', ':9090')}")
        print("   2. Vérifier l'endpoint /metrics:")
        print(f"      {server_url.replace('/chat', '/metrics')}")
        print("   3. Rechercher les métriques HTN:")
        print("      curl http://localhost:8000/metrics | grep htn_")
        return True
    else:
        print("⚠️  Aucune métrique générée (toutes les requêtes ont échoué)")
        return False


def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(
        description="Génère des métriques HTN de test en envoyant des requêtes au serveur FilAgent"
    )

    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="URL du serveur FilAgent (défaut: http://localhost:8000)",
    )

    parser.add_argument(
        "--count", type=int, default=10, help="Nombre de requêtes à envoyer (défaut: 10)"
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Délai entre les requêtes en secondes (défaut: 2.0)",
    )

    parser.add_argument(
        "--continuous", action="store_true", help="Mode continu: envoie des requêtes indéfiniment"
    )

    args = parser.parse_args()

    # Mode continu
    if args.continuous:
        print("🔄 Mode continu activé (Ctrl+C pour arrêter)\n")
        iteration = 0
        try:
            while True:
                iteration += 1
                print(f"\n{'='*70}")
                print(f"ITÉRATION {iteration}")
                print(f"{'='*70}\n")

                generate_metrics(args.url, count=5, delay=args.delay)

                print(f"\n⏳ Pause de {args.delay * 5}s avant la prochaine itération...\n")
                time.sleep(args.delay * 5)
        except KeyboardInterrupt:
            print("\n\n✅ Arrêt demandé par l'utilisateur")
            return 0
    else:
        # Mode normal
        success = generate_metrics(args.url, count=args.count, delay=args.delay)
        return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
