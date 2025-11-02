# 📜 Scripts d'Automatisation Prometheus

**Scripts pour automatiser le monitoring Prometheus de FilAgent**

---

## 📋 Scripts Disponibles

### 1. Installation

#### `install_prometheus_monitoring.sh`
**Installation automatique complète du monitoring Prometheus**

```bash
# Installation de base (prometheus-client uniquement)
./scripts/install_prometheus_monitoring.sh

# Installation complète (incluant Prometheus)
./scripts/install_prometheus_monitoring.sh --install-prometheus
```

**Fait:**
- ✅ Installe `prometheus-client` (Python)
- ✅ Vérifie les fichiers de configuration
- ✅ Crée les répertoires nécessaires
- ✅ Optionnellement installe Prometheus

---

### 2. Tests

#### `test_metrics.py`
**Test l'endpoint `/metrics` du serveur FilAgent**

```bash
python3 scripts/test_metrics.py
```

**Vérifie:**
- ✅ prometheus-client installé
- ✅ Endpoint `/metrics` accessible
- ✅ Métriques HTN présentes

---

#### `validate_prometheus_setup.py`
**Validation complète de l'installation**

```bash
# Validation de base
python3 scripts/validate_prometheus_setup.py

# Avec vérification Prometheus
python3 scripts/validate_prometheus_setup.py --check-prometheus

# Avec vérification des alertes
python3 scripts/validate_prometheus_setup.py --check-alerts

# Tout vérifier
python3 scripts/validate_prometheus_setup.py --check-prometheus --check-alerts
```

**Vérifie:**
- ✅ Dépendances Python
- ✅ Fichiers de configuration
- ✅ Module metrics
- ✅ Serveur FilAgent
- ✅ Endpoint `/metrics`
- ✅ Prometheus (optionnel)
- ✅ Règles d'alertes (optionnel)

---

### 3. Génération de Métriques

#### `generate_test_metrics.py`
**Génère des métriques HTN de test**

```bash
# Générer 10 requêtes
python3 scripts/generate_test_metrics.py

# Générer 20 requêtes avec délai de 1s
python3 scripts/generate_test_metrics.py --count 20 --delay 1.0

# Mode continu (Ctrl+C pour arrêter)
python3 scripts/generate_test_metrics.py --continuous
```

**Options:**
- `--url`: URL du serveur (défaut: `http://localhost:8000`)
- `--count`: Nombre de requêtes (défaut: `10`)
- `--delay`: Délai entre requêtes en secondes (défaut: `2.0`)
- `--continuous`: Mode continu

**Utile pour:**
- ✅ Tester le dashboard Grafana
- ✅ Vérifier les alertes Prometheus
- ✅ Valider la collecte de métriques

---

### 4. Démarrage

#### `start_prometheus.sh`
**Démarre Prometheus avec la configuration FilAgent**

```bash
./scripts/start_prometheus.sh
```

**Fait:**
- ✅ Vérifie l'installation de Prometheus
- ✅ Crée le répertoire de données
- ✅ Démarre Prometheus avec la config FilAgent

**Interface:** http://localhost:9090

---

## 🚀 Workflow Recommandé

### 1. Installation Initiale

```bash
# 1. Installer les dépendances
./scripts/install_prometheus_monitoring.sh

# 2. Valider l'installation
python3 scripts/validate_prometheus_setup.py
```

### 2. Démarrage

```bash
# 1. Démarrer FilAgent (terminal 1)
python3 -m runtime.server

# 2. Démarrer Prometheus (terminal 2)
./scripts/start_prometheus.sh
```

### 3. Génération de Métriques

```bash
# Générer des métriques de test
python3 scripts/generate_test_metrics.py --count 20
```

### 4. Vérification

```bash
# Tester l'endpoint métriques
python3 scripts/test_metrics.py

# Valider l'installation complète
python3 scripts/validate_prometheus_setup.py --check-prometheus
```

---

## 📊 Structure des Scripts

```
scripts/
├── install_prometheus_monitoring.sh    # Installation automatique
├── test_metrics.py                    # Test endpoint /metrics
├── validate_prometheus_setup.py      # Validation complète
├── generate_test_metrics.py           # Génération métriques test
└── start_prometheus.sh                # Démarrage Prometheus
```

---

## ✅ Checklist d'Utilisation

- [ ] Installation: `./scripts/install_prometheus_monitoring.sh`
- [ ] Validation: `python3 scripts/validate_prometheus_setup.py`
- [ ] Démarrage FilAgent: `python3 -m runtime.server`
- [ ] Démarrage Prometheus: `./scripts/start_prometheus.sh`
- [ ] Test métriques: `python3 scripts/test_metrics.py`
- [ ] Génération métriques: `python3 scripts/generate_test_metrics.py`
- [ ] Vérification Prometheus: http://localhost:9090

---

## 💡 Conseils

### Débogage

Si un script échoue:
1. Vérifier les permissions: `chmod +x scripts/*.sh`
2. Vérifier Python: `python3 --version`
3. Vérifier les dépendances: `pip list | grep prometheus`
4. Vérifier les logs: Les scripts affichent les erreurs détaillées

### Performance

- Pour générer beaucoup de métriques rapidement: `--delay 0.5`
- Pour tester en continu: `--continuous`
- Pour valider sans métriques: Attendez après le démarrage du serveur

---

**Status**: ✅ **Scripts Prêts pour Utilisation**

