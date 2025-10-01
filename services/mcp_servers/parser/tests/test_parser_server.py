"""Tests for Parser MCP server components."""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from pathlib import Path
import tempfile
import json

from mavik_common.models import (
    ParserRequest, ParserResponse, ParsedDocument, DocumentMetadata,
    DocumentPage, DocumentElement, DocumentTable, DocumentForm, BoundingBox
)
from mavik_common.errors import ValidationError, DocumentProcessingError

from parser_server.document_parser import (
    DocumentFormatDetector, TextractParser, LocalPDFParser, DocumentParser
)


@pytest.fixture
def mock_textract_client():
    """Mock Textract client."""
    client = Mock()
    client.analyze_document = AsyncMock()
    client.start_document_analysis = AsyncMock()
    client.get_document_analysis = AsyncMock()
    return client


@pytest.fixture
def mock_s3_client():
    """Mock S3 client."""
    client = Mock()
    client.download_file = AsyncMock()
    return client


@pytest.fixture
def sample_textract_response():
    """Sample Textract response for testing."""
    return {
        "Blocks": [
            {
                "Id": "page_1",
                "BlockType": "PAGE",
                "Page": 1,
                "Geometry": {
                    "BoundingBox": {
                        "Width": 1.0,
                        "Height": 1.0,
                        "Left": 0.0,
                        "Top": 0.0
                    }
                },
                "Relationships": [
                    {"Type": "CHILD", "Ids": ["line_1", "line_2"]}
                ]
            },
            {
                "Id": "line_1",
                "BlockType": "LINE",
                "Text": "OFFERING MEMORANDUM",
                "Confidence": 99.5,
                "Page": 1,
                "Geometry": {
                    "BoundingBox": {
                        "Width": 0.8,
                        "Height": 0.05,
                        "Left": 0.1,
                        "Top": 0.1
                    }
                },
                "Relationships": [
                    {"Type": "CHILD", "Ids": ["word_1", "word_2"]}
                ]
            },
            {
                "Id": "line_2",
                "BlockType": "LINE",
                "Text": "300 Hillsborough Street",
                "Confidence": 98.2,
                "Page": 1,
                "Geometry": {
                    "BoundingBox": {
                        "Width": 0.6,
                        "Height": 0.04,
                        "Left": 0.2,
                        "Top": 0.2
                    }
                },
                "Relationships": [
                    {"Type": "CHILD", "Ids": ["word_3", "word_4", "word_5"]}
                ]
            },
            {
                "Id": "word_1",
                "BlockType": "WORD",
                "Text": "OFFERING",
                "Confidence": 99.8,
                "Page": 1,
                "Geometry": {
                    "BoundingBox": {
                        "Width": 0.35,
                        "Height": 0.05,
                        "Left": 0.1,
                        "Top": 0.1
                    }
                }
            },
            {
                "Id": "word_2",
                "BlockType": "WORD",
                "Text": "MEMORANDUM",
                "Confidence": 99.2,
                "Page": 1,
                "Geometry": {
                    "BoundingBox": {
                        "Width": 0.35,
                        "Height": 0.05,
                        "Left": 0.55,
                        "Top": 0.1
                    }
                }
            },
            {
                "Id": "word_3",
                "BlockType": "WORD",
                "Text": "300",
                "Confidence": 98.9,
                "Page": 1
            },
            {
                "Id": "word_4",
                "BlockType": "WORD",
                "Text": "Hillsborough",
                "Confidence": 97.8,
                "Page": 1
            },
            {
                "Id": "word_5",
                "BlockType": "WORD",
                "Text": "Street",
                "Confidence": 98.1,
                "Page": 1
            },
            # Table example
            {
                "Id": "table_1",
                "BlockType": "TABLE",
                "Confidence": 95.0,
                "Page": 1,
                "Geometry": {
                    "BoundingBox": {
                        "Width": 0.8,
                        "Height": 0.3,
                        "Left": 0.1,
                        "Top": 0.4
                    }
                },
                "Relationships": [
                    {"Type": "CHILD", "Ids": ["cell_1", "cell_2", "cell_3", "cell_4"]}
                ]
            },
            # Table cells
            {
                "Id": "cell_1",
                "BlockType": "CELL",
                "RowIndex": 0,
                "ColumnIndex": 0,
                "Confidence": 96.0,
                "EntityTypes": ["COLUMN_HEADER"],
                "Relationships": [
                    {"Type": "CHILD", "Ids": ["word_6"]}
                ]
            },
            {
                "Id": "cell_2",
                "BlockType": "CELL",
                "RowIndex": 0,
                "ColumnIndex": 1,
                "Confidence": 94.5,
                "EntityTypes": ["COLUMN_HEADER"],
                "Relationships": [
                    {"Type": "CHILD", "Ids": ["word_7"]}
                ]
            },
            {
                "Id": "cell_3",
                "BlockType": "CELL",
                "RowIndex": 1,
                "ColumnIndex": 0,
                "Confidence": 97.2,
                "Relationships": [
                    {"Type": "CHILD", "Ids": ["word_8"]}
                ]
            },
            {
                "Id": "cell_4",
                "BlockType": "CELL",
                "RowIndex": 1,
                "ColumnIndex": 1,
                "Confidence": 95.8,
                "Relationships": [
                    {"Type": "CHILD", "Ids": ["word_9"]}
                ]
            },
            # Table cell words
            {
                "Id": "word_6",
                "BlockType": "WORD",
                "Text": "Property",
                "Confidence": 96.0
            },
            {
                "Id": "word_7",
                "BlockType": "WORD",
                "Text": "Value",
                "Confidence": 94.5
            },
            {
                "Id": "word_8",
                "BlockType": "WORD",
                "Text": "Building",
                "Confidence": 97.2
            },
            {
                "Id": "word_9",
                "BlockType": "WORD",
                "Text": "$50M",
                "Confidence": 95.8
            }
        ]
    }


@pytest.fixture
def sample_pdf_content():
    """Sample PDF content for testing."""
    return b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
(Test PDF Content) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000189 00000 n
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
285
%%EOF"""


class TestDocumentFormatDetector:
    """Test document format detection."""

    def test_detect_pdf_format(self, tmp_path):
        """Test PDF format detection."""
        # Create test PDF file
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\nTest content")

        format_type = DocumentFormatDetector.detect_format(str(pdf_file))
        assert format_type == "pdf"

    def test_detect_image_format(self, tmp_path):
        """Test image format detection."""
        # Create test image file with PNG magic bytes
        img_file = tmp_path / "test.png"
        img_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"fake image data")

        format_type = DocumentFormatDetector.detect_format(str(img_file))
        assert format_type == "image"

    def test_detect_text_format(self, tmp_path):
        """Test text format detection."""
        text_file = tmp_path / "test.txt"
        text_file.write_text("Test text content")

        format_type = DocumentFormatDetector.detect_format(str(text_file))
        assert format_type == "text"

    def test_unsupported_format(self, tmp_path):
        """Test unsupported format handling."""
        unsupported_file = tmp_path / "test.xyz"
        unsupported_file.write_text("Some content")

        with pytest.raises(ValidationError, match="Unsupported file extension"):
            DocumentFormatDetector.detect_format(str(unsupported_file))

    def test_invalid_pdf_content(self, tmp_path):
        """Test invalid PDF content detection."""
        fake_pdf = tmp_path / "fake.pdf"
        fake_pdf.write_bytes(b"Not a real PDF file")

        with pytest.raises(ValidationError, match="File does not appear to be a valid PDF"):
            DocumentFormatDetector.detect_format(str(fake_pdf))

    def test_is_supported(self, tmp_path):
        """Test format support checking."""
        # Supported format
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\nContent")
        assert DocumentFormatDetector.is_supported(str(pdf_file)) is True

        # Unsupported format
        bad_file = tmp_path / "test.bad"
        bad_file.write_text("Content")
        assert DocumentFormatDetector.is_supported(str(bad_file)) is False


class TestTextractParser:
    """Test Textract parsing functionality."""

    @pytest.mark.asyncio
    async def test_parse_document_sync(self, mock_textract_client, sample_textract_response):
        """Test synchronous document parsing."""
        # Setup mock response
        mock_textract_client.analyze_document.return_value = sample_textract_response

        parser = TextractParser(mock_textract_client)

        # Parse document (no advanced features)
        result = await parser.parse_document(
            s3_bucket="test-bucket",
            s3_key="test-doc.pdf",
            document_id="test_doc",
            extract_tables=False,
            extract_forms=False,
        )

        # Verify result
        assert isinstance(result, ParsedDocument)
        assert result.metadata.document_id == "test_doc"
        assert len(result.pages) == 1
        assert len(result.pages[0].elements) == 2  # Two lines
        assert result.pages[0].elements[0].text == "OFFERING MEMORANDUM"
        assert result.pages[0].elements[1].text == "300 Hillsborough Street"

        # Verify Textract was called correctly
        mock_textract_client.analyze_document.assert_called_once_with(
            s3_bucket="test-bucket",
            s3_key="test-doc.pdf"
        )

    @pytest.mark.asyncio
    async def test_parse_document_async(self, mock_textract_client, sample_textract_response):
        """Test asynchronous document parsing with advanced features."""
        # Setup mock responses
        mock_textract_client.start_document_analysis.return_value = {"JobId": "job123"}

        # Mock successful job completion
        completed_response = sample_textract_response.copy()
        completed_response["JobStatus"] = "SUCCEEDED"
        mock_textract_client.get_document_analysis.return_value = completed_response

        parser = TextractParser(mock_textract_client)

        # Parse document with advanced features
        result = await parser.parse_document(
            s3_bucket="test-bucket",
            s3_key="test-doc.pdf",
            document_id="test_doc",
            extract_tables=True,
            extract_forms=True,
        )

        # Verify result
        assert isinstance(result, ParsedDocument)
        assert len(result.tables) == 1  # One table in sample response
        assert len(result.tables[0].rows) == 2  # Two rows in table
        assert result.tables[0].rows[0] == ["Property", "Value"]  # Header row
        assert result.tables[0].rows[1] == ["Building", "$50M"]   # Data row

        # Verify async workflow was used
        mock_textract_client.start_document_analysis.assert_called_once()
        mock_textract_client.get_document_analysis.assert_called_once_with("job123")

    @pytest.mark.asyncio
    async def test_table_processing(self, mock_textract_client, sample_textract_response):
        """Test table extraction and processing."""
        mock_textract_client.analyze_document.return_value = sample_textract_response

        parser = TextractParser(mock_textract_client)
        result = await parser.parse_document(
            s3_bucket="test-bucket",
            s3_key="test-doc.pdf",
            document_id="test_doc",
        )

        # Verify table structure
        assert len(result.tables) == 1
        table = result.tables[0]

        assert table.table_id == "table_1"
        assert len(table.rows) == 2
        assert table.rows[0] == ["Property", "Value"]  # Headers
        assert table.rows[1] == ["Building", "$50M"]   # Data
        assert table.confidence == 95.0

    @pytest.mark.asyncio
    async def test_bounding_box_extraction(self, mock_textract_client, sample_textract_response):
        """Test bounding box extraction from geometry."""
        mock_textract_client.analyze_document.return_value = sample_textract_response

        parser = TextractParser(mock_textract_client)
        result = await parser.parse_document(
            s3_bucket="test-bucket",
            s3_key="test-doc.pdf",
            document_id="test_doc",
        )

        # Check line bounding boxes
        line1 = result.pages[0].elements[0]
        assert line1.bounding_box is not None
        assert line1.bounding_box.left == 0.1
        assert line1.bounding_box.top == 0.1
        assert line1.bounding_box.width == 0.8
        assert line1.bounding_box.height == 0.05

    @pytest.mark.asyncio
    async def test_job_failure_handling(self, mock_textract_client):
        """Test handling of failed Textract jobs."""
        # Setup mock responses
        mock_textract_client.start_document_analysis.return_value = {"JobId": "job123"}
        mock_textract_client.get_document_analysis.return_value = {
            "JobStatus": "FAILED",
            "StatusMessage": "Processing failed due to invalid document"
        }

        parser = TextractParser(mock_textract_client)

        with pytest.raises(DocumentProcessingError, match="Textract job failed"):
            await parser.parse_document(
                s3_bucket="test-bucket",
                s3_key="bad-doc.pdf",
                document_id="test_doc",
                extract_tables=True,
            )


class TestLocalPDFParser:
    """Test local PDF parsing functionality."""

    @pytest.mark.asyncio
    async def test_parse_simple_pdf(self, tmp_path, sample_pdf_content):
        """Test parsing a simple PDF."""
        # Create test PDF file
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(sample_pdf_content)

        parser = LocalPDFParser()

        # Mock PyPDF2 to avoid dependency on actual PDF parsing
        with patch('parser_server.document_parser.PyPDF2.PdfReader') as mock_reader:
            # Mock page with text
            mock_page = Mock()
            mock_page.extract_text.return_value = "Test PDF Content\nSecond line of text"

            mock_pdf = Mock()
            mock_pdf.pages = [mock_page]
            mock_reader.return_value = mock_pdf

            result = await parser.parse_pdf(str(pdf_file), "test_pdf")

        # Verify result
        assert isinstance(result, ParsedDocument)
        assert result.metadata.document_id == "test_pdf"
        assert result.metadata.parser_version == "pypdf2-local"
        assert len(result.pages) == 1
        assert len(result.pages[0].elements) == 1
        assert result.pages[0].elements[0].text == "Test PDF Content\nSecond line of text"
        assert result.full_text == "Test PDF Content\nSecond line of text"

    @pytest.mark.asyncio
    async def test_parse_pdf_with_extraction_error(self, tmp_path, sample_pdf_content):
        """Test handling of PDF extraction errors."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(sample_pdf_content)

        parser = LocalPDFParser()

        with patch('parser_server.document_parser.PyPDF2.PdfReader') as mock_reader:
            # Mock page that raises exception
            mock_page = Mock()
            mock_page.extract_text.side_effect = Exception("Extraction failed")

            mock_pdf = Mock()
            mock_pdf.pages = [mock_page]
            mock_reader.return_value = mock_pdf

            result = await parser.parse_pdf(str(pdf_file), "test_pdf")

        # Should create empty page on extraction error
        assert len(result.pages) == 1
        assert len(result.pages[0].elements) == 0


class TestDocumentParser:
    """Test main document parser orchestration."""

    @pytest.mark.asyncio
    async def test_parse_s3_document_with_textract(self, mock_textract_client, mock_s3_client):
        """Test parsing S3 document with Textract."""
        # Setup mock Textract response
        mock_textract_response = {
            "Blocks": [
                {
                    "Id": "page_1",
                    "BlockType": "PAGE",
                    "Page": 1,
                    "Relationships": [{"Type": "CHILD", "Ids": ["line_1"]}]
                },
                {
                    "Id": "line_1",
                    "BlockType": "LINE",
                    "Text": "S3 Document Content",
                    "Confidence": 99.0,
                    "Page": 1,
                    "Relationships": [{"Type": "CHILD", "Ids": ["word_1"]}]
                },
                {
                    "Id": "word_1",
                    "BlockType": "WORD",
                    "Text": "Content",
                    "Confidence": 99.0,
                    "Page": 1
                }
            ]
        }

        # Create parser with Textract
        textract_parser = TextractParser(mock_textract_client)
        textract_parser.parse_document = AsyncMock(return_value=ParsedDocument(
            metadata=DocumentMetadata(
                document_id="s3_test",
                source_location="s3://bucket/key",
                processing_timestamp=datetime.utcnow(),
                total_pages=1,
                content_type="application/pdf",
                file_size=1024,
                parser_version="textract-1.0"
            ),
            pages=[],
            tables=[],
            forms=[],
            full_text="S3 Document Content"
        ))

        parser = DocumentParser(
            textract_client=mock_textract_client,
            s3_client=mock_s3_client,
        )
        parser.textract_parser = textract_parser

        # Parse S3 document
        result = await parser.parse_document(
            document_source="s3://test-bucket/test-doc.pdf",
            document_id="s3_test",
        )

        # Verify result
        assert isinstance(result, ParsedDocument)
        assert result.metadata.document_id == "s3_test"
        assert result.full_text == "S3 Document Content"

        # Verify Textract parser was called
        textract_parser.parse_document.assert_called_once_with(
            s3_bucket="test-bucket",
            s3_key="test-doc.pdf",
            document_id="s3_test",
            extract_tables=True,
            extract_forms=True,
            extract_signatures=False,
        )

    @pytest.mark.asyncio
    async def test_parse_local_pdf(self, tmp_path):
        """Test parsing local PDF file."""
        # Create test PDF
        pdf_file = tmp_path / "local.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\nTest content")

        parser = DocumentParser(use_local_fallback=True)

        # Mock LocalPDFParser
        with patch.object(parser.pdf_parser, 'parse_pdf') as mock_parse:
            mock_parse.return_value = ParsedDocument(
                metadata=DocumentMetadata(
                    document_id="local_test",
                    source_location=str(pdf_file),
                    processing_timestamp=datetime.utcnow(),
                    total_pages=1,
                    content_type="application/pdf",
                    file_size=pdf_file.stat().st_size,
                    parser_version="pypdf2-local"
                ),
                pages=[],
                tables=[],
                forms=[],
                full_text="Local PDF Content"
            )

            result = await parser.parse_document(
                document_source=str(pdf_file),
                document_id="local_test",
            )

        # Verify result
        assert isinstance(result, ParsedDocument)
        assert result.metadata.document_id == "local_test"
        assert result.full_text == "Local PDF Content"

        # Verify local parser was called
        mock_parse.assert_called_once_with(str(pdf_file), "local_test")

    @pytest.mark.asyncio
    async def test_parse_text_file(self, tmp_path):
        """Test parsing plain text file."""
        # Create test text file
        text_file = tmp_path / "test.txt"
        text_file.write_text("This is test content\nWith multiple lines")

        parser = DocumentParser()

        result = await parser.parse_document(
            document_source=str(text_file),
            document_id="text_test",
        )

        # Verify result
        assert isinstance(result, ParsedDocument)
        assert result.metadata.document_id == "text_test"
        assert result.metadata.content_type == "text/plain"
        assert len(result.pages) == 1
        assert result.full_text == "This is test content\nWith multiple lines"

    @pytest.mark.asyncio
    async def test_unsupported_format_error(self, tmp_path):
        """Test error handling for unsupported formats."""
        # Create unsupported file
        bad_file = tmp_path / "test.xyz"
        bad_file.write_text("Content")

        parser = DocumentParser()

        with pytest.raises(ValidationError, match="Unsupported document format"):
            await parser.parse_document(
                document_source=str(bad_file),
                document_id="bad_test",
            )

    @pytest.mark.asyncio
    async def test_health_check(self, mock_textract_client, mock_s3_client):
        """Test parser health check."""
        parser = DocumentParser(
            textract_client=mock_textract_client,
            s3_client=mock_s3_client,
        )

        health = await parser.health_check()

        # Verify health response
        assert "parsers" in health
        assert health["parsers"]["textract"] is True
        assert health["parsers"]["local_pdf"] is True
        assert health["parsers"]["local_text"] is True

        assert "capabilities" in health
        assert health["capabilities"]["s3_documents"] is True
        assert health["capabilities"]["table_extraction"] is True
        assert health["capabilities"]["form_extraction"] is True

        assert "supported_formats" in health
        assert "pdf" in health["supported_formats"]
        assert "image" in health["supported_formats"]
        assert "text" in health["supported_formats"]


@pytest.mark.asyncio
async def test_integration_workflow(mock_textract_client, sample_textract_response):
    """Test complete parsing workflow integration."""

    # Setup Textract mock
    mock_textract_client.analyze_document.return_value = sample_textract_response

    # Create parser
    parser = DocumentParser(textract_client=mock_textract_client)

    # Parse document
    result = await parser.parse_document(
        document_source="s3://test-bucket/integration-doc.pdf",
        document_id="integration_test",
        parser_options={
            "extract_tables": True,
            "extract_forms": False,
        }
    )

    # Verify complete workflow
    assert isinstance(result, ParsedDocument)
    assert result.metadata.document_id == "integration_test"
    assert len(result.pages) == 1
    assert len(result.tables) == 1
    assert len(result.forms) == 0  # Forms extraction disabled

    # Verify page content
    page = result.pages[0]
    assert len(page.elements) == 2
    assert page.elements[0].text == "OFFERING MEMORANDUM"
    assert page.elements[1].text == "300 Hillsborough Street"

    # Verify table content
    table = result.tables[0]
    assert table.table_id == "table_1"
    assert table.rows == [["Property", "Value"], ["Building", "$50M"]]

    # Verify full text extraction
    expected_text = "OFFERING MEMORANDUM\n300 Hillsborough Street"
    assert result.full_text == expected_text

    # Verify Textract was called correctly
    mock_textract_client.analyze_document.assert_called_once()
