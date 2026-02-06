"""
Tests for VectorStore abstraction and implementations
Tests both FAISSVectorStore and ChromaDBVectorStore
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import numpy as np


# Mock dependencies before importing
@pytest.fixture(scope="module", autouse=True)
def mock_dependencies():
    """Mock FAISS, sentence-transformers, and chromadb"""
    mock_faiss = MagicMock()
    mock_faiss.IndexFlatL2 = MagicMock(return_value=MagicMock())
    mock_faiss.read_index = MagicMock()
    mock_faiss.write_index = MagicMock()

    mock_st = MagicMock()
    mock_chromadb = MagicMock()

    with patch.dict(
        "sys.modules",
        {
            "faiss": mock_faiss,
            "sentence_transformers": mock_st,
            "chromadb": mock_chromadb,
        },
    ):
        yield


# ============================================================================
# TESTS: VectorStore Abstract Interface
# ============================================================================


@pytest.mark.unit
def test_vector_store_is_abstract():
    """Test that VectorStore is an abstract base class"""
    from memory.semantic import VectorStore

    # Should not be able to instantiate abstract class
    with pytest.raises(TypeError):
        VectorStore()


# ============================================================================
# TESTS: FAISSVectorStore - Initialization
# ============================================================================


@pytest.mark.unit
def test_faiss_vector_store_initialization():
    """Test FAISSVectorStore initialization"""
    with (
        patch("memory.semantic.FAISS_AVAILABLE", True),
        patch("memory.semantic.SENTENCE_TRANSFORMERS_AVAILABLE", True),
        patch("memory.semantic.faiss") as mock_faiss,
        patch("memory.semantic.SentenceTransformer") as mock_st,
    ):

        mock_index = MagicMock()
        mock_index.ntotal = 0
        mock_faiss.IndexFlatL2 = MagicMock(return_value=mock_index)

        mock_embedder = MagicMock()
        mock_embedder.get_sentence_embedding_dimension.return_value = 384
        mock_st.return_value = mock_embedder

        from memory.semantic import FAISSVectorStore

        store = FAISSVectorStore(
            index_path="test_index.faiss",
            store_path="test_store.parquet",
            model_name="all-MiniLM-L6-v2",
        )

        assert store.embedding_dim == 384
        assert store.index is not None
        assert store.store == []


@pytest.mark.unit
def test_faiss_vector_store_custom_embedding_dim():
    """Test FAISSVectorStore with custom embedding dimension"""
    with (
        patch("memory.semantic.FAISS_AVAILABLE", True),
        patch("memory.semantic.SENTENCE_TRANSFORMERS_AVAILABLE", True),
        patch("memory.semantic.faiss") as mock_faiss,
        patch("memory.semantic.SentenceTransformer") as mock_st,
    ):

        mock_index = MagicMock()
        mock_index.ntotal = 0
        mock_faiss.IndexFlatL2 = MagicMock(return_value=mock_index)

        mock_embedder = MagicMock()
        mock_embedder.get_sentence_embedding_dimension.return_value = 384
        mock_st.return_value = mock_embedder

        from memory.semantic import FAISSVectorStore

        store = FAISSVectorStore(embedding_dim=768)

        assert store.embedding_dim == 768  # Should use override


# ============================================================================
# TESTS: FAISSVectorStore - add_documents
# ============================================================================


@pytest.mark.unit
def test_faiss_add_documents_empty():
    """Test adding empty list returns empty"""
    with (
        patch("memory.semantic.FAISS_AVAILABLE", True),
        patch("memory.semantic.SENTENCE_TRANSFORMERS_AVAILABLE", True),
        patch("memory.semantic.faiss") as mock_faiss,
        patch("memory.semantic.SentenceTransformer") as mock_st,
    ):

        mock_index = MagicMock()
        mock_index.ntotal = 0
        mock_faiss.IndexFlatL2 = MagicMock(return_value=mock_index)

        mock_embedder = MagicMock()
        mock_embedder.get_sentence_embedding_dimension.return_value = 384
        mock_st.return_value = mock_embedder

        from memory.semantic import FAISSVectorStore

        store = FAISSVectorStore()
        ids = store.add_documents([])

        assert ids == []


@pytest.mark.unit
def test_faiss_add_documents_single():
    """Test adding single document"""
    with (
        patch("memory.semantic.FAISS_AVAILABLE", True),
        patch("memory.semantic.SENTENCE_TRANSFORMERS_AVAILABLE", True),
        patch("memory.semantic.faiss") as mock_faiss,
        patch("memory.semantic.SentenceTransformer") as mock_st,
    ):

        mock_index = MagicMock()
        mock_index.ntotal = 0
        mock_index.add = MagicMock()
        mock_faiss.IndexFlatL2 = MagicMock(return_value=mock_index)

        mock_embedder = MagicMock()
        mock_embedder.get_sentence_embedding_dimension.return_value = 384
        mock_embedder.encode = MagicMock(return_value=np.random.rand(384).astype(np.float32))
        mock_st.return_value = mock_embedder

        from memory.semantic import FAISSVectorStore

        store = FAISSVectorStore()
        ids = store.add_documents(["Test document"])

        assert len(ids) == 1
        assert ids[0].startswith("doc:")
        assert len(store.store) == 1
        assert store.store[0]["text"] == "Test document"


@pytest.mark.unit
def test_faiss_add_documents_with_metadata():
    """Test adding documents with metadata"""
    with (
        patch("memory.semantic.FAISS_AVAILABLE", True),
        patch("memory.semantic.SENTENCE_TRANSFORMERS_AVAILABLE", True),
        patch("memory.semantic.faiss") as mock_faiss,
        patch("memory.semantic.SentenceTransformer") as mock_st,
    ):

        mock_index = MagicMock()
        mock_index.ntotal = 0
        mock_index.add = MagicMock()
        mock_faiss.IndexFlatL2 = MagicMock(return_value=mock_index)

        mock_embedder = MagicMock()
        mock_embedder.get_sentence_embedding_dimension.return_value = 384
        mock_embedder.encode = MagicMock(return_value=np.random.rand(1, 384).astype(np.float32))
        mock_st.return_value = mock_embedder

        from memory.semantic import FAISSVectorStore

        store = FAISSVectorStore()

        metadatas = [{"source": "test.pdf", "page": 1}]
        ids = store.add_documents(["Test document"], metadatas=metadatas)

        assert len(ids) == 1
        assert store.store[0]["metadata"]["source"] == "test.pdf"
        assert store.store[0]["metadata"]["page"] == 1


@pytest.mark.unit
def test_faiss_add_documents_custom_ids():
    """Test adding documents with custom IDs"""
    with (
        patch("memory.semantic.FAISS_AVAILABLE", True),
        patch("memory.semantic.SENTENCE_TRANSFORMERS_AVAILABLE", True),
        patch("memory.semantic.faiss") as mock_faiss,
        patch("memory.semantic.SentenceTransformer") as mock_st,
    ):

        mock_index = MagicMock()
        mock_index.ntotal = 0
        mock_index.add = MagicMock()
        mock_faiss.IndexFlatL2 = MagicMock(return_value=mock_index)

        mock_embedder = MagicMock()
        mock_embedder.get_sentence_embedding_dimension.return_value = 384
        mock_embedder.encode = MagicMock(return_value=np.random.rand(1, 384).astype(np.float32))
        mock_st.return_value = mock_embedder

        from memory.semantic import FAISSVectorStore

        store = FAISSVectorStore()

        custom_ids = ["custom-id-1"]
        ids = store.add_documents(["Test document"], ids=custom_ids)

        assert ids == custom_ids
        assert store.store[0]["id"] == "custom-id-1"


# ============================================================================
# TESTS: FAISSVectorStore - similarity_search
# ============================================================================


@pytest.mark.unit
def test_faiss_similarity_search_empty_index():
    """Test searching empty index returns empty list"""
    with (
        patch("memory.semantic.FAISS_AVAILABLE", True),
        patch("memory.semantic.SENTENCE_TRANSFORMERS_AVAILABLE", True),
        patch("memory.semantic.faiss") as mock_faiss,
        patch("memory.semantic.SentenceTransformer") as mock_st,
    ):

        mock_index = MagicMock()
        mock_index.ntotal = 0
        mock_faiss.IndexFlatL2 = MagicMock(return_value=mock_index)

        mock_embedder = MagicMock()
        mock_embedder.get_sentence_embedding_dimension.return_value = 384
        mock_st.return_value = mock_embedder

        from memory.semantic import FAISSVectorStore

        store = FAISSVectorStore()
        results = store.similarity_search("test query")

        assert results == []


@pytest.mark.unit
def test_faiss_similarity_search_with_results():
    """Test similarity search returns formatted results"""
    with (
        patch("memory.semantic.FAISS_AVAILABLE", True),
        patch("memory.semantic.SENTENCE_TRANSFORMERS_AVAILABLE", True),
        patch("memory.semantic.faiss") as mock_faiss,
        patch("memory.semantic.SentenceTransformer") as mock_st,
    ):

        mock_index = MagicMock()
        mock_index.ntotal = 2
        mock_index.add = MagicMock()
        # Mock search to return 2 results
        mock_index.search = MagicMock(
            return_value=(np.array([[0.5, 1.0]]), np.array([[0, 1]]))  # distances  # indices
        )
        mock_faiss.IndexFlatL2 = MagicMock(return_value=mock_index)

        mock_embedder = MagicMock()
        mock_embedder.get_sentence_embedding_dimension.return_value = 384
        mock_embedder.encode = MagicMock(return_value=np.random.rand(384).astype(np.float32))
        mock_st.return_value = mock_embedder

        from memory.semantic import FAISSVectorStore

        store = FAISSVectorStore()

        # Add documents
        store.store = [
            {"id": "doc1", "text": "Document 1", "metadata": {}, "timestamp": "2024-01-01"},
            {"id": "doc2", "text": "Document 2", "metadata": {}, "timestamp": "2024-01-02"},
        ]

        results = store.similarity_search("test query", k=2)

        assert len(results) == 2
        assert results[0]["id"] == "doc1"
        assert results[0]["text"] == "Document 1"
        assert "score" in results[0]
        assert results[0]["score"] > 0


# ============================================================================
# TESTS: FAISSVectorStore - delete
# ============================================================================


@pytest.mark.unit
def test_faiss_delete_documents():
    """Test deleting documents by IDs"""
    with (
        patch("memory.semantic.FAISS_AVAILABLE", True),
        patch("memory.semantic.SENTENCE_TRANSFORMERS_AVAILABLE", True),
        patch("memory.semantic.faiss") as mock_faiss,
        patch("memory.semantic.SentenceTransformer") as mock_st,
    ):

        mock_index = MagicMock()
        mock_index.ntotal = 3
        mock_faiss.IndexFlatL2 = MagicMock(return_value=mock_index)

        mock_embedder = MagicMock()
        mock_embedder.get_sentence_embedding_dimension.return_value = 384
        mock_embedder.encode = MagicMock(return_value=np.random.rand(2, 384).astype(np.float32))
        mock_st.return_value = mock_embedder

        from memory.semantic import FAISSVectorStore

        store = FAISSVectorStore()

        # Add documents
        store.store = [
            {"id": "doc1", "text": "Document 1", "metadata": {}, "timestamp": "2024-01-01"},
            {"id": "doc2", "text": "Document 2", "metadata": {}, "timestamp": "2024-01-02"},
            {"id": "doc3", "text": "Document 3", "metadata": {}, "timestamp": "2024-01-03"},
        ]

        # Delete one document
        success = store.delete(["doc2"])

        assert success is True
        assert len(store.store) == 2
        assert all(doc["id"] != "doc2" for doc in store.store)


@pytest.mark.unit
def test_faiss_delete_nonexistent():
    """Test deleting nonexistent documents returns False"""
    with (
        patch("memory.semantic.FAISS_AVAILABLE", True),
        patch("memory.semantic.SENTENCE_TRANSFORMERS_AVAILABLE", True),
        patch("memory.semantic.faiss") as mock_faiss,
        patch("memory.semantic.SentenceTransformer") as mock_st,
    ):

        mock_index = MagicMock()
        mock_index.ntotal = 1
        mock_faiss.IndexFlatL2 = MagicMock(return_value=mock_index)

        mock_embedder = MagicMock()
        mock_embedder.get_sentence_embedding_dimension.return_value = 384
        mock_st.return_value = mock_embedder

        from memory.semantic import FAISSVectorStore

        store = FAISSVectorStore()
        store.store = [
            {"id": "doc1", "text": "Document 1", "metadata": {}, "timestamp": "2024-01-01"},
        ]

        # Try to delete nonexistent document
        success = store.delete(["nonexistent"])

        assert success is False


# ============================================================================
# TESTS: FAISSVectorStore - count
# ============================================================================


@pytest.mark.unit
def test_faiss_count():
    """Test counting documents in FAISS store"""
    with (
        patch("memory.semantic.FAISS_AVAILABLE", True),
        patch("memory.semantic.SENTENCE_TRANSFORMERS_AVAILABLE", True),
        patch("memory.semantic.faiss") as mock_faiss,
        patch("memory.semantic.SentenceTransformer") as mock_st,
    ):

        mock_index = MagicMock()
        mock_index.ntotal = 5
        mock_faiss.IndexFlatL2 = MagicMock(return_value=mock_index)

        mock_embedder = MagicMock()
        mock_embedder.get_sentence_embedding_dimension.return_value = 384
        mock_st.return_value = mock_embedder

        from memory.semantic import FAISSVectorStore

        store = FAISSVectorStore()

        count = store.count()
        assert count == 5


# ============================================================================
# TESTS: FAISSVectorStore - save/load
# ============================================================================


@pytest.mark.unit
def test_faiss_save():
    """Test saving FAISS index"""
    with (
        patch("memory.semantic.FAISS_AVAILABLE", True),
        patch("memory.semantic.SENTENCE_TRANSFORMERS_AVAILABLE", True),
        patch("memory.semantic.PANDAS_AVAILABLE", True),
        patch("memory.semantic.faiss") as mock_faiss,
        patch("memory.semantic.SentenceTransformer") as mock_st,
        patch("memory.semantic.pd") as mock_pd,
    ):

        mock_index = MagicMock()
        mock_index.ntotal = 1
        mock_faiss.IndexFlatL2 = MagicMock(return_value=mock_index)
        mock_faiss.write_index = MagicMock()

        mock_embedder = MagicMock()
        mock_embedder.get_sentence_embedding_dimension.return_value = 384
        mock_st.return_value = mock_embedder

        mock_df = MagicMock()
        mock_pd.DataFrame.return_value = mock_df

        from memory.semantic import FAISSVectorStore

        store = FAISSVectorStore()
        store.store = [{"id": "doc1", "text": "Test", "metadata": {}}]

        store.save()

        # Verify FAISS index was saved
        mock_faiss.write_index.assert_called_once()

        # Verify DataFrame was created and saved
        mock_pd.DataFrame.assert_called_once()
        mock_df.to_parquet.assert_called_once()


# ============================================================================
# TESTS: ChromaDBVectorStore - Initialization
# ============================================================================


@pytest.mark.unit
def test_chromadb_initialization():
    """Test ChromaDBVectorStore initialization"""
    with (
        patch("memory.semantic.CHROMADB_AVAILABLE", True),
        patch("memory.semantic.chromadb") as mock_chromadb,
    ):

        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chromadb.PersistentClient.return_value = mock_client

        from memory.semantic import ChromaDBVectorStore

        store = ChromaDBVectorStore(
            collection_name="test_collection",
            persist_directory="test_dir",
        )

        assert store.collection_name == "test_collection"
        assert store.collection == mock_collection


@pytest.mark.unit
def test_chromadb_missing_dependency():
    """Test ChromaDB initialization fails without chromadb"""
    with patch("memory.semantic.CHROMADB_AVAILABLE", False):
        from memory.semantic import ChromaDBVectorStore

        with pytest.raises(ImportError, match="chromadb not installed"):
            ChromaDBVectorStore()


# ============================================================================
# TESTS: ChromaDBVectorStore - Operations
# ============================================================================


@pytest.mark.unit
def test_chromadb_add_documents():
    """Test adding documents to ChromaDB"""
    with (
        patch("memory.semantic.CHROMADB_AVAILABLE", True),
        patch("memory.semantic.chromadb") as mock_chromadb,
    ):

        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_collection.add = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chromadb.PersistentClient.return_value = mock_client

        from memory.semantic import ChromaDBVectorStore

        store = ChromaDBVectorStore()
        ids = store.add_documents(
            ["Document 1", "Document 2"], metadatas=[{"source": "test"}, {"source": "test"}]
        )

        assert len(ids) == 2
        mock_collection.add.assert_called_once()


@pytest.mark.unit
def test_chromadb_similarity_search():
    """Test similarity search in ChromaDB"""
    with (
        patch("memory.semantic.CHROMADB_AVAILABLE", True),
        patch("memory.semantic.chromadb") as mock_chromadb,
    ):

        mock_client = MagicMock()
        mock_collection = MagicMock()

        # Mock query results
        mock_collection.query.return_value = {
            "ids": [["doc1", "doc2"]],
            "documents": [["Document 1", "Document 2"]],
            "distances": [[0.1, 0.2]],
            "metadatas": [[{"source": "test1"}, {"source": "test2"}]],
        }

        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chromadb.PersistentClient.return_value = mock_client

        from memory.semantic import ChromaDBVectorStore

        store = ChromaDBVectorStore()
        results = store.similarity_search("test query", k=2)

        assert len(results) == 2
        assert results[0]["id"] == "doc1"
        assert results[0]["text"] == "Document 1"
        assert "score" in results[0]


@pytest.mark.unit
def test_chromadb_delete():
    """Test deleting documents from ChromaDB"""
    with (
        patch("memory.semantic.CHROMADB_AVAILABLE", True),
        patch("memory.semantic.chromadb") as mock_chromadb,
    ):

        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_collection.delete = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chromadb.PersistentClient.return_value = mock_client

        from memory.semantic import ChromaDBVectorStore

        store = ChromaDBVectorStore()
        success = store.delete(["doc1", "doc2"])

        assert success is True
        mock_collection.delete.assert_called_once_with(ids=["doc1", "doc2"])


@pytest.mark.unit
def test_chromadb_count():
    """Test counting documents in ChromaDB"""
    with (
        patch("memory.semantic.CHROMADB_AVAILABLE", True),
        patch("memory.semantic.chromadb") as mock_chromadb,
    ):

        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_collection.count.return_value = 10
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chromadb.PersistentClient.return_value = mock_client

        from memory.semantic import ChromaDBVectorStore

        store = ChromaDBVectorStore()
        count = store.count()

        assert count == 10


# ============================================================================
# TESTS: Global Instance Management
# ============================================================================


@pytest.mark.unit
def test_init_semantic_memory_faiss():
    """Test initializing semantic memory with FAISS backend"""
    with (
        patch("memory.semantic.FAISS_AVAILABLE", True),
        patch("memory.semantic.SENTENCE_TRANSFORMERS_AVAILABLE", True),
        patch("memory.semantic.faiss") as mock_faiss,
        patch("memory.semantic.SentenceTransformer") as mock_st,
    ):

        mock_index = MagicMock()
        mock_index.ntotal = 0
        mock_faiss.IndexFlatL2 = MagicMock(return_value=mock_index)

        mock_embedder = MagicMock()
        mock_embedder.get_sentence_embedding_dimension.return_value = 384
        mock_st.return_value = mock_embedder

        from memory.semantic import init_semantic_memory, FAISSVectorStore

        store = init_semantic_memory(backend="faiss")

        assert isinstance(store, FAISSVectorStore)


@pytest.mark.unit
def test_init_semantic_memory_chromadb():
    """Test initializing semantic memory with ChromaDB backend"""
    with (
        patch("memory.semantic.CHROMADB_AVAILABLE", True),
        patch("memory.semantic.chromadb") as mock_chromadb,
    ):

        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chromadb.PersistentClient.return_value = mock_client

        from memory.semantic import init_semantic_memory, ChromaDBVectorStore

        store = init_semantic_memory(backend="chromadb")

        assert isinstance(store, ChromaDBVectorStore)


@pytest.mark.unit
def test_get_semantic_memory_singleton():
    """Test get_semantic_memory returns singleton"""
    with (
        patch("memory.semantic.FAISS_AVAILABLE", True),
        patch("memory.semantic.SENTENCE_TRANSFORMERS_AVAILABLE", True),
        patch("memory.semantic.faiss") as mock_faiss,
        patch("memory.semantic.SentenceTransformer") as mock_st,
    ):

        mock_index = MagicMock()
        mock_index.ntotal = 0
        mock_faiss.IndexFlatL2 = MagicMock(return_value=mock_index)

        mock_embedder = MagicMock()
        mock_embedder.get_sentence_embedding_dimension.return_value = 384
        mock_st.return_value = mock_embedder

        # Reset singleton
        import memory.semantic

        memory.semantic._semantic_memory = None

        from memory.semantic import get_semantic_memory

        instance1 = get_semantic_memory()
        instance2 = get_semantic_memory()

        assert instance1 is instance2
