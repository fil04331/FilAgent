# Structure de la Documentation FilAgent

**Version** : 2.1.0  
**Dernière mise à jour** : 2025-12-16  
**Auteur** : Équipe Documentation FilAgent

---

## Vue d'ensemble

Ce document décrit la structure organisationnelle complète de la documentation du projet FilAgent, les principes qui la sous-tendent, et les règles à suivre pour maintenir cette organisation.

---

## Philosophie de documentation

### Principes fondamentaux

1. **Minimalisme structuré** : Conserver uniquement la documentation pertinente et active dans les emplacements principaux
2. **Traçabilité historique** : Archiver (ne pas supprimer) les documents ayant une valeur historique
3. **Accessibilité** : Faciliter la découverte rapide de l'information
4. **Cohérence** : Maintenir une structure uniforme et prévisible
5. **Séparation des préoccupations** : Organiser par audience et objectif

---

## Structure des répertoires

```
FilAgent/
├── README.md                    # Point d'entrée principal
├── CHANGELOG.md                 # Historique officiel des versions
├── LICENSE                      # Licence du projet
├── SECURITY.md                  # Politique de sécurité
├── README_SETUP.md              # Guide d'installation rapide
├── CLAUDE.md                    # Guide pour Claude Code
├── AGENTS.md                    # Guidelines pour AI agents
│
├── docs/                        # Documentation active
│   ├── INDEX.md                 # Index complet de la documentation
│   ├── DOCUMENTATION_STRUCTURE.md  # Ce fichier
│   │
│   ├── DEPLOYMENT.md            # Guide de déploiement
│   ├── CONFIGURATION_CAPACITES.md
│   ├── DEPENDENCY_MANAGEMENT.md
│   ├── PDM_QUICK_REFERENCE.md
│   │
│   ├── PERPLEXITY_INTEGRATION.md
│   ├── COMPLIANCE_GUARDIAN.md
│   ├── BENCHMARKS.md
│   │
│   ├── PROMETHEUS_SETUP.md
│   ├── PROMETHEUS_QUICKSTART.md
│   ├── PROMETHEUS_DASHBOARD.md
│   ├── PROMETHEUS_PROMQL_EXAMPLES.md
│   │
│   ├── INTEGRATION_OPENAPI.md
│   ├── OPENAPI_INTEGRATION_SUMMARY.md
│   ├── CODEQL_WORKFLOWS.md
│   ├── CODEQL_VERIFICATION_SUMMARY.md
│   ├── CI_FIX_DOCUMENTATION.md
│   ├── WORM_FINALIZATION_VALIDATION.md
│   │
│   ├── GUIDE_ANALYSEUR_DOCUMENTS.md
│   ├── DEPLOYMENT_DOCUMENT_ANALYZER.md
│   ├── DOCUMENT_ANALYZER_QUICK_START.md
│   ├── GUIDE_SELECTION_MODELES_PERPLEXITY.md
│   │
│   ├── PHASE_6_1_ERROR_HANDLING_SUMMARY.md
│   ├── PHASE_6_2_TESTING_SUMMARY.md
│   ├── PHASE_6_3_COMPLIANCE_REPORT.md
│   │
│   ├── ADRs/                    # Architecture Decision Records
│   │   ├── 001-initial-architecture.md
│   │   ├── 002-decision-records.md
│   │   └── 003-openapi-placement.md
│   │
│   ├── SOPs/                    # Standard Operating Procedures
│   │   ├── incident-response.md
│   │   ├── deployment.md
│   │   ├── backup-recovery.md
│   │   └── security-incident.md
│   │
│   └── archive/                 # Documentation archivée
│       ├── README.md            # Politique d'archivage
│       ├── phases/              # Rapports de phases (0-5)
│       ├── reports/             # Rapports techniques historiques
│       ├── guides/              # Guides consolidés/remplacés
│       └── development/         # Artefacts de développement
│
├── config/                      # Fichiers de configuration
│   ├── agent.yaml
│   ├── policies.yaml
│   ├── retention.yaml
│   ├── provenance.yaml
│   └── eval_targets.yaml
│
└── examples/                    # Exemples d'utilisation
    └── perplexity_example.py
```

---

## Catégories de documentation

### 1. Documentation racine (essentielle)

**Emplacement** : Racine du dépôt (`/`)

**Contenu** :
- Documents essentiels consultés régulièrement
- Points d'entrée pour nouveaux utilisateurs
- Politiques et licences
- Guides pour assistants IA

**Règle** : Limité à 7-10 fichiers maximum

**Documents actuels** :
- `README.md` - Vue d'ensemble et démarrage rapide
- `CHANGELOG.md` - Historique des versions
- `LICENSE` - Licence propriétaire duale
- `SECURITY.md` - Politique de sécurité
- `README_SETUP.md` - Installation rapide
- `CLAUDE.md` - Guide pour Claude Code
- `AGENTS.md` - Guidelines pour AI agents

### 2. Documentation active (`docs/`)

**Emplacement** : `/docs/`

**Contenu** :
- Documentation technique maintenue activement
- Guides d'intégration et déploiement
- Documentation des fonctionnalités
- Guides de configuration
- Documentation d'architecture (ADRs)
- Procédures opérationnelles (SOPs)

**Règle** : Tout document doit être à jour et pertinent pour la version actuelle

**Sous-catégories** :

#### ADRs (`docs/ADRs/`)
- Architecture Decision Records
- Format standardisé pour décisions architecturales
- Numérotation séquentielle (001, 002, 003...)
- Immuables une fois publiés (créer nouveau ADR pour révisions)

#### SOPs (`docs/SOPs/`)
- Standard Operating Procedures
- Procédures opérationnelles critiques
- Runbooks pour incidents
- Guides de déploiement et maintenance

### 3. Documentation archivée (`docs/archive/`)

**Emplacement** : `/docs/archive/`

**Contenu** :
- Documentation historique avec valeur contextuelle
- Rapports de phases de développement complétées
- Guides obsolètes mais référentiellement utiles
- Artefacts de développement temporaires

**Règle** : Documents non modifiés après archivage (préserver l'histoire)

**Sous-catégories** :

#### Phases (`docs/archive/phases/`)
- Rapports de statut par phase de développement
- Documentation de progression historique
- `STATUS_PHASE0.md` à `STATUS_PHASE5.md`
- `STATUS_FALLBACKS.md` et autres documents de statut

#### Reports (`docs/archive/reports/`)
- Rapports d'audit historiques
- Analyses de code et couverture passées
- Rapports de benchmarks antérieurs
- Synthèses techniques diverses

#### Guides (`docs/archive/guides/`)
- Guides utilisateur consolidés ou remplacés
- Versions précédentes de guides de démarrage
- Documentation spécifique à des versions antérieures
- Résumés exécutifs historiques

#### Development (`docs/archive/development/`)
- Task cards et checklists de développement
- Notes de développement temporaires
- Documents de travail non finalisés
- Réponses à questions spécifiques de développement

---

## Critères de placement

### Doit rester dans la racine (`/`)

Un document reste dans la racine si :
- ✅ Il est consulté fréquemment par les nouveaux arrivants
- ✅ Il définit des règles/politiques applicables à tout le projet
- ✅ Il sert de point d'entrée principal
- ✅ Il est maintenu activement et à jour
- ✅ Il a une valeur légale/contractuelle (LICENSE, SECURITY)

### Doit être dans `docs/`

Un document va dans `docs/` si :
- ✅ Il documente une fonctionnalité ou intégration spécifique
- ✅ Il est technique et détaillé
- ✅ Il est maintenu activement
- ✅ Il s'adresse à un public technique spécifique
- ✅ Il fait partie d'un ensemble de documents (ADRs, SOPs)

### Doit être archivé (`docs/archive/`)

Un document est archivé si :
- ✅ Il documente une phase ou version passée
- ✅ Il a été remplacé par une version plus récente
- ✅ Son contenu est obsolète mais historiquement pertinent
- ✅ Il était temporaire et a accompli son objectif
- ✅ Il a une valeur de référence contextuelle

### Doit être supprimé

Un document est supprimé (non archivé) si :
- ❌ C'est un vrai doublon sans valeur historique
- ❌ Il contient des informations erronées sans valeur de référence
- ❌ Il est complètement obsolète sans contexte historique utile
- ❌ Il était généré automatiquement et recréable

---

## Processus de maintenance

### Ajout de nouveau document

1. **Identifier la catégorie appropriée** selon les critères ci-dessus
2. **Choisir un nom descriptif** :
   - Éviter les noms génériques (`GUIDE.md`, `DOC.md`)
   - Utiliser `SCREAMING_SNAKE_CASE` pour cohérence
   - Inclure le sujet principal dans le nom
3. **Ajouter les métadonnées** :
   ```markdown
   # Titre du Document
   
   **Version** : 1.0.0
   **Dernière mise à jour** : YYYY-MM-DD
   **Auteur** : Nom ou Équipe
   ```
4. **Mettre à jour `docs/INDEX.md`** avec le nouveau document
5. **Ajouter des références croisées** dans les documents liés
6. **Documenter dans le CHANGELOG** si c'est un ajout majeur

### Mise à jour de document existant

1. **Mettre à jour la date** dans les métadonnées
2. **Incrémenter la version** si changements significatifs
3. **Documenter les changements** :
   - Dans le CHANGELOG pour documents essentiels
   - Dans le document lui-même pour changements mineurs
4. **Vérifier les références croisées** restent valides
5. **Tester les exemples de code** s'il y en a

### Archivage de document

1. **Vérifier qu'il existe une alternative** à jour ou que le document n'est plus pertinent
2. **Identifier la catégorie d'archive** appropriée
3. **Déplacer avec `git mv`** (préserve l'historique Git)
4. **Mettre à jour `docs/archive/README.md`** si nécessaire
5. **Supprimer les références** dans `docs/INDEX.md` et autres documents
6. **Ajouter une note** dans le CHANGELOG si document majeur
7. **Créer une redirection** si le document était souvent référencé

### Suppression de document

⚠️ **À utiliser avec précaution** - Préférer l'archivage dans la plupart des cas

1. **Confirmer qu'il n'y a pas de valeur historique**
2. **Vérifier qu'aucun document actif** ne le référence
3. **Documenter la suppression** dans le CHANGELOG
4. **Utiliser `git rm`** pour suppression propre

---

## Règles de nommage

### Fichiers Markdown

**Format général** : `SUJET_PRINCIPAL_DESCRIPTIF.md`

**Exemples** :
- ✅ `DEPLOYMENT_DOCUMENT_ANALYZER.md` - Clair et descriptif
- ✅ `PERPLEXITY_INTEGRATION.md` - Sujet spécifique
- ✅ `PROMETHEUS_QUICKSTART.md` - Combinaison sujet + type
- ❌ `GUIDE.md` - Trop générique
- ❌ `doc1.md` - Non descriptif
- ❌ `new_feature.md` - Pas de convention SCREAMING_SNAKE_CASE

**Conventions spéciales** :
- `README.md` - Toujours pour point d'entrée de répertoire
- `CHANGELOG.md` - Format standard
- `LICENSE` - Sans extension
- `SECURITY.md` - Nom standard GitHub

### ADRs (Architecture Decision Records)

**Format** : `NNN-short-title.md`

**Exemples** :
- `001-initial-architecture.md`
- `002-decision-records.md`
- `003-openapi-placement.md`

**Règles** :
- Numérotation séquentielle à 3 chiffres
- Titre court en kebab-case
- Immuables après publication

### SOPs (Standard Operating Procedures)

**Format** : `action-subject.md`

**Exemples** :
- `incident-response.md`
- `backup-recovery.md`
- `deployment.md`

**Règles** :
- Verbe d'action ou processus
- kebab-case
- Orienté action/procédure

---

## Standards de contenu

### Structure de document type

```markdown
# Titre Principal

**Version** : 1.0.0
**Dernière mise à jour** : 2025-12-08
**Auteur** : Équipe ou Nom

---

## Vue d'ensemble

Brève description du sujet (2-3 paragraphes maximum).

---

## Section Principale 1

Contenu...

### Sous-section

Détails...

---

## Section Principale 2

Contenu...

---

## Références

- [Document lié 1](/path/to/doc1.md)
- [Document lié 2](/path/to/doc2.md)
- Ressource externe

---

**Voir aussi** : [Index de la documentation](/docs/INDEX.md)
```

### Éléments obligatoires

1. **Métadonnées en en-tête** :
   - Titre (H1)
   - Version
   - Date de dernière mise à jour
   - Auteur ou équipe responsable

2. **Vue d'ensemble** :
   - Résumé exécutif du contenu
   - Objectif du document
   - Public cible

3. **Structure hiérarchique claire** :
   - H1 pour titre principal (un seul)
   - H2 pour sections principales
   - H3 pour sous-sections
   - Pas plus de 4 niveaux de profondeur

4. **Références** :
   - Liens vers documents connexes
   - Ressources externes si applicables
   - Lien vers INDEX.md

### Style et ton

**Langue** :
- **Français** pour documentation utilisateur et métier
- **Anglais** pour code, commentaires, documentation technique bas niveau

**Ton** :
- Professionnel, neutre, factuel
- Phrases courtes et affirmatives
- Éviter le jargon non expliqué
- Définir les acronymes à première occurrence

**Formatage** :
- Code en blocs avec highlighting : ` ```python `, ` ```yaml `, etc.
- Commandes shell en blocs : ` ```bash `
- Emphase avec **gras** pour termes importants
- Listes à puces pour énumérations
- Tableaux pour comparaisons

---

## Workflow de revue

### Revue de documentation nouvelle ou modifiée

1. **Auto-revue** :
   - [ ] Métadonnées complètes et à jour
   - [ ] Orthographe et grammaire correctes
   - [ ] Liens fonctionnels et à jour
   - [ ] Exemples de code testés
   - [ ] Structure cohérente avec standards

2. **Revue par pair** :
   - [ ] Clarté et complétude
   - [ ] Exactitude technique
   - [ ] Pertinence et utilité
   - [ ] Cohérence avec documentation existante

3. **Mise à jour des indices** :
   - [ ] `docs/INDEX.md` mis à jour
   - [ ] Références croisées ajoutées
   - [ ] CHANGELOG mis à jour si nécessaire

---

## Maintenance continue

### Tâches mensuelles

- [ ] Vérifier que tous les liens dans `docs/INDEX.md` sont valides
- [ ] Mettre à jour les dates "Dernière mise à jour" des documents modifiés
- [ ] Identifier les documents potentiellement obsolètes
- [ ] Vérifier que les exemples de code fonctionnent toujours

### Tâches trimestrielles

- [ ] Audit complet de la structure documentaire
- [ ] Identification des documents à archiver
- [ ] Consolidation de documents redondants
- [ ] Mise à jour de ce document si la structure évolue

### Indicateurs de qualité

**Métriques à suivre** :
- Nombre de fichiers dans la racine (objectif : ≤ 10)
- Nombre de documents avec dates > 6 mois (signal d'obsolescence)
- Nombre de liens brisés (objectif : 0)
- Ratio docs actives / docs archivées (évolution)

---

## Outils et automatisation

### Scripts de maintenance

```bash
# Vérifier les liens brisés
./scripts/check_doc_links.sh

# Lister les documents non à jour
./scripts/list_outdated_docs.sh

# Générer rapport de structure
./scripts/doc_structure_report.sh
```

### Intégration CI/CD

La CI vérifie automatiquement :
- Liens brisés dans documentation
- Format Markdown valide
- Présence de métadonnées obligatoires

---

## Contact et support

**Questions sur la structure documentaire** :
- Ouvrir une issue GitHub avec label `documentation`
- Consulter l'équipe de documentation technique

**Propositions d'amélioration** :
- Pull Request avec modifications proposées
- Discussion dans issue GitHub

---

## Historique des changements

### Version 2.1.0 - 2025-12-16

**Changements majeurs** :
- Archivage de 11 documents temporaires et rapports historiques depuis la racine
- Documents archivés:
  - Rapports de tests: ANALYSE_TESTS_RESUME, COVERAGE_REPORT, TEST_DIAGNOSTIC_REPORT
  - Implémentations: OPENTELEMETRY_IMPLEMENTATION_SUMMARY, SEMANTIC_CACHE_IMPLEMENTATION, TEMPLATE_MIGRATION_SUMMARY
  - Rapports de développement: IMPLEMENTATION_REPORT_DEC8, REFACTORING_SUMMARY
  - Documents de planification: PLAN-ACTION-DEC8, CI_CD_VERIFICATION_CHECKLIST, ARCHITECTURE_OVERVIEW
- Réduction finale de la racine: 17 → 6 fichiers MD essentiels
- Mise à jour de `docs/archive/README.md` avec détails des nouveaux archivages
- Mise à jour de `docs/INDEX.md` version 2.1.0
- Ajout d'entrée dans CHANGELOG.md

**Motivations** :
- Compléter le nettoyage documentaire initié en 2025-12-08
- Archiver les rapports temporaires et documents de développement accomplis
- Maintenir uniquement les documents essentiels et activement maintenus à la racine
- Faciliter l'onboarding des nouveaux contributeurs

### Version 2.0.0 - 2025-12-08

**Changements majeurs** :
- Création de la structure d'archivage `docs/archive/`
- Déplacement de 40+ documents vers archives
- Consolidation de la racine du dépôt (45 → 7 fichiers)
- Création de ce document de référence
- Mise à jour complète de `docs/INDEX.md`

**Motivations** :
- Réduction de la surcharge cognitive pour nouveaux contributeurs
- Meilleure découvrabilité de la documentation active
- Conservation de l'historique et du contexte
- Alignement avec les meilleures pratiques de documentation logicielle

### Version 1.0.0 - 2025-11-16

- Structure initiale de documentation
- Création de `docs/INDEX.md`
- Organisation des ADRs et SOPs

---

## État actuel (2025-12-16)

**Fichiers MD à la racine** : 6
- README.md
- CHANGELOG.md
- SECURITY.md
- README_SETUP.md
- CLAUDE.md
- AGENTS.md

**Documentation active dans docs/** : ~40 fichiers techniques

**Documents archivés dans docs/archive/** : ~60+ documents historiques

**Objectif atteint** : Structure claire, minimaliste et maintenable avec séparation nette entre documentation active et archives historiques.

---

**Maintenu par** : Équipe Documentation Technique FilAgent  
**Dernière revue** : 2025-12-16
