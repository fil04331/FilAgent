# **LLM-Agent : Gouvernance & Traçabilité**

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

* **Inférence Flexible :** Support de multiples backends LLM :
  - **Local** : llama.cpp ou vLLM pour garantir la confidentialité des données
  - **Cloud** : Perplexity API avec recherche web en temps réel
* **Mémoire Hybride :** Combine une mémoire épisodique (SQLite) pour le contexte de la conversation et une mémoire sémantique (FAISS/Parquet) pour la recherche de connaissances à long terme.
* **Observabilité :** Les logs sont structurés au format JSONL compatible OpenTelemetry pour une analyse et une surveillance facilitées.
* **Provenance :** Chaque artefact généré est accompagné de métadonnées de provenance suivant le standard W3C PROV-JSON.

### **Choix du Backend LLM**

FilAgent supporte deux modes d'exécution selon vos besoins :

#### **Option 1 : Perplexity API (Cloud)** - Configuration actuelle

**Avantages :**
- Démarrage rapide sans téléchargement de modèle
- Recherche web en temps réel intégrée (modèles Sonar)
- Performance élevée sur tâches complexes
- Pas de matériel GPU requis

**Prérequis :**
- Clé API Perplexity (obtenir sur https://www.perplexity.ai/settings/api)
- Connexion Internet stable

**Statut :** Backend actuellement configuré et fonctionnel avec Perplexity API.

#### **Option 2 : Modèle Local (llama.cpp)** - Privé

**Avantages :**
- Confidentialité maximale (100% local)
- Pas de dépendance Internet
- Conformité stricte pour données sensibles
- Coûts d'opération réduits

**Prérequis :**
- Téléchargement modèle GGUF (~4-8 GB selon quantisation)
- 8+ GB RAM (16GB recommandé)
- GPU optionnel mais recommandé pour performance

**Note :** Les deux backends garantissent la même conformité (Loi 25, GDPR, AI Act) grâce aux middlewares de gouvernance intégrés.

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

# 4. Choisir votre backend LLM

# Option A: Perplexity API (RECOMMANDÉ pour démarrage rapide)
# - Copier le fichier .env.example vers .env
cp .env.example .env
# - Éditer .env et ajouter votre clé API Perplexity
#   LLM_BACKEND=perplexity
#   PERPLEXITY_API_KEY=pplx-votre-cle-ici
# - Aucun téléchargement de modèle requis
# Voir docs/PERPLEXITY_INTEGRATION.md pour configuration détaillée

# Option B: Modèle local llama.cpp (pour confidentialité maximale)
# - Télécharger un modèle GGUF
mkdir -p models/weights
cd models/weights
wget https://huggingface.co/TheBloke/Llama-3-8B-Instruct-GGUF/resolve/main/llama-3-8b-instruct.Q4_K_M.gguf -O base.gguf
cd ../..
# - Configurer .env avec LLM_BACKEND=llama.cpp
# Voir models/weights/README.md pour plus de modèles disponibles

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
# Test avec Perplexity (backend actuel)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Bonjour ! Peux-tu me confirmer que tu fonctionnes ?"}],
    "conversation_id": "test-123"
  }'

# Test avec modèle local (si configuré)
# Même commande - le backend est transparent pour l'utilisateur
```

**Guides additionnels :**
- [QUICK_TEST.md](QUICK_TEST.md) - Guide complet de tests post-installation
- [README_DEPLOYMENT.md](README_DEPLOYMENT.md) - Guide de déploiement en production
- [docs/PERPLEXITY_INTEGRATION.md](docs/PERPLEXITY_INTEGRATION.md) - Configuration détaillée Perplexity

## **⚖️ Conformité et Gouvernance**

Ce projet intègre dès sa conception les cadres de gouvernance suivants :

* **ISO/IEC 42001 :** Système de management de l'IA.  
* **NIST AI RMF 1.0 :** Cadre de gestion des risques de l'IA.  
* **Loi 25 (Québec) :** Transparence et explicabilité des décisions automatisées.  
* **AI Act (UE) :** Exigences de traçabilité et de transparence.