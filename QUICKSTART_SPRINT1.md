# Quick Start - Corrections Sprint 1

**Objectif**: Corriger les 3 problèmes critiques en 1 journée  
**Pour**: Développeurs assignés au Sprint 1

---

## 🚀 Setup Initial (10 min)

```bash
# 1. Créer branche
git checkout -b fix/sprint1-critical-corrections

# 2. Installer dépendances
pip install black flake8 pytest pytest-cov

# 3. Baseline metrics
flake8 . --select=E722,F824 --count  # Note le nombre
```

---

## ✅ Task 1: Bare Except Blocks (1h 30min)

### Trouver tous les bare excepts
```bash
# Chercher le pattern
grep -rn "except:" memory/ tests/ runtime/ --include="*.py" | grep -v "except ("

# Résultat attendu: ~9 locations
```

### Corriger - Pattern à suivre
```python
# AVANT ❌
try:
    result = parse_timestamp(value)
except:
    return False

# APRÈS ✅
try:
    result = parse_timestamp(value)
except (ValueError, TypeError) as e:
    logger.warning(f"Failed to parse timestamp: {value}", exc_info=True)
    return False
```

### Fichiers prioritaires
1. `memory/retention.py` (6+ locations)
   - Lignes ~26, 50, 78, 105, 132, 158
2. `test_filagent_capabilities.py` (2 locations)
3. `tests/test_document_analyzer_security.py` (1 location)

### Validation
```bash
# Vérifier qu'il ne reste aucun bare except
flake8 . --select=E722 --count
# Objectif: 0

# Tests de régression
pytest tests/test_retention.py -v
pytest tests/test_filagent_capabilities.py -v
```

---

## ✅ Task 2: Global State Thread-Safety (1h)

### Fichiers à modifier
1. `planner/work_stealing.py`
2. `planner/plan_cache.py`  
3. `planner/metrics.py`

### Pattern à ajouter
```python
import threading

# Ajouter en haut du module
_instance_lock = threading.Lock()
_executor_instance = None

def get_executor():
    """Thread-safe singleton getter."""
    global _executor_instance
    if _executor_instance is None:
        with _instance_lock:  # Double-checked locking
            if _executor_instance is None:
                _executor_instance = Executor()
    return _executor_instance
```

### Exemple complet - work_stealing.py
```python
# Ligne 15-30
import threading
from typing import Optional

_instance_lock = threading.Lock()
_executor_instance: Optional[WorkStealingExecutor] = None

def get_work_stealing_executor() -> WorkStealingExecutor:
    """Get or create the global work-stealing executor (thread-safe)."""
    global _executor_instance
    if _executor_instance is None:
        with _instance_lock:
            if _executor_instance is None:
                _executor_instance = WorkStealingExecutor()
    return _executor_instance
```

### Validation
```bash
# Test de concurrence
pytest tests/test_concurrency.py -v -n 8
# Si pas de test concurrency, créer un test simple:
```

```python
# tests/test_concurrency_basic.py
import pytest
from concurrent.futures import ThreadPoolExecutor
from planner.work_stealing import get_work_stealing_executor

@pytest.mark.unit
def test_singleton_thread_safety():
    """Test que le singleton est thread-safe."""
    instances = []
    
    def get_instance():
        instances.append(get_work_stealing_executor())
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(get_instance) for _ in range(100)]
        for future in futures:
            future.result()
    
    # Toutes les instances doivent être la même
    assert len(set(id(i) for i in instances)) == 1
```

---

## ✅ Task 3: Debug Prints → Logging (1h 30min)

### Trouver tous les prints
```bash
# Chercher dans le code de production (pas tests)
grep -rn "print(" runtime/ planner/ tools/ --include="*.py" | grep -v test

# Résultat attendu: 20+ lignes
```

### Correction automatique (recommandé)
```bash
# Script de remplacement
cat > replace_prints.sh << 'EOF'
#!/bin/bash

# runtime/agent.py - Debug HTN
sed -i 's/print(f"\\n\[HTN-DEBUG\]/logger.debug("[HTN]/g' runtime/agent.py
sed -i 's/print(f"\[HTN-DEBUG\]/logger.debug("[HTN]/g' runtime/agent.py

# planner/executor.py - Info executor
sed -i 's/print(f"\[EXECUTOR\]/logger.info("[EXECUTOR]/g' planner/executor.py
sed -i 's/print(f"\\n\[EXECUTOR\]/logger.info("[EXECUTOR]/g' planner/executor.py

# Nettoyer les newlines de debug
sed -i 's/\\n\[/[/g' runtime/agent.py planner/executor.py

echo "✅ Remplacement terminé"
EOF

chmod +x replace_prints.sh
./replace_prints.sh
```

### Correction manuelle (si script échoue)
```python
# AVANT ❌
print(f"\n[HTN-DEBUG] _requires_planning called for query: {query[:100]}...")

# APRÈS ✅
logger.debug("[HTN] Planning check for query: %s...", query[:100])
```

### Validation
```bash
# Vérifier qu'il ne reste aucun print dans prod
grep -rn "print(" runtime/ planner/ tools/ --include="*.py" | grep -v test
# Objectif: 0 résultats

# Tests fonctionnels
pytest tests/test_agent.py -v
pytest tests/test_executor.py -v
```

---

## ✅ Task 4: Fix F824 Warning (15min)

### Fichier: `runtime/template_loader.py` ligne 251

```python
# AVANT ❌
def clear_template_cache():
    """Clear the global template cache."""
    global _template_loader  # ← Déclaré mais jamais assigné
    if _template_loader:
        _template_loader.reload_templates()
    get_template_loader.cache_clear()

# APRÈS ✅ (Option préférée: retirer global)
def clear_template_cache():
    """Clear the global template cache."""
    # Utiliser directement la fonction
    if get_template_loader.cache_info().currsize > 0:
        loader = get_template_loader()
        loader.reload_templates()
        get_template_loader.cache_clear()
```

### Validation
```bash
flake8 runtime/template_loader.py --select=F824
# Objectif: 0 erreurs
```

---

## ✅ Task 5: Black Formatting (30min)

```bash
# Auto-formatter sur tout le projet
black . --line-length 100

# Vérifier
black --check .

# Corriger imports non utilisés (optionnel)
pip install autoflake
autoflake --remove-all-unused-imports --in-place --recursive runtime/ planner/ tools/
```

---

## ✅ Validation Finale (30min)

### Tests complets
```bash
# 1. Linting
flake8 . --select=E9,F63,F7,F82 --count
# Objectif: 0 erreurs critiques

# 2. Tests unitaires
pytest tests/ -m unit -v
# Objectif: Pas de régression

# 3. Couverture
pytest tests/ --cov=runtime --cov=planner --cov=tools --cov-report=term
# Objectif: > 84% (ne pas régresser)
```

### Checklist finale
- [ ] Bare excepts: 0 (était: 9)
- [ ] Thread locks: 3 fichiers protégés
- [ ] Debug prints: 0 dans prod (était: 20+)
- [ ] F824 warning: 0 (était: 1)
- [ ] Black format: ✅ passé
- [ ] Tests: ≥95% passants
- [ ] Couverture: ≥84%

---

## 📤 Commit et PR

```bash
# Stage tous les changements
git add .

# Commit avec message descriptif
git commit -m "fix: critical code quality and security corrections (Sprint 1)

- Fixed 9 bare except blocks for proper error handling
- Added threading locks for 3 global singleton managers
- Replaced 20+ debug prints with proper logging
- Fixed F824 warning in template_loader.py
- Applied Black formatting (100 chars)
- All tests passing (95.5%+ pass rate)
- Coverage maintained (>84%)

BREAKING: None
SECURITY: Improved error visibility and thread safety
"

# Push
git push origin fix/sprint1-critical-corrections

# Créer PR sur GitHub
# Titre: "fix: Sprint 1 critical corrections (bare excepts, thread safety, logging)"
# Description: Copier la checklist de validation
```

---

## 🐛 Troubleshooting

### Problème: Tests échouent après corrections bare excepts
**Solution**: Vérifier que les tests attendent les bonnes exceptions
```python
# Si test fait:
with pytest.raises(Exception):
    func()

# Changer pour exception spécifique:
with pytest.raises(ValueError):
    func()
```

### Problème: Import errors après corrections
**Solution**: Vérifier les imports manquants
```python
import logging
import threading
from typing import Optional
```

### Problème: Black change trop de fichiers
**Solution**: Commit les changements Black séparément
```bash
git add . && git commit -m "style: apply Black formatting"
# Puis faire les corrections dans un second commit
```

---

## ⏱️ Timeline Réaliste

| Task | Temps | Cumulatif |
|------|-------|-----------|
| Setup | 10min | 10min |
| Bare excepts | 1h30 | 1h40 |
| Thread locks | 1h | 2h40 |
| Debug prints | 1h30 | 4h10 |
| F824 fix | 15min | 4h25 |
| Black format | 30min | 4h55 |
| Validation | 30min | 5h25 |
| PR creation | 15min | **5h40** |

**Total**: ~6 heures pour 1 développeur expérimenté

---

## 📞 Support

**Bloqué?** Consulter:
1. [AUDIT_POST_MERGE_MLOPS.md](AUDIT_POST_MERGE_MLOPS.md) - Détails techniques
2. [PLAN_ACTION_AMELIORATION.md](PLAN_ACTION_AMELIORATION.md) - Plan complet
3. Issues GitHub - Poser une question
4. Slack #dev-filagent - Chat avec l'équipe

---

**Créé par**: Ingénieur MLOps  
**Date**: 2026-02-06  
**Version**: 1.0

---

## ✅ Après Sprint 1

Une fois ce sprint terminé:
1. ✅ Code production-ready
2. ✅ 0 erreurs critiques
3. ✅ Logs propres
4. ✅ Thread-safe
5. → **Passer au Sprint 2** (tests et robustesse)
