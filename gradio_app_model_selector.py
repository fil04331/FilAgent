#!/usr/bin/env python3
"""
FilAgent - Interface Gradio avec Sélection de Modèle Perplexity

Extension de l'interface production avec:
- Sélection dynamique du modèle Perplexity
- Comparaison visuelle des réponses
- Métriques de performance par modèle
"""

import gradio as gr
import asyncio
import json
import uuid
import time
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Dict, Optional

# Ajouter le chemin du projet
sys.path.insert(0, str(Path(__file__).parent))

from runtime.model_interface import init_model, GenerationConfig, GenerationResult
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# CONFIGURATION MODÈLES PERPLEXITY
# ============================================================================

PERPLEXITY_MODELS = {
    "sonar": {
        "name": "Sonar (Rapide)",
        "full_name": "sonar",
        "description": "Modèle rapide pour questions simples",
        "use_case": "FAQ, calculs simples, recherche factuelle",
        "latency": "Très faible (<300ms)",
        "quality": "Bonne pour questions simples",
        "cost": "$",
        "features": ["Recherche web", "Rapide", "Économique"],
    },
    "sonar-pro": {
        "name": "Sonar Pro (Équilibré)",
        "full_name": "sonar-pro",
        "description": "Modèle équilibré - RECOMMANDÉ",
        "use_case": "Usage général, analyses, conformité",
        "latency": "Faible (<500ms)",
        "quality": "Très bonne qualité/vitesse",
        "cost": "$$",
        "features": ["Recherche web avancée", "Recommandé"],
    },
    "sonar-reasoning": {
        "name": "Sonar Reasoning (Raisonnement)",
        "full_name": "sonar-reasoning",
        "description": "Raisonnement avec recherche web",
        "use_case": "Analyse complexe avec chaîne de pensée",
        "latency": "Modérée (<1s)",
        "quality": "Excellence pour raisonnement",
        "cost": "$$$",
        "features": ["Recherche web", "Chain-of-thought", "Raisonnement"],
    },
    "sonar-reasoning-pro": {
        "name": "Sonar Reasoning Pro (Précis)",
        "full_name": "sonar-reasoning-pro",
        "description": "Raisonnement avancé (DeepSeek-R1)",
        "use_case": "Décisions critiques, analyse juridique approfondie",
        "latency": "Élevée (<2s)",
        "quality": "Qualité maximale avec justification",
        "cost": "$$$$",
        "features": ["Recherche web", "DeepSeek-R1", "Qualité maximale"],
    },
    "sonar-deep-research": {
        "name": "Deep Research (Expert)",
        "full_name": "sonar-deep-research",
        "description": "Recherche approfondie niveau expert",
        "use_case": "Rapports détaillés, recherche exhaustive",
        "latency": "Très élevée (>10s)",
        "quality": "Rapports experts détaillés",
        "cost": "$$$$$",
        "features": ["Recherche exhaustive", "Rapports longs", "Expert"],
    },
}

# ============================================================================
# CLASSE GESTIONNAIRE DE MODÈLES
# ============================================================================


class ModelManager:
    """Gestionnaire pour charger et utiliser différents modèles Perplexity"""

    def __init__(self):
        self.current_model = None
        self.current_model_name = None
        self.generation_config = GenerationConfig(temperature=0.7, max_tokens=2048, seed=42)

    def load_model(self, model_key: str) -> bool:
        """
        Charge un modèle Perplexity

        Args:
            model_key: Clé du modèle dans PERPLEXITY_MODELS

        Returns:
            True si chargement réussi
        """
        try:
            model_info = PERPLEXITY_MODELS[model_key]
            full_name = model_info["full_name"]

            print(f"🔄 Chargement du modèle: {full_name}")

            self.current_model = init_model(backend="perplexity", model_path=full_name, config={})

            self.current_model_name = model_key
            print(f"✅ Modèle chargé: {model_info['name']}")
            return True

        except Exception as e:
            print(f"❌ Erreur chargement modèle: {e}")
            return False

    def extract_sources(self, text: str) -> Tuple[str, List[str]]:
        """
        Extrait les sources citées dans le texte Perplexity

        Returns:
            Tuple[str, List[str]]: (texte nettoyé, liste des sources)
        """
        import re

        sources = []
        # Chercher les patterns de sources [1], [2], etc.
        citation_pattern = r"\[(\d+)\]"
        citations = re.findall(citation_pattern, text)

        # Pour l'instant, on garde les citations telles quelles
        # Les vraies URLs ne sont pas dans le texte mais dans les métadonnées de l'API
        # On va formater pour rendre les citations cliquables visuellement

        return text, citations

    def clean_response(self, text: str, citation_urls: Optional[List[str]] = None) -> str:
        """
        Nettoie la réponse en formatant les balises spéciales pour Gradio

        Convertit les balises <think> en blocs formatés et extrait le contenu final
        AFFICHE TOUT LE RAISONNEMENT (pas de troncature)
        Affiche les URLs réelles des sources si disponibles

        Args:
            text: Le texte de la réponse
            citation_urls: Liste optionnelle des URLs de sources (depuis Perplexity API)
        """
        import re

        # Cas 1: Si la réponse contient <think>...</think>, extraire et formater
        think_pattern = r"<think>(.*?)</think>\s*(.*)"
        match = re.search(think_pattern, text, flags=re.DOTALL)

        if match:
            think_content = match.group(1).strip()
            final_answer = match.group(2).strip()

            # Extraire les numéros de citations du texte
            clean_answer, citation_numbers = self.extract_sources(final_answer)

            # ✅ AFFICHER TOUT LE RAISONNEMENT (enlever la limite de 500 caractères)
            # Formater le raisonnement en bloc dépliable
            formatted = f"""💭 **Chaîne de pensée complète**:

<details>
<summary>🧠 Cliquez pour voir le raisonnement détaillé ({len(think_content)} caractères)</summary>

```
{think_content}
```
</details>

**📝 Réponse finale**:

{clean_answer}"""

            # Afficher les sources avec les URLs réelles si disponibles
            if citation_urls and citation_numbers:
                formatted += "\n\n📚 **Sources citées**:\n\n"
                # Map citation numbers to URLs
                for num_str in sorted(set(citation_numbers)):
                    try:
                        idx = int(num_str) - 1  # [1] -> index 0
                        if 0 <= idx < len(citation_urls):
                            url = citation_urls[idx]
                            formatted += f"- [{num_str}] {url}\n"
                    except (ValueError, IndexError):
                        pass
            elif citation_numbers:
                # Fallback si pas d'URLs disponibles
                formatted += f"\n\n📚 **Sources citées**: {', '.join([f'[{c}]' for c in sorted(set(citation_numbers))])}"

            return formatted

        # Cas 2: Pas de balises <think>, extraire quand même les sources
        clean_text, citation_numbers = self.extract_sources(text)

        # Afficher les sources avec les URLs réelles si disponibles
        if citation_urls and citation_numbers:
            clean_text += "\n\n📚 **Sources citées**:\n\n"
            for num_str in sorted(set(citation_numbers)):
                try:
                    idx = int(num_str) - 1  # [1] -> index 0
                    if 0 <= idx < len(citation_urls):
                        url = citation_urls[idx]
                        clean_text += f"- [{num_str}] {url}\n"
                except (ValueError, IndexError):
                    pass
        elif citation_numbers:
            # Fallback si pas d'URLs disponibles
            clean_text += f"\n\n📚 **Sources citées**: {', '.join([f'[{c}]' for c in sorted(set(citation_numbers))])}"

        return clean_text

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Tuple[str, Dict]:
        """
        Génère une réponse avec le modèle actuel

        Returns:
            Tuple (réponse, métriques)
        """
        if not self.current_model:
            return "❌ Aucun modèle chargé", {}

        try:
            start_time = time.time()

            result: GenerationResult = self.current_model.generate(
                prompt=prompt, config=self.generation_config, system_prompt=system_prompt
            )

            generation_time = (time.time() - start_time) * 1000  # en ms

            metrics = {
                "model": PERPLEXITY_MODELS[self.current_model_name]["name"],
                "generation_time_ms": generation_time,
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.tokens_generated,
                "total_tokens": result.total_tokens,
                "finish_reason": result.finish_reason,
                "response_length": len(result.text),
            }

            # Nettoyer la réponse pour affichage Gradio avec citations
            cleaned_text = self.clean_response(result.text, citation_urls=result.citations)

            return cleaned_text, metrics

        except Exception as e:
            print(f"❌ Erreur génération: {e}")
            return f"❌ Erreur: {str(e)}", {}


# ============================================================================
# INTERFACE GRADIO
# ============================================================================


class FilAgentModelSelector:
    """Interface Gradio avec sélection de modèle"""

    def __init__(self):
        self.model_manager = ModelManager()
        self.conversation_history = []

    def format_model_info(self, model_key: str) -> str:
        """Formate les informations d'un modèle pour affichage"""
        if model_key not in PERPLEXITY_MODELS:
            return "Sélectionnez un modèle"

        info = PERPLEXITY_MODELS[model_key]

        features_str = " • ".join(info["features"])

        return f"""### {info['name']}

**Description**: {info['description']}

**Cas d'usage**: {info['use_case']}

**Caractéristiques**:
- Latence: {info['latency']}
- Qualité: {info['quality']}
- Coût: {info['cost']}

**Fonctionnalités**: {features_str}
"""

    def process_message(
        self, message: str, model_key: str, history: List[List[str]]
    ) -> Tuple[str, List[List[str]], str]:
        """
        Traite un message avec le modèle sélectionné

        Returns:
            Tuple (message_vide, historique_mis_à_jour, métriques_formatées)
        """
        if not message.strip():
            return "", history, ""

        if model_key not in PERPLEXITY_MODELS:
            error_msg = "⚠️ Veuillez sélectionner un modèle Perplexity"
            history.append([message, error_msg])
            return "", history, ""

        # Charger le modèle si nécessaire
        if self.model_manager.current_model_name != model_key:
            success = self.model_manager.load_model(model_key)
            if not success:
                error_msg = (
                    f"❌ Impossible de charger le modèle {PERPLEXITY_MODELS[model_key]['name']}"
                )
                history.append([message, error_msg])
                return "", history, ""

        # Générer la réponse
        response, metrics = self.model_manager.generate(prompt=message)

        # Mettre à jour l'historique
        history.append([message, response])

        # Formater les métriques
        if metrics:
            metrics_text = f"""**Métriques de génération**:
- Modèle: {metrics['model']}
- Temps: {metrics['generation_time_ms']:.0f} ms
- Tokens: {metrics['total_tokens']} ({metrics['prompt_tokens']} prompt + {metrics['completion_tokens']} completion)
- Longueur réponse: {metrics['response_length']} caractères
- Statut: {metrics['finish_reason']}
"""
        else:
            metrics_text = ""

        return "", history, metrics_text

    def compare_models(self, query: str, model1_key: str, model2_key: str, model3_key: str) -> str:
        """
        Compare les réponses de plusieurs modèles

        Returns:
            Résultats formatés en Markdown
        """
        if not query.strip():
            return "⚠️ Veuillez entrer une question pour la comparaison"

        results_md = f"""# Comparaison de Modèles

**Question**: {query}

**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

"""

        for model_key in [model1_key, model2_key, model3_key]:
            if not model_key or model_key not in PERPLEXITY_MODELS:
                continue

            model_info = PERPLEXITY_MODELS[model_key]
            results_md += f"""## {model_info['name']}

"""

            # Charger et tester le modèle
            success = self.model_manager.load_model(model_key)

            if not success:
                results_md += "❌ **Erreur de chargement du modèle**\n\n---\n\n"
                continue

            response, metrics = self.model_manager.generate(prompt=query)

            if metrics:
                results_md += f"""**Métriques**:
- ⏱️ Temps: {metrics['generation_time_ms']:.0f} ms
- 🎯 Tokens: {metrics['total_tokens']}
- 📝 Longueur: {metrics['response_length']} caractères

**Réponse**:
```
{response}
```

---

"""
            else:
                results_md += f"""**Erreur**: {response}

---

"""

        return results_md


def create_interface() -> gr.Blocks:
    """Crée l'interface Gradio complète"""

    app_instance = FilAgentModelSelector()

    with gr.Blocks(
        title="FilAgent - Sélection de Modèle Perplexity",
        theme=gr.themes.Soft(primary_hue="blue", secondary_hue="gray"),
    ) as app:

        gr.Markdown("""
# 🤖 FilAgent - Sélecteur de Modèle Perplexity

### 🎯 Testez et comparez les modèles Perplexity selon vos besoins
        """)

        with gr.Tabs():
            # ========== ONGLET CHAT ==========
            with gr.Tab("💬 Chat avec Modèle"):
                with gr.Row():
                    with gr.Column(scale=2):
                        model_selector = gr.Dropdown(
                            choices=list(PERPLEXITY_MODELS.keys()),
                            label="🎯 Sélectionnez un modèle",
                            value="sonar-pro",
                            interactive=True,
                        )

                        model_info = gr.Markdown(app_instance.format_model_info("sonar-pro"))

                        chatbot = gr.Chatbot(
                            label="Conversation", height=400, show_copy_button=True
                        )

                        with gr.Row():
                            msg_input = gr.Textbox(
                                label="Message",
                                placeholder="Posez votre question...",
                                lines=2,
                                scale=4,
                            )
                            send_btn = gr.Button("📤 Envoyer", variant="primary", scale=1)

                        clear_btn = gr.Button("🗑️ Effacer la conversation")

                        gr.Examples(
                            examples=[
                                "Quelle est la capitale du Québec?",
                                "Explique la Loi 25 du Québec en 3 points",
                                "Calcule TPS (5%) et TVQ (9.975%) sur 1500$",
                                "Quels sont les risques d'utiliser l'IA sans conformité?",
                            ],
                            inputs=msg_input,
                            label="💡 Questions exemples",
                        )

                    with gr.Column(scale=1):
                        gr.Markdown("### 📊 Métriques")
                        metrics_display = gr.Markdown("")

                        gr.Markdown("### ℹ️ Guide de sélection")
                        gr.Markdown("""
**Faible difficulté**:
- sonar-small (rapide)
- 8b-instruct (économique)

**Moyen difficulté**:
- sonar-large (équilibré)

**Haute difficulté**:
- sonar-huge (précis)
- 70b-instruct (puissant)
                        """)

                # Connexions événements
                model_selector.change(
                    fn=app_instance.format_model_info, inputs=[model_selector], outputs=[model_info]
                )

                msg_input.submit(
                    fn=app_instance.process_message,
                    inputs=[msg_input, model_selector, chatbot],
                    outputs=[msg_input, chatbot, metrics_display],
                )

                send_btn.click(
                    fn=app_instance.process_message,
                    inputs=[msg_input, model_selector, chatbot],
                    outputs=[msg_input, chatbot, metrics_display],
                )

                clear_btn.click(fn=lambda: ([], ""), outputs=[chatbot, metrics_display])

            # ========== ONGLET COMPARAISON ==========
            with gr.Tab("⚖️ Comparaison de Modèles"):
                gr.Markdown("""
## Comparez les réponses de plusieurs modèles

Testez la même question avec différents modèles pour voir les différences de qualité,
vitesse et style de réponse.
                """)

                compare_query = gr.Textbox(
                    label="Question à tester", placeholder="Entrez votre question...", lines=3
                )

                with gr.Row():
                    compare_model1 = gr.Dropdown(
                        choices=list(PERPLEXITY_MODELS.keys()), label="Modèle 1", value="sonar"
                    )
                    compare_model2 = gr.Dropdown(
                        choices=list(PERPLEXITY_MODELS.keys()), label="Modèle 2", value="sonar-pro"
                    )
                    compare_model3 = gr.Dropdown(
                        choices=list(PERPLEXITY_MODELS.keys()),
                        label="Modèle 3",
                        value="sonar-reasoning",
                    )

                compare_btn = gr.Button("🔍 Comparer les modèles", variant="primary", size="lg")

                comparison_results = gr.Markdown(label="Résultats de comparaison")

                gr.Examples(
                    examples=[
                        "Explique la différence entre la Loi 25 et le RGPD",
                        "Une PME veut utiliser l'IA pour analyser des CV. Quelles sont les obligations légales au Québec?",
                        "Compare les avantages et inconvénients de 3 tailles de modèles LLM (petit, moyen, grand)",
                    ],
                    inputs=compare_query,
                    label="💡 Questions de comparaison",
                )

                compare_btn.click(
                    fn=app_instance.compare_models,
                    inputs=[compare_query, compare_model1, compare_model2, compare_model3],
                    outputs=[comparison_results],
                )

            # ========== ONGLET INFO MODÈLES ==========
            with gr.Tab("📚 Informations Modèles"):
                gr.Markdown("""
## Tous les Modèles Perplexity Disponibles

Chaque modèle a ses forces et cas d'usage spécifiques.
                """)

                for model_key, model_info in PERPLEXITY_MODELS.items():
                    with gr.Accordion(
                        f"{model_info['name']} - {model_info['description']}", open=False
                    ):
                        gr.Markdown(f"""
**Nom complet**: `{model_info['full_name']}`

**Cas d'usage**: {model_info['use_case']}

**Caractéristiques**:
- **Latence**: {model_info['latency']}
- **Qualité**: {model_info['quality']}
- **Coût relatif**: {model_info['cost']}

**Fonctionnalités**: {', '.join(model_info['features'])}

---

**Quand l'utiliser?**

{model_info['description']}
                        """)

    return app


# ============================================================================
# POINT D'ENTRÉE
# ============================================================================

if __name__ == "__main__":
    import os

    # Vérifier la clé API
    if not os.getenv("PERPLEXITY_API_KEY"):
        print("❌ ERREUR: PERPLEXITY_API_KEY non définie dans .env")
        sys.exit(1)

    print("=" * 60)
    print("🚀 Lancement de FilAgent Model Selector")
    print("=" * 60)

    app = create_interface()

    app.launch(server_name="0.0.0.0", server_port=7861, share=False, show_error=True)
