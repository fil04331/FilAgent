# Modèles LLM

Ce dossier contient les poids des modèles pour l'exécution locale de l'agent.

**IMPORTANT** : Le téléchargement d'un modèle local est **OPTIONNEL**. FilAgent peut fonctionner avec Perplexity API (configuration actuelle) sans téléchargement de modèle.

## Quand télécharger un modèle local ?

Téléchargez un modèle GGUF uniquement si :
- Vous souhaitez une confidentialité maximale (100% local)
- Vous n'avez pas de connexion Internet stable
- Vous voulez éviter les coûts API récurrents
- Vos données sont trop sensibles pour le cloud

**Statut actuel** : FilAgent est configuré avec Perplexity API et fonctionne sans modèle local.

## Installation d'un modèle local (optionnel)

### Modèle recommandé par défaut : Llama 3 8B Instruct

**Caractéristiques** :
- **Taille** : ~4.6 GB (quantification Q4_K_M)
- **RAM requise** : 8 GB minimum
- **Performance** : Bon équilibre qualité/vitesse
- **Licence** : Llama 3 Community License (usage commercial autorisé)

**Commande de téléchargement** :

```bash
# Depuis le répertoire FilAgent
cd models/weights

# Télécharger Llama 3 8B Instruct (Q4_K_M quantization)
wget https://huggingface.co/TheBloke/Llama-3-8B-Instruct-GGUF/resolve/main/llama-3-8b-instruct.Q4_K_M.gguf -O base.gguf

# Vérifier le téléchargement (doit afficher ~4.6 GB)
ls -lh base.gguf

# Retour au répertoire racine
cd ../..
```

**Temps estimé** : 5-30 minutes selon votre connexion Internet.

### Option 2 : Utiliser vLLM avec un modèle HF

Si vous voulez utiliser vLLM au lieu de llama.cpp :

```bash
# Créer un dossier pour les modèles HF
mkdir -p models/hf_models

# Télécharger depuis HuggingFace
git lfs install
git clone https://huggingface.co/meta-llama/Llama-3-8B-Instruct models/hf_models/llama-3-8b-instruct
```

## Autres modèles recommandés

Si Llama 3 8B ne convient pas, alternatives :

| Modèle | Taille | Cas d'usage | Commande téléchargement |
|--------|--------|-------------|------------------------|
| **Mistral 7B** | 4.1 GB | Excellent français | `wget https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf -O base.gguf` |
| **CodeLlama 7B** | 3.8 GB | Spécialisé code | `wget https://huggingface.co/TheBloke/CodeLlama-7B-Instruct-GGUF/resolve/main/codellama-7b-instruct.Q4_K_M.gguf -O base.gguf` |
| **Qwen 7B** | 4.2 GB | Multilangue performant | `wget https://huggingface.co/TheBloke/Qwen-7B-GGUF/resolve/main/qwen-7b.Q4_K_M.gguf -O base.gguf` |

## Quantification GGUF expliquée

Les modèles GGUF sont compressés pour réduire l'usage mémoire :

| Format | Bits | Taille | Qualité | Recommandation |
|--------|------|--------|---------|----------------|
| **Q4_K_M** | 4-bit | ~4 GB | Bonne | **Défaut - équilibre optimal** |
| Q4_0 | 4-bit | ~3.5 GB | Acceptable | Si RAM très limitée |
| Q5_K_M | 5-bit | ~5 GB | Très bonne | Si RAM disponible |
| Q8_0 | 8-bit | ~8 GB | Excellente | Si RAM ample + GPU |

**Recommandation générale** : Commencer avec Q4_K_M, upgrader à Q5_K_M ou Q8_0 si performance insuffisante.

## Configuration après téléchargement

### 1. Modifier .env

Basculer de Perplexity vers modèle local :

```bash
# Éditer .env
nano .env

# Changer ces lignes :
LLM_BACKEND=llama.cpp           # Au lieu de "perplexity"
MODEL_PATH=models/weights/base.gguf
CONTEXT_SIZE=4096
N_GPU_LAYERS=35                 # 0 si pas de GPU
```

### 2. Vérifier config/agent.yaml

Le fichier `config/agent.yaml` doit correspondre :

```yaml
model:
  path: "models/weights/base.gguf"
  type: "llama-cpp"
  temperature: 0.7
  max_tokens: 2048
```

### 3. Redémarrer le serveur

```bash
# Arrêter le serveur si en cours
# Ctrl+C

# Relancer
python runtime/server.py

# Vérifier dans les logs :
# "✓ Model loaded successfully from models/weights/base.gguf"
```

## Dépannage

### Problème : Fichier base.gguf introuvable

**Erreur** :
```
FileNotFoundError: models/weights/base.gguf
```

**Solutions** :
1. Vérifier que le fichier existe : `ls -lh models/weights/base.gguf`
2. Vérifier le chemin dans `.env` : `MODEL_PATH=models/weights/base.gguf`
3. Retélécharger si corrompu ou incomplet

### Problème : Modèle trop lent

**Causes** :
- Exécution CPU uniquement (pas de GPU)
- Modèle trop grand pour la RAM disponible
- Context size trop élevé

**Solutions** :
1. **Activer GPU** si disponible :
   ```bash
   # Dans .env
   N_GPU_LAYERS=35
   ```

2. **Utiliser quantification plus agressive** :
   ```bash
   # Télécharger Q4_0 au lieu de Q4_K_M
   wget https://huggingface.co/TheBloke/Llama-3-8B-Instruct-GGUF/resolve/main/llama-3-8b-instruct.Q4_0.gguf -O base.gguf
   ```

3. **Réduire context size** :
   ```bash
   # Dans .env
   CONTEXT_SIZE=2048  # Au lieu de 4096
   ```

### Problème : Out of Memory (OOM)

**Symptômes** :
```
RuntimeError: Out of memory
```

**Solutions** :
1. Vérifier RAM disponible : `free -h`
2. Réduire `N_GPU_LAYERS` si GPU :
   ```bash
   N_GPU_LAYERS=20  # Au lieu de 35
   ```
3. Utiliser un modèle plus petit (Q4_0 ou même un modèle 3B/7B plus léger)

## Retour vers Perplexity API

Si le modèle local ne fonctionne pas bien :

```bash
# Éditer .env
nano .env

# Restaurer configuration Perplexity
LLM_BACKEND=perplexity
PERPLEXITY_API_KEY=pplx-votre-cle-ici
PERPLEXITY_MODEL=llama-3.1-sonar-large-128k-online

# Redémarrer serveur
python runtime/server.py
```

## Ressources additionnelles

- **Documentation Perplexity** : [docs/PERPLEXITY_INTEGRATION.md](../../docs/PERPLEXITY_INTEGRATION.md)
- **Guide déploiement** : [README_DEPLOYMENT.md](../../README_DEPLOYMENT.md)
- **HuggingFace GGUF models** : https://huggingface.co/models?search=gguf
- **llama.cpp GitHub** : https://github.com/ggerganov/llama.cpp
