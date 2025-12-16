"""
Tests for Semantic Cache Manager

Tests cache hit/miss behavior, persistence, invalidation, and edge cases.
"""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch, Mock
import numpy as np


# Mock dependencies before importing cache_manager
@pytest.fixture(scope="module", autouse=True)
def mock_dependencies():
    """Mock FAISS and sentence-transformers dependencies"""
    # Mock faiss module
    mock_faiss = MagicMock()
    mock_faiss.IndexFlatIP = MagicMock(return_value=MagicMock())
    mock_faiss.read_index = MagicMock()
    mock_faiss.write_index = MagicMock()
    
    # Mock SentenceTransformer
    mock_st_class = MagicMock()
    mock_st = MagicMock(name='SentenceTransformer')
    
    with patch.dict('sys.modules', {
        'faiss': mock_faiss,
        'sentence_transformers': mock_st_class
    }):
        mock_st_class.SentenceTransformer = MagicMock(return_value=mock_st)
        yield {'faiss': mock_faiss, 'sentence_transformers': mock_st_class, 'embedder': mock_st}


@pytest.fixture
def mock_faiss_index():
    """Create a mock FAISS index"""
    index = MagicMock()
    index.ntotal = 0
    
    def add_side_effect(x):
        index.ntotal += 1
    
    index.add = MagicMock(side_effect=add_side_effect)
    
    # Default search returns no results
    index.search = MagicMock(return_value=(
        np.array([[0.95]]),  # High similarity
        np.array([[0]])  # First entry
    ))
    return index


@pytest.fixture
def mock_embedder():
    """Create a mock sentence transformer embedder"""
    embedder = MagicMock()
    embedder.get_sentence_embedding_dimension = MagicMock(return_value=384)
    
    # Return deterministic embeddings for testing
    def encode_side_effect(text, **kwargs):
        # Generate pseudo-random but deterministic embedding based on text hash
        seed = hash(text) % (2**32)
        np.random.seed(seed)
        embedding = np.random.rand(384).astype(np.float32)
        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        return embedding
    
    embedder.encode = MagicMock(side_effect=encode_side_effect)
    return embedder


@pytest.fixture
def temp_cache_paths(tmp_path):
    """Create temporary paths for cache storage"""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return {
        'index_path': str(cache_dir / "cache_index.faiss"),
        'store_path': str(cache_dir / "cache_store.parquet"),
        'cache_dir': cache_dir
    }


@pytest.fixture
def cache_manager(temp_cache_paths, mock_faiss_index, mock_embedder, mock_dependencies):
    """Create a SemanticCacheManager instance with mocked dependencies"""
    with patch('memory.cache_manager.SentenceTransformer', return_value=mock_embedder):
        with patch('memory.cache_manager.faiss') as mock_faiss:
            mock_faiss.IndexFlatIP = MagicMock(return_value=mock_faiss_index)
            mock_faiss.read_index = MagicMock(return_value=mock_faiss_index)
            mock_faiss.write_index = MagicMock()
            
            from memory.cache_manager import SemanticCacheManager
            
            cache = SemanticCacheManager(
                index_path=temp_cache_paths['index_path'],
                store_path=temp_cache_paths['store_path'],
                similarity_threshold=0.9,
                max_cache_size=10,
                ttl_hours=24
            )
            yield cache


class TestCacheManagerBasics:
    """Test basic cache functionality"""
    
    def test_cache_initialization(self, cache_manager):
        """Test cache manager initializes correctly"""
        assert cache_manager is not None
        assert cache_manager.similarity_threshold == 0.9
        assert cache_manager.max_cache_size == 10
        assert cache_manager.ttl_hours == 24
        assert len(cache_manager.entries) == 0
    
    def test_cache_store(self, cache_manager):
        """Test storing a query-response pair"""
        entry_id = cache_manager.store(
            query="What is the capital of France?",
            response_text="The capital of France is Paris.",
            conversation_id="conv_123",
            task_id="task_456",
            tools_used=["search"],
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            iterations=1
        )
        
        assert entry_id is not None
        assert len(cache_manager.entries) == 1
        assert cache_manager.entries[0].query.query_text == "What is the capital of France?"
        assert cache_manager.entries[0].response.response_text == "The capital of France is Paris."
    
    def test_cache_get_exact_match(self, cache_manager):
        """Test retrieving exact same query"""
        # Store entry
        cache_manager.store(
            query="What is Python?",
            response_text="Python is a programming language.",
            conversation_id="conv_123"
        )
        
        # Retrieve with exact same query
        result = cache_manager.get("What is Python?")
        
        # Should get cache hit with very high similarity
        assert result is not None
        assert result['cache_hit'] is True
        assert result['response']['response_text'] == "Python is a programming language."
        assert result['similarity_score'] > 0.9  # Should be above threshold
    
    def test_cache_miss_empty(self, cache_manager):
        """Test cache miss when cache is empty"""
        result = cache_manager.get("Random query")
        assert result is None
        assert cache_manager.metrics.cache_misses == 1
        assert cache_manager.metrics.cache_hits == 0


class TestCacheSimilarity:
    """Test semantic similarity matching"""
    
    def test_cache_hit_similar_query(self, cache_manager):
        """Test cache hit for semantically similar query"""
        # Store original query
        cache_manager.store(
            query="How do I install Python?",
            response_text="Use pip install or download from python.org",
            conversation_id="conv_123"
        )
        
        # Mock the search to return high similarity
        cache_manager.index.search = MagicMock(return_value=(
            np.array([[0.92]]),  # 0.92 similarity (above 0.9 threshold)
            np.array([[0]])  # First entry
        ))
        
        # Try similar query
        result = cache_manager.get("What's the way to install Python?")
        
        # Should get cache hit
        assert result is not None
        assert result['cache_hit'] is True
        assert result['similarity_score'] == 0.92
    
    def test_cache_miss_low_similarity(self, cache_manager):
        """Test cache miss when similarity is below threshold"""
        # Store original query
        cache_manager.store(
            query="How to cook pasta?",
            response_text="Boil water and add pasta.",
            conversation_id="conv_123"
        )
        
        # Mock the search to return low similarity
        cache_manager.index.search = MagicMock(return_value=(
            np.array([[0.7]]),  # 0.7 similarity (below 0.9 threshold)
            np.array([[0]])
        ))
        
        # Try dissimilar query
        result = cache_manager.get("How to code in Python?")
        
        # Should get cache miss
        assert result is None
        assert cache_manager.metrics.cache_misses == 1


class TestCacheMetrics:
    """Test cache metrics tracking"""
    
    def test_hit_rate_calculation(self, cache_manager):
        """Test hit rate is calculated correctly"""
        # Store entries
        cache_manager.store(
            query="Query 1",
            response_text="Response 1",
            conversation_id="conv_1"
        )
        
        cache_manager.store(
            query="Query 2",
            response_text="Response 2",
            conversation_id="conv_2"
        )
        
        # Mock searches - 1 hit, 2 misses
        # First query: hit
        cache_manager.index.search = MagicMock(return_value=(
            np.array([[0.95]]),
            np.array([[0]])
        ))
        result1 = cache_manager.get("Query 1")
        assert result1 is not None
        
        # Second query: miss (low similarity)
        cache_manager.index.search = MagicMock(return_value=(
            np.array([[0.5]]),
            np.array([[0]])
        ))
        result2 = cache_manager.get("Different query")
        assert result2 is None
        
        # Third query: miss (empty result)
        cache_manager.index.search = MagicMock(return_value=(
            np.array([[]]),
            np.array([[]])
        ))
        result3 = cache_manager.get("Another query")
        assert result3 is None
        
        # Check metrics
        metrics = cache_manager.get_metrics()
        assert metrics['total_queries'] == 3
        assert metrics['cache_hits'] == 1
        assert metrics['cache_misses'] == 2
        assert metrics['hit_rate'] == pytest.approx(1/3, rel=0.01)
    
    def test_hit_count_increments(self, cache_manager):
        """Test that hit count increments on repeated cache hits"""
        # Store entry
        cache_manager.store(
            query="Popular query",
            response_text="Popular response",
            conversation_id="conv_1"
        )
        
        # Mock search to always return hit
        cache_manager.index.search = MagicMock(return_value=(
            np.array([[0.95]]),
            np.array([[0]])
        ))
        
        # Hit cache multiple times
        result1 = cache_manager.get("Popular query")
        assert result1['hit_count'] == 1
        
        result2 = cache_manager.get("Popular query")
        assert result2['hit_count'] == 2
        
        result3 = cache_manager.get("Popular query")
        assert result3['hit_count'] == 3


class TestCacheInvalidation:
    """Test cache invalidation mechanisms"""
    
    def test_invalidate_by_age(self, cache_manager):
        """Test invalidating old cache entries"""
        # Store entries with different ages
        with patch('memory.cache_manager.datetime') as mock_datetime:
            # Old entry (25 hours ago)
            old_time = datetime.now(timezone.utc) - timedelta(hours=25)
            mock_datetime.now.return_value = old_time
            mock_datetime.fromisoformat = datetime.fromisoformat
            
            cache_manager.store(
                query="Old query",
                response_text="Old response",
                conversation_id="conv_old"
            )
            
            # Recent entry (1 hour ago)
            recent_time = datetime.now(timezone.utc) - timedelta(hours=1)
            mock_datetime.now.return_value = recent_time
            
            cache_manager.store(
                query="Recent query",
                response_text="Recent response",
                conversation_id="conv_recent"
            )
            
            # Update entry timestamps manually (since mocking might not work perfectly)
            cache_manager.entries[0].created_at = old_time.isoformat()
            cache_manager.entries[1].created_at = recent_time.isoformat()
        
        # Invalidate entries older than 24 hours
        removed = cache_manager.invalidate_by_age(max_age_hours=24)
        
        assert removed == 1
        assert len(cache_manager.entries) == 1
        assert cache_manager.entries[0].query.query_text == "Recent query"
    
    def test_invalidate_all(self, cache_manager):
        """Test clearing all cache entries"""
        # Add multiple entries
        for i in range(5):
            cache_manager.store(
                query=f"Query {i}",
                response_text=f"Response {i}",
                conversation_id=f"conv_{i}"
            )
        
        assert len(cache_manager.entries) == 5
        
        # Clear cache
        cache_manager.invalidate_all()
        
        assert len(cache_manager.entries) == 0
        assert cache_manager.metrics.total_queries == 0
        assert cache_manager.metrics.cache_hits == 0
    
    def test_ttl_expiration(self, cache_manager):
        """Test that expired entries are not returned"""
        # Store entry with old timestamp
        with patch('memory.cache_manager.datetime') as mock_datetime:
            old_time = datetime.now(timezone.utc) - timedelta(hours=30)  # Beyond TTL
            mock_datetime.now.return_value = old_time
            mock_datetime.fromisoformat = datetime.fromisoformat
            
            cache_manager.store(
                query="Expired query",
                response_text="Expired response",
                conversation_id="conv_expired"
            )
            
            # Update entry timestamp
            cache_manager.entries[0].created_at = old_time.isoformat()
        
        # Mock search to return hit
        cache_manager.index.search = MagicMock(return_value=(
            np.array([[0.95]]),
            np.array([[0]])
        ))
        
        # Try to retrieve - should miss due to TTL
        result = cache_manager.get("Expired query")
        
        assert result is None  # Entry expired
        assert cache_manager.metrics.cache_misses == 1


class TestCacheEviction:
    """Test LRU eviction when cache is full"""
    
    def test_evict_oldest_on_max_size(self, cache_manager):
        """Test that oldest entry is evicted when max size is reached"""
        # Fill cache to max size (10 entries)
        for i in range(10):
            cache_manager.store(
                query=f"Query {i}",
                response_text=f"Response {i}",
                conversation_id=f"conv_{i}"
            )
        
        assert len(cache_manager.entries) == 10
        
        # Add one more entry (should evict oldest)
        cache_manager.store(
            query="Query 10",
            response_text="Response 10",
            conversation_id="conv_10"
        )
        
        # Should still have 10 entries (oldest evicted)
        assert len(cache_manager.entries) == 10
        
        # First entry should have been evicted
        query_texts = [entry.query.query_text for entry in cache_manager.entries]
        assert "Query 0" not in query_texts
        assert "Query 10" in query_texts


class TestCachePersistence:
    """Test cache persistence to disk"""
    
    def test_save_and_load_cache(self, temp_cache_paths, mock_faiss_index, mock_embedder):
        """Test saving and loading cache from disk"""
        with patch('memory.cache_manager.SentenceTransformer', return_value=mock_embedder):
            with patch('memory.cache_manager.faiss') as mock_faiss:
                mock_faiss.IndexFlatIP = MagicMock(return_value=mock_faiss_index)
                mock_faiss.read_index = MagicMock(return_value=mock_faiss_index)
                mock_faiss.write_index = MagicMock()
                
                from memory.cache_manager import SemanticCacheManager
                
                # Create cache and add entries
                cache1 = SemanticCacheManager(
                    index_path=temp_cache_paths['index_path'],
                    store_path=temp_cache_paths['store_path']
                )
                
                cache1.store(
                    query="Test query",
                    response_text="Test response",
                    conversation_id="conv_test"
                )
                
                # Verify save was called
                assert mock_faiss.write_index.called
    
    def test_get_stats(self, cache_manager):
        """Test getting cache statistics"""
        # Add some entries
        cache_manager.store(
            query="Query 1",
            response_text="Response 1",
            conversation_id="conv_1"
        )
        
        stats = cache_manager.get_stats()
        
        assert stats['total_entries'] == 1
        assert stats['similarity_threshold'] == 0.9
        assert stats['max_cache_size'] == 10
        assert stats['ttl_hours'] == 24
        assert 'metrics' in stats


class TestCacheEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_cache_get(self, cache_manager):
        """Test get on empty cache"""
        result = cache_manager.get("Any query")
        assert result is None
    
    def test_store_with_all_metadata(self, cache_manager):
        """Test storing with full metadata"""
        entry_id = cache_manager.store(
            query="Complex query",
            response_text="Complex response",
            conversation_id="conv_123",
            task_id="task_456",
            tools_used=["tool1", "tool2", "tool3"],
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            iterations=3,
            metadata={"strategy": "htn", "complexity": "high"}
        )
        
        assert entry_id is not None
        entry = cache_manager.entries[0]
        assert entry.response.tools_used == ["tool1", "tool2", "tool3"]
        assert entry.response.usage["total_tokens"] == 150
        assert entry.response.iterations == 3
        assert entry.response.metadata["strategy"] == "htn"
    
    def test_override_similarity_threshold(self, cache_manager):
        """Test overriding similarity threshold on get"""
        cache_manager.store(
            query="Test query",
            response_text="Test response",
            conversation_id="conv_1"
        )
        
        # Mock search with moderate similarity
        cache_manager.index.search = MagicMock(return_value=(
            np.array([[0.85]]),  # Below default threshold (0.9)
            np.array([[0]])
        ))
        
        # Should miss with default threshold
        result1 = cache_manager.get("Test query")
        assert result1 is None
        
        # Should hit with lower threshold
        result2 = cache_manager.get("Test query", similarity_threshold=0.8)
        assert result2 is not None
        assert result2['similarity_score'] == 0.85


class TestCacheIntegration:
    """Test cache manager singleton and initialization"""
    
    def test_get_cache_manager_singleton(self):
        """Test that get_cache_manager returns singleton"""
        with patch('memory.cache_manager.FAISS_AVAILABLE', True):
            with patch('memory.cache_manager.SENTENCE_TRANSFORMERS_AVAILABLE', True):
                with patch('memory.cache_manager.SemanticCacheManager'):
                    from memory.cache_manager import get_cache_manager
                    
                    manager1 = get_cache_manager()
                    manager2 = get_cache_manager()
                    
                    # Should be same instance
                    assert manager1 is manager2
    
    def test_init_cache_manager_custom(self):
        """Test initializing cache manager with custom parameters"""
        with patch('memory.cache_manager.FAISS_AVAILABLE', True):
            with patch('memory.cache_manager.SENTENCE_TRANSFORMERS_AVAILABLE', True):
                with patch('memory.cache_manager.SemanticCacheManager') as MockCache:
                    from memory.cache_manager import init_cache_manager
                    
                    init_cache_manager(
                        similarity_threshold=0.95,
                        max_cache_size=500,
                        ttl_hours=48
                    )
                    
                    # Verify custom parameters were passed
                    MockCache.assert_called_once()
                    call_kwargs = MockCache.call_args[1]
                    assert call_kwargs['similarity_threshold'] == 0.95
                    assert call_kwargs['max_cache_size'] == 500
                    assert call_kwargs['ttl_hours'] == 48


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
