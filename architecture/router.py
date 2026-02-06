"""
Router Component - Strategic Decision Making

Implements the Router pattern to decide execution strategy (Planning vs Direct)
BEFORE executing the agent loop. This follows the Strategy pattern and separates
decision logic from execution logic.

Key Principles:
1. Single Responsibility: ONLY decides strategy, doesn't execute
2. Dependency Injection: Receives configuration, doesn't instantiate
3. Testability: Pure logic, no side effects
4. Extensibility: Easy to add new routing rules
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ExecutionStrategy(str, Enum):
    """Execution strategy options"""

    SIMPLE = "simple"  # Direct execution without planning
    HTN = "htn"  # Hierarchical Task Network planning


class RoutingDecision(BaseModel):
    """Result of routing decision with justification"""

    strategy: ExecutionStrategy
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in decision (0-1)")
    reasoning: str = Field(description="Human-readable explanation of decision")
    detected_patterns: list[str] = Field(
        default_factory=list, description="Patterns detected in query"
    )


class StrategyRouter:
    """
    Router component that decides execution strategy based on query analysis.

    This class implements semantic routing to determine if a query requires
    HTN planning or can be handled with simple execution.

    Design:
    - Stateless: No instance variables except configuration
    - Pure logic: Decision based only on input parameters
    - Testable: No external dependencies
    """

    def __init__(
        self,
        htn_enabled: bool = True,
        multi_step_keywords: Optional[list[str]] = None,
        action_verbs: Optional[list[str]] = None,
        min_actions_for_planning: int = 2,
    ):
        """
        Initialize router with configuration.

        Args:
            htn_enabled: Whether HTN planning is available
            multi_step_keywords: Keywords indicating multi-step tasks
            action_verbs: Action verbs to count
            min_actions_for_planning: Minimum actions to trigger planning
        """
        self.htn_enabled = htn_enabled
        self.multi_step_keywords = multi_step_keywords or [
            "puis",
            "ensuite",
            "après",
            "finalement",
            "et",
            "then",
            "next",
            "after",
            "finally",
            "and",
        ]
        self.action_verbs = action_verbs or [
            "lis",
            "analyse",
            "génère",
            "crée",
            "calcule",
            "read",
            "analyze",
            "generate",
            "create",
            "calculate",
            "écris",
            "supprime",
            "modifie",
            "vérifie",
            "write",
            "delete",
            "modify",
            "verify",
            "check",
        ]
        self.min_actions_for_planning = min_actions_for_planning

    def route(self, query: str) -> RoutingDecision:
        """
        Analyze query and decide execution strategy.

        Args:
            query: User query to analyze

        Returns:
            RoutingDecision with strategy, confidence, and reasoning
        """
        # If HTN is disabled, always use simple strategy
        if not self.htn_enabled:
            return RoutingDecision(
                strategy=ExecutionStrategy.SIMPLE,
                confidence=1.0,
                reasoning="HTN planning is disabled in configuration",
                detected_patterns=[],
            )

        # Analyze query patterns
        query_lower = query.lower()
        detected_patterns = []

        # Check for multi-step keywords
        multi_step_detected = any(keyword in query_lower for keyword in self.multi_step_keywords)
        if multi_step_detected:
            detected_keywords = [kw for kw in self.multi_step_keywords if kw in query_lower]
            detected_patterns.append(f"multi_step_keywords: {', '.join(detected_keywords)}")

        # Count action verbs
        action_count = sum(1 for verb in self.action_verbs if verb in query_lower)
        if action_count >= self.min_actions_for_planning:
            detected_patterns.append(f"action_verbs: {action_count} detected")

        # Decision logic
        requires_planning = multi_step_detected or action_count >= self.min_actions_for_planning

        if requires_planning:
            # Calculate confidence based on strength of signals
            confidence = 0.7  # Base confidence
            if multi_step_detected:
                confidence += 0.15
            if action_count >= 3:
                confidence += 0.15
            confidence = min(confidence, 1.0)

            return RoutingDecision(
                strategy=ExecutionStrategy.HTN,
                confidence=confidence,
                reasoning=f"Complex query detected: {len(detected_patterns)} patterns matched",
                detected_patterns=detected_patterns,
            )
        else:
            return RoutingDecision(
                strategy=ExecutionStrategy.SIMPLE,
                confidence=0.8,
                reasoning="Simple query, direct execution sufficient",
                detected_patterns=[],
            )

    def should_use_planning(self, query: str) -> bool:
        """
        Simplified boolean decision for backward compatibility.

        Args:
            query: User query to analyze

        Returns:
            True if HTN planning should be used
        """
        decision = self.route(query)
        return decision.strategy == ExecutionStrategy.HTN
