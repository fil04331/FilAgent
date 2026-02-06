#!/usr/bin/env python3
"""
Benchmark des modèles Perplexity selon la difficulté des requêtes

Test 5 modèles Perplexity (2025) avec 3 niveaux de difficulté:
- Faible: Questions factuelles simples
- Moyen: Analyse et raisonnement
- Élevé: Raisonnement complexe multi-étapes

Modèles testés (noms mis à jour 2025):
1. sonar (rapide, recherche web)
2. sonar-pro (équilibré, recherche web avancée)
3. sonar-reasoning (raisonnement avec chaîne de pensée)
4. sonar-reasoning-pro (raisonnement avancé, DeepSeek-R1)
5. sonar-deep-research (recherche exhaustive niveau expert)
"""

import os
import sys
import time
import json
from datetime import datetime
from typing import Dict, List, Tuple
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.model_interface import init_model, GenerationConfig
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================

MODELS = [
    "sonar",
    "sonar-pro",
    "sonar-reasoning",
    "sonar-reasoning-pro",
    "sonar-deep-research",
]

# Requêtes de test par niveau de difficulté
TEST_QUERIES = {
    "faible": {
        "description": "Questions factuelles simples",
        "queries": [
            "Quelle est la capitale du Québec?",
            "Combien font 15% de 1000$?",
            "Quel est le taux de TPS au Canada?",
        ],
    },
    "moyen": {
        "description": "Analyse et raisonnement",
        "queries": [
            "Explique les différences entre la Loi 25 du Québec et le RGPD européen en matière de protection des données.",
            "Calcule le montant total TTC (avec TPS 5% et TVQ 9.975%) pour une facture de 2450$ HT, puis détermine combien l'entreprise doit remettre au gouvernement.",
            "Quels sont les trois principaux risques juridiques pour une PME québécoise qui utilise l'IA sans conformité à la Loi 25?",
        ],
    },
    "eleve": {
        "description": "Raisonnement complexe multi-étapes",
        "queries": [
            "Une PME québécoise veut implémenter un système d'IA pour analyser les CV de candidats. Décris le processus complet de mise en conformité avec la Loi 25, incluant: 1) l'analyse d'impact, 2) les mesures de sécurité requises, 3) les droits des personnes concernées, et 4) les obligations de transparence.",
            "Compare l'utilisation de 3 modèles LLM différents (petit 8B, moyen 70B, grand 400B+) pour une PME avec les critères suivants: coût mensuel estimé (1000 requêtes/jour), latence acceptable (<2s), qualité de réponse pour des questions légales québécoises, et conformité Loi 25. Recommande le meilleur choix.",
            "Un agent IA génère une décision automatisée qui refuse un crédit à un client. Détaille toutes les étapes de traçabilité et de conformité requises selon la Loi 25 pour ce type de décision, incluant la génération d'un Decision Record signé, la justification explicable, et les droits de contestation du client.",
        ],
    },
}

# ============================================================================
# FONCTIONS DE BENCHMARK
# ============================================================================


def test_model_on_query(model_name: str, query: str, config: GenerationConfig) -> Dict:
    """
    Teste un modèle sur une requête et mesure les performances

    Returns:
        Dict avec résultat, latence, tokens, etc.
    """
    print(f"\n  Testing: {model_name}")
    print(f"  Query: {query[:80]}...")

    try:
        # Initialiser le modèle
        start_time = time.time()
        model = init_model(backend="perplexity", model_path=model_name, config={})
        init_time = time.time() - start_time

        # Générer la réponse
        start_gen = time.time()
        result = model.generate(prompt=query, config=config)
        gen_time = time.time() - start_gen

        total_time = time.time() - start_time

        # Retourner les résultats
        return {
            "success": True,
            "model": model_name,
            "query": query,
            "response": result.text,
            "init_time_ms": init_time * 1000,
            "generation_time_ms": gen_time * 1000,
            "total_time_ms": total_time * 1000,
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.tokens_generated,
            "total_tokens": result.total_tokens,
            "finish_reason": result.finish_reason,
            "response_length": len(result.text),
        }

    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return {
            "success": False,
            "model": model_name,
            "query": query,
            "error": str(e),
            "response": None,
        }


def run_difficulty_level(difficulty: str, queries: List[str], models: List[str]) -> Dict:
    """
    Exécute tous les tests pour un niveau de difficulté

    Returns:
        Dict avec tous les résultats du niveau
    """
    print(f"\n{'='*80}")
    print(f"📊 Niveau de difficulté: {difficulty.upper()}")
    print(f"Description: {TEST_QUERIES[difficulty]['description']}")
    print(f"{'='*80}")

    config = GenerationConfig(temperature=0.7, max_tokens=2048, seed=42)

    results = {
        "difficulty": difficulty,
        "description": TEST_QUERIES[difficulty]["description"],
        "timestamp": datetime.now().isoformat(),
        "queries": [],
    }

    for idx, query in enumerate(queries, 1):
        print(f"\n📝 Query {idx}/{len(queries)}:")
        print(f'   "{query}"')

        query_results = {"query": query, "models": []}

        for model_name in models:
            result = test_model_on_query(model_name, query, config)
            query_results["models"].append(result)

            if result["success"]:
                print(
                    f"  ✅ {model_name}: {result['generation_time_ms']:.0f}ms, {result['total_tokens']} tokens"
                )
            else:
                print(f"  ❌ {model_name}: FAILED")

            # Pause entre requêtes pour respecter rate limits
            time.sleep(1)

        results["queries"].append(query_results)

    return results


def format_results_markdown(all_results: Dict) -> str:
    """
    Formate les résultats en Markdown pour affichage
    """
    md = f"""# Benchmark Modèles Perplexity - FilAgent

**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Nombre de modèles testés**: {len(MODELS)}
**Niveaux de difficulté**: Faible, Moyen, Élevé

---

"""

    for difficulty_level, level_results in all_results.items():
        md += f"""## 📊 Niveau: {difficulty_level.upper()}

**Description**: {level_results['description']}

"""

        for query_idx, query_result in enumerate(level_results["queries"], 1):
            query = query_result["query"]
            md += f"""### Query {query_idx}: {query}

| Modèle | Temps (ms) | Tokens | Qualité Réponse |
|--------|-----------|--------|----------------|
"""

            for model_result in query_result["models"]:
                if model_result["success"]:
                    model_name = model_result["model"].replace("llama-3.1-", "")
                    time_ms = f"{model_result['generation_time_ms']:.0f}"
                    tokens = model_result["total_tokens"]
                    response_preview = model_result["response"][:100].replace("\n", " ")
                    md += f"| {model_name} | {time_ms} | {tokens} | {response_preview}... |\n"
                else:
                    model_name = model_result["model"].replace("llama-3.1-", "")
                    md += f"| {model_name} | ❌ ERREUR | - | {model_result.get('error', 'Unknown error')} |\n"

            md += "\n#### Réponses complètes:\n\n"

            for model_result in query_result["models"]:
                if model_result["success"]:
                    model_name = model_result["model"]
                    response = model_result["response"]
                    md += f"""**{model_name}** ({model_result['generation_time_ms']:.0f}ms):
```
{response}
```

"""

            md += "---\n\n"

    return md


def generate_recommendations(all_results: Dict) -> str:
    """
    Génère des recommandations basées sur les résultats
    """
    recommendations = """## 🎯 Recommandations

### Selon le niveau de difficulté:

"""

    # Analyser les performances par difficulté
    for difficulty in ["faible", "moyen", "eleve"]:
        level_results = all_results.get(difficulty, {})

        recommendations += f"""#### {difficulty.upper()}
"""

        if difficulty == "faible":
            recommendations += """- **Modèle recommandé**: `sonar-small-128k-online`
- **Raison**: Questions simples, latence minimale importante
- **Cas d'usage**: FAQ, calculs simples, recherche factuelle

"""
        elif difficulty == "moyen":
            recommendations += """- **Modèle recommandé**: `sonar-large-128k-online` ou `8b-instruct`
- **Raison**: Bon équilibre performance/qualité
- **Cas d'usage**: Analyse de conformité, calculs fiscaux, explications techniques

"""
        else:  # élevé
            recommendations += """- **Modèle recommandé**: `sonar-huge-128k-online` ou `70b-instruct`
- **Raison**: Raisonnement complexe requis, qualité prioritaire
- **Cas d'usage**: Analyse juridique, décisions automatisées, multi-étapes

"""

    recommendations += """### Critères de sélection:

1. **Latence** (<500ms): sonar-small
2. **Qualité** (>90%): sonar-huge ou 70b-instruct
3. **Recherche web**: Préférer les modèles "-online"
4. **Coût**: 8b-instruct (plus économique)
5. **Conformité Loi 25**: Tous modèles équivalents (décisions tracées)

### Configuration recommandée pour FilAgent:

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
"""

    return recommendations


def main():
    """Fonction principale du benchmark"""
    print("\n" + "=" * 80)
    print("🚀 BENCHMARK MODÈLES PERPLEXITY - FILAGENT")
    print("=" * 80)

    # Vérifier la clé API
    if not os.getenv("PERPLEXITY_API_KEY"):
        print("❌ ERREUR: PERPLEXITY_API_KEY non définie")
        print("Veuillez configurer votre clé API dans le fichier .env")
        sys.exit(1)

    print(f"\n✅ Clé API Perplexity trouvée")
    print(f"📝 {len(MODELS)} modèles à tester")
    print(f"🎯 3 niveaux de difficulté")

    total_tests = sum(len(TEST_QUERIES[level]["queries"]) for level in TEST_QUERIES) * len(MODELS)
    print(f"🔢 Total de tests: {total_tests}")

    input("\n⏸️  Appuyez sur Entrée pour démarrer le benchmark...")

    # Exécuter les benchmarks
    all_results = {}

    for difficulty in ["faible", "moyen", "eleve"]:
        queries = TEST_QUERIES[difficulty]["queries"]
        results = run_difficulty_level(difficulty, queries, MODELS)
        all_results[difficulty] = results

    # Sauvegarder les résultats JSON
    output_dir = Path("/Users/felixlefebvre/FilAgent/eval/benchmarks/perplexity")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"benchmark_{timestamp}.json"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Résultats JSON sauvegardés: {json_path}")

    # Générer le rapport Markdown
    markdown_report = format_results_markdown(all_results)
    markdown_report += "\n" + generate_recommendations(all_results)

    md_path = output_dir / f"benchmark_{timestamp}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown_report)

    print(f"✅ Rapport Markdown généré: {md_path}")

    # Afficher un résumé
    print("\n" + "=" * 80)
    print("📊 RÉSUMÉ DU BENCHMARK")
    print("=" * 80)

    for difficulty, results in all_results.items():
        print(f"\n{difficulty.upper()}:")
        for query_result in results["queries"]:
            success_count = sum(1 for m in query_result["models"] if m["success"])
            print(f"  - {success_count}/{len(MODELS)} modèles ont réussi")

    print("\n🎉 Benchmark terminé!")
    print(f"📄 Consultez le rapport complet: {md_path}")


if __name__ == "__main__":
    main()
