"""Document parsing and extraction using AWS Textract and other parsers."""

import logging
import tempfile
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import asyncio

import aiofiles
from PIL import Image
import PyPDF2

from mavik_common.models import (
    ParsedDocument
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
            raise DocumentProcessingError(
                document=str(file_path),
                operation="file_format_detection",
                reason=f"Error reading file: {e}"
            )

        return format_type

    @classmethod
    def is_supported(cls, file_path: str) -> bool:
        """Check if file format is supported by extension only."""
        try:
            path = Path(file_path)
            extension = path.suffix.lower()

            # Check if extension is in supported formats
            for format_type, extensions in cls.SUPPORTED_FORMATS.items():
                if extension in extensions:
                    return True
            return False
        except Exception:
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

            logger.info("Textract analysis completed")

            return parsed_doc

        except Exception as e:
            logger.error(f"Textract parsing failed for {document_id}: {e}")
            if isinstance(e, DocumentProcessingError):
                raise
            raise DocumentProcessingError(
                document="textract_document",
                operation="textract_analysis",
                reason=f"Textract analysis failed: {e}"
            )

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
                raise DocumentProcessingError(
                    document="textract_document",
                    operation="textract_job_start",
                    reason="Failed to start Textract analysis job"
                )

            logger.info(f"Started Textract job: {job_id}")
            return job_id

        except Exception as e:
            raise DocumentProcessingError(
                document="textract_document",
                operation="textract_job_initiation",
                reason=f"Failed to start Textract analysis: {e}"
            )

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
                    raise DocumentProcessingError(
                        document="textract_document",
                        operation="textract_job_execution",
                        reason=f"Textract job failed: {error_msg}"
                    )
                elif status in ["IN_PROGRESS", "PARTIAL_SUCCESS"]:
                    # Check timeout
                    elapsed = (datetime.utcnow() - start_time).total_seconds()
                    if elapsed > max_wait_seconds:
                        raise DocumentProcessingError(
                            document=job_id,
                            operation="textract_job_timeout",
                            reason=f"Textract job timeout after {max_wait_seconds}s"
                        )

                    logger.debug(f"Textract job in progress: {job_id} ({elapsed:.0f}s)")
                    await asyncio.sleep(poll_interval)
                else:
                    raise DocumentProcessingError(
                        document="textract_document",
                        operation="textract_status_check",
                        reason=f"Unknown Textract job status: {status}"
                    )

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
        """Process Textract response into a simple ParsedDocument aligned with current models."""

        blocks = response.get("Blocks", [])
        if not blocks:
            raise DocumentProcessingError(
                document=f"s3://{s3_bucket}/{s3_key}",
                operation="textract_response_processing",
                reason="No blocks found in Textract response"
            )

        # Extract plain text content from LINE blocks
        lines: List[str] = []
        for block in blocks:
            try:
                if block.get("BlockType") == "LINE" and block.get("Text"):
                    lines.append(block.get("Text", ""))
            except Exception:
                # Be resilient to unexpected block shapes
                continue

        content_text = "\n".join(lines).strip()

        # Build metadata summary as a plain dict
        page_count = sum(1 for b in blocks if b.get("BlockType") == "PAGE")
        table_count = sum(1 for b in blocks if b.get("BlockType") == "TABLE")
        metadata: Dict[str, Any] = {
            "source": f"s3://{s3_bucket}/{s3_key}",
            "page_count": page_count,
            "table_count": table_count,
            "parser": "textract",
            "processed_at": datetime.utcnow().isoformat(),
        }

        return ParsedDocument(
            document_id=document_id,
            s3_uri=f"s3://{s3_bucket}/{s3_key}",
            content=content_text,
            metadata=metadata,
            tables=[],
            confidence=1.0,
        )

    # Legacy structured helper methods removed; using simplified text extraction in _process_textract_response


class LocalPDFParser:
    """Parse PDF documents locally using PyPDF2 and return simple ParsedDocument."""

    def __init__(self):
        pass

    async def parse_pdf(self, file_path: str, document_id: str) -> ParsedDocument:
        try:
            logger.info(f"Parsing PDF locally: {document_id} ({file_path})")

            text_chunks: List[str] = []
            page_count = 0
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                page_count = len(pdf_reader.pages)
                for page in pdf_reader.pages:
                    try:
                        text = page.extract_text() or ""
                        if text:
                            text_chunks.append(text)
                    except Exception as e:
                        logger.warning(f"Error extracting page text: {e}")

            full_text = "\n\n".join(t.strip() for t in text_chunks if t and t.strip())

            # Build metadata as a simple dict
            file_stat = Path(file_path).stat()
            metadata: Dict[str, Any] = {
                "source": f"file://{file_path}",
                "page_count": page_count,
                "file_size": file_stat.st_size,
                "content_type": "application/pdf",
                "parser": "pypdf2-local",
                "processed_at": datetime.utcnow().isoformat(),
            }

            return ParsedDocument(
                document_id=document_id,
                s3_uri=f"file://{file_path}",
                content=full_text,
                metadata=metadata,
                tables=[],
                confidence=1.0,
            )

        except Exception as e:
            logger.error(f"Local PDF parsing failed for {document_id}: {e}")
            raise DocumentProcessingError(
                document=str(file_path),
                operation="pdf_parsing",
                reason=f"PDF parsing failed: {e}"
            )


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
            raise DocumentProcessingError(
                document=document_id,
                operation="document_parsing",
                reason=f"Document parsing failed: {e}"
            )

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

        raise DocumentProcessingError(
            document=s3_uri,
            operation="s3_document_parsing",
            reason="No available parser for S3 document"
        )

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
            raise DocumentProcessingError(
                document=file_path,
                operation="image_parsing",
                reason="Image parsing requires Textract integration"
            )
        elif format_type == "text":
            return await self._parse_text_file(file_path, document_id)
        else:
            raise DocumentProcessingError(
                document=file_path,
                operation="format_parsing",
                reason=f"No parser available for format: {format_type}"
            )

    async def _parse_text_file(self, file_path: str, document_id: str) -> ParsedDocument:
        """Parse plain text file and return simple ParsedDocument."""

        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
                content = (await file.read()) or ""

            file_stat = Path(file_path).stat()
            metadata: Dict[str, Any] = {
                "source": f"file://{file_path}",
                "page_count": 1,
                "file_size": file_stat.st_size,
                "content_type": "text/plain",
                "parser": "text-local",
                "processed_at": datetime.utcnow().isoformat(),
            }

            return ParsedDocument(
                document_id=document_id,
                s3_uri=f"file://{file_path}",
                content=content,
                metadata=metadata,
                tables=[],
                confidence=1.0,
            )

        except Exception as e:
            raise DocumentProcessingError(
                document=str(file_path),
                operation="text_file_parsing",
                reason=f"Text file parsing failed: {e}"
            )

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
