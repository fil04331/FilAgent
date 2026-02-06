"""
Unit tests for architecture.router module

Tests the StrategyRouter component following Clean Architecture principles.
"""

import pytest
from architecture.router import StrategyRouter, ExecutionStrategy, RoutingDecision


@pytest.mark.unit
class TestStrategyRouter:
    """Test suite for StrategyRouter component"""

    def test_router_initialization_defaults(self):
        """Test router initializes with sensible defaults"""
        router = StrategyRouter()

        assert router.htn_enabled is True
        assert "puis" in router.multi_step_keywords
        assert "analyse" in router.action_verbs
        assert router.min_actions_for_planning == 2

    def test_router_initialization_custom(self):
        """Test router accepts custom configuration"""
        custom_keywords = ["step1", "step2"]
        custom_verbs = ["do", "make"]

        router = StrategyRouter(
            htn_enabled=False,
            multi_step_keywords=custom_keywords,
            action_verbs=custom_verbs,
            min_actions_for_planning=3,
        )

        assert router.htn_enabled is False
        assert router.multi_step_keywords == custom_keywords
        assert router.action_verbs == custom_verbs
        assert router.min_actions_for_planning == 3

    def test_route_htn_disabled(self):
        """When HTN disabled, should always return SIMPLE strategy"""
        router = StrategyRouter(htn_enabled=False)

        # Even complex query should return SIMPLE
        decision = router.route("Lis le fichier puis analyse-le et crée un rapport")

        assert decision.strategy == ExecutionStrategy.SIMPLE
        assert decision.confidence == 1.0
        assert "disabled" in decision.reasoning.lower()

    def test_route_multi_step_keyword_puis(self):
        """Should detect 'puis' keyword for planning"""
        router = StrategyRouter()

        decision = router.route("Lis le fichier puis affiche le résultat")

        assert decision.strategy == ExecutionStrategy.HTN
        assert decision.confidence >= 0.7
        assert len(decision.detected_patterns) > 0
        assert any("multi_step" in p for p in decision.detected_patterns)

    def test_route_multi_step_keyword_ensuite(self):
        """Should detect 'ensuite' keyword for planning"""
        router = StrategyRouter()

        decision = router.route("Crée un fichier, ensuite calcule la somme")

        assert decision.strategy == ExecutionStrategy.HTN
        assert "multi_step" in decision.detected_patterns[0]

    def test_route_multi_step_keyword_apres(self):
        """Should detect 'après' keyword for planning"""
        router = StrategyRouter()

        decision = router.route("Après avoir lu, génère un rapport")

        assert decision.strategy == ExecutionStrategy.HTN

    def test_route_multiple_action_verbs(self):
        """Should detect multiple action verbs for planning"""
        router = StrategyRouter()

        decision = router.route("Lis le document, analyse les données et génère un rapport")

        assert decision.strategy == ExecutionStrategy.HTN
        assert any("action_verbs" in p for p in decision.detected_patterns)

    def test_route_simple_query(self):
        """Simple query should return SIMPLE strategy"""
        router = StrategyRouter()

        decision = router.route("Quelle est la capitale du Québec?")

        assert decision.strategy == ExecutionStrategy.SIMPLE
        assert decision.confidence >= 0.7
        assert len(decision.detected_patterns) == 0

    def test_route_single_action(self):
        """Single action query should return SIMPLE"""
        router = StrategyRouter()

        decision = router.route("Lis le fichier config.yaml")

        assert decision.strategy == ExecutionStrategy.SIMPLE

    def test_route_english_keywords(self):
        """Should detect English multi-step keywords"""
        router = StrategyRouter()

        decision = router.route("Read the file then analyze the data")

        assert decision.strategy == ExecutionStrategy.HTN

    def test_route_english_verbs(self):
        """Should detect English action verbs"""
        router = StrategyRouter()

        decision = router.route("Read the document, analyze data, and create report")

        assert decision.strategy == ExecutionStrategy.HTN

    def test_route_confidence_scaling(self):
        """Confidence should increase with more signals"""
        router = StrategyRouter()

        # Single keyword
        decision1 = router.route("Lis puis affiche")

        # Multiple keywords and actions
        decision2 = router.route("Lis, puis analyse, ensuite génère, finalement affiche")

        assert decision2.confidence >= decision1.confidence

    def test_route_case_insensitive(self):
        """Routing should be case-insensitive"""
        router = StrategyRouter()

        decision1 = router.route("Lis puis analyse")
        decision2 = router.route("LIS PUIS ANALYSE")
        decision3 = router.route("LiS pUiS aNaLySe")

        assert (
            decision1.strategy == decision2.strategy == decision3.strategy == ExecutionStrategy.HTN
        )

    def test_should_use_planning_shortcut(self):
        """Test backward-compatible boolean method"""
        router = StrategyRouter()

        assert router.should_use_planning("Lis puis analyse") is True
        assert router.should_use_planning("Quelle heure est-il?") is False

    def test_routing_decision_model(self):
        """Test RoutingDecision Pydantic model"""
        decision = RoutingDecision(
            strategy=ExecutionStrategy.HTN,
            confidence=0.85,
            reasoning="Test reasoning",
            detected_patterns=["pattern1", "pattern2"],
        )

        assert decision.strategy == ExecutionStrategy.HTN
        assert decision.confidence == 0.85
        assert len(decision.detected_patterns) == 2

    def test_routing_decision_confidence_validation(self):
        """Confidence must be between 0 and 1"""
        # Valid confidence
        decision = RoutingDecision(
            strategy=ExecutionStrategy.SIMPLE,
            confidence=0.5,
            reasoning="Test",
        )
        assert decision.confidence == 0.5

        # Invalid confidence should fail validation
        with pytest.raises(Exception):  # Pydantic validation error
            RoutingDecision(
                strategy=ExecutionStrategy.SIMPLE,
                confidence=1.5,  # > 1.0
                reasoning="Test",
            )

    def test_router_with_custom_min_actions(self):
        """Test custom minimum actions threshold"""
        router = StrategyRouter(min_actions_for_planning=3)

        # 2 actions but no multi-step keywords - should be SIMPLE
        # Use "avec" instead of "et" since "et" is a multi-step keyword
        decision1 = router.route("Lis avec analyse")
        assert decision1.strategy == ExecutionStrategy.SIMPLE

        # 3 actions - should be HTN
        decision2 = router.route("Lis avec analyse et génère")
        assert decision2.strategy == ExecutionStrategy.HTN

    def test_router_reasoning_messages(self):
        """Routing decision should include human-readable reasoning"""
        router = StrategyRouter()

        decision_htn = router.route("Lis puis analyse")
        assert len(decision_htn.reasoning) > 0
        assert isinstance(decision_htn.reasoning, str)

        decision_simple = router.route("Bonjour")
        assert len(decision_simple.reasoning) > 0
        assert isinstance(decision_simple.reasoning, str)


@pytest.mark.unit
class TestExecutionStrategy:
    """Test ExecutionStrategy enum"""

    def test_strategy_values(self):
        """Test enum has expected values"""
        assert ExecutionStrategy.SIMPLE.value == "simple"
        assert ExecutionStrategy.HTN.value == "htn"

    def test_strategy_comparison(self):
        """Test enum comparison"""
        assert ExecutionStrategy.SIMPLE == ExecutionStrategy.SIMPLE
        assert ExecutionStrategy.SIMPLE != ExecutionStrategy.HTN
