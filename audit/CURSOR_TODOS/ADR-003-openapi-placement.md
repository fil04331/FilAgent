# ADR 003 : Placement et Intégration du Spec OpenAPI

**Date**: 2025-10-27  
**Statut**: Accepté  
**Contexte**: Intégration du fichier `openapi.yaml` dans l'architecture FilAgent

---

## Contexte

FilAgent nécessite une spécification d'API formelle pour:
1. **Conformité légale contractuelle** (Loi 25, AI Act) - Le spec OpenAPI sert de contrat légalement opposable
2. **Génération automatique de clients** pour intégrations tierces
3. **Tests de contrat** (contract testing) dans CI/CD
4. **Documentation interactive** (Swagger UI, ReDoc)
5. **Validation automatique** de l'implémentation vs spécification

Le fichier `openapi.yaml` (1027 lignes) a été développé avec Cursor et documente:
- 4 endpoints principaux (`/`, `/health`, `/chat`, `/memory/*`)
- 15+ schémas de données (ChatRequest, ChatResponse, DecisionRecord, ProvenanceGraph, EventLog)
- Métadonnées de conformité (middlewares, cadres légaux)
- Exemples détaillés pour chaque endpoint

---

## Décision

**Placement du fichier** : `FilAgent/openapi.yaml` (racine du projet)

**Rationales** :

### 1. Convention Industrielle Standard
- GitHub, Stripe, Twilio, AWS placent leurs specs OpenAPI à la racine
- Les outils OpenAPI (swagger-codegen, openapi-generator, Prism) s'attendent à trouver le spec à la racine
- Simplification des chemins dans CI/CD : `./openapi.yaml` vs `./docs/api/openapi.yaml`

### 2. Conformité Légale
Le spec OpenAPI de FilAgent n'est pas qu'une documentation technique - c'est un **contrat légal** qui :
- Définit formellement les garanties de traçabilité (Loi 25 Article 53.1)
- Spécifie les métadonnées de conformité (middlewares, PROV-JSON, Decision Records)
- Documente les engagements RGPD/AI Act dans `info.description`

**Placement à la racine** = visibilité maximale pour auditeurs et régulateurs.

### 3. Intégration FastAPI
FastAPI permet de servir un spec manuel via :
```python
def custom_openapi():
    openapi_path = Path(__file__).parent.parent / "openapi.yaml"
    with open(openapi_path, 'r') as f:
        return yaml.safe_load(f)

app.openapi = custom_openapi
```

Chemin relatif simplifié avec placement racine : `../openapi.yaml` vs `../../docs/api/openapi.yaml`.

### 4. Outillage CI/CD
Workflow GitHub Actions simplifié :
```yaml
- name: Validate OpenAPI Spec
  run: python scripts/validate_openapi.py
  
- name: Contract Testing
  run: prism mock openapi.yaml  # Chemin direct
```

Vs chemins plus complexes si dans sous-dossiers.

### 5. Génération de Clients
```bash
openapi-generator generate -i openapi.yaml -g python -o clients/python
```

Convention standard = chemin direct sans spécifier `-i docs/api/openapi.yaml`.

---

## Alternatives Considérées

### Alternative 1 : `docs/api/openapi.yaml`

**Pour** :
- Groupé avec documentation existante (ADRs, SOPs)
- Séparation claire code/spécifications
- Structure `docs/` déjà existante

**Contre** :
- Chemin non-standard = friction pour outils tiers
- Complexification CI/CD (chemins relatifs plus longs)
- Moins visible pour auditeurs

**Verdict** : ❌ Rejeté

### Alternative 2 : `api/openapi.yaml`

**Pour** :
- Dossier dédié pour écosystème API
- Permet d'ajouter `api/validators/`, `api/mocks/`

**Contre** :
- Création d'un nouveau dossier top-level (complexification structure)
- Non-standard pour projets Python (pas de package `api/`)
- Outils s'attendent à racine

**Verdict** : ❌ Rejeté

### Alternative 3 : Génération automatique via FastAPI

**Pour** :
- Pas de maintenance manuelle
- Toujours synchronisé avec implémentation

**Contre** :
- **CRITIQUE** : Perte de contrôle sur métadonnées de conformité
  - FastAPI auto-génère un spec technique, pas un **contrat légal**
  - Métadonnées cruciales (middlewares, cadres légaux) non incluses
  - Description détaillée de conformité perdue
- Pas de validation contractuelle (spec ne définit plus le comportement attendu)
- Difficulté à documenter exigences légales (Loi 25, RGPD, AI Act)

**Verdict** : ❌ Rejeté (incompatible avec exigences légales)

---

## Conséquences

### Positives

1. **Conformité maximale** : Spec OpenAPI = contrat légal opposable avec métadonnées complètes
2. **Tooling standard** : Tous les outils OpenAPI fonctionnent sans configuration supplémentaire
3. **CI/CD simplifié** : Validation automatique triviale (`python scripts/validate_openapi.py`)
4. **Documentation contractuelle** : Swagger UI/ReDoc génèrent docs depuis spec manuel
5. **Tests de contrat** : Schemathesis/Prism peuvent valider implémentation vs spec
6. **Génération clients** : `openapi-generator` peut créer SDKs Python/TS/Go automatiquement

### Négatives

1. **Maintenance double** : Spec OpenAPI + implémentation FastAPI doivent rester synchronisés
   - **Mitigation** : Tests de contrat automatiques détectent divergences
   - **Mitigation** : CI/CD bloque PRs si validation échoue
   
2. **Fichier volumineux racine** : 1027 lignes peuvent sembler "polluer" la racine
   - **Mitigation** : Standard industriel, fichier unique et bien documenté
   
3. **Risque de drift** : Spec peut diverger de l'implémentation
   - **Mitigation** : Pipeline CI/CD avec `schemathesis` pour tests automatiques
   - **Mitigation** : Hook pre-commit pour validation

---

## Plan d'Implémentation

### Phase 1 : Setup Initial (Jour 1)

```bash
# 1. Placer le fichier
cp openapi.yaml FilAgent/openapi.yaml

# 2. Créer script de validation
mkdir -p FilAgent/scripts
cp validate_openapi.py FilAgent/scripts/

# 3. Ajouter dépendances
echo "openapi-spec-validator>=0.7.1" >> FilAgent/requirements.txt
echo "schemathesis>=3.19.0" >> FilAgent/requirements.txt

# 4. Premier test de validation
cd FilAgent
python scripts/validate_openapi.py
```

### Phase 2 : Intégration FastAPI (Jour 1-2)

Modifier `runtime/server.py` :

```python
import yaml
from pathlib import Path
from fastapi import FastAPI

app = FastAPI(
    title="FilAgent API",
    version="0.1.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

def custom_openapi():
    """Charge le spec OpenAPI manuel depuis la racine"""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_path = Path(__file__).parent.parent / "openapi.yaml"
    with open(openapi_path, 'r', encoding='utf-8') as f:
        openapi_schema = yaml.safe_load(f)
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```

Tests :
```bash
# Démarrer serveur
python runtime/server.py &

# Vérifier que le spec custom est servi
curl http://localhost:8000/openapi.json | jq '.info.title'
# Devrait retourner: "FilAgent API"

# Vérifier Swagger UI
curl http://localhost:8000/docs  # Devrait afficher page HTML
```

### Phase 3 : Tests de Contrat (Jour 2-3)

Créer `tests/contract/test_openapi_contract.py` :

```python
import pytest
import requests
from schemathesis import from_uri
from schemathesis.checks import not_a_server_error

schema = from_uri("http://localhost:8000/openapi.json")

@schema.parametrize()
def test_api_conforms_to_openapi(case):
    """
    Générer automatiquement des tests pour TOUS les endpoints
    selon le spec OpenAPI
    """
    response = case.call()
    case.validate_response(response, checks=(not_a_server_error,))
```

Exécution :
```bash
# Démarrer serveur en background
python runtime/server.py &

# Lancer tests de contrat
pytest tests/contract/test_openapi_contract.py -v

# Attendu : Tous les endpoints testés automatiquement
```

### Phase 4 : CI/CD Integration (Jour 3-4)

Créer `.github/workflows/openapi_validation.yml` :

```yaml
name: OpenAPI Validation

on:
  push:
    paths:
      - 'openapi.yaml'
      - 'runtime/server.py'
  pull_request:

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Validate OpenAPI Spec
        run: python scripts/validate_openapi.py
      
      - name: Contract Testing
        run: |
          python runtime/server.py &
          sleep 5
          pytest tests/contract/ -v
      
      - name: Generate Documentation
        run: |
          npx @redocly/cli build-docs openapi.yaml \
            --output docs/api/index.html
```

### Phase 5 : Génération de Clients (Jour 4-5)

```bash
# Installer openapi-generator
npm install -g @openapitools/openapi-generator-cli

# Générer client Python
openapi-generator generate \
  -i openapi.yaml \
  -g python \
  -o clients/python \
  --package-name filagent_client

# Générer client TypeScript
openapi-generator generate \
  -i openapi.yaml \
  -g typescript-fetch \
  -o clients/typescript

# Tester clients générés
cd clients/python
pip install -e .
python -c "from filagent_client import ApiClient; print('OK')"
```

---

## Métriques de Succès

| Métrique | Cible | Mesure |
|----------|-------|--------|
| **Validation spec** | 100% pass | `python scripts/validate_openapi.py` |
| **Tests de contrat** | 100% endpoints testés | `pytest tests/contract/` |
| **Drift détection** | 0 divergences | CI/CD bloque si spec ≠ impl |
| **Documentation auto** | Swagger UI opérationnel | `http://localhost:8000/docs` |
| **Génération clients** | Python + TS générés | Clients compilent sans erreurs |

---

## Risques et Mitigations

### Risque 1 : Drift entre spec et implémentation

**Impact** : Élevé (conformité légale compromise)  
**Probabilité** : Moyenne

**Mitigations** :
1. **Tests automatiques** via Schemathesis : CI/CD bloque si divergence
2. **Hook pre-commit** : Validation avant chaque commit
3. **Review process** : PRs modifiant `runtime/server.py` doivent aussi mettre à jour `openapi.yaml`

### Risque 2 : Maintenance double effort

**Impact** : Moyen (charge de travail accrue)  
**Probabilité** : Élevée

**Mitigations** :
1. **Génération partielle** : Envisager génération automatique de sections non-critiques
2. **Tooling** : Scripts pour détecter endpoints non documentés
3. **Process** : Checklist PR incluant "OpenAPI spec updated?"

### Risque 3 : Spec trop verbeux (1027 lignes)

**Impact** : Faible (maintenabilité)  
**Probabilité** : Faible

**Mitigations** :
1. **Modularisation** : Envisager split en fichiers séparés (`openapi/schemas/*.yaml`)
2. **Refs** : Utiliser `$ref` pour réduire duplication
3. **Tooling** : Utiliser redocly pour bundling si nécessaire

---

## Évolution Future

### Court Terme (1-3 mois)
- [ ] Implémenter tous les tests de contrat
- [ ] Générer clients Python/TS pour partenaires
- [ ] Documenter process de mise à jour du spec

### Moyen Terme (3-6 mois)
- [ ] Ajouter exemples de requêtes/réponses pour chaque endpoint
- [ ] Générer mocks Prism pour tests d'intégration
- [ ] Ajouter versioning API (v1, v2)

### Long Terme (6-12 mois)
- [ ] Envisager génération hybride (auto + manuel)
- [ ] Ajouter webhooks dans spec
- [ ] Implémenter API Gateway avec validation OpenAPI inline

---

## Références

- [OpenAPI Specification 3.0.3](https://spec.openapis.org/oas/v3.0.3)
- [FastAPI OpenAPI Customization](https://fastapi.tiangolo.com/advanced/extending-openapi/)
- [Schemathesis - Property-Based Testing](https://schemathesis.readthedocs.io/)
- [OpenAPI Generator](https://openapi-generator.tech/)
- **Loi 25 (Québec)** : Article 53.1 sur transparence des décisions automatisées
- **RGPD (UE)** : Article 15 (droit d'accès) et Article 22 (décisions automatisées)
- **AI Act (UE)** : Article 13 (exigences de traçabilité)

---

## Approbation

**Architecte** : FilAgent Team  
**Date** : 2025-10-27  
**Révision suivante** : 2025-11-27 (1 mois après implémentation)

---

**Statut** : ✅ **ACCEPTÉ** - Implémentation peut commencer
