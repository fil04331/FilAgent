"""
Tests d'intégration HTN avec Agent

Couvre:
- Intégration complète HTN dans Agent
- Détection automatique de requêtes complexes
- Planification et exécution via Agent
- Vérification des résultats
- Mode simple vs mode HTN

Exécution:
    pytest tests/test_planner/test_agent_htn_integration.py -v
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from planner import (
    HierarchicalPlanner,
    PlanningStrategy,
    ExecutionStrategy,
    VerificationLevel,
)
from planner.task_graph import TaskStatus


class TestAgentHTNIntegration:
    """Tests d'intégration HTN avec Agent"""

    @patch("runtime.agent.get_config")
    def test_agent_htn_initialization(self, mock_get_config):
        """Test initialisation HTN dans Agent"""
        from runtime.agent import Agent

        # Mock configuration
        mock_config = Mock()
        mock_config.htn_planning = None
        mock_config.htn_execution = None
        mock_config.htn_verification = None
        mock_get_config.return_value = mock_config

        agent = Agent(config=mock_config)

        # HTN ne devrait pas être initialisé avant initialize_model()
        assert agent.planner is None
        assert agent.executor is None
        assert agent.verifier is None

    @patch("runtime.agent.get_config")
    @patch("runtime.model_interface.init_model")
    def test_agent_requires_planning_detection(self, mock_init_model, mock_get_config):
        """Test détection automatique de requêtes complexes"""
        from runtime.agent import Agent

        # Mock configuration
        mock_config = Mock()
        mock_config.htn_planning = Mock()
        mock_config.htn_planning.enabled = True
        mock_config.htn_execution = None
        mock_config.htn_verification = None
        mock_get_config.return_value = mock_config

        # Mock model
        mock_model = Mock()
        mock_init_model.return_value = mock_model

        agent = Agent(config=mock_config)
        agent.initialize_model()

        # Requête simple (pas HTN)
        simple_query = "Lis data.csv"
        requires = agent._requires_planning(simple_query)
        assert requires is False

        # Requête complexe (HTN nécessaire)
        complex_query = "Lis data.csv, analyse les données, crée un rapport"
        requires = agent._requires_planning(complex_query)
        assert requires is True

    @patch("runtime.agent.get_config")
    @patch("runtime.model_interface.init_model")
    def test_agent_htn_disabled(self, mock_init_model, mock_get_config):
        """Test quand HTN est désactivé"""
        from runtime.agent import Agent

        # Mock configuration avec HTN désactivé
        mock_config = Mock()
        mock_config.htn_planning = Mock()
        mock_config.htn_planning.enabled = False
        mock_config.htn_verification = None  # Pas de config de vérification
        mock_get_config.return_value = mock_config

        # Mock model
        mock_model = Mock()
        mock_init_model.return_value = mock_model

        agent = Agent(config=mock_config)
        agent.initialize_model()

        # Même avec requête complexe, ne devrait pas utiliser HTN
        complex_query = "Lis data.csv, analyse, crée rapport"
        requires = agent._requires_planning(complex_query)
        assert requires is False

    @patch("runtime.agent.get_config")
    @patch("runtime.model_interface.init_model")
    def test_agent_build_action_registry(self, mock_init_model, mock_get_config):
        """Test construction du registre d'actions"""
        from runtime.agent import Agent

        # Mock configuration
        mock_config = Mock()
        mock_config.htn_planning = None
        mock_get_config.return_value = mock_config

        # Mock tool registry
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tool.execute = Mock(return_value="result")

        mock_tool_registry = Mock()
        mock_tool_registry.list_all.return_value = {"test_tool": mock_tool}

        agent = Agent(config=mock_config)
        agent.tool_registry = mock_tool_registry

        registry = agent._build_action_registry()

        assert "test_tool" in registry
        assert "generic_execute" in registry
        assert callable(registry["test_tool"])
        assert callable(registry["generic_execute"])

    @patch("runtime.agent.get_config")
    @patch("runtime.model_interface.init_model")
    def test_agent_run_with_htn(self, mock_init_model, mock_get_config):
        """Test exécution avec HTN"""
        from runtime.agent import Agent
        from planner.task_graph import Task, TaskGraph, TaskPriority
        from planner.planner import PlanningResult

        # Mock configuration
        mock_config = Mock()
        mock_config.htn_planning = Mock()
        mock_config.htn_planning.default_strategy = "hybrid"
        mock_config.htn_execution = None
        mock_config.htn_verification = Mock()
        mock_config.htn_verification.default_level = "strict"
        mock_get_config.return_value = mock_config

        # Mock model
        mock_model = Mock()
        mock_init_model.return_value = mock_model

        agent = Agent(config=mock_config)
        agent.initialize_model()

        # Mock planner, executor, verifier
        mock_planner = Mock()
        graph = TaskGraph()
        task = Task(name="test_task", action="test_action")
        task.set_result({"data": "result"})
        task.update_status(TaskStatus.COMPLETED)
        graph.add_task(task)

        planning_result = PlanningResult(
            graph=graph,
            strategy_used=PlanningStrategy.RULE_BASED,
            confidence=0.8,
            reasoning="Test reasoning",
        )
        mock_planner.plan.return_value = planning_result

        mock_executor = Mock()
        from planner.executor import ExecutionResult

        exec_result = ExecutionResult(
            success=True,
            completed_tasks=1,
            failed_tasks=0,
            skipped_tasks=0,
            total_duration_ms=50.0,
        )
        mock_executor.execute.return_value = exec_result

        mock_verifier = Mock()
        from planner.verifier import VerificationResult

        verif_result = VerificationResult(
            passed=True,
            level=VerificationLevel.STRICT,
        )
        mock_verifier.verify_graph_results.return_value = {task.task_id: verif_result}

        agent.planner = mock_planner
        agent.executor = mock_executor
        agent.verifier = mock_verifier
        agent.dr_manager = None  # Simplifier

        # Exécuter avec HTN
        conversation_id = "test_conv"
        response = agent._run_with_htn("Lis data.csv, analyse", conversation_id=conversation_id)

        # Vérifier que le planner a été appelé
        mock_planner.plan.assert_called_once()
        mock_executor.execute.assert_called_once()
        mock_verifier.verify_graph_results.assert_called_once()

        # Vérifier la réponse
        assert "response" in response
        assert "plan" in response
        assert "execution" in response
        assert "verifications" in response
        assert response["conversation_id"] == conversation_id


class TestAgentHTNModes:
    """Tests pour modes de fonctionnement Agent"""

    @patch("runtime.agent.get_config")
    @patch("runtime.model_interface.init_model")
    def test_agent_mode_simple_vs_htn(self, mock_init_model, mock_get_config):
        """Test distinction entre mode simple et HTN"""
        from runtime.agent import Agent

        # Mock configuration
        mock_config = Mock()
        mock_config.htn_planning = Mock()
        mock_config.htn_planning.enabled = True
        mock_config.htn_verification = None  # Pas de config de vérification
        mock_get_config.return_value = mock_config

        # Mock model
        mock_model = Mock()
        mock_init_model.return_value = mock_model

        agent = Agent(config=mock_config)
        agent.initialize_model()

        # Requête simple → mode simple
        simple_query = "Bonjour"
        requires = agent._requires_planning(simple_query)
        assert requires is False

        # Requête avec mots-clés multi-étapes → HTN
        multi_step_query = "Lis fichier puis analyse"
        requires = agent._requires_planning(multi_step_query)
        assert requires is True

        # Requête avec plusieurs actions → HTN
        multi_action_query = "Lis analyse génère"
        requires = agent._requires_planning(multi_action_query)
        assert requires is True


class TestAgentHTNErrorHandling:
    """Tests pour gestion d'erreurs HTN"""

    @patch("runtime.agent.get_config")
    @patch("runtime.model_interface.init_model")
    def test_agent_htn_execution_failure_fallback(self, mock_init_model, mock_get_config):
        """Test fallback sur mode simple si HTN échoue"""
        from runtime.agent import Agent
        from planner.task_graph import TaskGraph
        from planner.planner import PlanningResult
        from planner.executor import ExecutionResult

        # Mock configuration
        mock_config = Mock()
        mock_config.htn_planning = Mock()
        mock_config.htn_planning.default_strategy = "hybrid"
        mock_config.htn_execution = None
        mock_config.htn_verification = Mock()
        mock_config.htn_verification.default_level = "strict"
        mock_get_config.return_value = mock_config

        # Mock model
        mock_model = Mock()
        mock_init_model.return_value = mock_model

        agent = Agent(config=mock_config)
        agent.initialize_model()

        # Mock planner, executor (échec), verifier
        mock_planner = Mock()
        graph = TaskGraph()
        planning_result = PlanningResult(
            graph=graph,
            strategy_used=PlanningStrategy.RULE_BASED,
            confidence=0.8,
            reasoning="Test",
        )
        mock_planner.plan.return_value = planning_result

        mock_executor = Mock()
        # Simuler échec critique
        exec_result = ExecutionResult(
            success=False,  # Échec
            completed_tasks=0,
            failed_tasks=1,
            skipped_tasks=0,
            total_duration_ms=10.0,
        )
        mock_executor.execute.return_value = exec_result

        agent.planner = mock_planner
        agent.executor = mock_executor
        agent.verifier = Mock()
        agent.dr_manager = None

        # Mock _run_simple pour vérifier qu'il est appelé
        agent._run_simple = Mock(return_value={"response": "Simple mode fallback"})

        conversation_id = "test_conv"
        response = agent._run_with_htn("Requête complexe", conversation_id=conversation_id)

        # Devrait fallback sur mode simple
        agent._run_simple.assert_called_once()
        assert response["response"] == "Simple mode fallback"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
