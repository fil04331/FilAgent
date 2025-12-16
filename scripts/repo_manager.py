"""Script d'Agent Dédié à la Gestion du Dépôt (Repository Manager Agent).
Ce script instancie un agent spécialisé pour la maintenance, l'audit et l'évolution du code source FilAgent,
en respectant strictement les standards définis.
"""

import sys
import os
import textwrap
from typing import Dict, Optional, List
import logging

# Configuration des chemins pour garantir l'import des modules runtime
# Assumes script is in scripts/ or root
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir) if current_dir.endswith("scripts") else current_dir

if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from runtime.agent import Agent
    from runtime.config import get_config
    from runtime.model_interface import init_model
except ImportError as e:
    print(f"❌ Erreur critique d'import : {e}")
    print("Assurez-vous d'être à la racine du projet ou d'avoir configuré le PYTHONPATH.")
    sys.exit(1)

# --- Configuration du Logging Spécifique ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [REPO-AGENT] - %(levelname)s - %(message)s"
)
logger = logging.getLogger("RepoAgent")


class RepositoryAgent(Agent):
    """
    Agent spécialisé dans la maintenance du dépôt FilAgent.
    Surcharge l'Agent standard pour appliquer des directives d'ingénierie strictes.
    """

    def _get_system_prompt(self) -> str:
        """
        Surcharge du prompt système pour définir l'identité 'Repository Guardian'.
        Intègre les directives des fichiers ArchitectePrincipal.md et IngenieurQAAutomation.md.
        """
        tools = self.tool_registry.list_all()
        tool_descriptions = []

        for tool_name, tool in tools.items():
            try:
                schema = tool.get_schema()
                tool_descriptions.append(
                    f"- {tool_name}: {schema.get('description', 'Pas de description')}\n"
                    f"  Paramètres: {schema.get('parameters', {})}"
                )
            except Exception as e:
                logger.warning(f"Impossible de charger le schéma pour l'outil {tool_name}: {e}")

        # Prompt d'ingénierie stricte
        raw_prompt = f"""Tu es le 'Repository Guardian' du projet FilAgent.
Ton périmètre est EXCLUSIVEMENT ce dépôt de code source.
Tu es un Ingénieur IA Senior et Architecte Logiciel.

CONTEXTE TECHNIQUE :
- Architecture : Modulaire, basée sur `runtime/`, `planner/` (HTN), et `tools/`.
- Standards : Pydantic V2 (validation stricte), Typing Strict (pas de `Any`), Pytest (>80% coverage).
- Conformité : Loi 25 (protection des données), Audit Trails obligatoires.

TES RESPONSABILITÉS :
1. **Audit de Code** : Analyser le code existant pour détecter la dette technique, les failles de sécurité ou les violations de typage.
2. **Maintenance** : Proposer des refactorings respectant les principes SOLID et DRY.
3. **QA & Tests** : T'assurer que tout nouveau code est couvert par des tests unitaires (mocking I/O) et d'intégration.
4. **Documentation** : Maintenir les ADR (Architecture Decision Records) et la documentation technique à jour.

RÈGLES D'INTERVENTION (PROTOCOLES STRICTS) :
- **AUDIT-FIRST** : Avant de proposer une modification, analyse les fichiers existants via `file_reader`.
- **NO REGRESSION** : Ne jamais casser la compatibilité existante sans raison majeure et documentée.
- **TYPAGE** : Tout code généré doit être strictement typé (Python 3.9+ type hinting).
- **OUTILS** : Utilise `python_sandbox` pour vérifier des hypothèses ou exécuter des tests, et `file_reader` pour lire le contexte.

OUTILS DISPONIBLES :
{chr(10).join(tool_descriptions)}

Format d'appel d'outil (JSON strict) :
{"tool": "nom_outil", "arguments": {"param": "valeur"}}

Si tu manques d'information sur un fichier, utilise `file_reader` pour le lire AVANT de répondre.
Ne réponds jamais avec des suppositions. Vérifie le code source.
"""
        return textwrap.dedent(raw_prompt).strip()


def interactive_session():
    """Lance une session interactive avec l'agent du dépôt."""
    print("🚀 Initialisation du Repository Manager Agent...")
    try:
        # 1. Charger la configuration
        config = get_config()

        # 2. Instancier l'agent spécialisé
        # Note: On force l'utilisation de RepositoryAgent au lieu de Agent standard
        agent = RepositoryAgent(config=config)

        # 3. Initialiser le modèle (chargement des poids/connexion API)
        agent.initialize_model()

        print("\n✅ Agent prêt. Posez vos questions sur le dépôt (ex: 'Analyse runtime/agent.py', 'Génère un test pour...').")
        print("Tapez 'exit' ou 'quit' pour quitter.\n")

        conversation_id = "repo_session_cli"

        while True:
            try:
                user_input = input("\n[USER] > ").strip()

                if user_input.lower() in ["exit", "quit"]:
                    print("Arrêt de la session.")
                    break

                if not user_input:
                    continue

                # Appel à l'agent
                print("⏳ Analyse en cours...")
                result = agent.chat(user_input, conversation_id=conversation_id)
                response = result.get("response", "Erreur: Pas de réponse générée.")
                tools_used = result.get("tools_used", [])

                print(f"\n[AGENT] > {response}")

                if tools_used:
                    print(f"\n🛠️ Outils utilisés : {', '.join(tools_used)}")

            except KeyboardInterrupt:
                print("\nInterruption détectée. Arrêt.")
                break
            except Exception as e:
                logger.error(f"Erreur durant l'échange : {e}")

    except Exception as e:
        logger.critical(f"Échec de l'initialisation de l'agent : {e}")
        sys.exit(1)


if __name__ == "__main__":
    interactive_session()
