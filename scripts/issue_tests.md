## 📋 Description

Augmenter la couverture de tests pour renforcer la robustesse et la fiabilité du système FilAgent.

## 🎯 Objectifs

- [ ] Atteindre 80% de couverture de code
- [ ] Ajouter tests unitaires manquants
- [ ] Créer tests d'intégration pour flux critiques
- [ ] Implémenter tests de régression

## 📝 Tâches

### Tests Unitaires Prioritaires

- [ ] **Agent Core** (`runtime/agent.py`)
  - [ ] Test `_requires_planning()` avec différents patterns
  - [ ] Test `_run_with_htn()` avec mock HTN planner
  - [ ] Test fallback mechanisms

- [ ] **HTN Planner** (`planner/`)
  - [ ] Test task decomposition
  - [ ] Test parallel execution
  - [ ] Test verification levels

- [ ] **Compliance Guardian**
  - [ ] Test PII redaction patterns
  - [ ] Test forbidden query detection
  - [ ] Test email pattern exclusion

- [ ] **Tools Registry**
  - [ ] Test tool registration
  - [ ] Test tool execution with timeouts
  - [ ] Test sandboxing

### Tests d'Intégration

- [ ] **Workflow E2E**
  - [ ] User query → HTN planning → Execution → Response
  - [ ] Multi-tool orchestration
  - [ ] Error recovery flows

- [ ] **Compliance Flow**
  - [ ] Decision Record generation
  - [ ] WORM logging integrity
  - [ ] Provenance tracking

### Tests de Performance

- [ ] Benchmark HTN planning time
- [ ] Memory usage profiling
- [ ] Concurrent request handling

## 🛠️ Outils Recommandés

- `pytest-cov` pour coverage
- `pytest-benchmark` pour performance
- `hypothesis` pour property-based testing
- `pytest-mock` pour mocking

## 📊 Métriques de Succès

- Coverage > 80%
- Tous les tests passent en < 5 minutes
- 0 tests flaky
- Documentation de test à jour

## 🏷️ Labels

- `testing`
- `enhancement`
- `good first issue`

## 🔗 Références

- [Normes de codage FilAgent](../NORMES_CODAGE_FILAGENT.md)
- [Guide de contribution](../CONTRIBUTING.md)
- [Architecture](../docs/ADRs/)