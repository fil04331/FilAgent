# FilAgent — KPIs & SLOs Architecture Document

> **Version**: 1.0.0  
> **Date**: 2025-12-10  
> **Auteur**: Principal Software Architect  
> **Statut**: Production-Ready

---

## Executive Summary

Ce document définit les **Key Performance Indicators (KPIs)** et **Service Level Objectives (SLOs)** pour FilAgent v2.0.0, un système multi-agents gouverné basé sur HTN (Hierarchical Task Network) planning.

**Dimensions de monitoring couvertes :**
1. **System/Infrastructure** — Uptime, latence, saturation, circuit breakers
2. **Cognitive/HTN Logic** — Planning efficiency, décomposition, goal achievement
3. **Development/Code Quality** — Couverture, dette technique, CI/CD velocity

---

## 1. Architectural Context

### 1.1 Vue d'ensemble du système

FilAgent est un agent LLM gouverné conçu pour les PME québécoises, avec conformité intégrée (Loi 25, RGPD, AI Act).

```
┌─────────────────────────────────────────────────────────────────┐
│                        FilAgent v2.0.0                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   runtime/  │  │  planner/   │  │   tools/    │              │
│  │   agent.py  │──│  planner.py │──│ registry.py │              │
│  │   server.py │  │  executor.py│  │ calculator  │              │
│  │ middleware/ │  │  verifier.py│  │ file_reader │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│         │                │                │                      │
│         ▼                ▼                ▼                      │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              Observability Layer (Prometheus)               ││
│  │  • HTNMetrics  • DecisionRecords  • AuditTrail             ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Bounded Contexts (DDD)

| Context | Module | Responsabilité | Métriques clés |
|---------|--------|----------------|----------------|
| **Planning** | `planner/` | Décomposition HTN, tri topologique | Planning duration, confidence |
| **Execution** | `planner/executor.py` | Orchestration séquentielle/parallèle | Task success rate, parallelization |
| **Compliance** | `runtime/middleware/` | Audit trail, RBAC, WORM | Verification pass rate |
| **Tools** | `tools/` | Exécution atomique d'actions | Tool latency, error rate |
| **Memory** | `memory/` | Épisodic, semantic, retention | Memory hit rate |

---

## 2. Performance Matrix — System/Infrastructure

### 2.1 Métriques d'infrastructure (RED Method + Saturation)


| Indicator Name | Category | Type | Unit | Description & Justification |
|:---|:---|:---|:---|:---|
| `filagent_http_requests_total` | System | Counter | requests | Nombre total de requêtes HTTP entrantes. Label: `method`, `endpoint`, `status_code`. Essentiel pour calculer le throughput et détecter les anomalies de trafic. |
| `filagent_http_request_duration_seconds` | System | Histogram | seconds | Latence des requêtes HTTP (P50, P90, P99). Buckets: `[0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]`. Critique pour SLO de latence. |
| `filagent_http_request_size_bytes` | System | Histogram | bytes | Taille des payloads entrants. Détecte les requêtes anormalement volumineuses (DoS potentiel). |
| `filagent_active_connections` | System | Gauge | connections | Connexions HTTP actives simultanées. Indicateur de saturation du serveur. |
| `filagent_memory_usage_bytes` | System | Gauge | bytes | Mémoire utilisée par le process Python. Labels: `type` (rss, heap, stack). |
| `filagent_cpu_usage_ratio` | System | Gauge | ratio [0-1] | Utilisation CPU du process. Seuil warning: 0.8, critical: 0.95. |
| `filagent_circuit_breaker_state` | System | Gauge | enum | État du circuit breaker (0=closed, 1=open, 2=half-open). Par service externe (LLM, DB). |
| `filagent_circuit_breaker_trips_total` | System | Counter | trips | Nombre de déclenchements du circuit breaker. Indicateur de dégradation upstream. |

### 2.2 Métriques de dépendances externes

| Indicator Name | Category | Type | Unit | Description & Justification |
|:---|:---|:---|:---|:---|
| `filagent_llm_request_duration_seconds` | External | Histogram | seconds | Latence des appels LLM (OpenAI, Perplexity, local). Label: `provider`, `model`. |
| `filagent_llm_tokens_total` | External | Counter | tokens | Tokens consommés par requête. Labels: `provider`, `direction` (input/output). Critique pour cost monitoring. |
| `filagent_llm_errors_total` | External | Counter | errors | Erreurs LLM par type. Labels: `provider`, `error_type` (timeout, rate_limit, api_error). |
| `filagent_db_query_duration_seconds` | External | Histogram | seconds | Latence des requêtes SQLite/aiosqlite. Label: `operation` (read, write, delete). |
| `filagent_db_connections_active` | External | Gauge | connections | Pool de connexions actives. Saturation si proche de max_connections. |

---

## 3. Performance Matrix — Cognitive/HTN Logic

### 3.1 Métriques de planification HTN (existantes + nouvelles)

| Indicator Name | Category | Type | Unit | Description & Justification |
|:---|:---|:---|:---|:---|
| `htn_requests_total` | HTN | Counter | requests | **[EXISTE]** Requêtes HTN totales. Labels: `strategy` (rule_based, llm_based, hybrid), `status`. |
| `htn_planning_duration_seconds` | HTN | Histogram | seconds | **[EXISTE]** Durée de planification. Buckets optimisés pour détection de lenteur. |
| `htn_planning_confidence` | HTN | Gauge | ratio [0-1] | **[EXISTE]** Score de confiance du plan généré. Seuil: ≥0.7 pour exécution. |
| `htn_decomposition_depth` | HTN | Histogram | levels | **[NOUVEAU]** Profondeur de décomposition des tâches. Indique complexité cognitive. |
| `htn_backtracking_count` | HTN | Counter | backtracks | **[NOUVEAU]** Nombre de retours arrière lors de la planification. Indicateur d'inefficacité heuristique. |
| `htn_method_selection_latency_seconds` | HTN | Histogram | seconds | **[NOUVEAU]** Temps de sélection de méthode de décomposition. Goulot d'étranglement potentiel. |
| `htn_plan_cache_hits_total` | HTN | Counter | hits | **[NOUVEAU]** Cache hits pour plans similaires. Améliore performance sur requêtes répétitives. |
| `htn_plan_cache_misses_total` | HTN | Counter | misses | **[NOUVEAU]** Cache misses. Ratio hit/miss indique efficacité du caching. |

### 3.2 Métriques d'exécution HTN (existantes + nouvelles)

| Indicator Name | Category | Type | Unit | Description & Justification |
|:---|:---|:---|:---|:---|
| `htn_execution_duration_seconds` | HTN | Histogram | seconds | **[EXISTE]** Durée d'exécution complète du plan. Labels: `strategy` (sequential, parallel, adaptive). |
| `htn_tasks_completed_total` | HTN | Counter | tasks | **[EXISTE]** Tâches complétées. Labels: `priority`, `action`, `status`. |
| `htn_tasks_failed_total` | HTN | Counter | tasks | **[EXISTE]** Tâches échouées. Labels: `priority`, `action`, `error_type`. |
| `htn_tasks_parallel_total` | HTN | Counter | tasks | **[EXISTE]** Tâches exécutées en parallèle. Indicateur d'efficacité. |
| `htn_task_queue_depth` | HTN | Gauge | tasks | **[NOUVEAU]** Tâches en attente d'exécution. Saturation si > 50. |
| `htn_work_stealing_operations_total` | HTN | Counter | steals | **[NOUVEAU]** Opérations de work-stealing entre workers. Indique load balancing. |
| `htn_dependency_resolution_time_seconds` | HTN | Histogram | seconds | **[NOUVEAU]** Temps de résolution du graphe de dépendances (tri topologique). |

### 3.3 Métriques de vérification (existantes + nouvelles)

| Indicator Name | Category | Type | Unit | Description & Justification |
|:---|:---|:---|:---|:---|
| `htn_verifications_total` | HTN | Counter | verifications | **[EXISTE]** Vérifications effectuées. Labels: `level` (basic, strict, paranoid), `status`. |
| `htn_verification_pass_rate` | HTN | Gauge | ratio [0-1] | **[EXISTE]** Taux de réussite des vérifications. Calculé via PromQL. |
| `htn_precondition_failures_total` | HTN | Counter | failures | **[NOUVEAU]** Échecs de préconditions. Indique mauvaise modélisation du domaine. |
| `htn_postcondition_violations_total` | HTN | Counter | violations | **[NOUVEAU]** Violations de postconditions. Détecte comportements inattendus. |


---

## 4. Performance Matrix — Development/Code Quality

### 4.1 Métriques de qualité de code

| Indicator Name | Category | Type | Unit | Description & Justification |
|:---|:---|:---|:---|:---|
| `filagent_test_coverage_ratio` | Dev | Gauge | ratio [0-1] | Couverture de tests (pytest-cov). Cible: ≥0.80. |
| `filagent_test_count_total` | Dev | Gauge | tests | Nombre total de fonctions de test. Actuel: 1,512. |
| `filagent_test_duration_seconds` | Dev | Gauge | seconds | Durée de la suite de tests complète. Cible: <120s. |
| `filagent_linter_violations_total` | Dev | Gauge | violations | Violations ruff/flake8/mypy. Labels: `severity` (error, warning, info). |
| `filagent_type_coverage_ratio` | Dev | Gauge | ratio [0-1] | Couverture de typage strict (mypy). Cible: ≥0.95. |
| `filagent_cyclomatic_complexity_avg` | Dev | Gauge | complexity | Complexité cyclomatique moyenne. Seuil: ≤10 par fonction. |
| `filagent_technical_debt_hours` | Dev | Gauge | hours | Dette technique estimée (SonarQube/radon). Tracking tendance. |
| `filagent_todos_critical_count` | Dev | Gauge | count | TODOs critiques non résolus. Actuel: 3. Cible: 0. |
| `filagent_print_statements_count` | Dev | Gauge | count | Print statements dans le code production. Actuel: 143. Cible: 0. |

### 4.2 Métriques CI/CD

| Indicator Name | Category | Type | Unit | Description & Justification |
|:---|:---|:---|:---|:---|
| `filagent_ci_pipeline_duration_seconds` | Dev | Histogram | seconds | Durée du pipeline CI complet. Cible: <300s. |
| `filagent_ci_pipeline_success_rate` | Dev | Gauge | ratio [0-1] | Taux de succès des pipelines. Cible: ≥0.95. |
| `filagent_deployment_frequency` | Dev | Counter | deployments/day | Fréquence de déploiement. DORA metric. |
| `filagent_lead_time_for_changes_hours` | Dev | Gauge | hours | Temps entre commit et production. DORA metric. |
| `filagent_mean_time_to_recovery_hours` | Dev | Gauge | hours | MTTR après incident. DORA metric. |
| `filagent_change_failure_rate` | Dev | Gauge | ratio [0-1] | Taux d'échec des changements. DORA metric. |

---

## 5. Service Level Objectives (SLOs)

### 5.1 SLOs Système

| SLO Name | Indicator | Target | Window | Error Budget |
|:---|:---|:---|:---|:---|
| **Availability** | `filagent_http_requests_total{status!~"5.."}` / total | ≥99.5% | 30 jours | 3.6 heures/mois |
| **Latency P99** | `histogram_quantile(0.99, htn_execution_duration_seconds)` | ≤5s | 7 jours | N/A |
| **Latency P50** | `histogram_quantile(0.50, htn_execution_duration_seconds)` | ≤1s | 7 jours | N/A |
| **Error Rate** | `htn_tasks_failed_total` / `htn_tasks_completed_total` | ≤5% | 24 heures | 72 minutes/jour |

### 5.2 SLOs HTN Cognitifs

| SLO Name | Indicator | Target | Window | Justification |
|:---|:---|:---|:---|:---|
| **HTN Usage Rate** | `htn_usage_rate` | ≥30% | 7 jours | Adoption minimale pour ROI du HTN planning. |
| **HTN Success Rate** | `htn_success_rate` | ≥95% | 24 heures | Fiabilité critique pour confiance utilisateur. |
| **Parallelization Factor** | `htn_parallelization_factor` | ≥40% | 7 jours | Exploitation des capacités de parallélisation. |
| **Verification Pass Rate** | `htn_verification_pass_rate` | ≥90% | 24 heures | Qualité des plans générés. |
| **Planning Confidence** | `htn_planning_confidence` | ≥0.70 | Temps réel | Seuil minimal pour exécution automatique. |

### 5.3 SLOs Développement

| SLO Name | Indicator | Target | Window | Justification |
|:---|:---|:---|:---|:---|
| **Test Coverage** | `filagent_test_coverage_ratio` | ≥80% | Release | Standard Production-First. |
| **Pipeline Success** | `filagent_ci_pipeline_success_rate` | ≥95% | 7 jours | Friction dev minimale. |
| **Deployment Frequency** | `filagent_deployment_frequency` | ≥1/semaine | 30 jours | Vélocité PME raisonnable. |
| **Lead Time** | `filagent_lead_time_for_changes_hours` | ≤24h | 30 jours | Time-to-market compétitif. |


---

## 6. HTN-Specific Deep Dive

### 6.1 Modèle cognitif HTN et ses métriques

Le Hierarchical Task Network de FilAgent suit un modèle de décomposition récursive :

```
┌──────────────────────────────────────────────────────────────────┐
│                     REQUÊTE UTILISATEUR                          │
│           "Analyse data.csv, génère stats, crée PDF"             │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                    HTN PLANNER (planner.py)                      │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ Strategy Selection: HYBRID                                  │ │
│  │ • Rule-based: Pattern matching → Confiance 0.8              │ │
│  │ • LLM-based: Décomposition intelligente → Confiance 0.9     │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  METRICS POINTS:                                                  │
│  → htn_planning_duration_seconds                                  │
│  → htn_planning_confidence                                        │
│  → htn_decomposition_depth                                        │
│  → htn_method_selection_latency_seconds                           │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                    TASK GRAPH (task_graph.py)                    │
│                                                                   │
│    [read_file_0] ──────► [analyze_data_1] ──────► [generate_2]   │
│         │                       │                       │         │
│    priority:3             priority:3              priority:3      │
│    action:read            action:analyze          action:report   │
│                                                                   │
│  METRICS POINTS:                                                  │
│  → htn_dependency_resolution_time_seconds                         │
│  → htn_tasks_completed_total (par action)                         │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                    EXECUTOR (executor.py)                        │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ Strategy: ADAPTIVE                                          │ │
│  │ • < 3 tasks OR critical → Sequential                        │ │
│  │ • Else → Parallel (ThreadPoolExecutor, max_workers=4)       │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  METRICS POINTS:                                                  │
│  → htn_execution_duration_seconds                                 │
│  → htn_tasks_parallel_total                                       │
│  → htn_work_stealing_operations_total                             │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                    VERIFIER (verifier.py)                        │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ Levels: BASIC → STRICT → PARANOID                           │ │
│  │ • Precondition check                                        │ │
│  │ • Postcondition validation                                  │ │
│  │ • Compliance rules (Loi 25, RGPD)                           │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  METRICS POINTS:                                                  │
│  → htn_verifications_total                                        │
│  → htn_precondition_failures_total                                │
│  → htn_postcondition_violations_total                             │
└──────────────────────────────────────────────────────────────────┘
```

### 6.2 Indicateurs de santé cognitive HTN

| Symptôme | Métrique indicatrice | Seuil d'alerte | Diagnostic probable |
|:---|:---|:---|:---|
| Plans inefficaces | `htn_backtracking_count` > 3/plan | Warning | Heuristiques de décomposition inadaptées |
| Lenteur planification | `htn_planning_duration_seconds` P99 > 2s | Warning | Pattern matching trop coûteux ou LLM lent |
| Faible parallélisation | `htn_parallelization_factor` < 0.3 | Info | Trop de dépendances séquentielles |
| Échecs récurrents | `htn_tasks_failed_total{action="X"}` spike | Critical | Outil défaillant ou préconditions incorrectes |
| Plans trop profonds | `htn_decomposition_depth` > 5 | Warning | Sur-décomposition, simplifier le domaine |
| Cache inefficace | `cache_hit_ratio` < 0.5 | Info | Requêtes trop variées ou TTL trop court |

### 6.3 Corrélations critiques à monitorer

```promql
# Corrélation entre confiance et succès
# Si confiance haute mais succès bas → calibration du modèle nécessaire
correlation(htn_planning_confidence, htn_success_rate)

# Coût du backtracking
# Temps perdu en retours arrière
rate(htn_backtracking_count[5m]) * avg(htn_method_selection_latency_seconds)

# Efficacité du parallélisme
# Gain réel vs théorique
htn_execution_duration_seconds{strategy="parallel"} / 
htn_execution_duration_seconds{strategy="sequential"}
```


---

## 7. Implementation Strategy (OpenTelemetry/Prometheus)

### 7.1 Extension de HTNMetrics existant

Le fichier `planner/metrics.py` doit être étendu avec les nouvelles métriques :

```python
# planner/metrics.py — Extension proposée

from prometheus_client import Counter, Histogram, Gauge, Info

class HTNMetricsExtended(HTNMetrics):
    """Extension avec métriques cognitives avancées"""
    
    def __init__(self, enabled: bool = True):
        super().__init__(enabled=enabled)
        
        if not self.enabled:
            return
        
        # === Métriques Cognitives Avancées ===
        
        self.htn_decomposition_depth = Histogram(
            "htn_decomposition_depth",
            "Depth of task decomposition hierarchy",
            ["strategy"],
            buckets=[1, 2, 3, 4, 5, 6, 7, 8, 10],
        )
        
        self.htn_backtracking_count = Counter(
            "htn_backtracking_count_total",
            "Number of backtracking operations during planning",
            ["strategy", "reason"],
        )
        
        self.htn_method_selection_latency = Histogram(
            "htn_method_selection_latency_seconds",
            "Time to select decomposition method",
            ["strategy"],
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
        )
        
        self.htn_plan_cache_hits = Counter(
            "htn_plan_cache_hits_total",
            "Plan cache hits",
            ["cache_type"],  # exact, fuzzy
        )
        
        self.htn_plan_cache_misses = Counter(
            "htn_plan_cache_misses_total",
            "Plan cache misses",
            ["reason"],  # not_found, expired, invalidated
        )
        
        # === Métriques de Vérification Avancées ===
        
        self.htn_precondition_failures = Counter(
            "htn_precondition_failures_total",
            "Precondition check failures",
            ["task_action", "failure_type"],
        )
        
        self.htn_postcondition_violations = Counter(
            "htn_postcondition_violations_total",
            "Postcondition violations detected",
            ["task_action", "violation_type"],
        )
```

### 7.2 Métriques d'infrastructure (nouveau fichier)

```python
# runtime/metrics.py — Métriques système

from prometheus_client import Counter, Histogram, Gauge
import psutil
import os

class SystemMetrics:
    """Métriques d'infrastructure pour FilAgent"""
    
    def __init__(self):
        self.http_requests = Counter(
            "filagent_http_requests_total",
            "Total HTTP requests",
            ["method", "endpoint", "status_code"],
        )
        
        self.http_latency = Histogram(
            "filagent_http_request_duration_seconds",
            "HTTP request latency",
            ["method", "endpoint"],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10],
        )
        
        self.active_connections = Gauge(
            "filagent_active_connections",
            "Active HTTP connections",
        )
        
        self.memory_usage = Gauge(
            "filagent_memory_usage_bytes",
            "Process memory usage",
            ["type"],  # rss, vms, shared
        )
        
        self.cpu_usage = Gauge(
            "filagent_cpu_usage_ratio",
            "CPU usage ratio",
        )
        
        self.circuit_breaker_state = Gauge(
            "filagent_circuit_breaker_state",
            "Circuit breaker state (0=closed, 1=open, 2=half-open)",
            ["service"],
        )
        
        self.circuit_breaker_trips = Counter(
            "filagent_circuit_breaker_trips_total",
            "Circuit breaker trip count",
            ["service", "reason"],
        )
    
    def update_resource_metrics(self):
        """Mise à jour périodique des métriques ressources"""
        process = psutil.Process(os.getpid())
        mem = process.memory_info()
        
        self.memory_usage.labels(type="rss").set(mem.rss)
        self.memory_usage.labels(type="vms").set(mem.vms)
        self.cpu_usage.set(process.cpu_percent() / 100.0)
```

### 7.3 Middleware FastAPI pour collecte

```python
# runtime/middleware/metrics_middleware.py

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import time
from runtime.metrics import get_system_metrics

class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware de collecte de métriques HTTP"""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        metrics = get_system_metrics()
        
        # Incrémenter connexions actives
        metrics.active_connections.inc()
        
        start_time = time.perf_counter()
        
        try:
            response = await call_next(request)
            
            # Enregistrer métriques
            duration = time.perf_counter() - start_time
            metrics.http_requests.labels(
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code,
            ).inc()
            
            metrics.http_latency.labels(
                method=request.method,
                endpoint=request.url.path,
            ).observe(duration)
            
            return response
            
        finally:
            metrics.active_connections.dec()
```

### 7.4 Configuration Prometheus étendue

```yaml
# config/prometheus.yml — Configuration étendue

global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    environment: production
    service: filagent

rule_files:
  - prometheus_alerts.yml
  - prometheus_recording_rules.yml

scrape_configs:
  - job_name: 'filagent-api'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s  # Plus fréquent pour API

  - job_name: 'filagent-gradio'
    static_configs:
      - targets: ['localhost:7860']
    metrics_path: '/metrics'
    scrape_interval: 30s  # Moins critique

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['localhost:9093']
```

### 7.5 Recording Rules pour SLOs

```yaml
# config/prometheus_recording_rules.yml

groups:
  - name: filagent_slos
    interval: 30s
    rules:
      # SLO: Availability (99.5%)
      - record: filagent:availability:ratio_30d
        expr: |
          sum(rate(filagent_http_requests_total{status_code!~"5.."}[30d])) /
          sum(rate(filagent_http_requests_total[30d]))

      # SLO: HTN Success Rate
      - record: filagent:htn_success_rate:ratio_24h
        expr: |
          sum(rate(htn_tasks_completed_total[24h])) /
          (sum(rate(htn_tasks_completed_total[24h])) + sum(rate(htn_tasks_failed_total[24h])))

      # SLO: Parallelization Factor
      - record: filagent:htn_parallelization:ratio_7d
        expr: |
          sum(rate(htn_tasks_parallel_total[7d])) /
          sum(rate(htn_tasks_completed_total[7d]))

      # Error Budget Remaining (Availability)
      - record: filagent:error_budget:remaining_30d
        expr: |
          1 - ((1 - filagent:availability:ratio_30d) / (1 - 0.995))
```


---

## 8. Architect's Recommendation

### 8.1 Priorités d'implémentation

| Phase | Scope | Effort | Impact | Priorité |
|:---|:---|:---|:---|:---|
| **Phase 1** | Étendre `HTNMetrics` avec métriques cognitives | 2-3 jours | Haut | P0 |
| **Phase 2** | Ajouter `SystemMetrics` + middleware FastAPI | 1-2 jours | Haut | P0 |
| **Phase 3** | Configurer recording rules + dashboards Grafana | 1 jour | Moyen | P1 |
| **Phase 4** | Implémenter circuit breakers + métriques | 2-3 jours | Moyen | P1 |
| **Phase 5** | Intégrer métriques de qualité code (CI) | 1 jour | Faible | P2 |

### 8.2 Dashboard Grafana recommandé

Structure de dashboard en 4 panels :

```
┌─────────────────────────────────────────────────────────────────┐
│                    FilAgent Executive Dashboard                  │
├─────────────────────────────────────────────────────────────────┤
│ ┌──────────────────────┐ ┌──────────────────────┐               │
│ │   SLO Status         │ │   Error Budget       │               │
│ │   ✅ Availability    │ │   ████████░░ 72%     │               │
│ │   ✅ HTN Success     │ │   Burn rate: 0.8x    │               │
│ │   ⚠️ Parallelization │ │                      │               │
│ └──────────────────────┘ └──────────────────────┘               │
├─────────────────────────────────────────────────────────────────┤
│ ┌──────────────────────────────────────────────────────────────┐│
│ │              HTN Planning Performance (24h)                  ││
│ │  [Histogram: planning duration by strategy]                  ││
│ │  [Line: confidence score trend]                              ││
│ └──────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────┤
│ ┌──────────────────────────────────────────────────────────────┐│
│ │              Task Execution (24h)                            ││
│ │  [Stacked: completed vs failed vs skipped by priority]       ││
│ │  [Gauge: parallelization factor]                             ││
│ └──────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────┤
│ ┌──────────────────────────────────────────────────────────────┐│
│ │              Infrastructure Health                           ││
│ │  [Memory/CPU gauges]  [Circuit breaker status]               ││
│ │  [HTTP latency P50/P99]                                      ││
│ └──────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### 8.3 Anti-patterns à éviter

| Anti-pattern | Pourquoi c'est problématique | Solution |
|:---|:---|:---|
| **Cardinality explosion** | Labels avec valeurs unbounded (user_id, request_id) | Utiliser des buckets ou aggregations |
| **Missing labels** | Métriques sans contexte suffisant | Toujours inclure `strategy`, `action`, `status` |
| **Sampling bias** | Ne collecter que les succès | Collecter TOUS les outcomes |
| **Alert fatigue** | Trop d'alertes warning | Seuils calibrés + grouping |
| **SLO sans error budget** | Pas de tolérance définie | Toujours définir le budget d'erreur |

### 8.4 Checklist de validation Production-First

Avant déploiement, valider :

- [ ] **Métriques HTN** : Tous les counters/histogrammes initialisés avec labels
- [ ] **SLOs** : Recording rules testées en staging
- [ ] **Alertes** : Chaque alerte a un runbook associé
- [ ] **Dashboards** : Au moins 1 dashboard par bounded context
- [ ] **Circuit breakers** : Configurés pour chaque dépendance externe
- [ ] **Tests** : Métriques couvertes par tests unitaires
- [ ] **Documentation** : Ce document à jour dans `/docs/`

### 8.5 Recommandation finale

> **L'observabilité n'est pas un nice-to-have — c'est une exigence de production.**

Pour FilAgent, les métriques HTN cognitives sont particulièrement critiques car elles permettent de :
1. **Détecter** les dégradations de qualité de planification avant l'impact utilisateur
2. **Diagnostiquer** les causes racines (heuristiques, LLM, domaine)
3. **Optimiser** le ratio performance/coût (tokens LLM, parallélisation)
4. **Prouver** la conformité aux régulateurs (Loi 25, AI Act via audit trail)

**Investissement recommandé** : 2 semaines développeur pour l'implémentation complète des Phases 1-3.

**ROI attendu** : Réduction de 50% du MTTR (Mean Time To Recovery) et amélioration de 20% du taux de succès HTN grâce à l'identification proactive des problèmes.

---

## Annexe A — Références

- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [Google SRE Book — SLOs](https://sre.google/sre-book/service-level-objectives/)
- [DORA Metrics](https://dora.dev/research/)
- [OpenTelemetry Python SDK](https://opentelemetry.io/docs/instrumentation/python/)
- [FilAgent Architecture — CLAUDE.md](../CLAUDE.md)
- [HTN Planning Theory — Ghallab et al.](https://www.laas.fr/~felix/PDDL+/References.html)

---

## Annexe B — Glossaire

| Terme | Définition |
|:---|:---|
| **HTN** | Hierarchical Task Network — méthode de planification par décomposition hiérarchique |
| **SLO** | Service Level Objective — cible de qualité de service mesurable |
| **SLI** | Service Level Indicator — métrique utilisée pour mesurer un SLO |
| **Error Budget** | Tolérance d'erreur acceptable avant violation de SLO |
| **Circuit Breaker** | Pattern de résilience qui coupe les appels à un service défaillant |
| **Backtracking** | Retour arrière dans la planification quand un chemin échoue |
| **Work Stealing** | Technique de load balancing où un worker inactif prend du travail à un autre |
| **Cardinality** | Nombre de combinaisons uniques de labels d'une métrique |

---

*Document généré pour FilAgent v2.0.0 — Conformité Production-First*
