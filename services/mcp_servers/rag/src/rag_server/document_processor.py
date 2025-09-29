"""Document processing and chunking for RAG system."""

import logging
import hashlib
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import re

from mavik_common.models import RAGChunk
from mavik_common.errors import DocumentParsingError, ValidationError

logger = logging.getLogger(__name__)


@dataclass
class DocumentMetadata:
    """Metadata for processed documents."""
    
    document_id: str
    title: str
    source_type: str
    file_path: str
    total_pages: Optional[int] = None
    author: Optional[str] = None
    created_date: Optional[str] = None
    mnpi_classification: str = "public"
    deal_id: Optional[str] = None
    tags: Optional[Dict[str, str]] = None


class DocumentProcessor:
    """Processes documents into searchable chunks for RAG system."""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100,
    ):
        """Initialize document processor.
        
        Args:
            chunk_size: Target size of text chunks in characters
            chunk_overlap: Overlap between consecutive chunks
            min_chunk_size: Minimum chunk size to keep
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
    
    def process_document(
        self,
        content: str,
        metadata: DocumentMetadata,
    ) -> List[RAGChunk]:
        """Process document content into searchable chunks.
        
        Args:
            content: Raw document text content
            metadata: Document metadata
            
        Returns:
            List of processed chunks
            
        Raises:
            DocumentParsingError: If document processing fails
            ValidationError: If input validation fails
        """
        try:
            if not content or not content.strip():
                raise ValidationError("Document content is empty")
            
            if not metadata.document_id:
                raise ValidationError("Document ID is required")
            
            # Clean and preprocess content
            cleaned_content = self._clean_content(content)
            
            # Split into chunks
            text_chunks = self._split_text(cleaned_content)
            
            # Create RAG chunks with metadata
            rag_chunks = []
            for i, chunk_text in enumerate(text_chunks):
                if len(chunk_text.strip()) < self.min_chunk_size:
                    continue
                
                chunk = RAGChunk(
                    chunk_id=self._generate_chunk_id(metadata.document_id, i),
                    document_id=metadata.document_id,
                    content=chunk_text.strip(),
                    page_number=self._estimate_page_number(i, len(text_chunks), metadata.total_pages),
                    chunk_index=i,
                    source_type=metadata.source_type,
                    metadata={
                        "title": metadata.title,
                        "file_path": metadata.file_path,
                        "author": metadata.author,
                        "created_date": metadata.created_date,
                        "mnpi_classification": metadata.mnpi_classification,
                        "deal_id": metadata.deal_id,
                        **(metadata.tags or {}),
                    }
                )
                rag_chunks.append(chunk)
            
            logger.info(f"Processed document {metadata.document_id} into {len(rag_chunks)} chunks")
            return rag_chunks
            
        except Exception as e:
            logger.error(f"Document processing failed for {metadata.document_id}: {e}")
            if isinstance(e, (DocumentParsingError, ValidationError)):
                raise
            raise DocumentParsingError(f"Failed to process document: {e}")
    
    def _clean_content(self, content: str) -> str:
        """Clean and normalize document content."""
        
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content)
        
        # Remove page headers/footers (common patterns)
        content = re.sub(r'Page \d+ of \d+', '', content, flags=re.IGNORECASE)
        content = re.sub(r'^\d+\s*$', '', content, flags=re.MULTILINE)
        
        # Normalize line breaks
        content = re.sub(r'\n\s*\n', '\n\n', content)
        
        # Remove excessive punctuation
        content = re.sub(r'\.{3,}', '...', content)
        content = re.sub(r'-{3,}', '---', content)
        
        return content.strip()
    
    def _split_text(self, content: str) -> List[str]:
        """Split content into overlapping chunks."""
        
        chunks = []
        start = 0
        content_length = len(content)
        
        while start < content_length:
            # Calculate end position
            end = start + self.chunk_size
            
            # If we're at the end, take the rest
            if end >= content_length:
                chunk = content[start:]
                if chunk.strip():
                    chunks.append(chunk)
                break
            
            # Try to break at sentence boundary
            chunk_end = self._find_sentence_boundary(content, start, end)
            
            # If no good sentence boundary found, try paragraph boundary
            if chunk_end == end:
                chunk_end = self._find_paragraph_boundary(content, start, end)
            
            # If still no good boundary, try word boundary
            if chunk_end == end:
                chunk_end = self._find_word_boundary(content, start, end)
            
            chunk = content[start:chunk_end]
            if chunk.strip():
                chunks.append(chunk)
            
            # Move start position with overlap
            start = chunk_end - self.chunk_overlap
            
            # Ensure we make progress
            if start <= 0:
                start = chunk_end
        
        return chunks
    
    def _find_sentence_boundary(self, content: str, start: int, end: int) -> int:
        """Find a good sentence boundary near the end position."""
        
        # Look backward from end for sentence endings
        search_start = max(start, end - 200)  # Don't search too far back
        
        sentence_endings = ['. ', '! ', '? ', '.\n', '!\n', '?\n']
        
        best_pos = end
        for ending in sentence_endings:
            pos = content.rfind(ending, search_start, end)
            if pos != -1:
                # Take the position after the sentence ending
                candidate_pos = pos + len(ending)
                if candidate_pos > start + self.min_chunk_size:
                    best_pos = min(best_pos, candidate_pos)
        
        return best_pos
    
    def _find_paragraph_boundary(self, content: str, start: int, end: int) -> int:
        """Find a paragraph boundary near the end position."""
        
        # Look for double newlines (paragraph breaks)
        search_start = max(start, end - 200)
        
        pos = content.rfind('\n\n', search_start, end)
        if pos != -1 and pos > start + self.min_chunk_size:
            return pos + 2
        
        # Single newline as fallback
        pos = content.rfind('\n', search_start, end)
        if pos != -1 and pos > start + self.min_chunk_size:
            return pos + 1
        
        return end
    
    def _find_word_boundary(self, content: str, start: int, end: int) -> int:
        """Find a word boundary near the end position."""
        
        # Look backward for whitespace
        search_start = max(start, end - 100)
        
        for i in range(end - 1, search_start - 1, -1):
            if content[i].isspace():
                return i + 1
        
        return end
    
    def _generate_chunk_id(self, document_id: str, chunk_index: int) -> str:
        """Generate unique chunk ID."""
        
        # Create hash from document ID and chunk index
        content = f"{document_id}:{chunk_index}"
        hash_obj = hashlib.md5(content.encode())
        return f"{document_id}-chunk-{chunk_index}-{hash_obj.hexdigest()[:8]}"
    
    def _estimate_page_number(
        self, 
        chunk_index: int, 
        total_chunks: int, 
        total_pages: Optional[int]
    ) -> Optional[int]:
        """Estimate page number for chunk based on position."""
        
        if total_pages is None or total_chunks == 0:
            return None
        
        # Simple linear estimation
        estimated_page = int((chunk_index / total_chunks) * total_pages) + 1
        return min(estimated_page, total_pages)


class DocumentIndexer:
    """Handles document indexing and metadata management."""
    
    def __init__(self):
        """Initialize document indexer."""
        self.document_registry: Dict[str, DocumentMetadata] = {}
    
    def register_document(self, metadata: DocumentMetadata) -> None:
        """Register document metadata."""
        self.document_registry[metadata.document_id] = metadata
        logger.info(f"Registered document: {metadata.document_id}")
    
    def get_document_metadata(self, document_id: str) -> Optional[DocumentMetadata]:
        """Get document metadata by ID."""
        return self.document_registry.get(document_id)
    
    def list_documents(
        self,
        deal_id: Optional[str] = None,
        source_type: Optional[str] = None,
        mnpi_classification: Optional[str] = None,
    ) -> List[DocumentMetadata]:
        """List documents with optional filtering."""
        
        documents = list(self.document_registry.values())
        
        if deal_id:
            documents = [d for d in documents if d.deal_id == deal_id]
        
        if source_type:
            documents = [d for d in documents if d.source_type == source_type]
        
        if mnpi_classification:
            documents = [d for d in documents if d.mnpi_classification == mnpi_classification]
        
        return documents
    
    def extract_document_metadata(
        self,
        file_path: str,
        content: str,
        document_id: Optional[str] = None,
        **kwargs
    ) -> DocumentMetadata:
        """Extract metadata from document content and path."""
        
        if document_id is None:
            document_id = self._generate_document_id(file_path)
        
        # Extract title from content or filename
        title = self._extract_title(content) or self._filename_to_title(file_path)
        
        # Determine source type from file extension
        source_type = self._determine_source_type(file_path)
        
        # Extract other metadata from content
        author = self._extract_author(content)
        created_date = self._extract_date(content)
        
        return DocumentMetadata(
            document_id=document_id,
            title=title,
            source_type=source_type,
            file_path=file_path,
            author=author,
            created_date=created_date,
            **kwargs
        )
    
    def _generate_document_id(self, file_path: str) -> str:
        """Generate unique document ID from file path."""
        
        # Create hash from file path
        hash_obj = hashlib.md5(file_path.encode())
        return f"doc-{hash_obj.hexdigest()[:16]}"
    
    def _extract_title(self, content: str) -> Optional[str]:
        """Extract title from document content."""
        
        lines = content.split('\n')[:10]  # Check first 10 lines
        
        for line in lines:
            line = line.strip()
            
            # Look for title patterns
            if len(line) > 5 and len(line) < 200:
                # Skip lines that look like headers/metadata
                if any(x in line.lower() for x in ['page', 'date:', 'from:', 'to:', 'subject:']):
                    continue
                
                # First substantial line is likely the title
                if line and not line.startswith(('•', '-', '*', '1.', 'a.')):
                    return line
        
        return None
    
    def _filename_to_title(self, file_path: str) -> str:
        """Convert filename to title."""
        
        import os
        
        filename = os.path.basename(file_path)
        
        # Remove extension
        title = os.path.splitext(filename)[0]
        
        # Replace underscores and hyphens with spaces
        title = title.replace('_', ' ').replace('-', ' ')
        
        # Title case
        title = title.title()
        
        return title
    
    def _determine_source_type(self, file_path: str) -> str:
        """Determine document source type from file path."""
        
        import os
        
        _, ext = os.path.splitext(file_path.lower())
        
        type_mapping = {
            '.pdf': 'pdf',
            '.doc': 'word',
            '.docx': 'word',
            '.txt': 'text',
            '.md': 'markdown',
            '.html': 'html',
            '.htm': 'html',
        }
        
        return type_mapping.get(ext, 'unknown')
    
    def _extract_author(self, content: str) -> Optional[str]:
        """Extract author from document content."""
        
        lines = content.split('\n')[:20]  # Check first 20 lines
        
        author_patterns = [
            r'(?:author|by|prepared by|written by):\s*(.+)',
            r'(?:from|sender):\s*(.+)',
        ]
        
        for line in lines:
            for pattern in author_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    return match.group(1).strip()
        
        return None
    
    def _extract_date(self, content: str) -> Optional[str]:
        """Extract creation date from document content."""
        
        lines = content.split('\n')[:20]  # Check first 20 lines
        
        date_patterns = [
            r'(?:date|created|dated):\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(?:date|created|dated):\s*(\w+\s+\d{1,2},?\s+\d{4})',
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        ]
        
        for line in lines:
            for pattern in date_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    return match.group(1).strip()
        
        return None