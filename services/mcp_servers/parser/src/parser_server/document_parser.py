"""Document parsing and extraction using AWS Textract and other parsers."""

import logging
import tempfile
import json
from typing import List, Dict, Any, Optional, Tuple, BinaryIO
from pathlib import Path
from datetime import datetime
import asyncio

import aiofiles
from PIL import Image
import PyPDF2

from mavik_common.models import (
    DocumentMetadata, ParsedDocument, DocumentPage, DocumentElement,
    DocumentTable, DocumentForm, BoundingBox
)
from mavik_common.errors import DocumentProcessingError, ValidationError
from mavik_aws_clients import TextractClient, S3Client

logger = logging.getLogger(__name__)


class DocumentFormatDetector:
    """Detect and validate document formats."""
    
    SUPPORTED_FORMATS = {
        'pdf': ['.pdf'],
        'image': ['.png', '.jpg', '.jpeg', '.tiff', '.gif', '.bmp'],
        'text': ['.txt', '.md', '.rtf'],
        'office': ['.docx', '.doc', '.pptx', '.ppt', '.xlsx', '.xls'],
    }
    
    PDF_MAGIC_BYTES = b'%PDF'
    IMAGE_MAGIC_BYTES = {
        b'\x89PNG': 'png',
        b'\xff\xd8\xff': 'jpeg', 
        b'GIF87a': 'gif',
        b'GIF89a': 'gif',
        b'BM': 'bmp',
        b'II*\x00': 'tiff',
        b'MM\x00*': 'tiff',
    }
    
    @classmethod
    def detect_format(cls, file_path: str) -> str:
        """Detect document format from file path and content."""
        
        path = Path(file_path)
        extension = path.suffix.lower()
        
        # Check extension first
        format_type = None
        for fmt, extensions in cls.SUPPORTED_FORMATS.items():
            if extension in extensions:
                format_type = fmt
                break
        
        if not format_type:
            raise ValidationError(f"Unsupported file extension: {extension}")
        
        # Verify with magic bytes for binary formats
        try:
            with open(file_path, 'rb') as f:
                header = f.read(16)
                
            if format_type == 'pdf' and not header.startswith(cls.PDF_MAGIC_BYTES):
                raise ValidationError("File does not appear to be a valid PDF")
            
            if format_type == 'image':
                detected_image_type = None
                for magic, img_type in cls.IMAGE_MAGIC_BYTES.items():
                    if header.startswith(magic):
                        detected_image_type = img_type
                        break
                
                if not detected_image_type:
                    # Try PIL as fallback
                    try:
                        with Image.open(file_path) as img:
                            img.verify()
                    except Exception:
                        raise ValidationError("File does not appear to be a valid image")
                        
        except (OSError, IOError) as e:
            raise DocumentProcessingError(f"Error reading file: {e}")
        
        return format_type
    
    @classmethod
    def is_supported(cls, file_path: str) -> bool:
        """Check if file format is supported."""
        try:
            cls.detect_format(file_path)
            return True
        except (ValidationError, DocumentProcessingError):
            return False


class TextractParser:
    """Parse documents using AWS Textract."""
    
    def __init__(self, textract_client: TextractClient):
        """Initialize Textract parser.
        
        Args:
            textract_client: AWS Textract client instance
        """
        self.textract_client = textract_client
    
    async def parse_document(
        self,
        s3_bucket: str,
        s3_key: str,
        document_id: str,
        extract_tables: bool = True,
        extract_forms: bool = True,
        extract_signatures: bool = False,
    ) -> ParsedDocument:
        """Parse document using Textract.
        
        Args:
            s3_bucket: S3 bucket containing the document
            s3_key: S3 key (path) to the document
            document_id: Unique document identifier
            extract_tables: Whether to extract table data
            extract_forms: Whether to extract form key-value pairs
            extract_signatures: Whether to detect signatures
            
        Returns:
            Parsed document with extracted content
            
        Raises:
            DocumentProcessingError: If parsing fails
        """
        
        try:
            logger.info(f"Starting Textract analysis for {document_id} (s3://{s3_bucket}/{s3_key})")
            
            # Determine analysis features
            features = []
            if extract_tables:
                features.append("TABLES")
            if extract_forms:
                features.append("FORMS")
            if extract_signatures:
                features.append("SIGNATURES")
            
            # Start Textract analysis
            if features:
                # Use asynchronous analysis for complex features
                job_id = await self._start_async_analysis(s3_bucket, s3_key, features)
                textract_response = await self._wait_for_analysis(job_id)
            else:
                # Use synchronous analysis for text only
                textract_response = await self.textract_client.analyze_document(
                    s3_bucket=s3_bucket,
                    s3_key=s3_key,
                )
            
            # Process Textract response
            parsed_doc = await self._process_textract_response(
                textract_response, document_id, s3_bucket, s3_key
            )
            
            logger.info(f"Textract analysis completed: {len(parsed_doc.pages)} pages, "
                       f"{len(parsed_doc.tables)} tables, {len(parsed_doc.forms)} forms")
            
            return parsed_doc
            
        except Exception as e:
            logger.error(f"Textract parsing failed for {document_id}: {e}")
            if isinstance(e, DocumentProcessingError):
                raise
            raise DocumentProcessingError(f"Textract analysis failed: {e}")
    
    async def _start_async_analysis(
        self, s3_bucket: str, s3_key: str, features: List[str]
    ) -> str:
        """Start asynchronous Textract analysis."""
        
        try:
            response = await self.textract_client.start_document_analysis(
                s3_bucket=s3_bucket,
                s3_key=s3_key,
                features=features,
            )
            
            job_id = response.get("JobId")
            if not job_id:
                raise DocumentProcessingError("Failed to start Textract analysis job")
            
            logger.info(f"Started Textract job: {job_id}")
            return job_id
            
        except Exception as e:
            raise DocumentProcessingError(f"Failed to start Textract analysis: {e}")
    
    async def _wait_for_analysis(self, job_id: str, max_wait_seconds: int = 300) -> Dict[str, Any]:
        """Wait for Textract analysis to complete."""
        
        logger.info(f"Waiting for Textract job completion: {job_id}")
        
        start_time = datetime.utcnow()
        poll_interval = 5  # seconds
        
        while True:
            try:
                response = await self.textract_client.get_document_analysis(job_id)
                status = response.get("JobStatus")
                
                if status == "SUCCEEDED":
                    logger.info(f"Textract job completed successfully: {job_id}")
                    return response
                elif status == "FAILED":
                    error_msg = response.get("StatusMessage", "Unknown error")
                    raise DocumentProcessingError(f"Textract job failed: {error_msg}")
                elif status in ["IN_PROGRESS", "PARTIAL_SUCCESS"]:
                    # Check timeout
                    elapsed = (datetime.utcnow() - start_time).total_seconds()
                    if elapsed > max_wait_seconds:
                        raise DocumentProcessingError(
                            f"Textract job timeout after {max_wait_seconds}s: {job_id}"
                        )
                    
                    logger.debug(f"Textract job in progress: {job_id} ({elapsed:.0f}s)")
                    await asyncio.sleep(poll_interval)
                else:
                    raise DocumentProcessingError(f"Unknown Textract job status: {status}")
                    
            except Exception as e:
                if isinstance(e, DocumentProcessingError):
                    raise
                logger.error(f"Error checking Textract job status: {e}")
                await asyncio.sleep(poll_interval)
    
    async def _process_textract_response(
        self,
        response: Dict[str, Any],
        document_id: str,
        s3_bucket: str,
        s3_key: str,
    ) -> ParsedDocument:
        """Process Textract response into structured document."""
        
        blocks = response.get("Blocks", [])
        if not blocks:
            raise DocumentProcessingError("No blocks found in Textract response")
        
        # Group blocks by type
        pages = []
        tables = []
        forms = []
        
        # Create lookup for blocks
        block_map = {block["Id"]: block for block in blocks}
        
        # Process pages
        page_blocks = [block for block in blocks if block["BlockType"] == "PAGE"]
        for page_block in page_blocks:
            page = await self._process_page_block(page_block, block_map)
            pages.append(page)
        
        # Process tables
        table_blocks = [block for block in blocks if block["BlockType"] == "TABLE"]
        for table_block in table_blocks:
            table = await self._process_table_block(table_block, block_map)
            tables.append(table)
        
        # Process forms (key-value pairs)
        kv_blocks = [block for block in blocks if block["BlockType"] == "KEY_VALUE_SET"]
        if kv_blocks:
            forms = await self._process_form_blocks(kv_blocks, block_map)
        
        # Create document metadata
        metadata = DocumentMetadata(
            document_id=document_id,
            source_location=f"s3://{s3_bucket}/{s3_key}",
            processing_timestamp=datetime.utcnow(),
            total_pages=len(pages),
            content_type="application/pdf",  # Default, could be detected
            file_size=0,  # Would need to get from S3
            parser_version="textract-1.0",
        )
        
        return ParsedDocument(
            metadata=metadata,
            pages=pages,
            tables=tables,
            forms=forms,
            full_text=self._extract_full_text(pages),
        )
    
    async def _process_page_block(
        self, page_block: Dict[str, Any], block_map: Dict[str, Dict[str, Any]]
    ) -> DocumentPage:
        """Process a page block into structured page data."""
        
        page_number = page_block.get("Page", 1)
        
        # Get geometry
        geometry = page_block.get("Geometry", {})
        bbox = self._extract_bounding_box(geometry)
        
        # Extract text elements from child blocks
        elements = []
        relationships = page_block.get("Relationships", [])
        
        for relationship in relationships:
            if relationship["Type"] == "CHILD":
                child_ids = relationship.get("Ids", [])
                
                for child_id in child_ids:
                    child_block = block_map.get(child_id)
                    if child_block and child_block["BlockType"] == "LINE":
                        element = await self._process_line_block(child_block, block_map)
                        elements.append(element)
        
        return DocumentPage(
            page_number=page_number,
            elements=elements,
            bounding_box=bbox,
            width=geometry.get("BoundingBox", {}).get("Width", 1.0),
            height=geometry.get("BoundingBox", {}).get("Height", 1.0),
        )
    
    async def _process_line_block(
        self, line_block: Dict[str, Any], block_map: Dict[str, Dict[str, Any]]
    ) -> DocumentElement:
        """Process a line block into a document element."""
        
        text = line_block.get("Text", "")
        confidence = line_block.get("Confidence", 0.0)
        geometry = line_block.get("Geometry", {})
        bbox = self._extract_bounding_box(geometry)
        
        # Extract word-level information
        word_details = []
        relationships = line_block.get("Relationships", [])
        
        for relationship in relationships:
            if relationship["Type"] == "CHILD":
                word_ids = relationship.get("Ids", [])
                
                for word_id in word_ids:
                    word_block = block_map.get(word_id)
                    if word_block and word_block["BlockType"] == "WORD":
                        word_details.append({
                            "text": word_block.get("Text", ""),
                            "confidence": word_block.get("Confidence", 0.0),
                            "bounding_box": self._extract_bounding_box(
                                word_block.get("Geometry", {})
                            ),
                        })
        
        return DocumentElement(
            element_type="line",
            text=text,
            bounding_box=bbox,
            confidence=confidence,
            properties={
                "word_count": len(word_details),
                "words": word_details,
            },
        )
    
    async def _process_table_block(
        self, table_block: Dict[str, Any], block_map: Dict[str, Dict[str, Any]]
    ) -> DocumentTable:
        """Process a table block into structured table data."""
        
        table_id = table_block["Id"]
        confidence = table_block.get("Confidence", 0.0)
        geometry = table_block.get("Geometry", {})
        bbox = self._extract_bounding_box(geometry)
        
        # Extract table cells
        cells = []
        relationships = table_block.get("Relationships", [])
        
        for relationship in relationships:
            if relationship["Type"] == "CHILD":
                cell_ids = relationship.get("Ids", [])
                
                for cell_id in cell_ids:
                    cell_block = block_map.get(cell_id)
                    if cell_block and cell_block["BlockType"] == "CELL":
                        cell_data = await self._process_cell_block(cell_block, block_map)
                        cells.append(cell_data)
        
        # Organize cells into rows and columns
        rows = self._organize_table_cells(cells)
        
        return DocumentTable(
            table_id=table_id,
            rows=rows,
            bounding_box=bbox,
            confidence=confidence,
        )
    
    async def _process_cell_block(
        self, cell_block: Dict[str, Any], block_map: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Process a table cell block."""
        
        row_index = cell_block.get("RowIndex", 0)
        column_index = cell_block.get("ColumnIndex", 0)
        row_span = cell_block.get("RowSpan", 1)
        column_span = cell_block.get("ColumnSpan", 1)
        is_header = cell_block.get("EntityTypes", []) and "COLUMN_HEADER" in cell_block["EntityTypes"]
        
        # Extract cell text
        cell_text = ""
        relationships = cell_block.get("Relationships", [])
        
        for relationship in relationships:
            if relationship["Type"] == "CHILD":
                word_ids = relationship.get("Ids", [])
                
                words = []
                for word_id in word_ids:
                    word_block = block_map.get(word_id)
                    if word_block and word_block["BlockType"] == "WORD":
                        words.append(word_block.get("Text", ""))
                
                cell_text = " ".join(words)
        
        return {
            "text": cell_text,
            "row_index": row_index,
            "column_index": column_index,
            "row_span": row_span,
            "column_span": column_span,
            "is_header": is_header,
            "confidence": cell_block.get("Confidence", 0.0),
            "bounding_box": self._extract_bounding_box(cell_block.get("Geometry", {})),
        }
    
    def _organize_table_cells(self, cells: List[Dict[str, Any]]) -> List[List[str]]:
        """Organize table cells into a 2D array of rows and columns."""
        
        if not cells:
            return []
        
        # Determine table dimensions
        max_row = max(cell["row_index"] + cell["row_span"] - 1 for cell in cells)
        max_col = max(cell["column_index"] + cell["column_span"] - 1 for cell in cells)
        
        # Initialize table grid
        table_grid = [["" for _ in range(max_col + 1)] for _ in range(max_row + 1)]
        
        # Fill table grid
        for cell in cells:
            text = cell["text"]
            row_start = cell["row_index"]
            col_start = cell["column_index"]
            
            # Handle cell spans
            for r in range(row_start, row_start + cell["row_span"]):
                for c in range(col_start, col_start + cell["column_span"]):
                    if r <= max_row and c <= max_col:
                        table_grid[r][c] = text if r == row_start and c == col_start else ""
        
        return table_grid
    
    async def _process_form_blocks(
        self, kv_blocks: List[Dict[str, Any]], block_map: Dict[str, Dict[str, Any]]
    ) -> List[DocumentForm]:
        """Process key-value pair blocks into form data."""
        
        forms = []
        key_blocks = [block for block in kv_blocks if block.get("EntityTypes") == ["KEY"]]
        
        for key_block in key_blocks:
            # Find corresponding value block
            value_block = None
            relationships = key_block.get("Relationships", [])
            
            for relationship in relationships:
                if relationship["Type"] == "VALUE":
                    value_ids = relationship.get("Ids", [])
                    if value_ids:
                        value_block = block_map.get(value_ids[0])
                        break
            
            if value_block:
                key_text = self._extract_text_from_block(key_block, block_map)
                value_text = self._extract_text_from_block(value_block, block_map)
                
                form = DocumentForm(
                    key=key_text,
                    value=value_text,
                    confidence=min(
                        key_block.get("Confidence", 0.0),
                        value_block.get("Confidence", 0.0)
                    ),
                    key_bounding_box=self._extract_bounding_box(key_block.get("Geometry", {})),
                    value_bounding_box=self._extract_bounding_box(value_block.get("Geometry", {})),
                )
                forms.append(form)
        
        return forms
    
    def _extract_text_from_block(
        self, block: Dict[str, Any], block_map: Dict[str, Dict[str, Any]]
    ) -> str:
        """Extract text content from a block and its children."""
        
        text_parts = []
        
        # Check if block has direct text
        if "Text" in block:
            text_parts.append(block["Text"])
        
        # Extract text from child blocks
        relationships = block.get("Relationships", [])
        for relationship in relationships:
            if relationship["Type"] == "CHILD":
                child_ids = relationship.get("Ids", [])
                
                for child_id in child_ids:
                    child_block = block_map.get(child_id)
                    if child_block and "Text" in child_block:
                        text_parts.append(child_block["Text"])
        
        return " ".join(text_parts).strip()
    
    def _extract_bounding_box(self, geometry: Dict[str, Any]) -> Optional[BoundingBox]:
        """Extract bounding box from Textract geometry."""
        
        bbox_data = geometry.get("BoundingBox")
        if not bbox_data:
            return None
        
        return BoundingBox(
            left=bbox_data.get("Left", 0.0),
            top=bbox_data.get("Top", 0.0),
            width=bbox_data.get("Width", 0.0),
            height=bbox_data.get("Height", 0.0),
        )
    
    def _extract_full_text(self, pages: List[DocumentPage]) -> str:
        """Extract full text content from all pages."""
        
        text_parts = []
        
        for page in pages:
            page_text = []
            for element in page.elements:
                if element.text:
                    page_text.append(element.text)
            
            if page_text:
                text_parts.append("\n".join(page_text))
        
        return "\n\n".join(text_parts)


class LocalPDFParser:
    """Parse PDF documents locally using PyPDF2."""
    
    def __init__(self):
        """Initialize PDF parser."""
        pass
    
    async def parse_pdf(self, file_path: str, document_id: str) -> ParsedDocument:
        """Parse PDF document locally.
        
        Args:
            file_path: Path to PDF file
            document_id: Unique document identifier
            
        Returns:
            Parsed document with basic text extraction
        """
        
        try:
            logger.info(f"Parsing PDF locally: {document_id} ({file_path})")
            
            pages = []
            
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    try:
                        # Extract text from page
                        text = page.extract_text()
                        
                        # Create simple document element
                        element = DocumentElement(
                            element_type="page_text",
                            text=text,
                            bounding_box=None,  # Not available in PyPDF2
                            confidence=1.0,     # Assume perfect for local extraction
                        )
                        
                        # Create page
                        doc_page = DocumentPage(
                            page_number=page_num,
                            elements=[element] if text.strip() else [],
                            bounding_box=None,
                            width=1.0,  # Normalized
                            height=1.0, # Normalized
                        )
                        
                        pages.append(doc_page)
                        
                    except Exception as e:
                        logger.warning(f"Error extracting page {page_num}: {e}")
                        # Create empty page
                        doc_page = DocumentPage(
                            page_number=page_num,
                            elements=[],
                            bounding_box=None,
                            width=1.0,
                            height=1.0,
                        )
                        pages.append(doc_page)
            
            # Create metadata
            file_stat = Path(file_path).stat()
            metadata = DocumentMetadata(
                document_id=document_id,
                source_location=file_path,
                processing_timestamp=datetime.utcnow(),
                total_pages=len(pages),
                content_type="application/pdf",
                file_size=file_stat.st_size,
                parser_version="pypdf2-local",
            )
            
            # Extract full text
            full_text = "\n\n".join(
                "\n".join(elem.text for elem in page.elements if elem.text)
                for page in pages
            )
            
            parsed_doc = ParsedDocument(
                metadata=metadata,
                pages=pages,
                tables=[],  # Not extracted in local mode
                forms=[],   # Not extracted in local mode
                full_text=full_text,
            )
            
            logger.info(f"Local PDF parsing completed: {len(pages)} pages")
            return parsed_doc
            
        except Exception as e:
            logger.error(f"Local PDF parsing failed for {document_id}: {e}")
            raise DocumentProcessingError(f"PDF parsing failed: {e}")


class DocumentParser:
    """Main document parser that routes to appropriate parsers."""
    
    def __init__(
        self,
        textract_client: Optional[TextractClient] = None,
        s3_client: Optional[S3Client] = None,
        use_local_fallback: bool = True,
    ):
        """Initialize document parser.
        
        Args:
            textract_client: AWS Textract client (optional)
            s3_client: AWS S3 client (optional)
            use_local_fallback: Whether to use local parsing as fallback
        """
        self.textract_parser = TextractParser(textract_client) if textract_client else None
        self.s3_client = s3_client
        self.pdf_parser = LocalPDFParser()
        self.use_local_fallback = use_local_fallback
    
    async def parse_document(
        self,
        document_source: str,
        document_id: str,
        parser_options: Optional[Dict[str, Any]] = None,
    ) -> ParsedDocument:
        """Parse document from various sources.
        
        Args:
            document_source: Source location (file path, S3 URI, etc.)
            document_id: Unique document identifier
            parser_options: Parser configuration options
            
        Returns:
            Parsed document
            
        Raises:
            DocumentProcessingError: If parsing fails
            ValidationError: If source format is invalid
        """
        
        options = parser_options or {}
        
        try:
            # Determine source type and route to appropriate parser
            if document_source.startswith("s3://"):
                # S3 document
                return await self._parse_s3_document(document_source, document_id, options)
            else:
                # Local file
                return await self._parse_local_document(document_source, document_id, options)
                
        except Exception as e:
            logger.error(f"Document parsing failed for {document_id}: {e}")
            if isinstance(e, (DocumentProcessingError, ValidationError)):
                raise
            raise DocumentProcessingError(f"Document parsing failed: {e}")
    
    async def _parse_s3_document(
        self, s3_uri: str, document_id: str, options: Dict[str, Any]
    ) -> ParsedDocument:
        """Parse document from S3."""
        
        # Parse S3 URI
        if not s3_uri.startswith("s3://"):
            raise ValidationError("Invalid S3 URI format")
        
        s3_path = s3_uri[5:]  # Remove 's3://' prefix
        bucket, key = s3_path.split("/", 1)
        
        # Use Textract if available
        if self.textract_parser:
            return await self.textract_parser.parse_document(
                s3_bucket=bucket,
                s3_key=key,
                document_id=document_id,
                extract_tables=options.get("extract_tables", True),
                extract_forms=options.get("extract_forms", True),
                extract_signatures=options.get("extract_signatures", False),
            )
        
        # Fallback: download and parse locally
        if self.use_local_fallback and self.s3_client:
            logger.info(f"Using local fallback for S3 document: {document_id}")
            
            # Download to temporary file
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_path = temp_file.name
                
            try:
                await self.s3_client.download_file(bucket, key, temp_path)
                return await self._parse_local_document(temp_path, document_id, options)
            finally:
                # Clean up temp file
                try:
                    Path(temp_path).unlink()
                except:
                    pass
        
        raise DocumentProcessingError("No available parser for S3 document")
    
    async def _parse_local_document(
        self, file_path: str, document_id: str, options: Dict[str, Any]
    ) -> ParsedDocument:
        """Parse local document file."""
        
        # Detect format
        try:
            format_type = DocumentFormatDetector.detect_format(file_path)
        except ValidationError as e:
            raise ValidationError(f"Unsupported document format: {e}")
        
        # Route to appropriate parser
        if format_type == "pdf":
            return await self.pdf_parser.parse_pdf(file_path, document_id)
        elif format_type == "image":
            # For images, we'd need Textract or OCR
            raise DocumentProcessingError("Image parsing requires Textract integration")
        elif format_type == "text":
            return await self._parse_text_file(file_path, document_id)
        else:
            raise DocumentProcessingError(f"No parser available for format: {format_type}")
    
    async def _parse_text_file(self, file_path: str, document_id: str) -> ParsedDocument:
        """Parse plain text file."""
        
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
                content = await file.read()
            
            # Create single page with text content
            element = DocumentElement(
                element_type="text",
                text=content,
                bounding_box=None,
                confidence=1.0,
            )
            
            page = DocumentPage(
                page_number=1,
                elements=[element],
                bounding_box=None,
                width=1.0,
                height=1.0,
            )
            
            # Create metadata
            file_stat = Path(file_path).stat()
            metadata = DocumentMetadata(
                document_id=document_id,
                source_location=file_path,
                processing_timestamp=datetime.utcnow(),
                total_pages=1,
                content_type="text/plain",
                file_size=file_stat.st_size,
                parser_version="text-local",
            )
            
            return ParsedDocument(
                metadata=metadata,
                pages=[page],
                tables=[],
                forms=[],
                full_text=content,
            )
            
        except Exception as e:
            raise DocumentProcessingError(f"Text file parsing failed: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check parser health and capabilities."""
        
        health = {
            "parsers": {
                "textract": bool(self.textract_parser),
                "local_pdf": True,
                "local_text": True,
            },
            "capabilities": {
                "s3_documents": bool(self.s3_client),
                "local_files": True,
                "table_extraction": bool(self.textract_parser),
                "form_extraction": bool(self.textract_parser),
                "ocr": bool(self.textract_parser),
            },
            "supported_formats": list(DocumentFormatDetector.SUPPORTED_FORMATS.keys()),
        }
        
        return health