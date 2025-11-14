# Plan de Gestion des Pull Requests - FilAgent

**Date**: 2025-11-14
**Objectif**: Nettoyer et fusionner les PRs selon la priorité sécurité/conformité

---

## 📋 Ordre d'Exécution

### Phase 1: Fusion Critique (PR #118)
**Priorité**: 🔴 CRITIQUE - À fusionner immédiatement

**PR #118**: Correctif ComplianceGuardian + Sécurité
- **Raison**: Bug critique + améliorations sécurité
- **Contenu**:
  - Correction bug ComplianceGuardian
  - Redaction PII améliorée
  - Logs d'erreurs sécurisés
  - Configuration clarifiée
  - Rationalisation dépendances

**Action**:
```bash
# Via GitHub Web UI
1. Aller sur https://github.com/fil04331/FilAgent/pull/118
2. Vérifier que tous les tests passent
3. Reviewer les changements
4. Cliquer "Merge pull request"
5. Confirmer avec "Confirm merge"
6. Option: "Delete branch" après fusion
```

**Alternative CLI** (si GitHub CLI est installé localement):
```bash
gh pr view 118
gh pr checks 118
gh pr merge 118 --squash --delete-branch
```

---

### Phase 2: Fermeture des PRs Redondantes
**Priorité**: 🟡 HAUTE - À fermer après #118

#### PRs à Fermer

| PR | Titre | Raison de Fermeture |
|----|-------|---------------------|
| #114 | ? | Doublon du correctif ComplianceGuardian |
| #110 | ? | Modifications dépendances dépassées |
| #104 | ? | Doublon ou dépassé |
| #117 | ? | Doublon ou dépassé |
| #116 | ? | Doublon ou dépassé |
| #108 | ? | Modifications test/docs à gérer séparément |
| #107 | Tests/Docs | À extraire en issue séparée |

**Actions pour chaque PR**:

```bash
# Via GitHub Web UI pour chaque PR
1. Aller sur https://github.com/fil04331/FilAgent/pull/{NUM}
2. Ajouter un commentaire expliquant la fermeture
3. Cliquer "Close pull request"

# Commentaire type pour doublons
# "Cette PR est fermée car elle est redondante avec #118 qui a été fusionnée.
#  Les correctifs ComplianceGuardian sont maintenant intégrés dans main."

# Commentaire type pour #107 (tests/docs)
# "Cette PR est fermée. Les tests et documentation seront gérés dans des issues
#  séparées (voir #XXX). Merci pour votre contribution!"
```

**Alternative CLI**:
```bash
# Fermer les PRs redondantes
gh pr close 114 --comment "Fermée: redondante avec #118 (déjà fusionnée)"
gh pr close 110 --comment "Fermée: modifications dépendances dépassées"
gh pr close 104 --comment "Fermée: redondante ou dépassée"
gh pr close 117 --comment "Fermée: redondante ou dépassée"
gh pr close 116 --comment "Fermée: redondante ou dépassée"
gh pr close 108 --comment "Fermée: tests/docs à gérer séparément (voir issues)"
gh pr close 107 --comment "Fermée: tests/docs extraits en issues séparées (#XXX, #YYY)"
```

---

### Phase 3: Fusion Nettoyage (PR #112)
**Priorité**: 🟢 MOYENNE - Après #118

**PR #112**: Nettoyage scripts obsolètes
- **Raison**: Maintenance et clarté du code
- **Condition**: Attendre que #118 soit fusionnée

**Action**:
```bash
# Via GitHub Web UI
1. Aller sur https://github.com/fil04331/FilAgent/pull/112
2. Vérifier qu'il n'y a pas de conflits avec #118 fusionnée
3. Vérifier que les tests passent
4. Merger avec "Squash and merge"

# Via CLI
gh pr view 112
gh pr checks 112
gh pr merge 112 --squash --delete-branch
```

---

### Phase 4: Fusion Dependabot (PRs #105 & #106)
**Priorité**: 🟢 MOYENNE - Après #118 et #112

**PR #105 & #106**: Mises à jour GitHub Actions
- **Raison**: Sécurité et mises à jour dépendances
- **Condition**: Vérifier pas de conflits avec #118

**Actions**:
```bash
# Pour chaque PR Dependabot
1. Vérifier les changements (généralement sûrs)
2. Vérifier que les tests CI passent
3. Merger

# Via CLI
gh pr merge 105 --squash --delete-branch
gh pr merge 106 --squash --delete-branch
```

---

## 📝 Phase 5: Création des Issues

### Issue 1: Tests Automatisés (inspiré de #107)

**Titre**: Ajouter tests automatisés pour renforcer la couverture

**Description**:
```markdown
## Contexte
Suite à la fermeture de #107, extraire les tests utiles pour renforcer la couverture.

## Objectifs
- [ ] Ajouter tests unitaires pour ComplianceGuardian
- [ ] Ajouter tests d'intégration pour HTN Planning
- [ ] Améliorer couverture tests middleware (logging, provenance, etc.)
- [ ] Ajouter tests de régression pour bugs connus

## Référence
- PR #107 (fermée, mais contient des tests à extraire)
- Documentation: tests/README_E2E_COMPLIANCE.md

## Critères d'Acceptation
- Couverture de tests > 80%
- Tous les tests passent en CI
- Documentation des nouveaux tests

## Labels
- `testing`
- `enhancement`
- `good first issue`
```

**Commande CLI**:
```bash
gh issue create --title "Ajouter tests automatisés pour renforcer la couverture" \
  --body-file scripts/issue_tests.md \
  --label "testing,enhancement,good first issue"
```

---

### Issue 2: Intégration Benchmarks

**Titre**: Intégrer benchmarks HumanEval, MBPP et SWE-bench pour évaluation continue

**Description**:
```markdown
## Contexte
Conformément à la vision du projet (eval/benchmarks/), intégrer les benchmarks standards
pour valider les capacités de l'agent.

## Objectifs
- [ ] Intégrer HumanEval avec harness de reproduction pass@k
- [ ] Intégrer MBPP (Python benchmark)
- [ ] Intégrer SWE-bench-lite (agent tasks)
- [ ] Configurer seuils d'acceptation dans config/eval_targets.yaml
- [ ] Ajouter CI job pour exécution automatique des benchmarks

## Critères de Succès
Selon eval_targets.yaml et vision projet:
- HumanEval pass@1 ≥ baseline cible
- MBPP ≥ baseline
- SWE-bench-lite ≥ baseline
- Temps moyen ≤ baseline +10%

## Référence
- eval/benchmarks/ (structure existante)
- config/eval_targets.yaml
- Documentation Notion: Vision long terme

## Labels
- `evaluation`
- `benchmark`
- `enhancement`
- `high priority`
```

**Commande CLI**:
```bash
gh issue create --title "Intégrer benchmarks HumanEval, MBPP et SWE-bench" \
  --body-file scripts/issue_benchmarks.md \
  --label "evaluation,benchmark,enhancement,high priority"
```

---

### Issue 3: Extension Policy Engine et RBAC

**Titre**: Étendre policy engine et implémenter RBAC complet avec redaction PII

**Description**:
```markdown
## Contexte
Vision du projet: policy engine complet avec RBAC, PII redaction, JSONSchema validation,
et guardrails de sécurité.

## Objectifs

### Phase 1: Policy Engine Core
- [ ] Implémenter JSONSchema validation pour outputs
- [ ] Ajouter regex/allowlist pour commandes shell
- [ ] Créer post-validators spécifiques (sécurité, conformité)
- [ ] Refus dur si validation échoue

### Phase 2: RBAC Complet
- [ ] Définir rôles et permissions (config/policies.yaml)
- [ ] Implémenter contrôle d'accès par rôle
- [ ] Ajouter journalisation des accès
- [ ] Justification obligatoire pour accès sensibles

### Phase 3: PII Redaction Avancée
- [ ] Étendre détecteurs PII (emails, téléphones, SSN, etc.)
- [ ] Masquage configurable par type de PII
- [ ] Validation avant vectorisation (mémoire sémantique)
- [ ] Tests de non-régression PII

### Phase 4: Guardrails
- [ ] Anti-prompt-injection
- [ ] Détection tentatives jailbreak
- [ ] Limites de ressources (CPU, mémoire, temps)
- [ ] Circuit breakers et fallbacks

## Référence
- policy/ (structure existante)
- runtime/middleware/rbac.py
- runtime/middleware/redaction.py
- config/policies.yaml

## Critères d'Acceptation
- 100% des actions sensibles protégées par RBAC
- PII jamais exposée dans logs
- Validation outputs stricte (JSONSchema)
- Tests de sécurité passent (red teaming)

## Labels
- `security`
- `compliance`
- `enhancement`
- `high priority`
```

**Commande CLI**:
```bash
gh issue create --title "Étendre policy engine et RBAC complet" \
  --body-file scripts/issue_policy_engine.md \
  --label "security,compliance,enhancement,high priority"
```

---

## 📊 Checklist de Vérification

Après chaque fusion, vérifier:

### Après PR #118
- [ ] Branch `main` mise à jour
- [ ] Tests CI passent sur `main`
- [ ] Aucune régression détectée
- [ ] ComplianceGuardian fonctionne correctement
- [ ] Documentation à jour

### Après Fermeture des PRs Redondantes
- [ ] Issues créées pour préserver travail utile de #107
- [ ] Commentaires explicatifs ajoutés à chaque PR fermée
- [ ] Aucune PR oubliée

### Après PR #112
- [ ] Scripts obsolètes supprimés
- [ ] Aucune dépendance cassée
- [ ] Tests passent

### Après PRs Dependabot (#105, #106)
- [ ] GitHub Actions à jour
- [ ] Workflows CI fonctionnent
- [ ] Aucune vulnérabilité connue

### Issues Créées
- [ ] Issue tests automatisés créée
- [ ] Issue benchmarks créée
- [ ] Issue policy engine créée
- [ ] Toutes les issues ont labels appropriés
- [ ] Toutes les issues liées aux PRs fermées

---

## 🎯 Résultat Final Attendu

Après exécution complète du plan:

1. ✅ **Code Base Stable**
   - Bug ComplianceGuardian corrigé
   - Sécurité renforcée (PII redaction, logs)
   - Scripts obsolètes supprimés
   - Dépendances à jour

2. ✅ **PRs Nettoyées**
   - PRs redondantes fermées
   - Historique Git propre
   - Aucun doublon

3. ✅ **Roadmap Claire**
   - Issues créées pour prochaines étapes
   - Priorités définies
   - Travail utile préservé

4. ✅ **Conformité Vision Projet**
   - Sécurité et conformité en priorité
   - Architecture modulaire préservée
   - Traçabilité maintenue

---

## 🚨 Points de Vigilance

### Avant Fusion #118
- Vérifier que TOUS les tests passent
- Reviewer les changements de sécurité
- Valider que la configuration est compatible

### Avant Fermeture #107
- EXTRAIRE les tests/docs utiles en issues
- NE PAS perdre de travail de qualité
- Créer issues AVANT de fermer la PR

### Conflits Potentiels
- #112 pourrait avoir conflits avec #118 → Résoudre avant fusion
- Dependabot PRs généralement sans conflits
- Si conflits: rebaser ou merger main dans la PR

---

## 📞 Aide

Si problèmes durant l'exécution:

1. **Tests échouent après #118**
   - Vérifier logs CI
   - Checker compatibilité configuration
   - Rollback si critique: `git revert <commit>`

2. **Conflits de merge**
   - Résoudre manuellement
   - Tester localement avant push
   - Demander review si incertain

3. **Questions sur fermeture PR**
   - Vérifier qu'aucun travail utile n'est perdu
   - Créer issue si doute
   - Expliquer clairement dans commentaire

---

**Ce plan suit strictement l'ordre: Core → Client-facing → Cosmétique**
**Priorité absolue: Sécurité et Conformité**
