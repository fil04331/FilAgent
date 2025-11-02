# 🚀 Guide de Démarrage Rapide Prometheus

**Guide rapide pour configurer le monitoring HTN de FilAgent**

---

## ✅ Étapes Complétées

Les tâches suivantes ont été automatisées:

1. ✅ **Installation prometheus-client**
   - Ajouté à `requirements.txt`
   - Peut être installé avec: `pip install prometheus-client`

2. ✅ **Script de test des métriques**
   - `scripts/test_metrics.py` - Teste l'endpoint `/metrics`
   - Usage: `python3 scripts/test_metrics.py`

3. ✅ **Script de démarrage Prometheus**
   - `scripts/start_prometheus.sh` - Démarre Prometheus avec la config FilAgent
   - Usage: `./scripts/start_prometheus.sh`

4. ✅ **Dashboard Grafana pré-configuré**
   - `grafana/dashboard_htn.json` - Dashboard prêt à importer
   - Import dans Grafana: Dashboards → Import → Upload JSON

---

## 🎯 Démarrage Rapide

### 1. Installer prometheus-client

```bash
# Option 1: Via pip
pip install prometheus-client>=0.19.0

# Option 2: Via requirements.txt
pip install -r requirements.txt
```

### 2. Démarrer FilAgent

```bash
cd /Volumes/DevSSD/FilAgent
python3 -m runtime.server
```

Ou via uvicorn:
```bash
uvicorn runtime.server:app --host 0.0.0.0 --port 8000
```

### 3. Tester l'endpoint métriques

```bash
# Option 1: Script de test
python3 scripts/test_metrics.py

# Option 2: Curl manuel
curl http://localhost:8000/metrics | grep htn_
```

### 4. Démarrer Prometheus

```bash
# Option 1: Script automatique
./scripts/start_prometheus.sh

# Option 2: Manuel
prometheus --config.file=config/prometheus.yml \
           --storage.tsdb.path=./prometheus_data
```

**Accéder à Prometheus**: http://localhost:9090

### 5. Importer Dashboard Grafana

1. Ouvrir Grafana: http://localhost:3000
2. Aller à: Dashboards → Import
3. Upload: `grafana/dashboard_htn.json`
4. Sélectionner la datasource Prometheus
5. Cliquer sur "Import"

---

## 📊 Vérification

### Tester les métriques

```bash
# Vérifier que l'endpoint répond
curl http://localhost:8000/metrics

# Chercher les métriques HTN
curl http://localhost:8000/metrics | grep htn_requests_total

# Tester une requête PromQL dans Prometheus
# Dans http://localhost:9090/graph:
htn_usage_rate
```

### Déclencher des métriques HTN

Pour générer des métriques, envoyez une requête complexe au serveur:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Lis data.csv, analyse les données, crée un rapport"}
    ]
  }'
```

Cette requête devrait déclencher HTN et générer des métriques.

---

## 🔍 Dépannage

### Problème: Endpoint `/metrics` retourne 503

**Solution**: Installer prometheus-client
```bash
pip install prometheus-client
```

### Problème: Prometheus ne trouve pas les métriques

**Vérifications**:
1. FilAgent tourne sur le bon port (par défaut: 8000)
2. Endpoint `/metrics` accessible: `curl http://localhost:8000/metrics`
3. Configuration Prometheus pointe vers le bon target

### Problème: Aucune métrique HTN visible

**Raison**: Les métriques ne sont générées que lorsque HTN est utilisé.
- Les requêtes simples n'utilisent pas HTN
- Seules les requêtes complexes (multi-étapes) déclenchent HTN
- Envoyez une requête complexe pour générer des métriques

---

## 📚 Documentation Complète

Pour plus de détails, voir:
- `docs/PROMETHEUS_SETUP.md` - Configuration complète
- `docs/PROMETHEUS_DASHBOARD.md` - Guide dashboard Grafana
- `config/prometheus.yml` - Configuration Prometheus
- `config/prometheus_alerts.yml` - Règles d'alertes

---

## ✅ Checklist

- [ ] prometheus-client installé
- [ ] FilAgent démarré et accessible
- [ ] Endpoint `/metrics` répond
- [ ] Prometheus démarré et scrape les métriques
- [ ] Dashboard Grafana importé
- [ ] Requêtes HTN testées (métriques générées)

---

**Status**: ✅ **Prêt pour utilisation**

