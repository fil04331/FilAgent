"""
Integration tests for Agent with Semantic Cache

Tests that the agent correctly uses the semantic cache to reduce
inference costs and latency for similar queries.
"""

import pytest
from unittest.mock import MagicMock, patch, Mock
import numpy as np


@pytest.fixture
def mock_cache_dependencies():
    """Mock FAISS and sentence-transformers for cache"""
    mock_faiss = MagicMock()
    mock_faiss.IndexFlatIP = MagicMock(return_value=MagicMock())
    mock_faiss.read_index = MagicMock()
    mock_faiss.write_index = MagicMock()
    
    mock_st_class = MagicMock()
    mock_st = MagicMock()
    mock_st.get_sentence_embedding_dimension = MagicMock(return_value=384)
    mock_st.encode = MagicMock(side_effect=lambda text, **kwargs: np.random.rand(384).astype(np.float32))
    mock_st_class.SentenceTransformer = MagicMock(return_value=mock_st)
    
    with patch.dict('sys.modules', {
        'faiss': mock_faiss,
        'sentence_transformers': mock_st_class
    }):
        yield {'faiss': mock_faiss, 'st_class': mock_st_class, 'embedder': mock_st}


@pytest.fixture
def mock_agent_config():
    """Create a mock agent configuration"""
    config = MagicMock()
    
    # Model config
    config.model.backend = "mock"
    config.model.path = "/path/to/model"
    config.model.context_size = 4096
    config.model.n_gpu_layers = 0
    
    # Generation config
    config.generation.temperature = 0.7
    config.generation.top_p = 0.9
    config.generation.max_tokens = 512
    config.generation.seed = 42
    config.generation.top_k = 40
    config.generation.repetition_penalty = 1.0
    
    # Compliance guardian disabled for tests
    config.compliance_guardian = None
    
    return config


@pytest.fixture
def mock_model():
    """Create a mock model interface"""
    model = MagicMock()
    generation_result = MagicMock()
    generation_result.text = "This is a test response."
    generation_result.prompt_tokens = 10
    generation_result.tokens_generated = 5
    generation_result.total_tokens = 15
    model.generate = MagicMock(return_value=generation_result)
    return model


class TestAgentCacheIntegration:
    """Test agent integration with semantic cache"""
    
    def test_agent_cache_hit(self, mock_cache_dependencies, mock_agent_config, mock_model, tmp_path):
        """Test that agent returns cached response on cache hit"""
        from runtime.agent import Agent
        
        # Create cache directory
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        
        # Patch cache manager initialization
        with patch('memory.cache_manager.SemanticCacheManager') as MockCache:
            cache_instance = MagicMock()
            MockCache.return_value = cache_instance
            
            # First query: cache miss
            cache_instance.get = MagicMock(return_value=None)
            cache_instance.store = MagicMock()
            
            # Patch runtime.agent.CACHE_AVAILABLE
            with patch('runtime.agent.CACHE_AVAILABLE', True):
                with patch('runtime.agent.get_cache_manager', return_value=cache_instance):
                    # Create agent
                    agent = Agent(config=mock_agent_config)
                    agent.model = mock_model
                    
                    # First query - should miss cache and execute
                    result1 = agent.chat("What is Python?", "conv_123")
                    
                    # Should have called model.generate
                    assert mock_model.generate.called
                    
                    # Should have stored in cache
                    cache_instance.store.assert_called_once()
                    
                    # Reset mocks
                    mock_model.generate.reset_mock()
                    cache_instance.store.reset_mock()
                    
                    # Second query: cache hit
                    cache_instance.get = MagicMock(return_value={
                        'entry_id': 'cache:123',
                        'query': {
                            'query_text': 'What is Python?',
                            'query_hash': 'abc123',
                            'conversation_id': 'conv_123',
                            'task_id': None,
                            'timestamp': '2024-01-01T00:00:00Z'
                        },
                        'response': {
                            'response_text': 'Python is a programming language.',
                            'tools_used': [],
                            'usage': {'prompt_tokens': 10, 'completion_tokens': 5, 'total_tokens': 15},
                            'iterations': 1,
                            'metadata': {}
                        },
                        'similarity_score': 0.95,
                        'cache_hit': True,
                        'hit_count': 1,
                        'age_hours': 1.0
                    })
                    
                    result2 = agent.chat("What's Python?", "conv_123")
                    
                    # Should NOT have called model.generate (cache hit)
                    assert not mock_model.generate.called
                    
                    # Should have returned cached response
                    assert result2['response'] == 'Python is a programming language.'
                    assert result2['cache_hit'] is True
                    assert 'cache_metadata' in result2
                    assert result2['cache_metadata']['similarity_score'] == 0.95
    
    def test_agent_cache_miss_fallback(self, mock_cache_dependencies, mock_agent_config, mock_model, tmp_path):
        """Test that agent falls back to normal execution on cache miss"""
        from runtime.agent import Agent
        
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        
        with patch('memory.cache_manager.SemanticCacheManager') as MockCache:
            cache_instance = MagicMock()
            MockCache.return_value = cache_instance
            
            # Cache miss
            cache_instance.get = MagicMock(return_value=None)
            cache_instance.store = MagicMock()
            
            with patch('runtime.agent.CACHE_AVAILABLE', True):
                with patch('runtime.agent.get_cache_manager', return_value=cache_instance):
                    agent = Agent(config=mock_agent_config)
                    agent.model = mock_model
                    
                    result = agent.chat("Unique query", "conv_456")
                    
                    # Should have executed normally
                    assert mock_model.generate.called
                    
                    # Should have stored result in cache
                    cache_instance.store.assert_called_once()
    
    def test_agent_cache_disabled(self, mock_agent_config, mock_model):
        """Test agent behavior when cache is not available"""
        from runtime.agent import Agent
        
        with patch('runtime.agent.CACHE_AVAILABLE', False):
            agent = Agent(config=mock_agent_config)
            agent.model = mock_model
            
            # Should execute normally without cache
            result = agent.chat("Test query", "conv_789")
            
            # Should have called model.generate
            assert mock_model.generate.called
    
    def test_agent_cache_error_fallback(self, mock_cache_dependencies, mock_agent_config, mock_model):
        """Test that agent handles cache errors gracefully"""
        from runtime.agent import Agent
        
        with patch('memory.cache_manager.SemanticCacheManager') as MockCache:
            cache_instance = MagicMock()
            MockCache.return_value = cache_instance
            
            # Cache throws error
            cache_instance.get = MagicMock(side_effect=Exception("Cache error"))
            cache_instance.store = MagicMock()
            
            with patch('runtime.agent.CACHE_AVAILABLE', True):
                with patch('runtime.agent.get_cache_manager', return_value=cache_instance):
                    agent = Agent(config=mock_agent_config)
                    agent.model = mock_model
                    
                    # Should not crash, should fall back to normal execution
                    result = agent.chat("Test query", "conv_error")
                    
                    # Should have executed normally
                    assert mock_model.generate.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
