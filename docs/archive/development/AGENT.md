# 🎯 TASK CARD: Configuration HTN Planning

**ID Task**: HTN-INT-002  
**Titre**: Créer fichier de configuration config/agent.yaml  
**Phase**: Phase 1 - Configuration Infrastructure  
**Priorité**: 🟠 P1 - HAUTE  
**Estimation**: 30-60 minutes  
**Dépendances**: Aucune (peut être exécuté en parallèle de HTN-INT-001)  
**Assigné à**: Agent/Développeur  

---

## 🔄 MISE À JOUR 2025-11-07

- ✅ Scan de secrets `detect-secrets 1.5.0` exécuté — aucun secret actif détecté (rapport dans `audit/reports/`).
- ✅ Journalisation : ajout d'un masquage automatique PII avant écriture + test unitaire `tests/test_logging_pii.py`.
- 📌 Prochaine étape liée : surveiller les prochaines exécutions de scan et étendre la couverture PII si de nouveaux champs apparaissent.

## 📋 CONTEXTE DU PROJET

### Situation Actuelle
FilAgent nécessite un fichier de configuration structuré pour gérer les paramètres du système HTN Planning. La configuration doit être:
- **Externalisée** - Séparation code/config (12-factor app)
- **Versionnée** - Traçabilité des changements de config
- **Validable** - Schema YAML pour éviter erreurs de typage
- **Documentée** - Commentaires inline pour chaque paramètre

### Objectif Global
Créer un fichier `config/agent.yaml` contenant tous les paramètres de configuration du système HTN avec:
- Valeurs par défaut sécuritaires (Safety by Design)
- Feature flags pour activation progressive
- Paramètres de performance ajustables
- Niveaux de validation configurables

### Valeurs Fondamentales du Projet
1. **Safety by Design** - Valeurs par défaut sécuritaires
2. **Separation of Concerns** - Config séparée du code
3. **Documentation** - Chaque paramètre expliqué
4. **Traçabilité** - Versioning et changelog

---

## 🎯 OBJECTIF DE CE TASK

### Mission
Créer le fichier `config/agent.yaml` contenant la configuration complète du système HTN avec:
- ✅ Feature flags (activation/désactivation modules)
- ✅ Paramètres planificateur (stratégies, profondeur)
- ✅ Paramètres exécuteur (workers, timeouts)
- ✅ Paramètres vérificateur (niveaux validation)
- ✅ Paramètres logging et traçabilité
- ✅ Configurations par environnement (dev, prod)

### Résultat Attendu
Après ce task:
- Fichier config/agent.yaml créé et documenté
- Tous les paramètres HTN définis avec valeurs par défaut
- Documentation inline complète
- Exemples de configurations pour différents cas d'usage
- Validable via schema YAML (optionnel)

---

## 📂 FICHIERS À CRÉER

### Fichier Principal
```
📁 /Volumes/DevSSD/FilAgent/
└── config/
    └── agent.yaml  ← CRÉER CE FICHIER
```

### Structure Recommandée
```
📁 /Volumes/DevSSD/FilAgent/
├── config/
│   ├── agent.yaml           ← Configuration principale
│   ├── agent.dev.yaml       ← Overrides pour dev (optionnel)
│   ├── agent.prod.yaml      ← Overrides pour prod (optionnel)
│   └── schema.yaml          ← Schema de validation (optionnel)
└── runtime/
    └── agent.py             ← Charge cette config
```

---

## 🔧 CONTENU DU FICHIER À CRÉER

### Structure Complète config/agent.yaml

```yaml
# ============================================================================
# FilAgent - Configuration Système HTN Planning
# ============================================================================
# 
# Ce fichier contient tous les paramètres de configuration du système HTN.
# Respecte les principes Safety by Design avec valeurs par défaut sécuritaires.
#
# Version: 1.0.0
# Date: 2025-11-04
# Conformité: Loi 25, RGPD, AI Act, NIST AI RMF
# ============================================================================

# ============================================================================
# SECTION 1: FEATURE FLAGS
# ============================================================================
# Contrôle l'activation/désactivation de modules entiers
# Défaut: false (activation progressive, Safety by Design)

features:
  # Active le planificateur HTN pour requêtes complexes
  # Impact: Si false, agent utilise uniquement mode simple
  # Production: Commencer à false, activer après validation
  htn_enabled: false
  
  # Active le mode de debug avec logs détaillés
  # Impact: Augmente volume de logs (~3x), ralentit exécution (~10%)
  # Production: false (sauf troubleshooting)
  debug_mode: false
  
  # Active la parallélisation des tâches indépendantes
  # Impact: Améliore performance mais augmente complexité
  # Production: true (après tests de charge)
  parallel_execution: true
  
  # Active la validation stricte des résultats
  # Impact: Ralentit exécution (~20%) mais augmente fiabilité
  # Production: true (conformité Loi 25)
  strict_validation: true
  
  # Active l'enregistrement des Decision Records
  # Impact: Crée fichiers ADR pour chaque décision majeure
  # Production: true (traçabilité obligatoire)
  decision_records: true


# ============================================================================
# SECTION 2: PLANIFICATEUR HTN
# ============================================================================
# Configuration du HierarchicalPlanner
# Responsable: Décomposition de requêtes en graphe de tâches

planner:
  # Stratégie de planification par défaut
  # Options: "llm_based" | "rule_based" | "hybrid"
  # - llm_based: Utilise LLM pour décomposition intelligente (flexible)
  # - rule_based: Règles prédéfinies (rapide, déterministe)
  # - hybrid: Combinaison des deux (recommandé)
  default_strategy: "hybrid"
  
  # Profondeur maximale de décomposition hiérarchique
  # Range: 1-5 (valeurs plus élevées = plus d'étapes, plus lent)
  # Recommandation: 3 (équilibre complexité/performance)
  # Impact: Limite la complexité des plans générés
  max_decomposition_depth: 3
  
  # Nombre maximum de tentatives si planification échoue
  # Range: 1-5
  # Impact: Augmente robustesse mais peut ralentir sur erreurs
  max_retry_attempts: 2
  
  # Timeout pour génération d'un plan (secondes)
  # Range: 5-120
  # Production: 30 (évite blocages sur requêtes complexes)
  planning_timeout_sec: 30
  
  # Score de confiance minimum pour accepter un plan (0-1)
  # Range: 0.0-1.0
  # Recommandation: 0.7 (équilibre qualité/disponibilité)
  # Impact: Plans avec score < seuil sont rejetés
  min_confidence_score: 0.7
  
  # Active les traces détaillées de planification
  # Impact: Logs détaillés pour debug (conformité RGPD)
  # Production: true (traçabilité obligatoire)
  enable_tracing: true


# ============================================================================
# SECTION 3: EXÉCUTEUR DE TÂCHES
# ============================================================================
# Configuration du TaskExecutor
# Responsable: Orchestration et exécution du graphe de tâches

executor:
  # Stratégie d'exécution par défaut
  # Options: "sequential" | "parallel" | "adaptive"
  # - sequential: Une tâche à la fois (sécuritaire)
  # - parallel: Parallélisation maximale (performant)
  # - adaptive: Hybride selon ressources (recommandé)
  default_strategy: "adaptive"
  
  # Nombre maximum de workers parallèles
  # Range: 1-16
  # Recommandation: 4 (équilibre perf/ressources)
  # Impact: Plus de workers = plus rapide mais plus de RAM
  max_workers: 4
  
  # Timeout par tâche individuelle (secondes)
  # Range: 10-300
  # Production: 60 (évite tâches bloquées indéfiniment)
  timeout_per_task_sec: 60
  
  # Timeout pour exécution complète du plan (secondes)
  # Range: 30-600
  # Production: 300 (5 minutes max pour plan complet)
  total_execution_timeout_sec: 300
  
  # Nombre maximum de tentatives par tâche si échec
  # Range: 0-5
  # Impact: 0 = pas de retry, >0 = résilience accrue
  max_task_retries: 1
  
  # Délai entre tentatives (secondes)
  # Range: 1-30
  # Production: 5 (évite surcharge immédiate)
  retry_delay_sec: 5
  
  # Continue l'exécution même si tâches optionnelles échouent
  # Impact: true = plan partiellement exécuté peut être valide
  # Production: true (résilience)
  continue_on_optional_failure: true
  
  # Active l'isolation sandbox pour exécution de tâches
  # Impact: Sécurise l'exécution mais ralentit (~15%)
  # Production: true (Security by Design)
  enable_sandbox: true
  
  # Active les traces détaillées d'exécution
  # Impact: Logs détaillés pour debug (conformité RGPD)
  # Production: true (traçabilité obligatoire)
  enable_tracing: true


# ============================================================================
# SECTION 4: VÉRIFICATEUR DE RÉSULTATS
# ============================================================================
# Configuration du TaskVerifier
# Responsable: Validation et self-checks des résultats

verifier:
  # Niveau de vérification par défaut
  # Options: "basic" | "strict" | "paranoid"
  # - basic: Vérifications minimales (rapide)
  # - strict: Vérifications standard (équilibré)
  # - paranoid: Vérifications exhaustives (lent mais sûr)
  # Production: strict (conformité Loi 25)
  default_level: "strict"
  
  # Score de confiance minimum pour accepter un résultat (0-1)
  # Range: 0.0-1.0
  # Recommandation: 0.8 (haute qualité)
  # Impact: Résultats avec score < seuil sont rejetés
  min_confidence_score: 0.8
  
  # Active la validation de schéma JSON pour résultats structurés
  # Impact: Vérifie conformité avec schémas définis
  # Production: true (détection erreurs structurelles)
  enable_schema_validation: true
  
  # Active la détection d'anomalies via patterns
  # Impact: Détecte résultats incohérents ou suspects
  # Production: true (détection anomalies)
  enable_anomaly_detection: true
  
  # Active les self-checks automatiques
  # Impact: Tests unitaires automatiques sur résultats
  # Production: true (conformité AI Act)
  enable_self_checks: true
  
  # Active les traces détaillées de vérification
  # Impact: Logs détaillés pour debug (conformité RGPD)
  # Production: true (traçabilité obligatoire)
  enable_tracing: true


# ============================================================================
# SECTION 5: LOGGING ET TRAÇABILITÉ
# ============================================================================
# Configuration des logs et traçabilité (conformité Loi 25, RGPD)

logging:
  # Niveau de log global
  # Options: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"
  # Production: INFO (équilibre détail/volume)
  level: "INFO"
  
  # Format des logs
  # Options: "json" | "text"
  # Production: json (parsing automatique, intégration monitoring)
  format: "json"
  
  # Destination des logs
  # Options: "stdout" | "file" | "both"
  # Production: both (console + fichiers)
  output: "both"
  
  # Répertoire pour fichiers de logs
  # Production: /var/log/filagent ou ./logs
  log_directory: "./logs"
  
  # Taille maximale par fichier de log (MB)
  # Range: 10-1000
  # Production: 100 (rotation automatique)
  max_file_size_mb: 100
  
  # Nombre de fichiers de rotation à conserver
  # Range: 5-50
  # Production: 10 (2-3 semaines de logs typiquement)
  max_backup_count: 10
  
  # Inclure stack traces dans logs d'erreur
  # Impact: Détails techniques complets pour debug
  # Production: true (diagnostic)
  include_stacktraces: true
  
  # Logs WORM (Write-Once-Read-Many) pour audit
  # Impact: Logs immuables pour conformité légale
  # Production: true (conformité Loi 25)
  worm_logs: true


# ============================================================================
# SECTION 6: DÉCISION RECORDS (ADR)
# ============================================================================
# Configuration des Architecture Decision Records
# Conformité: AI Act (transparence), NIST AI RMF

decision_records:
  # Active l'enregistrement automatique des décisions
  # Impact: Crée fichier ADR pour chaque décision majeure
  # Production: true (traçabilité obligatoire)
  enabled: true
  
  # Répertoire pour stocker les ADR
  # Production: ./docs/decisions ou ./adr
  directory: "./docs/decisions"
  
  # Format des ADR
  # Options: "markdown" | "json"
  # Production: markdown (lisibilité humaine)
  format: "markdown"
  
  # Inclure contexte complet dans ADR
  # Impact: ADR plus volumineux mais autonomes
  # Production: true (conformité)
  include_full_context: true
  
  # Niveaux de décision à enregistrer
  # Options: ["critical", "major", "minor"]
  # Production: ["critical", "major"] (évite bruit)
  capture_levels:
    - "critical"
    - "major"


# ============================================================================
# SECTION 7: PERFORMANCE ET RESSOURCES
# ============================================================================
# Limites de ressources et optimisations

performance:
  # Limite mémoire par worker (MB)
  # Range: 256-4096
  # Production: 1024 (1GB par worker)
  max_memory_per_worker_mb: 1024
  
  # Limite CPU par worker (%)
  # Range: 10-100
  # Production: 80 (évite surcharge système)
  max_cpu_per_worker_percent: 80
  
  # Cache des plans fréquents
  # Impact: Réutilise plans similaires (performance)
  # Production: true (optimisation)
  enable_plan_caching: true
  
  # Taille maximale du cache de plans
  # Range: 10-1000
  # Production: 100 (équilibre RAM/performance)
  max_cache_size: 100
  
  # Durée de vie du cache (secondes)
  # Range: 300-86400 (5min - 24h)
  # Production: 3600 (1 heure)
  cache_ttl_sec: 3600


# ============================================================================
# SECTION 8: SÉCURITÉ ET CONFORMITÉ
# ============================================================================
# Paramètres de sécurité et conformité légale

security:
  # Active la validation des paramètres d'entrée
  # Impact: Vérifie que paramètres ne contiennent pas de code malveillant
  # Production: true (Security by Design)
  validate_inputs: true
  
  # Active l'isolation sandbox pour exécution
  # Impact: Exécute tâches dans environnement isolé
  # Production: true (sécurité)
  sandbox_execution: true
  
  # Bloque l'exécution de commandes système dangereuses
  # Impact: Liste noire de commandes (rm, format, etc.)
  # Production: true (sécurité)
  block_dangerous_commands: true
  
  # Active le chiffrement des données sensibles en transit
  # Impact: Chiffre paramètres/résultats sensibles
  # Production: true (conformité RGPD)
  encrypt_sensitive_data: true
  
  # Active l'anonymisation automatique des logs
  # Impact: Supprime PII des logs (emails, noms, etc.)
  # Production: true (conformité Loi 25)
  anonymize_logs: true


# ============================================================================
# SECTION 9: INTÉGRATIONS EXTERNES
# ============================================================================
# Configuration des intégrations avec outils externes

integrations:
  # Configuration LLM (pour planification)
  llm:
    provider: "anthropic"  # "anthropic" | "openai" | "custom"
    model: "claude-sonnet-4-20250514"
    temperature: 0.7
    max_tokens: 4000
    timeout_sec: 30
  
  # Configuration base de données (pour persistence)
  database:
    enabled: false  # Activer pour persistence long-terme
    type: "sqlite"  # "sqlite" | "postgresql" | "mongodb"
    connection_string: "sqlite:///./filagent.db"
    pool_size: 5
  
  # Configuration monitoring (pour observabilité)
  monitoring:
    enabled: false  # Activer en production
    provider: "prometheus"  # "prometheus" | "datadog" | "custom"
    endpoint: "http://localhost:9090"
    push_interval_sec: 60


# ============================================================================
# SECTION 10: ENVIRONNEMENTS
# ============================================================================
# Configurations spécifiques par environnement
# Note: Les valeurs ci-dessous peuvent être surchargées par
#       agent.dev.yaml, agent.prod.yaml, etc.

environments:
  # Configuration pour développement
  development:
    features:
      debug_mode: true
    logging:
      level: "DEBUG"
    performance:
      max_workers: 2  # Moins de charge sur machine dev
  
  # Configuration pour tests
  testing:
    features:
      htn_enabled: true
      parallel_execution: false  # Déterminisme pour tests
    executor:
      max_workers: 1
      timeout_per_task_sec: 10  # Tests rapides
    verifier:
      default_level: "paranoid"  # Validation maximale
  
  # Configuration pour production
  production:
    features:
      debug_mode: false
      htn_enabled: true
      strict_validation: true
      decision_records: true
    logging:
      level: "INFO"
      worm_logs: true
    security:
      validate_inputs: true
      sandbox_execution: true
      encrypt_sensitive_data: true
      anonymize_logs: true
    performance:
      max_workers: 4
      enable_plan_caching: true


# ============================================================================
# SECTION 11: MÉTADONNÉES
# ============================================================================
# Informations sur ce fichier de configuration

metadata:
  version: "1.0.0"
  created_at: "2025-11-04T00:00:00Z"
  updated_at: "2025-11-04T00:00:00Z"
  author: "FilAgent Team"
  description: "Configuration principale du système HTN Planning"
  schema_version: "1.0"
  
  # Changelog pour traçabilité
  changelog:
    - version: "1.0.0"
      date: "2025-11-04"
      author: "Claude (Anthropic) via Fil"
      changes:
        - "Création initiale du fichier de configuration"
        - "Définition de tous les paramètres HTN avec valeurs par défaut"
        - "Documentation inline complète"
        - "Configurations par environnement (dev, test, prod)"

# ============================================================================
# FIN DU FICHIER config/agent.yaml
# ============================================================================
```

---

## ✅ CRITÈRES DE SUCCÈS

### Tests de Validation Minimaux

Avant de considérer le task comme terminé, vérifier:

#### 1. Fichier Créé et Valide
```bash
# Test: Fichier existe
ls -la config/agent.yaml
# ✅ Fichier présent

# Test: YAML valide (syntaxe)
python -c "import yaml; yaml.safe_load(open('config/agent.yaml'))"
# ✅ Pas d'erreur de parsing

# Test: Structure conforme
python -c "
import yaml
config = yaml.safe_load(open('config/agent.yaml'))
assert 'features' in config
assert 'planner' in config
assert 'executor' in config
assert 'verifier' in config
print('✅ Structure valide')
"
```

#### 2. Valeurs Par Défaut Sécuritaires
```python
# Test: Feature flags désactivés par défaut
import yaml
config = yaml.safe_load(open('config/agent.yaml'))

assert config['features']['htn_enabled'] == False
assert config['features']['debug_mode'] == False
# ✅ Safety by Design respecté

# Test: Timeouts raisonnables
assert config['executor']['timeout_per_task_sec'] >= 10
assert config['executor']['total_execution_timeout_sec'] >= 30
# ✅ Pas de risque de blocage infini
```

#### 3. Documentation Complète
```bash
# Test: Commentaires présents
grep -c "#" config/agent.yaml
# ✅ Devrait retourner > 100 (documentation extensive)

# Test: Sections bien délimitées
grep -c "========" config/agent.yaml
# ✅ Devrait retourner > 20 (11 sections minimum)
```

#### 4. Chargement par Agent
```python
# Test: Agent peut charger la config
from runtime.agent import Agent
import yaml

config = yaml.safe_load(open('config/agent.yaml'))
agent = Agent(config)
# ✅ Pas d'erreur de chargement

# Test: Paramètres appliqués correctement
assert agent.htn_enabled == config['features']['htn_enabled']
# ✅ Configuration prise en compte
```

### Checklist de Validation

- [ ] ✅ Fichier config/agent.yaml créé
- [ ] ✅ Syntaxe YAML valide (parse sans erreur)
- [ ] ✅ Toutes les 11 sections présentes
- [ ] ✅ Feature flags avec valeurs par défaut sécuritaires
- [ ] ✅ Paramètres planner documentés
- [ ] ✅ Paramètres executor documentés
- [ ] ✅ Paramètres verifier documentés
- [ ] ✅ Configuration logging complète
- [ ] ✅ Configurations par environnement (dev, test, prod)
- [ ] ✅ Commentaires inline pour chaque paramètre
- [ ] ✅ Métadonnées et changelog présents
- [ ] ✅ Agent peut charger le fichier sans erreur

---

## 🚨 CONTRAINTES ET GARDE-FOUS

### Règles de Sécurité

1. **Valeurs par défaut TOUJOURS sécuritaires**
   - Features désactivées par défaut (`htn_enabled: false`)
   - Timeouts raisonnables (pas d'infini)
   - Validation stricte activée
   - Traçabilité activée

2. **Documentation obligatoire**
   - Chaque paramètre doit avoir un commentaire
   - Expliquer l'impact de chaque valeur
   - Donner des exemples de valeurs valides
   - Indiquer les valeurs de production recommandées

3. **Pas de secrets dans le fichier**
   - ❌ Pas de clés API
   - ❌ Pas de mots de passe
   - ❌ Pas de tokens
   - ✅ Utiliser variables d'environnement ou fichier séparé

4. **Versioning et traçabilité**
   - Section metadata avec version
   - Changelog pour chaque modification
   - Auteur et date de création

### Standards YAML

```yaml
# ✅ BON: Commentaires descriptifs
# Active le planificateur HTN pour requêtes complexes
# Impact: Si false, agent utilise uniquement mode simple
# Production: Commencer à false, activer après validation
htn_enabled: false

# ✅ BON: Valeurs explicites
timeout_per_task_sec: 60  # Integer explicite

# ✅ BON: Structure cohérente
features:
  htn_enabled: false
  debug_mode: false

# ❌ MAUVAIS: Pas de commentaire
htn_enabled: false

# ❌ MAUVAIS: Valeur dangereuse par défaut
timeout_per_task_sec: 999999  # Risque de blocage

# ❌ MAUVAIS: Structure incohérente
features:
  htn_enabled: false
debug_mode: false  # Devrait être sous features
```

---

## 📝 NOTES D'IMPLÉMENTATION

### Ordre de Développement Recommandé

1. **Phase 1: Structure de base** (5 min)
   - Créer fichier config/agent.yaml vide
   - Ajouter header avec métadonnées
   - Créer sections principales (11 sections)

2. **Phase 2: Features et Planner** (10 min)
   - Section 1: Feature Flags
   - Section 2: Planificateur HTN
   - Tester parsing YAML

3. **Phase 3: Executor et Verifier** (10 min)
   - Section 3: Exécuteur de Tâches
   - Section 4: Vérificateur de Résultats
   - Tester parsing YAML

4. **Phase 4: Infrastructure** (10 min)
   - Section 5: Logging et Traçabilité
   - Section 6: Decision Records
   - Section 7: Performance et Ressources

5. **Phase 5: Sécurité et Intégrations** (10 min)
   - Section 8: Sécurité et Conformité
   - Section 9: Intégrations Externes

6. **Phase 6: Environnements et Finalisation** (10 min)
   - Section 10: Environnements
   - Section 11: Métadonnées
   - Validation finale et tests

### Points d'Attention Spécifiques

⚠️ **Indentation YAML**
```yaml
# ❌ MAUVAIS: Indentation incorrecte (mélange tabs/spaces)
features:
	htn_enabled: false
  debug_mode: false

# ✅ BON: Indentation cohérente (2 espaces partout)
features:
  htn_enabled: false
  debug_mode: false
```

⚠️ **Types de données**
```yaml
# ✅ BON: Types explicites
timeout_per_task_sec: 60  # Integer
min_confidence_score: 0.7  # Float
htn_enabled: false  # Boolean
default_strategy: "hybrid"  # String

# ❌ MAUVAIS: Types ambigus
timeout_per_task_sec: "60"  # String au lieu de int
```

⚠️ **Commentaires multilignes**
```yaml
# ✅ BON: Commentaires courts et précis
# Active le planificateur HTN
htn_enabled: false

# ✅ BON: Commentaires structurés
# Active le planificateur HTN pour requêtes complexes
# Impact: Si false, agent utilise uniquement mode simple
# Production: Commencer à false, activer après validation
htn_enabled: false

# ❌ MAUVAIS: Commentaire trop long non structuré
# Ce paramètre active ou désactive le planificateur HTN qui est responsable de la décomposition des requêtes complexes en graphes de tâches exécutables avec parallélisation...
htn_enabled: false
```

---

## 🎯 LIVRABLES ATTENDUS

### 1. Fichier de Configuration
- `config/agent.yaml` complet et documenté
- Syntaxe YAML valide
- Toutes les 11 sections présentes
- Commentaires inline pour chaque paramètre

### 2. Tests de Validation
- Parse YAML sans erreur
- Structure conforme aux attentes
- Valeurs par défaut sécuritaires vérifiées
- Chargement par Agent réussi

### 3. Documentation
- Commentaires inline complets
- Section métadonnées avec version
- Changelog initialisé
- README.md mis à jour (optionnel)

---

## 📗 RESSOURCES

### Documentation YAML
- Spécification YAML 1.2: https://yaml.org/spec/1.2/spec.html
- Parser Python: https://pyyaml.org/wiki/PyYAMLDocumentation

### Exemples de Référence
- `/Volumes/DevSSD/FilAgent/planner/README.md` - Paramètres HTN
- `/Volumes/DevSSD/FilAgent/examples/config_example.yaml` - Template

### Validation de Configuration
```python
# Script pour valider config/agent.yaml
import yaml
import jsonschema

# Charger config
with open('config/agent.yaml') as f:
    config = yaml.safe_load(f)

# Valider structure minimale
required_sections = [
    'features', 'planner', 'executor', 'verifier',
    'logging', 'decision_records', 'performance',
    'security', 'integrations', 'environments', 'metadata'
]

for section in required_sections:
    assert section in config, f"Section manquante: {section}"

print("✅ Configuration valide!")
```

---

## 🚦 STATUT DU TASK

**État actuel**: 🟡 **À FAIRE**

**Prochaine action**: Créer config/agent.yaml selon structure ci-dessus

**Bloqueurs**: Aucun (indépendant de HTN-INT-001)

---

## 💬 QUESTIONS / CLARIFICATIONS

Si des questions se présentent pendant l'implémentation:

1. **Emplacement du fichier**: Où créer config/?
   → Racine du projet FilAgent: `/Volumes/DevSSD/FilAgent/config/`

2. **Format des commentaires**: Quel style adopter?
   → Style ci-dessus: commentaire multi-ligne avec Impact/Production

3. **Valeurs par environnement**: Créer fichiers séparés?
   → Optionnel dans ce task. Section 10 suffit pour commencer.

4. **Validation de schema**: Créer schema.yaml?
   → Optionnel dans ce task. Peut être fait dans HTN-INT-003.

---

**Task créé le**: 4 novembre 2025  
**Dernière mise à jour**: 4 novembre 2025  
**Auteur**: Claude (Anthropic) via Fil  
**Version**: 1.0.0
