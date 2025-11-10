# ComplianceGuardian - Guide d'utilisation

## Vue d'ensemble

Le module `ComplianceGuardian` assure la conformité réglementaire de FilAgent avec:
- **Loi 25** (Québec) - Protection des renseignements personnels
- **RGPD** (Europe) - Règlement général sur la protection des données
- **AI Act** (Europe) - Réglementation sur l'intelligence artificielle
- **NIST AI RMF** (USA) - Cadre de gestion des risques de l'IA

## Installation

Le ComplianceGuardian est automatiquement initialisé au démarrage de l'agent si activé dans la configuration.

## Configuration

### Fichier: `config/agent.yaml`

```yaml
compliance_guardian:
  enabled: true                    # Activer le ComplianceGuardian
  rules_path: "config/compliance_rules.yaml"
  validate_queries: true           # Valider les requêtes
  validate_plans: true             # Valider les plans d'exécution
  audit_executions: true           # Auditer les exécutions
  auto_generate_dr: true           # Générer automatiquement les DR
  strict_mode: true                # Mode strict (rejeter violations)
  log_compliance_events: true      # Logger les événements
  active_frameworks:
    - loi25
    - gdpr
    - ai_act
    - nist_ai_rmf
```

### Fichier: `config/compliance_rules.yaml`

Contient les règles détaillées de conformité:
- Patterns interdits (mots de passe, secrets, etc.)
- Patterns de PII (emails, SSN, numéros d'assurance, etc.)
- Limites (profondeur de plan, nombre d'outils, etc.)
- Outils nécessitant approbation
- Politiques d'audit et de rétention

## Utilisation

### Utilisation automatique (Recommandé)

Le ComplianceGuardian est intégré automatiquement dans l'agent:

```python
from runtime.agent import Agent

# L'agent initialise automatiquement le ComplianceGuardian
agent = Agent()
agent.initialize_model()

# Les requêtes sont automatiquement validées
response = agent.chat("Quelle est la météo?", conversation_id="conv123")
```

### Utilisation manuelle

```python
from planner.compliance_guardian import ComplianceGuardian, ComplianceError

# Initialiser
guardian = ComplianceGuardian(config_path="config/compliance_rules.yaml")

# 1. Valider une requête
try:
    result = guardian.validate_query(
        query="Quelle est la météo?",
        context={'user_id': 'user123'}
    )
    print(f"Validation: {result['valid']}")
except ComplianceError as e:
    print(f"Erreur de conformité: {e}")

# 2. Valider un plan d'exécution
plan = {
    'actions': [
        {'tool': 'calculator', 'params': {'expr': '2+2'}}
    ]
}
plan_result = guardian.validate_execution_plan(plan, {'task_id': 'task123'})

# 3. Auditer une exécution
execution_result = {
    'success': True,
    'result': 4,
    'errors': []
}
audit = guardian.audit_execution(execution_result, {'task_id': 'task123'})

# 4. Générer un Decision Record
dr = guardian.generate_decision_record(
    decision_type='calculation',
    query="Calcule 2+2",
    plan=plan,
    execution_result=execution_result,
    context={'actor': 'agent', 'task_id': 'task123'}
)
print(f"DR créé: {dr['dr_id']}")
```

## Points de validation

Le ComplianceGuardian intervient à plusieurs points du cycle de vie:

### 1. Validation de requête (avant planification)
- Longueur de la requête
- Détection de patterns interdits
- Détection de PII
- Vérification des champs requis

### 2. Validation de plan (après planification, avant exécution)
- Profondeur du plan
- Nombre d'outils
- Outils interdits
- Outils nécessitant approbation

### 3. Audit d'exécution (après exécution)
- Succès/échec
- Erreurs rencontrées
- Vérification de conformité

### 4. Génération de Decision Record (après exécution)
- Hash de la requête
- Hash du plan
- Hash du résultat
- Frameworks de conformité
- Métadonnées

## Gestion des erreurs

### Mode strict (strict_mode: true)

Les violations de conformité lèvent une exception `ComplianceError`:

```python
try:
    agent.chat("What is my password?", conversation_id="conv123")
except ComplianceError as e:
    print(f"Violation de conformité: {e}")
    # La requête est rejetée
```

### Mode permissif (strict_mode: false)

Les violations génèrent des warnings mais n'arrêtent pas l'exécution:

```python
# En mode permissif, la requête est traitée avec warnings
response = agent.chat("What is my password?", conversation_id="conv123")
# Warning: Query contains forbidden pattern
```

## Audit et traçabilité

### Logs d'audit

Tous les événements de conformité sont logués:

```python
# Récupérer le log d'audit
audit_log = guardian.get_audit_log()

for entry in audit_log:
    print(f"{entry['timestamp']}: {entry['event_type']}")
    print(f"  Data: {entry['data']}")
```

### Decision Records

Les Decision Records contiennent:
- ID unique (DR-YYYYMMDDHHMMSS-xxxxxx)
- Timestamp
- Type de décision
- Acteur
- Hash de la requête
- Hash du plan
- Hash du résultat
- Outils utilisés
- Frameworks de conformité

## Tests

### Tests unitaires

```bash
pytest tests/test_compliance_guardian.py -v
```

### Tests d'intégration

```bash
pytest tests/test_compliance_integration.py -v
```

### Tous les tests de conformité

```bash
pytest tests/test_compliance*.py -v
```

## Configuration par environnement

### Développement

```yaml
environments:
  development:
    compliance_guardian:
      strict_mode: false  # Plus permissif pour le développement
```

### Tests

```yaml
environments:
  testing:
    compliance_guardian:
      strict_mode: true  # Tester en mode strict
```

### Production

```yaml
environments:
  production:
    compliance_guardian:
      enabled: true
      strict_mode: true
      auto_generate_dr: true
      log_compliance_events: true
```

## Dépannage

### ComplianceGuardian non initialisé

Si vous voyez: `⚠ Failed to initialize ComplianceGuardian`

Vérifiez:
1. Le fichier `config/compliance_rules.yaml` existe
2. Les dépendances sont installées (`pip install pyyaml`)
3. La configuration `compliance_guardian.enabled` est à `true`

### Requêtes rejetées de manière inattendue

Vérifiez les patterns interdits dans `config/compliance_rules.yaml`:

```yaml
validation:
  forbidden_patterns:
    - '(?i)(password|secret|token|api[_-]?key)'
```

### Plan rejeté de manière inattendue

Vérifiez les limites dans `config/compliance_rules.yaml`:

```yaml
execution:
  max_plan_depth: 5
  max_tools_per_plan: 20
  forbidden_tools: []
```

## Conformité réglementaire

### Loi 25 (Québec)

- ✓ Détection et masquage de PII
- ✓ Traçabilité complète des opérations
- ✓ Rétention des logs (configurable)
- ✓ Decision Records signés

### RGPD (Europe)

- ✓ Protection des données personnelles
- ✓ Droit à l'oubli (via rétention configurable)
- ✓ Transparence des traitements
- ✓ Logs d'audit

### AI Act (Europe)

- ✓ Transparence des décisions
- ✓ Surveillance humaine (outils nécessitant approbation)
- ✓ Gestion des risques
- ✓ Documentation complète

### NIST AI RMF (USA)

- ✓ Gouvernance
- ✓ Cartographie des risques
- ✓ Mesures de sécurité
- ✓ Gestion continue

## Support

Pour plus d'informations:
- Code source: `planner/compliance_guardian.py`
- Configuration: `config/compliance_rules.yaml`
- Tests: `tests/test_compliance_guardian.py`, `tests/test_compliance_integration.py`
- Documentation projet: `README.md`
