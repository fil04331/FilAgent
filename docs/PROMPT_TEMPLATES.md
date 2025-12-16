# Guide des Templates de Prompts FilAgent

Ce guide explique le système de templates de prompts de FilAgent, basé sur Jinja2.

## Table des Matières

1. [Vue d'ensemble](#vue-densemble)
2. [Architecture](#architecture)
3. [Utilisation](#utilisation)
4. [Versioning](#versioning)
5. [Création de Templates](#création-de-templates)
6. [Tests](#tests)
7. [Migration et Rollback](#migration-et-rollback)
8. [Meilleures Pratiques](#meilleures-pratiques)

## Vue d'ensemble

### Pourquoi des Templates?

**Avant** (prompts hardcodés dans le code):
```python
# runtime/context_builder.py
def build_system_prompt(self, tools):
    return f"""Tu es FilAgent...
    OUTILS: {tools}
    ..."""
```

**Problèmes**:
- ❌ Difficile à maintenir (prompts éparpillés dans le code)
- ❌ Impossible de faire de l'A/B testing
- ❌ Pas de versioning des prompts
- ❌ Difficile de collaborer sur les prompts (merge conflicts)

**Après** (templates Jinja2):
```python
# runtime/context_builder.py
def build_system_prompt(self, tools):
    return self.template_loader.render('system_prompt', tools=tools)
```

**Avantages**:
- ✅ Templates séparés du code (faciles à éditer)
- ✅ Versioning complet (v1, v2, etc.)
- ✅ A/B testing possible
- ✅ Collaboration facilitée
- ✅ Fallback automatique en cas d'erreur

## Architecture

### Structure des Dossiers

```
prompts/
├── README.md                          # Documentation des templates
└── templates/
    ├── v1/                            # Version 1 (actuelle)
    │   ├── system_prompt.j2           # Prompt système FilAgent
    │   ├── planner_decomposition.j2   # Prompt système planner HTN
    │   └── planner_user_prompt.j2     # Prompt utilisateur planner
    └── v2/                            # Version 2 (future)
        └── ...
```

### Composants

1. **TemplateLoader** (`runtime/template_loader.py`)
   - Charge et met en cache les templates Jinja2
   - Supporte le versioning
   - Singleton pattern pour performance

2. **ContextBuilder** (`runtime/context_builder.py`)
   - Utilise TemplateLoader pour générer les prompts système
   - Fallback automatique si template échoue

3. **HierarchicalPlanner** (`planner/planner.py`)
   - Utilise TemplateLoader pour les prompts de décomposition
   - Fallback automatique

## Utilisation

### Utilisation Basique

```python
from runtime.template_loader import get_template_loader

# Obtenir le loader (singleton)
loader = get_template_loader()

# Rendre un template simple
prompt = loader.render('planner_decomposition')

# Rendre avec variables
prompt = loader.render('system_prompt', 
                      tools="tool1, tool2",
                      semantic_context="[Context]")
```

### Utilisation avec ContextBuilder

```python
from runtime.context_builder import ContextBuilder

# Créer builder (utilise v1 par défaut)
builder = ContextBuilder()

# Générer prompt système
prompt = builder.build_system_prompt(tool_registry)
```

### Utilisation avec Planner

```python
from planner.planner import HierarchicalPlanner

# Créer planner (utilise v1 par défaut)
planner = HierarchicalPlanner()

# Les prompts sont générés automatiquement
result = planner.plan(query="Analyser données...")
```

### Utilisation avec Version Personnalisée

```python
# Utiliser version spécifique
loader = get_template_loader(version='v2')

# Builder avec version personnalisée
builder = ContextBuilder(template_version='v2')

# Planner avec version personnalisée
planner = HierarchicalPlanner(template_version='v2')
```

## Versioning

### Versions Disponibles

- **v1**: Version actuelle (extraite du code original)
  - Templates stables et testés
  - Production-ready

- **v2+**: Versions futures
  - Expérimentation et A/B testing
  - Améliorations progressives

### Créer une Nouvelle Version

1. **Copier la version existante**:
```bash
cp -r prompts/templates/v1 prompts/templates/v2
```

2. **Modifier les templates** dans `v2/`

3. **Tester la nouvelle version**:
```python
loader = get_template_loader(version='v2')
prompt = loader.render('system_prompt', tools="...")
```

4. **Déployer en production** (configurer dans `config/agent.yaml`):
```yaml
prompts:
  default_version: "v2"
```

### Rollback

Si la v2 pose problème:

```python
# Code
loader = get_template_loader(version='v1', force_reload=True)

# Ou configuration
# config/agent.yaml
prompts:
  default_version: "v1"
```

## Création de Templates

### Syntaxe Jinja2

#### Variables
```jinja2
Bonjour {{ name }}!
```

#### Conditions
```jinja2
{% if show_section %}
SECTION:
{{ section_content }}
{% endif %}
```

#### Boucles
```jinja2
{% for tool in tools %}
- {{ tool.name }}: {{ tool.description }}
{% endfor %}
```

#### Commentaires
```jinja2
{# Ceci est un commentaire, ignoré lors du rendu #}
```

### Template system_prompt.j2

**Variables requises**:
- `tools` (str): Description des outils disponibles

**Variables optionnelles**:
- `semantic_context` (str): Contexte sémantique additionnel

**Exemple**:
```jinja2
Tu es {{ agent_name }}.

OUTILS DISPONIBLES:
{{ tools }}

{% if semantic_context %}
CONTEXTE ADDITIONNEL:
{{ semantic_context }}
{% endif %}
```

### Template planner_decomposition.j2

**Variables**: Aucune (prompt système statique)

**Contenu**: Instructions pour la décomposition de tâches

### Template planner_user_prompt.j2

**Variables requises**:
- `query` (str): Requête utilisateur à décomposer
- `available_actions` (str): Liste des actions disponibles

**Exemple**:
```jinja2
Décompose cette requête: {{ query }}

Actions disponibles: {{ available_actions }}
```

## Tests

### Tests Unitaires

```bash
# Tests du template loader
pytest tests/test_template_loader.py -v

# Tests du context builder avec templates
pytest tests/test_context_builder_templates.py -v

# Tests d'intégration
pytest tests/test_template_integration.py -v
```

### Tests Manuels

```python
# Tester rendu d'un template
from runtime.template_loader import get_template_loader

loader = get_template_loader()
prompt = loader.render('system_prompt', tools="test")
print(prompt)
```

### Vérifier les Templates

```python
# Lister templates disponibles
loader = get_template_loader()
print(loader.list_templates())
# ['planner_decomposition', 'planner_user_prompt', 'system_prompt']

# Obtenir le chemin d'un template
path = loader.get_template_path('system_prompt')
print(path)
# .../prompts/templates/v1/system_prompt.j2
```

## Migration et Rollback

### Scénario: Déploiement v2 en Production

1. **Développement**:
```bash
# Créer v2
mkdir prompts/templates/v2
cp prompts/templates/v1/*.j2 prompts/templates/v2/

# Éditer v2
vim prompts/templates/v2/system_prompt.j2
```

2. **Tests locaux**:
```python
# Tester v2
builder = ContextBuilder(template_version='v2')
prompt = builder.build_system_prompt(registry)
# Vérifier le prompt
```

3. **A/B Testing**:
```python
# 50% trafic v1, 50% trafic v2
import random
version = random.choice(['v1', 'v2'])
builder = ContextBuilder(template_version=version)
```

4. **Déploiement complet**:
```python
# Tous les utilisateurs sur v2
builder = ContextBuilder(template_version='v2')
```

5. **Rollback si problème**:
```python
# Retour à v1
builder = ContextBuilder(template_version='v1')
```

## Meilleures Pratiques

### 1. Garder les Templates Simples

✅ **Bon**:
```jinja2
Tu es FilAgent.
OUTILS: {{ tools }}
```

❌ **Mauvais**:
```jinja2
{% for tool in tools %}
  {% if tool.category == 'pme' %}
    {% for param in tool.params %}
      ...
    {% endfor %}
  {% endif %}
{% endfor %}
```

**Raison**: La logique complexe doit rester dans le code Python, pas dans les templates.

### 2. Variables Optionnelles

✅ **Bon**:
```jinja2
{% if semantic_context %}
CONTEXTE: {{ semantic_context }}
{% endif %}
```

❌ **Mauvais**:
```jinja2
CONTEXTE: {{ semantic_context }}
{# Crash si semantic_context n'est pas fourni #}
```

### 3. Documentation

Chaque template doit être documenté dans `prompts/README.md`:

```markdown
### system_prompt.j2
Description: Prompt système principal
Variables:
- tools (requis): Description des outils
- semantic_context (optionnel): Contexte additionnel
```

### 4. Nommage

- Format: `<composant>_<fonction>.j2`
- Exemples: `system_prompt.j2`, `planner_decomposition.j2`
- Toujours en minuscules avec underscores

### 5. Versioning Sémantique

- **v1.0**: Version stable initiale
- **v1.1**: Améliorations mineures (compatible)
- **v2.0**: Changements majeurs (peut casser la compatibilité)

### 6. Tests Avant Déploiement

Toujours tester:
- ✅ Syntaxe Jinja2 valide
- ✅ Toutes les variables requises fournies
- ✅ Output cohérent avec l'attendu
- ✅ Pas de régression par rapport à v1

### 7. Fallback

Le code doit toujours avoir un fallback:

```python
try:
    prompt = loader.render('system_prompt', tools=tools)
except Exception as e:
    print(f"Warning: Template error, using fallback: {e}")
    prompt = self._build_system_prompt_fallback(tools)
```

### 8. Performance

- Templates sont mis en cache automatiquement
- Éviter de recharger inutilement: `loader.reload_templates()`
- Utiliser le singleton: `get_template_loader()`

## Dépannage

### Erreur: Template not found

**Symptôme**:
```
jinja2.exceptions.TemplateNotFound: system_prompt
```

**Solutions**:
1. Vérifier que le fichier existe: `prompts/templates/v1/system_prompt.j2`
2. Vérifier le nom (sans `.j2`)
3. Vérifier la version: `loader = get_template_loader(version='v1')`

### Erreur: Missing variable

**Symptôme**:
```
jinja2.exceptions.UndefinedError: 'tools' is undefined
```

**Solutions**:
1. Fournir la variable: `loader.render('system_prompt', tools="...")`
2. Rendre la variable optionnelle: `{% if tools %}{{ tools }}{% endif %}`

### Prompts vides ou incomplets

**Symptôme**: Le prompt généré est trop court

**Solutions**:
1. Vérifier les variables fournies
2. Vérifier les conditions `{% if %}`
3. Utiliser `print(prompt)` pour déboguer

### Performance dégradée

**Symptôme**: Génération de prompts lente

**Solutions**:
1. Vérifier que le caching fonctionne
2. Ne pas recharger les templates: `loader.reload_templates()`
3. Utiliser le singleton: `get_template_loader()`

## Ressources

- [Documentation Jinja2](https://jinja.palletsprojects.com/)
- [Code TemplateLoader](../runtime/template_loader.py)
- [Tests](../tests/test_template_loader.py)
- [README Templates](../prompts/README.md)

## Support

Pour toute question:
- Consulter les tests: `tests/test_template_*.py`
- Lire le code: `runtime/template_loader.py`
- Vérifier les templates: `prompts/templates/v1/`
