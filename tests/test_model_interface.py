"""
Tests for runtime/model_interface.py

Tests cover:
- GenerationConfig and GenerationResult dataclasses
- LlamaCppInterface (load, generate, unload, is_loaded)
- ModelFactory (backend creation)
- Global singleton functions (init_model, get_model)
- Generation with various configs
- Error handling and fallback mechanisms
- Token counting
- Timeout handling
"""

import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock
from typing import Dict, Any

from runtime.model_interface import (
    GenerationConfig,
    GenerationResult,
    ModelInterface,
    LlamaCppInterface,
    ModelFactory,
    init_model,
    get_model,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_model_path(tmp_path):
    """Create a temporary model file path"""
    model_path = tmp_path / "test_model.gguf"
    model_path.write_text("dummy model content")
    return model_path


@pytest.fixture
def mock_llama_class():
    """Mock the Llama class from llama_cpp"""
    class MockLlama:
        def __init__(self, model_path, n_ctx, n_gpu_layers, use_mmap, use_mlock, verbose):
            self.model_path = model_path
            self.n_ctx = n_ctx
            self.n_gpu_layers = n_gpu_layers

        def __call__(self, prompt, **kwargs):
            """Simulate model generation"""
            return {
                "choices": [{
                    "text": "This is a test response.",
                    "finish_reason": "stop"
                }],
                "usage": {
                    "completion_tokens": 5,
                    "total_tokens": 15
                }
            }

    return MockLlama


@pytest.fixture
def model_config() -> Dict[str, Any]:
    """Standard model configuration for tests"""
    return {
        "context_size": 4096,
        "n_gpu_layers": 35
    }


@pytest.fixture
def generation_config() -> GenerationConfig:
    """Standard generation configuration for tests"""
    return GenerationConfig(
        temperature=0.2,
        top_p=0.95,
        max_tokens=800,
        seed=42,
        top_k=40,
        repetition_penalty=1.1
    )


@pytest.fixture(autouse=True)
def reset_model_singleton():
    """Reset the global model singleton before each test"""
    import runtime.model_interface as mi
    mi._model_instance = None
    yield
    mi._model_instance = None


# ============================================================================
# TESTS: GenerationConfig
# ============================================================================

class TestGenerationConfig:
    """Tests for GenerationConfig dataclass"""

    def test_default_values(self):
        """Test that GenerationConfig has correct default values"""
        config = GenerationConfig()

        assert config.temperature == 0.2
        assert config.top_p == 0.95
        assert config.max_tokens == 800
        assert config.seed == 42
        assert config.top_k == 40
        assert config.repetition_penalty == 1.1

    def test_custom_values(self):
        """Test creating GenerationConfig with custom values"""
        config = GenerationConfig(
            temperature=0.8,
            top_p=0.9,
            max_tokens=1000,
            seed=123,
            top_k=50,
            repetition_penalty=1.2
        )

        assert config.temperature == 0.8
        assert config.top_p == 0.9
        assert config.max_tokens == 1000
        assert config.seed == 123
        assert config.top_k == 50
        assert config.repetition_penalty == 1.2

    def test_partial_custom_values(self):
        """Test creating GenerationConfig with some custom values"""
        config = GenerationConfig(temperature=0.5, max_tokens=500)

        assert config.temperature == 0.5
        assert config.max_tokens == 500
        # Defaults should still apply
        assert config.top_p == 0.95
        assert config.seed == 42


# ============================================================================
# TESTS: GenerationResult
# ============================================================================

class TestGenerationResult:
    """Tests for GenerationResult dataclass"""

    def test_basic_result(self):
        """Test creating a basic GenerationResult"""
        result = GenerationResult(
            text="Test response",
            finish_reason="stop",
            tokens_generated=10,
            prompt_tokens=5,
            total_tokens=15
        )

        assert result.text == "Test response"
        assert result.finish_reason == "stop"
        assert result.tokens_generated == 10
        assert result.prompt_tokens == 5
        assert result.total_tokens == 15
        assert result.tool_calls is None

    def test_result_with_tool_calls(self):
        """Test GenerationResult with tool calls"""
        tool_calls = [
            {"name": "calculator", "arguments": {"expression": "2+2"}},
            {"name": "search", "arguments": {"query": "test"}}
        ]

        result = GenerationResult(
            text="Let me use some tools",
            finish_reason="tool_calls",
            tokens_generated=10,
            prompt_tokens=5,
            total_tokens=15,
            tool_calls=tool_calls
        )

        assert result.tool_calls == tool_calls
        assert result.finish_reason == "tool_calls"
        assert len(result.tool_calls) == 2

    def test_finish_reasons(self):
        """Test different finish reasons"""
        for reason in ["stop", "length", "tool_calls"]:
            result = GenerationResult(
                text="Test",
                finish_reason=reason,
                tokens_generated=5,
                prompt_tokens=5,
                total_tokens=10
            )
            assert result.finish_reason == reason


# ============================================================================
# TESTS: LlamaCppInterface - Initialization and Loading
# ============================================================================

class TestLlamaCppInterface:
    """Tests for LlamaCppInterface class"""

    def test_initialization(self):
        """Test that LlamaCppInterface initializes correctly"""
        interface = LlamaCppInterface()

        assert interface.model is None
        assert interface._loaded is False
        assert interface.is_loaded() is False

    def test_load_success_with_mock(self, temp_model_path, model_config, mock_llama_class):
        """Test successful model loading with mock"""
        interface = LlamaCppInterface()

        with patch('llama_cpp.Llama', mock_llama_class):
            success = interface.load(str(temp_model_path), model_config)

            assert success is True
            assert interface.is_loaded() is True
            assert interface.model is not None

    def test_load_file_not_found(self, tmp_path, model_config):
        """Test loading when model file doesn't exist (should fallback to mock)"""
        interface = LlamaCppInterface()
        non_existent = str(tmp_path / "non_existent.gguf")

        # Should create fallback mock model
        success = interface.load(non_existent, model_config)

        assert success is True  # Fallback succeeds
        assert interface.is_loaded() is True
        assert interface.model is not None

    def test_load_with_fallback_path(self, tmp_path, model_config):
        """Test loading with fallback to default model path"""
        interface = LlamaCppInterface()
        non_existent = str(tmp_path / "non_existent.gguf")

        # Create fallback model
        fallback_path = Path("models/weights/base.gguf")
        fallback_path.parent.mkdir(parents=True, exist_ok=True)
        fallback_path.write_text("fallback model")

        try:
            with patch('llama_cpp.Llama') as mock_llama:
                mock_llama.return_value = MagicMock()
                success = interface.load(non_existent, model_config)

                assert success is True
                assert interface.is_loaded() is True
        finally:
            # Cleanup
            if fallback_path.exists():
                fallback_path.unlink()

    def test_load_import_error_fallback(self, temp_model_path, model_config):
        """Test fallback to mock when llama_cpp is not available"""
        interface = LlamaCppInterface()

        # Simulate ImportError
        with patch('builtins.__import__', side_effect=ImportError("llama_cpp not found")):
            success = interface.load(str(temp_model_path), model_config)

            assert success is True  # Fallback to mock
            assert interface.is_loaded() is True
            assert interface.model is not None

    def test_load_with_custom_config(self, temp_model_path, mock_llama_class):
        """Test loading with custom configuration parameters"""
        interface = LlamaCppInterface()
        custom_config = {
            "context_size": 8192,
            "n_gpu_layers": 50
        }

        with patch('llama_cpp.Llama', mock_llama_class) as mock_llama:
            success = interface.load(str(temp_model_path), custom_config)

            assert success is True
            # Verify custom config was used
            call_args = mock_llama.call_args
            assert call_args is not None

    def test_unload(self, temp_model_path, model_config, mock_llama_class):
        """Test unloading a loaded model"""
        interface = LlamaCppInterface()

        with patch('llama_cpp.Llama', mock_llama_class):
            interface.load(str(temp_model_path), model_config)
            assert interface.is_loaded() is True

            interface.unload()

            assert interface.is_loaded() is False
            assert interface.model is None

    def test_unload_when_not_loaded(self):
        """Test unloading when no model is loaded"""
        interface = LlamaCppInterface()

        # Should not raise an error
        interface.unload()

        assert interface.is_loaded() is False


# ============================================================================
# TESTS: LlamaCppInterface - Generation
# ============================================================================

class TestLlamaCppGeneration:
    """Tests for text generation with LlamaCppInterface"""

    def test_generate_basic(self, temp_model_path, model_config, generation_config, mock_llama_class):
        """Test basic text generation"""
        interface = LlamaCppInterface()

        with patch('llama_cpp.Llama', mock_llama_class):
            interface.load(str(temp_model_path), model_config)

            result = interface.generate("Hello, how are you?", generation_config)

            assert isinstance(result, GenerationResult)
            assert isinstance(result.text, str)
            assert len(result.text) > 0
            assert result.finish_reason == "stop"
            assert result.tokens_generated > 0
            assert result.prompt_tokens > 0
            assert result.total_tokens > 0

    def test_generate_with_system_prompt(self, temp_model_path, model_config, generation_config, mock_llama_class):
        """Test generation with system prompt"""
        interface = LlamaCppInterface()

        with patch('llama_cpp.Llama', mock_llama_class):
            interface.load(str(temp_model_path), model_config)

            result = interface.generate(
                "What is 2+2?",
                generation_config,
                system_prompt="You are a helpful math assistant."
            )

            assert isinstance(result, GenerationResult)
            assert len(result.text) > 0

    def test_generate_without_loading_model(self, generation_config):
        """Test that generation fails when model is not loaded"""
        interface = LlamaCppInterface()

        with pytest.raises(RuntimeError, match="Model not loaded"):
            interface.generate("Test prompt", generation_config)

    def test_generate_with_different_configs(self, temp_model_path, model_config, mock_llama_class):
        """Test generation with various configuration parameters"""
        interface = LlamaCppInterface()

        configs = [
            GenerationConfig(temperature=0.1, max_tokens=100),
            GenerationConfig(temperature=0.9, max_tokens=500),
            GenerationConfig(temperature=0.5, top_p=0.8, top_k=50),
        ]

        with patch('llama_cpp.Llama', mock_llama_class):
            interface.load(str(temp_model_path), model_config)

            for config in configs:
                result = interface.generate("Test prompt", config)
                assert isinstance(result, GenerationResult)
                assert len(result.text) > 0

    def test_generate_token_counting(self, temp_model_path, model_config, generation_config):
        """Test that token counting is accurate"""
        interface = LlamaCppInterface()

        # Create mock that returns specific token counts
        mock_llama_instance = MagicMock()
        mock_llama_instance.return_value = {
            "choices": [{
                "text": "This is a response with ten words in it.",
                "finish_reason": "stop"
            }],
            "usage": {
                "completion_tokens": 10,
                "total_tokens": 20
            }
        }

        with patch('llama_cpp.Llama', return_value=mock_llama_instance):
            interface.load(str(temp_model_path), model_config)

            result = interface.generate("Count tokens", generation_config)

            assert result.tokens_generated == 10
            assert result.total_tokens == 20
            assert result.prompt_tokens > 0

    def test_generate_error_handling(self, temp_model_path, model_config, generation_config):
        """Test error handling during generation"""
        interface = LlamaCppInterface()

        # Create mock that raises an exception
        mock_llama_instance = MagicMock()
        mock_llama_instance.side_effect = Exception("Generation failed")

        with patch('llama_cpp.Llama', return_value=mock_llama_instance):
            interface.load(str(temp_model_path), model_config)

            result = interface.generate("Test prompt", generation_config)

            # Should return error result, not raise
            assert isinstance(result, GenerationResult)
            assert result.finish_reason == "error"
            assert "[Error]" in result.text
            assert result.tokens_generated == 0

    def test_generate_finish_reason_length(self, temp_model_path, model_config, generation_config):
        """Test generation that finishes due to length limit"""
        interface = LlamaCppInterface()

        mock_llama_instance = MagicMock()
        mock_llama_instance.return_value = {
            "choices": [{
                "text": "Response that hit max tokens",
                "finish_reason": "length"
            }],
            "usage": {
                "completion_tokens": 800,
                "total_tokens": 850
            }
        }

        with patch('llama_cpp.Llama', return_value=mock_llama_instance):
            interface.load(str(temp_model_path), model_config)

            result = interface.generate("Long prompt", generation_config)

            assert result.finish_reason == "length"

    def test_generate_strips_whitespace(self, temp_model_path, model_config, generation_config):
        """Test that generated text is stripped of leading/trailing whitespace"""
        interface = LlamaCppInterface()

        mock_llama_instance = MagicMock()
        mock_llama_instance.return_value = {
            "choices": [{
                "text": "  \n  Response with whitespace  \n  ",
                "finish_reason": "stop"
            }],
            "usage": {
                "completion_tokens": 5,
                "total_tokens": 15
            }
        }

        with patch('llama_cpp.Llama', return_value=mock_llama_instance):
            interface.load(str(temp_model_path), model_config)

            result = interface.generate("Test", generation_config)

            assert result.text == "Response with whitespace"


# ============================================================================
# TESTS: Mock Model (Fallback)
# ============================================================================

class TestMockModel:
    """Tests for the mock model fallback mechanism"""

    def test_mock_model_creation(self):
        """Test that mock model is created correctly"""
        interface = LlamaCppInterface()
        interface._create_mock_model()

        assert interface.model is not None
        assert interface.is_loaded() is True

    def test_mock_model_generation(self, generation_config):
        """Test that mock model can generate responses"""
        interface = LlamaCppInterface()
        interface._create_mock_model()

        result = interface.generate("Test prompt", generation_config)

        assert isinstance(result, GenerationResult)
        assert "[Mock Response]" in result.text
        assert result.finish_reason == "stop"
        assert result.tokens_generated > 0

    def test_mock_model_is_consistent(self, generation_config):
        """Test that mock model returns consistent responses"""
        interface = LlamaCppInterface()
        interface._create_mock_model()

        result1 = interface.generate("Prompt 1", generation_config)
        result2 = interface.generate("Prompt 2", generation_config)

        # Mock should return same text for any prompt
        assert result1.text == result2.text


# ============================================================================
# TESTS: ModelFactory
# ============================================================================

class TestModelFactory:
    """Tests for ModelFactory class"""

    def test_create_llama_cpp_backend(self):
        """Test creating llama.cpp backend"""
        model = ModelFactory.create("llama.cpp")

        assert isinstance(model, LlamaCppInterface)
        assert isinstance(model, ModelInterface)

    def test_create_vllm_backend_not_implemented(self):
        """Test that vLLM backend raises NotImplementedError"""
        with pytest.raises(NotImplementedError, match="vLLM backend not yet implemented"):
            ModelFactory.create("vllm")

    def test_create_unknown_backend(self):
        """Test that unknown backend raises ValueError"""
        with pytest.raises(ValueError, match="Unknown backend"):
            ModelFactory.create("unknown_backend")

    def test_create_returns_model_interface(self):
        """Test that factory returns correct interface type"""
        model = ModelFactory.create("llama.cpp")

        # Should have all required methods
        assert hasattr(model, 'load')
        assert hasattr(model, 'generate')
        assert hasattr(model, 'unload')
        assert hasattr(model, 'is_loaded')


# ============================================================================
# TESTS: Global Singleton Functions
# ============================================================================

class TestGlobalSingleton:
    """Tests for global model singleton functions"""

    def test_get_model_before_init_raises_error(self):
        """Test that get_model raises error before initialization"""
        with pytest.raises(RuntimeError, match="Model not initialized"):
            get_model()

    def test_init_model_creates_singleton(self, temp_model_path, model_config):
        """Test that init_model creates the global singleton"""
        with patch('llama_cpp.Llama', return_value=MagicMock()):
            model = init_model("llama.cpp", str(temp_model_path), model_config)

            assert model is not None
            assert isinstance(model, ModelInterface)

    def test_get_model_after_init_returns_same_instance(self, temp_model_path, model_config):
        """Test that get_model returns the same instance after init"""
        with patch('llama_cpp.Llama', return_value=MagicMock()):
            model1 = init_model("llama.cpp", str(temp_model_path), model_config)
            model2 = get_model()

            assert model1 is model2

    def test_init_model_multiple_times_replaces_instance(self, temp_model_path, model_config):
        """Test that calling init_model multiple times replaces the singleton"""
        with patch('llama_cpp.Llama', return_value=MagicMock()):
            model1 = init_model("llama.cpp", str(temp_model_path), model_config)
            model2 = init_model("llama.cpp", str(temp_model_path), model_config)

            # Should be different instances
            assert model1 is not model2

            # get_model should return the latest
            model3 = get_model()
            assert model3 is model2

    def test_init_model_with_invalid_path_uses_fallback(self, tmp_path, model_config):
        """Test that init_model uses fallback when path is invalid"""
        non_existent = str(tmp_path / "non_existent.gguf")

        # Should succeed with fallback mock
        model = init_model("llama.cpp", non_existent, model_config)

        assert model is not None
        assert model.is_loaded() is True


# ============================================================================
# TESTS: Advanced Scenarios
# ============================================================================

class TestAdvancedScenarios:
    """Tests for advanced usage scenarios"""

    def test_multiple_generations_same_model(self, temp_model_path, model_config, generation_config):
        """Test multiple generations using the same model instance"""
        interface = LlamaCppInterface()

        with patch('llama_cpp.Llama', return_value=MagicMock(return_value={
            "choices": [{"text": "Response", "finish_reason": "stop"}],
            "usage": {"completion_tokens": 5, "total_tokens": 15}
        })):
            interface.load(str(temp_model_path), model_config)

            results = []
            for i in range(5):
                result = interface.generate(f"Prompt {i}", generation_config)
                results.append(result)

            assert len(results) == 5
            assert all(isinstance(r, GenerationResult) for r in results)

    def test_load_unload_reload_cycle(self, temp_model_path, model_config):
        """Test loading, unloading, and reloading a model"""
        interface = LlamaCppInterface()

        with patch('llama_cpp.Llama', return_value=MagicMock()):
            # Load
            success1 = interface.load(str(temp_model_path), model_config)
            assert success1 is True
            assert interface.is_loaded() is True

            # Unload
            interface.unload()
            assert interface.is_loaded() is False

            # Reload
            success2 = interface.load(str(temp_model_path), model_config)
            assert success2 is True
            assert interface.is_loaded() is True

    def test_generation_with_varying_prompt_lengths(self, temp_model_path, model_config, generation_config):
        """Test generation with prompts of different lengths"""
        interface = LlamaCppInterface()

        prompts = [
            "Short",
            "This is a medium length prompt with more words.",
            "This is a very long prompt " * 50  # Very long prompt
        ]

        with patch('llama_cpp.Llama', return_value=MagicMock(return_value={
            "choices": [{"text": "Response", "finish_reason": "stop"}],
            "usage": {"completion_tokens": 5, "total_tokens": 15}
        })):
            interface.load(str(temp_model_path), model_config)

            for prompt in prompts:
                result = interface.generate(prompt, generation_config)
                assert isinstance(result, GenerationResult)
                # Longer prompts should estimate more prompt tokens
                if len(prompt) > 100:
                    assert result.prompt_tokens > 10

    def test_concurrent_safety_same_instance(self, temp_model_path, model_config, generation_config):
        """Test that the same model instance can handle sequential calls"""
        interface = LlamaCppInterface()

        with patch('llama_cpp.Llama', return_value=MagicMock(return_value={
            "choices": [{"text": "Response", "finish_reason": "stop"}],
            "usage": {"completion_tokens": 5, "total_tokens": 15}
        })):
            interface.load(str(temp_model_path), model_config)

            # Simulate rapid sequential calls
            results = []
            for i in range(10):
                result = interface.generate(f"Prompt {i}", generation_config)
                results.append(result)

            assert len(results) == 10
            assert all(r.text == "Response" for r in results)

    def test_error_recovery_after_failed_generation(self, temp_model_path, model_config, generation_config):
        """Test that model can recover after a failed generation"""
        interface = LlamaCppInterface()

        # Create mock that fails once then succeeds
        call_count = [0]

        def mock_generate(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("First call fails")
            return {
                "choices": [{"text": "Success", "finish_reason": "stop"}],
                "usage": {"completion_tokens": 5, "total_tokens": 15}
            }

        mock_llama_instance = MagicMock(side_effect=mock_generate)

        with patch('llama_cpp.Llama', return_value=mock_llama_instance):
            interface.load(str(temp_model_path), model_config)

            # First call should return error result
            result1 = interface.generate("Test 1", generation_config)
            assert result1.finish_reason == "error"

            # Second call should succeed
            result2 = interface.generate("Test 2", generation_config)
            assert result2.finish_reason == "stop"
            assert result2.text == "Success"


# ============================================================================
# TESTS: Edge Cases
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions"""

    def test_empty_prompt(self, temp_model_path, model_config, generation_config):
        """Test generation with empty prompt"""
        interface = LlamaCppInterface()

        with patch('llama_cpp.Llama', return_value=MagicMock(return_value={
            "choices": [{"text": "Response to empty prompt", "finish_reason": "stop"}],
            "usage": {"completion_tokens": 5, "total_tokens": 5}
        })):
            interface.load(str(temp_model_path), model_config)

            result = interface.generate("", generation_config)

            assert isinstance(result, GenerationResult)
            assert len(result.text) > 0

    def test_very_long_system_prompt(self, temp_model_path, model_config, generation_config):
        """Test generation with very long system prompt"""
        interface = LlamaCppInterface()
        long_system_prompt = "You are a helpful assistant. " * 1000

        with patch('llama_cpp.Llama', return_value=MagicMock(return_value={
            "choices": [{"text": "Response", "finish_reason": "stop"}],
            "usage": {"completion_tokens": 5, "total_tokens": 1005}
        })):
            interface.load(str(temp_model_path), model_config)

            result = interface.generate(
                "Test",
                generation_config,
                system_prompt=long_system_prompt
            )

            assert isinstance(result, GenerationResult)

    def test_zero_max_tokens(self, temp_model_path, model_config):
        """Test generation with zero max tokens"""
        interface = LlamaCppInterface()
        config = GenerationConfig(max_tokens=0)

        with patch('llama_cpp.Llama', return_value=MagicMock(return_value={
            "choices": [{"text": "", "finish_reason": "length"}],
            "usage": {"completion_tokens": 0, "total_tokens": 5}
        })):
            interface.load(str(temp_model_path), model_config)

            # Should still work, just return empty text
            result = interface.generate("Test", config)
            assert isinstance(result, GenerationResult)

    def test_extreme_temperature_values(self, temp_model_path, model_config):
        """Test generation with extreme temperature values"""
        interface = LlamaCppInterface()

        configs = [
            GenerationConfig(temperature=0.0),   # Deterministic
            GenerationConfig(temperature=2.0),   # Very random
        ]

        with patch('llama_cpp.Llama', return_value=MagicMock(return_value={
            "choices": [{"text": "Response", "finish_reason": "stop"}],
            "usage": {"completion_tokens": 5, "total_tokens": 15}
        })):
            interface.load(str(temp_model_path), model_config)

            for config in configs:
                result = interface.generate("Test", config)
                assert isinstance(result, GenerationResult)

    def test_special_characters_in_prompt(self, temp_model_path, model_config, generation_config):
        """Test generation with special characters in prompt"""
        interface = LlamaCppInterface()
        special_prompt = "Test with émojis 🎉 and symbols @#$%^&*()"

        with patch('llama_cpp.Llama', return_value=MagicMock(return_value={
            "choices": [{"text": "Response", "finish_reason": "stop"}],
            "usage": {"completion_tokens": 5, "total_tokens": 15}
        })):
            interface.load(str(temp_model_path), model_config)

            result = interface.generate(special_prompt, generation_config)

            assert isinstance(result, GenerationResult)


# ============================================================================
# TESTS: Integration with Compliance
# ============================================================================

@pytest.mark.compliance
class TestComplianceIntegration:
    """Tests for compliance and audit trail integration"""

    def test_generation_is_deterministic_with_seed(self, temp_model_path, model_config):
        """Test that using same seed produces deterministic results"""
        interface = LlamaCppInterface()

        # Use fixed seed
        config1 = GenerationConfig(seed=42)
        config2 = GenerationConfig(seed=42)

        with patch('llama_cpp.Llama', return_value=MagicMock(return_value={
            "choices": [{"text": "Deterministic response", "finish_reason": "stop"}],
            "usage": {"completion_tokens": 5, "total_tokens": 15}
        })):
            interface.load(str(temp_model_path), model_config)

            result1 = interface.generate("Test", config1)
            result2 = interface.generate("Test", config2)

            # With same seed and prompt, should get same result (mocked)
            assert result1.text == result2.text

    def test_model_path_is_traceable(self, temp_model_path, model_config, mock_llama_class):
        """Test that model path is stored for audit purposes"""
        interface = LlamaCppInterface()

        with patch('llama_cpp.Llama', mock_llama_class) as mock_llama:
            interface.load(str(temp_model_path), model_config)

            # Verify model was loaded with correct path
            call_args = mock_llama.call_args
            assert call_args is not None
            assert 'model_path' in call_args.kwargs or len(call_args.args) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
