
1. Cartographie de la configuration et des dépendances
Le guide de démarrage confirme l’environnement Python 3.10+, l’installation via pip install -r requirements.txt, l’initialisation de la base SQLite et le démarrage du serveur sur python runtime/server.py avec un curl de test sur /chat.

requirements.txt regroupe les dépendances clés : FastAPI/uvicorn pour l’API, llama-cpp-python pour le backend LLM par défaut, cryptography pour les signatures EdDSA, ainsi que les outils d’observabilité et de test.

config/agent.yaml fixe les paramètres de génération (temperature 0.2, top_p 0.95, max_tokens 800), les timeouts (60 s pour la génération, 30 s pour les outils, 300 s global), le modèle GGUF par défaut et la mémoire (TTL 30 jours pour l’épisodique, 14 jours pour la reconstruction sémantique) tout en activant WORM, PII redaction et provenance par défaut.

Le loader Pydantic (runtime/config.py) valide ces sections et expose un singleton get_config(), ce qui permet de centraliser toute évolution des paramètres.

2. Pipeline FastAPI ↔️ agent
L’API /chat (FastAPI) instancie l’agent via get_agent(), vérifie la présence d’un message utilisateur, et renvoie une réponse type OpenAI en injectant l’ID de conversation et le modèle actif; les TODO signalent la nécessité de calculer les tokens réels et d’enrichir /health avec des checks de dépendances.

Le cœur agent applique une boucle de raisonnement sur 10 itérations maximum, avec enregistrement de chaque message en mémoire, hachage du prompt pour la traçabilité, parsing des balises <tool_call> et relance du modèle après exécution d’outils; la logique actuelle ne réutilise cependant pas la variable context construite pour le modèle (le prompt reste message), ce qui limite l’ancrage conversationnel et mérite une correction avant les tests.

Les appels d’outils sont journalisés, hashés puis tracés, et un DR signé est émis si des outils sont utilisés ou si des actions critiques sont détectées dans la réponse; la boucle se termine en stockant la réponse et en loggant la fin de conversation.

Suggestion : intégrer context au prompt transmis au modèle et propager les métriques d’usage (tokens) depuis GenerationResult vers la réponse API pour disposer d’un suivi cohérent avant benchmarking.

3. Middlewares de conformité et traçabilité
Le logger JSONL crée des événements append-only avec trace/span IDs et hash des entrées/sorties outils, mais il faudrait relier ce flux au logger WORM pour garantir l’immuabilité promise dans la configuration.

Les Decision Records sont signés EdDSA, sauvegardés dans logs/decisions/, et les clés sont stockées sous provenance/signatures/; pour durcir WORM, envisager un stockage hors disque (vault/HSM) et l’intégration d’une vérification périodique via le middleware WORM.

Le tracker PROV-JSON enregistre les graphes d’activités (génération, outils) dans logs/traces/otlp, avec liens agent→activité→artefacts.

Le middleware WORM génère un arbre de Merkle et des checkpoints sur logs/digests/; il manque cependant le branchement effectif depuis le logger pour bénéficier du mode append-only automatique.

Recommandations : compléter /health avec une vérification de disponibilité des logs/provenance, exécuter régulièrement create_checkpoint/verify_integrity, et automatiser la rotation/rotation de clés selon la politique 90 jours définie dans provenance.yaml.

4. Persistance mémoire
memory/episodic.py crée deux tables (conversations/messages) avec index sur conversation_id et timestamp, stocke chaque échange et propose un nettoyage basé sur updated_at; la TTL par défaut est de 30 jours.

RetentionManager charge config/retention.yaml, applique les TTL par type (événements 90 jours, DR 365 jours, audit 7 ans, etc.), et fournit une routine de purge multi-dossiers, avec option dry-run et export avant suppression.

Avant montée en charge, prévoir des migrations (ex. vers Postgres) en gardant la même couche DAO, et ajouter des tests automatiques pour run_cleanup afin de vérifier la conformité aux bases légales configurées.

5. Arsenal d’outils et sandbox
Le registre central (tools/registry.py) instancie par défaut python_sandbox, file_read, math_calculator et expose register() pour brancher rapidement des outils métiers supplémentaires; l’agent réutilise ce registre pour générer le prompt système dynamique.

Le sandbox Python bloque des patterns dangereux (__import__, eval, os.system, etc.), limite la taille du code et stoppe l’exécution après 30 secondes; prévoir un durcissement supplémentaire (cgroups ou execution dans un microservice isolé) pour supporter du code utilisateur non fiable en production.

Le lecteur de fichiers applique une allowlist (working_set/, temp/, memory/working_set/), détecte le path traversal et limite la taille à 10 MB, mais il serait utile d’aligner dynamiquement ces chemins avec config/policies.yaml pour éviter les divergences statiques.

6. Benchmarks et mesure continue
config/eval_targets.yaml fixe les seuils (HumanEval pass@1≥0.65, MBPP≥0.60, SWE-bench lite 50 % sur 50 tâches, scénarios agentiques ≥0.75) et impose des métriques de conformité (DR/provenance ≥95 % de couverture, zéro violation critique sur 1000 tâches).

Le harnais générique (eval/base.py) charge les tâches, mesure la latence par item, calcule le taux de réussite et sauvegarde les rapports datés dans eval/reports/; il suffit de fournir un callback agent qui wrappe /chat pour orchestrer une campagne complète.

Plan de campagne conseillé : automatiser un run hebdomadaire (cron ou CI) qui 1) synchronise le modèle/config, 2) exécute chaque benchmark avec suivi des métriques citées, 3) compare les rapports aux seuils acceptance_criteria, puis 4) archive les rapports/artefacts dans le pipeline de provenance pour détecter toute régression de performance ou de conformité.

Aucune commande de test exécutée pour cette analyse (revue statique uniquement).



















