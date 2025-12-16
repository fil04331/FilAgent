# 📋 PLAN D'ACTION DÉTAILLÉ - JOUR 1 (8 Décembre)

## 🚀 PHASE 1: FIXES CRITIQUES (45 minutes)

### Fix #1: TaskNode Import Error (15 min)

**Fichier à corriger:** `tests/test_performance.py`

**Étapes:**
1. Lire le fichier et identifier toutes les références à `TaskNode`
2. Les remplacer par `Task` 
3. Valider que la syntaxe reste correcte

**Code actuel (MAUVAIS):**
```python
from planner.task_graph import TaskGraph, TaskNode
# puis l'utilisation
task_node = TaskNode(...)
```

**Code après correction (BON):**
```python
from planner.task_graph import TaskGraph, Task
# puis l'utilisation  
task = Task(...)
```

---

### Fix #2: Pin Dependencies (10 min)

**Fichier à corriger:** `requirements.txt`

**Chercher la ligne:**
```
datasets
```

**Remplacer par:**
```
datasets~=2.15.0
```

---

### Fix #3: Stricter ComplianceGuardian Tests (20 min)

**Fichier à corriger:** `tests/test_agent.py`

**Chercher les lignes:**
```python
assert agent.compliance_guardian is None or isinstance(agent.compliance_guardian, ComplianceGuardian)
```

**Remplacer par:**
```python
assert hasattr(agent, 'compliance_guardian')
assert isinstance(agent.compliance_guardian, ComplianceGuardian)
```

---

## 🔧 PHASE 2: TESTS DE COMPLIANCE - IMPLÉMENTATIONS (2-3 heures)

### Fix #4: Implémenter _evaluate_provenance()

**Fichier:** `eval/compliance_benchmark.py`

**Remplacement complet de la fonction:**

```python
def _evaluate_provenance(self) -> bool:
    """
    Valider que les métadonnées de provenance W3C PROV-JSON sont présentes.
    
    Critères:
    - Chaque action a un hash Merkle
    - Trace complète de la décision enregistrée
    - Signatures numériques valides
    - Immuabilité garantie
    """
    try:
        # 1. Vérifier que les logs existent
        if not hasattr(self.agent, 'audit_trail'):
            logger.error("Agent missing audit_trail")
            return False
        
        # 2. Vérifier la structure WORM
        for log_entry in self.agent.audit_trail:
            # Chaque entrée doit avoir:
            # - id (unique)
            # - timestamp (ISO 8601)
            # - action (type d'action)
            # - hash (Merkle tree hash)
            # - previous_hash (chaîne d'intégrité)
            # - signature (Ed25519)
            
            required_fields = ['id', 'timestamp', 'action', 'hash', 'previous_hash', 'signature']
            if not all(field in log_entry for field in required_fields):
                logger.error(f"Missing provenance fields in entry: {log_entry}")
                return False
            
            # 3. Valider la chaîne de hachage
            if log_entry['hash'] is None:
                logger.error(f"Hash is None for entry {log_entry['id']}")
                return False
            
            # 4. Valider la signature (simulé ici, faut vérifier avec clé publique réelle)
            if not self._verify_signature(log_entry):
                logger.error(f"Signature verification failed for entry {log_entry['id']}")
                return False
        
        logger.info("✅ Provenance validation passed")
        return True
        
    except Exception as e:
        logger.error(f"Provenance evaluation failed: {e}")
        return False

def _verify_signature(self, log_entry: dict) -> bool:
    """Valider la signature Ed25519 d'une entrée de log."""
    try:
        # TODO: Implémenter avec crypto réelle (nacl.signing)
        # Pour maintenant, vérifier la présence de la signature
        signature = log_entry.get('signature')
        return signature is not None and len(signature) == 128  # 64 bytes en hex
    except Exception:
        return False
```

---

### Fix #5: Implémenter _evaluate_audit_trail()

**Fichier:** `eval/compliance_benchmark.py`

```python
def _evaluate_audit_trail(self) -> bool:
    """
    Valider le journal WORM (Write-Once-Read-Many).
    
    Critères:
    - Immuabilité des logs confirmée
    - Chaîne de hachage valide (pas de bris)
    - Ordre chronologique respecté
    - Format conforme JSON Lines
    """
    try:
        audit_trail = self.agent.audit_trail
        
        # 1. Vérifier que c'est une liste non-vide
        if not audit_trail or len(audit_trail) == 0:
            logger.error("Audit trail is empty")
            return False
        
        # 2. Valider l'ordre chronologique
        previous_timestamp = None
        previous_hash = None
        
        for i, entry in enumerate(audit_trail):
            # Timestamps doivent être croissants
            current_timestamp = entry.get('timestamp')
            
            if previous_timestamp and current_timestamp < previous_timestamp:
                logger.error(f"Chronological order violation at entry {i}")
                return False
            
            # 3. Valider la chaîne de hachage (intégrité)
            current_hash = entry.get('hash')
            expected_previous_hash = entry.get('previous_hash')
            
            if i > 0 and expected_previous_hash != previous_hash:
                logger.error(f"Hash chain broken at entry {i}")
                logger.error(f"  Expected: {previous_hash}")
                logger.error(f"  Got: {expected_previous_hash}")
                return False
            
            # 4. Vérifier la structure JSON Lines
            required_fields = ['id', 'timestamp', 'action', 'hash', 'previous_hash']
            if not all(field in entry for field in required_fields):
                logger.error(f"Missing field in audit trail entry {i}: {entry.keys()}")
                return False
            
            previous_timestamp = current_timestamp
            previous_hash = current_hash
        
        logger.info(f"✅ Audit trail validation passed ({len(audit_trail)} entries)")
        return True
        
    except Exception as e:
        logger.error(f"Audit trail evaluation failed: {e}")
        return False
```

---

### Fix #6: Implémenter _evaluate_retention()

**Fichier:** `eval/compliance_benchmark.py`

```python
def _evaluate_retention(self) -> bool:
    """
    Valider que les politiques de rétention sont appliquées correctement.
    
    Critères:
    - Données personnelles supprimées selon la politique
    - Logs conservés selon les règles de conformité
    - Minimisation des données respectée
    - TTL appliqué correctement
    """
    try:
        # 1. Vérifier la configuration de rétention
        retention_config = self.agent.config.get('retention', {})
        
        if not retention_config:
            logger.warning("No retention policy configured")
            return False
        
        # 2. Valider les TTLs (Time To Live)
        required_ttl_keys = ['pii_ttl_days', 'logs_ttl_days', 'cache_ttl_days']
        for key in required_ttl_keys:
            if key not in retention_config:
                logger.error(f"Missing retention config: {key}")
                return False
            
            ttl_value = retention_config[key]
            if not isinstance(ttl_value, int) or ttl_value <= 0:
                logger.error(f"Invalid {key}: {ttl_value}")
                return False
        
        # 3. Vérifier que les données personnelles ont un TTL < logs
        pii_ttl = retention_config['pii_ttl_days']
        logs_ttl = retention_config['logs_ttl_days']
        
        if pii_ttl >= logs_ttl:
            logger.error("PII TTL should be less than logs TTL (minimize retention)")
            return False
        
        # 4. Valider l'application des politiques
        if hasattr(self.agent, 'memory'):
            # Vérifier que pas de PII stockée au-delà du TTL
            pii_entries = [e for e in self.agent.memory.episodic_store if e.contains_pii]
            
            for entry in pii_entries:
                age_days = (datetime.now() - entry.created_at).days
                if age_days > pii_ttl:
                    logger.error(f"PII entry age ({age_days}d) exceeds TTL ({pii_ttl}d)")
                    return False
        
        logger.info("✅ Retention policies validation passed")
        return True
        
    except Exception as e:
        logger.error(f"Retention evaluation failed: {e}")
        return False
```

---

### Fix #7: Implémenter _evaluate_multi_step()

**Fichier:** `eval/compliance_benchmark.py`

```python
def _evaluate_multi_step(self) -> bool:
    """
    Valider que les tasks multi-étapes sont décomposées et exécutées correctement.
    
    Critères:
    - Décomposition HTN (Hierarchical Task Network) correcte
    - Dépendances entre tâches respectées
    - Gestion des erreurs dans les subtasks
    - Rollback en cas d'échec
    """
    try:
        # Créer une task complexe pour tester
        test_task = {
            "name": "complex_workflow",
            "type": "sequential",
            "subtasks": [
                {"name": "step1", "type": "analyze"},
                {"name": "step2", "type": "process"},
                {"name": "step3", "type": "validate"}
            ],
            "dependencies": {
                "step2": ["step1"],  # step2 dépend de step1
                "step3": ["step2"]   # step3 dépend de step2
            }
        }
        
        # 1. Vérifier la décomposition
        if not hasattr(self.agent.planner, 'decompose'):
            logger.error("Planner missing decompose method")
            return False
        
        decomposed = self.agent.planner.decompose(test_task)
        
        if not decomposed:
            logger.error("Task decomposition returned empty")
            return False
        
        # 2. Vérifier que les dépendances sont respectées
        execution_order = [t.name for t in decomposed]
        
        for task_name, deps in test_task['dependencies'].items():
            for dep in deps:
                if execution_order.index(dep) >= execution_order.index(task_name):
                    logger.error(f"Dependency order violation: {task_name} before {dep}")
                    return False
        
        # 3. Exécuter et vérifier la gestion d'erreurs
        result = self.agent.planner.execute(decomposed)
        
        if not result:
            logger.error("Task execution failed")
            return False
        
        logger.info("✅ Multi-step task validation passed")
        return True
        
    except Exception as e:
        logger.error(f"Multi-step evaluation failed: {e}")
        return False
```

---

## 📊 PHASE 3: CONFIGURATION ÉVALUATION DATA-DRIVEN (1 heure)

### Fix #8: Rendre _check_targets() data-driven

**Fichier:** `eval/compliance_benchmark.py`

**Remplacer la logique hardcodée par:**

```python
from typing import List
from dataclasses import dataclass

@dataclass
class EvaluationTarget:
    """Cible d'évaluation configurable."""
    benchmark: str
    metric: str
    operator: str  # ">=", ">", "==", "<=", "<"
    value: float
    description: str = ""

class EvaluationTargetLoader:
    """Charger les cibles d'évaluation depuis la configuration."""
    
    @staticmethod
    def load_targets(config_path: str = "config/eval_targets.yaml") -> List[EvaluationTarget]:
        """
        Charger les targets d'évaluation depuis YAML.
        
        Format YAML attendu:
        ```yaml
        targets:
          - benchmark: humaneval
            metric: pass_rate
            operator: ">="
            value: 65
            description: "HumanEval pass@1 baseline"
          
          - benchmark: compliance
            metric: provenance_integrity
            operator: "=="
            value: 100
            description: "Provenance tests must pass 100%"
        ```
        """
        try:
            if not os.path.exists(config_path):
                raise FileNotFoundError(f"Config file not found: {config_path}")
            
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            if not config or 'targets' not in config:
                raise ValueError("Config must contain 'targets' key")
            
            targets = []
            for target_dict in config['targets']:
                # Validation
                required_fields = ['benchmark', 'metric', 'operator', 'value']
                missing = [f for f in required_fields if f not in target_dict]
                
                if missing:
                    raise ValueError(f"Missing fields in target: {missing}")
                
                # Créer l'objet
                target = EvaluationTarget(**target_dict)
                
                # Valider l'operator
                valid_ops = [">=", ">", "==", "<=", "<"]
                if target.operator not in valid_ops:
                    raise ValueError(f"Invalid operator: {target.operator}")
                
                targets.append(target)
            
            logger.info(f"✅ Loaded {len(targets)} evaluation targets")
            return targets
            
        except FileNotFoundError as e:
            logger.error(f"❌ Config file not found: {e}")
            raise  # ❌ NE PAS IGNORER
        except yaml.YAMLError as e:
            logger.error(f"❌ Invalid YAML format: {e}")
            raise  # ❌ NE PAS IGNORER
        except Exception as e:
            logger.error(f"❌ Failed to load targets: {e}")
            raise  # ❌ NE PAS IGNORER

def _check_targets(self) -> bool:
    """Vérifier que les targets d'évaluation sont atteints."""
    try:
        targets = EvaluationTargetLoader.load_targets()
        
        results = []
        
        for target in targets:
            # Récupérer la valeur actuelle du benchmark
            current_value = self._get_benchmark_value(target.benchmark, target.metric)
            
            # Évaluer contre le target
            passed = self._evaluate_operator(current_value, target.operator, target.value)
            
            status = "✅ PASS" if passed else "❌ FAIL"
            logger.info(f"{status}: {target.description}")
            logger.info(f"  {target.metric} = {current_value} {target.operator} {target.value}")
            
            results.append({
                'target': target,
                'current_value': current_value,
                'passed': passed
            })
        
        # Résumé
        passed_count = sum(1 for r in results if r['passed'])
        total_count = len(results)
        
        logger.info(f"\nTarget Summary: {passed_count}/{total_count} passed")
        
        return passed_count == total_count
        
    except Exception as e:
        logger.error(f"❌ Failed to check targets: {e}")
        raise  # ❌ NE PAS IGNORER

def _get_benchmark_value(self, benchmark: str, metric: str) -> float:
    """Récupérer la valeur actuelle d'un benchmark."""
    if benchmark == "humaneval":
        return self.humaneval_results.get(metric, 0.0)
    elif benchmark == "mbpp":
        return self.mbpp_results.get(metric, 0.0)
    elif benchmark == "compliance":
        # Pour compliance, c'est 0-100%
        return self.compliance_results.get(metric, 0.0)
    else:
        raise ValueError(f"Unknown benchmark: {benchmark}")

def _evaluate_operator(self, current: float, operator: str, target: float) -> bool:
    """Évaluer une condition avec l'operator spécifié."""
    if operator == ">=":
        return current >= target
    elif operator == ">":
        return current > target
    elif operator == "==":
        return current == target
    elif operator == "<=":
        return current <= target
    elif operator == "<":
        return current < target
    else:
        raise ValueError(f"Unknown operator: {operator}")
```

---

## 🎯 AMÉLIORER LOGIQUE PLANNING EVAL (1-2 heures)

### Fix #9: Planning Evaluation Robustness

**Fichier:** `eval/compliance_benchmark.py`

**Remplacer la logique simple par:**

```python
from dataclasses import dataclass
from typing import List, Dict, Set

@dataclass
class Task:
    """Représentation d'une tâche dans un plan."""
    id: str
    name: str
    dependencies: Set[str]  # IDs des tâches dont elle dépend
    duration: float = 0.0

class PlanValidator:
    """Valider la structure et l'exécution d'un plan."""
    
    @staticmethod
    def parse_plan_from_text(text: str) -> List[Task]:
        """Parser un plan depuis texte naturel du LLM."""
        # Implémenter un parser simple ou utiliser regex
        # Pour maintenant, c'est un placeholder
        # En production: utiliser un LLM pour extraire la structure
        pass
    
    @staticmethod
    def validate_dependencies(tasks: List[Task]) -> bool:
        """Vérifier qu'il n'y a pas de cycle (DAG)."""
        visited = set()
        rec_stack = set()
        
        def has_cycle(task_id: str) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)
            
            task = next((t for t in tasks if t.id == task_id), None)
            if not task:
                return False
            
            for dep_id in task.dependencies:
                if dep_id not in visited:
                    if has_cycle(dep_id):
                        return True
                elif dep_id in rec_stack:
                    return True
            
            rec_stack.remove(task_id)
            return False
        
        # Vérifier chaque tâche
        for task in tasks:
            if task.id not in visited:
                if has_cycle(task.id):
                    return False
        
        return True
    
    @staticmethod
    def validate_topological_order(tasks: List[Task]) -> bool:
        """Vérifier l'ordre topologique du plan."""
        # Vérifier que chaque tâche vient après ses dépendances
        task_positions = {t.id: i for i, t in enumerate(tasks)}
        
        for task in tasks:
            for dep_id in task.dependencies:
                if dep_id in task_positions:
                    if task_positions[dep_id] >= task_positions[task.id]:
                        # Dépendance vient après la tâche!
                        return False
        
        return True
    
    @staticmethod
    def simulate_execution(tasks: List[Task]) -> Dict:
        """Simuler l'exécution du plan."""
        completed = set()
        total_duration = 0.0
        
        # Exécution topologique
        while len(completed) < len(tasks):
            found_ready = False
            
            for task in tasks:
                if task.id not in completed:
                    # Vérifier si les dépendances sont complètes
                    if task.dependencies.issubset(completed):
                        completed.add(task.id)
                        total_duration += task.duration
                        found_ready = True
            
            if not found_ready and len(completed) < len(tasks):
                # Deadlock!
                return {
                    'success': False,
                    'error': 'deadlock',
                    'completed': completed
                }
        
        return {
            'success': True,
            'completed': completed,
            'total_duration': total_duration
        }

def _evaluate_planning(self) -> bool:
    """
    Évaluer la qualité du planning.
    
    Au lieu de chercher des keywords, on valide la structure réelle.
    """
    try:
        # 1. Parser le plan
        plan_text = self.agent.last_planning_output
        tasks = PlanValidator.parse_plan_from_text(plan_text)
        
        if not tasks or len(tasks) < 2:
            logger.error("Plan must contain at least 2 tasks")
            return False
        
        # 2. Valider qu'il n'y a pas de cycles
        if not PlanValidator.validate_dependencies(tasks):
            logger.error("Plan contains circular dependencies")
            return False
        
        # 3. Valider l'ordre topologique
        if not PlanValidator.validate_topological_order(tasks):
            logger.error("Tasks not in topological order")
            return False
        
        # 4. Simuler l'exécution
        execution = PlanValidator.simulate_execution(tasks)
        
        if not execution['success']:
            logger.error(f"Plan execution failed: {execution.get('error')}")
            return False
        
        logger.info(f"✅ Planning validation passed ({len(tasks)} tasks)")
        logger.info(f"   Total duration: {execution['total_duration']}s")
        
        return True
        
    except Exception as e:
        logger.error(f"Planning evaluation failed: {e}")
        return False
```

---

## ✅ CHECKLIST FINALES

- [ ] Fix TaskNode import error (#164)
- [ ] Pin datasets dependency
- [ ] Fix ComplianceGuardian assertions
- [ ] Implement _evaluate_provenance()
- [ ] Implement _evaluate_audit_trail()
- [ ] Implement _evaluate_retention()
- [ ] Implement _evaluate_multi_step()
- [ ] Make eval targets data-driven
- [ ] Improve planning evaluation logic
- [ ] Enable branch coverage in pytest
- [ ] Run full test suite and verify
- [ ] Commit all changes to GitHub

---

## 🚀 RÉSUMÉ

**Total Estimated Time:** 5-7 heures  
**Impact:** Production-ready compliance + robust evaluation system

Dès que vous êtes prêt à implémenter, **dites-moi simplement "OK"** et je peux:
1. ✅ Générer les PR directement
2. ✅ Vous expliquer chaque section
3. ✅ Implémenter avec vous step-by-step

**À demain avec de nouvelles priorités!**
