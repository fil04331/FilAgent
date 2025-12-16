# FilAgent Prompt Templates

Ce dossier contient les templates de prompts système utilisés par FilAgent. Les prompts sont gérés comme du contenu séparé du code pour faciliter la maintenance, le versioning et l'A/B testing.

## Structure

```
prompts/
├── README.md (ce fichier)
└── templates/
    └── v1/
        ├── system_prompt.j2           # Prompt système principal de l'agent
        ├── planner_decomposition.j2   # Prompt système du planificateur HTN
        └── planner_user_prompt.j2     # Prompt utilisateur pour décomposition
```

## Versioning

Les templates sont organisés par version (`v1/`, `v2/`, etc.) pour supporter:
- **A/B testing**: Comparer différentes versions de prompts
- **Rollback**: Revenir à une version précédente si nécessaire
- **Evolution**: Améliorer les prompts sans casser le code existant

### Version actuelle: v1

La version v1 contient les prompts originaux extraits de `runtime/context_builder.py` et `planner/planner.py`.

## Format des Templates

Les templates utilisent **Jinja2** avec la syntaxe suivante:

### Variables simples
```jinja2
{{ variable_name }}
```

### Conditions
```jinja2
{% if condition %}
    contenu si vrai
{% endif %}
```

### Boucles
```jinja2
{% for item in items %}
    {{ item }}
{% endfor %}
```

## Templates Disponibles

### 1. system_prompt.j2
Prompt système principal de FilAgent.

**Variables:**
- `tools` (str): Description formatée des outils disponibles
- `semantic_context` (str, optional): Contexte sémantique additionnel

**Usage:**
```python
from runtime.template_loader import get_template_loader

loader = get_template_loader()
prompt = loader.render('system_prompt', tools=tools_desc, semantic_context=context)
```

### 2. planner_decomposition.j2
Prompt système pour le planificateur HTN (décomposition de tâches).

**Variables:** Aucune

**Usage:**
```python
prompt = loader.render('planner_decomposition')
```

### 3. planner_user_prompt.j2
Prompt utilisateur pour la décomposition de requêtes.

**Variables:**
- `query` (str): Requête utilisateur à décomposer
- `available_actions` (str): Liste des actions disponibles

**Usage:**
```python
prompt = loader.render('planner_user_prompt', 
                       query=user_query, 
                       available_actions=actions_list)
```

## Bonnes Pratiques

### 1. Création d'un Nouveau Template
```jinja2
{# Commentaire décrivant le template #}
Tu es {{ agent_name }}, un assistant {{ specialization }}.

CONTEXTE:
{{ context }}

{% if optional_section %}
SECTION OPTIONNELLE:
{{ optional_section }}
{% endif %}
```

### 2. Nommage des Fichiers
- Format: `<composant>_<fonction>.j2`
- Exemples: `system_prompt.j2`, `planner_decomposition.j2`
- Extension: `.j2` pour indiquer Jinja2

### 3. Variables Requises vs Optionnelles
- **Requises**: Utilisez `{{ variable }}`
- **Optionnelles**: Utilisez `{% if variable %}{{ variable }}{% endif %}`

### 4. Documentation
Chaque template doit être documenté dans ce README avec:
- Description du template
- Liste des variables (requises et optionnelles)
- Exemple d'usage

## Migration vers une Nouvelle Version

Pour créer une nouvelle version de prompts:

1. **Créer un nouveau dossier**:
   ```bash
   mkdir prompts/templates/v2
   ```

2. **Copier les templates existants**:
   ```bash
   cp prompts/templates/v1/*.j2 prompts/templates/v2/
   ```

3. **Modifier les templates** dans `v2/`

4. **Configurer la version par défaut** dans `config/agent.yaml`:
   ```yaml
   prompts:
     version: "v2"  # ou "v1" pour rollback
   ```

5. **Tester la nouvelle version**:
   ```python
   loader = get_template_loader(version='v2')
   ```

## Tests

Les templates doivent être testés pour:
- **Syntaxe valide**: Jinja2 compile sans erreur
- **Variables requises**: Toutes fournies lors du render
- **Output attendu**: Contenu généré correspond aux attentes

Voir `tests/test_template_loader.py` pour les tests existants.

## Troubleshooting

### Erreur: Template not found
- Vérifier que le fichier existe dans `prompts/templates/<version>/`
- Vérifier le nom du template (sans `.j2`)

### Erreur: Missing variable
- Vérifier que toutes les variables requises sont passées à `render()`
- Rendre la variable optionnelle si elle n'est pas toujours disponible

### Erreur: UndefinedError
- Une variable utilisée dans le template n'a pas été fournie
- Solution: Ajouter la variable ou la rendre optionnelle avec `{% if %}`

## Maintenance

- **Review régulier**: Vérifier que les prompts sont à jour avec les fonctionnalités
- **A/B testing**: Comparer les performances de différentes versions
- **Métriques**: Suivre l'efficacité des prompts (qualité des réponses)
- **Documentation**: Maintenir ce README à jour

## Conformité

Les prompts doivent respecter:
- **Loi 25 (Québec)**: Pas d'information personnelle dans les prompts statiques
- **AI Act (EU)**: Traçabilité des versions utilisées
- **Transparence**: Documentation claire de ce que fait l'agent

## Ressources

- [Documentation Jinja2](https://jinja.palletsprojects.com/)
- [Guide des Templates](../docs/PROMPT_TEMPLATES.md)
- [Code de Template Loader](../runtime/template_loader.py)
