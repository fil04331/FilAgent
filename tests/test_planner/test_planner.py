"""
Tests unitaires pour planner.py

Couvre:
- HierarchicalPlanner: initialisation, planification
- PlanningStrategy: RULE_BASED, LLM_BASED, HYBRID
- PlanningResult: structure, sérialisation, métadonnées
- Patterns rule-based: matching, décomposition
- Edge cases: requêtes vides, LLM échec, validation

Exécution:
    pytest tests/test_planner/test_planner.py -v
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from planner.planner import (
    HierarchicalPlanner,
    PlanningStrategy,
    PlanningResult,
)
from planner.task_graph import (
    TaskGraph,
    Task,
    TaskPriority,
    TaskDecompositionError,
)


class TestHierarchicalPlanner:
    """Tests pour la classe HierarchicalPlanner"""
    
    def test_planner_initialization_default(self):
        """Test initialisation avec valeurs par défaut"""
        planner = HierarchicalPlanner()
        
        assert planner.model is None
        assert planner.tools is None
        assert planner.max_depth == 3
        assert planner.enable_tracing is True
        assert hasattr(planner, 'patterns')
        assert len(planner.patterns) > 0
    
    def test_planner_initialization_custom(self):
        """Test initialisation avec paramètres personnalisés"""
        mock_model = Mock()
        mock_tools = Mock()
        
        planner = HierarchicalPlanner(
            model_interface=mock_model,
            tools_registry=mock_tools,
            max_decomposition_depth=5,
            enable_tracing=False,
        )
        
        assert planner.model == mock_model
        assert planner.tools == mock_tools
        assert planner.max_depth == 5
        assert planner.enable_tracing is False
    
    def test_init_rule_patterns(self):
        """Test initialisation des patterns de règles"""
        planner = HierarchicalPlanner()
        
        assert isinstance(planner.patterns, dict)
        # Vérifier qu'il y a des patterns
        assert len(planner.patterns) > 0
        
        # Vérifier structure des patterns (regex + templates)
        for pattern, templates in planner.patterns.items():
            assert isinstance(pattern, str)
            assert isinstance(templates, list)
            for template in templates:
                assert "action" in template


class TestPlanningStrategyRuleBased:
    """Tests pour stratégie RULE_BASED"""
    
    def test_rule_based_simple_pattern_match(self):
        """Test décomposition rule-based avec pattern simple"""
        planner = HierarchicalPlanner()
        
        query = "Lis data.csv, calcule la moyenne"
        result = planner.plan(query, strategy=PlanningStrategy.RULE_BASED)
        
        assert isinstance(result, PlanningResult)
        assert result.strategy_used == PlanningStrategy.RULE_BASED
        assert result.confidence >= 0.5
        assert len(result.graph.tasks) >= 1
        assert "Rule-based" in result.reasoning
        assert result.metadata["validation_passed"] is True
    
    def test_rule_based_multi_step_pattern(self):
        """Test décomposition avec pattern multi-étapes"""
        planner = HierarchicalPlanner()
        
        query = "Analyse donnees.csv, génère statistiques, crée rapport"
        result = planner.plan(query, strategy=PlanningStrategy.RULE_BASED)
        
        assert isinstance(result, PlanningResult)
        assert len(result.graph.tasks) >= 1
        assert result.metadata["validation_passed"] is True
    
    def test_rule_based_no_pattern_match(self):
        """Test fallback quand aucun pattern ne matche"""
        planner = HierarchicalPlanner()
        
        query = "Requête complètement inconnue sans pattern"
        result = planner.plan(query, strategy=PlanningStrategy.RULE_BASED)
        
        # Devrait créer une tâche générique
        assert len(result.graph.tasks) == 1
        task = list(result.graph.tasks.values())[0]
        assert task.action == "generic_execute"
        assert result.confidence == 0.5  # Faible confiance sans match
    
    def test_rule_based_empty_query(self):
        """Test avec requête vide"""
        planner = HierarchicalPlanner()
        
        result = planner.plan("", strategy=PlanningStrategy.RULE_BASED)
        
        # Devrait créer une tâche générique
        assert len(result.graph.tasks) == 1
        task = list(result.graph.tasks.values())[0]
        assert task.action == "generic_execute"
    
    def test_rule_based_with_context(self):
        """Test avec contexte additionnel"""
        planner = HierarchicalPlanner()
        
        query = "Lis fichier.csv"
        context = {"conversation_id": "test123", "user_id": "user1"}
        result = planner.plan(query, strategy=PlanningStrategy.RULE_BASED, context=context)
        
        assert result.metadata["context"] == context
        assert "started_at" in result.metadata
        assert "completed_at" in result.metadata


class TestPlanningStrategyLLMBased:
    """Tests pour stratégie LLM_BASED"""
    
    def test_llm_based_requires_model(self):
        """Test que LLM_BASED nécessite un modèle"""
        planner = HierarchicalPlanner(model_interface=None)
        
        with pytest.raises(TaskDecompositionError, match="requires a model_interface"):
            planner.plan("test query", strategy=PlanningStrategy.LLM_BASED)
    
    def test_llm_based_with_mock_model(self):
        """Test LLM_BASED avec modèle mock"""
        # Créer un mock modèle qui retourne une réponse JSON valide
        mock_model = Mock()
        mock_response = """{
  "tasks": [
    {
      "name": "read_file",
      "action": "read_file",
      "params": {"file": "data.csv"},
      "depends_on": [],
      "priority": 3
    },
    {
      "name": "analyze_data",
      "action": "analyze_data",
      "params": {"data": "from_file"},
      "depends_on": [0],
      "priority": 3
    }
  ],
  "reasoning": "LLM decomposition test"
}"""
        mock_model.generate.return_value = mock_response
        
        planner = HierarchicalPlanner(model_interface=mock_model)
        
        query = "Analyse data.csv"
        result = planner.plan(query, strategy=PlanningStrategy.LLM_BASED)
        
        assert isinstance(result, PlanningResult)
        assert result.strategy_used == PlanningStrategy.LLM_BASED
        assert len(result.graph.tasks) == 2
        assert result.confidence == 0.9
        assert "LLM decomposition" in result.reasoning
        assert mock_model.generate.called
    
    def test_llm_based_invalid_json_response(self):
        """Test gestion erreur JSON invalide du LLM"""
        mock_model = Mock()
        mock_model.generate.return_value = "Invalid JSON response"
        
        planner = HierarchicalPlanner(model_interface=mock_model)
        
        with pytest.raises(TaskDecompositionError, match="Failed to parse LLM response"):
            planner.plan("test", strategy=PlanningStrategy.LLM_BASED)
    
    def test_llm_based_model_exception(self):
        """Test gestion exception du modèle"""
        mock_model = Mock()
        mock_model.generate.side_effect = Exception("Model error")
        
        planner = HierarchicalPlanner(model_interface=mock_model)
        
        with pytest.raises(TaskDecompositionError, match="LLM-based planning failed"):
            planner.plan("test", strategy=PlanningStrategy.LLM_BASED)


class TestPlanningStrategyHybrid:
    """Tests pour stratégie HYBRID"""
    
    def test_hybrid_high_confidence_rule_based(self):
        """Test HYBRID avec confiance élevée (utilise rule-based seulement)"""
        planner = HierarchicalPlanner()
        
        query = "Lis data.csv, calcule la moyenne"
        result = planner.plan(query, strategy=PlanningStrategy.HYBRID)
        
        assert result.strategy_used == PlanningStrategy.HYBRID
        assert result.confidence >= 0.7
        assert "Hybrid (rule-based sufficient)" in result.reasoning
    
    def test_hybrid_low_confidence_fallback_llm(self):
        """Test HYBRID avec faible confiance (fallback LLM)"""
        # Simuler faible confiance en utilisant une requête sans pattern
        planner = HierarchicalPlanner()
        
        query = "Requête très complexe sans pattern connu"
        result = planner.plan(query, strategy=PlanningStrategy.HYBRID)
        
        # Devrait utiliser rule-based avec faible confiance
        assert result.strategy_used == PlanningStrategy.HYBRID
        # Si pas de modèle, reste sur rule-based
    
    def test_hybrid_llm_fallback_on_error(self):
        """Test HYBRID avec LLM qui échoue (fallback sur rules)"""
        mock_model = Mock()
        mock_model.generate.side_effect = Exception("LLM error")
        
        planner = HierarchicalPlanner(model_interface=mock_model)
        
        query = "Requête complexe"
        result = planner.plan(query, strategy=PlanningStrategy.HYBRID)
        
        # Devrait fallback sur rule-based
        assert result.strategy_used == PlanningStrategy.HYBRID
        assert "fallback to rules" in result.reasoning


class TestPlanningResult:
    """Tests pour la classe PlanningResult"""
    
    def test_planning_result_creation(self):
        """Test création PlanningResult"""
        graph = TaskGraph()
        task = Task(name="test", action="test_action")
        graph.add_task(task)
        
        result = PlanningResult(
            graph=graph,
            strategy_used=PlanningStrategy.RULE_BASED,
            confidence=0.8,
            reasoning="Test reasoning",
        )
        
        assert result.graph == graph
        assert result.strategy_used == PlanningStrategy.RULE_BASED
        assert result.confidence == 0.8
        assert result.reasoning == "Test reasoning"
        assert "planned_at" in result.metadata
    
    def test_planning_result_to_dict(self):
        """Test sérialisation PlanningResult"""
        graph = TaskGraph()
        task = Task(name="test", action="test_action")
        graph.add_task(task)
        
        result = PlanningResult(
            graph=graph,
            strategy_used=PlanningStrategy.RULE_BASED,
            confidence=0.8,
            reasoning="Test",
        )
        
        result_dict = result.to_dict()
        
        assert "graph" in result_dict
        assert result_dict["strategy_used"] == "rule_based"
        assert result_dict["confidence"] == 0.8
        assert result_dict["reasoning"] == "Test"
        assert "metadata" in result_dict


class TestPlannerValidation:
    """Tests pour validation des plans"""
    
    def test_validate_empty_plan(self):
        """Test validation plan vide (devrait échouer)"""
        planner = HierarchicalPlanner()
        
        # Créer un plan vide
        graph = TaskGraph()
        result = PlanningResult(
            graph=graph,
            strategy_used=PlanningStrategy.RULE_BASED,
            confidence=0.5,
            reasoning="Test",
        )
        
        with pytest.raises(TaskDecompositionError, match="at least one task"):
            planner.validate_execution_plan(graph)
    
    def test_validate_invalid_action(self):
        """Test validation avec action invalide"""
        planner = HierarchicalPlanner()
        
        # Mock tools registry qui ne contient pas l'action
        mock_tools = Mock()
        mock_tools.get_all.return_value = []  # Pas d'outils
        
        planner.tools = mock_tools
        
        graph = TaskGraph()
        task = Task(name="test", action="unknown_action")
        graph.add_task(task)
        
        with pytest.raises(TaskDecompositionError, match="Unknown action"):
            planner.validate_execution_plan(graph)
    
    def test_validate_plan_success(self):
        """Test validation plan valide"""
        planner = HierarchicalPlanner()
        
        graph = TaskGraph()
        task = Task(name="test", action="generic_execute")
        graph.add_task(task)
        
        # Ne devrait pas lever d'exception
        planner.validate_execution_plan(graph)


class TestPlannerHelperMethods:
    """Tests pour méthodes helper du planificateur"""
    
    def test_get_available_actions_with_tools(self):
        """Test récupération actions disponibles depuis tools"""
        mock_tools = Mock()
        mock_tool1 = Mock()
        mock_tool1.name = "tool1"
        mock_tool2 = Mock()
        mock_tool2.name = "tool2"
        mock_tools.get_all.return_value = [mock_tool1, mock_tool2]
        
        planner = HierarchicalPlanner(tools_registry=mock_tools)
        
        actions = planner._get_available_actions()
        assert "tool1" in actions
        assert "tool2" in actions
    
    def test_get_available_actions_without_tools(self):
        """Test récupération actions par défaut sans tools"""
        planner = HierarchicalPlanner(tools_registry=None)
        
        actions = planner._get_available_actions()
        assert "read_file" in actions
        assert "write_file" in actions
        assert "calculate" in actions
    
    def test_parse_llm_response_clean_json(self):
        """Test parsing réponse LLM JSON propre"""
        planner = HierarchicalPlanner()
        
        response = '{"tasks": [{"name": "test"}], "reasoning": "test"}'
        parsed = planner._parse_llm_response(response)
        
        assert isinstance(parsed, dict)
        assert "tasks" in parsed
        assert "reasoning" in parsed
    
    def test_parse_llm_response_markdown_wrapped(self):
        """Test parsing réponse LLM avec markdown"""
        planner = HierarchicalPlanner()
        
        response = """```json
{"tasks": [{"name": "test"}], "reasoning": "test"}
```"""
        parsed = planner._parse_llm_response(response)
        
        assert isinstance(parsed, dict)
        assert "tasks" in parsed
    
    def test_parse_llm_response_invalid_json(self):
        """Test parsing JSON invalide"""
        planner = HierarchicalPlanner()
        
        with pytest.raises(TaskDecompositionError, match="Failed to parse"):
            planner._parse_llm_response("Invalid JSON")


class TestPlannerEdgeCases:
    """Tests pour cas limites"""
    
    def test_plan_with_very_long_query(self):
        """Test planification avec requête très longue"""
        planner = HierarchicalPlanner()
        
        long_query = "Lis " + "fichier_" * 1000 + ".csv"
        result = planner.plan(long_query, strategy=PlanningStrategy.RULE_BASED)
        
        # Devrait fonctionner sans erreur
        assert isinstance(result, PlanningResult)
        assert len(result.graph.tasks) >= 1
    
    def test_plan_with_special_characters(self):
        """Test planification avec caractères spéciaux"""
        planner = HierarchicalPlanner()
        
        query = "Lis fichier@#$%^&*.csv, calcule la moyenne!"
        result = planner.plan(query, strategy=PlanningStrategy.RULE_BASED)
        
        # Devrait fonctionner
        assert isinstance(result, PlanningResult)
    
    def test_plan_multiple_contexts(self):
        """Test planification avec plusieurs appels (métadonnées)"""
        planner = HierarchicalPlanner()
        
        query = "Lis data.csv"
        result1 = planner.plan(query, context={"id": 1})
        result2 = planner.plan(query, context={"id": 2})
        
        assert result1.metadata["context"]["id"] == 1
        assert result2.metadata["context"]["id"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

