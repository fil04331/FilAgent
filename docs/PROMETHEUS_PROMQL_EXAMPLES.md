# 📊 Exemples de Requêtes PromQL pour HTN

**Guide des requêtes PromQL pour monitorer les métriques HTN de FilAgent**

---

## 🎯 Métriques de Base

### Planning

#### Requêtes HTN totales

```promql
# Total de requêtes HTN
htn_requests_total

# Par stratégie
htn_requests_total{strategy="hybrid"}
htn_requests_total{strategy="rule_based"}
htn_requests_total{strategy="llm_based"}

# Par statut
htn_requests_total{status="success"}
htn_requests_total{status="failure"}

# Taux de requêtes (par seconde)
rate(htn_requests_total[5m])
```

#### Durée de planification

```promql
# Durée moyenne de planification (secondes)
rate(htn_planning_duration_seconds_sum[5m]) / rate(htn_planning_duration_seconds_count[5m])

# Par stratégie
rate(htn_planning_duration_seconds_sum{strategy="hybrid"}[5m]) / 
rate(htn_planning_duration_seconds_count{strategy="hybrid"}[5m])

# P95 (95ème percentile)
histogram_quantile(0.95, rate(htn_planning_duration_seconds_bucket[5m]))

# P99 (99ème percentile)
histogram_quantile(0.99, rate(htn_planning_duration_seconds_bucket[5m]))
```

#### Confiance de planification

```promql
# Confiance moyenne
avg(htn_planning_confidence)

# Par stratégie
avg(htn_planning_confidence{strategy="hybrid"})

# Minimum
min(htn_planning_confidence)

# Maximum
max(htn_planning_confidence)
```

### Execution

#### Durée d'exécution

```promql
# Durée moyenne d'exécution (secondes)
rate(htn_execution_duration_seconds_sum[5m]) / rate(htn_execution_duration_seconds_count[5m])

# Par stratégie
rate(htn_execution_duration_seconds_sum{strategy="parallel"}[5m]) / 
rate(htn_execution_duration_seconds_count{strategy="parallel"}[5m])

# P95
histogram_quantile(0.95, rate(htn_execution_duration_seconds_bucket[5m]))

# P99
histogram_quantile(0.99, rate(htn_execution_duration_seconds_bucket[5m]))
```

#### Tâches complétées/échouées

```promql
# Tâches complétées (taux par seconde)
rate(htn_tasks_completed_total[5m])

# Par priorité
rate(htn_tasks_completed_total{priority="critical"}[5m])
rate(htn_tasks_completed_total{priority="high"}[5m])
rate(htn_tasks_completed_total{priority="normal"}[5m])

# Par action
rate(htn_tasks_completed_total{action="read_file"}[5m])
rate(htn_tasks_completed_total{action="analyze_data"}[5m])

# Tâches échouées
rate(htn_tasks_failed_total[5m])

# Par type d'erreur
rate(htn_tasks_failed_total{error_type="TimeoutError"}[5m])
rate(htn_tasks_failed_total{error_type="ExecutionError"}[5m])
```

#### Taux de succès

```promql
# Taux de succès global
rate(htn_tasks_completed_total[5m]) / 
(rate(htn_tasks_completed_total[5m]) + rate(htn_tasks_failed_total[5m]))

# Par priorité
rate(htn_tasks_completed_total{priority="critical"}[5m]) / 
(rate(htn_tasks_completed_total{priority="critical"}[5m]) + 
 rate(htn_tasks_failed_total{priority="critical"}[5m]))

# Par stratégie d'exécution
rate(htn_tasks_completed_total{strategy="parallel"}[5m]) / 
(rate(htn_tasks_completed_total{strategy="parallel"}[5m]) + 
 rate(htn_tasks_failed_total{strategy="parallel"}[5m]))
```

#### Parallélisation

```promql
# Tâches exécutées en parallèle (taux)
rate(htn_tasks_parallel_total[5m])

# Par stratégie
rate(htn_tasks_parallel_total{strategy="parallel"}[5m])

# Tâches en cours
htn_tasks_in_progress

# Par stratégie
htn_tasks_in_progress{strategy="adaptive"}
```

### Verification

#### Vérifications

```promql
# Vérifications totales (taux)
rate(htn_verifications_total[5m])

# Par niveau
rate(htn_verifications_total{level="strict"}[5m])
rate(htn_verifications_total{level="basic"}[5m])

# Par statut
rate(htn_verifications_total{status="passed"}[5m])
rate(htn_verifications_total{status="failed"}[5m])

# Taux de réussite
rate(htn_verifications_total{status="passed"}[5m]) / 
rate(htn_verifications_total[5m])

# Par niveau
rate(htn_verifications_total{level="strict", status="passed"}[5m]) / 
rate(htn_verifications_total{level="strict"}[5m])
```

---

## 📊 Métriques Calculées (KPIs)

### Adoption HTN

```promql
# Si la métrique calculée existe
htn_usage_rate

# Sinon, calculer manuellement (nécessite métrique agent_requests_total)
rate(htn_requests_total[5m]) / 
(rate(htn_requests_total[5m]) + rate(agent_requests_total[5m]))
```

### Performance

```promql
# Durée moyenne d'exécution
rate(htn_execution_duration_seconds_sum[5m]) / rate(htn_execution_duration_seconds_count[5m])

# Si < 5 secondes = OK
```

### Parallélisation

```promql
# Si la métrique calculée existe
htn_parallelization_factor

# Sinon, calculer manuellement
sum(rate(htn_tasks_parallel_total[5m])) / 
(sum(rate(htn_tasks_completed_total[5m])) + sum(rate(htn_tasks_failed_total[5m])))
```

### Fiabilité

```promql
# Si la métrique calculée existe
htn_success_rate

# Sinon, calculer manuellement
sum(rate(htn_tasks_completed_total[5m])) / 
(sum(rate(htn_tasks_completed_total[5m])) + sum(rate(htn_tasks_failed_total[5m])))
```

### Vérification

```promql
# Taux de réussite des vérifications
rate(htn_verifications_total{status="passed"}[5m]) / 
rate(htn_verifications_total[5m])

# Si >= 0.90 (90%) = OK
```

---

## 📈 Requêtes Avancées

### Taux d'échec par priorité

```promql
# Échecs de tâches critiques
rate(htn_tasks_failed_total{priority="critical"}[5m])

# Pourcentage d'échecs critiques
rate(htn_tasks_failed_total{priority="critical"}[5m]) / 
(rate(htn_tasks_completed_total{priority="critical"}[5m]) + 
 rate(htn_tasks_failed_total{priority="critical"}[5m]))
```

### Performance par stratégie

```promql
# Comparer les stratégies d'exécution
rate(htn_execution_duration_seconds_sum{strategy="sequential"}[5m]) / 
rate(htn_execution_duration_seconds_count{strategy="sequential"}[5m])

rate(htn_execution_duration_seconds_sum{strategy="parallel"}[5m]) / 
rate(htn_execution_duration_seconds_count{strategy="parallel"}[5m])

rate(htn_execution_duration_seconds_sum{strategy="adaptive"}[5m]) / 
rate(htn_execution_duration_seconds_count{strategy="adaptive"}[5m])
```

### Distribution des tâches

```promql
# Top 10 des actions les plus utilisées
topk(10, sum by (action) (rate(htn_tasks_completed_total[5m])))

# Top 5 des actions avec le plus d'échecs
topk(5, sum by (action) (rate(htn_tasks_failed_total[5m])))
```

### Erreurs récentes

```promql
# Erreurs dans les 5 dernières minutes
increase(htn_tasks_failed_total[5m])

# Par type d'erreur
sum by (error_type) (increase(htn_tasks_failed_total[5m]))

# Erreurs critiques récentes
increase(htn_tasks_failed_total{priority="critical"}[5m])
```

---

## 🚨 Requêtes pour Alertes

### Alertes Configurées (voir `config/prometheus_alerts.yml`)

```promql
# Usage rate trop bas
htn_usage_rate < 0.30

# Performance dégradée (> 5s)
rate(htn_execution_duration_seconds_sum[5m]) / rate(htn_execution_duration_seconds_count[5m]) > 5.0

# Taux de succès trop bas (< 95%)
htn_success_rate < 0.95

# Taux de succès critique (< 90%)
htn_success_rate < 0.90

# Tâche critique échouée
increase(htn_tasks_failed_total{priority="critical"}[5m]) > 0

# Taux d'échec élevé (> 10%)
rate(htn_tasks_failed_total[5m]) / 
(rate(htn_tasks_completed_total[5m]) + rate(htn_tasks_failed_total[5m])) > 0.10

# Parallélisation trop basse (< 40%)
htn_parallelization_factor < 0.40

# Timeout d'exécution (> 5 minutes)
htn_execution_duration_seconds > 300

# Taux de validation trop bas (< 90%)
rate(htn_verifications_total{status="passed"}[5m]) / 
rate(htn_verifications_total[5m]) < 0.90
```

---

## 📊 Exemples pour Dashboards Grafana

### Panneau: Adoption HTN

```promql
htn_usage_rate
```

### Panneau: Performance (graphique temps)

```promql
rate(htn_execution_duration_seconds_sum[5m]) / rate(htn_execution_duration_seconds_count[5m])
```

### Panneau: Taux de Succès

```promql
htn_success_rate
```

### Panneau: Parallélisation

```promql
htn_parallelization_factor
```

### Panneau: Tâches par Priorité (bar chart)

```promql
sum by (priority) (rate(htn_tasks_completed_total[5m]))
```

### Panneau: Erreurs par Type (pie chart)

```promql
sum by (error_type) (rate(htn_tasks_failed_total[5m]))
```

### Panneau: Requêtes par Stratégie (stat)

```promql
sum by (strategy) (rate(htn_requests_total[5m]))
```

---

## 💡 Conseils d'Utilisation

### Intervalle de Temps

- **Court terme (détection rapide)**: `[1m]` ou `[5m]`
- **Moyen terme (moyennes)**: `[15m]` ou `[30m]`
- **Long terme (tendances)**: `[1h]` ou `[6h]`

### Fonctions Utiles

- `rate()`: Taux par seconde
- `increase()`: Augmentation totale sur la période
- `sum()`: Somme des valeurs
- `avg()`: Moyenne
- `min()` / `max()`: Minimum / Maximum
- `histogram_quantile()`: Percentiles (P95, P99)
- `topk()`: Top K valeurs

### Labels pour Filtrage

- `strategy`: Stratégie de planification/exécution
- `priority`: Priorité de la tâche
- `action`: Action de la tâche
- `status`: Statut (success/failure, passed/failed)
- `level`: Niveau de vérification
- `error_type`: Type d'erreur

---

## 📚 Ressources

- [PromQL Documentation](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [PromQL Functions](https://prometheus.io/docs/prometheus/latest/querying/functions/)
- [PromQL Operators](https://prometheus.io/docs/prometheus/latest/querying/operators/)

---

**Status**: ✅ **Prêt pour utilisation**

