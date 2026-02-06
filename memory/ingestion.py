"""
Document Ingestion and Chunking for RAG
Handles document processing, text extraction, and optimal chunking
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import re
from dataclasses import dataclass


@dataclass
class Chunk:
    """Represents a text chunk with metadata"""

    text: str
    chunk_id: str
    source: str
    start_idx: int
    end_idx: int
    metadata: Dict[str, Any]


class DocumentChunker:
    """
    Document chunking utility for RAG pipelines

    Splits documents into optimal chunks with overlap for better retrieval.
    Supports token-based and sentence-based chunking strategies.
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separator: str = "\n\n",
        keep_separator: bool = True,
    ):
        """
        Initialize document chunker

        Args:
            chunk_size: Target number of tokens per chunk (default: 500)
            chunk_overlap: Number of overlapping tokens between chunks (default: 50)
            separator: Primary separator for splitting (default: paragraph break)
            keep_separator: Whether to keep separator in chunks (default: True)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separator = separator
        self.keep_separator = keep_separator

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count using simple heuristic

        Args:
            text: Input text

        Returns:
            Estimated token count (~1 token per 4 characters)

        Note:
            This is a fast approximation that works reasonably well for
            English and French text (~1 token per 4 chars). For production
            use with other languages or precise token counting, consider
            using the actual tokenizer (e.g., tiktoken for OpenAI models).
            Trade-off: Speed vs. accuracy.
        """
        # Simple heuristic: ~1 token per 4 characters for English/French
        # More accurate would use actual tokenizer, but this is fast
        return len(text) // 4

    def chunk_text(
        self,
        text: str,
        source: str = "unknown",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Chunk]:
        """
        Split text into chunks with overlap

        Args:
            text: Text to chunk
            source: Source identifier (filename, URL, etc.)
            metadata: Additional metadata to attach to chunks

        Returns:
            List of Chunk objects
        """
        if not text or not text.strip():
            return []

        metadata = metadata or {}
        chunks = []

        # Split by separator first
        segments = self._split_by_separator(text)

        # Combine segments into chunks of appropriate size
        current_chunk = ""
        current_start = 0
        chunk_counter = 0

        for segment in segments:
            segment_tokens = self.estimate_tokens(segment)
            current_tokens = self.estimate_tokens(current_chunk)

            # If adding this segment would exceed chunk_size, save current chunk
            if current_tokens > 0 and current_tokens + segment_tokens > self.chunk_size:
                chunk_id = f"{source}:chunk:{chunk_counter}"
                chunks.append(
                    Chunk(
                        text=current_chunk.strip(),
                        chunk_id=chunk_id,
                        source=source,
                        start_idx=current_start,
                        end_idx=current_start + len(current_chunk),
                        metadata={**metadata, "chunk_index": chunk_counter},
                    )
                )

                # Apply overlap: keep last portion of current chunk
                overlap_text = self._get_overlap(current_chunk)
                current_chunk = overlap_text + segment
                current_start += len(current_chunk) - len(overlap_text)
                chunk_counter += 1
            else:
                current_chunk += segment

        # Add final chunk
        if current_chunk.strip():
            chunk_id = f"{source}:chunk:{chunk_counter}"
            chunks.append(
                Chunk(
                    text=current_chunk.strip(),
                    chunk_id=chunk_id,
                    source=source,
                    start_idx=current_start,
                    end_idx=current_start + len(current_chunk),
                    metadata={**metadata, "chunk_index": chunk_counter},
                )
            )

        return chunks

    def _split_by_separator(self, text: str) -> List[str]:
        """Split text by separator while optionally keeping it"""
        if self.keep_separator:
            # Split but keep separator attached to preceding segment
            parts = text.split(self.separator)
            return [part + self.separator for part in parts[:-1]] + [parts[-1]]
        else:
            return text.split(self.separator)

    def _get_overlap(self, text: str) -> str:
        """
        Get overlap portion from end of text

        Args:
            text: Text to extract overlap from

        Returns:
            Overlap text (last chunk_overlap tokens)
        """
        # Estimate character count for overlap tokens
        overlap_chars = self.chunk_overlap * 4  # ~4 chars per token

        if len(text) <= overlap_chars:
            return text

        # Try to break at word boundary
        overlap_text = text[-overlap_chars:]
        space_idx = overlap_text.find(" ")

        if space_idx > 0:
            return overlap_text[space_idx + 1 :]

        return overlap_text

    def chunk_by_sentences(
        self,
        text: str,
        source: str = "unknown",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Chunk]:
        """
        Split text into chunks at sentence boundaries

        More intelligent than simple token-based chunking.
        Preserves sentence integrity.

        Args:
            text: Text to chunk
            source: Source identifier
            metadata: Additional metadata

        Returns:
            List of Chunk objects
        """
        if not text or not text.strip():
            return []

        metadata = metadata or {}

        # Split into sentences using simple regex
        # Note: This may not handle all edge cases (abbreviations like "Dr.",
        # "Inc.", decimal numbers, etc.). For production use with complex text,
        # consider using spaCy (spacy.load('en_core_web_sm').pipe()) or
        # NLTK (nltk.sent_tokenize()) for more robust sentence detection.
        sentences = re.split(r"(?<=[.!?])\s+", text)

        chunks = []
        current_chunk = ""
        current_start = 0
        chunk_counter = 0

        for sentence in sentences:
            sentence_tokens = self.estimate_tokens(sentence)
            current_tokens = self.estimate_tokens(current_chunk)

            # If adding sentence exceeds limit, save current chunk
            if current_tokens + sentence_tokens > self.chunk_size and current_chunk:
                chunk_id = f"{source}:chunk:{chunk_counter}"
                chunks.append(
                    Chunk(
                        text=current_chunk.strip(),
                        chunk_id=chunk_id,
                        source=source,
                        start_idx=current_start,
                        end_idx=current_start + len(current_chunk),
                        metadata={**metadata, "chunk_index": chunk_counter},
                    )
                )

                # Overlap: keep last few sentences
                overlap_sentences = self._get_last_sentences(current_chunk, 2)
                current_chunk = overlap_sentences + " " + sentence
                current_start += len(current_chunk) - len(overlap_sentences)
                chunk_counter += 1
            else:
                if current_chunk:
                    current_chunk += " "
                current_chunk += sentence

        # Add final chunk
        if current_chunk.strip():
            chunk_id = f"{source}:chunk:{chunk_counter}"
            chunks.append(
                Chunk(
                    text=current_chunk.strip(),
                    chunk_id=chunk_id,
                    source=source,
                    start_idx=current_start,
                    end_idx=current_start + len(current_chunk),
                    metadata={**metadata, "chunk_index": chunk_counter},
                )
            )

        return chunks

    def _get_last_sentences(self, text: str, n: int = 2) -> str:
        """Get last n sentences from text"""
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return " ".join(sentences[-n:]) if len(sentences) >= n else text


class DocumentLoader:
    """
    Document loader for various file formats

    Extracts text from PDF, DOCX, TXT files for ingestion into vector store.
    """

    @staticmethod
    def load_text(file_path: str) -> str:
        """
        Load plain text file

        Args:
            file_path: Path to text file

        Returns:
            Extracted text content
        """
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    @staticmethod
    def load_pdf(file_path: str) -> str:
        """
        Load PDF document

        Args:
            file_path: Path to PDF file

        Returns:
            Extracted text content
        """
        try:
            import PyPDF2
        except ImportError:
            raise ImportError(
                "PyPDF2 is required for PDF loading. Install with: pip install PyPDF2"
            )

        text_parts = []
        with open(file_path, "rb") as f:
            pdf_reader = PyPDF2.PdfReader(f)
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)

        return "\n\n".join(text_parts)

    @staticmethod
    def load_docx(file_path: str) -> str:
        """
        Load Word document

        Args:
            file_path: Path to DOCX file

        Returns:
            Extracted text content
        """
        try:
            import docx
        except ImportError:
            raise ImportError(
                "python-docx is required for DOCX loading. Install with: pip install python-docx"
            )

        doc = docx.Document(file_path)
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        return "\n\n".join(paragraphs)

    @staticmethod
    def load_document(file_path: str) -> str:
        """
        Auto-detect and load document based on extension

        Args:
            file_path: Path to document

        Returns:
            Extracted text content

        Raises:
            ValueError: If file format is not supported
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        extension = path.suffix.lower()

        if extension == ".txt":
            return DocumentLoader.load_text(file_path)
        elif extension == ".pdf":
            return DocumentLoader.load_pdf(file_path)
        elif extension in [".docx", ".doc"]:
            return DocumentLoader.load_docx(file_path)
        else:
            raise ValueError(f"Unsupported file format: {extension}")


def ingest_document(
    file_path: str,
    chunker: Optional[DocumentChunker] = None,
    use_sentence_chunking: bool = False,
    metadata: Optional[Dict[str, Any]] = None,
) -> List[Chunk]:
    """
    High-level function to ingest a document and return chunks

    Args:
        file_path: Path to document to ingest
        chunker: Optional custom chunker (uses default if None)
        use_sentence_chunking: If True, use sentence-aware chunking
        metadata: Additional metadata to attach to chunks

    Returns:
        List of Chunk objects ready for vector store ingestion
    """
    # Load document
    text = DocumentLoader.load_document(file_path)

    # Create chunker if not provided
    if chunker is None:
        chunker = DocumentChunker()

    # Add file path to metadata
    metadata = metadata or {}
    metadata["file_path"] = file_path
    metadata["file_name"] = Path(file_path).name

    # Chunk text
    if use_sentence_chunking:
        chunks = chunker.chunk_by_sentences(text, source=file_path, metadata=metadata)
    else:
        chunks = chunker.chunk_text(text, source=file_path, metadata=metadata)

    return chunks
