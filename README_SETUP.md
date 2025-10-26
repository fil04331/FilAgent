# Guide de démarrage - FilAgent

## Prérequis

- Python 3.10+
- Git
- `pip` ou `uv` (gestionnaire de paquets)

## Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/votre-org/FilAgent.git
cd FilAgent
```

### 2. Créer un environnement virtuel

```bash
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Télécharger un modèle

Voir `models/weights/README.md` pour les instructions détaillées.

Pour un démarrage rapide :

```bash
# Créer le dossier
mkdir -p models/weights

# Télécharger Llama 3 8B (env. 4.5 GB)
cd models/weights
wget https://huggingface.co/TheBloke/Llama-3-8B-Instruct-GGUF/resolve/main/llama-3-8b-instruct.Q4_K_M.gguf -O base.gguf
cd ../..
```

### 5. Initialiser la base de données

```bash
# Créer la base de données SQLite pour la mémoire épisodique
python -c "from memory.episodic import create_tables; create_tables()"
```

### 6. Configurer (optionnel)

Les configurations par défaut sont dans `config/agent.yaml`.

Si vous voulez ajuster :
- `generation.temperature` : contrôle de la créativité (0.0 = déterministe)
- `generation.seed` : pour la reproductibilité
- `model.path` : chemin vers votre modèle
- `memory.episodic_ttl_days` : durée de conservation des conversations

## Lancer l'agent

### Mode développement (serveur local)

```bash
python runtime/server.py
```

L'API sera accessible sur `http://localhost:8000`

### Test rapide

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Bonjour !"}],
    "conversation_id": "test-123"
  }'
```

## Structure des logs

- `logs/events/*.jsonl` : Événements structurés
- `logs/decisions/DR-*.json` : Decision Records
- `logs/traces/otlp/` : Traces de provenance

## Prochaines étapes

- Voir `FilAgent.md` pour les spécifications complètes
- Consulter `docs/ADRs/` pour les décisions architecturales
- Lire `docs/SOPs/` pour les procédures opérationnelles

## Troubleshooting

### Erreur "Model not found"

Vérifier que le modèle est dans `models/weights/base.gguf` et que le chemin est correct dans `config/agent.yaml`.

### Erreur "llama-cpp-python not installed"

Réinstaller :

```bash
pip uninstall llama-cpp-python
pip install llama-cpp-python
```

### Manque de mémoire GPU

Réduire `n_gpu_layers` dans `config/agent.yaml` ou utiliser un modèle quantifié plus faible (Q3_K_S).

## Support

Pour les questions et contributions, voir le README principal.
