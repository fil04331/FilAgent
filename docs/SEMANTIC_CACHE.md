# Semantic Cache Layer

## Overview

The Semantic Cache Layer is a performance optimization feature that reduces API inference costs and perceived latency by caching query-response pairs and using semantic similarity to retrieve cached responses for similar queries.

## Features

- **Semantic Similarity Matching**: Uses FAISS for efficient vector similarity search with cosine similarity
- **Persistent Storage**: Cache is stored on disk using FAISS index + Parquet for durability
- **Configurable Thresholds**: Default similarity threshold of 0.9 (can be overridden)
- **Automatic Invalidation**: TTL-based expiration and manual invalidation support
- **Metrics Tracking**: Tracks hit rate, miss rate, and average similarity scores
- **Transparent Fallback**: Automatically falls back to normal execution on cache miss

## Architecture

```
User Query
    ↓
Semantic Cache Check (FAISS similarity search)
    ↓
├─→ Cache Hit (similarity ≥ 0.9)
│       ↓
│   Return Cached Response
│       ↓
│   Update hit count & metrics
│
└─→ Cache Miss (similarity < 0.9 or empty)
        ↓
    Execute Query Normally (Agent + LLM)
        ↓
    Store Response in Cache
        ↓
    Return Response
```

## Configuration

The cache manager can be configured at initialization:

```python
from memory.cache_manager import init_cache_manager

cache = init_cache_manager(
    index_path="memory/semantic/cache_index.faiss",
    store_path="memory/semantic/cache_store.parquet",
    model_name="all-MiniLM-L6-v2",  # Sentence transformer model
    similarity_threshold=0.9,  # Minimum similarity for cache hit
    max_cache_size=1000,  # Maximum entries in cache
    ttl_hours=24  # Time-to-live for entries
)
```

## Usage

### Automatic (Agent Integration)

The cache is automatically integrated into the Agent's `chat()` method:

```python
from runtime.agent import Agent

agent = Agent()
agent.initialize_model()

# First query - cache miss, executes normally
response1 = agent.chat("What is Python?", "conv_123")

# Similar query - cache hit, returns cached response
response2 = agent.chat("What's Python?", "conv_123")
# response2['cache_hit'] == True
# response2['cache_metadata']['similarity_score'] ≈ 0.95
```

### Manual Cache Management

```python
from memory.cache_manager import get_cache_manager

cache = get_cache_manager()

# Store a response
cache.store(
    query="What is the capital of France?",
    response_text="The capital of France is Paris.",
    conversation_id="conv_123",
    tools_used=["search"],
    usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
)

# Retrieve cached response
result = cache.get("What's France's capital?")
if result:
    print(f"Cached response: {result['response']['response_text']}")
    print(f"Similarity: {result['similarity_score']:.3f}")
    print(f"Hit count: {result['hit_count']}")
else:
    print("Cache miss")

# Get cache metrics
metrics = cache.get_metrics()
print(f"Hit rate: {metrics['hit_rate']:.2%}")
print(f"Cache hits: {metrics['cache_hits']}")
print(f"Cache misses: {metrics['cache_misses']}")

# Get cache statistics
stats = cache.get_stats()
print(f"Total entries: {stats['total_entries']}")
print(f"Index size: {stats['index_size']}")
```

### Cache Invalidation

```python
cache = get_cache_manager()

# Invalidate entries older than 12 hours
removed = cache.invalidate_by_age(max_age_hours=12)
print(f"Removed {removed} old entries")

# Clear all cache entries
cache.invalidate_all()
```

## Performance Benefits

### Latency Reduction

- **Cache Hit**: ~10-50ms (embedding + FAISS search)
- **Cache Miss**: Normal agent execution time (1-5 seconds)
- **Speedup**: 20-100x faster for cache hits

### Cost Savings

- **Cache Hit**: Zero LLM API calls
- **Typical Hit Rate**: 30-50% for conversational workloads
- **Monthly Savings**: Potentially 30-50% reduction in API costs

### Example Metrics

For a system with 1000 queries/day:
- Hit rate: 40%
- Cache hits: 400 queries/day
- LLM calls saved: 400/day = 12,000/month
- Cost savings: ~$60-120/month (depending on model pricing)

## Implementation Details

### Embedding Model

Default: `all-MiniLM-L6-v2` (sentence-transformers)
- Embedding dimension: 384
- Fast inference: ~10ms per query
- Good balance of speed and quality

### Similarity Metric

Uses cosine similarity via FAISS IndexFlatIP:
- Vectors are L2-normalized before indexing
- Inner product equals cosine similarity for normalized vectors
- Threshold: 0.9 (highly similar queries)

### Storage Format

- **FAISS Index**: Binary format, ~1.5KB per entry (384D float32)
- **Parquet Store**: Compressed columnar format, ~500 bytes per entry
- **Total**: ~2KB per cached query-response pair

### Cache Eviction

LRU (Least Recently Used) by creation time:
- When cache reaches `max_cache_size`, oldest entry is evicted
- Eviction triggers index rebuild (expensive, avoid frequent evictions)
- Recommendation: Set `max_cache_size` large enough to avoid evictions

## Dependencies

Required packages (already in `pyproject.toml`):
- `faiss-cpu>=1.8.0` (or `faiss-gpu` for GPU acceleration)
- `sentence-transformers>=2.2.2`
- `pandas>=2.3.3` (for Parquet storage)
- `pyarrow>=17.0.0` (Parquet backend)
- `pydantic>=2.6.0` (data validation)
- `numpy>=1.24.0`

## Monitoring

### Cache Metrics

The cache manager tracks:
- `total_queries`: Total queries processed
- `cache_hits`: Number of cache hits
- `cache_misses`: Number of cache misses
- `hit_rate`: Ratio of hits to total queries (0.0-1.0)
- `avg_similarity_on_hit`: Average similarity score for cache hits

### Response Metadata

Cached responses include metadata:
```json
{
  "response": "...",
  "cache_hit": true,
  "cache_metadata": {
    "similarity_score": 0.95,
    "hit_count": 3,
    "age_hours": 2.5,
    "entry_id": "cache:abc123:1234567890.0"
  }
}
```

## Best Practices

### 1. Set Appropriate Threshold

- **Higher threshold (0.95)**: More conservative, fewer false positives
- **Lower threshold (0.85)**: More aggressive, higher hit rate but risk of irrelevant responses
- **Default (0.9)**: Good balance for most use cases

### 2. Monitor Hit Rate

- Target: 30-50% hit rate for conversational workloads
- If hit rate is low (<10%), consider:
  - Lowering similarity threshold
  - Increasing TTL
  - Pre-populating cache with common queries

### 3. Manage Cache Size

- Set `max_cache_size` based on available disk space
- 1000 entries ≈ 2MB disk space
- Evictions trigger index rebuild (slow)
- Consider periodic cleanup instead of relying on eviction

### 4. TTL Configuration

- Short TTL (1-6 hours): For rapidly changing data
- Medium TTL (24 hours): Default, good for most use cases
- Long TTL (7 days): For stable knowledge bases

### 5. Manual Invalidation

Invalidate cache when:
- Tools are updated or changed
- System prompts are modified
- New features are deployed
- Data sources are refreshed

```python
# After system update
cache = get_cache_manager()
cache.invalidate_all()
```

## Limitations

1. **Semantic Similarity Threshold**: Not perfect - some similar queries may be semantically different in intent
2. **Context Ignorance**: Cache doesn't consider conversation context (same query in different contexts returns same response)
3. **Storage Overhead**: ~2KB per entry, can accumulate over time
4. **Cold Start**: First query always misses cache
5. **Embedding Cost**: ~10ms per query for embedding generation

## Future Enhancements

Potential improvements for Phase 3:
- Context-aware caching (consider conversation history)
- Multi-level cache (L1: in-memory, L2: disk)
- Distributed cache for multi-node deployments
- Semantic clustering for improved search
- Automatic threshold tuning based on feedback
- Cache warming from historical queries

## Troubleshooting

### Cache Always Misses

1. Check if FAISS and sentence-transformers are installed
2. Verify cache files exist: `ls -la memory/semantic/cache_*`
3. Check similarity scores: Lower threshold temporarily to debug
4. Inspect metrics: `cache.get_metrics()`

### High Memory Usage

1. Reduce `max_cache_size`
2. Decrease TTL to expire entries faster
3. Run periodic cleanup: `cache.invalidate_by_age()`

### Slow Performance

1. Use GPU acceleration: Install `faiss-gpu` instead of `faiss-cpu`
2. Use smaller embedding model (trade quality for speed)
3. Reduce index size by lowering `max_cache_size`

## References

- [FAISS Documentation](https://github.com/facebookresearch/faiss/wiki)
- [Sentence Transformers](https://www.sbert.net/)
- [Semantic Caching Paper](https://arxiv.org/abs/2304.01191)

## License

This implementation is part of FilAgent and follows the same license as the main project.
