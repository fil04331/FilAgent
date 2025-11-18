# Guide Utilisateur - Analyseur de Documents FilAgent

**Version**: 1.0.0
**Date**: 2025-11-18
**Pour**: PME québécoises

---

## Table des Matières

1. [Vue d'ensemble](#vue-densemble)
2. [Formats supportés](#formats-supportés)
3. [Types d'analyse](#types-danalyse)
4. [Utilisation de l'interface Gradio](#utilisation-de-linterface-gradio)
5. [Export des résultats](#export-des-résultats)
6. [Limites et contraintes](#limites-et-contraintes)
7. [Résolution de problèmes](#résolution-de-problèmes)
8. [Conformité et sécurité](#conformité-et-sécurité)
9. [Support](#support)

---

## Vue d'ensemble

L'Analyseur de Documents FilAgent est un outil spécialisé pour les PME québécoises qui permet d'extraire, analyser et structurer automatiquement les informations contenues dans vos documents commerciaux.

### Caractéristiques principales

✅ **Formats multiples**: PDF, Word (.docx), Excel (.xlsx)
✅ **Analyses spécialisées**: Factures, contrats, rapports financiers
✅ **Prévisualisation en temps réel**: Voir votre document avant l'analyse
✅ **Export flexible**: JSON, CSV, Excel
✅ **Conforme Loi 25**: Redaction automatique des informations personnelles
✅ **Sécurisé**: Traçabilité complète avec Decision Records
✅ **Calculs TPS/TVQ**: Validation automatique des taxes québécoises

### Capacités

- **Extraction de texte**: Extrait tout le contenu textuel des documents
- **Analyse de factures**: Identifie montants, taxes, fournisseurs, dates
- **Analyse financière**: Détecte métriques financières, KPIs, tendances
- **Analyse de contrats**: Extrait clauses, parties, conditions
- **Génération de rapports**: Crée des rapports structurés et exportables

---

## Formats supportés

### Documents PDF (.pdf)

**Extensions acceptées**: `.pdf`

**Capacités**:
- Extraction de texte complet
- Lecture de documents multi-pages
- Support des PDF générés (non-scannés)

**Limitations**:
- Les PDF scannés (images) ne sont pas supportés actuellement
- Le texte doit être sélectionnable (pas d'OCR)

**Exemple d'utilisation**:
- Factures PDF de fournisseurs
- Contrats juridiques
- Rapports d'audit

---

### Documents Word (.docx)

**Extensions acceptées**: `.docx`

**Capacités**:
- Extraction du texte avec formatage
- Support des tableaux
- Lecture des métadonnées

**Limitations**:
- Anciens formats (.doc) non supportés
- Images et graphiques non analysés

**Exemple d'utilisation**:
- Rapports d'activité
- Propositions commerciales
- Documentation interne

---

### Fichiers Excel (.xlsx)

**Extensions acceptées**: `.xlsx`, `.xls`

**Capacités**:
- Lecture de toutes les feuilles
- Extraction des tableaux de données
- Support des formules (résultats calculés)
- Détection automatique des colonnes

**Limitations**:
- Macros non exécutées
- Graphiques non analysés
- Maximum 10 000 lignes par feuille

**Exemple d'utilisation**:
- Factures Excel
- Rapports financiers mensuels
- Listes de clients/fournisseurs
- Inventaires

---

## Types d'analyse

### 1. Analyse de Facture (`invoice`)

**Usage**: Pour extraire les informations commerciales d'une facture

**Données extraites**:
- Numéro de facture
- Date d'émission
- Fournisseur/Client
- Montants (sous-total, taxes, total)
- TPS (5%) et TVQ (9.975%)
- Conditions de paiement
- Articles/services

**Format de sortie**:
```json
{
  "invoice_number": "INV-2025-001",
  "date": "2025-11-18",
  "supplier": "Entreprise ABC Inc.",
  "subtotal": 1000.00,
  "tps": 50.00,
  "tvq": 99.75,
  "total": 1149.75,
  "items": [
    {
      "description": "Service de consultation",
      "quantity": 10,
      "unit_price": 100.00,
      "amount": 1000.00
    }
  ]
}
```

**Validation automatique**:
- ✅ Calculs TPS/TVQ corrects
- ✅ Total = Sous-total + TPS + TVQ
- ⚠️ Avertissements si les montants ne concordent pas

---

### 2. Extraction Simple (`extract`)

**Usage**: Pour extraire tout le texte d'un document sans structuration spécifique

**Données extraites**:
- Texte brut complet
- Nombre de pages
- Nombre de mots
- Encodage détecté

**Cas d'usage**:
- Archivage de documents
- Recherche plein-texte
- Conversion de format
- Indexation de contenu

---

### 3. Analyse Financière (`financial`)

**Usage**: Pour extraire les métriques et indicateurs financiers

**Données extraites**:
- Revenus
- Dépenses
- Profits/Pertes
- Ratios financiers
- Tendances (si données temporelles)

**Cas d'usage**:
- Rapports trimestriels
- Bilans annuels
- États financiers

---

### 4. Analyse de Contrat (`contract`)

**Usage**: Pour identifier les éléments clés d'un contrat

**Données extraites**:
- Parties contractantes
- Dates (début, fin, renouvellement)
- Clauses importantes
- Conditions financières
- Obligations

**Cas d'usage**:
- Contrats de service
- Baux commerciaux
- Accords de partenariat

---

### 5. Génération de Rapport (`report`)

**Usage**: Pour créer un rapport structuré et exportable

**Données extraites**:
- Résumé exécutif
- Sections principales
- Tableaux et chiffres clés
- Conclusions

**Format de sortie**: Rapport formaté en Markdown ou JSON

---

## Utilisation de l'interface Gradio

### Démarrage

1. **Lancer l'interface**:
```bash
pdm run python gradio_app_production.py
```

2. **Accéder à l'interface**:
   - Ouvrir navigateur: `http://localhost:7860`
   - Cliquer sur l'onglet **"📄 Document Analyzer"**

---

### Étape par étape

#### Étape 1: Téléverser un fichier

1. Cliquez sur la zone **"Téléverser un fichier"**
2. Sélectionnez votre document (PDF, DOCX, XLSX)
3. Attendez le message de confirmation ✅

**Contraintes**:
- Taille maximale: **50 MB**
- Extensions autorisées: `.pdf`, `.docx`, `.xlsx`, `.xls`

---

#### Étape 2: Sélectionner le type d'analyse

Dans le menu déroulant **"Type d'analyse"**, choisissez:
- **Invoice** - Pour les factures
- **Extract** - Pour extraction simple
- **Financial** - Pour documents financiers
- **Contract** - Pour les contrats
- **Report** - Pour générer un rapport

**Recommandation**: Si vous n'êtes pas sûr, utilisez **Extract** pour commencer.

---

#### Étape 3: Lancer l'analyse

1. Cliquez sur le bouton **"📊 Analyser"**
2. Attendez le traitement (maximum 30 secondes)
3. Consultez les résultats dans la zone de sortie

**Messages possibles**:
- ✅ Analyse réussie
- ⚠️ Avertissements (fichier suspect, calculs incorrects)
- ❌ Erreurs (fichier corrompu, format non supporté)

---

#### Étape 4: Prévisualiser le document

La **zone de prévisualisation** affiche automatiquement:

**Pour PDF**:
- Aperçu de la première page
- Nombre de pages
- Dimensions

**Pour Excel**:
- Première feuille avec données
- Noms des colonnes
- Nombre de lignes

**Pour Word**:
- Extrait du début du document
- Nombre de mots
- Structure

---

## Export des résultats

### Format JSON (avec signature EdDSA)

**Usage**: Pour archivage sécurisé et conformité

**Contenu**:
```json
{
  "metadata": {
    "file_name": "facture_nov_2025.pdf",
    "file_size_bytes": 125840,
    "analysis_type": "invoice",
    "timestamp": "2025-11-18T14:30:00Z",
    "filagent_version": "2.3.0"
  },
  "results": {
    "invoice_number": "INV-2025-001",
    "total": 1149.75
  },
  "compliance": {
    "pii_redacted": true,
    "decision_record_id": "DR-20251118-143000-abc123"
  },
  "signature": {
    "algorithm": "EdDSA",
    "public_key": "...",
    "signature": "..."
  }
}
```

**Avantages**:
- ✅ Signature cryptographique (non-répudiation)
- ✅ Traçabilité complète
- ✅ Conforme Loi 25

**Vérification de la signature**:
```python
# Exemple de vérification (optionnel)
import json
from cryptography.hazmat.primitives.asymmetric import ed25519

with open('results.json') as f:
    data = json.load(f)

# Extraire signature et données
signature = bytes.fromhex(data['signature']['signature'])
public_key_bytes = bytes.fromhex(data['signature']['public_key'])

# Vérifier
public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)
public_key.verify(signature, json.dumps(data['results']).encode())
```

---

### Format CSV (UTF-8)

**Usage**: Pour import dans Excel, Google Sheets, bases de données

**Exemple (factures)**:
```csv
invoice_number,date,supplier,subtotal,tps,tvq,total
INV-2025-001,2025-11-18,Entreprise ABC Inc.,1000.00,50.00,99.75,1149.75
```

**Encodage**: UTF-8 avec BOM (compatible Excel)

**Avantages**:
- ✅ Facilement importable
- ✅ Léger et portable
- ✅ Compatible avec la plupart des outils

---

### Format Excel (.xlsx)

**Usage**: Pour analyse dans Excel avec formules

**Contenu**:
- **Feuille 1**: Résultats principaux
- **Feuille 2**: Métadonnées (date, version, paramètres)
- **Feuille 3**: Informations de conformité

**Formules incluses**:
- Sommes automatiques
- Validation TPS/TVQ
- Calculs de totaux

**Avantages**:
- ✅ Mise en forme professionnelle
- ✅ Formules pré-calculées
- ✅ Multi-feuilles pour organisation

---

### Package ZIP (Download All)

**Usage**: Pour archiver tous les formats en un seul fichier

**Contenu du ZIP**:
```
analysis_package_20251118_143000.zip
├── analysis_results.json    (avec signature EdDSA)
├── analysis_results.csv     (UTF-8)
├── analysis_results.xlsx    (Excel multi-feuilles)
└── metadata.txt            (informations du système)
```

**Utilisation**:
1. Cliquez sur **"📦 Download All"**
2. Téléchargez le fichier ZIP
3. Extrayez pour accéder à tous les formats

**Avantages**:
- ✅ Un seul téléchargement
- ✅ Tous les formats disponibles
- ✅ Métadonnées de conformité incluses
- ✅ Archivage simplifié

---

## Limites et contraintes

### Limites techniques

| Limite | Valeur | Raison |
|--------|--------|--------|
| Taille maximale | 50 MB | Performance et mémoire |
| Timeout traitement | 30 secondes | Éviter les blocages |
| Lignes Excel max | 10 000 par feuille | Performance |
| Pages PDF max | Illimité | (mais timeout à 30s) |

### Extensions non supportées

❌ Formats **NON** supportés:
- `.txt` (fichiers texte bruts)
- `.doc` (ancien Word)
- `.xls` binaire (ancien Excel)
- Images (`.jpg`, `.png`, `.tiff`)
- PDF scannés (OCR requis)
- Archives (`.zip`, `.rar`)

### Validation automatique

Avant chaque analyse, FilAgent vérifie:

1. ✅ **Existence du fichier**
2. ✅ **Extension autorisée**
3. ✅ **Taille < 50 MB**
4. ✅ **Permissions de lecture**
5. ✅ **Fichier non corrompu**
6. ✅ **Espace disque disponible**

Si une vérification échoue, un message d'erreur clair est affiché avec la solution.

---

## Résolution de problèmes

### Erreur: "Fichier trop volumineux"

**Message**:
```
❌ Fichier trop volumineux
Taille maximale autorisée: 50 MB
Taille actuelle: 65.3 MB

💡 Solution:
1. Compresser le PDF (via Adobe Acrobat, PDF24)
2. Diviser le document en plusieurs fichiers
3. Supprimer les images inutiles
```

**Solutions**:
- Compresser le PDF avec [PDF24](https://tools.pdf24.org/fr/compresser-pdf)
- Diviser le fichier en sections plus petites
- Convertir les images en résolution inférieure

---

### Erreur: "Format non supporté"

**Message**:
```
❌ Format de fichier non supporté
Extension détectée: .txt

💡 Formats acceptés:
- PDF: .pdf
- Word: .docx
- Excel: .xlsx, .xls
```

**Solutions**:
- Vérifier l'extension du fichier
- Convertir le fichier dans un format supporté
- Renommer le fichier avec la bonne extension (si mal nommé)

---

### Erreur: "Fichier corrompu"

**Message**:
```
❌ Impossible de lire le fichier
Le fichier semble corrompu ou endommagé.

💡 Solutions:
1. Réessayer le téléchargement
2. Ouvrir et ré-enregistrer le fichier
3. Vérifier l'intégrité avec l'application source
```

**Solutions**:
- Ouvrir le fichier dans son application native (Adobe, Word, Excel)
- Enregistrer une nouvelle copie
- Vérifier que le téléchargement est complet

---

### Erreur: "Timeout dépassé"

**Message**:
```
❌ Temps de traitement dépassé
L'analyse a pris plus de 30 secondes.

💡 Solutions:
1. Réduire la taille du fichier
2. Diviser en sections plus petites
3. Simplifier le document (supprimer images)
```

**Solutions**:
- Simplifier le document
- Analyser section par section
- Contacter le support si le problème persiste

---

### Avertissement: "Calculs TPS/TVQ incorrects"

**Message**:
```
⚠️ Attention: Les taxes ne correspondent pas aux taux québécois

Attendu:
- TPS (5%): 50.00$
- TVQ (9.975%): 99.75$

Détecté:
- TPS: 48.50$
- TVQ: 95.00$

💡 Note: Ceci est un avertissement, pas une erreur.
Vérifiez les taux avec votre comptable.
```

**Interprétation**:
- Ce n'est **pas une erreur** d'analyse
- Les montants ont été correctement extraits
- Mais ils ne correspondent pas aux taux standards (5% et 9.975%)
- Raisons possibles:
  - Taux de taxe différents (certains produits/services)
  - Erreur dans la facture originale
  - Arrondissement

**Action recommandée**: Vérifier avec votre comptable

---

### Problème: "Aucune donnée extraite"

**Symptômes**:
- L'analyse réussit mais les résultats sont vides
- Message: `{}`

**Causes possibles**:
1. Document vide ou sans texte
2. PDF scanné (image, pas de texte sélectionnable)
3. Mauvais type d'analyse sélectionné

**Solutions**:
- Vérifier que le document contient du texte
- Essayer type d'analyse "Extract" (plus permissif)
- Si PDF scanné, utiliser un outil OCR d'abord

---

## Conformité et sécurité

### Conformité Loi 25 (Québec)

L'Analyseur de Documents FilAgent est **100% conforme** à la Loi 25:

✅ **Article 3 - Minimisation des données**:
- Seules les données nécessaires à l'analyse sont extraites
- Pas de collecte d'informations superflues

✅ **Article 4 - Exactitude**:
- Validation automatique des calculs (TPS/TVQ)
- Vérification de cohérence des montants

✅ **Article 8 - Redaction PII**:
- Masquage automatique des informations personnelles dans les logs
- Formats redactés: NAS, cartes de crédit, emails, téléphones

**Exemple**:
```python
# Dans les logs
"Processing file: facture_[REDACTED].pdf"  # Nom de fichier anonymisé
"Supplier: Entreprise ABC Inc."            # Nom d'entreprise conservé (non-PII)
"Email: [EMAIL_REDACTED]"                  # Email masqué
```

---

### Decision Records (Traçabilité)

**Chaque analyse génère un Decision Record** dans `logs/decisions/`:

**Contenu du DR**:
```json
{
  "decision_id": "DR-20251118-143000-abc123",
  "timestamp": "2025-11-18T14:30:00Z",
  "actor": "document_analyzer_tool",
  "decision": "analyze_document",
  "task_id": "task-456",
  "reasoning": "User requested invoice analysis",
  "tools_used": ["document_analyzer_pme"],
  "parameters": {
    "file_name": "facture_nov_2025.pdf",
    "analysis_type": "invoice"
  },
  "signature": {
    "algorithm": "EdDSA",
    "public_key": "...",
    "signature": "..."
  }
}
```

**Avantages**:
- ✅ **Non-répudiation**: Signature cryptographique
- ✅ **Auditabilité**: Traçabilité complète de toutes les actions
- ✅ **Conformité**: Prêt pour audits CAI (Commission d'accès à l'information)

---

### Sécurité des données

**Protection des données**:
1. **Traitement local**: Aucune donnée envoyée à des serveurs externes
2. **Cleanup automatique**: Fichiers temporaires supprimés après traitement
3. **Pas de stockage**: Documents non conservés après analyse
4. **Logs sécurisés**: PII redactée dans tous les logs

**Garanties**:
- ❌ Aucune donnée transmise à des tiers
- ❌ Aucun stockage permanent des documents
- ✅ Suppression garantie des fichiers temporaires
- ✅ Conformité PIPEDA et RGPD

---

## Support

### Documentation complémentaire

- **Guide technique**: `docs/PHASE_6_1_ERROR_HANDLING_SUMMARY.md`
- **Rapport de conformité**: `docs/PHASE_6_3_COMPLIANCE_REPORT.md`
- **Tests**: `docs/PHASE_6_2_TESTING_SUMMARY.md`
- **Architecture**: `CLAUDE.md`

---

### FAQ

**Q: Puis-je analyser plusieurs fichiers en même temps?**
R: Non, l'interface actuelle supporte un fichier à la fois. Analysez-les séquentiellement.

**Q: Les données de mon document sont-elles envoyées à des serveurs externes?**
R: Non. Tout le traitement est local. Aucune donnée n'est transmise.

**Q: Combien de temps sont conservés les résultats?**
R: Les résultats sont affichés dans l'interface et exportables. FilAgent ne les stocke pas de manière permanente. Exportez-les pour les conserver.

**Q: Puis-je analyser des factures en anglais?**
R: Oui. L'outil supporte le français et l'anglais. Les calculs TPS/TVQ fonctionnent dans les deux langues.

**Q: Comment vérifier la signature EdDSA des exports JSON?**
R: Voir la section [Export JSON](#format-json-avec-signature-eddsa) pour un exemple de code Python.

**Q: L'outil supporte-t-il l'OCR pour les PDF scannés?**
R: Non, pas actuellement. Les PDF doivent contenir du texte sélectionnable.

**Q: Quelle est la précision de l'extraction?**
R: L'extraction de texte est très fiable (>95%). L'analyse structurée (factures, contrats) dépend de la qualité du formatage du document original.

---

### Contact

**Problèmes techniques**: Créer un ticket dans le système de suivi

**Questions de conformité**: Consulter le responsable de la protection des données

**Suggestions**: Les retours d'expérience sont les bienvenus pour améliorer l'outil

---

**Version du guide**: 1.0.0
**Dernière mise à jour**: 2025-11-18
**Compatible avec**: FilAgent v2.3.0+
