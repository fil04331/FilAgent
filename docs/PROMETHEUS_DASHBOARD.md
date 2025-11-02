# 📊 Dashboard Prometheus/Grafana pour HTN

**Date**: 2025-11-02  
**Version**: 1.0.0  

---

## 🎯 Vue d'ensemble

Guide pour créer un dashboard Grafana complet pour monitorer les métriques HTN de FilAgent.

---

## 📈 Métriques Disponibles

### Planning

```promql
# Requêtes HTN totales
htn_requests_total

# Par stratégie
htn_requests_total{strategy="hybrid"}
htn_requests_total{strategy="rule_based"}
htn_requests_total{strategy="llm_based"}

# Durée moyenne de planification
rate(htn_planning_duration_seconds_sum[5m]) / rate(htn_planning_duration_seconds_count[5m])

# Confiance moyenne
avg(htn_planning_confidence)
```

### Execution

```promql
# Durée moyenne d'exécution
rate(htn_execution_duration_seconds_sum[5m]) / rate(htn_execution_duration_seconds_count[5m])

# Tâches complétées/échouées par priorité
rate(htn_tasks_completed_total[5m])
rate(htn_tasks_failed_total[5m])

# Taux de succès
rate(htn_tasks_completed_total[5m]) / (rate(htn_tasks_completed_total[5m]) + rate(htn_tasks_failed_total[5m]))

# Tâches en cours
htn_tasks_in_progress
```

### Verification

```promql
# Vérifications totales
rate(htn_verifications_total[5m])

# Taux de réussite
rate(htn_verifications_total{status="passed"}[5m]) / rate(htn_verifications_total[5m])
```

### Métriques Calculées

```promql
# Taux d'usage HTN (calculé par Agent)
htn_usage_rate

# Taux de succès global
htn_success_rate

# Facteur de parallélisation
htn_parallelization_factor
```

---

## 📊 Exemple de Dashboard Grafana

### Panneau 1: Adoption HTN

**Type**: Gauge  
**Query**: `htn_usage_rate`  
**Min/Max**: 0, 1  
**Thresholds**:
- Red: < 0.30
- Yellow: 0.30-0.40
- Green: > 0.40

### Panneau 2: Performance (Durée d'exécution)

**Type**: Graph  
**Query**: `rate(htn_execution_duration_seconds_sum[5m]) / rate(htn_execution_duration_seconds_count[5m])`  
**Unit**: seconds  
**Y-axis**: 0, 10  
**Thresholds**:
- Warning: > 5.0
- Critical: > 10.0

### Panneau 3: Taux de Succès

**Type**: Gauge  
**Query**: `htn_success_rate`  
**Min/Max**: 0, 1  
**Thresholds**:
- Red: < 0.95
- Yellow: 0.95-0.98
- Green: > 0.98

### Panneau 4: Parallélisation

**Type**: Gauge  
**Query**: `htn_parallelization_factor`  
**Min/Max**: 0, 1  
**Thresholds**:
- Red: < 0.40
- Yellow: 0.40-0.50
- Green: > 0.50

### Panneau 5: Tâches par Priorité

**Type**: Bar chart  
**Query**: `rate(htn_tasks_completed_total[5m])`  
**Group by**: `priority`  
**Legend**: `{{priority}}`

### Panneau 6: Erreurs par Type

**Type**: Pie chart  
**Query**: `rate(htn_tasks_failed_total[5m])`  
**Group by**: `error_type`

---

## 🔍 Requêtes PromQL Avancées

### Taux d'Usage HTN (si calculé)

```promql
# Sinon calculer manuellement
rate(htn_requests_total[5m]) / 
(rate(htn_requests_total[5m]) + rate(agent_requests_total[5m]))
```

### Performance P95

```promql
histogram_quantile(0.95, rate(htn_execution_duration_seconds_bucket[5m]))
```

### Taux de Succès par Stratégie

```promql
rate(htn_tasks_completed_total{strategy="parallel"}[5m]) / 
(rate(htn_tasks_completed_total{strategy="parallel"}[5m]) + 
 rate(htn_tasks_failed_total{strategy="parallel"}[5m]))
```

---

## ✅ Checklist Dashboard

- [ ] Panneau Adoption HTN (Gauge)
- [ ] Panneau Performance (Graph)
- [ ] Panneau Taux de Succès (Gauge)
- [ ] Panneau Parallélisation (Gauge)
- [ ] Panneau Tâches par Priorité (Bar)
- [ ] Panneau Erreurs par Type (Pie)
- [ ] Panneau Durée Planning/Execution (Time series)
- [ ] Panneau Stratégies Utilisées (Stat)

---

**Status**: ✅ **Configuration Prête - Attendre Validation Tests**

