# Mutation Testing avec Mutmut

## Vue d'ensemble

Le **mutation testing** est une technique avancée de validation de la qualité des tests. Elle consiste à introduire des mutations (modifications) dans le code source et à vérifier que les tests détectent ces changements. Si un test ne détecte pas une mutation, cela signifie que le test n'est pas assez robuste.

## Philosophie

> "Si ce n'est pas testé, c'est cassé"

Le mutation testing nous aide à garantir que nos tests sont réellement efficaces et ne sont pas des "tests verts" artificiels qui passent sans vérifier vraiment le comportement du code.

## Installation

Mutmut est inclus dans les dépendances de développement. Pour l'installer :

```bash
pdm install
```

## Configuration

La configuration de mutmut est définie dans `pyproject.toml` sous la section `[tool.mutmut]` :

```toml
[tool.mutmut]
paths_to_mutate = [
    "runtime/",
    "planner/",
    "tools/",
    "memory/",
    "policy/",
]

paths_to_exclude = [
    "tests/",
    "gradio_app*.py",
    "mcp_server.py",
    "examples/",
    "scripts/",
]

runner = "pytest"
test_command = "pytest -x --tb=short -q"
```

## Utilisation

### Lancer le mutation testing

Pour lancer une campagne de mutation testing complète :

```bash
pdm run mutate
```

Cette commande va :
1. Analyser le code dans les chemins configurés
2. Générer des mutations (modifications du code)
3. Exécuter les tests pour chaque mutation
4. Rapporter les résultats

⚠️ **Attention** : Le mutation testing peut prendre beaucoup de temps (plusieurs heures pour un projet complet).

### Lancer sur un fichier spécifique

Pour tester un fichier particulier :

```bash
mutmut run --paths-to-mutate=runtime/agent.py
```

### Voir les résultats

Pour afficher un résumé des résultats :

```bash
pdm run mutate-results
```

Pour voir les détails d'un mutant spécifique :

```bash
pdm run mutate-show <mutant-id>
```

Exemple :
```bash
pdm run mutate-show 42
```

### Générer un rapport HTML

Pour générer un rapport HTML interactif :

```bash
pdm run mutate-html
```

Le rapport sera disponible dans `html/index.html`.

## Interprétation des résultats

### États des mutants

- **Killed** (Tué) : ✅ Le test a détecté la mutation. C'est le résultat souhaité.
- **Survived** (Survécu) : ❌ Le test n'a pas détecté la mutation. Il faut améliorer le test.
- **Timeout** : ⏱️ Le test a pris trop de temps. Peut indiquer un problème de performance.
- **Suspicious** : 🤔 Le mutant a produit un comportement inattendu.

### Objectif de couverture

Un bon projet devrait avoir un **taux de mutants tués > 80%**. Cela signifie que 80% des mutations introduites sont détectées par les tests.

## Exemples de mutations

Mutmut peut introduire plusieurs types de mutations :

### 1. Opérateurs arithmétiques
```python
# Original
result = a + b

# Mutation
result = a - b
```

### 2. Opérateurs de comparaison
```python
# Original
if x > 10:

# Mutation
if x >= 10:
```

### 3. Constantes
```python
# Original
timeout = 30

# Mutation
timeout = 31
```

### 4. Conditions booléennes
```python
# Original
if condition and other_condition:

# Mutation
if condition or other_condition:
```

## Workflow recommandé

### 1. Développement initial
- Écrire le code
- Écrire les tests
- Atteindre 80% de couverture de code

### 2. Validation par mutation testing
- Lancer mutmut sur le nouveau code
- Identifier les mutants survivants
- Améliorer les tests pour tuer ces mutants
- Re-lancer mutmut pour vérifier

### 3. Maintenance continue
- Lancer mutmut périodiquement (hebdomadaire/mensuel)
- Intégrer dans le processus de revue de code
- Garder un taux de mutants tués > 80%

## Bonnes pratiques

### ✅ À faire

1. **Commencer petit** : Tester un module à la fois
2. **Prioriser** : Se concentrer sur le code critique (runtime, policy)
3. **Itérer** : Améliorer progressivement les tests
4. **Documenter** : Noter pourquoi certains mutants survivent légitimement

### ❌ À éviter

1. **Ne pas modifier le code pour tuer les mutants** : Les tests doivent valider le comportement, pas juste passer
2. **Ne pas désactiver des assertions** : C'est du greenwashing de tests
3. **Ne pas ignorer les timeouts** : Ils peuvent révéler des problèmes de performance

## Cas spéciaux

### Mutants équivalents

Certains mutants sont **équivalents** au code original et ne peuvent pas être détectés :

```python
# Original
x = y + 0

# Mutation équivalente
x = y - 0  # Même résultat mathématique
```

Dans ce cas, il est acceptable que le mutant survive.

### Code de configuration

Le code de configuration (lecture de YAML, etc.) peut être difficile à tester avec mutation testing. On peut l'exclure avec `paths_to_exclude`.

## Intégration CI/CD (Future)

Pour l'instant, le mutation testing est manuel. Dans une future itération, on pourra :

1. Ajouter un job CI pour mutation testing incrémental
2. Ne tester que les fichiers modifiés
3. Bloquer les PRs si le taux de mutants tués baisse

## Ressources

- [Documentation Mutmut](https://mutmut.readthedocs.io/)
- [Mutation Testing Best Practices](https://pedrorijo.com/blog/mutation-testing/)
- [Understanding Mutation Testing](https://stryker-mutator.io/docs/mutation-testing-elements/what-is-mutation-testing/)

## Support

Pour toute question sur le mutation testing dans FilAgent, consulter :
- Cette documentation
- Les issues GitHub du projet
- L'équipe de développement
