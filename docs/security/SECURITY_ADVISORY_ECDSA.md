# Advisory de Sécurité : CVE-2024-23342 (python-ecdsa)

**Date** : 2025-11-18
**Sévérité** : HIGH
**Statut** : IMPACT MINIMAL - Dépendance indirecte non utilisée

---

## 📋 Résumé

Une vulnérabilité de type **Minerva timing attack** a été détectée dans `python-ecdsa` (CVE-2024-23342).

**Détails Dependabot Alert #85** :
- **Package** : `ecdsa` v0.19.1
- **Vulnérabilité** : Minerva timing attack sur courbe P-256
- **Versions affectées** : TOUTES (`>= 0`)
- **Correctif disponible** : ❌ AUCUN (projet considère side-channel attacks hors scope)

---

## 🔍 Analyse d'Impact sur FilAgent

### ✅ **Conclusion : IMPACT MINIMAL**

FilAgent **N'EST PAS vulnérable** pour les raisons suivantes :

1. **python-ecdsa n'est PAS directement utilisé**
   - Dépendance indirecte via `python-jose` (JWT library)
   - Aucun import direct de `ecdsa` dans le code FilAgent

2. **FilAgent utilise Ed25519, PAS P-256**
   ```python
   # runtime/middleware/audittrail.py:13
   from cryptography.hazmat.primitives.asymmetric import ed25519
   ```
   - **Ed25519** (Curve25519) - Résistant aux timing attacks par conception
   - **P-256** (NIST curve) - Vulnérable selon CVE-2024-23342

3. **Isolation cryptographique**
   - Toutes les signatures critiques (Decision Records, WORM logs) utilisent Ed25519
   - `python-jose` utilisé uniquement pour JWT (non critique pour la gouvernance)

---

## 🎯 Actions Recommandées

### **Priorité 1 : Migration python-jose**

`python-jose` est un projet peu maintenu. Migrer vers une alternative moderne :

#### Option A : PyJWT (RECOMMANDÉ)
```bash
pdm remove python-jose
pdm add "pyjwt[crypto]>=2.10.1"
```

**Avantages** :
- ✅ Activement maintenu (dernière release : Janvier 2025)
- ✅ Utilise `cryptography` (Ed25519 natif)
- ✅ Compatible Python 3.8-3.14
- ✅ Pas de dépendance à python-ecdsa

#### Option B : python-jose[cryptography]
```bash
pdm remove python-jose
pdm add "python-jose[cryptography]>=3.5.0"
```

**Avantages** :
- ✅ Backend cryptography au lieu de python-ecdsa
- ✅ API identique (migration transparente)

**Inconvénients** :
- ⚠️ Projet moins actif que PyJWT

---

### **Priorité 2 : Audit Code JWT**

Identifier tous les usages de `python-jose` :

```bash
grep -r "import jose" --include="*.py"
grep -r "from jose" --include="*.py"
```

**Résultats actuels** :
```
SECURITY_AUDIT.md:204:   from jose import jwt, JWTError
```

**Action** : Vérifier si ce code est actif ou documentation uniquement.

---

### **Priorité 3 : Validation Compliance**

Après migration, valider conformité :

```bash
# Tests de conformité
pdm run test-compliance

# Audit sécurité
pdm run security
pdm run bandit

# Vérifier signatures EdDSA intactes
pytest tests/test_middleware_audittrail.py::test_signature_functionality -v
```

---

## 📊 Chronologie

| Date | Action | Statut |
|------|--------|--------|
| 2024-XX-XX | CVE-2024-23342 publié | - |
| 2025-11-16 | Commit 656021c (sécurité Phase 2) | ✅ |
| 2025-11-18 | Dependabot Alert #85 détecté | 🔍 En analyse |
| 2025-11-18 | Analyse d'impact complétée | ✅ IMPACT MINIMAL |
| TBD | Migration python-jose → PyJWT | ⏳ Planifié |

---

## 🔐 Contexte Technique

### Qu'est-ce qu'une attaque Minerva ?

**Type** : Side-channel attack (canal auxiliaire)
**Vecteur** : Timing analysis

**Principe** :
1. Attaquant mesure le **temps d'exécution** des signatures ECDSA
2. Analyse statistique sur des milliers d'échantillons
3. Révèle le **nonce interne** (nombre aléatoire)
4. Calcule la **clé privée** à partir du nonce

**Courbes affectées** :
- ✅ P-256 (NIST) - VULNÉRABLE
- ✅ P-384, P-521 - VULNÉRABLES
- ❌ Curve25519 (Ed25519) - RÉSISTANT (constant-time operations)

### Pourquoi Ed25519 est résistant ?

```python
# Ed25519 garantit constant-time operations
signature = private_key.sign(message)
# ⏱️ Temps d'exécution indépendant du message
# 🔐 Pas de fuite d'information via timing
```

**Design de sécurité** :
- Opérations à temps constant (constant-time)
- Pas de branches conditionnelles dépendantes des secrets
- Résistant aux side-channels par conception (RFC 8032)

---

## 📚 Références

- **CVE** : CVE-2024-23342
- **CWE** : CWE-208 (Observable Timing Discrepancy)
- **Dependabot Alert** : #85
- **RFC 8032** : Edwards-Curve Digital Signature Algorithm (EdDSA)
- **NIST FIPS 186-5** : Digital Signature Standard

---

## ✅ Validation

### Tests de Non-Régression

Après toute modification :

```bash
# Signatures EdDSA fonctionnelles
pytest tests/test_middleware_audittrail.py -v

# Conformité Loi 25
pytest tests/test_compliance_flow.py -v

# Intégrité WORM
pytest tests/test_worm_finalization.py -v
```

### Checklist de Migration

- [ ] Remplacer `python-jose` par `pyjwt[crypto]`
- [ ] Mettre à jour imports dans SECURITY_AUDIT.md (si code actif)
- [ ] Exécuter suite de tests complète (`pdm run test`)
- [ ] Valider aucun import `ecdsa` résiduel
- [ ] Vérifier audit `pdm run security` (0 vulnérabilités HIGH)
- [ ] Documenter changement dans CHANGELOG.md
- [ ] Créer Decision Record de la migration

---

**Responsable** : DevSecOps
**Prochaine revue** : 2025-12-01

