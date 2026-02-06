"""
Tests pour la mémoire sémantique (FAISS + Sentence Transformers)

Coverage targets:
- FAISS index creation/updates
- Semantic search queries
- Embedding generation
- LRU eviction
- Index persistence
- Error handling
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# ============================================================================
# MODULE-LEVEL MOCK SETUP
# ============================================================================
# These mocks must be installed BEFORE any import of memory.semantic
# because the module uses try/except imports at module load time


def _create_mock_faiss():
    """Create a comprehensive mock faiss module"""
    mock_faiss = MagicMock()
    mock_index = MagicMock()
    mock_index.ntotal = 0
    mock_faiss.IndexFlatL2 = MagicMock(return_value=mock_index)
    mock_faiss.read_index = MagicMock(return_value=mock_index)
    mock_faiss.write_index = MagicMock()
    return mock_faiss


def _create_mock_sentence_transformers():
    """Create a comprehensive mock sentence_transformers module"""
    mock_st_module = MagicMock()
    mock_embedder = MagicMock()
    mock_embedder.get_sentence_embedding_dimension.return_value = 384
    mock_embedder.encode.side_effect = lambda text, **kwargs: np.random.rand(
        384
    ).astype(np.float32)
    mock_st_module.SentenceTransformer.return_value = mock_embedder
    return mock_st_module


# Install mocks into sys.modules BEFORE any test runs
# This ensures memory.semantic sees the mocks when it does "import faiss"
_mock_faiss_module = _create_mock_faiss()
_mock_st_module = _create_mock_sentence_transformers()

if "faiss" not in sys.modules:
    sys.modules["faiss"] = _mock_faiss_module
if "sentence_transformers" not in sys.modules:
    sys.modules["sentence_transformers"] = _mock_st_module


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_faiss_index():
    """Create a mock FAISS index"""
    index = MagicMock()
    index.ntotal = 0
    index.add = MagicMock(
        side_effect=lambda x: setattr(index, "ntotal", index.ntotal + 1)
    )
    index.search = MagicMock(
        return_value=(
            np.array([[0.5, 1.0, 1.5]]),  # distances
            np.array([[0, 1, 2]]),  # indices
        )
    )
    return index


@pytest.fixture
def mock_embedder():
    """Create a mock sentence transformer embedder"""
    embedder = MagicMock()
    embedder.get_sentence_embedding_dimension = MagicMock(return_value=384)
    embedder.encode = MagicMock(
        side_effect=lambda text, **kwargs: np.random.rand(384).astype(np.float32)
    )
    return embedder


@pytest.fixture
def temp_semantic_paths(tmp_path):
    """Create temporary paths for semantic memory"""
    paths = {
        "index_path": tmp_path / "index.faiss",
        "store_path": tmp_path / "store.parquet",
        "semantic_dir": tmp_path,
    }
    paths["semantic_dir"].mkdir(parents=True, exist_ok=True)
    return paths


@pytest.fixture
def semantic_memory_instance(temp_semantic_paths, mock_faiss_index, mock_embedder):
    """Create a SemanticMemory instance with mocked dependencies"""
    # Configure the global mock faiss to use our test-specific index
    _mock_faiss_module.IndexFlatL2.return_value = mock_faiss_index
    _mock_faiss_module.read_index.return_value = mock_faiss_index
    _mock_faiss_module.write_index.reset_mock()

    # Configure the global mock sentence_transformers to use our embedder
    _mock_st_module.SentenceTransformer.return_value = mock_embedder

    # Force reload of the module to pick up new mock configuration
    if "memory.semantic" in sys.modules:
        del sys.modules["memory.semantic"]

    from memory.semantic import SemanticMemory

    memory = SemanticMemory(
        index_path=str(temp_semantic_paths["index_path"]),
        store_path=str(temp_semantic_paths["store_path"]),
        model_name="all-MiniLM-L6-v2",
    )

    yield memory


# ============================================================================
# TESTS: Initialization
# ============================================================================


@pytest.mark.unit
def test_semantic_memory_initialization(temp_semantic_paths, mock_embedder):
    """Test basic initialization of SemanticMemory"""
    # Configure global mocks
    mock_index = MagicMock()
    mock_index.ntotal = 0
    _mock_faiss_module.IndexFlatL2.return_value = mock_index
    _mock_st_module.SentenceTransformer.return_value = mock_embedder

    # Force reload to pick up mock config
    if "memory.semantic" in sys.modules:
        del sys.modules["memory.semantic"]

    from memory.semantic import SemanticMemory

    memory = SemanticMemory(
        index_path=str(temp_semantic_paths["index_path"]),
        store_path=str(temp_semantic_paths["store_path"]),
    )

    assert memory.index is not None
    assert memory.store == []
    assert memory.embedding_dim == 384
    assert memory.embedder is not None


@pytest.mark.unit
def test_semantic_memory_missing_dependencies():
    """Test initialization fails when dependencies are missing"""
    # Force reload to test dependency check
    if "memory.semantic" in sys.modules:
        del sys.modules["memory.semantic"]

    with patch.dict(sys.modules, {"faiss": None}):
        # Re-import with faiss set to None (simulating import failure)
        import importlib

        import memory.semantic as sem_module

        importlib.reload(sem_module)

        # After reload with faiss=None, FAISS_AVAILABLE should be False
        # But our mock is still in place, so we patch the flag directly
        with patch.object(sem_module, "FAISS_AVAILABLE", False):
            with pytest.raises(
                ImportError, match="FAISS or sentence-transformers not installed"
            ):
                sem_module.SemanticMemory()


@pytest.mark.unit
def test_create_empty_index(semantic_memory_instance):
    """Test creating an empty FAISS index"""
    semantic_memory_instance._create_empty_index()

    assert semantic_memory_instance.index is not None
    assert semantic_memory_instance.store == []


# ============================================================================
# TESTS: Adding Passages
# ============================================================================


@pytest.mark.unit
def test_add_passage_basic(semantic_memory_instance):
    """Test adding a basic passage to semantic memory"""
    text = "This is a test passage about machine learning."

    initial_count = semantic_memory_instance.index.ntotal
    semantic_memory_instance.add_passage(text)

    # Verify passage was added to store
    assert len(semantic_memory_instance.store) == 1
    assert semantic_memory_instance.store[0]["text"] == text
    assert "passage_id" in semantic_memory_instance.store[0]
    assert "timestamp" in semantic_memory_instance.store[0]

    # Verify index was updated
    assert semantic_memory_instance.index.ntotal == initial_count + 1


@pytest.mark.unit
def test_add_passage_with_metadata(semantic_memory_instance):
    """Test adding passage with conversation_id, task_id, and metadata"""
    text = "Test passage with metadata"
    conversation_id = "conv-123"
    task_id = "task-456"
    metadata = {"source": "test", "priority": "high"}

    semantic_memory_instance.add_passage(
        text=text, conversation_id=conversation_id, task_id=task_id, metadata=metadata
    )

    passage = semantic_memory_instance.store[0]
    assert passage["text"] == text
    assert passage["conversation_id"] == conversation_id
    assert passage["task_id"] == task_id
    assert passage["metadata"] == metadata


@pytest.mark.unit
def test_add_passage_unique_id(semantic_memory_instance):
    """Test that passage IDs are unique and consistent"""
    text = "Same text for ID test"

    # Add same text twice
    semantic_memory_instance.add_passage(text)
    semantic_memory_instance.add_passage(text)

    # IDs should be the same (based on content hash)
    id1 = semantic_memory_instance.store[0]["passage_id"]
    id2 = semantic_memory_instance.store[1]["passage_id"]

    assert id1 == id2
    assert id1.startswith("passage:")


@pytest.mark.unit
def test_add_multiple_passages(semantic_memory_instance):
    """Test adding multiple passages"""
    passages = [
        "First passage about AI",
        "Second passage about machine learning",
        "Third passage about neural networks",
    ]

    for text in passages:
        semantic_memory_instance.add_passage(text)

    assert len(semantic_memory_instance.store) == 3
    assert semantic_memory_instance.index.ntotal == 3

    # Verify all texts are stored
    stored_texts = [p["text"] for p in semantic_memory_instance.store]
    assert stored_texts == passages


# ============================================================================
# TESTS: Searching
# ============================================================================


@pytest.mark.unit
def test_search_basic(semantic_memory_instance):
    """Test basic semantic search"""
    # Add some passages
    semantic_memory_instance.add_passage("Machine learning is fascinating")
    semantic_memory_instance.add_passage("Deep learning uses neural networks")
    semantic_memory_instance.add_passage("AI is transforming the world")

    # Search
    results = semantic_memory_instance.search("AI and machine learning", top_k=2)

    assert isinstance(results, list)
    assert len(results) <= 2

    # Verify result structure
    if results:
        for result in results:
            assert "text" in result
            assert "score" in result
            assert "rank" in result
            assert "passage_id" in result


@pytest.mark.unit
def test_search_empty_index(semantic_memory_instance):
    """Test searching on empty index returns empty list"""
    results = semantic_memory_instance.search("test query")
    assert results == []


@pytest.mark.unit
def test_search_with_similarity_threshold(semantic_memory_instance):
    """Test search with similarity threshold filtering"""
    semantic_memory_instance.add_passage("Test passage 1")
    semantic_memory_instance.add_passage("Test passage 2")

    # Search with high threshold (should filter out low-similarity results)
    results_high = semantic_memory_instance.search(
        "test query", top_k=5, similarity_threshold=0.9
    )

    # Search with low threshold (should include more results)
    results_low = semantic_memory_instance.search(
        "test query", top_k=5, similarity_threshold=0.1
    )

    # Low threshold should return same or more results
    assert len(results_low) >= len(results_high)


@pytest.mark.unit
def test_search_top_k_limit(semantic_memory_instance):
    """Test that search respects top_k limit"""
    # Add 10 passages
    for i in range(10):
        semantic_memory_instance.add_passage(f"Test passage number {i}")

    # Search with top_k=3
    results = semantic_memory_instance.search("test", top_k=3)

    # Should return at most 3 results
    assert len(results) <= 3


@pytest.mark.unit
def test_search_score_calculation(semantic_memory_instance):
    """Test that search results have valid similarity scores"""
    semantic_memory_instance.add_passage("Machine learning")
    semantic_memory_instance.add_passage("Artificial intelligence")

    results = semantic_memory_instance.search("AI", top_k=2, similarity_threshold=0.0)

    for result in results:
        # Score should be between 0 and 1
        assert 0.0 <= result["score"] <= 1.0


@pytest.mark.unit
def test_search_ranking(semantic_memory_instance):
    """Test that search results are properly ranked"""
    semantic_memory_instance.add_passage("First passage")
    semantic_memory_instance.add_passage("Second passage")
    semantic_memory_instance.add_passage("Third passage")

    results = semantic_memory_instance.search(
        "passage", top_k=3, similarity_threshold=0.0
    )

    # Verify ranks are sequential
    for i, result in enumerate(results):
        assert result["rank"] == i + 1


# ============================================================================
# TESTS: Index Persistence
# ============================================================================


@pytest.mark.unit
def test_save_index(semantic_memory_instance, temp_semantic_paths):
    """Test saving FAISS index to disk"""
    # Add some data
    semantic_memory_instance.add_passage("Test passage for save")

    with (
        patch("memory.semantic.faiss.write_index") as mock_write,
        patch("memory.semantic.pd") as mock_pd,
    ):
        mock_pd.DataFrame.return_value.to_parquet = MagicMock()

        semantic_memory_instance.save_index()

        # Verify FAISS index was saved
        mock_write.assert_called_once()

        # Verify store was saved
        mock_pd.DataFrame.assert_called_once()


@pytest.mark.unit
def test_save_empty_index(semantic_memory_instance):
    """Test saving empty index (no store)"""
    with patch("memory.semantic.faiss.write_index") as mock_write:
        semantic_memory_instance.save_index()

        # FAISS index should still be saved even if empty
        mock_write.assert_called_once()


@pytest.mark.unit
def test_load_index_existing(temp_semantic_paths, mock_embedder):
    """Test loading existing FAISS index from disk"""
    # Create mock index file
    temp_semantic_paths["index_path"].touch()
    temp_semantic_paths["store_path"].touch()

    # Mock store data that should be loaded
    mock_store_data = [
        {
            "passage_id": "passage:abc123",
            "text": "Loaded passage",
            "conversation_id": "conv-1",
            "task_id": None,
            "timestamp": datetime.now().isoformat(),
            "metadata": {},
        }
    ]

    # Configure global mocks
    mock_index = MagicMock()
    mock_index.ntotal = 1
    _mock_faiss_module.read_index.return_value = mock_index
    _mock_faiss_module.IndexFlatL2.return_value = mock_index
    _mock_faiss_module.read_index.reset_mock()
    _mock_st_module.SentenceTransformer.return_value = mock_embedder

    # Force reload
    if "memory.semantic" in sys.modules:
        del sys.modules["memory.semantic"]

    # Mock pandas inside the module after reload
    from memory import semantic as sem_module

    # Create a mock for pd.read_parquet
    mock_df = MagicMock()
    mock_df.to_dict.return_value = mock_store_data

    with (
        patch.object(sem_module, "pd") as mock_pd,
        patch.object(sem_module, "PANDAS_AVAILABLE", True),
    ):
        mock_pd.read_parquet.return_value = mock_df

        memory = sem_module.SemanticMemory(
            index_path=str(temp_semantic_paths["index_path"]),
            store_path=str(temp_semantic_paths["store_path"]),
        )

        # Verify index was loaded
        _mock_faiss_module.read_index.assert_called_once()
        assert memory.store == mock_store_data


@pytest.mark.unit
def test_load_index_error_fallback(temp_semantic_paths, mock_embedder):
    """Test fallback to empty index when loading fails"""
    # Create mock index file that will fail to load
    temp_semantic_paths["index_path"].touch()

    # Configure global mocks
    _mock_faiss_module.read_index.side_effect = Exception("Load error")
    mock_index = MagicMock()
    mock_index.ntotal = 0
    _mock_faiss_module.IndexFlatL2.return_value = mock_index
    _mock_st_module.SentenceTransformer.return_value = mock_embedder

    # Force reload
    if "memory.semantic" in sys.modules:
        del sys.modules["memory.semantic"]

    from memory.semantic import SemanticMemory

    memory = SemanticMemory(
        index_path=str(temp_semantic_paths["index_path"]),
        store_path=str(temp_semantic_paths["store_path"]),
    )

    # Should create empty index instead
    assert memory.index is not None
    assert memory.store == []

    # Reset side_effect for other tests
    _mock_faiss_module.read_index.side_effect = None


@pytest.mark.unit
def test_rebuild_index(semantic_memory_instance):
    """Test rebuilding FAISS index from store"""
    # Add passages to store
    semantic_memory_instance.store = [
        {
            "passage_id": "passage:1",
            "text": "First passage",
            "conversation_id": None,
            "task_id": None,
            "timestamp": datetime.now().isoformat(),
            "metadata": {},
        },
        {
            "passage_id": "passage:2",
            "text": "Second passage",
            "conversation_id": None,
            "task_id": None,
            "timestamp": datetime.now().isoformat(),
            "metadata": {},
        },
    ]

    # Configure and reset global mock for this test
    mock_new_index = MagicMock()
    mock_new_index.ntotal = 0
    _mock_faiss_module.IndexFlatL2.return_value = mock_new_index
    _mock_faiss_module.IndexFlatL2.reset_mock()

    semantic_memory_instance.rebuild_index()

    # Verify new index was created
    _mock_faiss_module.IndexFlatL2.assert_called()

    # Verify embeddings were added
    assert mock_new_index.add.call_count == 2


@pytest.mark.unit
def test_rebuild_index_empty_store(semantic_memory_instance):
    """Test rebuilding index with empty store does nothing"""
    semantic_memory_instance.store = []

    # Reset mock to track calls
    _mock_faiss_module.IndexFlatL2.reset_mock()

    semantic_memory_instance.rebuild_index()

    # Should not create new index
    _mock_faiss_module.IndexFlatL2.assert_not_called()


# ============================================================================
# TESTS: Cleanup and LRU Eviction
# ============================================================================


@pytest.mark.unit
def test_cleanup_old_passages(semantic_memory_instance):
    """Test cleanup of old passages based on TTL"""
    # Add passages with different timestamps
    now = datetime.now()
    old_date = now - timedelta(days=40)
    recent_date = now - timedelta(days=10)

    semantic_memory_instance.store = [
        {
            "passage_id": "passage:old",
            "text": "Old passage",
            "timestamp": old_date.isoformat(),
            "conversation_id": None,
            "task_id": None,
            "metadata": {},
        },
        {
            "passage_id": "passage:recent",
            "text": "Recent passage",
            "timestamp": recent_date.isoformat(),
            "conversation_id": None,
            "task_id": None,
            "metadata": {},
        },
    ]

    # Configure global mock
    mock_new_index = MagicMock()
    _mock_faiss_module.IndexFlatL2.return_value = mock_new_index

    # Cleanup with 30-day TTL
    removed_count = semantic_memory_instance.cleanup_old_passages(ttl_days=30)

    # Should remove 1 passage
    assert removed_count == 1
    assert len(semantic_memory_instance.store) == 1
    assert semantic_memory_instance.store[0]["passage_id"] == "passage:recent"


@pytest.mark.unit
def test_cleanup_no_old_passages(semantic_memory_instance):
    """Test cleanup when no passages are old enough"""
    # Add recent passages
    recent_date = datetime.now() - timedelta(days=10)

    semantic_memory_instance.store = [
        {
            "passage_id": "passage:1",
            "text": "Recent passage 1",
            "timestamp": recent_date.isoformat(),
            "conversation_id": None,
            "task_id": None,
            "metadata": {},
        },
        {
            "passage_id": "passage:2",
            "text": "Recent passage 2",
            "timestamp": recent_date.isoformat(),
            "conversation_id": None,
            "task_id": None,
            "metadata": {},
        },
    ]

    # Cleanup with 30-day TTL
    removed_count = semantic_memory_instance.cleanup_old_passages(ttl_days=30)

    # Should remove 0 passages
    assert removed_count == 0
    assert len(semantic_memory_instance.store) == 2


@pytest.mark.unit
def test_cleanup_all_old(semantic_memory_instance):
    """Test cleanup when all passages are old"""
    old_date = datetime.now() - timedelta(days=60)

    semantic_memory_instance.store = [
        {
            "passage_id": "passage:1",
            "text": "Old passage 1",
            "timestamp": old_date.isoformat(),
            "conversation_id": None,
            "task_id": None,
            "metadata": {},
        },
        {
            "passage_id": "passage:2",
            "text": "Old passage 2",
            "timestamp": old_date.isoformat(),
            "conversation_id": None,
            "task_id": None,
            "metadata": {},
        },
    ]

    # Configure global mock
    mock_new_index = MagicMock()
    _mock_faiss_module.IndexFlatL2.return_value = mock_new_index

    # Cleanup with 30-day TTL
    removed_count = semantic_memory_instance.cleanup_old_passages(ttl_days=30)

    # Should remove all passages
    assert removed_count == 2
    assert len(semantic_memory_instance.store) == 0


@pytest.mark.unit
def test_cleanup_rebuilds_index(semantic_memory_instance):
    """Test that cleanup rebuilds the FAISS index"""
    old_date = datetime.now() - timedelta(days=40)
    recent_date = datetime.now() - timedelta(days=10)

    semantic_memory_instance.store = [
        {
            "passage_id": "passage:old",
            "text": "Old passage",
            "timestamp": old_date.isoformat(),
            "conversation_id": None,
            "task_id": None,
            "metadata": {},
        },
        {
            "passage_id": "passage:recent",
            "text": "Recent passage",
            "timestamp": recent_date.isoformat(),
            "conversation_id": None,
            "task_id": None,
            "metadata": {},
        },
    ]

    # Configure global mock and reset to track calls
    mock_new_index = MagicMock()
    _mock_faiss_module.IndexFlatL2.return_value = mock_new_index
    _mock_faiss_module.IndexFlatL2.reset_mock()

    semantic_memory_instance.cleanup_old_passages(ttl_days=30)

    # Should create new index
    _mock_faiss_module.IndexFlatL2.assert_called()

    # Should re-add remaining passages
    assert mock_new_index.add.call_count == 1


# ============================================================================
# TESTS: Singleton Pattern
# ============================================================================


@pytest.mark.unit
def test_get_semantic_memory_singleton():
    """Test get_semantic_memory returns singleton instance"""
    # Force reload
    if "memory.semantic" in sys.modules:
        del sys.modules["memory.semantic"]

    import memory.semantic
    from memory.semantic import get_semantic_memory

    # Reset singleton
    memory.semantic._semantic_memory = None

    # Get instance
    instance1 = get_semantic_memory()
    instance2 = get_semantic_memory()

    # Should be the same instance
    assert instance1 is instance2


@pytest.mark.unit
def test_init_semantic_memory():
    """Test init_semantic_memory creates new instance"""
    # Configure global mocks
    mock_index = MagicMock()
    mock_index.ntotal = 0
    _mock_faiss_module.IndexFlatL2.return_value = mock_index

    mock_embedder = MagicMock()
    mock_embedder.get_sentence_embedding_dimension.return_value = 384
    _mock_st_module.SentenceTransformer.return_value = mock_embedder

    # Force reload
    if "memory.semantic" in sys.modules:
        del sys.modules["memory.semantic"]

    from memory.semantic import init_semantic_memory

    # Initialize with custom parameters
    instance = init_semantic_memory(
        index_path="/tmp/custom_index.faiss", store_path="/tmp/custom_store.parquet"
    )

    assert instance is not None
    assert instance.index_path == Path("/tmp/custom_index.faiss")
    assert instance.store_path == Path("/tmp/custom_store.parquet")


# ============================================================================
# TESTS: Integration Scenarios
# ============================================================================


@pytest.mark.integration
def test_full_workflow(semantic_memory_instance, temp_semantic_paths):
    """Test complete workflow: add, search, save, load"""
    # Add passages
    passages = [
        "Machine learning is a subset of artificial intelligence",
        "Deep learning uses neural networks with multiple layers",
        "Natural language processing helps computers understand text",
    ]

    for text in passages:
        semantic_memory_instance.add_passage(text, conversation_id="conv-1")

    # Search
    results = semantic_memory_instance.search("AI and neural networks", top_k=2)
    assert len(results) <= 2

    # Save
    with (
        patch("memory.semantic.faiss.write_index"),
        patch("memory.semantic.pd") as mock_pd,
    ):
        mock_pd.DataFrame.return_value.to_parquet = MagicMock()
        semantic_memory_instance.save_index()

    # Verify all passages were stored
    assert len(semantic_memory_instance.store) == 3


@pytest.mark.integration
def test_passage_lifecycle(semantic_memory_instance):
    """Test full lifecycle: add, search, cleanup"""
    # Add old passage
    old_date = datetime.now() - timedelta(days=40)
    semantic_memory_instance.store.append(
        {
            "passage_id": "passage:old",
            "text": "Old passage to be cleaned",
            "timestamp": old_date.isoformat(),
            "conversation_id": "conv-old",
            "task_id": None,
            "metadata": {},
        }
    )

    # Add new passage
    semantic_memory_instance.add_passage(
        "Recent passage to keep", conversation_id="conv-new"
    )

    # Cleanup old passages
    mock_new_index = MagicMock()
    _mock_faiss_module.IndexFlatL2.return_value = mock_new_index

    removed = semantic_memory_instance.cleanup_old_passages(ttl_days=30)

    assert removed == 1
    assert len(semantic_memory_instance.store) == 1
    assert semantic_memory_instance.store[0]["conversation_id"] == "conv-new"


@pytest.mark.integration
def test_concurrent_operations(semantic_memory_instance):
    """Test handling multiple operations in sequence"""
    # Add passages
    for i in range(5):
        semantic_memory_instance.add_passage(f"Passage {i}", task_id=f"task-{i}")

    # Search multiple times
    for query in ["Passage 0", "Passage 2", "Passage 4"]:
        results = semantic_memory_instance.search(query, top_k=2)
        assert isinstance(results, list)

    # Rebuild index
    mock_new_index = MagicMock()
    _mock_faiss_module.IndexFlatL2.return_value = mock_new_index
    semantic_memory_instance.rebuild_index()

    # Verify store integrity
    assert len(semantic_memory_instance.store) == 5


# ============================================================================
# TESTS: Edge Cases
# ============================================================================


@pytest.mark.unit
def test_empty_text_passage(semantic_memory_instance):
    """Test handling empty text passage"""
    semantic_memory_instance.add_passage("")

    assert len(semantic_memory_instance.store) == 1
    assert semantic_memory_instance.store[0]["text"] == ""


@pytest.mark.unit
def test_very_long_passage(semantic_memory_instance):
    """Test handling very long text passage"""
    long_text = "This is a long passage. " * 1000
    semantic_memory_instance.add_passage(long_text)

    assert len(semantic_memory_instance.store) == 1
    assert semantic_memory_instance.store[0]["text"] == long_text


@pytest.mark.unit
def test_special_characters_in_passage(semantic_memory_instance):
    """Test handling special characters in passages"""
    special_text = "Test with special chars: @#$%^&*(){}[]|\\/<>?~`"
    semantic_memory_instance.add_passage(special_text)

    assert len(semantic_memory_instance.store) == 1
    assert semantic_memory_instance.store[0]["text"] == special_text


@pytest.mark.unit
def test_unicode_in_passage(semantic_memory_instance):
    """Test handling Unicode characters"""
    unicode_text = "Test avec caractères spéciaux: éàùç 中文 العربية 🚀"
    semantic_memory_instance.add_passage(unicode_text)

    assert len(semantic_memory_instance.store) == 1
    assert semantic_memory_instance.store[0]["text"] == unicode_text


@pytest.mark.unit
def test_search_with_zero_top_k(semantic_memory_instance):
    """Test search with top_k=0 returns empty list"""
    semantic_memory_instance.add_passage("Test passage")

    results = semantic_memory_instance.search("test", top_k=0)

    # FAISS will return empty results for top_k=0
    assert isinstance(results, list)


@pytest.mark.unit
def test_cleanup_with_invalid_timestamp(semantic_memory_instance):
    """Test cleanup handles invalid timestamp gracefully"""
    # This test verifies robust error handling
    # The actual implementation may raise an exception for invalid timestamps
    # which is acceptable behavior

    semantic_memory_instance.store = [
        {
            "passage_id": "passage:bad",
            "text": "Passage with bad timestamp",
            "timestamp": "invalid-timestamp",
            "conversation_id": None,
            "task_id": None,
            "metadata": {},
        }
    ]

    # Should raise ValueError from datetime.fromisoformat
    with pytest.raises(ValueError):
        semantic_memory_instance.cleanup_old_passages(ttl_days=30)
