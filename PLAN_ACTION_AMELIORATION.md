# Plan d'Action - Amélioration Continue FilAgent

**Date**: 2026-02-06  
**Type**: Roadmap Technique MLOps  
**Durée**: 4 sprints (1 mois)  
**Objectif**: Atteindre excellence en production

---

## 🎯 Objectifs Stratégiques

### Vision 4 Sprints
```
Sprint 1 → STABILITÉ     : Corrections critiques (Production Ready)
Sprint 2 → ROBUSTESSE    : Tests et fiabilité
Sprint 3 → EXCELLENCE    : Qualité et optimisation  
Sprint 4 → INNOVATION    : MLOps avancé
```

---

## 📅 SPRINT 1: Corrections Critiques (Semaine 1)

### 🎯 Objectif: Production Ready
**Durée**: 5 jours ouvrables  
**Effort**: ~5 jours-personne  
**Priorité**: 🔴 CRITIQUE

### Tâches

#### Jour 1-2: Corrections de Sécurité et Stabilité

**Task 1.1: Corriger Bare Except Blocks** (4h)
```python
# Fichiers à modifier:
# - memory/retention.py (6+ locations)
# - test_filagent_capabilities.py (2 locations)
# - tests/test_document_analyzer_security.py (1 location)

# Pattern à rechercher:
grep -rn "except:" memory/ tests/

# Correction type:
- except:                              # ❌ AVANT
+ except (ValueError, TypeError) as e:  # ✅ APRÈS
+     logger.warning(f"Error: {e}", exc_info=True)
```

**Validation**:
```bash
# Vérifier qu'il ne reste aucun bare except
flake8 . --select=E722 --count
# Objectif: 0 erreurs
```

**Task 1.2: Sécuriser Global State avec Locks** (3h)
```python
# Fichiers à modifier:
# - planner/work_stealing.py
# - planner/plan_cache.py
# - planner/metrics.py

# Pattern à ajouter:
import threading

_instance_lock = threading.Lock()
_executor_instance = None

def get_executor():
    global _executor_instance
    if _executor_instance is None:
        with _instance_lock:
            if _executor_instance is None:
                _executor_instance = Executor()
    return _executor_instance
```

**Validation**:
```bash
# Tester sous charge
pytest tests/test_concurrency.py -n 8
```

**Task 1.3: Corriger F824 dans template_loader.py** (30min)
```python
# Fichier: runtime/template_loader.py ligne 251

# Option A: Assigner la variable
def clear_template_cache():
    global _template_loader
    _template_loader = None  # ✅ Assigner
    get_template_loader.cache_clear()

# Option B: Retirer le global (préféré)
def clear_template_cache():
    # global _template_loader  # ❌ Retirer cette ligne
    if get_template_loader.cache_info().currsize > 0:
        get_template_loader.cache_clear()
```

**Validation**:
```bash
flake8 runtime/template_loader.py --select=F824
# Objectif: 0 erreurs
```

#### Jour 3: Nettoyage du Code

**Task 1.4: Remplacer Debug Prints par Logging** (4h)
```python
# Fichiers à modifier:
# - runtime/agent.py (15+ prints)
# - planner/executor.py (8+ prints)

# Script de remplacement automatique:
#!/bin/bash
# replace_prints.sh

# Remplacer dans agent.py
sed -i 's/print(f"\[HTN-DEBUG\]/logger.debug("[HTN]/g' runtime/agent.py
sed -i 's/print(f"\[EXECUTOR\]/logger.info("[EXECUTOR]/g' planner/executor.py

# Retirer les newlines inutiles
sed -i 's/\\n\[HTN-DEBUG\]/[HTN]/g' runtime/agent.py
```

**Validation manuelle**:
```bash
# Chercher tous les prints restants
grep -rn "print(" runtime/ planner/ --exclude="*test*"
# Objectif: 0 résultats (hors tests)
```

**Task 1.5: Exécuter Black et Corriger Formatting** (1h)
```bash
# Auto-formatter
black . --line-length 100

# Vérifier
black --check .

# Corriger imports non utilisés
autoflake --remove-all-unused-imports --in-place --recursive runtime/ planner/ tools/
```

**Validation**:
```bash
flake8 . --select=W293,E501,F401 --count
# Objectif: Réduction de 80% des warnings
```

#### Jour 4-5: Tests et Documentation

**Task 1.6: Tests de Régression** (4h)
```bash
# Exécuter suite complète
pytest tests/ -v --cov=runtime --cov=planner --cov=tools --cov-report=html

# Vérifier couverture maintenue
# Objectif: > 84% (ne pas régresser)
```

**Task 1.7: Mettre à Jour Documentation** (2h)
```markdown
# Ajouter dans CHANGELOG.md:

## [2026-02-06] - Sprint 1 Corrections

### Fixed
- 🔐 Corrected bare except blocks for proper error handling
- 🔒 Added threading locks for global state management  
- 🧹 Replaced debug prints with proper logging
- ✨ Fixed flake8 F824 warning in template_loader.py
- 📝 Code formatting with Black (100 chars)

### Security
- Improved exception handling visibility
- Thread-safe singleton implementations

### Quality
- Reduced flake8 warnings by 80%
- All critical security issues resolved
```

**Task 1.8: Code Review et Merge** (2h)
```bash
# Créer PR
git checkout -b fix/sprint1-critical-corrections
git add .
git commit -m "fix: critical code quality and security corrections (Sprint 1)"
git push origin fix/sprint1-critical-corrections

# Code review obligatoire
# Merge après validation
```

### ✅ Critères de Succès Sprint 1

| Critère | Cible | Mesure |
|---------|-------|--------|
| Bare except blocks | 0 | `flake8 --select=E722` |
| Debug prints production | 0 | `grep print() runtime/` |
| Flake8 critiques | 0 | `flake8 --select=F` |
| Tests passants | >96% | `pytest --tb=short` |
| Thread safety | ✅ | `pytest test_concurrency` |

---

## 📅 SPRINT 2: Robustesse et Tests (Semaine 2)

### 🎯 Objectif: Fiabilité > 99%
**Durée**: 5 jours ouvrables  
**Effort**: ~5 jours-personne  
**Priorité**: 🟡 HAUTE

### Tâches

#### Jour 1-2: Correction des Tests Échoués

**Task 2.1: Fixer ComplianceGuardian Tests** (4h)
```python
# 14 tests à corriger dans test_compliance_guardian_comprehensive.py

# AVANT:
result = guardian.validate_query("query")
assert isinstance(result, ValidationResult)  # ❌

# APRÈS:
result = guardian.validate_query("query")
assert isinstance(result, dict)  # ✅
assert "valid" in result
assert "warnings" in result
assert "errors" in result
```

**Task 2.2: Fixer Tool Execution Tests** (2h)
```python
# 2 tests dans test_tools_registry_comprehensive.py

# AVANT:
calc.execute(expression="2 + 2")  # ❌

# APRÈS:
calc.execute({"expression": "2 + 2"})  # ✅
```

**Task 2.3: Ajouter Database Fixtures Manquantes** (3h)
```python
# tests/conftest.py

@pytest.fixture
async def initialized_db():
    """Fixture pour DB initialisée."""
    db = await get_database()
    await db.initialize()
    yield db
    await db.cleanup()
```

#### Jour 3-4: Tests Additionnels

**Task 2.4: Tests de Dérive de Modèle** (6h)
```python
# tests/test_model_drift.py (NOUVEAU)

import pytest
from runtime.model_monitoring import DriftDetector

@pytest.mark.integration
def test_prediction_drift_detection():
    """Test détection drift sur prédictions."""
    detector = DriftDetector()
    
    baseline = load_baseline_predictions()
    current = get_current_predictions()
    
    drift_score = detector.calculate_drift(baseline, current)
    assert drift_score < 0.1, f"Drift détecté: {drift_score}"

@pytest.mark.integration  
def test_feature_drift_detection():
    """Test détection drift sur features."""
    detector = DriftDetector()
    
    # Simuler drift de features
    baseline_features = generate_features(seed=42)
    drifted_features = generate_features(seed=43, shift=2.0)
    
    drift = detector.detect_feature_drift(baseline_features, drifted_features)
    assert drift.is_significant == True
```

**Task 2.5: Tests de Charge** (4h)
```python
# tests/test_load.py (NOUVEAU)

import pytest
from locust import HttpUser, task, between

class FilAgentLoadTest(HttpUser):
    wait_time = between(1, 3)
    
    @task(3)
    def query_agent(self):
        self.client.post("/api/v1/agent/query", json={
            "query": "Analyze this document",
            "conversation_id": "test-conv-001"
        })
    
    @task(1)
    def health_check(self):
        self.client.get("/health")

# Exécuter: locust -f tests/test_load.py --headless -u 100 -r 10 -t 5m
```

#### Jour 5: Validation

**Task 2.6: Tests de Régression Complets** (4h)
```bash
# Suite complète
pytest tests/ -v --cov-report=html

# Tests de performance
pytest tests/ -m performance --benchmark-only

# Tests de compliance
pytest tests/ -m compliance -v
```

### ✅ Critères de Succès Sprint 2

| Critère | Cible | Mesure |
|---------|-------|--------|
| Tests passants | >98% | 1,495+/1,523 |
| Couverture | >85% | coverage.py |
| Temps exécution tests | <10min | pytest --durations=10 |
| Tests drift | ✅ | 3+ tests drift |
| Tests charge | ✅ | 100 users, 5min |

---

## 📅 SPRINT 3: Excellence et Optimisation (Semaine 3)

### 🎯 Objectif: Qualité Code Premium
**Durée**: 5 jours ouvrables  
**Effort**: ~5 jours-personne  
**Priorité**: 🟢 MOYENNE

### Tâches

#### Jour 1-2: Refactoring Complexité

**Task 3.1: Réduire Complexité Agent.__init__** (6h)
```python
# runtime/agent.py
# Complexité actuelle: 20 → Cible: <10

# Extraire méthodes:
def _initialize_model(self, config):
    """Initialize model backend."""
    # Code extraction
    
def _initialize_memory(self, config):
    """Initialize memory systems."""
    # Code extraction
    
def _initialize_planner(self, config):
    """Initialize HTN planner."""
    # Code extraction

def __init__(self, config):
    self.config = config
    self._initialize_model(config)
    self._initialize_memory(config)
    self._initialize_planner(config)
```

**Task 3.2: Consolider GenerationConfig** (2h)
```python
# Supprimer duplication dans model_interface.py
# Garder seulement dans config.py

# runtime/config.py (GARDER)
class GenerationConfig(BaseModel):
    temperature: float = 0.7
    max_tokens: int = 2048
    # ...

# runtime/model_interface.py (SUPPRIMER)
# class GenerationConfig: ...  # ❌ Supprimer

# Importer partout:
from runtime.config import GenerationConfig
```

#### Jour 3-4: Amélioration Gestion d'Erreurs

**Task 3.3: Exceptions Spécifiques** (6h)
```python
# Créer exceptions custom
# runtime/exceptions.py (NOUVEAU)

class FilAgentException(Exception):
    """Base exception for FilAgent."""
    pass

class ModelError(FilAgentException):
    """Model inference errors."""
    pass

class ToolExecutionError(FilAgentException):
    """Tool execution errors."""
    pass

class ComplianceViolation(FilAgentException):
    """Compliance policy violations."""
    pass

# Utiliser partout:
# runtime/server.py
try:
    result = await agent.process(query)
except ModelError as e:
    raise HTTPException(status_code=503, detail=f"Model error: {e}")
except ComplianceViolation as e:
    raise HTTPException(status_code=403, detail=f"Compliance: {e}")
```

**Task 3.4: Chemins Relatifs → Path Objects** (3h)
```python
# memory/retention.py et autres

from pathlib import Path

# AVANT:
config_path = "config/retention.yaml"  # ❌

# APRÈS:
BASE_DIR = Path(__file__).parent.parent
config_path = BASE_DIR / "config" / "retention.yaml"  # ✅
```

#### Jour 5: Documentation et Review

**Task 3.5: Documentation Refactoring** (3h)
```markdown
# docs/REFACTORING_SUMMARY.md (NOUVEAU)

## Sprint 3 Refactoring

### Code Quality Improvements
- Reduced cyclomatic complexity in Agent.__init__ (20 → 8)
- Consolidated GenerationConfig duplication
- Implemented custom exception hierarchy
- Migrated to Path objects (cross-platform)

### Metrics
- Maintainability Index: 68 → 82
- Cyclomatic Complexity: 15 → 9 (avg)
- Code Duplication: 5% → 2%
```

### ✅ Critères de Succès Sprint 3

| Critère | Cible | Mesure |
|---------|-------|--------|
| Complexité moyenne | <10 | radon cc -a |
| Duplication code | <3% | jscpd |
| Maintainability Index | >80 | radon mi -s |
| Exception coverage | 100% | Custom exceptions |
| Path objects | 100% | grep "config/" |

---

## 📅 SPRINT 4: MLOps Avancé (Semaine 4)

### 🎯 Objectif: Production Excellence
**Durée**: 5 jours ouvrables  
**Effort**: ~5 jours-personne  
**Priorité**: 🔵 FUTURE

### Tâches

#### Jour 1-2: Circuit Breaker et Resilience

**Task 4.1: Implémenter Circuit Breaker** (6h)
```python
# runtime/resilience.py (NOUVEAU)

from circuitbreaker import circuit

class APICircuitBreaker:
    @circuit(failure_threshold=5, recovery_timeout=60)
    async def call_perplexity_api(self, query):
        """Call with circuit breaker protection."""
        response = await self.client.post(...)
        if response.status_code >= 500:
            raise Exception("API Error")
        return response

# Métriques:
# - Requests total
# - Circuit open/closed state
# - Fallback invocations
```

**Task 4.2: Retry avec Exponential Backoff** (3h)
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def robust_api_call(self, request):
    """API call with automatic retry."""
    return await self.api_client.post(request)
```

#### Jour 3-4: Monitoring Avancé

**Task 4.3: Dashboards Grafana** (6h)
```yaml
# grafana/dashboards/filagent_mlops.json

{
  "dashboard": {
    "title": "FilAgent MLOps",
    "panels": [
      {
        "title": "Model Latency P95",
        "targets": [{
          "expr": "histogram_quantile(0.95, model_inference_duration_seconds)"
        }]
      },
      {
        "title": "Drift Score",
        "targets": [{
          "expr": "model_drift_score"
        }]
      },
      {
        "title": "Circuit Breaker State",
        "targets": [{
          "expr": "circuit_breaker_state"
        }]
      }
    ]
  }
}
```

**Task 4.4: Alerting Rules** (3h)
```yaml
# grafana/alerts/filagent.yml

groups:
  - name: filagent_alerts
    interval: 30s
    rules:
      - alert: HighModelLatency
        expr: model_latency_p95 > 2000
        for: 5m
        annotations:
          summary: "Model latency too high"
          
      - alert: ModelDriftDetected
        expr: model_drift_score > 0.1
        for: 10m
        annotations:
          summary: "Model drift above threshold"
          
      - alert: CircuitBreakerOpen
        expr: circuit_breaker_state == 1
        for: 2m
        annotations:
          summary: "Circuit breaker opened for API"
```

#### Jour 5: Documentation Production

**Task 4.5: Runbook Opérationnel** (4h)
```markdown
# docs/OPERATIONS_RUNBOOK.md (NOUVEAU)

## Runbook Opérationnel FilAgent

### Incident Response

#### 1. High Latency (P95 > 2s)
**Symptômes**: Requêtes lentes, timeouts
**Investigation**:
1. Check Grafana dashboard "Model Latency"
2. Verify Perplexity API status
3. Check resource utilization (CPU, RAM)

**Résolution**:
1. Si API externe: activer fallback local
2. Si ressources: scale horizontal (K8s)
3. Si modèle: restart service

#### 2. Model Drift Detected
**Symptômes**: Drift score > 0.1
**Investigation**:
1. Compare baseline vs current predictions
2. Analyze feature distributions
3. Review recent data changes

**Résolution**:
1. Trigger retraining pipeline
2. Validate new model
3. Canary deployment (10% → 50% → 100%)

#### 3. Circuit Breaker Open
**Symptômes**: API calls failing repeatedly
**Investigation**:
1. Check external API health
2. Review error logs
3. Verify network connectivity

**Résolution**:
1. Wait for recovery timeout (60s)
2. Manual reset if needed: `curl -X POST /admin/circuit/reset`
3. Fallback to local model if persistent
```

**Task 4.6: Deployment Strategy** (3h)
```yaml
# docs/DEPLOYMENT_STRATEGY.md (NOUVEAU)

## Stratégie de Déploiement

### Canary Deployment

1. **Phase 1: 10% Traffic** (30 min)
   - Deploy new version to canary pods
   - Route 10% traffic
   - Monitor: errors, latency, drift
   - Rollback if: error rate > 0.5%

2. **Phase 2: 50% Traffic** (1 hour)
   - Increase to 50% if Phase 1 success
   - Monitor same metrics
   - Rollback if: latency P95 > 2s

3. **Phase 3: 100% Traffic** (2 hours)
   - Full rollout
   - Monitor for 24h
   - Keep previous version for quick rollback

### Rollback Procedure
```bash
# Rollback automatique
kubectl rollout undo deployment/filagent-api

# Rollback vers version spécifique
kubectl rollout undo deployment/filagent-api --to-revision=3
```
```

### ✅ Critères de Succès Sprint 4

| Critère | Cible | Mesure |
|---------|-------|--------|
| Circuit breaker | ✅ | Implemented + tested |
| Dashboards Grafana | 3+ | Production dashboards |
| Alert rules | 5+ | Critical alerts |
| Runbook | ✅ | Complete operations guide |
| Canary deployment | ✅ | Documented + tested |

---

## 📊 Métriques de Succès Globales (4 Sprints)

### KPIs Finaux

| Catégorie | Métrique | Avant | Après | Objectif |
|-----------|----------|-------|-------|----------|
| **Qualité** | Tests passants | 95.5% | 98%+ | ✅ |
| **Qualité** | Couverture code | 84.46% | 85%+ | ✅ |
| **Qualité** | Flake8 errors | 493 | <50 | ✅ |
| **Qualité** | Complexité moyenne | 15 | <10 | ✅ |
| **Fiabilité** | Disponibilité | N/A | 99.5%+ | ✅ |
| **Fiabilité** | P95 latency | N/A | <500ms | ✅ |
| **Fiabilité** | Error rate | N/A | <0.1% | ✅ |
| **Sécurité** | Bare excepts | 9 | 0 | ✅ |
| **Sécurité** | CVEs | 0 | 0 | ✅ |
| **MLOps** | Monitoring | Basic | Advanced | ✅ |
| **MLOps** | Alerting | None | 5+ rules | ✅ |
| **MLOps** | Drift detection | No | Yes | ✅ |

---

## 🎓 Bonnes Pratiques à Adopter

### Standards de Développement

#### 1. Avant chaque commit
```bash
# Checklist pré-commit
black .                    # Format code
flake8 .                   # Lint
mypy runtime/ planner/     # Type check
pytest tests/ -x           # Tests pass
```

#### 2. Avant chaque PR
```bash
# Checklist PR
pytest tests/ --cov       # Coverage > 85%
pytest -m integration     # Integration tests
pytest -m compliance      # Compliance tests
python validate_deps.py   # No vulnerabilities
```

#### 3. Logging Standard
```python
# ✅ BON
logger.info("Processing query", extra={
    "query_id": query_id,
    "conversation_id": conv_id,
    "duration_ms": duration
})

# ❌ MAUVAIS
print(f"Processing {query_id}")
```

#### 4. Exception Handling
```python
# ✅ BON
try:
    result = risky_operation()
except SpecificError as e:
    logger.error("Operation failed", exc_info=True, extra={"context": ctx})
    raise ServiceError("Failed") from e

# ❌ MAUVAIS
try:
    result = risky_operation()
except:
    pass
```

---

## 🔗 Ressources et Références

### Documentation Interne
- [AUDIT_POST_MERGE_MLOPS.md](AUDIT_POST_MERGE_MLOPS.md) - Audit complet
- [CLAUDE.md](CLAUDE.md) - Quick reference
- [COMPLIANCE_FEATURES.md](docs/COMPLIANCE_FEATURES.md) - Conformité
- [DEPLOYMENT.md](docs/DEPLOYMENT.md) - Déploiement

### Outils Externes
- **Black**: https://black.readthedocs.io/
- **Flake8**: https://flake8.pycqa.org/
- **Pytest**: https://docs.pytest.org/
- **Circuit Breaker**: https://pypi.org/project/circuitbreaker/
- **Grafana**: https://grafana.com/docs/
- **Prometheus**: https://prometheus.io/docs/

---

## ✅ Validation Finale

### Checklist Sprint par Sprint

#### Sprint 1 ✅
- [ ] Bare except blocks corrigés
- [ ] Global state thread-safe
- [ ] Debug prints → logging
- [ ] Black formatter appliqué
- [ ] F824 corrigé
- [ ] Tests régression passent
- [ ] Documentation mise à jour
- [ ] PR merged

#### Sprint 2 ✅
- [ ] 62 tests échoués corrigés
- [ ] Tests drift ajoutés
- [ ] Tests charge ajoutés
- [ ] Database fixtures complètes
- [ ] Couverture > 85%
- [ ] Performance validée

#### Sprint 3 ✅
- [ ] Complexité Agent < 10
- [ ] GenerationConfig consolidé
- [ ] Exceptions custom implémentées
- [ ] Path objects migration
- [ ] Documentation refactoring
- [ ] Code review approuvé

#### Sprint 4 ✅
- [ ] Circuit breaker implémenté
- [ ] Dashboards Grafana créés
- [ ] Alert rules configurées
- [ ] Runbook opérationnel écrit
- [ ] Stratégie canary documentée
- [ ] Tests production validés

---

**Créé par**: Ingénieur MLOps - GitHub Copilot  
**Date**: 2026-02-06  
**Version**: 1.0  
**Statut**: READY FOR EXECUTION

---

## 📞 Support et Questions

Pour toute question sur ce plan d'action:
1. Consulter la documentation interne
2. Vérifier les exemples de code
3. Reviewer les PRs précédentes
4. Contacter l'équipe MLOps

**Prochaine révision**: Fin Sprint 1 (2026-02-13)
