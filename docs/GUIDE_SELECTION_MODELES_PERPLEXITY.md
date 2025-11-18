# Guide de Sélection des Modèles Perplexity - FilAgent

**Date**: 2025-11-17
**Version**: 1.0.0
**Auteur**: FilAgent Team

---

## 📋 Table des Matières

1. [Présentation](#présentation)
2. [Modèles Disponibles](#modèles-disponibles)
3. [Interface de Sélection](#interface-de-sélection)
4. [Scripts de Benchmark](#scripts-de-benchmark)
5. [Recommandations par Difficulté](#recommandations-par-difficulté)
6. [Guide d'Utilisation](#guide-dutilisation)

---

## 🎯 Présentation

Ce document décrit le système de sélection dynamique de modèles Perplexity intégré à FilAgent. Le système permet de:

- **Choisir le modèle optimal** selon la difficulté de la requête
- **Comparer les performances** de différents modèles
- **Optimiser les coûts** en utilisant le bon modèle au bon moment
- **Maintenir la qualité** tout en contrôlant la latence

### Nouveaux Fichiers Créés

1. **Interface Gradio avec sélecteur**: `gradio_app_model_selector.py`
2. **Script de benchmark complet**: `scripts/benchmark_perplexity_models.py`
3. **Script de démonstration rapide**: `scripts/demo_model_comparison.py`
4. **Ce guide**: `docs/GUIDE_SELECTION_MODELES_PERPLEXITY.md`

---

## 📊 Modèles Disponibles

FilAgent supporte 5 modèles Perplexity avec des caractéristiques distinctes:

### 1. Sonar Small - Rapide 🚀

**Nom complet**: `llama-3.1-sonar-small-128k-online`

- **Latence**: Très faible (<300ms)
- **Qualité**: Bonne pour questions simples
- **Coût**: $ (économique)
- **Fonctionnalités**: Recherche web, Rapide
- **Cas d'usage**: FAQ, calculs simples, recherche factuelle

**Quand l'utiliser**:
- Questions factuelles directes
- Calculs simples (TPS/TVQ)
- Recherches d'information basiques
- Lorsque la vitesse est prioritaire

### 2. Sonar Large - Équilibré ⚖️

**Nom complet**: `llama-3.1-sonar-large-128k-online`

- **Latence**: Faible (<500ms)
- **Qualité**: Très bonne
- **Coût**: $$ (modéré)
- **Fonctionnalités**: Recherche web, Équilibré
- **Cas d'usage**: Analyse de conformité, explications techniques

**Quand l'utiliser**:
- Analyse de conformité (Loi 25, RGPD)
- Explications techniques détaillées
- Raisonnement modéré
- **Recommandé comme défaut** pour usage général

### 3. Sonar Huge - Maximum Qualité 🎯

**Nom complet**: `llama-3.1-sonar-huge-128k-online`

- **Latence**: Moyenne (<1s)
- **Qualité**: Excellence
- **Coût**: $$$ (premium)
- **Fonctionnalités**: Recherche web, Précis, Complexe
- **Cas d'usage**: Analyse juridique, décisions automatisées

**Quand l'utiliser**:
- Raisonnement complexe multi-étapes
- Analyse juridique approfondie
- Décisions automatisées critiques
- Lorsque la qualité est absolument prioritaire

### 4. Llama 8B Instruct - Économique 💰

**Nom complet**: `llama-3.1-8b-instruct`

- **Latence**: Très faible (<200ms)
- **Qualité**: Bonne
- **Coût**: $ (très économique)
- **Fonctionnalités**: Rapide, Économique
- **Cas d'usage**: Tâches générales, économique

**Quand l'utiliser**:
- Environnement sans accès Internet
- Budget très limité
- Tâches générales ne nécessitant pas de recherche web
- Tests et développement

### 5. Llama 70B Instruct - Puissant 💪

**Nom complet**: `llama-3.1-70b-instruct`

- **Latence**: Moyenne (<800ms)
- **Qualité**: Excellente
- **Coût**: $$ (modéré)
- **Fonctionnalités**: Puissant, Précis
- **Cas d'usage**: Raisonnement complexe, qualité élevée

**Quand l'utiliser**:
- Raisonnement complexe sans besoin de recherche web
- Alternative à Sonar Huge pour réduire les coûts
- Contexte privé nécessitant l'absence de recherche web

---

## 🖥️ Interface de Sélection

### Lancement de l'Interface

```bash
# Depuis le répertoire FilAgent
python gradio_app_model_selector.py
```

L'interface sera accessible sur: **http://localhost:7861**

### Fonctionnalités de l'Interface

#### 1. Onglet "Chat avec Modèle"

- **Sélecteur de modèle**: Dropdown pour choisir le modèle actif
- **Informations du modèle**: Affichage des caractéristiques du modèle sélectionné
- **Chat interactif**: Conversation avec le modèle sélectionné
- **Métriques en temps réel**: Temps de réponse, tokens utilisés
- **Exemples de questions**: Questions prédéfinies par niveau de difficulté

#### 2. Onglet "Comparaison de Modèles"

- **Test simultané**: Compare 3 modèles sur la même question
- **Affichage côte-à-côte**: Résultats formatés en Markdown
- **Métriques comparatives**: Temps, tokens, qualité
- **Questions de comparaison**: Exemples pour tester les différences

#### 3. Onglet "Informations Modèles"

- **Documentation complète**: Détails de chaque modèle
- **Cas d'usage**: Quand utiliser chaque modèle
- **Caractéristiques techniques**: Latence, qualité, coût

---

## 🔬 Scripts de Benchmark

### Script de Démonstration Rapide

**Fichier**: `scripts/demo_model_comparison.py`

Teste **3 modèles** avec **1 question par niveau** de difficulté (9 tests au total).

```bash
# Exécution
pdm run python scripts/demo_model_comparison.py
```

**Sortie**: Rapport comparatif en console avec recommandations.

**Durée**: ~2-3 minutes

### Script de Benchmark Complet

**Fichier**: `scripts/benchmark_perplexity_models.py`

Teste **5 modèles** avec **3 questions par niveau** de difficulté (45 tests au total).

```bash
# Exécution
pdm run python scripts/benchmark_perplexity_models.py
```

**Sorties**:
- `eval/benchmarks/perplexity/benchmark_YYYYMMDD_HHMMSS.json` (résultats bruts)
- `eval/benchmarks/perplexity/benchmark_YYYYMMDD_HHMMSS.md` (rapport formaté)

**Durée**: ~10-15 minutes

### Questions de Test par Niveau

#### FAIBLE Difficulté
1. Quelle est la capitale du Québec?
2. Combien font 15% de 1000$?
3. Quel est le taux de TPS au Canada?

#### MOYEN Difficulté
1. Explique les différences entre la Loi 25 du Québec et le RGPD européen
2. Calcule le montant total TTC (TPS 5% + TVQ 9.975%) pour une facture de 2450$ HT
3. Quels sont les trois principaux risques juridiques pour une PME québécoise qui utilise l'IA sans conformité?

#### ÉLEVÉ Difficulté
1. Processus complet de mise en conformité Loi 25 pour un système d'IA d'analyse de CV
2. Comparaison de 3 modèles LLM pour une PME selon coût, latence, qualité et conformité
3. Traçabilité complète pour une décision automatisée de refus de crédit selon Loi 25

---

## 🎯 Recommandations par Difficulté

### Configuration Recommandée

```yaml
# config/agent.yaml
model:
  backend: "perplexity"

  # Sélection dynamique selon difficulté de la requête
  models:
    easy: "llama-3.1-sonar-small-128k-online"
    medium: "llama-3.1-sonar-large-128k-online"
    hard: "llama-3.1-sonar-huge-128k-online"

  # Ou modèle unique par défaut
  path: "llama-3.1-sonar-large-128k-online"
```

### Matrice de Décision

| Critère | Small | Large | Huge | 8B | 70B |
|---------|-------|-------|------|-----|-----|
| **Latence < 300ms** | ✅ | ⚠️ | ❌ | ✅ | ❌ |
| **Qualité > 90%** | ❌ | ⚠️ | ✅ | ❌ | ✅ |
| **Recherche web** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **Coût $** | ✅ | ⚠️ | ❌ | ✅ | ⚠️ |
| **Raisonnement complexe** | ❌ | ⚠️ | ✅ | ❌ | ✅ |

**Légende**: ✅ Excellent | ⚠️ Acceptable | ❌ Limité

### Par Cas d'Usage Métier

#### Comptabilité & Finance
- **Calculs simples** (TPS/TVQ): Sonar Small
- **Analyse financière**: Sonar Large
- **Audit complexe**: Sonar Huge

#### Conformité & Juridique
- **Vérification basique**: Sonar Small
- **Analyse réglementaire**: Sonar Large
- **Décisions automatisées**: Sonar Huge (**requis** pour Decision Records critiques)

#### Support Client
- **FAQ standard**: Sonar Small ou 8B Instruct
- **Questions techniques**: Sonar Large
- **Problèmes complexes**: Sonar Huge

#### Analyse de Documents
- **Extraction simple**: Sonar Small
- **Analyse sémantique**: Sonar Large
- **Analyse juridique**: Sonar Huge

---

## 📖 Guide d'Utilisation

### Étape 1: Vérifier la Clé API

```bash
# Assurez-vous que PERPLEXITY_API_KEY est configurée dans .env
grep PERPLEXITY_API_KEY .env
```

Si absente, ajoutez-la:
```bash
echo "PERPLEXITY_API_KEY=pplx-votre-cle-ici" >> .env
```

Obtenez une clé sur: https://www.perplexity.ai/settings/api

### Étape 2: Installer les Dépendances

```bash
# Le package openai est requis pour l'API Perplexity
pdm add openai
# Ou si déjà installé:
pdm sync
```

### Étape 3: Tester avec la Démonstration

```bash
# Test rapide (9 requêtes)
pdm run python scripts/demo_model_comparison.py
```

### Étape 4: Lancer l'Interface Interactive

```bash
# Interface Gradio complète
python gradio_app_model_selector.py
```

Accédez à: http://localhost:7861

### Étape 5: Benchmark Complet (Optionnel)

```bash
# Benchmark exhaustif (45 requêtes)
pdm run python scripts/benchmark_perplexity_models.py
```

Consultez les résultats dans: `eval/benchmarks/perplexity/`

### Étape 6: Intégration dans FilAgent

Pour utiliser la sélection dynamique dans le code:

```python
from runtime.model_interface import init_model, GenerationConfig

# Déterminer la difficulté (à implémenter selon votre logique)
difficulty = detect_query_difficulty(user_query)

# Sélection du modèle
model_map = {
    "easy": "llama-3.1-sonar-small-128k-online",
    "medium": "llama-3.1-sonar-large-128k-online",
    "hard": "llama-3.1-sonar-huge-128k-online"
}

model_name = model_map[difficulty]

# Charger et utiliser
model = init_model(backend="perplexity", model_path=model_name, config={})
result = model.generate(prompt=user_query, config=GenerationConfig())
```

---

## 💡 Bonnes Pratiques

### 1. Détection de Difficulté

Implémentez une logique de détection basée sur:
- **Longueur de la requête**: Plus long = plus complexe
- **Mots-clés**: "analyse", "compare", "explique en détail" = complexe
- **Type de tâche**: Calcul simple vs raisonnement multi-étapes
- **Domaine**: Juridique/conformité = souvent complexe

### 2. Optimisation des Coûts

- Utilisez Sonar Small pour 60-70% des requêtes (FAQ, calculs)
- Sonar Large pour 25-30% (analyse standard)
- Sonar Huge pour 5-10% (décisions critiques uniquement)

### 3. Monitoring

Suivez ces métriques:
- Latence moyenne par modèle
- Distribution des requêtes par modèle
- Coût total par modèle
- Taux de satisfaction utilisateur par modèle

### 4. Conformité Loi 25

Pour les décisions automatisées critiques:
- **Toujours utiliser** Sonar Huge ou 70B Instruct
- **Générer un Decision Record** signé
- **Tracer la provenance** complète
- **Permettre la contestation** avec explication

---

## 🔧 Dépannage

### Erreur: "PERPLEXITY_API_KEY non définie"

**Solution**: Configurez la clé dans `.env`:
```bash
echo "PERPLEXITY_API_KEY=votre-cle" >> .env
```

### Erreur: "Module 'openai' non trouvé"

**Solution**: Installez le package:
```bash
pdm add openai
```

### Erreur: "Failed to load model"

**Vérifications**:
1. Clé API valide
2. Nom du modèle correct (voir liste ci-dessus)
3. Connexion Internet active (pour modèles "-online")

### Interface Gradio ne se lance pas

**Solution**: Vérifiez les dépendances:
```bash
pdm install -G ui  # Installe gradio
```

---

## 📊 Résultats Attendus du Benchmark

Après exécution du benchmark complet, vous devriez observer:

### Latence

- **Sonar Small**: 200-400ms
- **Sonar Large**: 400-700ms
- **Sonar Huge**: 700-1200ms
- **8B Instruct**: 150-300ms
- **70B Instruct**: 500-900ms

### Qualité (subjective)

- **Questions simples**: Tous modèles > 85%
- **Questions moyennes**: Large/Huge/70B > 80%, Small/8B ~70%
- **Questions complexes**: Huge/70B > 85%, Large ~75%, Small/8B < 65%

### Coût Relatif (estimé)

- **8B Instruct**: 1x (référence)
- **Sonar Small**: 1.5x
- **Sonar Large**: 2.5x
- **70B Instruct**: 3x
- **Sonar Huge**: 4x

---

## 🎓 Conclusion

Le système de sélection de modèles Perplexity permet à FilAgent de:

1. **Optimiser les coûts** en utilisant le bon modèle au bon moment
2. **Maintenir la qualité** pour les tâches critiques
3. **Réduire la latence** pour les requêtes simples
4. **Respecter la conformité** avec Decision Records appropriés

**Recommandation générale**: Utilisez **Sonar Large** comme défaut, et ajustez selon le cas d'usage.

---

**Mise à jour CLAUDE.md**: Ajoutez cette section à votre fichier CLAUDE.md:

```markdown
## Sélection de Modèles Perplexity

FilAgent supporte 5 modèles Perplexity avec sélection dynamique:

- **sonar-small-128k-online**: Rapide, questions simples
- **sonar-large-128k-online**: Équilibré (recommandé par défaut)
- **sonar-huge-128k-online**: Maximum qualité, raisonnement complexe
- **8b-instruct**: Économique, sans web
- **70b-instruct**: Puissant, sans web

**Interface interactive**: `python gradio_app_model_selector.py` (port 7861)
**Benchmark**: `scripts/benchmark_perplexity_models.py`
**Documentation**: `docs/GUIDE_SELECTION_MODELES_PERPLEXITY.md`
```

---

**Auteur**: FilAgent Team
**Date**: 2025-11-17
**Version**: 1.0.0
