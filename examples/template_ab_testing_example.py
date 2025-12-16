"""
Example: A/B Testing with Template Versions

This example demonstrates how to perform A/B testing with different
template versions to compare prompt effectiveness.

Use Case:
- Compare v1 (original) vs v2 (improved) system prompts
- Track metrics like response quality, token usage, user satisfaction
- Gradually roll out v2 based on results

Requirements:
1. Create v2 templates in prompts/templates/v2/
2. Run this script to simulate A/B testing
3. Analyze metrics to decide on rollout
"""

import random
import time
from typing import Dict, List, Tuple
from collections import defaultdict
from dataclasses import dataclass
from unittest.mock import Mock

from runtime.context_builder import ContextBuilder
from runtime.template_loader import get_template_loader


@dataclass
class ABTestMetrics:
    """Metrics for A/B test analysis"""
    version: str
    prompt_length: int
    generation_time: float
    tokens_used: int
    clarity_score: float  # 0-1, higher is better


class ABTestRunner:
    """
    A/B Test runner for template versions
    
    Distributes requests between versions and collects metrics.
    """
    
    def __init__(
        self,
        version_a: str = "v1",
        version_b: str = "v1",  # Use v1 for both in this demo
        split_ratio: float = 0.5,
    ):
        """
        Initialize A/B test runner
        
        Args:
            version_a: First template version to test
            version_b: Second template version to test
            split_ratio: Ratio of traffic to version_a (0.5 = 50/50)
        """
        self.version_a = version_a
        self.version_b = version_b
        self.split_ratio = split_ratio
        
        # Metrics storage
        self.metrics: Dict[str, List[ABTestMetrics]] = {
            version_a: [],
            version_b: [],
        }
    
    def select_version(self) -> str:
        """Select version based on split ratio"""
        return self.version_a if random.random() < self.split_ratio else self.version_b
    
    def generate_prompt(
        self,
        version: str,
        tool_registry: Mock,
        semantic_context: str = None,
    ) -> Tuple[str, ABTestMetrics]:
        """
        Generate prompt with specified version and collect metrics
        
        Args:
            version: Template version to use
            tool_registry: Mock tool registry
            semantic_context: Optional semantic context
            
        Returns:
            Tuple of (prompt, metrics)
        """
        # Create builder with specific version
        builder = ContextBuilder(template_version=version)
        
        # Measure generation time
        start_time = time.time()
        prompt = builder.build_system_prompt(
            tool_registry,
            semantic_context=semantic_context,
        )
        generation_time = time.time() - start_time
        
        # Estimate metrics
        prompt_length = len(prompt)
        tokens_used = len(prompt.split())  # Rough token estimate
        
        # Simulate clarity score (in real scenario, use LLM or human evaluation)
        clarity_score = self._estimate_clarity(prompt)
        
        # Collect metrics
        metrics = ABTestMetrics(
            version=version,
            prompt_length=prompt_length,
            generation_time=generation_time,
            tokens_used=tokens_used,
            clarity_score=clarity_score,
        )
        
        self.metrics[version].append(metrics)
        
        return prompt, metrics
    
    def _estimate_clarity(self, prompt: str) -> float:
        """
        Estimate prompt clarity score (0-1)
        
        In production, use:
        - LLM-based evaluation
        - Human ratings
        - Task completion rates
        """
        # Simple heuristics for demo
        score = 1.0
        
        # Penalize if too long
        if len(prompt) > 3000:
            score -= 0.1
        
        # Reward if has clear structure
        if "CONTEXTE:" in prompt:
            score += 0.05
        if "OUTILS DISPONIBLES:" in prompt:
            score += 0.05
        
        return min(1.0, max(0.0, score))
    
    def run_test(
        self,
        num_requests: int = 100,
    ):
        """
        Run A/B test with simulated requests
        
        Args:
            num_requests: Number of test requests to simulate
        """
        print(f"Starting A/B test: {self.version_a} vs {self.version_b}")
        print(f"Split ratio: {self.split_ratio:.0%} / {1-self.split_ratio:.0%}")
        print(f"Number of requests: {num_requests}\n")
        
        # Mock tool registry
        mock_tools = {}
        for i in range(5):
            mock_tool = Mock()
            mock_tool.get_schema.return_value = {
                'description': f'PME Tool {i}',
                'parameters': {'param': 'value'}
            }
            mock_tools[f'tool{i}'] = mock_tool
        
        mock_registry = Mock()
        mock_registry.list_all.return_value = mock_tools
        
        # Run requests
        for i in range(num_requests):
            version = self.select_version()
            
            # Add semantic context 20% of the time
            semantic_context = None
            if random.random() < 0.2:
                semantic_context = "[Contexte] PME québécoise..."
            
            prompt, metrics = self.generate_prompt(
                version,
                mock_registry,
                semantic_context,
            )
            
            if (i + 1) % 20 == 0:
                print(f"Progress: {i + 1}/{num_requests} requests completed")
        
        print("\nTest completed!\n")
    
    def analyze_results(self):
        """Analyze and display A/B test results"""
        print("=" * 60)
        print("A/B TEST RESULTS")
        print("=" * 60)
        
        for version in [self.version_a, self.version_b]:
            metrics = self.metrics[version]
            
            if not metrics:
                print(f"\n{version}: No data")
                continue
            
            # Calculate averages
            avg_length = sum(m.prompt_length for m in metrics) / len(metrics)
            avg_time = sum(m.generation_time for m in metrics) / len(metrics)
            avg_tokens = sum(m.tokens_used for m in metrics) / len(metrics)
            avg_clarity = sum(m.clarity_score for m in metrics) / len(metrics)
            
            print(f"\n{version.upper()} (n={len(metrics)}):")
            print(f"  Avg prompt length:     {avg_length:.0f} chars")
            print(f"  Avg generation time:   {avg_time*1000:.2f} ms")
            print(f"  Avg tokens used:       {avg_tokens:.0f}")
            print(f"  Avg clarity score:     {avg_clarity:.3f}")
        
        # Compare versions
        print("\n" + "=" * 60)
        print("COMPARISON")
        print("=" * 60)
        
        if len(self.metrics[self.version_a]) > 0 and len(self.metrics[self.version_b]) > 0:
            a_clarity = sum(m.clarity_score for m in self.metrics[self.version_a]) / len(self.metrics[self.version_a])
            b_clarity = sum(m.clarity_score for m in self.metrics[self.version_b]) / len(self.metrics[self.version_b])
            
            if a_clarity > b_clarity:
                winner = self.version_a
                improvement = (a_clarity - b_clarity) / b_clarity * 100
            else:
                winner = self.version_b
                improvement = (b_clarity - a_clarity) / a_clarity * 100
            
            print(f"\nWinner: {winner}")
            print(f"Improvement: {improvement:.1f}% better clarity")
            
            # Recommendation
            if improvement > 5:
                print(f"\n✅ RECOMMENDATION: Roll out {winner} to all users")
            elif improvement > 2:
                print(f"\n⚠️  RECOMMENDATION: Consider gradual rollout of {winner}")
            else:
                print(f"\n➡️  RECOMMENDATION: No significant difference, keep current version")
        
        print("\n" + "=" * 60)


def example_50_50_split():
    """Example: 50/50 A/B test"""
    print("\n" + "=" * 60)
    print("EXAMPLE 1: 50/50 Split Test")
    print("=" * 60 + "\n")
    
    runner = ABTestRunner(
        version_a="v1",
        version_b="v1",  # Using v1 for both in this demo
        split_ratio=0.5,
    )
    
    runner.run_test(num_requests=100)
    runner.analyze_results()


def example_gradual_rollout():
    """Example: Gradual rollout (10% v2, 90% v1)"""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Gradual Rollout (10% new version)")
    print("=" * 60 + "\n")
    
    runner = ABTestRunner(
        version_a="v1",
        version_b="v1",  # Using v1 for both in this demo
        split_ratio=0.9,  # 90% v1, 10% v2
    )
    
    runner.run_test(num_requests=100)
    runner.analyze_results()


def example_champion_challenger():
    """Example: Champion/Challenger (80/20)"""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Champion/Challenger (80/20)")
    print("=" * 60 + "\n")
    
    runner = ABTestRunner(
        version_a="v1",  # Champion
        version_b="v1",  # Challenger (using v1 for demo)
        split_ratio=0.8,
    )
    
    runner.run_test(num_requests=100)
    runner.analyze_results()


def main():
    """Run all A/B testing examples"""
    print("\n" + "=" * 60)
    print("FILAGENT TEMPLATE A/B TESTING EXAMPLES")
    print("=" * 60)
    print("\nThese examples demonstrate how to A/B test different")
    print("template versions to improve prompt quality.\n")
    print("Note: Using v1 for both versions in this demo.")
    print("In production, create v2 templates to compare.\n")
    
    # Run examples
    example_50_50_split()
    example_gradual_rollout()
    example_champion_challenger()
    
    print("\n" + "=" * 60)
    print("NEXT STEPS")
    print("=" * 60)
    print("""
To run real A/B tests:

1. Create v2 templates:
   mkdir prompts/templates/v2
   cp prompts/templates/v1/*.j2 prompts/templates/v2/
   # Edit v2 templates

2. Update this script to use v2:
   runner = ABTestRunner(version_a="v1", version_b="v2")

3. Collect real metrics:
   - User feedback
   - Task completion rates
   - Response quality scores
   - Token usage and costs

4. Make data-driven decisions:
   - If v2 is better: gradual rollout
   - If v2 is worse: stick with v1
   - If similar: consider other factors (cost, maintainability)
""")


if __name__ == '__main__':
    main()
