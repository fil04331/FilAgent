# Guide de Gestion des Pull Requests

Ce répertoire contient les outils et documentation pour gérer les Pull Requests selon le plan établi.

## 📋 Fichiers

- **`manage_prs.md`**: Plan détaillé de gestion des PRs (lecture complète recommandée)
- **`manage_prs.sh`**: Script automatisé pour exécuter le plan
- **`issue_tests.md`**: Template pour issue "Tests Automatisés"
- **`issue_benchmarks.md`**: Template pour issue "Benchmarks"
- **`issue_policy_engine.md`**: Template pour issue "Policy Engine & RBAC"

## 🚀 Exécution Rapide

### Option 1: Script Automatisé (Recommandé)

```bash
# Prérequis: Installer GitHub CLI
# https://cli.github.com/

# Authentification (une seule fois)
gh auth login

# Mode dry-run (simulation sans modifications)
./scripts/manage_prs.sh --dry-run

# Exécution réelle
./scripts/manage_prs.sh
```

Le script va:
1. ✅ Fusionner PR #118 (ComplianceGuardian fix)
2. ✅ Fermer PRs redondantes (#114, #110, #104, #117, #116, #108, #107)
3. ✅ Fusionner PR #112 (nettoyage scripts)
4. ✅ Fusionner PRs Dependabot (#105, #106)
5. ✅ Créer 3 issues pour prochaines étapes

### Option 2: Exécution Manuelle

Si vous préférez contrôler chaque étape:

```bash
# 1. Fusionner PR #118
gh pr view 118
gh pr merge 118 --squash --delete-branch

# 2. Fermer PRs redondantes
gh pr close 114 --comment "Fermée: redondante avec #118"
gh pr close 110 --comment "Fermée: modifications dépendances dépassées"
# ... etc (voir manage_prs.md pour commandes complètes)

# 3. Fusionner PR #112
gh pr merge 112 --squash --delete-branch

# 4. Fusionner Dependabot
gh pr merge 105 --squash --delete-branch
gh pr merge 106 --squash --delete-branch

# 5. Créer issues
gh issue create --title "..." --body-file scripts/issue_tests.md --label "testing,enhancement"
# ... etc
```

### Option 3: Via Interface Web GitHub

Suivez le plan détaillé dans `manage_prs.md` section par section via l'interface web GitHub.

## 📖 Plan Détaillé

Voir **`manage_prs.md`** pour:
- Justification de chaque action
- Ordre d'exécution (Core → Client-facing → Cosmétique)
- Checklist de vérification
- Points de vigilance
- Gestion des erreurs

## 🎯 Ordre d'Exécution

```
Phase 1: PR #118 (CRITIQUE)
    ↓
Phase 2: Fermeture PRs redondantes
    ↓
Phase 3: PR #112 (Nettoyage)
    ↓
Phase 4: PRs Dependabot (#105, #106)
    ↓
Phase 5: Création issues
```

**Principe**: Toujours commencer par les correctifs critiques (sécurité/conformité), puis nettoyage, puis améliorations.

## 🔍 Vérification Après Exécution

```bash
# Vérifier que main est stable
git checkout main
git pull origin main
pytest

# Lister les issues créées
gh issue list --label "enhancement"

# Vérifier qu'aucune PR redondante n'est ouverte
gh pr list --state open
```

## ⚠️ Points de Vigilance

### Avant de Commencer
- [ ] Vérifier que PR #118 passe TOUS les tests CI
- [ ] Sauvegarder état actuel: `git checkout -b backup-$(date +%Y%m%d)`
- [ ] Notifier l'équipe du nettoyage prévu

### Pendant l'Exécution
- [ ] Ne pas fusionner #112 avant #118 (éviter conflits)
- [ ] Extraire tests/docs utiles de #107 AVANT fermeture
- [ ] Vérifier pas de régression après chaque fusion

### Après l'Exécution
- [ ] Vérifier `main` est stable (`pytest`)
- [ ] Consulter les issues créées
- [ ] Planifier prochaines étapes

## 🆘 Aide & Dépannage

### Erreur: "gh: command not found"

```bash
# macOS
brew install gh

# Linux (Debian/Ubuntu)
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh

# Windows
winget install --id GitHub.cli
```

### Tests échouent après fusion

```bash
# Vérifier les logs CI
gh pr checks <PR_NUM>

# Si régression critique, rollback
git revert <commit_sha>
git push origin main
```

### Conflit de merge

```bash
# Option 1: Résoudre manuellement
git checkout <branch>
git merge main
# Résoudre conflits
git add .
git commit
git push

# Option 2: Rebaser
git checkout <branch>
git rebase main
# Résoudre conflits
git rebase --continue
git push --force-with-lease
```

### Question sur fermeture PR

Si incertain si une PR doit être fermée:
1. Lire le diff complet: `gh pr diff <NUM>`
2. Vérifier si travail unique ou redondant
3. Si doute, créer issue pour préserver travail
4. Demander review si nécessaire

## 📞 Contact

Pour questions ou problèmes:
- Créer une issue sur GitHub
- Consulter `docs/` pour documentation
- Checker `CLAUDE.md` pour guidelines AI

---

**Rappel**: Toujours prioriser Sécurité et Conformité en premier!
