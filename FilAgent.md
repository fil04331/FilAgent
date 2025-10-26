Arborescence cible (exécutable en local, évolutive)

llmagenta/
├─ config/
│  ├─ agent.yaml                    # hyperparamètres, top-p, température, max_tokens, timeouts, seeds
│  ├─ policies.yaml                 # règles d’usage, redaction, PII, RBAC, limites d’outils, réseau
│  ├─ retention.yaml                # durées de conservation, bases légales, minimisation
│  ├─ provenance.yaml               # schémas PROV, exigences de signature, horodatage
│  └─ eval_targets.yaml             # seuils de parité/supériorité (HumanEval, MBPP, SWE-bench, tasks agentiques)
├─ models/
│  ├─ runtime/
│  │  ├─ llama.cpp/                 # binaire + kernels CPU/GPU
│  │  ├─ tgi/                       # text-generation-inference optionnel
│  │  └─ vllm/                      # serveur vLLM optionnel
│  ├─ weights/
│  │  ├─ base.gguf                  # modèle fondation local (quantisé si besoin)
│  │  ├─ instruct.gguf              # variante instruction-tuned
│  │  └─ adapters/
│  │     └─ code.lora               # LoRA/QLoRA code-intelligence
│  └─ tokenizer/
│     └─ tokenizer.model
├─ memory/                          # mémoire gérée
│  ├─ episodic.sqlite               # épisodes structurés (clé conversation_id, task_id)
│  ├─ semantic/
│  │  ├─ index.faiss                # index vectoriel
│  │  ├─ store.parquet              # passages + métadonnées
│  │  └─ encoder/                   # modèle d’embedding local (gguf / onnx)
│  ├─ working_set/                  # contexte actif, TTL par entrée
│  └─ policies/
│     ├─ dedup_rules.yaml
│     ├─ retention_policies.yaml
│     └─ pii_redaction.yaml
├─ logs/
│  ├─ events/*.jsonl                # JSONL (OTel-compatible), 1 ligne = 1 événement
│  ├─ traces/otlp/                  # traces OpenTelemetry locales
│  ├─ decisions/DR-*.json           # Decision Records signés (voir schéma ci-dessous)
│  ├─ prompts/*.jsonl               # prompts/réponses/outil-calls (hashés, PII masquées)
│  ├─ safeties/*.jsonl              # blocages, filtres, raisons
│  └─ digests/                      # Merkle roots, checkpoints de journaux (WORM)
├─ audit/
│  ├─ reports/                      # rapports mensuels, DPIA/DPTA, fiches d’incident
│  ├─ samples/                      # échantillons vérifiables
│  └─ signed/                       # archives scellées (WORM, signature + horodatage)
├─ tools/                           # exécuteurs outillés (local-only)
│  ├─ python_sandbox/               # pyodide/microVM, quotas CPU/mémoire, fs virtuel
│  ├─ shell_sandbox/                # bash restreint, allowlist, chroot/namespace
│  ├─ code_exec/                    # runner tests (pytest, uv), timeouts/cgroups
│  └─ connectors/                   # fichiers locaux, DBs locales (pas d’Internet par défaut)
├─ policy/
│  ├─ guardrails.yaml               # regex, JSONSchema, sorties admissibles, stop sequences
│  ├─ pii.yaml                      # détecteurs/masqueurs PII, champs sensibles
│  ├─ rlhf_rules.yaml               # règles de refus/alignement
│  └─ legal/                        # templates clauses, notices, consentements
├─ planner/
│  ├─ task_graph.py                 # planification hiérarchique, DAG d’actions
│  ├─ state_machine.yaml            # états, transitions, critères d’arrêt
│  └─ verifier.py                   # self-checks, tests unitaires sur sorties intermédiaires
├─ provenance/
│  ├─ prov_schema.json              # W3C PROV-JSON
│  ├─ signatures/                   # clés, politiques de rotation, chaines de confiance
│  └─ snapshots/                    # versions prompts, policies, modèles (hash, commit)
├─ eval/
│  ├─ benchmarks/
│  │  ├─ humaneval/                 # harness reproduction pass@k
│  │  ├─ mbpp/
│  │  ├─ swe_bench_lite/
│  │  └─ agent_tasks/               # navigation fichiers, édition, planification + outils
│  ├─ runs/
│  └─ reports/
├─ runtime/
│  ├─ server.py                     # API locale (OpenAI-compatible), auth locale, rate limits
│  ├─ router.py                     # sélection modèle (routing par tâche), A/B, canary
│  ├─ decoder.py                    # sampling contrôlé, seeds, logits processors
│  └─ middleware/
│     ├─ logging.py                 # JSONL + OTel
│     ├─ redaction.py               # masquage PII en temps réel
│     ├─ constraints.py             # JSONSchema/Regex sur sorties (validation dure)
│     └─ audittrail.py              # enregistrement DR + PROV
└─ docs/
   ├─ ADRs/                         # Architecture Decision Records
   └─ SOPs/                         # procédures (incident, rotation clés, export sujet)

Schémas et invariants (extraits minimaux)

logs/events JSONL (OTel-like)

{
  "ts": "2025-08-20T15:12:05.431-04:00",
  "trace_id": "9b1d1f...",
  "span_id": "e21a...",
  "level": "INFO",
  "actor": "agent.core",
  "event": "tool.call",
  "task_id": "T-20250820-0012",
  "conversation_id": "C-1a2b3c",
  "input_ref": "sha256:...prompt",
  "output_ref": "sha256:...out",
  "pii_redacted": true
}

Decision Record (DR)

{
  "dr_id": "DR-20250820-0007",
  "ts": "2025-08-20T15:13:12.002-04:00",
  "actor": "agent.core",
  "task_id": "T-20250820-0012",
  "policy_version": "policies@a1b2c3d",
  "model_fingerprint": "weights/base.gguf@sha256:abc...",
  "prompt_hash": "sha256:...",
  "reasoning_markers": ["plan:3-steps", "constraints:jsonschema:v2"],
  "tools_used": ["python_sandbox@v0.3"],
  "alternatives_considered": ["do_nothing", "ask_clarification"],
  "decision": "proceed_generate_code",
  "constraints": {"timeout_s": 30, "max_tokens": 800},
  "expected_risk": ["path_traversal:low", "pii_leak:low"],
  "signature": "eddsa:..."
}

PROV-JSON (provenance minimal)

{
  "entity": {"out:9": {"prov:label": "response.json", "hash": "sha256:..."}},
  "activity": {"act:7": {"prov:type": "generation", "startTime": "...", "endTime": "..." }},
  "agent": {"ag:agentcore": {"prov:type": "softwareAgent", "version": "server@4.2.1"}},
  "wasGeneratedBy": {"wgb:1": {"prov:entity": "out:9", "prov:activity": "act:7"}},
  "wasAssociatedWith": {"waw:1": {"prov:activity": "act:7", "prov:agent": "ag:agentcore"}}
}

Validation dure de sortie
	•	JSONSchema obligatoire pour actions/outils.
	•	Regex/allowlist pour commandes shell.
	•	Post-validators spécifiques (sécurité, conformité, cohérence métier).
	•	Refus dur si validation échoue (code, motif enregistré).

Mémoire gérée
	•	Épisodique : fil par conversation/task, TTL configurable, résumé déterministe (seed fixé) + ancrage par hash des messages retenus.
	•	Sémantique : embeddings locaux, index FAISS/HNSW ; éviction LRU + fraîcheur ; re-embedding périodique versionné.
	•	Politique : filtrage PII avant vectorisation ; droits d’accès par rôle ; purge automatique selon retention.yaml ; export sujet (portabilité).
	•	Rappel contrôlé : fenêtres de contexte contraintes (budget tokens), anti-dérive par score minimal de pertinence + seuil de décroissance temporelle.
	•	Traçabilité : chaque récupération mémoire = événement logué (trace_id, scores, ids de passages).

Journalisation des interprétations (loggable et analysables)
	•	Niveaux : events (granulaire), decisions (DR), traces (spans), prompts (entrées/sorties).
	•	Analyse rapide : parquet + views SQL (DuckDB/SQLite), métriques: latence, taux refus, violations de policy, diff prompts, dérive.
	•	Reproductibilité : seed, sampler, version modèle, gabarit prompt, policies, outils = tous fixés et hashés par réponse.
	•	Échantillonnage légal : quotas d’exemples persistés, PII masquée par défaut ; accès via RBAC et justification consignée.

Conformité et traçabilité decisionnelle (local, sans cloud)
	•	Base légale & minimisation : retention.yaml encode finalités, durées (ex.: 90j events, 365j DR), champs sensibles exclus par défaut.
	•	DPIA/DPTA : modèles de rapports dans audit/reports ; registre des traitements ; matrice risques → mesures.
	•	Provenance scellée : journaux en WORM (append-only), scellés périodiques (Merkle root), signature + horodatage.
	•	Droits des personnes : export, rectification, effacement sélectif (sauf WORM : masquage irréversible des PII, conservation des hachés).
	•	Transparence : DR obligatoires pour décisions ayant impact ; cartouches standard dans réponses (« modèle, version, horodatage, outils, limites »).
	•	Sécurité : isolation outils (microVM/cgroups), politiques réseau = par défaut OFF, allowlist stricte.

Capacité ciblée (≥ Codex / ChatGPT-5 Agent — exigence d’acceptation)
	•	Routing modèle : base instruct + LoRA code ; option mixture-of-experts local si GPU multiple.
	•	Toolformer-like : préférer appels d’outils explicités (code_exec, python_sandbox).
	•	Harness d’évaluation : HumanEval pass@1 ≥ baseline cible ; MBPP ≥ baseline ; SWE-bench-lite ≥ baseline ; tasks agentiques locales (planifier→éditer→tester) ≥ taux cible.
	•	Gates : déploiement bloqué si seuils non atteints ; rapports dans eval/reports.

Sécurité opérationnelle
	•	Samplers : nucleus/top-p + température bornés ; seeds fixés ; anti-répétition ; logits processors (blocklists).
	•	Guardrails : JSONSchema, regex, invariants ; post-vérif code (lint + tests).
	•	Sandboxes : ressource caps, read-only FS par défaut, pas d’accès réseau sauf connecteurs autorisés.
	•	Key management : si secrets locaux nécessaires → vault local, rotation et scopes minimaux.

Erreurs probables si oubli + Préventions
	1.	Absence de seed et config figée → sorties non reproductibles.
Prévention : seed obligatoire, snapshot config (hash), stockage dans DR.
	2.	Journalisation non WORM → altération non détectable.
Prévention : append-only + Merkle + signature + horodatage ; vérif d’intégrité en tâche planifiée.
	3.	PII non masquée dans prompts/logs → non-conformité.
Prévention : redaction middleware avant persistance ; scans périodiques ; tests CI sur échantillons.
	4.	Fenêtre contexte saturée → troncature silencieuse et hallucinations.
Prévention : budget tokens, résumés déterministes, alerte si >80 % budget, refus dur si dépassement.
	5.	Index sémantique obsolète → rappels incohérents.
Prévention : re-embedding versionné, test de fraîcheur, invalidation planifiée.
	6.	Mise à jour modèle sans fingerprint → régressions invisibles.
Prévention : fingerprint obligatoire, canary + A/B, gate par seuils eval.
	7.	Ambiguïtés temporelles/format → actions erronées.
Prévention : ISO 8601, fuseau explicite America/Toronto, bornes inclusives/exclusives documentées.
	8.	Tools non restreints → exécution dangereuse (path traversal, rm récursif).
Prévention : allowlist, chroot/namespace, validations chemin, no-write par défaut.
	9.	Logs trop verbeux → fuite d’info, coûts d’analyse.
Prévention : niveaux log par événement, quotas, agrégations parquet, masquage par défaut.
	10.	Raisonnement non vérifié → chaînes convaincantes mais fausses.
Prévention : verifiers (tests unitaires, assertions), self-checks, exécution contrôlée dans sandbox.
	11.	Absence de DR/provenance → décision non traçable.
Prévention : middleware audittrail obligatoire ; refus si DR non écrit.
	12.	RBAC absent → accès non autorisé aux mémoires/logs.
Prévention : rôles minimaux, journalisation d’accès, justification obligatoire.
	13.	Décalage d’horloge → incohérences de traçabilité.
Prévention : NTP local, tolérances, horodatage monotone.
	14.	Schémas non validés → sorties non parseables.
Prévention : JSONSchema/Regex, tests contractuels, fuzzing de schéma.
	15.	Échecs silencieux des outils → décisions sur état incomplet.
Prévention : codes d’erreur obligatoires, timeouts, retries bornés, circuit-breaker.

Méthode d’évolution
	•	ADRs pour chaque changement majeur ; liens vers runs d’évaluation et DR associés.
	•	Versioning complet : modèles, prompts, policies, outils.
	•	Backtests : relecture de journaux, re-exécution déterministe sur snapshot.
	•	Red teaming local : corpus d’attaques prompt-injection, jailbreaks, exfiltration ; métriques de résistance.
	•	Observabilité : métriques (Prometheus local), alertes sur dérives (latence, taux refus, violations policy).

Paramètres par défaut (suggestion de départ, à ajuster par tests)
	•	temperature: 0.2 ; top_p: 0.95 ; max_tokens: 800 ; seed: 42
	•	Mémoire : episodic.TTL=30j ; semantic.rebuild=14j
	•	Logs : rotation quotidienne, scellé Merkle/heure
	•	DR obligatoires pour actions non triviales (écriture disque, exécution code, modification fichiers)

Acceptation « capacité ≥ Codex/ChatGPT-5 agent » (critères formels)
	•	Code : HumanEval pass@1 ≥ baseline cible ; MBPP ≥ baseline ; temps moyen ≤ baseline +10 %.
	•	Agentique : taux de réussite ≥ baseline sur tâches planifier→éditer→tester locales.
	•	Conformité : 0 violation critique (PII, WORM, DR manquant) sur 1 000 tâches.
	•	Traçabilité : 100 % des réponses actionnables avec DR + PROV cohérents et vérifiables.