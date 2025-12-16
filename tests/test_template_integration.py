"""
Integration Tests for Template System

Tests the complete template system working with Agent and Planner.
"""

import pytest
from unittest.mock import Mock, MagicMock

from runtime.context_builder import ContextBuilder
from planner.planner import HierarchicalPlanner, PlanningStrategy
from runtime.template_loader import get_template_loader


class TestTemplateSystemIntegration:
    """Integration tests for the template system"""
    
    def test_context_builder_with_template_loader(self):
        """Test ContextBuilder works with real template loader"""
        loader = get_template_loader(version='v1', force_reload=True)
        builder = ContextBuilder(template_loader=loader)
        
        # Mock tool registry
        mock_tool = Mock()
        mock_tool.get_schema.return_value = {
            'description': 'Analyzes PME business data',
            'parameters': {'file_path': 'string'}
        }
        
        mock_registry = Mock()
        mock_registry.list_all.return_value = {'pme_analyzer': mock_tool}
        
        # Generate system prompt
        prompt = builder.build_system_prompt(mock_registry)
        
        # Verify prompt quality
        assert 'FilAgent' in prompt
        assert 'PME québécoises' in prompt
        assert 'pme_analyzer' in prompt
        assert 'Analyzes PME business data' in prompt
        assert len(prompt) > 1500  # Substantial content
    
    def test_planner_with_template_loader(self):
        """Test HierarchicalPlanner works with real template loader"""
        loader = get_template_loader(version='v1', force_reload=True)
        
        # Mock model interface
        mock_model = Mock()
        
        planner = HierarchicalPlanner(
            model_interface=mock_model,
            template_loader=loader
        )
        
        # Test that prompt building works
        system_prompt = planner._build_decomposition_prompt()
        
        assert 'décomposition' in system_prompt.lower()
        assert 'tâches atomiques' in system_prompt.lower()
        assert 'JSON' in system_prompt
    
    def test_planner_user_prompt_with_query(self):
        """Test planner generates proper user prompt"""
        loader = get_template_loader(version='v1', force_reload=True)
        
        planner = HierarchicalPlanner(template_loader=loader)
        
        query = "Analyse les données de ventes et génère un rapport PDF"
        user_prompt = planner._build_user_decomposition_prompt(query)
        
        assert query in user_prompt
        assert 'JSON' in user_prompt
        assert 'tasks' in user_prompt
        assert 'depends_on' in user_prompt
    
    def test_end_to_end_prompt_generation(self):
        """Test complete prompt generation flow"""
        loader = get_template_loader(version='v1', force_reload=True)
        
        # 1. Context Builder generates system prompt
        builder = ContextBuilder(template_loader=loader)
        mock_registry = Mock()
        mock_registry.list_all.return_value = {}
        
        system_prompt = builder.build_system_prompt(mock_registry)
        assert len(system_prompt) > 1000
        
        # 2. Planner generates decomposition prompts
        planner = HierarchicalPlanner(template_loader=loader)
        
        decomp_prompt = planner._build_decomposition_prompt()
        assert len(decomp_prompt) > 200
        
        user_prompt = planner._build_user_decomposition_prompt("Test query")
        assert 'Test query' in user_prompt
        
        # Both use same template loader
        assert builder.template_loader.version == planner.template_loader.version
    
    def test_template_versioning_consistency(self):
        """Test that template versions are consistent across components"""
        loader_v1 = get_template_loader(version='v1', force_reload=True)
        
        builder = ContextBuilder(template_loader=loader_v1)
        planner = HierarchicalPlanner(template_loader=loader_v1)
        
        # Both should use same version
        assert builder.template_loader.version == 'v1'
        assert planner.template_loader.version == 'v1'
        
        # Verify templates exist
        templates = loader_v1.list_templates()
        assert 'system_prompt' in templates
        assert 'planner_decomposition' in templates
        assert 'planner_user_prompt' in templates


class TestTemplateWithSemanticContext:
    """Test template system with semantic context injection"""
    
    def test_system_prompt_with_semantic_context(self):
        """Test that semantic context is properly injected"""
        builder = ContextBuilder()
        
        mock_registry = Mock()
        mock_registry.list_all.return_value = {}
        
        semantic_context = """[Contexte sémantique pertinent]
1. (Score: 0.92, Source: pme_guide.pdf)
Les PME québécoises bénéficient de plusieurs programmes de subventions..."""
        
        prompt = builder.build_system_prompt(
            mock_registry,
            semantic_context=semantic_context
        )
        
        # Verify semantic context is included
        assert 'Contexte sémantique' in prompt or semantic_context in prompt
        assert 'PME québécoises' in prompt


class TestTemplateFallbackBehavior:
    """Test fallback behavior when templates fail"""
    
    def test_context_builder_fallback(self):
        """Test ContextBuilder falls back gracefully"""
        builder = ContextBuilder()
        
        # Mock template loader to fail
        mock_loader = Mock()
        mock_loader.render.side_effect = Exception("Template error")
        builder.template_loader = mock_loader
        
        mock_registry = Mock()
        mock_registry.list_all.return_value = {}
        
        # Should not crash, should use fallback
        prompt = builder.build_system_prompt(mock_registry)
        
        assert 'FilAgent' in prompt
        assert len(prompt) > 1000
    
    def test_planner_fallback(self):
        """Test HierarchicalPlanner falls back gracefully"""
        planner = HierarchicalPlanner()
        
        # Mock template loader to fail
        mock_loader = Mock()
        mock_loader.render.side_effect = Exception("Template error")
        planner.template_loader = mock_loader
        
        # Should not crash, should use fallback
        system_prompt = planner._build_decomposition_prompt()
        user_prompt = planner._build_user_decomposition_prompt("Test")
        
        assert 'décomposition' in system_prompt.lower()
        assert 'Test' in user_prompt


class TestTemplatePerformance:
    """Performance tests for template system"""
    
    def test_repeated_prompt_generation_performance(self):
        """Test that repeated prompt generation is fast (cached)"""
        import time
        
        builder = ContextBuilder()
        mock_registry = Mock()
        mock_registry.list_all.return_value = {}
        
        # First generation (includes template compilation)
        start = time.time()
        for _ in range(10):
            builder.build_system_prompt(mock_registry)
        first_batch = time.time() - start
        
        # Second batch (should be cached)
        start = time.time()
        for _ in range(10):
            builder.build_system_prompt(mock_registry)
        second_batch = time.time() - start
        
        # Second batch should be as fast or faster
        assert second_batch <= first_batch * 1.5  # Allow some variance
        
        # Both should be reasonably fast
        assert first_batch < 0.5  # 10 iterations in < 500ms
        assert second_batch < 0.5


@pytest.mark.integration
class TestRealWorldScenarios:
    """Test real-world usage scenarios"""
    
    def test_pme_business_scenario(self):
        """Test template system for PME business use case"""
        builder = ContextBuilder()
        
        # Simulate real PME tools
        mock_tools = {
            'document_analyzer': Mock(),
            'web_search': Mock(),
            'calculator': Mock(),
        }
        
        for tool in mock_tools.values():
            tool.get_schema.return_value = {
                'description': 'PME business tool',
                'parameters': {'input': 'string'}
            }
        
        mock_registry = Mock()
        mock_registry.list_all.return_value = mock_tools
        
        semantic_context = """[Documents pertinents]
- Guide des subventions PME Québec 2024
- Réglementation Loi 25"""
        
        prompt = builder.build_system_prompt(
            mock_registry,
            semantic_context=semantic_context
        )
        
        # Verify PME-specific content
        assert 'PME québécoises' in prompt
        assert 'Loi 25' in prompt
        assert 'document_analyzer' in prompt
        assert 'subventions' in prompt or 'Subventions' in prompt or semantic_context in prompt
    
    def test_multi_step_planning_scenario(self):
        """Test template system for multi-step planning"""
        planner = HierarchicalPlanner()
        
        query = "Analyse les données de ventes 2023, calcule les tendances, et génère un rapport exécutif"
        
        # Generate prompts
        system_prompt = planner._build_decomposition_prompt()
        user_prompt = planner._build_user_decomposition_prompt(query)
        
        # Verify planning-specific content
        assert 'décomposition' in system_prompt.lower()
        assert 'tâches atomiques' in system_prompt.lower()
        assert query in user_prompt
        assert 'JSON' in user_prompt


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
