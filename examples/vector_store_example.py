"""
Example: Using Vector Store for Document Search

This example demonstrates:
1. Initializing different vector store backends (FAISS, ChromaDB)
2. Ingesting documents with chunking
3. Performing semantic search
4. Using semantic context in agent responses
"""

from memory.semantic import init_semantic_memory, FAISSVectorStore, ChromaDBVectorStore
from memory.ingestion import ingest_document, DocumentChunker
from runtime.context_builder import ContextBuilder
import tempfile
from pathlib import Path


def example_1_basic_faiss():
    """Example 1: Basic FAISS vector store usage"""
    print("\n=== Example 1: Basic FAISS Vector Store ===\n")
    
    # Initialize FAISS vector store
    store = init_semantic_memory(
        backend="faiss",
        index_path="memory/semantic/demo_index.faiss",
        store_path="memory/semantic/demo_store.parquet",
        model_name="all-MiniLM-L6-v2"  # 384 dimensions, fast
    )
    
    # Add documents
    documents = [
        "La Loi 25 au Québec exige la protection des renseignements personnels.",
        "Les PME québécoises doivent se conformer aux normes de confidentialité.",
        "Le RGPD européen a inspiré plusieurs lois canadiennes sur la vie privée.",
        "FilAgent aide les propriétaires de PME à naviguer dans la conformité réglementaire.",
    ]
    
    metadatas = [
        {"source": "loi25_guide.pdf", "page": 1},
        {"source": "pme_conformite.pdf", "page": 3},
        {"source": "rgpd_comparison.pdf", "page": 5},
        {"source": "filagent_docs.pdf", "page": 1},
    ]
    
    ids = store.add_documents(documents, metadatas=metadatas)
    print(f"Added {len(ids)} documents to vector store")
    
    # Perform semantic search
    query = "Comment protéger les données personnelles au Québec?"
    results = store.similarity_search(query, k=3)
    
    print(f"\nSearch results for: '{query}'\n")
    for i, result in enumerate(results, 1):
        print(f"{i}. Score: {result['score']:.3f}")
        print(f"   Text: {result['text']}")
        print(f"   Source: {result['metadata'].get('source', 'unknown')}")
        print()
    
    # Save for later use
    store.save()
    print("Vector store saved!")
    
    return store


def example_2_document_ingestion():
    """Example 2: Ingest and chunk a document"""
    print("\n=== Example 2: Document Ingestion with Chunking ===\n")
    
    # Create a temporary document
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        content = """FilAgent est un assistant IA conçu pour les PME québécoises.
        
Il aide les entrepreneurs à gérer leurs opérations quotidiennes, 
notamment en matière de conformité réglementaire, marketing digital,
et gestion des ressources humaines.

FilAgent utilise des modèles de langage avancés pour fournir des réponses
contextuelles et pertinentes au marché québécois.

Les fonctionnalités incluent:
- Analyse de documents
- Calculs TPS/TVQ automatiques
- Recommandations de conformité Loi 25
- Conseils en marketing local
        """
        f.write(content)
        temp_path = f.name
    
    try:
        # Ingest document with sentence-aware chunking
        chunks = ingest_document(
            temp_path,
            use_sentence_chunking=True,
            metadata={"document_type": "product_description"}
        )
        
        print(f"Document split into {len(chunks)} chunks:\n")
        for i, chunk in enumerate(chunks, 1):
            print(f"Chunk {i}:")
            print(f"  Text: {chunk.text[:100]}...")
            print(f"  Tokens (estimated): {len(chunk.text) // 4}")
            print()
        
        # Add chunks to vector store
        store = init_semantic_memory(backend="faiss")
        texts = [chunk.text for chunk in chunks]
        metadatas = [chunk.metadata for chunk in chunks]
        ids = [chunk.chunk_id for chunk in chunks]
        
        store.add_documents(texts, metadatas=metadatas, ids=ids)
        print(f"All {len(chunks)} chunks added to vector store")
        
        # Test search
        query = "Quelles sont les fonctionnalités de FilAgent?"
        results = store.similarity_search(query, k=2)
        
        print(f"\nSearch results for: '{query}'\n")
        for result in results:
            print(f"- {result['text'][:150]}...")
            print(f"  Score: {result['score']:.3f}\n")
            
    finally:
        Path(temp_path).unlink()


def example_3_context_injection():
    """Example 3: Use semantic context in agent prompts"""
    print("\n=== Example 3: Context Injection for Agent ===\n")
    
    # Setup vector store with business knowledge
    store = init_semantic_memory(backend="faiss")
    
    knowledge_base = [
        "Pour démarrer une entreprise au Québec, vous devez vous inscrire au Registre des entreprises (REQ).",
        "Les subventions gouvernementales québécoises incluent le Programme de soutien aux entreprises (PSE).",
        "La conformité Loi 25 exige une évaluation des facteurs relatifs à la vie privée (ÉFVP).",
        "Le marketing numérique efficace au Québec doit tenir compte du bilinguisme français-anglais.",
    ]
    
    store.add_documents(knowledge_base)
    
    # Initialize context builder
    context_builder = ContextBuilder()
    
    # User query
    user_query = "Comment obtenir du financement gouvernemental pour ma PME?"
    
    # Inject semantic context
    semantic_context = context_builder.inject_semantic_context(
        query=user_query,
        top_k=2,
        semantic_memory=store
    )
    
    print(f"User query: {user_query}\n")
    print("Injected semantic context:")
    print(semantic_context)
    print("\n---")
    print("This context would be added to the system prompt to provide")
    print("the agent with relevant background knowledge.")


def example_4_chromadb():
    """Example 4: Using ChromaDB backend (optional)"""
    print("\n=== Example 4: ChromaDB Vector Store (Optional) ===\n")
    
    try:
        # Try to use ChromaDB
        store = init_semantic_memory(
            backend="chromadb",
            collection_name="filagent_demo",
            persist_directory="memory/semantic/chromadb_demo"
        )
        
        # Add documents
        documents = [
            "ChromaDB provides persistent vector storage.",
            "It has built-in metadata filtering capabilities.",
            "ChromaDB is ideal for production deployments.",
        ]
        
        store.add_documents(documents)
        print(f"Added {store.count()} documents to ChromaDB")
        
        # Search with metadata filter
        results = store.similarity_search("persistent storage", k=2)
        print(f"\nFound {len(results)} relevant documents")
        
        for result in results:
            print(f"- {result['text']} (score: {result['score']:.3f})")
        
    except ImportError:
        print("ChromaDB not installed. Install with: pip install chromadb")
        print("Falling back to FAISS...")


def example_5_custom_chunking():
    """Example 5: Custom chunking strategies"""
    print("\n=== Example 5: Custom Document Chunking ===\n")
    
    # Create custom chunker with specific parameters
    small_chunker = DocumentChunker(
        chunk_size=100,  # Smaller chunks
        chunk_overlap=20,  # More overlap
        separator="\n\n",
        keep_separator=True
    )
    
    large_chunker = DocumentChunker(
        chunk_size=1000,  # Larger chunks
        chunk_overlap=100,
        separator="\n",
        keep_separator=False
    )
    
    text = """
Paragraph 1: Introduction to the topic.
This is the first section explaining key concepts.

Paragraph 2: Detailed analysis.
Here we dive deeper into the subject matter.

Paragraph 3: Conclusions and recommendations.
Final thoughts and actionable insights.
    """.strip()
    
    small_chunks = small_chunker.chunk_text(text, source="demo.txt")
    large_chunks = large_chunker.chunk_text(text, source="demo.txt")
    
    print(f"Small chunker (size=100): {len(small_chunks)} chunks")
    print(f"Large chunker (size=1000): {len(large_chunks)} chunks")
    
    print("\nSmall chunks:")
    for i, chunk in enumerate(small_chunks, 1):
        print(f"  {i}. {chunk.text[:80]}...")
    
    print("\nLarge chunks:")
    for i, chunk in enumerate(large_chunks, 1):
        print(f"  {i}. {chunk.text[:80]}...")


def main():
    """Run all examples"""
    print("=" * 70)
    print("FILAGENT VECTOR STORE EXAMPLES")
    print("=" * 70)
    
    # Run examples
    example_1_basic_faiss()
    example_2_document_ingestion()
    example_3_context_injection()
    example_4_chromadb()
    example_5_custom_chunking()
    
    print("\n" + "=" * 70)
    print("All examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
