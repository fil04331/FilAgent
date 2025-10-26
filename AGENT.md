Cartographier la configuration de départ et les dépendances – passer en revue les guides d’installation/démarrage et les YAML de configuration pour confirmer les paramètres du modèle, des temps limites et des politiques par défaut avant toute expérimentation.

Valider le pipeline API ↔️ agent – analyser l’endpoint FastAPI /chat, la gestion des conversations et le cycle de raisonnement (construction du contexte, itérations outils/réponse) afin d’identifier les points de contrôle ou d’extension nécessaires.

Auditer les middlewares de conformité – examiner la journalisation JSONL, les Decision Records signés et le suivi de provenance pour vérifier l’exhaustivité des traces et définir les améliorations (ex. contrôles de santé, durcissement WORM).

Évaluer la persistance mémoire – vérifier la création des tables SQLite, la stratégie TTL et les index afin d’anticiper le dimensionnement ou les migrations vers d’autres backends si besoin.

Passer en revue l’arsenal d’outils et la sandbox – confirmer les garanties de sécurité (filtrage des arguments, timeouts) et préparer l’ajout d’outils métiers supplémentaires via le registre centralisé.

Planifier les benchmarks et la mesure continue – structurer une campagne avec le harnais générique d’évaluation pour quantifier la qualité des réponses et suivre les régressions au fil des itérations.




















