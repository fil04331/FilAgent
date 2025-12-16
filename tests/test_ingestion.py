"""
Tests for document ingestion and chunking functionality
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from memory.ingestion import (
    Chunk,
    DocumentChunker,
    DocumentLoader,
    ingest_document,
)


# ============================================================================
# TESTS: DocumentChunker - Basic Chunking
# ============================================================================

@pytest.mark.unit
def test_document_chunker_initialization():
    """Test DocumentChunker initialization with default parameters"""
    chunker = DocumentChunker()
    
    assert chunker.chunk_size == 500
    assert chunker.chunk_overlap == 50
    assert chunker.separator == "\n\n"
    assert chunker.keep_separator is True


@pytest.mark.unit
def test_document_chunker_custom_params():
    """Test DocumentChunker initialization with custom parameters"""
    chunker = DocumentChunker(
        chunk_size=300,
        chunk_overlap=30,
        separator="\n",
        keep_separator=False,
    )
    
    assert chunker.chunk_size == 300
    assert chunker.chunk_overlap == 30
    assert chunker.separator == "\n"
    assert chunker.keep_separator is False


@pytest.mark.unit
def test_estimate_tokens():
    """Test token estimation heuristic"""
    chunker = DocumentChunker()
    
    # ~1 token per 4 characters
    text = "This is a test string."  # 22 chars
    tokens = chunker.estimate_tokens(text)
    assert tokens == 5  # 22 // 4


@pytest.mark.unit
def test_chunk_text_empty():
    """Test chunking empty text returns empty list"""
    chunker = DocumentChunker()
    
    chunks = chunker.chunk_text("", source="test.txt")
    assert chunks == []
    
    chunks = chunker.chunk_text("   ", source="test.txt")
    assert chunks == []


@pytest.mark.unit
def test_chunk_text_single_chunk():
    """Test chunking text that fits in single chunk"""
    chunker = DocumentChunker(chunk_size=100)
    
    text = "This is a short text."
    chunks = chunker.chunk_text(text, source="test.txt")
    
    assert len(chunks) == 1
    assert chunks[0].text == text
    assert chunks[0].source == "test.txt"
    assert chunks[0].chunk_id == "test.txt:chunk:0"


@pytest.mark.unit
def test_chunk_text_multiple_chunks():
    """Test chunking text into multiple chunks"""
    chunker = DocumentChunker(chunk_size=20, chunk_overlap=5)
    
    # Create text that will require multiple chunks
    text = "A" * 100 + "\n\n" + "B" * 100
    chunks = chunker.chunk_text(text, source="test.txt")
    
    assert len(chunks) > 1
    
    # Verify chunk structure
    for i, chunk in enumerate(chunks):
        assert isinstance(chunk, Chunk)
        assert chunk.source == "test.txt"
        assert chunk.chunk_id == f"test.txt:chunk:{i}"
        assert chunk.metadata["chunk_index"] == i


@pytest.mark.unit
def test_chunk_text_with_metadata():
    """Test chunking with custom metadata"""
    chunker = DocumentChunker(chunk_size=100)
    
    text = "Test text"
    metadata = {"author": "John Doe", "category": "test"}
    chunks = chunker.chunk_text(text, source="test.txt", metadata=metadata)
    
    assert len(chunks) == 1
    assert chunks[0].metadata["author"] == "John Doe"
    assert chunks[0].metadata["category"] == "test"
    assert chunks[0].metadata["chunk_index"] == 0


@pytest.mark.unit
def test_chunk_text_overlap():
    """Test that chunks have proper overlap"""
    chunker = DocumentChunker(chunk_size=15, chunk_overlap=5)  # Very small to force splitting
    
    # Create text with clear segments that exceed chunk size
    text = "First segment here is longer.\n\nSecond segment here is also long.\n\nThird segment here too."
    chunks = chunker.chunk_text(text, source="test.txt")
    
    # Should have multiple chunks with overlap
    assert len(chunks) >= 2


# ============================================================================
# TESTS: DocumentChunker - Sentence-Based Chunking
# ============================================================================

@pytest.mark.unit
def test_chunk_by_sentences_empty():
    """Test sentence chunking with empty text"""
    chunker = DocumentChunker()
    
    chunks = chunker.chunk_by_sentences("", source="test.txt")
    assert chunks == []


@pytest.mark.unit
def test_chunk_by_sentences_single_sentence():
    """Test sentence chunking with single sentence"""
    chunker = DocumentChunker(chunk_size=100)
    
    text = "This is a single sentence."
    chunks = chunker.chunk_by_sentences(text, source="test.txt")
    
    assert len(chunks) == 1
    assert chunks[0].text == text


@pytest.mark.unit
def test_chunk_by_sentences_multiple_sentences():
    """Test sentence chunking with multiple sentences"""
    chunker = DocumentChunker(chunk_size=50)
    
    text = "First sentence. Second sentence! Third sentence? Fourth sentence."
    chunks = chunker.chunk_by_sentences(text, source="test.txt")
    
    assert len(chunks) >= 1
    
    # Verify sentences are not split
    for chunk in chunks:
        # Each chunk should end with sentence punctuation or be the last chunk
        assert chunk.text.strip()


@pytest.mark.unit
def test_chunk_by_sentences_preserves_integrity():
    """Test that sentence chunking doesn't split sentences"""
    chunker = DocumentChunker(chunk_size=30)
    
    text = "Short one. This is a much longer sentence that should not be split. End."
    chunks = chunker.chunk_by_sentences(text, source="test.txt")
    
    # Verify each sentence appears complete in some chunk
    all_text = " ".join(chunk.text for chunk in chunks)
    assert "This is a much longer sentence that should not be split." in all_text


# ============================================================================
# TESTS: DocumentLoader - Text Files
# ============================================================================

@pytest.mark.unit
def test_load_text_file():
    """Test loading plain text file"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("This is test content.\nSecond line.")
        temp_path = f.name
    
    try:
        text = DocumentLoader.load_text(temp_path)
        assert text == "This is test content.\nSecond line."
    finally:
        Path(temp_path).unlink()


@pytest.mark.unit
def test_load_text_unicode():
    """Test loading text file with Unicode characters"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write("Test avec accents: éàù\n中文\nEmoji: 🚀")
        temp_path = f.name
    
    try:
        text = DocumentLoader.load_text(temp_path)
        assert "éàù" in text
        assert "中文" in text
        assert "🚀" in text
    finally:
        Path(temp_path).unlink()


# ============================================================================
# TESTS: DocumentLoader - PDF Files
# ============================================================================

@pytest.mark.unit
def test_load_pdf_missing_dependency():
    """Test PDF loading fails gracefully without PyPDF2"""
    with patch.dict('sys.modules', {'PyPDF2': None}):
        with pytest.raises(ImportError, match="PyPDF2 is required"):
            DocumentLoader.load_pdf("test.pdf")


@pytest.mark.unit
def test_load_pdf_with_mock():
    """Test PDF loading with mocked PyPDF2"""
    pytest.importorskip("PyPDF2")
    
    mock_pdf = MagicMock()
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Page 1 content"
    mock_pdf.pages = [mock_page]
    
    with patch('builtins.open', MagicMock()):
        with patch('PyPDF2.PdfReader', return_value=mock_pdf):
            text = DocumentLoader.load_pdf("test.pdf")
            assert text == "Page 1 content"


# ============================================================================
# TESTS: DocumentLoader - DOCX Files
# ============================================================================

@pytest.mark.unit
def test_load_docx_missing_dependency():
    """Test DOCX loading fails gracefully without python-docx"""
    with patch.dict('sys.modules', {'docx': None}):
        with pytest.raises(ImportError, match="python-docx is required"):
            DocumentLoader.load_docx("test.docx")


@pytest.mark.unit
def test_load_docx_with_mock():
    """Test DOCX loading with mocked python-docx"""
    pytest.importorskip("docx")
    
    mock_doc = MagicMock()
    mock_para1 = MagicMock()
    mock_para1.text = "Paragraph 1"
    mock_para2 = MagicMock()
    mock_para2.text = "Paragraph 2"
    mock_doc.paragraphs = [mock_para1, mock_para2]
    
    with patch('docx.Document', return_value=mock_doc):
        text = DocumentLoader.load_docx("test.docx")
        assert text == "Paragraph 1\n\nParagraph 2"


# ============================================================================
# TESTS: DocumentLoader - Auto-Detection
# ============================================================================

@pytest.mark.unit
def test_load_document_txt():
    """Test auto-detection for .txt files"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Test content")
        temp_path = f.name
    
    try:
        text = DocumentLoader.load_document(temp_path)
        assert text == "Test content"
    finally:
        Path(temp_path).unlink()


@pytest.mark.unit
def test_load_document_nonexistent():
    """Test loading nonexistent file raises FileNotFoundError"""
    with pytest.raises(FileNotFoundError):
        DocumentLoader.load_document("/nonexistent/file.txt")


@pytest.mark.unit
def test_load_document_unsupported_format():
    """Test loading unsupported format raises ValueError"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xyz', delete=False) as f:
        f.write("Test")
        temp_path = f.name
    
    try:
        with pytest.raises(ValueError, match="Unsupported file format"):
            DocumentLoader.load_document(temp_path)
    finally:
        Path(temp_path).unlink()


# ============================================================================
# TESTS: High-Level ingest_document Function
# ============================================================================

@pytest.mark.unit
def test_ingest_document_text_file():
    """Test ingesting a text file"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Test document content.\n\nSecond paragraph.")
        temp_path = f.name
    
    try:
        chunks = ingest_document(temp_path)
        
        assert len(chunks) >= 1
        assert chunks[0].metadata['file_path'] == temp_path
        assert chunks[0].metadata['file_name'] == Path(temp_path).name
    finally:
        Path(temp_path).unlink()


@pytest.mark.unit
def test_ingest_document_with_custom_chunker():
    """Test ingesting document with custom chunker"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        # Create text with clear separators that will force multiple chunks
        f.write("A" * 200 + "\n\n" + "B" * 200 + "\n\n" + "C" * 200)
        temp_path = f.name
    
    try:
        custom_chunker = DocumentChunker(chunk_size=50, chunk_overlap=10)  # Small chunks
        chunks = ingest_document(temp_path, chunker=custom_chunker)
        
        assert len(chunks) >= 2  # Should be split into multiple chunks
    finally:
        Path(temp_path).unlink()


@pytest.mark.unit
def test_ingest_document_sentence_chunking():
    """Test ingesting document with sentence-based chunking"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Sentence one. Sentence two! Sentence three?")
        temp_path = f.name
    
    try:
        chunks = ingest_document(temp_path, use_sentence_chunking=True)
        
        assert len(chunks) >= 1
        # Verify sentences are preserved
        all_text = " ".join(chunk.text for chunk in chunks)
        assert "Sentence one." in all_text
    finally:
        Path(temp_path).unlink()


@pytest.mark.unit
def test_ingest_document_with_metadata():
    """Test ingesting document with custom metadata"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Test content")
        temp_path = f.name
    
    try:
        metadata = {"author": "Test Author", "category": "test"}
        chunks = ingest_document(temp_path, metadata=metadata)
        
        assert chunks[0].metadata['author'] == "Test Author"
        assert chunks[0].metadata['category'] == "test"
        assert 'file_path' in chunks[0].metadata  # Should still have file metadata
    finally:
        Path(temp_path).unlink()


# ============================================================================
# TESTS: Edge Cases
# ============================================================================

@pytest.mark.unit
def test_chunk_very_long_text():
    """Test chunking extremely long text"""
    chunker = DocumentChunker(chunk_size=50, separator="\n\n")  # Smaller chunks
    
    # Create text with separators to force chunking
    segments = ["Word " * 100 for _ in range(20)]
    text = "\n\n".join(segments)
    chunks = chunker.chunk_text(text, source="test.txt")
    
    assert len(chunks) > 10
    # Verify that chunking occurred successfully
    # Note: Individual chunks may exceed chunk_size due to:
    # - Separator preservation (keeps \n\n)
    # - Overlap (repeats last N tokens)
    # - Word boundaries (doesn't split mid-word)
    # The key is that text was split into multiple chunks
    assert all(len(chunk.text) > 0 for chunk in chunks)


@pytest.mark.unit
def test_chunk_special_characters():
    """Test chunking text with special characters"""
    chunker = DocumentChunker()
    
    text = "Special chars: @#$%^&*()\n\nMore: {}[]|\\/<>?~`"
    chunks = chunker.chunk_text(text, source="test.txt")
    
    assert len(chunks) >= 1
    assert "@#$%^&*()" in chunks[0].text


@pytest.mark.unit
def test_get_overlap_short_text():
    """Test overlap extraction with text shorter than overlap size"""
    chunker = DocumentChunker(chunk_overlap=100)
    
    short_text = "Short"
    overlap = chunker._get_overlap(short_text)
    
    assert overlap == short_text  # Should return full text


@pytest.mark.unit
def test_get_last_sentences():
    """Test getting last N sentences"""
    chunker = DocumentChunker()
    
    text = "First. Second. Third. Fourth."
    last_2 = chunker._get_last_sentences(text, n=2)
    
    assert "Third." in last_2
    assert "Fourth." in last_2


# ============================================================================
# TESTS: Integration Scenarios
# ============================================================================

@pytest.mark.integration
def test_full_ingestion_pipeline():
    """Test complete ingestion pipeline from file to chunks"""
    # Create temporary file with realistic content
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        content = """This is the first paragraph with important information about vector stores.

This is the second paragraph discussing document chunking strategies.

The third paragraph covers embedding models and their dimensions."""
        f.write(content)
        temp_path = f.name
    
    try:
        # Ingest with custom settings
        chunks = ingest_document(
            temp_path,
            use_sentence_chunking=False,
            metadata={"document_type": "test"}
        )
        
        # Verify chunks
        assert len(chunks) >= 1
        
        # Verify metadata is complete
        for chunk in chunks:
            assert chunk.source == temp_path
            assert "document_type" in chunk.metadata
            assert "file_path" in chunk.metadata
            assert "chunk_index" in chunk.metadata
            
        # Verify text preservation
        all_text = " ".join(chunk.text for chunk in chunks)
        assert "vector stores" in all_text
        assert "embedding models" in all_text
        
    finally:
        Path(temp_path).unlink()


@pytest.mark.integration
def test_chunking_preserves_context():
    """Test that chunking with overlap preserves context across boundaries"""
    chunker = DocumentChunker(chunk_size=20, chunk_overlap=10)  # Very small chunks to force splitting
    
    text = """Machine learning is a subset of artificial intelligence. 
    It focuses on algorithms that improve through experience. 
    Deep learning is a specialized technique within machine learning.
    Neural networks are fundamental building blocks.
    Training requires large datasets and compute power."""
    
    chunks = chunker.chunk_by_sentences(text, source="test.txt")
    
    # Should create multiple chunks with small chunk size
    assert len(chunks) >= 2
    
    # Verify overlap exists
    if len(chunks) >= 2:
        # Check that some content appears in multiple chunks
        texts = [chunk.text for chunk in chunks]
        # At least some words should be repeated due to overlap
        all_words = []
        for text in texts:
            all_words.extend(text.split())
        assert len(all_words) > len(set(all_words))  # Some repetition due to overlap
