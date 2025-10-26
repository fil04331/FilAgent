# Modèles LLM

Ce dossier contient les poids des modèles pour l'agent.

## Installation des modèles

### Option 1 : Télécharger un modèle GGUF (recommandé)

Pour commencer avec **Llama 3** (8B) :

```bash
# Depuis HuggingFace (via llama.cpp)
wget https://huggingface.co/TheBloke/Llama-3-8B-Instruct-GGUF/resolve/main/llama-3-8b-instruct.Q4_K_M.gguf -O base.gguf
```

### Option 2 : Utiliser vLLM avec un modèle HF

Si vous voulez utiliser vLLM au lieu de llama.cpp :

```bash
# Créer un dossier pour les modèles HF
mkdir -p models/hf_models

# Télécharger depuis HuggingFace
git lfs install
git clone https://huggingface.co/meta-llama/Llama-3-8B-Instruct models/hf_models/llama-3-8b-instruct
```

## Modèles recommandés

- **Llama 3 8B Instruct** : Bon compromis qualité/performance
- **CodeLlama 7B/13B** : Spécialisé code
- **Qwen 7B** : Très performant, licence permissive
- **Mistral 7B** : Excellent pour le français

## Format GGUF

Les modèles GGUF sont quantifiés pour optimiser la mémoire :
- Q4_K_M : Bon compromis (4-bit)
- Q5_K_M : Meilleure qualité (5-bit)
- Q8_0 : Très haute qualité (8-bit)

## Configuration

Ajuster le chemin du modèle dans `config/agent.yaml` :

```yaml
model:
  path: "models/weights/base.gguf"
  backend: "llama.cpp"
```
