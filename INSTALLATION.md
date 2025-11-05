# Installation de FilAgent

## 🔧 Problème de clonage résolu

### Symptôme

Lors du clonage du dépôt sur certains systèmes, un dossier `FilAgent-1` ou `filagent` était créé au lieu de `FilAgent`, causant des problèmes de routes et de chemins d'accès.

### Solution mise en place

Le projet utilise maintenant plusieurs fichiers de configuration pour garantir la cohérence :

1. **pyproject.toml** : Définit explicitement `name = "FilAgent"` pour le package Python
2. **.gitattributes** : Force la normalisation des fins de lignes et la gestion des fichiers binaires
3. **setup.cfg** : Configuration compatible avec les outils plus anciens
4. **.editorconfig** : Assure la cohérence du style de code entre éditeurs

### Instructions de clonage recommandées

```bash
# Option 1 : Clonage standard (recommandé)
git clone https://github.com/fil04331/FilAgent.git
cd FilAgent

# Option 2 : Clonage avec nom de dossier explicite
git clone https://github.com/fil04331/FilAgent.git FilAgent
cd FilAgent

# Option 3 : Si vous avez déjà un clone problématique
cd ..
rm -rf FilAgent-1  # ou filagent, selon le nom créé
git clone https://github.com/fil04331/FilAgent.git FilAgent
cd FilAgent
```

## 📦 Installation du package

### Méthode 1 : Installation avec pip (recommandé pour développement)

```bash
# 1. Cloner le dépôt
git clone https://github.com/fil04331/FilAgent.git
cd FilAgent

# 2. Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate

# 3. Installer en mode éditable avec dépendances de développement
pip install -e ".[dev,test]"
```

### Méthode 2 : Installation depuis requirements.txt (legacy)

```bash
# Pour compatibilité avec les anciens workflows
pip install -r requirements.txt
```

### Méthode 3 : Installation production

```bash
# Installation minimale pour production
pip install -e .

# Avec support GPU
pip install -e ".[gpu]"

# Avec vLLM
pip install -e ".[vllm]"

# Installation complète
pip install -e ".[all]"
```

## 🛠️ Vérification de l'installation

```bash
# Vérifier que le package est correctement installé
python -c "import runtime; import planner; import memory; print('FilAgent OK')"

# Vérifier la version
python -c "from importlib.metadata import version; print(f'FilAgent v{version(\"FilAgent\")}')"

# Lancer les tests
pytest tests/ -v

# Vérifier le formatage du code
black --check .
flake8 .
mypy runtime memory planner tools
```

## 📁 Structure du projet après installation

```
FilAgent/                    ← IMPORTANT: Le dossier DOIT s'appeler "FilAgent"
├── pyproject.toml          ← Configuration principale du package
├── setup.cfg               ← Configuration legacy (flake8, etc.)
├── requirements.txt        ← Dépendances (legacy)
├── MANIFEST.in             ← Fichiers à inclure dans la distribution
├── .gitattributes          ← Normalisation git
├── .editorconfig           ← Style de code
├── .gitignore              ← Fichiers à ignorer
├── runtime/                ← Code principal
├── planner/                ← HTN planning
├── memory/                 ← Gestion mémoire
├── tools/                  ← Outils et connecteurs
├── policy/                 ← Politiques de gouvernance
├── config/                 ← Configuration YAML
├── tests/                  ← Tests unitaires et intégration
└── ...
```

## 🚨 Dépannage

### Le dossier s'appelle toujours "FilAgent-1"

```bash
# Supprimer complètement le clone existant
cd /chemin/vers/parent
rm -rf FilAgent*

# Reconfigurer git pour respecter les noms de dossiers
git config --global core.ignorecase false

# Recloner
git clone https://github.com/fil04331/FilAgent.git FilAgent
```

### Problèmes de chemins après installation

```bash
# Si vous avez des imports qui échouent, réinstaller en mode éditable
pip uninstall FilAgent -y
pip install -e .

# Vérifier que PYTHONPATH est correct
python -c "import sys; print('\n'.join(sys.path))"
```

### Problèmes de fins de ligne (Windows)

```bash
# Configurer git pour utiliser LF (comme défini dans .gitattributes)
git config --global core.autocrlf input

# Recloner le dépôt
cd ..
rm -rf FilAgent
git clone https://github.com/fil04331/FilAgent.git FilAgent
```

### Problèmes de dépendances

```bash
# Réinstaller toutes les dépendances
pip install --upgrade pip setuptools wheel
pip install -e ".[dev,test]" --force-reinstall --no-cache-dir
```

## 🔄 Migration depuis une ancienne installation

Si vous avez déjà une installation existante sans pyproject.toml :

```bash
# 1. Sauvegarder vos modifications locales
git stash

# 2. Mettre à jour depuis origin
git pull origin main

# 3. Réinstaller le package
pip uninstall FilAgent -y
pip install -e ".[dev,test]"

# 4. Restaurer vos modifications
git stash pop
```

## ✅ Checklist d'installation

- [ ] Le dossier s'appelle `FilAgent` (pas `FilAgent-1`, `filagent`, etc.)
- [ ] L'environnement virtuel est activé
- [ ] Les dépendances sont installées (`pip install -e ".[dev,test]"`)
- [ ] Les tests passent (`pytest tests/ -v`)
- [ ] Les imports fonctionnent (`import runtime; import planner`)
- [ ] Le formatage est correct (`black --check .`)
- [ ] Flake8 ne remonte pas d'erreurs (`flake8 .`)

## 📚 Commandes utiles

```bash
# Lancer le serveur
python runtime/server.py

# Lancer les tests avec couverture
pytest tests/ --cov=. --cov-report=html

# Formatter le code
black .

# Vérifier le code
flake8 .
mypy runtime memory planner tools

# Générer la documentation
# (À configurer selon vos besoins)

# Construire le package
python -m build

# Publier sur PyPI (après configuration)
python -m twine upload dist/*
```

## 🆘 Support

Si vous rencontrez toujours des problèmes :

1. Vérifiez que vous utilisez Python 3.10+
2. Consultez les issues GitHub : https://github.com/fil04331/FilAgent/issues
3. Créez une nouvelle issue avec :
   - Votre OS et version de Python
   - La commande de clonage utilisée
   - Le nom du dossier créé
   - Les messages d'erreur complets
