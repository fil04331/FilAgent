# **LLM-Agent : Gouvernance & Traçabilité**

![Coverage](https://img.shields.io/badge/coverage-0%25-red)
![Tests](https://img.shields.io/badge/tests-no__data-lightgrey)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-blue)
![HTN Planning](https://img.shields.io/badge/HTN-enabled-brightgreen)
![Compliance](https://img.shields.io/badge/compliance-Loi%2025%20%7C%20GDPR%20%7C%20AI%20Act-blue)

Ce projet vise à développer un agent basé sur un Grand Modèle de Langage (LLM) avec un accent fondamental sur la gouvernance, la traçabilité légale, la sécurité et la reproductibilité des décisions. L'architecture est conçue pour être exécutable localement tout en respectant des normes de conformité strictes (Loi 25 du Québec, AI Act de l'UE, NIST AI RMF).

## **🎯 Objectifs Principaux**

1. **Mémoire Gérée :** Mettre en place une mémoire à court et long terme avec un contrôle strict des consentements et une minimisation des données.  
2. **Interprétations Loguées :** Assurer que chaque action, décision et interaction de l'agent soit enregistrée dans un journal immuable (WORM) et analysable.  
3. **Traçabilité Légale :** Garantir la capacité de reconstruire et d'expliquer une décision automatisée, conformément aux exigences légales (notamment l'ADM de la Loi 25).  
4. **Capacités d'Agent Avancées :** Viser des performances égales ou supérieures aux standards de l'industrie (Codex, agents avancés) sur des tâches de raisonnement et de manipulation d'outils, validées par des benchmarks rigoureux.

## **✨ Fonctionnalités Clés**

* **Moteur de Politiques (Policy Engine) :** Contrôle en amont de chaque action pour le masquage de PII, la vérification des droits et la conformité juridictionnelle.  
* **Exécution Sécurisée (Sandboxing) :** Isolation complète de l'exécution de code et des outils pour prévenir les risques de sécurité.  
* **Journalisation WORM :** Utilisation de chaînes de hachage (Merkle Tree) pour garantir l'intégrité et l'immuabilité des journaux d'audit.  
* **Génération de "Dossiers de Décision" :** Capacité à produire un rapport structuré pour chaque décision, expliquant les entrées, les règles appliquées et les sorties.  
* **Reproductibilité :** Versionnement strict des modèles, des paramètres (seed, température) et des politiques pour garantir des résultats reproductibles.  
* **Évaluation Continue :** Intégration d'un harnais d'évaluation continue basé sur des benchmarks standards (HumanEval, MBPP, SWE-bench-lite).

## **🛠️ Architecture Technique**

Le projet est structuré autour d'une arborescence claire, séparant la configuration, les modèles, la mémoire, les logs, les outils et l'évaluation.

* **Inférence Locale :** Le système est conçu pour utiliser des modèles locaux (ex: via llama.cpp ou vLLM) afin de garantir la confidentialité des données.  
* **Mémoire Hybride :** Combine une mémoire épisodique (SQLite) pour le contexte de la conversation et une mémoire sémantique (FAISS/Parquet) pour la recherche de connaissances à long terme.  
* **Observabilité :** Les logs sont structurés au format JSONL compatible OpenTelemetry pour une analyse et une surveillance facilitées.  
* **Provenance :** Chaque artefact généré est accompagné de métadonnées de provenance suivant le standard W3C PROV-JSON.

## **🚀 Démarrage Rapide (Getting Started)**

### Prérequis

- Python 3.10 ou supérieur
- Git
- 8+ GB de RAM (16GB recommandé)
- Optionnel : GPU NVIDIA pour accélération

### Installation

```bash
# 1. Cloner le dépôt
git clone https://github.com/votre-org/FilAgent.git
cd FilAgent

# 2. Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Télécharger un modèle
# Voir models/weights/README.md pour les instructions détaillées
mkdir -p models/weights
# Exemple avec Llama 3 :
cd models/weights
wget https://huggingface.co/TheBloke/Llama-3-8B-Instruct-GGUF/resolve/main/llama-3-8b-instruct.Q4_K_M.gguf -O base.gguf
cd ../..

# 5. Initialiser la base de données
python -c "from memory.episodic import create_tables; create_tables()"
```

### Configuration

Les configurations par défaut sont dans `config/`. Vous pouvez les ajuster :

- `config/agent.yaml` : Paramètres de génération, modèle, mémoire
- `config/policies.yaml` : Règles d'usage, RBAC, guardrails
- `config/retention.yaml` : Politiques de rétention des données
- `config/provenance.yaml` : Configuration de traçabilité
- `config/eval_targets.yaml` : Seuils d'évaluation

### Lancement

```bash
# Lancer le serveur API
python runtime/server.py

# Le serveur sera accessible sur http://localhost:8000
# Documentation API sur http://localhost:8000/docs
```

### Test rapide

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Bonjour !"}],
    "conversation_id": "test-123"
  }'
```

Pour plus de détails, voir [README_SETUP.md](README_SETUP.md)

## **📊 Métriques et Monitoring**

FilAgent intègre un système complet de métriques et de monitoring pour assurer la qualité et la performance du code.

### Métriques de Tests

Le système collecte automatiquement les métriques suivantes :

* **Couverture de code** - Suivi de la couverture avec tendances historiques
* **Résultats des tests** - Nombre de tests réussis/échoués/ignorés
* **Performance** - Durée d'exécution des tests
* **Régressions** - Détection automatique des régressions de couverture

### Utilisation

```bash
# Lancer les tests avec collecte de métriques
pytest --metrics

# Lancer les tests avec couverture
pytest --cov=runtime --cov=planner --cov=tools --cov-report=html --cov-report=term

# Vérifier les régressions de couverture
python scripts/check_coverage_regression.py

# Générer les badges
python scripts/generate_badges.py --markdown
```

### Pre-commit Hooks

Le projet utilise des hooks pre-commit pour garantir la qualité du code :

```bash
# Installer les hooks
pip install pre-commit
pre-commit install

# Les hooks incluent :
# - Formatage avec Black
# - Tri des imports avec isort
# - Linting avec flake8
# - Vérification de sécurité avec Bandit
# - Vérification de couverture (seuil: 70%)
# - Détection de régressions de couverture
```

### Rapports de Métriques

Les métriques sont stockées dans `eval/metrics/test_metrics.db` et peuvent être consultées via :

```python
from eval.metrics import get_test_metrics

metrics = get_test_metrics()

# Récupérer les derniers test runs
recent_runs = metrics.get_recent_runs(limit=10)

# Récupérer les tendances de couverture
trends = metrics.get_coverage_trends(days=30)

# Récupérer les régressions détectées
regressions = metrics.get_regressions(days=7, severity="critical")

# Générer un rapport complet
report = metrics.generate_report(output_path="eval/reports/test_metrics_report.json")
```

## **⚖️ Conformité et Gouvernance**

Ce projet intègre dès sa conception les cadres de gouvernance suivants :

* **ISO/IEC 42001 :** Système de management de l'IA.  
* **NIST AI RMF 1.0 :** Cadre de gestion des risques de l'IA.  
* **Loi 25 (Québec) :** Transparence et explicabilité des décisions automatisées.  
* **AI Act (UE) :** Exigences de traçabilité et de transparence.