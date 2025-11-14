## Contexte

Suite à la fermeture de PR #107, extraire les tests utiles pour renforcer la couverture de tests du projet FilAgent.

## Objectifs

### Tests Unitaires
- [ ] Ajouter tests unitaires pour ComplianceGuardian
  - Validation des règles de conformité
  - Gestion des erreurs et exceptions
  - Intégration avec les middlewares
- [ ] Ajouter tests pour HTN Planning
  - Planification avec différentes stratégies
  - Décomposition de tâches complexes
  - Gestion des dépendances dans le graphe
- [ ] Améliorer couverture tests middleware
  - `runtime/middleware/logging.py`
  - `runtime/middleware/provenance.py`
  - `runtime/middleware/audittrail.py`
  - `runtime/middleware/redaction.py`

### Tests d'Intégration
- [ ] Tests end-to-end pour workflows complets
- [ ] Tests d'intégration ComplianceGuardian + HTN
- [ ] Tests de conformité (Loi 25, GDPR, AI Act)

### Tests de Régression
- [ ] Ajouter tests pour bugs connus et corrigés
- [ ] Tests de non-régression pour ComplianceGuardian
- [ ] Tests de sécurité (PII redaction, WORM logging)

## Référence

- **PR fermée**: #107 (contient des tests à extraire)
- **Documentation existante**:
  - `tests/README_E2E_COMPLIANCE.md`
  - `tests/conftest.py` (fixtures)
  - `pytest.ini` (configuration)

## Structure Cible

```
tests/
├── test_compliance_guardian/
│   ├── test_validation.py
│   ├── test_integration.py
│   └── test_edge_cases.py
├── test_htn_planning/
│   ├── test_strategies.py
│   ├── test_execution.py
│   └── test_verification.py
└── test_middleware/
    ├── test_logging_edge_cases.py
    ├── test_provenance_tracking.py
    └── test_pii_redaction.py
```

## Critères d'Acceptation

- [ ] Couverture de tests globale > 80%
- [ ] Tous les tests passent en CI (`pytest`)
- [ ] Documentation des nouveaux tests (docstrings)
- [ ] Fixtures réutilisables pour tests futurs
- [ ] Tests marqués correctement (`@pytest.mark.unit`, `@pytest.mark.compliance`, etc.)

## Priorité

**MOYENNE** - Améliorer la qualité et la robustesse du code

## Estimation

2-3 semaines (selon volume de tests de #107 à extraire)

## Labels Suggérés

- `testing`
- `enhancement`
- `good first issue`
- `documentation`
