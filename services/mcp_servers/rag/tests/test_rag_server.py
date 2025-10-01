"""Tests for RAG MCP server components."""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
from typing import List, Dict, Any

from mavik_common.models import RAGSearchRequest, RAGSearchResponse, RAGChunk
from mavik_common.errors import ValidationError, OpenSearchError

from rag_server.vector_search import VectorSearchService
from rag_server.document_processor import DocumentProcessor, DocumentIndexer
from rag_server.health import HealthMonitor


@pytest.fixture
def mock_opensearch_client():
    """Mock OpenSearch client."""
    client = Mock()
    client.search = AsyncMock()
    client.bulk_index = AsyncMock()
    client.health_check = AsyncMock(return_value=True)
    client.client.indices.exists = AsyncMock(return_value=True)
    client.client.indices.stats = AsyncMock(return_value={
        "indices": {
            "test-index": {
                "total": {
                    "docs": {"count": 100},
                    "store": {"size_in_bytes": 1024000}
                }
            }
        }
    })
    client.client.delete_by_query = AsyncMock(return_value={"deleted": 5})
    return client


@pytest.fixture
def mock_bedrock_client():
    """Mock Bedrock client."""
    client = Mock()
    client.get_embeddings = AsyncMock(return_value=[0.1] * 1536)
    return client


@pytest.fixture
def vector_search_service(mock_opensearch_client, mock_bedrock_client):
    """Vector search service with mocked clients."""
    return VectorSearchService(
        opensearch_client=mock_opensearch_client,
        bedrock_client=mock_bedrock_client,
        index_name="test-index",
    )


class TestVectorSearchService:
    """Test vector search functionality."""

    @pytest.mark.asyncio
    async def test_search_documents_success(self, vector_search_service, mock_opensearch_client):
        """Test successful document search."""

        # Mock OpenSearch response
        mock_opensearch_client.search.return_value = {
            "took": 10,
            "hits": {
                "total": {"value": 2},
                "hits": [
                    {
                        "_score": 0.9,
                        "_source": {
                            "chunk_id": "chunk_1",
                            "document_id": "doc_1",
                            "content": "Test content 1",
                            "page_number": 1,
                            "chunk_index": 0,
                            "source_type": "pdf",
                            "metadata": {"title": "Test Document"},
                        },
                        "highlight": {
                            "content": ["Test <em>content</em> 1"]
                        }
                    },
                    {
                        "_score": 0.8,
                        "_source": {
                            "chunk_id": "chunk_2",
                            "document_id": "doc_1",
                            "content": "Test content 2",
                            "page_number": 2,
                            "chunk_index": 1,
                            "source_type": "pdf",
                            "metadata": {"title": "Test Document"},
                        }
                    }
                ]
            }
        }

        # Create search request
        request = RAGSearchRequest(
            query="test query",
            limit=10,
            use_vector_search=True,
            use_text_search=True,
        )

        # Execute search
        response = await vector_search_service.search_documents(request)

        # Verify response
        assert isinstance(response, RAGSearchResponse)
        assert response.total_results == 2
        assert len(response.chunks) == 2
        assert response.chunks[0].chunk_id == "chunk_1"
        assert response.chunks[0].relevance_score == 0.9
        assert response.chunks[0].highlights == ["Test <em>content</em> 1"]
        assert response.search_time_ms == 10

    @pytest.mark.asyncio
    async def test_search_documents_empty_query(self, vector_search_service):
        """Test search with empty query."""

        request = RAGSearchRequest(
            query="   ",  # Empty/whitespace query
            limit=10,
        )

        with pytest.raises(ValidationError, match="Search query cannot be empty"):
            await vector_search_service.search_documents(request)

    @pytest.mark.asyncio
    async def test_search_documents_with_filters(self, vector_search_service, mock_opensearch_client):
        """Test search with filters."""

        # Mock successful response
        mock_opensearch_client.search.return_value = {
            "took": 5,
            "hits": {"total": {"value": 0}, "hits": []}
        }

        request = RAGSearchRequest(
            query="test",
            limit=5,
            filters={
                "document_ids": ["doc_1", "doc_2"],
                "source_types": ["pdf"],
                "mnpi_classification": "public",
                "deal_id": "deal_123",
            }
        )

        response = await vector_search_service.search_documents(request)

        # Verify search was called with filters
        call_args = mock_opensearch_client.search.call_args
        query = call_args[1]["query"]

        # Should have filters in the query
        assert "bool" in query
        assert "filter" in query["bool"]

    @pytest.mark.asyncio
    async def test_index_chunks_success(self, vector_search_service, mock_opensearch_client):
        """Test successful chunk indexing."""

        # Mock successful bulk index response
        mock_opensearch_client.bulk_index.return_value = {
            "errors": False,
            "items": [{"index": {"status": 201}}] * 2
        }

        # Create test chunks
        chunks = [
            RAGChunk(
                chunk_id="chunk_1",
                document_id="doc_1",
                content="Test content 1",
                page_number=1,
                chunk_index=0,
                source_type="pdf",
                metadata={"title": "Test"},
            ),
            RAGChunk(
                chunk_id="chunk_2",
                document_id="doc_1",
                content="Test content 2",
                page_number=1,
                chunk_index=1,
                source_type="pdf",
                metadata={"title": "Test"},
            )
        ]

        # Execute indexing
        result = await vector_search_service.index_chunks(chunks)

        # Verify results
        assert result["indexed_count"] == 2
        assert result["failed_count"] == 0
        assert result["total_count"] == 2

    @pytest.mark.asyncio
    async def test_index_chunks_with_failures(self, vector_search_service, mock_opensearch_client):
        """Test chunk indexing with some failures."""

        # Mock response with some failures
        mock_opensearch_client.bulk_index.return_value = {
            "errors": True,
            "items": [
                {"index": {"status": 201}},  # Success
                {"index": {"status": 400, "error": {"reason": "Invalid data"}}},  # Failure
            ]
        }

        chunks = [
            RAGChunk(chunk_id="chunk_1", document_id="doc_1", content="Content 1"),
            RAGChunk(chunk_id="chunk_2", document_id="doc_1", content="Content 2"),
        ]

        result = await vector_search_service.index_chunks(chunks)

        assert result["indexed_count"] == 1
        assert result["failed_count"] == 1
        assert result["total_count"] == 2

    @pytest.mark.asyncio
    async def test_delete_document_chunks(self, vector_search_service, mock_opensearch_client):
        """Test document chunk deletion."""

        result = await vector_search_service.delete_document_chunks("doc_1")

        assert result["deleted_count"] == 5
        assert result["document_id"] == "doc_1"

        # Verify delete_by_query was called
        mock_opensearch_client.client.delete_by_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check(self, vector_search_service):
        """Test health check functionality."""

        health = await vector_search_service.health_check()

        assert "opensearch_healthy" in health
        assert "index_exists" in health
        assert "index_name" in health
        assert health["index_name"] == "test-index"


class TestDocumentProcessor:
    """Test document processing functionality."""

    def test_process_text_basic(self):
        """Test basic text processing."""

        processor = DocumentProcessor(chunk_size=100, chunk_overlap=20)

        text = "This is a test document. " * 20  # Long text
        chunks = processor.process_text(
            text=text,
            document_id="test_doc",
            source_type="text",
            metadata={"title": "Test"},
        )

        assert len(chunks) > 1  # Should be split into multiple chunks
        assert all(isinstance(chunk, RAGChunk) for chunk in chunks)
        assert all(chunk.document_id == "test_doc" for chunk in chunks)
        assert all(chunk.source_type == "text" for chunk in chunks)

    def test_process_text_short(self):
        """Test processing short text that doesn't need chunking."""

        processor = DocumentProcessor(chunk_size=1000, chunk_overlap=100)

        text = "Short text that fits in one chunk."
        chunks = processor.process_text(
            text=text,
            document_id="test_doc",
            source_type="text",
        )

        assert len(chunks) == 1
        assert chunks[0].content == text
        assert chunks[0].chunk_index == 0

    def test_chunk_overlap(self):
        """Test that chunk overlap works correctly."""

        processor = DocumentProcessor(chunk_size=50, chunk_overlap=10)

        # Create text with clear sentence boundaries
        sentences = [f"Sentence {i}. " for i in range(20)]
        text = "".join(sentences)

        chunks = processor.process_text(
            text=text,
            document_id="test_doc",
            source_type="text",
        )

        # Check that consecutive chunks have some overlap
        if len(chunks) > 1:
            # Find common words between consecutive chunks
            chunk1_words = set(chunks[0].content.split())
            chunk2_words = set(chunks[1].content.split())
            overlap_words = chunk1_words.intersection(chunk2_words)

            # Should have some overlapping words (though exact overlap depends on sentence boundaries)
            assert len(overlap_words) > 0


class TestHealthMonitor:
    """Test health monitoring functionality."""

    @pytest.mark.asyncio
    async def test_run_health_check(self, vector_search_service):
        """Test health check execution."""

        monitor = HealthMonitor(vector_search_service, check_interval_seconds=60)

        health_result = await monitor.run_health_check()

        assert "timestamp" in health_result
        assert "overall_status" in health_result
        assert "components" in health_result
        assert "performance" in health_result
        assert health_result["overall_status"] in ["healthy", "degraded", "unhealthy"]

    def test_health_summary_empty(self):
        """Test health summary with no data."""

        monitor = HealthMonitor(Mock(), check_interval_seconds=60)
        summary = monitor.get_health_summary(hours=24)

        assert "No health data available" in summary["summary"]
        assert summary["period_hours"] == 24

    def test_health_summary_with_data(self):
        """Test health summary with sample data."""

        monitor = HealthMonitor(Mock(), check_interval_seconds=60)

        # Add sample health checks
        now = datetime.utcnow()
        for i in range(5):
            health_check = {
                "timestamp": now.isoformat(),
                "overall_status": "healthy" if i < 4 else "degraded",
                "performance": {"search_latency_ms": 100 + i * 10},
            }
            monitor._add_to_history(health_check)

        summary = monitor.get_health_summary(hours=24)

        assert summary["total_checks"] == 5
        assert summary["status_distribution"]["healthy"] == 4
        assert summary["status_distribution"]["degraded"] == 1
        assert summary["uptime_percentage"] == 100.0  # Both healthy and degraded count as uptime


@pytest.mark.asyncio
async def test_integration_search_flow(mock_opensearch_client, mock_bedrock_client):
    """Test complete search flow integration."""

    # Setup vector search service
    service = VectorSearchService(
        opensearch_client=mock_opensearch_client,
        bedrock_client=mock_bedrock_client,
        index_name="test-index",
    )

    # Mock OpenSearch response
    mock_opensearch_client.search.return_value = {
        "took": 15,
        "hits": {
            "total": {"value": 1},
            "hits": [{
                "_score": 0.95,
                "_source": {
                    "chunk_id": "integration_chunk_1",
                    "document_id": "integration_doc",
                    "content": "Integration test content for document search",
                    "page_number": 1,
                    "chunk_index": 0,
                    "source_type": "pdf",
                    "metadata": {
                        "title": "Integration Test Document",
                        "deal_id": "integration_deal_123",
                        "mnpi_classification": "public",
                    },
                }
            }]
        }
    }

    # Execute search
    request = RAGSearchRequest(
        query="integration test",
        limit=10,
        filters={"deal_id": "integration_deal_123"},
        include_metadata=True,
    )

    response = await service.search_documents(request)

    # Verify complete flow
    assert response.total_results == 1
    assert len(response.chunks) == 1

    chunk = response.chunks[0]
    assert chunk.chunk_id == "integration_chunk_1"
    assert chunk.document_id == "integration_doc"
    assert chunk.content == "Integration test content for document search"
    assert chunk.metadata["deal_id"] == "integration_deal_123"
    assert chunk.metadata["mnpi_classification"] == "public"
    assert chunk.relevance_score == 0.95

    # Verify embedding was generated for query
    mock_bedrock_client.get_embeddings.assert_called_once()

    # Verify search was executed with proper parameters
    mock_opensearch_client.search.assert_called_once()
    call_kwargs = mock_opensearch_client.search.call_args[1]
    assert call_kwargs["index_name"] == "test-index"
    assert call_kwargs["size"] == 10
