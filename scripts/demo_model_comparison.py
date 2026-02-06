#!/usr/bin/env python3
"""
Démonstration rapide de comparaison des modèles Perplexity

Teste 1 question par niveau de difficulté avec 3 modèles représentatifs
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.model_interface import init_model, GenerationConfig
from dotenv import load_dotenv

load_dotenv()

# Modèles à tester (représentatifs) - Noms mis à jour 2025
DEMO_MODELS = [
    ("sonar", "sonar", "Rapide"),
    ("sonar-pro", "sonar-pro", "Équilibré"),
    ("sonar-reasoning", "sonar-reasoning", "Raisonnement"),
]

# Une question par niveau
DEMO_QUERIES = {
    "faible": "Quelle est la capitale du Québec?",
    "moyen": "Explique les différences entre la Loi 25 du Québec et le RGPD européen en 3 points.",
    "eleve": "Une PME québécoise veut implémenter un système d'IA pour analyser les CV. Quelles sont les 3 principales obligations de conformité avec la Loi 25?",
}


def test_query_with_model(query: str, model_name: str, model_full_name: str) -> dict:
    """Teste une requête avec un modèle"""
    print(f"\n  🔄 Test avec {model_name}...")

    try:
        start_time = time.time()

        # Charger le modèle
        model = init_model(backend="perplexity", model_path=model_full_name, config={})

        # Générer
        config = GenerationConfig(temperature=0.7, max_tokens=2048, seed=42)
        result = model.generate(prompt=query, config=config)

        elapsed = (time.time() - start_time) * 1000

        print(f"  ✅ Réponse en {elapsed:.0f}ms - {result.total_tokens} tokens")

        return {
            "success": True,
            "model": model_name,
            "response": result.text,
            "time_ms": elapsed,
            "tokens": result.total_tokens,
        }

    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        return {"success": False, "model": model_name, "error": str(e)}


def main():
    print("\n" + "=" * 80)
    print("🎯 DÉMONSTRATION COMPARAISON MODÈLES PERPLEXITY")
    print("=" * 80)

    # Vérifier clé API
    if not os.getenv("PERPLEXITY_API_KEY"):
        print("\n❌ ERREUR: PERPLEXITY_API_KEY non définie")
        print("Configurez votre clé API dans le fichier .env\n")
        return

    print("\n✅ Clé API Perplexity détectée")
    print(f"📝 3 niveaux de difficulté × 3 modèles = 9 tests\n")

    all_results = {}

    # Tester chaque niveau
    for difficulty, query in DEMO_QUERIES.items():
        print("\n" + "=" * 80)
        print(f"📊 NIVEAU: {difficulty.upper()}")
        print("=" * 80)
        print(f"\n❓ Question: {query}\n")

        results = []

        for model_key, model_full, model_desc in DEMO_MODELS:
            result = test_query_with_model(query, model_desc, model_full)
            results.append(result)
            time.sleep(0.5)  # Pause entre requêtes

        all_results[difficulty] = {"query": query, "results": results}

    # Afficher le rapport
    print("\n\n" + "=" * 80)
    print("📋 RAPPORT DE COMPARAISON")
    print("=" * 80)

    for difficulty, data in all_results.items():
        print(f"\n\n## {difficulty.upper()}\n")
        print(f"**Question**: {data['query']}\n")

        for result in data["results"]:
            if result["success"]:
                print(f"\n### {result['model']}")
                print(f"⏱️  Temps: {result['time_ms']:.0f}ms")
                print(f"🎯 Tokens: {result['tokens']}")
                print(f"\n**Réponse**:")
                print(f"```\n{result['response']}\n```")
                print("-" * 80)
            else:
                print(f"\n### {result['model']}")
                print(f"❌ Erreur: {result['error']}")
                print("-" * 80)

    # Générer les recommandations
    print("\n\n" + "=" * 80)
    print("🎯 RECOMMANDATIONS")
    print("=" * 80)

    print("""
### FAIBLE difficulté
- **Recommandé**: Sonar Small (Rapide)
- **Raison**: Questions simples, latence minimale
- **Cas**: FAQ, calculs, recherche factuelle

### MOYEN difficulté
- **Recommandé**: Sonar Large (Équilibré)
- **Raison**: Bon compromis vitesse/qualité
- **Cas**: Analyse conformité, explications techniques

### ÉLEVÉ difficulté
- **Recommandé**: Sonar Huge (Précis)
- **Raison**: Raisonnement complexe requis
- **Cas**: Analyse juridique, décisions automatisées

### Configuration FilAgent recommandée:

```yaml
# config/agent.yaml
model:
  backend: "perplexity"

  # Sélection dynamique selon difficulté
  models:
    easy: "llama-3.1-sonar-small-128k-online"
    medium: "llama-3.1-sonar-large-128k-online"
    hard: "llama-3.1-sonar-huge-128k-online"
```
    """)

    print("\n✅ Démonstration terminée!")
    print("\n💡 Pour lancer l'interface interactive:")
    print("   python gradio_app_model_selector.py")
    print("\n💡 Pour le benchmark complet:")
    print("   python scripts/benchmark_perplexity_models.py\n")


if __name__ == "__main__":
    main()
