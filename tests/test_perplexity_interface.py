"""
Tests for Perplexity API interface

Tests include:
- Factory creation
- Mock client initialization
- Generation with mock
- Error handling
"""

import sys
import pytest
from unittest.mock import Mock, patch, MagicMock
from runtime.model_interface import (
    PerplexityInterface,
    ModelFactory,
    GenerationConfig,
    GenerationResult,
)


class TestPerplexityInterfaceFactory:
    """Test model factory with Perplexity backend"""

    def test_factory_creates_perplexity_interface(self):
        """Test that factory creates PerplexityInterface"""
        model = ModelFactory.create("perplexity")
        assert isinstance(model, PerplexityInterface)
        assert not model.is_loaded()

    def test_factory_rejects_unknown_backend(self):
        """Test that factory rejects unknown backends"""
        with pytest.raises(ValueError) as exc_info:
            ModelFactory.create("unknown_backend")
        assert "Unknown backend" in str(exc_info.value)
        assert "llama.cpp, perplexity, vllm" in str(exc_info.value)


class TestPerplexityInterfaceLoad:
    """Test Perplexity client initialization"""

    @pytest.fixture(autouse=True)
    def mock_openai_module(self):
        """Mock the openai module if not installed"""
        try:
            import openai  # noqa: F401
        except ImportError:
            # Mock openai module globally for these tests
            sys.modules["openai"] = Mock()

    @patch.dict("os.environ", {"PERPLEXITY_API_KEY": "test-key"})
    @patch("openai.OpenAI")
    def test_load_with_env_var(self, mock_openai_class):
        """Test loading with API key from environment variable"""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        interface = PerplexityInterface()
        success = interface.load(model_path="llama-3.1-sonar-large-128k-online", config={})

        assert success
        assert interface.is_loaded()
        assert interface.model_name == "llama-3.1-sonar-large-128k-online"
        mock_openai_class.assert_called_once_with(
            api_key="test-key", base_url="https://api.perplexity.ai"
        )

    @patch("openai.OpenAI")
    def test_load_with_config_api_key(self, mock_openai_class):
        """Test loading with API key from config"""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        interface = PerplexityInterface()
        success = interface.load(
            model_path="llama-3.1-8b-instruct", config={"api_key": "config-key"}
        )

        assert success
        assert interface.is_loaded()
        mock_openai_class.assert_called_once_with(
            api_key="config-key", base_url="https://api.perplexity.ai"
        )

    @patch.dict("os.environ", {}, clear=True)
    def test_load_fails_without_api_key(self):
        """Test that load fails when no API key is provided"""
        interface = PerplexityInterface()
        success = interface.load(model_path="llama-3.1-sonar-large-128k-online", config={})

        assert not success
        assert not interface.is_loaded()

    @patch.dict("os.environ", {"PERPLEXITY_API_KEY": "test-key"})
    def test_load_fails_without_openai_package(self):
        """Test that load fails gracefully when openai package is not installed"""
        with patch("openai.OpenAI", side_effect=ImportError):
            interface = PerplexityInterface()
            success = interface.load(model_path="llama-3.1-sonar-large-128k-online", config={})

            assert not success
            assert not interface.is_loaded()


class TestPerplexityInterfaceGenerate:
    """Test text generation with Perplexity"""

    def setup_method(self):
        """Set up mock client for generation tests"""
        self.interface = PerplexityInterface()
        self.interface._loaded = True
        self.interface.model_name = "llama-3.1-sonar-large-128k-online"

        # Create mock client
        self.mock_client = Mock()
        self.interface.client = self.mock_client

    def test_generate_simple_prompt(self):
        """Test basic text generation"""
        # Mock response
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content="This is a test response"), finish_reason="stop")
        ]
        mock_response.usage = Mock(prompt_tokens=10, completion_tokens=5, total_tokens=15)

        self.mock_client.chat.completions.create.return_value = mock_response

        config = GenerationConfig(temperature=0.2, max_tokens=100)
        result = self.interface.generate("Test prompt", config)

        assert isinstance(result, GenerationResult)
        assert result.text == "This is a test response"
        assert result.finish_reason == "stop"
        assert result.prompt_tokens == 10
        assert result.tokens_generated == 5
        assert result.total_tokens == 15

    def test_generate_with_system_prompt(self):
        """Test generation with system prompt"""
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content="Expert response"), finish_reason="stop")
        ]
        mock_response.usage = Mock(prompt_tokens=20, completion_tokens=10, total_tokens=30)

        self.mock_client.chat.completions.create.return_value = mock_response

        config = GenerationConfig()
        result = self.interface.generate(
            prompt="User question", config=config, system_prompt="You are an expert"
        )

        # Verify that both system and user messages were sent
        call_args = self.mock_client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are an expert"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "User question"

    def test_generate_fails_when_not_loaded(self):
        """Test that generate raises error when client not loaded"""
        interface = PerplexityInterface()  # Not loaded

        with pytest.raises(RuntimeError) as exc_info:
            interface.generate("Test", GenerationConfig())

        assert "not loaded" in str(exc_info.value)

    def test_generate_handles_api_error(self):
        """Test that generation handles API errors gracefully"""
        self.mock_client.chat.completions.create.side_effect = Exception("API Error")

        config = GenerationConfig()
        result = self.interface.generate("Test prompt", config)

        assert isinstance(result, GenerationResult)
        assert "[Error]" in result.text
        assert "API Error" in result.text
        assert result.finish_reason == "error"
        assert result.tokens_generated == 0


class TestPerplexityInterfaceLifecycle:
    """Test interface lifecycle (load/unload)"""

    @pytest.fixture(autouse=True)
    def mock_openai_module(self):
        """Mock the openai module if not installed"""
        try:
            import openai  # noqa: F401
        except ImportError:
            # Mock openai module globally for these tests
            sys.modules["openai"] = Mock()

    @patch.dict("os.environ", {"PERPLEXITY_API_KEY": "test-key"})
    @patch("openai.OpenAI")
    def test_unload(self, mock_openai_class):
        """Test unloading client"""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        interface = PerplexityInterface()
        interface.load("llama-3.1-8b-instruct", {})

        assert interface.is_loaded()

        interface.unload()

        assert not interface.is_loaded()
        assert interface.client is None
        assert interface.model_name is None


@pytest.mark.integration
class TestPerplexityIntegration:
    """Integration tests (require real API key)"""

    def test_real_api_call(self):
        """
        Test real API call to Perplexity

        This test is skipped by default. To run:
        1. Set PERPLEXITY_API_KEY environment variable
        2. Install ML dependencies: pdm install --with ml
        3. Run: pytest tests/test_perplexity_interface.py -v -m integration
        """
        import os

        api_key = os.getenv("PERPLEXITY_API_KEY")
        if not api_key:
            pytest.skip("PERPLEXITY_API_KEY not set")

        try:
            from openai import OpenAI
        except ImportError:
            pytest.skip("openai package not installed")

        interface = PerplexityInterface()
        success = interface.load(
            model_path="llama-3.1-sonar-small-128k-online", config={"api_key": api_key}
        )

        assert success

        config = GenerationConfig(temperature=0.1, max_tokens=50)
        result = interface.generate(
            prompt="What is 2+2?", config=config, system_prompt="You are a helpful math tutor."
        )

        assert result.finish_reason in ["stop", "length"]
        assert len(result.text) > 0
        assert result.tokens_generated > 0

        interface.unload()
