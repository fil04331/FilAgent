# Guide de Contribution - FilAgent

Merci de votre intérêt pour contribuer à FilAgent ! Ce guide vous aidera à démarrer rapidement.

## 📋 Table des matières

- [Standards de code](#-standards-de-code)
- [Setup développeur](#-setup-développeur)
- [Workflow de développement](#-workflow-de-développement)
- [Tests](#-tests)
- [Documentation](#-documentation)
- [Commit messages](#-commit-messages)
- [Pull Requests](#-pull-requests)
- [Sécurité](#-sécurité)

---

## 🎨 Standards de Code

FilAgent suit **strictement PEP 8** via des outils automatisés :

| Outil | Rôle | Configuration |
|-------|------|---------------|
| **Black** | Formatage automatique (opinionated) | `pyproject.toml` |
| **isort** | Tri des imports | `pyproject.toml` |
| **flake8** | Linting & détection erreurs | `setup.cfg` |
| **mypy** | Type checking statique | `pyproject.toml` |
| **pre-commit** | Hooks Git automatiques | `.pre-commit-config.yaml` |

### Philosophie : "Safety by Design"

- ✅ **Code formaté automatiquement** : Pas de débat sur le style
- ✅ **Hooks pre-commit** : Bloque les commits non conformes
- ✅ **CI/CD strict** : Aucun merge sans passing des checks
- ✅ **Type hints** : Encouragés pour la maintenabilité
- ✅ **Documentation** : Docstrings Google style obligatoires

---

## 🛠️ Setup Développeur

### Prérequis

- Python 3.10 ou supérieur
- Git
- 8+ GB RAM (16GB recommandé)
- Éditeur compatible EditorConfig (VSCode, PyCharm, Vim)

### Installation rapide

```bash
# 1. Cloner le dépôt
git clone https://github.com/fil04331/FilAgent.git
cd FilAgent

# 2. Créer environnement virtuel
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Installer en mode développement
pip install -e ".[dev,test]"

# 4. Activer pre-commit hooks
pre-commit install
pre-commit install --hook-type commit-msg

# 5. Vérifier setup
pre-commit run --all-files
```

### Configuration éditeur

#### VSCode

Installer les extensions :
```bash
code --install-extension ms-python.python
code --install-extension ms-python.black-formatter
code --install-extension ms-python.flake8
code --install-extension ms-python.mypy-type-checker
code --install-extension EditorConfig.EditorConfig
```

Créer `.vscode/settings.json` :
```json
{
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.mypyEnabled": true,
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

#### PyCharm

1. Ouvrir **Settings** → **Tools** → **Python Integrated Tools**
2. Configurer Black comme formateur externe
3. Activer inspection flake8
4. Activer mypy

---

## 🔄 Workflow de Développement

### 1. Créer une branche

```bash
# Feature
git checkout -b feature/ma-nouvelle-feature

# Bug fix
git checkout -b fix/correction-bug-xyz

# Documentation
git checkout -b docs/amelioration-readme
```

### 2. Développer et formater

```bash
# Pendant le développement
# Les hooks pre-commit s'exécutent automatiquement à chaque commit

# Formater manuellement si nécessaire
black .
isort .

# Vérifier linting
flake8 .

# Type checking
mypy runtime memory planner tools
```

### 3. Tester

```bash
# Tests unitaires
pytest tests/

# Tests avec couverture
pytest tests/ --cov=. --cov-report=html

# Tests spécifiques
pytest tests/test_planner/ -v
```

### 4. Commit

```bash
# Format de commit : <type>(<scope>): <description>
git add .
git commit -m "feat(planner): Add HTN hierarchical task network"

# Les hooks pre-commit vont :
# 1. Formater avec Black
# 2. Trier imports avec isort
# 3. Vérifier avec flake8
# 4. Valider format du message (conventional commits)
```

### 5. Push et PR

```bash
# Push vers votre branche
git push origin feature/ma-nouvelle-feature

# Créer PR sur GitHub
# Le CI/CD va automatiquement :
# - Vérifier formatage
# - Exécuter linting
# - Lancer tests
# - Scanner sécurité (Bandit)
```

---

## 🧪 Tests

### Structure des tests

```
tests/
├── conftest.py           # Fixtures pytest globales
├── test_integration_e2e.py
├── test_planner/
│   ├── test_planner.py
│   ├── test_executor.py
│   └── test_verifier.py
└── test_tools.py
```

### Écrire un test

```python
# tests/test_example.py
import pytest
from runtime.agent import Agent

def test_agent_initialization():
    """Test que l'agent s'initialise correctement."""
    agent = Agent()
    assert agent is not None
    assert agent.config is not None

@pytest.mark.llm
def test_agent_generation():
    """Test nécessitant un LLM (marqué pour skip si pas de GPU)."""
    agent = Agent()
    result = agent.generate("Hello")
    assert result.success
```

### Markers disponibles

```python
@pytest.mark.unit         # Tests unitaires rapides
@pytest.mark.integration  # Tests d'intégration
@pytest.mark.e2e          # Tests end-to-end
@pytest.mark.slow         # Tests lents (skip par défaut)
@pytest.mark.llm          # Nécessite LLM
@pytest.mark.gpu          # Nécessite GPU
@pytest.mark.compliance   # Tests de conformité
@pytest.mark.htn          # Tests HTN planning
```

### Exécution sélective

```bash
# Seulement tests unitaires
pytest -m unit

# Exclure tests lents
pytest -m "not slow"

# Tests HTN avec verbosité
pytest -m htn -v
```

---

## 📝 Documentation

### Docstrings obligatoires

Utiliser **Google style** :

```python
def calculate_confidence(
    probabilities: List[float],
    threshold: float = 0.7
) -> Tuple[float, bool]:
    """Calcule le score de confiance basé sur les probabilités.

    Args:
        probabilities: Liste des probabilités de chaque classe.
        threshold: Seuil de confiance (défaut: 0.7).

    Returns:
        Tuple contenant :
        - float: Score de confiance moyen
        - bool: True si au-dessus du seuil

    Raises:
        ValueError: Si probabilities est vide.

    Examples:
        >>> calculate_confidence([0.8, 0.9, 0.75])
        (0.816, True)
    """
    if not probabilities:
        raise ValueError("probabilities ne peut pas être vide")

    avg = sum(probabilities) / len(probabilities)
    return avg, avg >= threshold
```

### Type hints obligatoires

```python
# ✅ CORRECT
def process_data(
    data: List[Dict[str, Any]],
    config: Optional[Config] = None
) -> ProcessingResult:
    ...

# ❌ INCORRECT
def process_data(data, config=None):
    ...
```

---

## 📬 Commit Messages

### Format Conventional Commits

```
<type>(<scope>): <description>

[corps optionnel]

[footer optionnel]
```

### Types autorisés

| Type | Description | Exemple |
|------|-------------|---------|
| **feat** | Nouvelle fonctionnalité | `feat(planner): Add HTN support` |
| **fix** | Correction de bug | `fix(rbac): Resolve permission check` |
| **docs** | Documentation uniquement | `docs: Update installation guide` |
| **style** | Formatage (pas de changement logique) | `style: Fix trailing whitespace` |
| **refactor** | Refactoring | `refactor(agent): Extract planning logic` |
| **test** | Ajout/modification tests | `test: Add HTN executor tests` |
| **chore** | Maintenance, config | `chore: Update dependencies` |
| **perf** | Optimisation performance | `perf: Improve memory lookup` |

### Exemples

```bash
# Feature simple
git commit -m "feat: Add email notification support"

# Feature avec scope
git commit -m "feat(memory): Implement semantic search with FAISS"

# Bug fix avec référence issue
git commit -m "fix(server): Resolve CORS error on /chat endpoint

Fixes #123"

# Breaking change
git commit -m "feat(api)!: Change response format to include metadata

BREAKING CHANGE: API responses now include 'metadata' field"
```

---

## 🔀 Pull Requests

### Checklist avant PR

- [ ] Code formaté avec Black + isort
- [ ] Tests passent localement (`pytest`)
- [ ] Linting passe (`flake8`)
- [ ] Docstrings ajoutées/mises à jour
- [ ] CHANGELOG.md mis à jour (si applicable)
- [ ] Aucun secret/clé API dans le code
- [ ] Commit messages suivent Conventional Commits

### Template PR

```markdown
## Description
Décrivez les changements apportés.

## Type de changement
- [ ] Bug fix (non-breaking)
- [ ] Nouvelle feature (non-breaking)
- [ ] Breaking change
- [ ] Documentation

## Tests
- [ ] Tests unitaires ajoutés
- [ ] Tests existants passent
- [ ] Couverture de code maintenue/améliorée

## Checklist
- [ ] Code formaté (Black + isort)
- [ ] Linting passé (flake8)
- [ ] Docstrings ajoutées
- [ ] CHANGELOG mis à jour
```

### Revue de code

Les PRs doivent :
1. ✅ Passer le CI/CD (lint + tests)
2. ✅ Avoir au moins 1 approbation
3. ✅ Résoudre tous les commentaires
4. ✅ Être à jour avec `main`

---

## 🔒 Sécurité

### Règles strictes

1. ❌ **JAMAIS** commiter :
   - Clés API, tokens, secrets
   - Mots de passe, credentials
   - Données personnelles (PII)
   - Fichiers `.env`

2. ✅ **TOUJOURS** :
   - Utiliser variables d'environnement
   - Scanner avec `detect-secrets`
   - Tester avec `bandit`

### Détection automatique

Les hooks pre-commit détectent :
```bash
# detect-secrets
- id: detect-secrets

# detect-private-key
- id: detect-private-key
```

### Rapporter une vulnérabilité

**NE PAS** ouvrir d'issue publique. Envoyer un email à :
- `security@filagent.example.com` (à configurer)

---

## 🆘 Dépannage

### Pre-commit échoue

```bash
# Réinstaller hooks
pre-commit clean
pre-commit install
pre-commit run --all-files
```

### Black modifie tout le fichier

```bash
# Normal ! Black est opinionated
# Accepter les changements :
git add .
git commit -m "style: Apply Black formatting"
```

### Imports cassés après isort

```bash
# Vérifier configuration isort
isort --check-only --diff .

# Réinitialiser si nécessaire
git checkout -- .
isort .
```

### CI/CD échoue mais local passe

```bash
# Vérifier versions
pip freeze | grep -E "black|isort|flake8"

# Aligner sur versions CI (.pre-commit-config.yaml)
pip install black==24.1.0 isort==5.13.2
```

---

## 📚 Ressources

- [PEP 8 Style Guide](https://peps.python.org/pep-0008/)
- [Black Documentation](https://black.readthedocs.io/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [pytest Documentation](https://docs.pytest.org/)
- [Type Hints (PEP 484)](https://peps.python.org/pep-0484/)

---

## 🙏 Remerciements

Merci de contribuer à FilAgent ! Votre code rendra les PME québécoises plus sécurisées et conformes.

**Questions ?** Ouvrez une issue ou contactez l'équipe sur [GitHub Discussions](https://github.com/fil04331/FilAgent/discussions).
