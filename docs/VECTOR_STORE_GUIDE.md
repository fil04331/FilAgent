# Vector Store & Document Ingestion Guide

## Overview

FilAgent includes a flexible vector store abstraction for semantic search and retrieval-augmented generation (RAG). This enables the agent to search through thousands of documents and inject relevant context into responses.

### Key Features

- **Abstract VectorStore Interface**: Swap backends without changing code
- **FAISS Backend**: Fast, local vector search (default)
- **ChromaDB Backend**: Persistent storage with metadata filtering (optional)
- **Document Ingestion**: Automatic chunking of PDF, DOCX, TXT files
- **Context Injection**: Seamless integration with agent prompts
- **Configurable Embeddings**: Support for multiple sentence-transformer models

## Architecture

```
┌─────────────────────────────────────────────────────┐
│              Agent (runtime/agent.py)               │
└────────────────────┬────────────────────────────────┘
                     │
        ┌────────────▼─────────────┐
        │  ContextBuilder          │
        │  inject_semantic_context()│
        └────────────┬──────────────┘
                     │
        ┌────────────▼──────────────┐
        │     VectorStore           │
        │  (Abstract Interface)     │
        └─────────┬─────────┬───────┘
                  │         │
       ┌──────────▼──┐  ┌──▼───────────┐
       │ FAISSVector │  │ ChromaDB     │
       │   Store     │  │ VectorStore  │
       └──────┬──────┘  └──┬───────────┘
              │            │
              ▼            ▼
        [FAISS Index]  [ChromaDB]
        [Parquet]      [Persistent]
```

## Configuration

Edit `config/agent.yaml`:

```yaml
memory:
  semantic:
    backend: "faiss"  # Options: "faiss" or "chromadb"
    embedding_model: "all-MiniLM-L6-v2"  # Default: 384 dimensions
    embedding_dim: 384  # Auto-detected if not specified
    chunk_size: 500  # Tokens per chunk for document ingestion
    chunk_overlap: 50  # Overlap between chunks
    top_k_retrieval: 3  # Number of chunks to retrieve for context
```

### Available Embedding Models

| Model | Dimensions | Speed | Quality | Use Case |
|-------|------------|-------|---------|----------|
| `all-MiniLM-L6-v2` | 384 | ⚡⚡⚡ | ⭐⭐ | Default, fast queries |
| `all-MiniLM-L12-v2` | 384 | ⚡⚡ | ⭐⭐⭐ | Balanced |
| `all-mpnet-base-v2` | 768 | ⚡ | ⭐⭐⭐⭐ | Best quality |
| `paraphrase-multilingual-mpnet-base-v2` | 768 | ⚡ | ⭐⭐⭐⭐ | Multilingual (FR/EN) |

## Usage

### 1. Basic Vector Store Operations

```python
from memory.semantic import init_semantic_memory

# Initialize FAISS backend
store = init_semantic_memory(backend="faiss")

# Add documents
documents = [
    "La Loi 25 au Québec protège les données personnelles.",
    "Les PME doivent implémenter des mesures de sécurité.",
]
metadatas = [
    {"source": "loi25_guide.pdf", "page": 1},
    {"source": "security_guide.pdf", "page": 5},
]

ids = store.add_documents(documents, metadatas=metadatas)

# Search
query = "Comment protéger les données?"
results = store.similarity_search(query, k=3)

for result in results:
    print(f"Score: {result['score']:.2f}")
    print(f"Text: {result['text']}")
    print(f"Source: {result['metadata']['source']}")

# Save
store.save()
```

### 2. Document Ingestion with Chunking

```python
from memory.ingestion import ingest_document, DocumentChunker

# Ingest PDF/DOCX/TXT with automatic chunking
chunks = ingest_document(
    "path/to/document.pdf",
    use_sentence_chunking=True,  # Preserve sentence boundaries
    metadata={"document_type": "contract", "year": 2024}
)

# Add to vector store
store = init_semantic_memory(backend="faiss")
texts = [chunk.text for chunk in chunks]
metadatas = [chunk.metadata for chunk in chunks]
ids = [chunk.chunk_id for chunk in chunks]

store.add_documents(texts, metadatas=metadatas, ids=ids)
```

### 3. Custom Chunking Strategy

```python
from memory.ingestion import DocumentChunker

# Create custom chunker
chunker = DocumentChunker(
    chunk_size=300,        # Smaller chunks for precise retrieval
    chunk_overlap=30,      # 10% overlap
    separator="\n\n",      # Split on paragraphs
    keep_separator=True    # Keep paragraph breaks
)

# Chunk text
text = open("document.txt").read()
chunks = chunker.chunk_text(text, source="document.txt")

# Or use sentence-aware chunking
chunks = chunker.chunk_by_sentences(text, source="document.txt")
```

### 4. Context Injection in Agent

```python
from runtime.context_builder import ContextBuilder
from memory.semantic import get_semantic_memory

# Setup
context_builder = ContextBuilder()
semantic_memory = get_semantic_memory()

# User query
user_query = "Quelles sont les obligations sous la Loi 25?"

# Inject relevant context
semantic_context = context_builder.inject_semantic_context(
    query=user_query,
    top_k=3,
    semantic_memory=semantic_memory
)

# Build system prompt with context
system_prompt = context_builder.build_system_prompt(
    tool_registry=tool_registry,
    semantic_context=semantic_context
)

# semantic_context is now part of system prompt
```

### 5. Using ChromaDB Backend

```python
# Install ChromaDB
# pip install chromadb

from memory.semantic import init_semantic_memory

# Initialize ChromaDB
store = init_semantic_memory(
    backend="chromadb",
    collection_name="filagent_documents",
    persist_directory="memory/semantic/chromadb"
)

# Add documents (same API as FAISS)
store.add_documents(documents, metadatas=metadatas)

# Search with metadata filtering
results = store.similarity_search(
    query="data privacy",
    k=5,
    filter={"source": "loi25_guide.pdf"}  # Only from this source
)

# ChromaDB auto-persists (no need to call save())
```

### 6. Advanced: Multiple Vector Stores

```python
# Separate stores for different domains
legal_store = init_semantic_memory(
    backend="faiss",
    index_path="memory/semantic/legal_index.faiss",
    store_path="memory/semantic/legal_store.parquet"
)

marketing_store = init_semantic_memory(
    backend="faiss",
    index_path="memory/semantic/marketing_index.faiss",
    store_path="memory/semantic/marketing_store.parquet"
)

# Populate with domain-specific documents
legal_store.add_documents(legal_docs)
marketing_store.add_documents(marketing_docs)

# Search relevant store based on query intent
if query_is_legal(query):
    results = legal_store.similarity_search(query)
else:
    results = marketing_store.similarity_search(query)
```

## API Reference

### VectorStore Interface

All vector store implementations support this interface:

```python
class VectorStore(ABC):
    def add_documents(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """Add documents to the vector store"""
        
    def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        
    def delete(self, ids: List[str]) -> bool:
        """Delete documents by IDs"""
        
    def count(self) -> int:
        """Get total number of documents"""
        
    def save(self) -> None:
        """Save vector store to disk"""
        
    def load(self) -> None:
        """Load vector store from disk"""
```

### DocumentChunker

```python
class DocumentChunker:
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separator: str = "\n\n",
        keep_separator: bool = True,
    ):
        """Initialize chunker with configuration"""
    
    def chunk_text(
        self,
        text: str,
        source: str = "unknown",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Chunk]:
        """Split text into chunks with overlap"""
    
    def chunk_by_sentences(
        self,
        text: str,
        source: str = "unknown",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Chunk]:
        """Split text at sentence boundaries"""
```

### DocumentLoader

```python
class DocumentLoader:
    @staticmethod
    def load_text(file_path: str) -> str:
        """Load plain text file"""
    
    @staticmethod
    def load_pdf(file_path: str) -> str:
        """Load PDF document (requires PyPDF2)"""
    
    @staticmethod
    def load_docx(file_path: str) -> str:
        """Load Word document (requires python-docx)"""
    
    @staticmethod
    def load_document(file_path: str) -> str:
        """Auto-detect format and load"""
```

## Performance Considerations

### FAISS Backend

**Pros:**
- Very fast search (sub-millisecond for < 10k documents)
- No external dependencies
- Works offline
- Lightweight

**Cons:**
- No built-in metadata filtering
- Requires explicit save/load
- Single-machine only

**Best for:**
- Development and testing
- < 100k documents
- Latency-critical applications
- Offline deployments

### ChromaDB Backend

**Pros:**
- Auto-persistence
- Metadata filtering
- Client-server architecture
- Better for large collections (> 100k docs)

**Cons:**
- Slower than FAISS for small collections
- Additional dependency
- More complex setup

**Best for:**
- Production deployments
- Large document collections
- Need metadata filtering
- Multi-user scenarios

### Chunking Strategy

**Token-based chunking:**
- Faster processing
- Predictable chunk sizes
- May split sentences

**Sentence-based chunking:**
- Preserves context
- Better retrieval quality
- Variable chunk sizes

**Recommendation:**
- Use sentence-based for narrative text (contracts, policies)
- Use token-based for structured data (tables, lists)

## Troubleshooting

### Import Errors

```python
# If you get "FAISS not installed"
pip install faiss-cpu  # or faiss-gpu

# If you get "sentence-transformers not installed"
pip install sentence-transformers

# If you get "chromadb not installed"
pip install chromadb
```

### Memory Issues

For very large document collections:
1. Use ChromaDB instead of FAISS
2. Reduce embedding dimensions (use all-MiniLM-L6-v2 instead of all-mpnet-base-v2)
3. Increase chunk size to reduce total chunks
4. Use batching for add_documents()

### Search Quality

If search results are poor:
1. Use larger embedding model (all-mpnet-base-v2)
2. Reduce chunk size for more precise retrieval
3. Increase chunk overlap
4. Use sentence-aware chunking
5. Adjust similarity threshold

## Examples

See `examples/vector_store_example.py` for complete working examples of:
- Basic FAISS usage
- Document ingestion pipeline
- Context injection
- ChromaDB backend
- Custom chunking strategies

## Migration from Old SemanticMemory

The old `SemanticMemory` class is now an alias for `FAISSVectorStore`. Legacy code using `add_passage()` and `search()` methods will continue to work.

**Old code:**
```python
from memory.semantic import SemanticMemory

memory = SemanticMemory()
memory.add_passage("text", conversation_id="123")
results = memory.search("query", top_k=5)
```

**New recommended code:**
```python
from memory.semantic import init_semantic_memory

store = init_semantic_memory(backend="faiss")
store.add_documents(["text"], [{"conversation_id": "123"}])
results = store.similarity_search("query", k=5)
```

## License & Compliance

- Vector stores respect PII redaction policies
- All searches are logged for audit trail (Loi 25 compliance)
- Document metadata preserved for provenance tracking
- Embedding models are open-source (Apache 2.0)

---

For questions or issues, see the main README or file an issue.
