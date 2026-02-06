"""
Tests for Context Builder with Template Support

Tests the refactored ContextBuilder that uses Jinja2 templates.
"""

import pytest
from unittest.mock import Mock, MagicMock

from runtime.context_builder import ContextBuilder
from runtime.template_loader import get_template_loader


class TestContextBuilderWithTemplates:
    """Tests for ContextBuilder using templates"""

    def test_initialization_with_default_template_loader(self):
        """Test that ContextBuilder initializes with default template loader"""
        builder = ContextBuilder()

        assert builder.template_loader is not None
        assert builder.template_loader.version == "v1"

    def test_initialization_with_custom_template_version(self):
        """Test initialization with custom template version"""
        builder = ContextBuilder(template_version="v1")

        assert builder.template_loader.version == "v1"

    def test_build_system_prompt_uses_template(self):
        """Test that build_system_prompt uses template"""
        builder = ContextBuilder()

        # Mock tool registry
        mock_tool = Mock()
        mock_tool.get_schema.return_value = {
            "description": "Test tool",
            "parameters": {"param1": "value1"},
        }

        mock_registry = Mock()
        mock_registry.list_all.return_value = {"test_tool": mock_tool}

        # Build prompt
        result = builder.build_system_prompt(mock_registry)

        # Verify template was used (check for key content)
        assert "FilAgent" in result
        assert "PME québécoises" in result
        assert "test_tool" in result
        assert "Test tool" in result

    def test_build_system_prompt_with_semantic_context(self):
        """Test build_system_prompt includes semantic context"""
        builder = ContextBuilder()

        mock_registry = Mock()
        mock_registry.list_all.return_value = {}

        semantic_context = "[Contexte sémantique]\nInformation pertinente"

        result = builder.build_system_prompt(mock_registry, semantic_context=semantic_context)

        # Verify semantic context is included
        assert semantic_context in result or "Contexte sémantique" in result

    def test_build_system_prompt_fallback_on_template_error(self):
        """Test that fallback works if template loading fails"""
        # Create builder with invalid template loader
        builder = ContextBuilder()

        # Mock template loader to raise error
        mock_loader = Mock()
        mock_loader.render.side_effect = Exception("Template error")
        builder.template_loader = mock_loader

        mock_registry = Mock()
        mock_registry.list_all.return_value = {}

        # Should not raise, should use fallback
        result = builder.build_system_prompt(mock_registry)

        # Verify fallback was used
        assert "FilAgent" in result
        assert "PME québécoises" in result

    def test_fallback_system_prompt_structure(self):
        """Test that fallback prompt has correct structure"""
        builder = ContextBuilder()

        tools_section = "- tool1: Description 1"
        semantic_context = "Context info"

        result = builder._build_system_prompt_fallback(tools_section, semantic_context)

        assert "FilAgent" in result
        assert tools_section in result
        assert semantic_context in result

    def test_build_context_unchanged(self):
        """Test that build_context still works (not affected by templates)"""
        builder = ContextBuilder()

        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]

        result = builder.build_context(history, "conv-123")

        assert "Utilisateur: Hello" in result
        assert "Assistant: Hi there" in result

    def test_compose_prompt_unchanged(self):
        """Test that compose_prompt still works"""
        builder = ContextBuilder()

        context = "Previous conversation"
        message = "New message"

        result = builder.compose_prompt(context, message)

        assert context in result
        assert message in result
        assert "Assistant:" in result


class TestContextBuilderToolDescriptions:
    """Tests for tool description formatting in templates"""

    def test_multiple_tools_formatting(self):
        """Test that multiple tools are formatted correctly"""
        builder = ContextBuilder()

        # Create mock tools
        mock_tools = {}
        for i in range(3):
            mock_tool = Mock()
            mock_tool.get_schema.return_value = {
                "description": f"Tool {i} description",
                "parameters": {"param": f"value{i}"},
            }
            mock_tools[f"tool{i}"] = mock_tool

        mock_registry = Mock()
        mock_registry.list_all.return_value = mock_tools

        result = builder.build_system_prompt(mock_registry)

        # Verify all tools are present
        for i in range(3):
            assert f"tool{i}" in result
            assert f"Tool {i} description" in result

    def test_tool_parameters_json_formatting(self):
        """Test that tool parameters are JSON formatted"""
        builder = ContextBuilder()

        mock_tool = Mock()
        mock_tool.get_schema.return_value = {
            "description": "Test tool",
            "parameters": {"input": {"type": "string"}, "count": {"type": "integer"}},
        }

        mock_registry = Mock()
        mock_registry.list_all.return_value = {"test_tool": mock_tool}

        result = builder.build_system_prompt(mock_registry)

        # Verify parameters are in result
        assert "input" in result
        assert "count" in result


class TestContextBuilderBackwardCompatibility:
    """Tests to ensure backward compatibility"""

    def test_api_signature_unchanged(self):
        """Test that public API signatures are unchanged"""
        builder = ContextBuilder()

        # Test that all original methods exist and work
        assert hasattr(builder, "build_context")
        assert hasattr(builder, "compose_prompt")
        assert hasattr(builder, "compute_prompt_hash")
        assert hasattr(builder, "inject_semantic_context")
        assert hasattr(builder, "build_system_prompt")

    def test_initialization_without_template_args(self):
        """Test that old initialization still works"""
        # Should work without template-related args
        builder = ContextBuilder(max_history_messages=5, role_labels={"user": "User"})

        assert builder.max_history_messages == 5
        assert builder.role_labels["user"] == "User"
        assert builder.template_loader is not None

    def test_build_system_prompt_minimal_args(self):
        """Test build_system_prompt with minimal arguments"""
        builder = ContextBuilder()

        mock_registry = Mock()
        mock_registry.list_all.return_value = {}

        # Should work with just tool_registry
        result = builder.build_system_prompt(mock_registry)

        assert isinstance(result, str)
        assert len(result) > 0


class TestContextBuilderEdgeCases:
    """Tests for edge cases and error conditions"""

    def test_empty_tool_registry(self):
        """Test with empty tool registry"""
        builder = ContextBuilder()

        mock_registry = Mock()
        mock_registry.list_all.return_value = {}

        result = builder.build_system_prompt(mock_registry)

        # Should still produce valid prompt
        assert "FilAgent" in result
        assert len(result) > 100

    def test_none_semantic_context(self):
        """Test with None semantic context"""
        builder = ContextBuilder()

        mock_registry = Mock()
        mock_registry.list_all.return_value = {}

        result = builder.build_system_prompt(mock_registry, semantic_context=None)

        assert isinstance(result, str)

    def test_empty_semantic_context(self):
        """Test with empty string semantic context"""
        builder = ContextBuilder()

        mock_registry = Mock()
        mock_registry.list_all.return_value = {}

        result = builder.build_system_prompt(mock_registry, semantic_context="")

        assert isinstance(result, str)


@pytest.mark.integration
class TestContextBuilderIntegration:
    """Integration tests with real template loader"""

    def test_full_system_prompt_generation(self):
        """Test full system prompt generation flow"""
        builder = ContextBuilder()

        # Create realistic mock registry
        mock_tool1 = Mock()
        mock_tool1.get_schema.return_value = {
            "description": "Calculates mathematical expressions",
            "parameters": {"expression": "string"},
        }

        mock_tool2 = Mock()
        mock_tool2.get_schema.return_value = {
            "description": "Searches the web for information",
            "parameters": {"query": "string", "limit": "integer"},
        }

        mock_registry = Mock()
        mock_registry.list_all.return_value = {
            "calculator": mock_tool1,
            "web_search": mock_tool2,
        }

        semantic_context = "[Contexte sémantique]\nDocument sur les PME du Québec"

        result = builder.build_system_prompt(mock_registry, semantic_context=semantic_context)

        # Verify complete prompt structure
        assert "FilAgent" in result
        assert "calculator" in result
        assert "web_search" in result
        assert "Calculates mathematical expressions" in result
        assert "Contexte sémantique" in result or semantic_context in result
        assert "<tool_call>" in result
        assert "Loi 25" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
