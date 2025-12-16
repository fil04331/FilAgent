"""
Mémoire sémantique pour recherche de connaissances à long terme
Utilise FAISS pour l'indexation vectorielle et sentence-transformers pour les embeddings

Architecture:
- VectorStore: Abstract base class for vector storage backends
- FAISSVectorStore: FAISS-based implementation (default, local)
- ChromaDBVectorStore: ChromaDB-based implementation (optional, persistent)
"""
import json
import hashlib
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
import numpy as np

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    print("Warning: FAISS not installed. Semantic memory will not work.")

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("Warning: sentence-transformers not installed. Semantic memory will not work.")

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None
    print("Warning: pandas not installed. save/load functionality will not work.")

try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False


class VectorStore(ABC):
    """
    Abstract base class for vector storage backends
    
    Defines the interface that all vector store implementations must follow.
    """
    
    @abstractmethod
    def add_documents(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Add documents to the vector store
        
        Args:
            texts: List of text documents to add
            metadatas: Optional list of metadata dictionaries (one per document)
            ids: Optional list of document IDs (auto-generated if None)
            
        Returns:
            List of document IDs that were added
        """
        pass
    
    @abstractmethod
    def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents
        
        Args:
            query: Query text
            k: Number of results to return
            filter: Optional metadata filter
            
        Returns:
            List of documents with scores and metadata
        """
        pass
    
    @abstractmethod
    def delete(self, ids: List[str]) -> bool:
        """
        Delete documents by IDs
        
        Args:
            ids: List of document IDs to delete
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    def count(self) -> int:
        """
        Get total number of documents in store
        
        Returns:
            Document count
        """
        pass
    
    @abstractmethod
    def save(self) -> None:
        """Save vector store to disk"""
        pass
    
    @abstractmethod
    def load(self) -> None:
        """Load vector store from disk"""
        pass


class FAISSVectorStore(VectorStore):
    """
    FAISS-based vector store implementation
    
    Uses FAISS for efficient similarity search and sentence-transformers for embeddings.
    Stores document metadata in Parquet format.
    """
    
    def __init__(
        self,
        index_path: str = "memory/semantic/index.faiss",
        store_path: str = "memory/semantic/store.parquet",
        model_name: str = "all-MiniLM-L6-v2",
        embedding_dim: Optional[int] = None,
    ):
        """
        Initialize FAISS vector store
        
        Args:
            index_path: Path to FAISS index file
            store_path: Path to metadata store (Parquet)
            model_name: Sentence transformer model name (default: all-MiniLM-L6-v2)
            embedding_dim: Override embedding dimension (auto-detected if None)
        """
        if not FAISS_AVAILABLE or not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError("FAISS or sentence-transformers not installed")
        
        self.index_path = Path(index_path)
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Embedding model
        self.embedder = SentenceTransformer(model_name)
        self.embedding_dim = embedding_dim or self.embedder.get_sentence_embedding_dimension()
        
        # FAISS index
        self.index = None
        self.store = []  # Document metadata store
        
        # Load existing index if available
        self.load()
    
    def load(self) -> None:
        """Load FAISS index from disk"""
        if self.index_path.exists():
            try:
                self.index = faiss.read_index(str(self.index_path))
                # Load metadata store
                if self.store_path.exists() and PANDAS_AVAILABLE:
                    self.store = pd.read_parquet(self.store_path).to_dict('records')
                print(f"✓ Loaded semantic index with {self.index.ntotal} passages")
            except Exception as e:
                print(f"Warning: Could not load index: {e}. Creating new index.")
                self._create_empty_index()
        else:
            self._create_empty_index()
    
    def _create_empty_index(self) -> None:
        """Create empty FAISS index"""
        # Flat index with L2 distance
        self.index = faiss.IndexFlatL2(self.embedding_dim)
        self.store = []
    
    def count(self) -> int:
        """Get total number of documents"""
        return self.index.ntotal if self.index else 0
    
    def add_documents(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Add documents to vector store
        
        Args:
            texts: List of text documents
            metadatas: Optional metadata for each document
            ids: Optional document IDs (auto-generated if None)
            
        Returns:
            List of document IDs
        """
        if not texts:
            return []
        
        # Generate IDs if not provided
        # Use 16 chars (64 bits) to minimize collision risk for large collections
        if ids is None:
            ids = [
                f"doc:{hashlib.sha256(text.encode()).hexdigest()[:16]}"
                for text in texts
            ]
        
        # Ensure metadatas list matches texts length
        if metadatas is None:
            metadatas = [{} for _ in texts]
        elif len(metadatas) != len(texts):
            raise ValueError("metadatas length must match texts length")
        
        # Generate embeddings
        embeddings = self.embedder.encode(texts, convert_to_numpy=True)
        if len(embeddings.shape) == 1:
            embeddings = embeddings.reshape(1, -1)
        
        # Add to FAISS index
        self.index.add(embeddings.astype(np.float32))
        
        # Add to metadata store
        timestamp = datetime.now().isoformat()
        for doc_id, text, metadata in zip(ids, texts, metadatas):
            self.store.append({
                "id": doc_id,
                "text": text,
                "timestamp": timestamp,
                "metadata": metadata,
            })
        
        return ids
    
    def add_passage(
        self,
        text: str,
        conversation_id: Optional[str] = None,
        task_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> str:
        """
        Legacy method: Add a single passage (kept for backward compatibility)
        
        Args:
            text: Text content
            conversation_id: Conversation ID
            task_id: Task ID
            metadata: Additional metadata
            
        Returns:
            Document ID
        """
        # Generate embedding
        embedding = self.embedder.encode(text, convert_to_numpy=True).reshape(1, -1)
        
        # Create unique ID
        passage_id = f"passage:{hashlib.sha256(text.encode()).hexdigest()[:8]}"
        
        # Add to index
        self.index.add(embedding.astype(np.float32))
        
        # Add to store (maintain old format for backward compatibility)
        self.store.append({
            "passage_id": passage_id,
            "id": passage_id,  # Also add new format
            "text": text,
            "conversation_id": conversation_id,
            "task_id": task_id,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        })
        
        return passage_id
    
    def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents
        
        Args:
            query: Query text
            k: Number of results to return
            filter: Optional metadata filter (not implemented for FAISS)
            
        Returns:
            List of documents with scores and metadata
        """
        if self.index is None or self.index.ntotal == 0:
            return []
        
        # Encode query
        query_embedding = self.embedder.encode(query, convert_to_numpy=True).reshape(1, -1)
        
        # Search in FAISS index (L2 distance)
        distances, indices = self.index.search(query_embedding.astype(np.float32), k)
        
        results = []
        for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
            # Skip invalid indices
            if idx < 0 or idx >= len(self.store):
                continue
            
            # Convert L2 distance to similarity score
            similarity = 1.0 / (1.0 + distance)
            
            doc = self.store[idx]
            
            # Apply filter if provided
            if filter:
                match = all(
                    doc.get("metadata", {}).get(k) == v
                    for k, v in filter.items()
                )
                if not match:
                    continue
            
            results.append({
                "id": doc.get("id", doc.get("passage_id", f"doc:{idx}")),
                "text": doc["text"],
                "score": float(similarity),
                "metadata": doc.get("metadata", {}),
                "timestamp": doc.get("timestamp"),
            })
        
        return results
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """
        Legacy search method (kept for backward compatibility)
        
        Args:
            query: Query text
            top_k: Number of results
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of results with scores
        """
        results = self.similarity_search(query, k=top_k)
        
        # Filter by threshold and add rank
        filtered = []
        for i, result in enumerate(results):
            if result["score"] >= similarity_threshold:
                result["rank"] = i + 1
                # Add legacy fields for backward compatibility
                if "passage_id" not in result and "id" in result:
                    result["passage_id"] = result["id"]
                filtered.append(result)
        
        return filtered
    
    def delete(self, ids: List[str]) -> bool:
        """
        Delete documents by IDs
        
        Note: FAISS doesn't support direct deletion. This rebuilds the index.
        
        Args:
            ids: List of document IDs to delete
            
        Returns:
            True if successful
        """
        if not ids:
            return True
        
        # Filter out documents to delete
        ids_set = set(ids)
        new_store = [
            doc for doc in self.store
            if doc.get("id", doc.get("passage_id")) not in ids_set
        ]
        
        if len(new_store) == len(self.store):
            return False  # No documents were deleted
        
        # Rebuild index without deleted documents
        self.store = new_store
        self._rebuild_index_from_store()
        
        return True
    
    def _rebuild_index_from_store(self) -> None:
        """Rebuild FAISS index from current store"""
        if not self.store:
            self._create_empty_index()
            return
        
        # Create new index
        new_index = faiss.IndexFlatL2(self.embedding_dim)
        
        # Re-encode all documents
        texts = [doc["text"] for doc in self.store]
        embeddings = self.embedder.encode(texts, convert_to_numpy=True)
        if len(embeddings.shape) == 1:
            embeddings = embeddings.reshape(1, -1)
        
        new_index.add(embeddings.astype(np.float32))
        self.index = new_index
    
    def cleanup_old_passages(self, ttl_days: int = 30) -> int:
        """
        Clean up passages older than ttl_days
        
        Args:
            ttl_days: Retention period in days
        
        Returns:
            Number of passages deleted
        """
        cutoff_date = datetime.now() - timedelta(days=ttl_days)
        
        initial_count = len(self.store)
        
        # Filter out old passages
        self.store = [
            doc for doc in self.store
            if datetime.fromisoformat(doc['timestamp']) >= cutoff_date
        ]
        
        removed_count = initial_count - len(self.store)
        
        # Rebuild index if documents were removed
        if removed_count > 0:
            self._rebuild_index_from_store()
        
        return removed_count
    
    def save(self) -> None:
        """Save FAISS index and metadata store to disk"""
        # Save FAISS index
        faiss.write_index(self.index, str(self.index_path))

        # Save metadata store
        if self.store and PANDAS_AVAILABLE:
            df = pd.DataFrame(self.store)
            df.to_parquet(self.store_path, index=False)
        
        print(f"✓ Saved semantic index with {len(self.store)} passages")
    
    def save_index(self) -> None:
        """Legacy method (kept for backward compatibility)"""
        self.save()
    
    def rebuild_index(self) -> None:
        """
        Rebuild index from store
        Useful if store is manually updated
        """
        if not self.store:
            return
        
        self._rebuild_index_from_store()
        print(f"✓ Rebuilt semantic index with {len(self.store)} passages")


class ChromaDBVectorStore(VectorStore):
    """
    ChromaDB-based vector store implementation
    
    Uses ChromaDB for persistent vector storage with built-in metadata filtering.
    Requires: pip install chromadb
    """
    
    def __init__(
        self,
        collection_name: str = "filagent_docs",
        persist_directory: str = "memory/semantic/chromadb",
        model_name: str = "all-MiniLM-L6-v2",
    ):
        """
        Initialize ChromaDB vector store
        
        Args:
            collection_name: Name of the collection
            persist_directory: Directory for persistent storage
            model_name: Sentence transformer model name
        """
        if not CHROMADB_AVAILABLE:
            raise ImportError("chromadb not installed. Install with: pip install chromadb")
        
        self.collection_name = collection_name
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=str(self.persist_directory))
        
        # Get or create collection with sentence transformer embedding function
        try:
            from chromadb.utils import embedding_functions
            self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=model_name
            )
        except ImportError:
            print("Warning: Using default ChromaDB embedding function")
            self.embedding_fn = None
        
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn,
        )
    
    def add_documents(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """Add documents to ChromaDB collection"""
        if not texts:
            return []
        
        # Generate IDs if not provided
        # Use 16 chars (64 bits) to minimize collision risk for large collections
        if ids is None:
            ids = [
                f"doc:{hashlib.sha256(text.encode()).hexdigest()[:16]}"
                for text in texts
            ]
        
        # Prepare metadatas
        if metadatas is None:
            metadatas = [{} for _ in texts]
        
        # Add timestamp to metadata
        timestamp = datetime.now().isoformat()
        for metadata in metadatas:
            if "timestamp" not in metadata:
                metadata["timestamp"] = timestamp
        
        # Add to collection
        self.collection.add(
            documents=texts,
            metadatas=metadatas,
            ids=ids,
        )
        
        return ids
    
    def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar documents in ChromaDB"""
        # Build where clause for filtering
        where = filter if filter else None
        
        # Query collection
        results = self.collection.query(
            query_texts=[query],
            n_results=k,
            where=where,
        )
        
        # Format results
        documents = []
        if results['ids'] and results['ids'][0]:
            for i in range(len(results['ids'][0])):
                doc = {
                    "id": results['ids'][0][i],
                    "text": results['documents'][0][i],
                    "score": 1.0 - results['distances'][0][i],  # Convert distance to similarity
                    "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                }
                documents.append(doc)
        
        return documents
    
    def delete(self, ids: List[str]) -> bool:
        """Delete documents by IDs from ChromaDB"""
        if not ids:
            return True
        
        try:
            self.collection.delete(ids=ids)
            return True
        except Exception as e:
            print(f"Error deleting documents: {e}")
            return False
    
    def count(self) -> int:
        """Get total number of documents in collection"""
        return self.collection.count()
    
    def save(self) -> None:
        """ChromaDB automatically persists, no explicit save needed"""
        pass
    
    def load(self) -> None:
        """ChromaDB automatically loads from persist_directory"""
        pass


# Backward compatibility: Keep SemanticMemory as alias for FAISSVectorStore
SemanticMemory = FAISSVectorStore


# Global instance management
_semantic_memory: Optional[VectorStore] = None


def get_semantic_memory() -> VectorStore:
    """Get global semantic memory instance"""
    global _semantic_memory
    if _semantic_memory is None:
        _semantic_memory = FAISSVectorStore()
    return _semantic_memory


def init_semantic_memory(
    backend: str = "faiss",
    **kwargs
) -> VectorStore:
    """
    Initialize semantic memory with specified backend
    
    Args:
        backend: "faiss" or "chromadb"
        **kwargs: Backend-specific parameters
        
    Returns:
        VectorStore instance
    """
    global _semantic_memory
    
    if backend.lower() == "chromadb":
        _semantic_memory = ChromaDBVectorStore(**kwargs)
    else:  # default to FAISS
        _semantic_memory = FAISSVectorStore(**kwargs)
    
    return _semantic_memory
