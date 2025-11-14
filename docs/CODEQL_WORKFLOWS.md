# Documentation des Workflows CodeQL - FilAgent

## Vue d'ensemble

FilAgent utilise deux workflows CodeQL complémentaires pour assurer une analyse de sécurité complète et rigoureuse du code Python.

## Workflows configurés

### 1. CodeQL Advanced (`.github/workflows/codeql.yml`)

**Objectif**: Analyse standard et complète du code avec CodeQL.

**Configuration**:
- **Langage**: Python
- **Build mode**: `none` (pas de compilation nécessaire)
- **Version Python**: 3.12
- **Déclencheurs**:
  - Push vers la branche `main`
  - Pull requests vers la branche `main`
  - Scan hebdomadaire: samedi à 6h22 UTC

**Caractéristiques**:
- Utilise les queries CodeQL par défaut
- Installation complète des dépendances via `requirements.txt`
- Analyse automatique sans build manuel
- Catégorisation des résultats par langage

### 2. Analyse Sécurité (`.github/workflows/codeql-security.yml`)

**Objectif**: Analyse de sécurité approfondie avec queries avancées et vérifications personnalisées.

**Configuration**:
- **Langage**: Python
- **Queries**: `security-and-quality` (queries avancées)
- **Version Python**: 3.12
- **Déclencheurs**:
  - Push vers la branche `main`
  - Pull requests vers la branche `main`
  - Scan hebdomadaire: dimanche à 3h00 UTC

**Caractéristiques**:
- Queries de sécurité avancées (`security-and-quality`)
- Vérifications personnalisées de sécurité:
  - Détection de secrets potentiels (api_key, secret_key, password)
  - Validation de la configuration du sandbox
  - Exclusion des fichiers de configuration et de test
- Installation complète des dépendances via `requirements.txt`

## Couverture du code

### Chemins analysés

Les deux workflows analysent **l'intégralité du repository** sans restrictions de chemins. Cette configuration est appropriée pour un projet de sécurité comme FilAgent.

**Répertoires critiques couverts** (66 fichiers Python au total):

| Répertoire | Fichiers | Description |
|-----------|----------|-------------|
| `runtime/` | 13 | Agent principal, serveur FastAPI, middleware |
| `tools/` | 6 | Outils et sandbox Python sécurisé |
| `memory/` | 4 | Gestion de la mémoire épisodique et sémantique |
| `planner/` | 9 | Planificateur et compliance guardian |
| `eval/` | 4 | Benchmarks et évaluation |
| `tests/` | 24 | Suite de tests complète |
| `scripts/` | 4 | Scripts d'administration |
| `examples/` | 1 | Exemples d'intégration |
| `audit/` | 1 | Scripts d'audit |

### Composants critiques pour la sécurité

Les workflows CodeQL analysent tous les composants critiques de FilAgent:

- ✅ `runtime/agent.py` - Agent LLM principal
- ✅ `runtime/server.py` - Serveur API FastAPI
- ✅ `runtime/middleware/*` - Middleware de sécurité (RBAC, WORM, provenance)
- ✅ `tools/python_sandbox.py` - Sandbox d'exécution sécurisé
- ✅ `memory/episodic.py` - Gestion de la mémoire avec SQLite
- ✅ `planner/compliance_guardian.py` - Gardien de conformité

## Compatibilité avec le stack

### Stack technique FilAgent
- **Langage**: Python 3.10+
- **Type**: Interprété (pas de compilation)
- **Dépendances**: `requirements.txt`
- **Framework**: FastAPI pour l'API REST

### Configuration CodeQL appropriée
- ✅ Build mode `none` (approprié pour Python)
- ✅ Installation automatique des dépendances
- ✅ Version Python 3.12 (compatible avec le projet)
- ✅ Analyse complète sans exclusions

## Stratégie de défense en profondeur

Les deux workflows sont **complémentaires** et offrent une couverture de sécurité multi-niveaux:

1. **CodeQL Advanced**:
   - Détection des vulnérabilités courantes
   - Analyse de qualité du code
   - Scan hebdomadaire le samedi

2. **Analyse Sécurité**:
   - Queries de sécurité avancées
   - Détection de secrets et credentials
   - Validation du sandbox
   - Scan hebdomadaire le dimanche

Cette stratégie garantit:
- Deux analyses indépendantes par semaine
- Couverture complète des patterns de sécurité
- Détection rapide lors des push et PR
- Vérifications personnalisées spécifiques à FilAgent

## Maintenance et mises à jour

### Actions GitHub utilisées
- `actions/checkout@v5` - Checkout du code
- `actions/setup-python@v6` - Configuration Python
- `github/codeql-action/init@v4` - Initialisation CodeQL
- `github/codeql-action/analyze@v4` - Analyse CodeQL

### Mise à jour des versions
Les versions des actions sont explicitement épinglées (v4, v5, v6) pour garantir la reproductibilité. Vérifier régulièrement les mises à jour de sécurité.

## Interprétation des résultats

### Où trouver les résultats
- GitHub Security tab > Code scanning alerts
- Dans chaque PR (checks CodeQL)
- Notifications par email si configuré

### Types d'alertes
- **Critical/High**: À corriger immédiatement
- **Medium**: À examiner et planifier
- **Low**: À évaluer selon le contexte
- **Note/Warning**: Suggestions d'amélioration

### False positives
Si CodeQL signale un faux positif:
1. Évaluer si c'est réellement un faux positif
2. Ajouter un commentaire explicatif dans le code
3. Marquer l'alerte comme "dismissed" dans GitHub avec justification

## Conformité réglementaire

Ces workflows contribuent à la conformité de FilAgent avec:
- **Loi 25 (Québec)**: Sécurité des données personnelles
- **EU AI Act**: Validation de la sécurité des systèmes IA
- **NIST AI RMF**: Gestion des risques et traçabilité

## Troubleshooting

### Le workflow échoue avec "Unable to build"
- Vérifier que `requirements.txt` est à jour
- S'assurer que build mode est `none` pour Python

### Timeout du workflow
- Réduire le nombre de dépendances si possible
- Considérer l'utilisation de cache pour pip

### Trop de faux positifs
- Ajuster les queries dans la configuration
- Ajouter des suppressions avec justification

## Références

- [CodeQL Documentation](https://codeql.github.com/docs/)
- [GitHub Code Scanning](https://docs.github.com/en/code-security/code-scanning)
- [CodeQL for Python](https://codeql.github.com/docs/codeql-language-guides/codeql-for-python/)
- [Security Queries](https://github.com/github/codeql/tree/main/python/ql/src/Security)

## Historique des modifications

- **2025-11-14**: Harmonisation des versions Python vers 3.12 dans les deux workflows
- **2025-11-14**: Création de cette documentation
