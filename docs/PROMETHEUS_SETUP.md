# 📊 Configuration Prometheus pour Monitoring HTN

**Date**: 2025-11-02  
**Version**: 1.0.0  
**Status**: ✅ **Prêt pour déploiement**

---

## 🎯 Vue d'ensemble

Configuration Prometheus complète pour monitorer les métriques HTN de FilAgent selon les KPIs définis dans `CLAUDE.md`.

### Métriques Monitorées

1. **Adoption HTN** (`htn_usage_rate`)
   - Target: > 30%
   - Formule: `htn_requests / total_requests`

2. **Performance** (`htn_execution_duration_seconds`)
   - Target: < 5000ms (5 secondes)
   - Formule: Durée moyenne d'exécution

3. **Parallélisation** (`htn_parallelization_factor`)
   - Target: > 40%
   - Formule: `tasks_parallel / total_tasks`

4. **Fiabilité** (`htn_success_rate`)
   - Target: > 95%
   - Formule: `successful_plans / total_plans`

5. **Vérification** (`htn_verification_pass_rate`)
   - Target: > 90%
   - Formule: `verified_ok / verified_total`

---

## 📦 Installation

### 1. Installer Prometheus

```bash
# macOS (Homebrew)
brew install prometheus

# Linux (apt)
sudo apt-get install prometheus

# Ou télécharger depuis https://prometheus.io/download/
```

### 2. Installer prometheus-client (Python)

```bash
# Déjà dans requirements.txt
pip install prometheus-client>=0.19.0
```

### 3. Vérifier l'installation

```bash
# Vérifier Prometheus
prometheus --version

# Vérifier prometheus-client
python3 -c "import prometheus_client; print('✓ OK')"
```

---

## 🔧 Configuration

### 1. Fichiers de Configuration

Trois fichiers ont été créés :

```
config/
├── prometheus.yml          # Configuration principale Prometheus
└── prometheus_alerts.yml   # Règles d'alertes
```

### 2. Configuration Prometheus (`config/prometheus.yml`)

```yaml
scrape_configs:
  - job_name: 'filagent-htn'
    static_configs:
      - targets: ['localhost:8000']  # Adapter selon votre config
```

**Important**: Modifier `targets` selon votre configuration :
- Si FilAgent tourne sur un autre port : `localhost:8001`
- Si déployé en réseau : `192.168.1.100:8000`

### 3. Exposer les Métriques

L'endpoint `/metrics` a été ajouté au serveur FastAPI :
```bash
# Test local
curl http://localhost:8000/metrics
```

---

## 🚀 Démarrage

### 1. Démarrer FilAgent avec Métriques

```bash
# Démarrer le serveur FilAgent
cd /Volumes/DevSSD/FilAgent
python3 -m runtime.server

# Ou via uvicorn
uvicorn runtime.server:app --host 0.0.0.0 --port 8000
```

### 2. Démarrer Prometheus

```bash
# Avec configuration personnalisée
prometheus --config.file=config/prometheus.yml \
           --storage.tsdb.path=./prometheus_data \
           --web.console.libraries=/usr/share/prometheus/console_libraries \
           --web.console.templates=/usr/share/prometheus/consoles

# Ou chemin complet
prometheus --config.file=/Volumes/DevSSD/FilAgent/config/prometheus.yml
```

### 3. Accéder à l'Interface

- **Prometheus**: http://localhost:9090
- **FilAgent Metrics**: http://localhost:8000/metrics
- **FilAgent API Docs**: http://localhost:8000/docs

---

## 📈 Métriques Disponibles

### Métriques Planning

```promql
# Requêtes HTN totales
htn_requests_total{strategy="hybrid", status="success"}

# Durée de planification
rate(htn_planning_duration_seconds_sum[5m]) / rate(htn_planning_duration_seconds_count[5m])

# Confiance de planification
htn_planning_confidence{strategy="hybrid"}
```

### Métriques Execution

```promql
# Durée d'exécution
rate(htn_execution_duration_seconds_sum[5m]) / rate(htn_execution_duration_seconds_count[5m])

# Tâches complétées
rate(htn_tasks_completed_total[5m])

# Tâches échouées
rate(htn_tasks_failed_total[5m])

# Taux de succès
rate(htn_tasks_completed_total[5m]) / (rate(htn_tasks_completed_total[5m]) + rate(htn_tasks_failed_total[5m]))
```

### Métriques Verification

```promql
# Vérifications totales
rate(htn_verifications_total[5m])

# Taux de réussite
rate(htn_verifications_total{status="passed"}[5m]) / rate(htn_verifications_total[5m])
```

### Métriques Calculées

```promql
# Taux d'usage HTN
htn_usage_rate

# Taux de succès global
htn_success_rate

# Facteur de parallélisation
htn_parallelization_factor
```

---

## 🚨 Alertes Configurées

Les règles d'alertes sont définies dans `config/prometheus_alerts.yml` :

### Alertes Critiques

1. **HTNCriticalTaskFailed**
   - Condition: Tâche critique échouée
   - Severity: `critical`
   - Action: Investigation immédiate

2. **HTNSuccessRateCritical**
   - Condition: Taux de succès < 90%
   - Severity: `critical`
   - Action: Action immédiate requise

### Alertes Warnings

1. **HTNUsageRateLow**
   - Condition: Usage rate < 30%
   - Severity: `warning`
   - Action: Améliorer détection requêtes complexes

2. **HTNPerformanceDegraded**
   - Condition: Durée moyenne > 5s
   - Severity: `warning`
   - Action: Vérifier goulots d'étranglement

3. **HTNSuccessRateLow**
   - Condition: Taux de succès < 95%
   - Severity: `warning`
   - Action: Investigation nécessaire

4. **HTNFailureRateHigh**
   - Condition: Taux d'échec > 10%
   - Severity: `warning`
   - Action: Analyser causes d'échec

5. **HTNVerificationPassRateLow**
   - Condition: Taux de validation < 90%
   - Severity: `warning`
   - Action: Revoir vérifications

### Alertes Info

1. **HTNParallelizationLow**
   - Condition: Parallélisation < 40%
   - Severity: `info`
   - Action: Optimisation possible

2. **HTNPlanningConfidenceLow**
   - Condition: Confiance < 60%
   - Severity: `info`
   - Action: Considérer raffinement

---

## 🔗 Intégration avec Alertmanager (Optionnel)

### Configuration Alertmanager

```yaml
# config/alertmanager.yml
route:
  receiver: 'default'
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h

receivers:
  - name: 'default'
    email_configs:
      - to: 'admin@example.com'
        from: 'prometheus@filagent.local'
        smarthost: 'smtp.example.com:587'
        auth_username: 'prometheus'
        auth_password: '<YOUR_PASSWORD>'
```

### Démarrage Alertmanager

```bash
alertmanager --config.file=config/alertmanager.yml
```

### Mise à jour Prometheus

```yaml
# Dans config/prometheus.yml
alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - 'localhost:9093'  # Alertmanager
```

---

## 📊 Dashboards Grafana (Optionnel)

### Exemple de Dashboard

Créer un dashboard Grafana avec les métriques suivantes :

1. **Panneau: Adoption HTN**
   ```
   Query: htn_usage_rate
   Visualization: Gauge (0-1)
   ```

2. **Panneau: Performance**
   ```
   Query: rate(htn_execution_duration_seconds_sum[5m]) / rate(htn_execution_duration_seconds_count[5m])
   Visualization: Graph
   Unit: seconds
   ```

3. **Panneau: Taux de Succès**
   ```
   Query: htn_success_rate
   Visualization: Gauge (0-1)
   ```

4. **Panneau: Tâches par Priorité**
   ```
   Query: rate(htn_tasks_completed_total[5m])
   Visualization: Bar chart
   Group by: priority
   ```

### Configuration Grafana

```yaml
# Ajouter Prometheus comme source de données
Datasource:
  Type: Prometheus
  URL: http://localhost:9090
  Access: Server (default)
```

---

## 🧪 Test de Validation

### 1. Vérifier les Métriques

```bash
# Tester endpoint métriques
curl http://localhost:8000/metrics | grep htn_

# Devrait retourner les métriques HTN
```

### 2. Tester Prometheus

```bash
# Requête PromQL test
curl 'http://localhost:9090/api/v1/query?query=htn_requests_total'
```

### 3. Déclencher des Alertes (Test)

Pour tester les alertes, vous pouvez :
- Simuler des échecs de tâches critiques
- Réduire artificiellement le taux de succès
- Dégradé les performances

---

## 📝 Notes d'Intégration

### Activer les Métriques dans le Code

Les métriques sont automatiquement collectées si `prometheus-client` est installé.

Pour activer explicitement :

```python
from planner.metrics import get_metrics

# Dans planner.py
metrics = get_metrics(enabled=True)
metrics.record_planning(...)

# Dans executor.py
metrics.record_execution(...)

# Dans verifier.py
metrics.record_verification(...)
```

### Mode sans Prometheus

Si `prometheus-client` n'est pas installé, les métriques utilisent des stubs et n'affectent pas le fonctionnement.

---

## 🔍 Dépannage

### Problème: Métriques non exposées

**Symptôme**: `/metrics` retourne erreur 503

**Solution**:
```bash
pip install prometheus-client>=0.19.0
```

### Problème: Prometheus ne scrap pas

**Symptôme**: Pas de métriques dans Prometheus

**Vérifications**:
1. FilAgent tourne sur le bon port
2. Endpoint `/metrics` accessible
3. Configuration `prometheus.yml` correcte

```bash
# Test endpoint
curl http://localhost:8000/metrics

# Vérifier logs Prometheus
prometheus --config.file=config/prometheus.yml --log.level=debug
```

### Problème: Alertes ne se déclenchent pas

**Vérifications**:
1. Règles chargées dans Prometheus
2. Conditions d'alerte remplies
3. Alertmanager configuré (si utilisé)

---

## 📚 Références

- [Prometheus Documentation](https://prometheus.io/docs/)
- [prometheus-client Python](https://github.com/prometheus/client_python)
- [PromQL Query Language](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Grafana Dashboards](https://grafana.com/docs/grafana/latest/dashboards/)

---

## ✅ Checklist de Déploiement

- [ ] Prometheus installé
- [ ] prometheus-client installé (`pip install prometheus-client`)
- [ ] Configuration `prometheus.yml` adaptée (port/targets)
- [ ] Endpoint `/metrics` accessible
- [ ] Prometheus démarre sans erreurs
- [ ] Métriques visibles dans Prometheus UI
- [ ] Alertes configurées (optionnel)
- [ ] Alertmanager configuré (optionnel)
- [ ] Dashboard Grafana créé (optionnel)

---

**Status**: ✅ **Configuration Prête - Attendre Intégration Code**

**Prochaine étape**: Intégrer les métriques dans `planner.py`, `executor.py`, `verifier.py`

