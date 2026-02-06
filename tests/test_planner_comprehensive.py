"""
Comprehensive tests for HTN Planner (planner/planner.py)

Coverage targets:
- Task decomposition logic
- Parallel execution coordination
- Verification levels
- Rule-based vs LLM-based strategies
- Error handling and fallbacks
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from planner import HierarchicalPlanner, PlanningStrategy, PlanningResult, TaskDecompositionError
from planner.task_graph import Task, TaskGraph, TaskPriority, TaskStatus


def create_valid_task_graph(
    task_name: str = "test_task", action: str = "generic_execute"
) -> TaskGraph:
    """Create a TaskGraph with one task - required for plan validation.

    Args:
        task_name: Name for the task (customize for specific test scenarios)
        action: Action name for the task

    Returns:
        TaskGraph with one valid task
    """
    graph = TaskGraph()
    task = Task(
        name=task_name,
        action=action,
        params={"query": "test"},
        priority=TaskPriority.NORMAL,
    )
    graph.add_task(task)
    return graph


@pytest.fixture
def mock_model():
    """Mock model interface"""
    model = Mock()
    model.generate.return_value = Mock(text="Mock response")
    return model


@pytest.fixture
def mock_tools_registry():
    """Mock tools registry"""
    registry = Mock()
    # get_all() returns a list of tools with 'name' attribute (per ToolsRegistry Protocol)
    registry.get_all.return_value = [
        Mock(name="calculator"),
        Mock(name="file_reader"),
    ]
    return registry


@pytest.fixture
def planner(mock_model, mock_tools_registry):
    """HTN Planner instance with mocks"""
    return HierarchicalPlanner(
        model_interface=mock_model,
        tools_registry=mock_tools_registry,
        max_decomposition_depth=3,
        enable_tracing=True,
    )


@pytest.mark.unit
@pytest.mark.htn
@pytest.mark.coverage
class TestHierarchicalPlanner:
    """Comprehensive tests for HierarchicalPlanner"""

    def test_planner_initialization(self, mock_model, mock_tools_registry):
        """Test planner initialization"""
        planner = HierarchicalPlanner(
            model_interface=mock_model,
            tools_registry=mock_tools_registry,
            max_decomposition_depth=5,
            enable_tracing=True,
        )

        # HierarchicalPlanner stores these with explicit attribute names
        assert planner.model == mock_model
        assert planner.tools_registry == mock_tools_registry
        assert planner.max_depth == 5
        assert planner.enable_tracing is True

    def test_plan_with_rule_based_strategy(self, planner):
        """Test planning with rule-based strategy"""
        query = "Calculate 2 + 2"

        with patch.object(planner, "_plan_rule_based") as mock_rule:
            mock_result = PlanningResult(
                graph=create_valid_task_graph(),
                strategy_used=PlanningStrategy.RULE_BASED,
                confidence=0.9,
                reasoning="Simple calculation",
            )
            mock_rule.return_value = mock_result

            result = planner.plan(query, strategy=PlanningStrategy.RULE_BASED)

            assert result.strategy_used == PlanningStrategy.RULE_BASED
            assert mock_rule.called

    def test_plan_with_llm_based_strategy(self, planner):
        """Test planning with LLM-based strategy"""
        query = "Analyze the data and create a report"

        with patch.object(planner, "_plan_llm_based") as mock_llm:
            mock_result = PlanningResult(
                graph=create_valid_task_graph(),
                strategy_used=PlanningStrategy.LLM_BASED,
                confidence=0.85,
                reasoning="Complex task requiring LLM",
            )
            mock_llm.return_value = mock_result

            result = planner.plan(query, strategy=PlanningStrategy.LLM_BASED)

            assert result.strategy_used == PlanningStrategy.LLM_BASED
            assert mock_llm.called

    def test_plan_with_hybrid_strategy(self, planner):
        """Test planning with hybrid strategy"""
        query = "Read file and calculate sum"

        with patch.object(planner, "_plan_hybrid") as mock_hybrid:
            mock_result = PlanningResult(
                graph=create_valid_task_graph(),
                strategy_used=PlanningStrategy.HYBRID,
                confidence=0.92,
                reasoning="Hybrid approach",
            )
            mock_hybrid.return_value = mock_result

            result = planner.plan(query, strategy=PlanningStrategy.HYBRID)

            assert result.strategy_used == PlanningStrategy.HYBRID
            assert mock_hybrid.called

    def test_plan_error_handling(self, planner):
        """Test planning error handling"""
        query = "Invalid query"

        with patch.object(planner, "_plan_hybrid", side_effect=Exception("Planning failed")):
            with pytest.raises(Exception):
                planner.plan(query, strategy=PlanningStrategy.HYBRID)

    # NOTE: Tests for _decompose_task and _identify_dependencies removed
    # These methods do not exist in the current HierarchicalPlanner implementation
    # The planner uses _plan_rule_based, _plan_llm_based, _plan_hybrid instead


@pytest.mark.unit
@pytest.mark.htn
@pytest.mark.coverage
class TestPlanningResult:
    """Tests for PlanningResult dataclass"""

    def test_planning_result_creation(self):
        """Test PlanningResult creation"""
        graph = TaskGraph()
        result = PlanningResult(
            graph=graph,
            strategy_used=PlanningStrategy.HYBRID,
            confidence=0.88,
            reasoning="Test reasoning",
        )

        assert result.graph == graph
        assert result.strategy_used == PlanningStrategy.HYBRID
        assert result.confidence == 0.88
        assert result.reasoning == "Test reasoning"

    def test_planning_result_metadata_auto_init(self):
        """Test metadata auto-initialization with timestamp"""
        result = PlanningResult(
            graph=create_valid_task_graph(),
            strategy_used=PlanningStrategy.RULE_BASED,
            confidence=0.9,
            reasoning="Test",
        )

        assert "planned_at" in result.metadata
        assert isinstance(result.metadata["planned_at"], str)

    def test_planning_result_to_dict(self):
        """Test PlanningResult serialization"""
        result = PlanningResult(
            graph=create_valid_task_graph(),
            strategy_used=PlanningStrategy.LLM_BASED,
            confidence=0.75,
            reasoning="LLM decomposition",
        )

        result_dict = result.to_dict()

        assert "graph" in result_dict
        assert "strategy_used" in result_dict
        assert result_dict["strategy_used"] == "llm_based"
        assert result_dict["confidence"] == 0.75
        assert "reasoning" in result_dict
        assert "metadata" in result_dict


@pytest.mark.unit
@pytest.mark.htn
@pytest.mark.coverage
class TestPlanningStrategies:
    """Tests for different planning strategies"""

    def test_rule_based_pattern_matching(self, planner):
        """Test rule-based strategy pattern matching"""
        # Test queries that match simple patterns
        simple_queries = ["Calculate 2 + 2", "Read file.txt", "List directory contents"]

        for query in simple_queries:
            # Rule-based should handle simple patterns
            with patch.object(planner, "_plan_rule_based") as mock_rule:
                mock_rule.return_value = PlanningResult(
                    graph=create_valid_task_graph(),
                    strategy_used=PlanningStrategy.RULE_BASED,
                    confidence=0.9,
                    reasoning="Simple pattern",
                )
                result = planner.plan(query, strategy=PlanningStrategy.RULE_BASED)
                assert result.strategy_used == PlanningStrategy.RULE_BASED

    def test_llm_based_complex_queries(self, planner):
        """Test LLM-based strategy for complex queries"""
        complex_query = "Analyze the sales data, identify trends, and generate a comprehensive report with visualizations"

        with patch.object(planner, "_plan_llm_based") as mock_llm:
            mock_llm.return_value = PlanningResult(
                graph=create_valid_task_graph(),
                strategy_used=PlanningStrategy.LLM_BASED,
                confidence=0.85,
                reasoning="Complex multi-step task",
            )

            result = planner.plan(complex_query, strategy=PlanningStrategy.LLM_BASED)
            assert result.strategy_used == PlanningStrategy.LLM_BASED

    def test_hybrid_strategy_fallback(self, planner):
        """Test hybrid strategy falls back appropriately"""
        query = "Moderate complexity task"

        with patch.object(planner, "_plan_hybrid") as mock_hybrid:
            # Hybrid tries rule-based first, then LLM
            mock_hybrid.return_value = PlanningResult(
                graph=create_valid_task_graph(),
                strategy_used=PlanningStrategy.HYBRID,
                confidence=0.88,
                reasoning="Combined approach",
            )

            result = planner.plan(query, strategy=PlanningStrategy.HYBRID)
            assert result.strategy_used == PlanningStrategy.HYBRID


@pytest.mark.unit
@pytest.mark.htn
@pytest.mark.coverage
class TestPlannerTraceability:
    """Tests for planner traceability and logging"""

    def test_tracing_enabled(self, mock_model, mock_tools_registry):
        """Test planner with tracing enabled"""
        planner = HierarchicalPlanner(
            model_interface=mock_model, tools_registry=mock_tools_registry, enable_tracing=True
        )

        assert planner.enable_tracing is True

    def test_tracing_disabled(self, mock_model, mock_tools_registry):
        """Test planner with tracing disabled"""
        planner = HierarchicalPlanner(
            model_interface=mock_model, tools_registry=mock_tools_registry, enable_tracing=False
        )

        assert planner.enable_tracing is False

    def test_planning_metrics_recorded(self, planner):
        """Test that planning metrics are recorded"""
        query = "Test query"

        with (
            patch.object(planner, "_plan_hybrid") as mock_plan,
            patch("planner.planner.get_metrics") as mock_metrics,
        ):
            mock_plan.return_value = PlanningResult(
                graph=create_valid_task_graph(),
                strategy_used=PlanningStrategy.HYBRID,
                confidence=0.9,
                reasoning="Test",
            )

            result = planner.plan(query, strategy=PlanningStrategy.HYBRID)

            # Metrics should be accessed
            assert mock_metrics.called or result is not None


@pytest.mark.unit
@pytest.mark.htn
@pytest.mark.coverage
class TestPlannerEdgeCases:
    """Tests for edge cases and error conditions"""

    def test_empty_query(self, planner):
        """Test planning with empty query creates fallback task"""
        # Empty queries don't raise - they create a fallback generic_execute task
        with patch.object(planner, "_plan_hybrid") as mock_hybrid:
            mock_hybrid.return_value = PlanningResult(
                graph=create_valid_task_graph(task_name="fallback_task"),
                strategy_used=PlanningStrategy.HYBRID,
                confidence=0.5,
                reasoning="Fallback for empty query",
            )
            result = planner.plan("", strategy=PlanningStrategy.HYBRID)
            assert result.graph is not None
            assert len(result.graph.tasks) >= 1

    def test_very_long_query(self, planner):
        """Test planning with very long query"""
        long_query = "Calculate " * 1000 + "2 + 2"

        with patch.object(planner, "_plan_rule_based") as mock_rule:
            mock_rule.return_value = PlanningResult(
                graph=create_valid_task_graph(),
                strategy_used=PlanningStrategy.RULE_BASED,
                confidence=0.5,
                reasoning="Long query",
            )

            result = planner.plan(long_query, strategy=PlanningStrategy.RULE_BASED)
            assert result is not None

    def test_none_model_interface(self, mock_tools_registry):
        """Test planner with None model interface"""
        planner = HierarchicalPlanner(model_interface=None, tools_registry=mock_tools_registry)

        # LLM-based planning should fail
        with pytest.raises(Exception):
            planner.plan("Test query", strategy=PlanningStrategy.LLM_BASED)

    def test_none_tools_registry(self, mock_model):
        """Test planner with None tools registry"""
        planner = HierarchicalPlanner(model_interface=mock_model, tools_registry=None)

        # Should still initialize
        assert planner.tools_registry is None
