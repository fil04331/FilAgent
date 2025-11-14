## Contexte

Conformément à la vision du projet FilAgent (voir architecture dans `eval/benchmarks/`), intégrer les benchmarks standards pour valider les capacités de l'agent LLM et garantir une performance ≥ aux standards de l'industrie (Codex, ChatGPT-5 Agent).

## Objectifs

### Phase 1: HumanEval Integration
- [ ] Configurer harness HumanEval dans `eval/benchmarks/humaneval/`
- [ ] Implémenter calcul pass@k (pass@1, pass@5, pass@10)
- [ ] Ajouter timeout et isolation pour exécution sécurisée
- [ ] Générer rapport automatique dans `eval/reports/`

### Phase 2: MBPP Integration
- [ ] Configurer harness MBPP dans `eval/benchmarks/mbpp/`
- [ ] Adapter prompts pour compatibilité FilAgent
- [ ] Validation résultats avec tests unitaires
- [ ] Métriques de performance (temps, tokens, précision)

### Phase 3: SWE-bench-lite Integration
- [ ] Configurer SWE-bench-lite dans `eval/benchmarks/swe_bench_lite/`
- [ ] Tests de tâches agentiques: navigation, édition, tests
- [ ] Intégration avec HTN Planning
- [ ] Validation end-to-end sur tâches réelles

### Phase 4: Seuils et CI Integration
- [ ] Définir seuils d'acceptation dans `config/eval_targets.yaml`
- [ ] Créer job CI pour exécution automatique
- [ ] Gates de déploiement basés sur benchmarks
- [ ] Alertes si régression de performance

## Critères de Succès

Selon `config/eval_targets.yaml` et vision du projet:

### Code Generation
- **HumanEval pass@1**: ≥ baseline cible (ex: 85%)
- **MBPP pass@1**: ≥ baseline cible (ex: 80%)
- **Temps moyen**: ≤ baseline +10%

### Agent Tasks
- **SWE-bench-lite**: Taux de réussite ≥ baseline (ex: 40%)
- **Planification + Édition + Tests**: Pipeline complet fonctionnel
- **Traçabilité**: 100% des exécutions avec Decision Records

### Performance
- **Latence**: p95 < 5 secondes par tâche
- **Token efficiency**: Minimiser tokens tout en gardant qualité
- **Parallélisation**: 40%+ des tâches parallélisées (HTN)

## Architecture Technique

```
eval/
├── benchmarks/
│   ├── humaneval/
│   │   ├── run.py           # Script exécution
│   │   ├── harness.py       # Logique pass@k
│   │   └── README.md
│   ├── mbpp/
│   │   ├── run.py
│   │   ├── harness.py
│   │   └── README.md
│   └── swe_bench_lite/
│       ├── run.py
│       ├── tasks.json       # Définition tâches
│       └── README.md
├── runs/                    # Résultats exécutions
│   └── {timestamp}/
│       ├── humaneval_results.json
│       ├── mbpp_results.json
│       └── swe_bench_results.json
└── reports/                 # Rapports consolidés
    ├── latest_report.json
    └── historical_trends.json
```

## Configuration Exemple

```yaml
# config/eval_targets.yaml
benchmarks:
  humaneval:
    enabled: true
    pass_k: [1, 5, 10]
    min_pass_1: 0.85
    timeout_per_task_sec: 30

  mbpp:
    enabled: true
    min_pass_1: 0.80
    timeout_per_task_sec: 30

  swe_bench_lite:
    enabled: true
    min_success_rate: 0.40
    max_execution_time_sec: 300

gates:
  block_deployment_if_below_threshold: true
  alert_on_regression: true
  regression_threshold: 0.05  # 5% drop
```

## CI/CD Integration

```yaml
# .github/workflows/benchmarks.yml
name: Benchmarks

on:
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * 0'  # Weekly on Sunday 2am

jobs:
  run-benchmarks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run HumanEval
        run: python eval/benchmarks/humaneval/run.py
      - name: Run MBPP
        run: python eval/benchmarks/mbpp/run.py
      - name: Run SWE-bench-lite
        run: python eval/benchmarks/swe_bench_lite/run.py
      - name: Check Thresholds
        run: python scripts/check_benchmark_thresholds.py
```

## Référence

- **Documentation**: `FilAgent.md` (sections eval/benchmarks)
- **Vision projet**: Capacité ≥ Codex/ChatGPT-5 Agent
- **Conformité**: Tous les benchmarks avec Decision Records et traçabilité

## Priorité

**HAUTE** - Validation objective des capacités de l'agent

## Estimation

3-4 semaines
- Semaine 1-2: HumanEval + MBPP
- Semaine 3: SWE-bench-lite
- Semaine 4: CI integration + optimisation

## Labels Suggérés

- `evaluation`
- `benchmark`
- `enhancement`
- `high priority`
- `performance`
