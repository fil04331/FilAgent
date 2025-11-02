# 📋 HTN Planning Module - FilAgent

**Version:** 1.0.0  
**Date:** 2025-11-01  
**Status:** ✅ Production-Ready

---

## 🎯 Vue d'ensemble

Module de planification hiérarchique (HTN - Hierarchical Task Network) permettant de décomposer des requêtes complexes en graphes de tâches exécutables avec gestion automatique des dépendances et parallélisation.

### Fonctionnalités principales

✅ **Décomposition intelligente** - Requêtes complexes → DAG de sous-tâches  
✅ **Stratégies multiples** - Rule-based, LLM-based, Hybrid  
✅ **Exécution parallèle** - Tâches indépendantes simultanées  
✅ **Validation multicouche** - BASIC, STRICT, PARANOID  
✅ **Traçabilité complète** - Conformité Loi 25, RGPD, AI Act  
✅ **Recovery gracieux** - Retry, fallback, circuit breaker  

---

## 📐 Architecture

```
planner/
├── __init__.py           # Exports publics
├── task_graph.py         # Structures de données (Task, TaskGraph)
├── planner.py            # Algorithme de décomposition HTN
├── executor.py           # Exécuteur avec tri topologique
├── verifier.py           # Validation et self-checks
├── state_machine.yaml    # Machine à états, transitions, critères d'arrêt
└── README.md             # Ce fichier
```

### Composants clés

#### 1. **Task & TaskGraph** (`task_graph.py`)
- **Task**: Unité atomique de travail avec métadonnées
- **TaskGraph**: DAG de tâches avec validation de cycles
- **Complexité**: O(V + E) pour construction et tri topologique

#### 2. **HierarchicalPlanner** (`planner.py`)
- Décompose requêtes en sous-tâches
- 3 stratégies: RULE_BASED, LLM_BASED, HYBRID
- Justification de chaque décomposition (AI Act)

#### 3. **TaskExecutor** (`executor.py`)
- Exécution séquentielle, parallèle, ou adaptive
- Gestion dépendances via tri topologique
- Propagation automatique des échecs

#### 4. **TaskVerifier** (`verifier.py`)
- Validation multi-niveaux des résultats
- Self-checks automatiques
- Détection d'anomalies

---

## 🚀 Quick Start

### Installation

```bash
# Module déjà dans FilAgent, pas d'installation nécessaire
cd /path/to/FilAgent
python3 -c "from planner import HierarchicalPlanner; print('✓ OK')"
```

### Usage basique

```python
from planner import (
    HierarchicalPlanner,
    TaskExecutor,
    TaskVerifier,
    PlanningStrategy,
    ExecutionStrategy,
    VerificationLevel,
)

# 1. Créer le planificateur
planner = HierarchicalPlanner(
    model_interface=model,  # Interface LLM
    tools_registry=registry,  # Registre d'outils
    max_decomposition_depth=3,
)

# 2. Planifier une requête complexe
query = "Analyse data.csv, génère statistiques, crée rapport PDF"
result = planner.plan(
    query=query,
    strategy=PlanningStrategy.HYBRID,
)

print(f"Plan créé: {len(result.graph.tasks)} tâches")
print(f"Confiance: {result.confidence}")
print(f"Raisonnement: {result.reasoning}")

# 3. Créer l'exécuteur
executor = TaskExecutor(
    action_registry={
        "read_file": read_file_func,
        "analyze_data": analyze_func,
        "create_pdf": create_pdf_func,
    },
    strategy=ExecutionStrategy.PARALLEL,
    max_workers=4,
)

# 4. Exécuter le plan
exec_result = executor.execute(result.graph)

print(f"Succès: {exec_result.success}")
print(f"Complétées: {exec_result.completed_tasks}/{len(result.graph.tasks)}")
print(f"Durée: {exec_result.total_duration_ms:.0f}ms")

# 5. Vérifier les résultats
verifier = TaskVerifier(default_level=VerificationLevel.STRICT)
verifications = verifier.verify_graph_results(result.graph)

for task_id, verif in verifications.items():
    if not verif.passed:
        print(f"❌ Tâche {task_id}: {verif.errors}")
```

---

## 📚 Exemples détaillés

### Exemple 1: Décomposition rule-based

```python
planner = HierarchicalPlanner()

# Requête avec pattern connu
query = "Lis donnees.csv, calcule la moyenne"
result = planner.plan(query, strategy=PlanningStrategy.RULE_BASED)

# Tâches générées automatiquement:
# 1. read_file(donnees.csv)
# 2. calculate(moyenne) [depends_on: [1]]

for task in result.graph.topological_sort():
    print(f"- {task.name}: {task.action}({task.params})")
```

### Exemple 2: Décomposition LLM-based

```python
planner = HierarchicalPlanner(model_interface=llm)

# Requête complexe et inhabituelle
query = """
Analyse les ventes du Q3 par région, 
identifie les tendances clés,
génère recommandations stratégiques
"""

result = planner.plan(query, strategy=PlanningStrategy.LLM_BASED)

print(f"Tâches générées par LLM:")
for task in result.graph.tasks.values():
    deps = f" (dépend de: {task.depends_on})" if task.depends_on else ""
    print(f"  {task.priority.value}. {task.name}{deps}")

print(f"\nJustification LLM:")
print(result.reasoning)
```

### Exemple 3: Exécution parallèle

```python
# Créer un graphe avec tâches indépendantes
graph = TaskGraph()

task1 = Task(name="fetch_data_source_1", action="fetch", params={"url": "api1"})
task2 = Task(name="fetch_data_source_2", action="fetch", params={"url": "api2"})
task3 = Task(name="fetch_data_source_3", action="fetch", params={"url": "api3"})
task4 = Task(
    name="merge_data",
    action="merge",
    depends_on=[task1.task_id, task2.task_id, task3.task_id],
)

for task in [task1, task2, task3, task4]:
    graph.add_task(task)

# Identifier les niveaux parallèles
levels = graph.get_parallelizable_tasks()
print(f"Niveaux de parallélisation: {len(levels)}")
print(f"Niveau 0 (parallèle): {[t.name for t in levels[0]]}")
print(f"Niveau 1 (dépendant): {[t.name for t in levels[1]]}")

# Exécuter avec parallélisation
executor = TaskExecutor(
    action_registry=actions,
    strategy=ExecutionStrategy.PARALLEL,
    max_workers=3,
)
result = executor.execute(graph)

# Niveau 0 exécuté en parallèle (3 workers)
# Niveau 1 exécuté après complétion du niveau 0
```

### Exemple 4: Gestion d'erreurs et recovery

```python
from planner.task_graph import TaskPriority

# Tâche critique avec retry
critical_task = Task(
    name="validate_payment",
    action="validate_payment",
    params={"amount": 1000},
    priority=TaskPriority.CRITICAL,  # Échec = abort
)

# Tâche optionnelle (peut échouer)
optional_task = Task(
    name="send_notification",
    action="send_email",
    params={"to": "user@example.com"},
    priority=TaskPriority.OPTIONAL,  # Échec = skip
)

graph = TaskGraph()
graph.add_task(critical_task)
graph.add_task(optional_task)

# Exécuter avec retry automatique (voir state_machine.yaml)
executor = TaskExecutor(action_registry=actions)
result = executor.execute(graph)

if not result.success:
    print(f"Échecs critiques: {result.errors}")
    # Decision Record généré automatiquement (conformité Loi 25)
```

### Exemple 5: Validation stricte

```python
verifier = TaskVerifier(default_level=VerificationLevel.PARANOID)

# Enregistrer vérificateur custom
def verify_pdf_generation(task, result):
    """Vérifie qu'un PDF valide a été généré"""
    checks = {}
    errors = []
    
    # Check 1: Fichier existe
    if not os.path.exists(result.get("pdf_path", "")):
        errors.append("PDF file not found")
        checks["file_exists"] = False
    else:
        checks["file_exists"] = True
    
    # Check 2: Taille > 0
    if checks["file_exists"]:
        size = os.path.getsize(result["pdf_path"])
        checks["file_not_empty"] = size > 0
        if size == 0:
            errors.append("PDF file is empty")
    
    return VerificationResult(
        passed=len(errors) == 0,
        level=VerificationLevel.PARANOID,
        checks=checks,
        errors=errors,
    )

verifier.register_custom_verifier("create_pdf", verify_pdf_generation)

# Vérifier après exécution
task = graph.tasks["pdf_generation_task_id"]
verif = verifier.verify_task(task, level=VerificationLevel.PARANOID)

if verif.passed:
    print(f"✅ PDF valide (confiance: {verif.confidence_score:.2%})")
else:
    print(f"❌ Erreurs: {verif.errors}")
```

---

## 🔧 Configuration

### Machine à états (`state_machine.yaml`)

Configurations importantes:

```yaml
# Timeout d'exécution (par environnement)
environments:
  production:
    max_execution_time_seconds: 300  # 5 minutes
    max_retries: 3
    circuit_breaker_threshold: 3

# Stratégies de recovery
recovery_strategies:
  simple_retry:
    max_attempts: 3
    backoff_strategy: exponential
    backoff_base_seconds: 1

# Critères d'arrêt
stopping_criteria:
  critical_failure:
    action: abort_execution
    priority_threshold: 5  # CRITICAL
```

Modifier selon vos besoins:

```python
import yaml

with open("planner/state_machine.yaml") as f:
    config = yaml.safe_load(f)

# Augmenter le timeout
config["environments"]["production"]["max_execution_time_seconds"] = 600

# Désactiver retry pour debug
config["recovery_strategies"]["simple_retry"]["max_attempts"] = 0
```

---

## 📊 Métriques et monitoring

### Statistiques disponibles

```python
# Statistiques du planificateur
planner_stats = planner.get_stats()  # Si implémenté

# Statistiques d'exécution
executor_stats = executor.get_stats()
print(f"Exécutions totales: {executor_stats['total_executions']}")
print(f"Succès: {executor_stats['successful_executions']}")
print(f"Échecs: {executor_stats['failed_executions']}")

# Statistiques de vérification
verifier_stats = verifier.get_stats()
print(f"Vérifications totales: {verifier_stats['total_verifications']}")
print(f"Taux de succès: {verifier_stats['passed'] / verifier_stats['total_verifications']:.2%}")
```

### Logs de traçabilité

Tous les événements sont tracés dans `logs/` avec:

- **events.jsonl** - Tous les événements (transitions, exécutions)
- **decisions/** - Decision Records (échecs critiques, cancellations)
- **provenance/** - Provenance W3C (lignée des données)

```python
# Exemple de log d'événement
{
  "timestamp": "2025-11-01T14:30:00Z",
  "event_type": "task_execution_start",
  "task_id": "abc123",
  "task_name": "analyze_data",
  "action": "analyze_data",
  "params": {"file": "data.csv"},
  "dependencies": ["def456"],
  "metadata": {...}
}
```

---

## 🧪 Tests

### Tests unitaires

```bash
# Exécuter tous les tests
python3 -m pytest tests/test_planner/ -v

# Tests par module
python3 -m pytest tests/test_planner/test_task_graph.py -v
python3 -m pytest tests/test_planner/test_planner.py -v
python3 -m pytest tests/test_planner/test_executor.py -v
python3 -m pytest tests/test_planner/test_verifier.py -v

# Avec coverage
python3 -m pytest tests/test_planner/ --cov=planner --cov-report=html
```

### Tests d'intégration

```bash
python3 tests/integration/test_htn_end_to_end.py
```

---

## 🛡️ Conformité et sécurité

### Conformité légale

✅ **Loi 25 (Québec)** - Transparence des décisions automatisées
- Decision Records pour échecs critiques
- Traçabilité complète des états et transitions
- Rétention 7 ans des logs de décisions

✅ **RGPD (UE)** - Protection des données
- Logs immuables (WORM)
- Métadonnées de provenance (W3C PROV)
- Droit à l'explication (reasoning dans PlanningResult)

✅ **AI Act (UE)** - Exigences transparence
- Justification des décompositions LLM
- Self-checks obligatoires (verifier.py)
- Documentation exhaustive

✅ **NIST AI RMF** - Gestion des risques
- Validation multicouche (BASIC, STRICT, PARANOID)
- Recovery automatique
- Circuit breaker contre cascades d'échecs

### Sécurité

- **Sandbox isolation** - Actions exécutées dans environnement contrôlé
- **Timeout enforcement** - Limite temps d'exécution
- **Resource limits** - max_workers, max_depth
- **Error propagation** - Échecs ne corrompent pas l'état

---

## 🤝 Contribution

### Ajouter une stratégie de planification

```python
# Dans planner.py
def _plan_custom_strategy(self, query, metadata):
    """Votre stratégie personnalisée"""
    # Votre logique ici
    return PlanningResult(...)

# Enregistrer
class PlanningStrategy(str, Enum):
    CUSTOM = "custom"  # Ajouter
```

### Ajouter un vérificateur custom

```python
def my_custom_verifier(task, result):
    # Votre logique de vérification
    return VerificationResult(...)

verifier.register_custom_verifier("my_action", my_custom_verifier)
```

---

## 📖 Références

### Papers académiques
- **HTN Planning**: "Hierarchical Task Networks" (Erol et al., 1994)
- **Task Decomposition**: "Goal Decomposition" (Sacerdoti, 1977)
- **Topological Sort**: "Algorithm T" (Knuth, 1973)

### Implémentations similaires
- **PDDL**: Planning Domain Definition Language
- **AutoGPT**: Autonomous agent avec décomposition
- **LangChain**: Framework avec planning basique

---

## 📝 Changelog

### v1.0.0 (2025-11-01)
- ✨ Implémentation initiale complète
- ✅ Task & TaskGraph avec validation de cycles
- ✅ HierarchicalPlanner (rule-based, LLM-based, hybrid)
- ✅ TaskExecutor (sequential, parallel, adaptive)
- ✅ TaskVerifier (multi-niveaux)
- ✅ State machine YAML avec recovery
- ✅ Documentation complète

---

**Auteur**: FilAgent Team  
**Licence**: Propriétaire  
**Contact**: fil@filagent.ai
