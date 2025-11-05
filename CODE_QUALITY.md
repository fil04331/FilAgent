# Code Quality & Developer Setup

## 🎯 Vue d'ensemble

FilAgent utilise une infrastructure complète de qualité de code pour garantir :
- ✅ **Conformité PEP 8** automatique via Black
- ✅ **Détection précoce** des erreurs avec pre-commit hooks
- ✅ **Sécurité** via scan automatique (Bandit, detect-secrets)
- ✅ **CI/CD robuste** avec quality gates
- ✅ **Onboarding rapide** pour nouveaux développeurs

---

## 🚀 Setup Rapide (Nouveaux Développeurs)

### Option 1: Script automatique (recommandé)

```bash
# Un seul commande pour tout installer
./scripts/setup-dev.sh

# Avec options
./scripts/setup-dev.sh --quick       # Installation rapide (dev seulement)
./scripts/setup-dev.sh --skip-venv   # Utilise environnement existant
```

### Option 2: Manuel

```bash
# 1. Créer environnement virtuel
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Installer dépendances
pip install -e ".[dev,test]"

# 3. Installer pre-commit hooks
pre-commit install
pre-commit install --hook-type commit-msg

# 4. Vérifier
pre-commit run --all-files
```

---

## 🛠️ Outils Installés

| Outil | Rôle | Quand s'exécute |
|-------|------|-----------------|
| **Black** | Formatage automatique PEP 8 | Pre-commit + CI/CD |
| **isort** | Tri des imports | Pre-commit + CI/CD |
| **flake8** | Linting & détection erreurs | Pre-commit + CI/CD |
| **mypy** | Type checking | Pre-commit + CI/CD |
| **detect-secrets** | Détection secrets/clés API | Pre-commit |
| **Bandit** | Analyse sécurité Python | CI/CD seulement |
| **conventional-pre-commit** | Validation format commits | Pre-commit (commit-msg) |

---

## 📝 Workflow de Développement

### 1. Créer une branche

```bash
git checkout -b feature/ma-feature
# ou
git checkout -b fix/correction-bug
```

### 2. Développer

Écrivez votre code normalement. Les hooks pre-commit s'exécuteront automatiquement.

### 3. Formater manuellement (optionnel)

```bash
# Formater tout le projet
black .
isort .

# Formater un seul fichier
black mon_fichier.py

# Vérifier sans modifier
black --check .
```

### 4. Vérifier linting

```bash
# Linting complet
flake8 .

# Linting d'un fichier
flake8 runtime/agent.py

# Ignorer certaines erreurs
flake8 --extend-ignore=E501 .
```

### 5. Commit

```bash
git add .
git commit -m "feat(planner): Add HTN support"

# Les hooks pre-commit vont automatiquement :
# ✅ Formater avec Black
# ✅ Trier imports avec isort
# ✅ Vérifier avec flake8
# ✅ Valider format du commit message
# ✅ Détecter secrets
```

Si un hook échoue :
```bash
# Les fichiers sont automatiquement corrigés
# Il suffit de re-add et re-commit
git add .
git commit -m "feat(planner): Add HTN support"
```

### 6. Push et PR

```bash
git push origin feature/ma-feature

# Sur GitHub, le CI/CD va :
# ✅ Vérifier formatage (Black + isort)
# ✅ Linting (flake8)
# ✅ Type checking (mypy)
# ✅ Security scan (Bandit)
# ✅ Test imports

# Si échec : GitHub Actions va auto-formater si possible
# Sinon : corriger localement et re-push
```

---

## 🔍 Commandes Utiles

### Formatage

```bash
# Formater tout le projet
black .

# Vérifier sans modifier (dry-run)
black --check --diff .

# Formater avec verbosité
black . --verbose

# Exclure certains dossiers
black . --exclude "/(models|\.venv)/"
```

### Linting

```bash
# Linting complet
flake8 .

# Linting critique uniquement (erreurs syntaxe)
flake8 . --select=E9,F63,F7,F82

# Stats de qualité
flake8 . --statistics

# Complexité cyclomatique
flake8 . --max-complexity=10
```

### Type Checking

```bash
# Type checking complet
mypy runtime memory planner tools

# Avec rapports détaillés
mypy . --show-error-codes --pretty

# Ignorer imports manquants
mypy . --ignore-missing-imports
```

### Pre-commit

```bash
# Exécuter tous les hooks sur tous les fichiers
pre-commit run --all-files

# Exécuter un hook spécifique
pre-commit run black --all-files
pre-commit run flake8 --all-files

# Mettre à jour versions des hooks
pre-commit autoupdate

# Désinstaller hooks (temporaire)
pre-commit uninstall

# Réinstaller
pre-commit install
```

### Security

```bash
# Scan sécurité avec Bandit
bandit -r runtime memory planner tools -ll

# Créer rapport JSON
bandit -r . -ll -f json -o bandit-report.json

# Détecter secrets
detect-secrets scan --baseline .secrets.baseline

# Mettre à jour baseline
detect-secrets scan --update .secrets.baseline
```

---

## 🐛 Dépannage

### "pre-commit command not found"

```bash
pip install pre-commit
pre-commit install
```

### "Black reformatte tout le fichier"

C'est normal ! Black est "opinionated" et impose son style. Acceptez les changements :

```bash
black .
git add .
git commit -m "style: Apply Black formatting"
```

### "flake8 trouve trop d'erreurs"

Corrigez les erreurs critiques d'abord :

```bash
# Erreurs critiques seulement
flake8 . --select=E9,F63,F7,F82

# Puis corrigez progressivement
flake8 runtime/  # Un dossier à la fois
```

### "CI/CD échoue mais local passe"

Vérifiez les versions des outils :

```bash
pip freeze | grep -E "black|isort|flake8|mypy"

# Alignez sur les versions du CI (.pre-commit-config.yaml)
pip install black==24.1.0 isort==5.13.2 flake8==7.0.0
```

### "Commit message rejeté"

Utilisez le format Conventional Commits :

```bash
# Format: <type>(<scope>): <description>

# ✅ CORRECT
git commit -m "feat(planner): Add HTN support"
git commit -m "fix(rbac): Resolve permission check"
git commit -m "docs: Update installation guide"

# ❌ INCORRECT
git commit -m "Added feature"
git commit -m "Fixed bug"
git commit -m "Updates"
```

Types valides : `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`

### "Hook trop lent"

Désactivez temporairement pour un commit rapide :

```bash
# ATTENTION : À utiliser avec parcimonie !
git commit --no-verify -m "..."

# Puis exécutez les hooks manuellement après
pre-commit run --all-files
```

---

## 📊 Métriques de Qualité

### Couverture de Tests

```bash
# Exécuter tests avec couverture
pytest tests/ --cov=. --cov-report=html

# Voir rapport
open htmlcov/index.html  # macOS/Linux
start htmlcov/index.html # Windows
```

### Complexité du Code

```bash
# Complexité cyclomatique
flake8 . --max-complexity=10 --statistics

# Identifiez fonctions trop complexes
flake8 . --max-complexity=5 --show-source
```

### Qualité globale

```bash
# Score Flake8 (moins = mieux)
flake8 . --statistics | tail -1

# Nombre de violations
flake8 . --count

# Erreurs par type
flake8 . --statistics | sort -rn
```

---

## 🔒 Sécurité

### Règles strictes

1. ❌ **JAMAIS** commiter :
   - Clés API, tokens OAuth
   - Mots de passe, credentials
   - Données personnelles (PII)
   - Fichiers `.env`

2. ✅ **TOUJOURS** :
   - Utiliser variables d'environnement
   - Exécuter `detect-secrets` avant commit
   - Vérifier rapports Bandit dans CI/CD

### Si vous committez accidentellement un secret

```bash
# 1. IMMÉDIATEMENT révoquer la clé/token

# 2. Supprimer du historique Git (DANGEREUX)
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch path/to/file" \
  --prune-empty --tag-name-filter cat -- --all

# 3. Force push (coordination équipe requise)
git push origin --force --all

# 4. Notifier l'équipe sécurité
```

---

## 📚 Ressources

### Documentation

- [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) - Guide de contribution complet
- [INSTALLATION.md](INSTALLATION.md) - Guide d'installation
- [pyproject.toml](pyproject.toml) - Configuration Black, isort, pytest
- [setup.cfg](setup.cfg) - Configuration flake8
- [.pre-commit-config.yaml](.pre-commit-config.yaml) - Configuration hooks

### Liens externes

- [Black Documentation](https://black.readthedocs.io/)
- [flake8 Documentation](https://flake8.pycqa.org/)
- [pre-commit Documentation](https://pre-commit.com/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [PEP 8 Style Guide](https://peps.python.org/pep-0008/)

---

## 🎯 Objectifs de Qualité

| Métrique | Cible | Actuel | Statut |
|----------|-------|--------|--------|
| Couverture tests | > 80% | - | 🔄 En cours |
| Flake8 violations | < 50 | 0 | ✅ Atteint |
| Complexité moyenne | < 10 | - | 🔄 En cours |
| Type hints | > 70% | - | 🔄 En cours |
| Bandit high severity | 0 | 0 | ✅ Atteint |

---

## 🆘 Support

**Questions ?**
- Ouvrir une [issue GitHub](https://github.com/fil04331/FilAgent/issues)
- Consulter [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)
- Contacter l'équipe sur [GitHub Discussions](https://github.com/fil04331/FilAgent/discussions)

**Bugs de tooling ?**
- Vérifier [.pre-commit-config.yaml](.pre-commit-config.yaml) pour versions
- Réinstaller : `pip install -e ".[dev,test]" --force-reinstall`
- Nettoyer caches : `pre-commit clean && pre-commit gc`

---

**Dernière mise à jour : 2025-11-05**
**Version : 0.3.0**
