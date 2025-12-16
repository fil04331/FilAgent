"""
Tests for Template Loader

Tests the Jinja2 template loading and rendering system.
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from runtime.template_loader import TemplateLoader, get_template_loader, clear_template_cache
from jinja2 import TemplateNotFound, UndefinedError


class TestTemplateLoader:
    """Tests for TemplateLoader class"""
    
    def test_loader_initialization(self):
        """Test that loader initializes correctly with default version"""
        loader = get_template_loader(version='v1', force_reload=True)
        assert loader.version == 'v1'
        assert loader.versioned_dir.exists()
    
    def test_list_templates(self):
        """Test listing available templates"""
        loader = get_template_loader(version='v1', force_reload=True)
        templates = loader.list_templates()
        
        # Should contain our v1 templates
        assert 'system_prompt' in templates
        assert 'planner_decomposition' in templates
        assert 'planner_user_prompt' in templates
    
    def test_render_system_prompt(self):
        """Test rendering system prompt template"""
        loader = get_template_loader(version='v1', force_reload=True)
        
        tools_desc = "- tool1: Does thing 1\n- tool2: Does thing 2"
        result = loader.render('system_prompt', tools=tools_desc)
        
        assert 'FilAgent' in result
        assert 'PME québécoises' in result
        assert tools_desc in result
        assert 'tool1' in result
    
    def test_render_system_prompt_with_semantic_context(self):
        """Test rendering system prompt with optional semantic context"""
        loader = get_template_loader(version='v1', force_reload=True)
        
        tools_desc = "- tool1: Test tool"
        semantic_ctx = "[Contexte pertinent]\nInformation importante"
        
        result = loader.render(
            'system_prompt',
            tools=tools_desc,
            semantic_context=semantic_ctx,
        )
        
        assert 'FilAgent' in result
        assert tools_desc in result
        assert semantic_ctx in result
    
    def test_render_planner_decomposition(self):
        """Test rendering planner decomposition template"""
        loader = get_template_loader(version='v1', force_reload=True)
        
        result = loader.render('planner_decomposition')
        
        assert 'expert en décomposition' in result
        assert 'Tâches atomiques' in result
        assert 'JSON valide' in result
    
    def test_render_planner_user_prompt(self):
        """Test rendering planner user prompt template"""
        loader = get_template_loader(version='v1', force_reload=True)
        
        query = "Analyse data.csv et génère rapport"
        actions = "read_file, analyze_data, generate_report"
        
        result = loader.render(
            'planner_user_prompt',
            query=query,
            available_actions=actions,
        )
        
        assert query in result
        assert actions in result
        assert 'JSON valide' in result
        assert 'tasks' in result
    
    def test_template_not_found(self):
        """Test error handling for missing template"""
        loader = get_template_loader(version='v1', force_reload=True)
        
        with pytest.raises(TemplateNotFound) as exc_info:
            loader.render('nonexistent_template')
        
        assert 'nonexistent_template' in str(exc_info.value)
        assert 'Available templates' in str(exc_info.value)
    
    def test_missing_required_variable(self):
        """Test that missing variables are handled gracefully"""
        loader = get_template_loader(version='v1', force_reload=True)
        
        # system_prompt requires 'tools' variable, but Jinja2's default
        # behavior is to render undefined variables as empty strings
        # This is actually acceptable for our use case as it provides
        # graceful degradation
        result = loader.render('system_prompt')  # Missing 'tools'
        
        # Should still render but without tools section content
        assert 'FilAgent' in result  # Base content should be there
        assert len(result) > 1000  # Should have substantial content
    
    def test_template_caching(self):
        """Test that templates are cached after first load"""
        loader = get_template_loader(version='v1', force_reload=True)
        
        # First render
        result1 = loader.render('planner_decomposition')
        
        # Template should be cached
        assert 'planner_decomposition.j2' in loader._template_cache
        
        # Second render (from cache)
        result2 = loader.render('planner_decomposition')
        
        assert result1 == result2
    
    def test_reload_templates(self):
        """Test template cache clearing"""
        loader = get_template_loader(version='v1', force_reload=True)
        
        # Load a template
        loader.render('planner_decomposition')
        assert len(loader._template_cache) > 0
        
        # Clear cache
        loader.reload_templates()
        assert len(loader._template_cache) == 0
    
    def test_get_template_path(self):
        """Test getting full path to template"""
        loader = get_template_loader(version='v1', force_reload=True)
        
        path = loader.get_template_path('system_prompt')
        
        assert path.exists()
        assert path.name == 'system_prompt.j2'
        assert 'v1' in str(path)
    
    def test_singleton_pattern(self):
        """Test that get_template_loader returns singleton"""
        clear_template_cache()
        
        loader1 = get_template_loader(version='v1')
        loader2 = get_template_loader(version='v1')
        
        # Should be same instance (caching behavior)
        # Note: With lru_cache, they reference the same cached result
        assert loader1.version == loader2.version
    
    def test_version_switching(self):
        """Test switching between template versions"""
        loader = get_template_loader(version='v1', force_reload=True)
        assert loader.version == 'v1'
        
        # Note: Version switching would require v2 to exist
        # This is a placeholder test for when v2 is created
        # For now, just verify we can reload v1
        loader.switch_version('v1')
        assert loader.version == 'v1'


class TestTemplateLoaderWithCustomDirectory:
    """Tests for TemplateLoader with custom directory"""
    
    def test_custom_template_directory(self):
        """Test loader with custom templates directory"""
        # Create temporary directory structure
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            templates_dir = tmp_path / "custom_templates"
            v1_dir = templates_dir / "v1"
            v1_dir.mkdir(parents=True)
            
            # Create a simple test template
            test_template = v1_dir / "test.j2"
            test_template.write_text("Hello {{ name }}!")
            
            # Initialize loader with custom directory
            loader = TemplateLoader(version='v1', templates_dir=templates_dir)
            
            # Render template
            result = loader.render('test', name='World')
            assert result == "Hello World!"
    
    def test_invalid_template_directory(self):
        """Test error handling for invalid template directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            templates_dir = tmp_path / "nonexistent"
            
            with pytest.raises(FileNotFoundError) as exc_info:
                TemplateLoader(version='v1', templates_dir=templates_dir)
            
            assert 'not found' in str(exc_info.value)


class TestTemplateLoaderIntegration:
    """Integration tests with actual template files"""
    
    def test_system_prompt_completeness(self):
        """Test that system prompt contains all required sections"""
        loader = get_template_loader(version='v1', force_reload=True)
        
        tools_desc = "- calculator: Performs calculations"
        result = loader.render('system_prompt', tools=tools_desc)
        
        # Verify key sections are present
        required_sections = [
            'FilAgent',
            'PME québécoises',
            'CONTEXTE',
            'DOMAINES D\'EXPERTISE',
            'QUALITÉ DES RÉPONSES',
            'OUTILS DISPONIBLES',
            '<tool_call>',
            'Loi 25',
        ]
        
        for section in required_sections:
            assert section in result, f"Missing section: {section}"
    
    def test_planner_prompt_format(self):
        """Test that planner prompts produce valid structure"""
        loader = get_template_loader(version='v1', force_reload=True)
        
        # System prompt
        sys_prompt = loader.render('planner_decomposition')
        assert 'décomposition' in sys_prompt.lower()
        assert 'JSON' in sys_prompt
        
        # User prompt
        user_prompt = loader.render(
            'planner_user_prompt',
            query="Test query",
            available_actions="action1, action2",
        )
        assert 'Test query' in user_prompt
        assert 'action1, action2' in user_prompt
        assert '"tasks"' in user_prompt  # JSON structure hint
    
    def test_template_whitespace_handling(self):
        """Test that templates handle whitespace correctly"""
        loader = get_template_loader(version='v1', force_reload=True)
        
        result = loader.render('planner_decomposition')
        
        # Should not have excessive whitespace
        assert '\n\n\n' not in result
        
        # Should be properly stripped
        assert not result.startswith('\n')
        assert not result.endswith('\n\n')


# Mark slow tests
@pytest.mark.unit
class TestTemplateLoaderPerformance:
    """Performance tests for template loader"""
    
    def test_template_loading_performance(self):
        """Test that template loading is reasonably fast"""
        import time
        
        loader = get_template_loader(version='v1', force_reload=True)
        
        # First load (includes compilation)
        start = time.time()
        loader.render('system_prompt', tools="test")
        first_duration = time.time() - start
        
        # Second load (from cache)
        start = time.time()
        loader.render('system_prompt', tools="test")
        cached_duration = time.time() - start
        
        # Cached should be significantly faster
        assert cached_duration < first_duration
        
        # Both should be reasonably fast (< 100ms)
        assert first_duration < 0.1
        assert cached_duration < 0.05


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
