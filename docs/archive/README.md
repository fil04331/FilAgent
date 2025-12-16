# Archive de Documentation FilAgent

## Vue d'ensemble

Ce répertoire contient la documentation archivée du projet FilAgent. Ces documents ont une valeur historique et contextuelle mais ne sont plus activement maintenus ou ne représentent plus l'état actuel du projet.

**Date création** : 2025-12-08  
**Dernière mise à jour** : 2025-12-16

## Structure

```
archive/
├── phases/          # Documents de statut par phase de développement
├── reports/         # Rapports techniques et d'audit historiques
├── guides/          # Guides et tutoriels obsolètes ou remplacés
└── development/     # Documents de développement temporaires
```

## Pourquoi archiver ?

Les documents sont archivés pour les raisons suivantes :

1. **Valeur historique** : Documentent l'évolution du projet et les décisions passées
2. **Référence contextuelle** : Peuvent être utiles pour comprendre pourquoi certaines décisions ont été prises
3. **Réduction du bruit** : Permettent de garder la racine du dépôt propre et focalisée
4. **Traçabilité** : Maintiennent une trace complète de l'historique du projet

## Documents archivés

### Phase Status Reports (`phases/`)

Documents décrivant l'état d'avancement du projet à différentes phases de développement :

- `STATUS_PHASE0.md` - Setup initial
- `STATUS_PHASE1.md` - MVP Agent fonctionnel
- `STATUS_PHASE2.md` - Fondations conformité
- `STATUS_PHASE2_COMPLETE.md` - Phase 2 complétée
- `STATUS_PHASE3.md` - Mémoire avancée
- `STATUS_PHASE4.md` - Policy Engine
- `STATUS_PHASE5.md` - Infrastructure évaluation

**Statut** : Phases complétées, voir CHANGELOG.md pour l'historique officiel

### Rapports Techniques (`reports/`)

Rapports d'analyse, d'audit et de synthèse générés durant le développement :

**Documents archivés (2025-12-16)** :
- `ANALYSE_TESTS_RESUME.md` - Résumé analyse tests (2025-12-10)
- `COVERAGE_REPORT.md` - Rapport couverture de tests (2025-12-08)
- `TEST_DIAGNOSTIC_REPORT.md` - Diagnostic suite de tests (2025-12-10)
- `IMPLEMENTATION_REPORT_DEC8.md` - Rapport d'implémentation (2025-12-08)
- `REFACTORING_SUMMARY.md` - Résumé refactoring Clean Architecture
- `OPENTELEMETRY_IMPLEMENTATION_SUMMARY.md` - Implémentation OpenTelemetry (voir docs/OPENTELEMETRY_USAGE.md)
- `SEMANTIC_CACHE_IMPLEMENTATION.md` - Implémentation cache sémantique (voir docs/SEMANTIC_CACHE.md)
- `TEMPLATE_MIGRATION_SUMMARY.md` - Migration système de templates (voir docs/PROMPT_TEMPLATES.md)

**Rapports historiques antérieurs** :
- Audits de sécurité et conformité
- Analyses de code et couverture
- Rapports de benchmarks et performances
- Synthèses techniques diverses

**Statut** : Remplacés par documentation vivante dans `docs/`

### Guides Archivés (`guides/`)

Guides utilisateur ou développeur qui ont été consolidés ou remplacés :

- Guides complets multiples (consolidés dans README.md)
- Guides de démarrage rapide obsolètes
- Tutoriels spécifiques à des versions antérieures

**Statut** : Voir README.md et docs/ pour documentation à jour

### Documents de Développement (`development/`)

Documents créés durant le développement pour des besoins temporaires :

**Documents archivés (2025-12-16)** :
- `PLAN-ACTION-DEC8.md` - Plan d'action détaillé du 8 décembre (objectifs atteints)
- `CI_CD_VERIFICATION_CHECKLIST.md` - Checklist de vérification CI/CD pour conformité Loi 25 (implémentée)
- `ARCHITECTURE_OVERVIEW.md` - Vue d'ensemble architecture Clean (consolidé dans ADRs)

**Documents historiques antérieurs** :
- Checklists de vérification
- Notes de développement temporaires
- Réponses à des questions spécifiques
- Documents de travail non finalisés

**Statut** : Objectifs atteints ou non pertinents pour utilisateurs finaux

## Documents conservés dans la racine

Les documents suivants restent dans la racine du dépôt car ils sont essentiels et activement maintenus :

- **README.md** - Point d'entrée principal du projet
- **CHANGELOG.md** - Historique officiel des versions et changements
- **LICENSE** - Licence du projet
- **SECURITY.md** - Politique de sécurité et signalement de vulnérabilités
- **README_SETUP.md** - Guide d'installation rapide

## Documents dans `docs/`

La documentation active et maintenue se trouve dans le répertoire `docs/` :

- **docs/INDEX.md** - Index de toute la documentation
- **docs/ADRs/** - Architecture Decision Records (décisions architecturales)
- **docs/SOPs/** - Standard Operating Procedures (procédures opérationnelles)
- **docs/*.md** - Guides techniques spécifiques

## Comment utiliser cette archive

### Rechercher une information historique

1. Consultez d'abord la documentation active dans `docs/`
2. Si l'information concerne une phase spécifique du développement, voir `phases/`
3. Pour comprendre une décision passée, voir `reports/` et les ADRs dans `docs/ADRs/`

### Restaurer un document

Si un document archivé doit être réactivé :

1. Vérifier qu'il n'existe pas une version plus récente dans `docs/`
2. Mettre à jour le contenu pour refléter l'état actuel du projet
3. Le déplacer vers l'emplacement approprié dans `docs/`
4. Documenter la restauration dans le CHANGELOG.md

## Politique de conservation

### Durée de conservation

Les documents archivés sont conservés indéfiniment pour :

- Traçabilité historique
- Conformité réglementaire (Loi 25, RGPD)
- Référence pour décisions architecturales

### Critères d'archivage

Un document est archivé si :

- ✅ Il documente une phase terminée du projet
- ✅ Il a été remplacé par une version plus récente
- ✅ Son contenu est obsolète mais historiquement pertinent
- ✅ Il était temporaire et a accompli son objectif

Un document est supprimé (non archivé) si :

- ❌ C'est un vrai doublon sans valeur historique
- ❌ Il contient des informations erronées sans valeur de référence
- ❌ Il est complètement obsolète sans contexte historique utile

## Métadonnées d'archivage

Chaque document archivé conserve :

- Son contenu original (non modifié)
- Sa date de création/dernière modification
- Le contexte de son archivage (via ce README)

## Contact et questions

Pour toute question sur un document archivé :

1. Consultez l'historique Git pour voir l'évolution du document
2. Consultez le CHANGELOG.md pour le contexte de la période
3. Référez-vous aux ADRs dans `docs/ADRs/` pour les décisions architecturales

---

**Note** : Cette archive fait partie intégrante de la stratégie de documentation du projet FilAgent et respecte les principes de gouvernance et traçabilité du projet.
