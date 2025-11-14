# Semantic Memory Tests Documentation

## Overview

Comprehensive test suite for `memory/semantic.py` covering FAISS indexing, semantic search, and memory management.

## Test Coverage

### Total Tests: 34
### Total Fixtures: 4

## Test Categories

### 1. Initialization Tests (3 tests)
- `test_semantic_memory_initialization` - Verify basic SemanticMemory initialization
- `test_semantic_memory_missing_dependencies` - Handle missing FAISS/sentence-transformers
- `test_create_empty_index` - Create empty FAISS index

### 2. Adding Passages Tests (4 tests)
- `test_add_passage_basic` - Add single passage with embedding generation
- `test_add_passage_with_metadata` - Add passage with conversation_id, task_id, metadata
- `test_add_passage_unique_id` - Verify passage IDs are content-based hashes
- `test_add_multiple_passages` - Add multiple passages sequentially

### 3. Semantic Search Tests (7 tests)
- `test_search_basic` - Basic semantic search with top_k
- `test_search_empty_index` - Search on empty index returns []
- `test_search_with_similarity_threshold` - Filter by similarity threshold
- `test_search_top_k_limit` - Respect top_k parameter
- `test_search_score_calculation` - Validate similarity scores (0.0-1.0)
- `test_search_ranking` - Verify results are properly ranked
- `test_search_with_zero_top_k` - Handle edge case of top_k=0

### 4. Index Persistence Tests (5 tests)
- `test_save_index` - Save FAISS index and store to disk
- `test_save_empty_index` - Save empty index without errors
- `test_load_index_existing` - Load existing index from disk
- `test_load_index_error_fallback` - Fallback to empty index on load error
- `test_rebuild_index` - Rebuild FAISS index from store
- `test_rebuild_index_empty_store` - Handle rebuild with empty store

### 5. Cleanup/LRU Eviction Tests (5 tests)
- `test_cleanup_old_passages` - Remove passages older than TTL
- `test_cleanup_no_old_passages` - Cleanup when no passages are old
- `test_cleanup_all_old` - Cleanup when all passages exceed TTL
- `test_cleanup_rebuilds_index` - Verify index is rebuilt after cleanup
- `test_cleanup_with_invalid_timestamp` - Handle invalid timestamps

### 6. Singleton Pattern Tests (2 tests)
- `test_get_semantic_memory_singleton` - Verify singleton behavior
- `test_init_semantic_memory` - Initialize with custom parameters

### 7. Integration Tests (3 tests)
- `test_full_workflow` - Complete workflow: add, search, save, load
- `test_passage_lifecycle` - Full lifecycle: add, search, cleanup
- `test_concurrent_operations` - Handle multiple operations in sequence

### 8. Edge Cases Tests (5 tests)
- `test_empty_text_passage` - Handle empty string passages
- `test_very_long_passage` - Handle very long text (1000+ words)
- `test_special_characters_in_passage` - Handle special characters
- `test_unicode_in_passage` - Handle Unicode (French, Chinese, Arabic, emojis)
- `test_search_with_zero_top_k` - Edge case for search parameters

## Fixtures

### 1. `mock_faiss_index`
Mock FAISS index with:
- `ntotal` tracking
- `add()` simulation
- `search()` returning mock distances/indices

### 2. `mock_embedder`
Mock SentenceTransformer with:
- 384-dimensional embeddings
- `encode()` returning random embeddings
- `get_sentence_embedding_dimension()` method

### 3. `temp_semantic_paths`
Temporary paths for isolated testing:
- `index_path` - Temporary FAISS index path
- `store_path` - Temporary parquet store path
- `semantic_dir` - Base directory

### 4. `semantic_memory_instance`
Fully configured SemanticMemory instance with mocked dependencies

## Running the Tests

### Prerequisites
```bash
pip install pytest numpy pandas faiss-cpu sentence-transformers
```

### Run All Semantic Memory Tests
```bash
pytest tests/test_semantic_memory.py -v
```

### Run Specific Test Categories
```bash
# Unit tests only
pytest tests/test_semantic_memory.py -v -m unit

# Integration tests only
pytest tests/test_semantic_memory.py -v -m integration

# Specific test
pytest tests/test_semantic_memory.py::test_add_passage_basic -v
```

### Run with Coverage
```bash
pytest tests/test_semantic_memory.py --cov=memory.semantic --cov-report=html
```

## Expected Coverage

Target: **70%+** code coverage for `memory/semantic.py`

### Coverage Areas:
- ✅ Initialization and setup
- ✅ FAISS index creation/updates
- ✅ Embedding generation
- ✅ Semantic search queries
- ✅ Similarity scoring
- ✅ Index persistence (save/load)
- ✅ LRU eviction/cleanup
- ✅ Singleton pattern
- ✅ Error handling
- ✅ Edge cases

## Test Architecture

### Mocking Strategy
Tests use comprehensive mocking to avoid external dependencies:
- **FAISS**: Mocked at module level to avoid binary dependencies
- **SentenceTransformer**: Mocked embedder with deterministic behavior
- **Pandas**: Real pandas for parquet operations
- **NumPy**: Real numpy for array operations

### Isolation
Each test is fully isolated:
- Temporary file paths per test
- Fresh SemanticMemory instance per test
- No shared state between tests

### Markers
- `@pytest.mark.unit` - Fast, isolated unit tests
- `@pytest.mark.integration` - Integration scenarios

## Notes

1. **Module-level mocking**: FAISS and sentence-transformers are mocked at module level before import
2. **No external models**: Tests don't download actual sentence-transformer models
3. **Deterministic**: Random embeddings are seeded for reproducibility
4. **Fast execution**: All tests run in < 5 seconds total

## Troubleshooting

### ImportError: No module named 'faiss'
This is expected - tests mock FAISS to avoid binary dependencies.

### ImportError: No module named 'sentence_transformers'
This is expected - tests mock SentenceTransformer.

### Tests won't collect
Ensure pytest can import the test file:
```bash
python -c "import tests.test_semantic_memory"
```

## Contributing

When adding new tests:
1. Follow existing naming conventions (`test_<function>_<scenario>`)
2. Add appropriate markers (`@pytest.mark.unit` or `@pytest.mark.integration`)
3. Use existing fixtures when possible
4. Document complex test scenarios
5. Ensure tests are isolated and don't depend on execution order

## Maintenance

- **Last Updated**: 2025-11-14
- **Maintainer**: FilAgent Team
- **Related Files**:
  - `memory/semantic.py` - Implementation
  - `tests/conftest.py` - Shared fixtures
  - `pytest.ini` - Pytest configuration
