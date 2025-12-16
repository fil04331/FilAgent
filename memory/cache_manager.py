"""
Semantic Cache Manager for FilAgent

Implements a persistent semantic caching layer using FAISS for vector similarity search.
When a user query is semantically similar (>0.9 cosine similarity by default) to a 
previously cached query, the stored response is returned immediately, avoiding expensive
LLM inference calls.

Performance Benefits:
- Reduced API inference costs
- Lower perceived latency for similar queries
- Transparent fallback on cache miss

Architecture:
- Uses FAISS for efficient vector similarity search
- Uses sentence-transformers for query embedding
- Persistent disk storage for cache entries (FAISS index + Parquet store)
- Pydantic models for type safety and validation
"""

import json
import hashlib
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
import numpy as np
from pydantic import BaseModel, Field, ConfigDict

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    print("Warning: FAISS not installed. Semantic cache will not work.")

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("Warning: sentence-transformers not installed. Semantic cache will not work.")

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None
    print("Warning: pandas not installed. Cache persistence will not work.")


class CachedQuery(BaseModel):
    """Pydantic model for a cached query"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    query_text: str = Field(..., description="Original query text")
    query_hash: str = Field(..., description="SHA256 hash of the query")
    embedding: Optional[np.ndarray] = Field(default=None, description="Query embedding vector")
    conversation_id: Optional[str] = Field(default=None, description="Conversation ID")
    task_id: Optional[str] = Field(default=None, description="Task ID")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CachedResponse(BaseModel):
    """Pydantic model for a cached response"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    response_text: str = Field(..., description="Agent response text")
    tools_used: List[str] = Field(default_factory=list, description="Tools used in response")
    usage: Dict[str, int] = Field(
        default_factory=lambda: {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        description="Token usage statistics"
    )
    iterations: int = Field(default=1, description="Number of agent iterations")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class CacheEntry(BaseModel):
    """Complete cache entry with query and response"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    entry_id: str = Field(..., description="Unique entry ID")
    query: CachedQuery = Field(..., description="Cached query")
    response: CachedResponse = Field(..., description="Cached response")
    hit_count: int = Field(default=0, description="Number of times this entry was hit")
    last_hit: Optional[str] = Field(default=None, description="Timestamp of last cache hit")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CacheMetrics(BaseModel):
    """Cache performance metrics"""
    total_queries: int = Field(default=0, description="Total queries processed")
    cache_hits: int = Field(default=0, description="Number of cache hits")
    cache_misses: int = Field(default=0, description="Number of cache misses")
    hit_rate: float = Field(default=0.0, description="Cache hit rate (0.0 to 1.0)")
    avg_similarity_on_hit: float = Field(default=0.0, description="Average similarity score on hits")


class SemanticCacheManager:
    """
    Semantic Cache Manager using FAISS for vector similarity search
    
    This cache manager stores query-response pairs and uses semantic similarity
    to retrieve cached responses for similar queries, reducing inference costs.
    
    Example:
        >>> cache = SemanticCacheManager()
        >>> # Store a response
        >>> cache.store(
        ...     query="What is the capital of France?",
        ...     response_text="The capital of France is Paris.",
        ...     conversation_id="conv_123"
        ... )
        >>> # Retrieve cached response for similar query
        >>> result = cache.get("What's France's capital city?")
        >>> if result:
        ...     print(result['response']['response_text'])
    """
    
    def __init__(
        self,
        index_path: str = "memory/semantic/cache_index.faiss",
        store_path: str = "memory/semantic/cache_store.parquet",
        model_name: str = "all-MiniLM-L6-v2",
        similarity_threshold: float = 0.9,
        max_cache_size: int = 1000,
        ttl_hours: int = 24,
    ):
        """
        Initialize Semantic Cache Manager
        
        Args:
            index_path: Path to FAISS index file
            store_path: Path to Parquet store file
            model_name: Sentence-transformers model name (default: all-MiniLM-L6-v2)
            similarity_threshold: Minimum cosine similarity for cache hit (default: 0.9)
            max_cache_size: Maximum number of entries in cache
            ttl_hours: Time-to-live for cache entries in hours (default: 24)
        """
        if not FAISS_AVAILABLE or not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "FAISS and sentence-transformers are required for semantic cache. "
                "Install with: pip install faiss-cpu sentence-transformers"
            )
        
        self.index_path = Path(index_path)
        self.store_path = Path(store_path)
        self.similarity_threshold = similarity_threshold
        self.max_cache_size = max_cache_size
        self.ttl_hours = ttl_hours
        
        # Ensure directory exists
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize embedder
        self.embedder = SentenceTransformer(model_name)
        self.embedding_dim = self.embedder.get_sentence_embedding_dimension()
        
        # Initialize FAISS index (using Inner Product for cosine similarity)
        # Note: FAISS IndexFlatIP computes inner product, which equals cosine similarity
        # when vectors are L2-normalized
        self.index = None
        self.entries: List[CacheEntry] = []
        
        # Metrics
        self.metrics = CacheMetrics()
        
        # Load existing cache
        self._load_cache()
    
    def _load_cache(self):
        """Load cache from disk if exists"""
        if self.index_path.exists() and self.store_path.exists():
            try:
                # Load FAISS index
                self.index = faiss.read_index(str(self.index_path))
                
                # Load store entries
                if PANDAS_AVAILABLE:
                    df = pd.read_parquet(self.store_path)
                    self.entries = []
                    for _, row in df.iterrows():
                        # Reconstruct CacheEntry from stored data
                        query = CachedQuery(
                            query_text=row['query_text'],
                            query_hash=row['query_hash'],
                            conversation_id=row.get('conversation_id'),
                            task_id=row.get('task_id'),
                            timestamp=row['timestamp']
                        )
                        response = CachedResponse(
                            response_text=row['response_text'],
                            tools_used=json.loads(row['tools_used']) if isinstance(row['tools_used'], str) else row['tools_used'],
                            usage=json.loads(row['usage']) if isinstance(row['usage'], str) else row['usage'],
                            iterations=int(row['iterations']),
                            metadata=json.loads(row['metadata']) if isinstance(row['metadata'], str) else row['metadata']
                        )
                        entry = CacheEntry(
                            entry_id=row['entry_id'],
                            query=query,
                            response=response,
                            hit_count=int(row.get('hit_count', 0)),
                            last_hit=row.get('last_hit'),
                            created_at=row['created_at']
                        )
                        self.entries.append(entry)
                    
                    print(f"✓ Loaded semantic cache with {len(self.entries)} entries")
                else:
                    print("⚠ Pandas not available, cannot load cache store")
                    self._create_empty_cache()
            except Exception as e:
                print(f"⚠ Could not load cache: {e}. Creating new cache.")
                self._create_empty_cache()
        else:
            self._create_empty_cache()
    
    def _create_empty_cache(self):
        """Create empty cache structures"""
        # Use IndexFlatIP for cosine similarity (with normalized vectors)
        self.index = faiss.IndexFlatIP(self.embedding_dim)
        self.entries = []
    
    def _compute_query_hash(self, query: str) -> str:
        """Compute SHA256 hash of query"""
        return hashlib.sha256(query.encode()).hexdigest()
    
    def _normalize_vector(self, vector: np.ndarray) -> np.ndarray:
        """L2-normalize vector for cosine similarity"""
        norm = np.linalg.norm(vector)
        if norm > 0:
            return vector / norm
        return vector
    
    def store(
        self,
        query: str,
        response_text: str,
        conversation_id: Optional[str] = None,
        task_id: Optional[str] = None,
        tools_used: Optional[List[str]] = None,
        usage: Optional[Dict[str, int]] = None,
        iterations: int = 1,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store a query-response pair in the semantic cache
        
        Args:
            query: User query text
            response_text: Agent response text
            conversation_id: Conversation ID
            task_id: Task ID
            tools_used: List of tools used
            usage: Token usage statistics
            iterations: Number of agent iterations
            metadata: Additional metadata
        
        Returns:
            Entry ID of stored cache entry
        """
        # Generate embedding for query
        query_embedding = self.embedder.encode(query, convert_to_numpy=True)
        query_embedding = self._normalize_vector(query_embedding)
        
        # Create cache entry
        query_hash = self._compute_query_hash(query)
        entry_id = f"cache:{query_hash[:12]}:{datetime.now(timezone.utc).timestamp()}"
        
        cached_query = CachedQuery(
            query_text=query,
            query_hash=query_hash,
            embedding=query_embedding,
            conversation_id=conversation_id,
            task_id=task_id
        )
        
        cached_response = CachedResponse(
            response_text=response_text,
            tools_used=tools_used or [],
            usage=usage or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            iterations=iterations,
            metadata=metadata or {}
        )
        
        entry = CacheEntry(
            entry_id=entry_id,
            query=cached_query,
            response=cached_response
        )
        
        # Add to FAISS index
        self.index.add(query_embedding.reshape(1, -1).astype(np.float32))
        
        # Add to entries store
        self.entries.append(entry)
        
        # Enforce max cache size (LRU eviction by creation time)
        if len(self.entries) > self.max_cache_size:
            self._evict_oldest()
        
        # Persist to disk
        self._save_cache()
        
        return entry_id
    
    def get(
        self,
        query: str,
        similarity_threshold: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached response for a query if similarity is above threshold
        
        Args:
            query: User query text
            similarity_threshold: Override default similarity threshold
        
        Returns:
            Dictionary with cached response data and metadata, or None if cache miss
        """
        self.metrics.total_queries += 1
        
        if self.index is None or self.index.ntotal == 0:
            self.metrics.cache_misses += 1
            self._update_hit_rate()
            return None
        
        threshold = similarity_threshold if similarity_threshold is not None else self.similarity_threshold
        
        # Generate embedding for query
        query_embedding = self.embedder.encode(query, convert_to_numpy=True)
        query_embedding = self._normalize_vector(query_embedding)
        
        # Search in FAISS index (top-1 result)
        similarities, indices = self.index.search(
            query_embedding.reshape(1, -1).astype(np.float32), 
            k=1
        )
        
        if len(indices[0]) == 0 or indices[0][0] < 0:
            self.metrics.cache_misses += 1
            self._update_hit_rate()
            return None
        
        # Check if similarity meets threshold
        similarity_score = float(similarities[0][0])
        idx = int(indices[0][0])
        
        if similarity_score < threshold or idx >= len(self.entries):
            self.metrics.cache_misses += 1
            self._update_hit_rate()
            return None
        
        # Cache hit!
        entry = self.entries[idx]
        
        # Check TTL
        created_at = datetime.fromisoformat(entry.created_at)
        age_hours = (datetime.now(timezone.utc) - created_at).total_seconds() / 3600
        if age_hours > self.ttl_hours:
            # Entry expired, treat as miss
            self.metrics.cache_misses += 1
            self._update_hit_rate()
            return None
        
        # Update hit metrics
        self.metrics.cache_hits += 1
        self.metrics.avg_similarity_on_hit = (
            (self.metrics.avg_similarity_on_hit * (self.metrics.cache_hits - 1) + similarity_score) 
            / self.metrics.cache_hits
        )
        self._update_hit_rate()
        
        # Update entry hit count
        entry.hit_count += 1
        entry.last_hit = datetime.now(timezone.utc).isoformat()
        
        # Return cached data
        return {
            "entry_id": entry.entry_id,
            "query": entry.query.model_dump(exclude={'embedding'}),
            "response": entry.response.model_dump(),
            "similarity_score": similarity_score,
            "cache_hit": True,
            "hit_count": entry.hit_count,
            "age_hours": age_hours
        }
    
    def invalidate_by_age(self, max_age_hours: Optional[int] = None) -> int:
        """
        Invalidate cache entries older than specified age
        
        Args:
            max_age_hours: Maximum age in hours (default: self.ttl_hours)
        
        Returns:
            Number of entries invalidated
        """
        max_age = max_age_hours if max_age_hours is not None else self.ttl_hours
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age)
        
        indices_to_keep = []
        entries_to_keep = []
        
        for i, entry in enumerate(self.entries):
            created_at = datetime.fromisoformat(entry.created_at)
            if created_at >= cutoff_time:
                indices_to_keep.append(i)
                entries_to_keep.append(entry)
        
        removed_count = len(self.entries) - len(entries_to_keep)
        
        if removed_count > 0:
            self._rebuild_index(entries_to_keep)
            print(f"✓ Invalidated {removed_count} cache entries by age")
        
        return removed_count
    
    def invalidate_all(self):
        """Clear all cache entries"""
        self._create_empty_cache()
        self.metrics = CacheMetrics()
        self._save_cache()
        print("✓ Cache cleared")
    
    def _evict_oldest(self):
        """Evict oldest entry (LRU by creation time)"""
        if not self.entries:
            return
        
        # Find oldest entry
        oldest_idx = 0
        oldest_time = datetime.fromisoformat(self.entries[0].created_at)
        
        for i, entry in enumerate(self.entries[1:], start=1):
            created_at = datetime.fromisoformat(entry.created_at)
            if created_at < oldest_time:
                oldest_time = created_at
                oldest_idx = i
        
        # Remove oldest entry and rebuild index
        entries_to_keep = [e for i, e in enumerate(self.entries) if i != oldest_idx]
        self._rebuild_index(entries_to_keep)
    
    def _rebuild_index(self, entries: List[CacheEntry]):
        """Rebuild FAISS index with specified entries"""
        # Create new index
        new_index = faiss.IndexFlatIP(self.embedding_dim)
        
        # Re-add entries
        for entry in entries:
            # Re-encode query (embeddings not stored in entries)
            embedding = self.embedder.encode(entry.query.query_text, convert_to_numpy=True)
            embedding = self._normalize_vector(embedding)
            new_index.add(embedding.reshape(1, -1).astype(np.float32))
        
        self.index = new_index
        self.entries = entries
        self._save_cache()
    
    def _save_cache(self):
        """Persist cache to disk"""
        try:
            # Save FAISS index
            faiss.write_index(self.index, str(self.index_path))
            
            # Save entries store
            if PANDAS_AVAILABLE and self.entries:
                # Convert entries to DataFrame
                records = []
                for entry in self.entries:
                    record = {
                        'entry_id': entry.entry_id,
                        'query_text': entry.query.query_text,
                        'query_hash': entry.query.query_hash,
                        'conversation_id': entry.query.conversation_id,
                        'task_id': entry.query.task_id,
                        'timestamp': entry.query.timestamp,
                        'response_text': entry.response.response_text,
                        'tools_used': json.dumps(entry.response.tools_used),
                        'usage': json.dumps(entry.response.usage),
                        'iterations': entry.response.iterations,
                        'metadata': json.dumps(entry.response.metadata),
                        'hit_count': entry.hit_count,
                        'last_hit': entry.last_hit,
                        'created_at': entry.created_at
                    }
                    records.append(record)
                
                df = pd.DataFrame(records)
                df.to_parquet(self.store_path, index=False)
        except Exception as e:
            print(f"⚠ Failed to save cache: {e}")
    
    def _update_hit_rate(self):
        """Update cache hit rate metric"""
        if self.metrics.total_queries > 0:
            self.metrics.hit_rate = self.metrics.cache_hits / self.metrics.total_queries
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get cache performance metrics"""
        return self.metrics.model_dump()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "total_entries": len(self.entries),
            "index_size": self.index.ntotal if self.index else 0,
            "similarity_threshold": self.similarity_threshold,
            "max_cache_size": self.max_cache_size,
            "ttl_hours": self.ttl_hours,
            "metrics": self.get_metrics()
        }


# Global singleton instance
_cache_manager: Optional[SemanticCacheManager] = None


def get_cache_manager() -> SemanticCacheManager:
    """Get global semantic cache manager instance"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = SemanticCacheManager()
    return _cache_manager


def init_cache_manager(**kwargs) -> SemanticCacheManager:
    """Initialize semantic cache manager with custom parameters"""
    global _cache_manager
    _cache_manager = SemanticCacheManager(**kwargs)
    return _cache_manager
