Étape 1: Importer le module
python# Dans runtime/agent.py
from planner import (
    HierarchicalPlanner,
    TaskExecutor,
    TaskVerifier,
    PlanningStrategy,
    ExecutionStrategy,
    VerificationLevel,
)
Étape 2: Initialiser dans Agent.init
pythonclass Agent:
    def __init__(self, config: AgentConfig):
        # ... existing code ...
        
        # Ajouter le planificateur HTN
        self.planner = HierarchicalPlanner(
            model_interface=self.model,
            tools_registry=self.tools_registry,
            max_decomposition_depth=config.max_decomposition_depth,
            enable_tracing=True,
        )
        
        # Ajouter l'exécuteur
        self.executor = TaskExecutor(
            action_registry=self._build_action_registry(),
            strategy=ExecutionStrategy.ADAPTIVE,
            max_workers=config.max_parallel_workers,
            timeout_per_task_sec=config.task_timeout,
            enable_tracing=True,
        )
        
        # Ajouter le vérificateur
        self.verifier = TaskVerifier(
            default_level=VerificationLevel.STRICT,
            enable_tracing=True,
        )
Étape 3: Modifier la boucle principale
pythondef run(self, user_query: str) -> Dict[str, Any]:
    """
    Méthode modifiée pour utiliser HTN
    
    AVANT: Boucle simple max 10 iterations
    APRÈS: Planification puis exécution parallèle
    """
    
    # NOUVEAU: Détecter si la requête nécessite HTN
    if self._requires_planning(user_query):
        return self._run_with_htn(user_query)
    else:
        return self._run_simple(user_query)  # Ancien comportement
    
def _requires_planning(self, query: str) -> bool:
    """
    Détermine si HTN est nécessaire
    
    Critères:
    - Mots-clés multi-étapes: "puis", "ensuite", "après"
    - Requêtes complexes: "analyse... génère... crée..."
    - Nombre de verbes d'action > 2
    """
    keywords = ["puis", "ensuite", "après", "finalement", "et"]
    action_verbs = ["lis", "analyse", "génère", "crée", "calcule"]
    
    has_multi_step = any(kw in query.lower() for kw in keywords)
    num_actions = sum(1 for verb in action_verbs if verb in query.lower())
    
    return has_multi_step or num_actions >= 2

def _run_with_htn(self, user_query: str) -> Dict[str, Any]:
    """Exécution avec planification HTN"""
    
    # 1. Planifier
    plan_result = self.planner.plan(
        query=user_query,
        strategy=PlanningStrategy.HYBRID,
        context={"conversation_id": self.conversation_id},
    )
    
    # Log decision record (conformité Loi 25)
    self.decision_manager.record_decision(
        decision_type="planning",
        input_data={"query": user_query},
        output_data={"plan": plan_result.to_dict()},
        reasoning=plan_result.reasoning,
    )
    
    # 2. Exécuter
    exec_result = self.executor.execute(
        graph=plan_result.graph,
        context={"conversation_id": self.conversation_id},
    )
    
    # 3. Vérifier
    verifications = self.verifier.verify_graph_results(
        graph=plan_result.graph,
        level=VerificationLevel.STRICT,
    )
    
    # 4. Construire la réponse
    if exec_result.success:
        # Toutes les tâches critiques réussies
        response = self._format_htn_response(
            plan_result, exec_result, verifications
        )
    else:
        # Échec critique: fallback sur mode simple
        response = self._run_simple(user_query)
    
    return response
Étape 4: Créer le registre d'actions
pythondef _build_action_registry(self) -> Dict[str, Callable]:
    """
    Mappe les actions HTN aux outils FilAgent
    
    Returns:
        Dict[action_name, fonction_executable]
    """
    registry = {}
    
    # Mapper chaque outil du registre
    for tool in self.tools_registry.get_all():
        # Wrapper pour adapter l'interface
        def tool_wrapper(params, tool=tool):
            return tool.execute(**params)
        
        registry[tool.name] = tool_wrapper
    
    # Actions génériques
    registry["generic_execute"] = self._generic_execute
    
    return registry

def _generic_execute(self, params: Dict) -> Any:
    """Action générique pour tâches non-mappées"""
    query = params.get("query", "")
    return self._run_simple(query)
Étape 5: Formatter la réponse
pythondef _format_htn_response(
    self,
    plan_result: PlanningResult,
    exec_result: ExecutionResult,
    verifications: Dict[str, VerificationResult],
) -> Dict[str, Any]:
    """Formate la réponse finale"""
    
    # Agréger les résultats
    results = []
    for task in plan_result.graph.topological_sort():
        if task.status.value == "completed":
            results.append({
                "task": task.name,
                "result": task.result,
                "verified": verifications.get(task.task_id, None),
            })
    
    # Générer le texte de réponse
    response_text = self._generate_response_from_results(results)
    
    return {
        "response": response_text,
        "plan": plan_result.to_dict(),
        "execution": exec_result.to_dict(),
        "verifications": {
            k: v.to_dict() for k, v in verifications.items()
        },
        "metadata": {
            "planning_strategy": plan_result.strategy_used.value,
            "execution_strategy": ExecutionStrategy.ADAPTIVE.value,
            "total_duration_ms": exec_result.total_duration_ms,
            "success": exec_result.success,
        },
    }

📝 CONFIGURATION REQUISE
Dans config/agent.yaml
yaml# Ajouter ces paramètres pour HTN
htn_planning:
  enabled: true
  default_strategy: hybrid  # rule_based, llm_based, hybrid
  max_decomposition_depth: 3
  
htn_execution:
  default_strategy: adaptive  # sequential, parallel, adaptive
  max_parallel_workers: 4
  task_timeout_sec: 60
  
htn_verification:
  default_level: strict  # basic, strict, paranoid
  custom_verifiers: []
Dans config/policies.yaml
yaml# Ajouter les politiques HTN
htn_policies:
  max_tasks_per_plan: 50
  max_execution_time_sec: 300
  
  allowed_actions:
    - read_file
    - write_file
    - analyze_data
    - generate_report
    - calculate
    - search
  
  blocked_actions:
    - delete_system_file
    - execute_system_command
  
  retry_policies:
    max_retries: 3
    backoff_strategy: exponential
    backoff_base_sec: 1

🧪 TESTS ET VALIDATION
Tests unitaires à exécuter
bash# Tests task_graph (DÉJÀ CRÉÉS)
pytest tests/test_planner/test_task_graph.py -v

# Tests à créer pour couverture complète
pytest tests/test_planner/test_planner.py -v
pytest tests/test_planner/test_executor.py -v
pytest tests/test_planner/test_verifier.py -v

# Tests d'intégration
python3 examples/htn_integration_example.py
Scénarios de test recommandés

Requête simple: "Lis data.csv"

Devrait utiliser mode simple (pas HTN)


Requête multi-étapes: "Lis data.csv, analyse les données, crée un rapport"

Devrait utiliser HTN avec 3+ tâches


Tâches parallèles: "Lis file1.csv, file2.csv, file3.csv puis analyse tout"

Devrait paralléliser les 3 lectures


Gestion d'erreur: Tâche critique échoue

Devrait abort et générer Decision Record


Tâche optionnelle: Email échoue

Devrait continuer sans abort




📊 MÉTRIQUES DE SUCCÈS
KPIs à monitorer
python# Après intégration, monitorer:

# 1. Adoption du HTN
htn_usage_rate = htn_requests / total_requests
target: > 30%  # 30% des requêtes utilisent HTN

# 2. Performance
avg_execution_time = sum(durations) / count
target: < 5000ms  # Moins de 5 secondes

# 3. Parallélisation
parallelization_factor = tasks_parallel / total_tasks
target: > 0.4  # 40% des tâches parallélisées

# 4. Fiabilité
success_rate = successful_plans / total_plans
target: > 95%  # 95% de succès

# 5. Vérification
verification_pass_rate = verified_ok / verified_total
target: > 90%  # 90% passent la vérification
CHOOSE WITH --->  Tests d'intégration - Exécuter exemples et valider
 Documentation utilisateur - Guide d'utilisation HTN

Court terme (2 semaines)

 Tests supplémentaires - Créer test_planner.py, test_executor.py, test_verifier.py
 Monitoring - Ajouter métriques Prometheus pour HTN
 Optimisations - Profiling et amélioration performance
 Recovery avancé - Implémenter circuit breaker, fallback

Moyen terme (1 mois)

 LLM fine-tuning - Améliorer décomposition LLM-based
 Patterns avancés - Ajouter plus de règles prédéfinies
 UI/UX - Visualisation des plans dans l'interface
 Formation - Tutoriels vidéo et documentation