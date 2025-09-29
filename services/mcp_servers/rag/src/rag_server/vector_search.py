"""Vector search and retrieval using OpenSearch."""

import logging
from typing import List, Dict, Any, Optional, Tuple
import asyncio

from mavik_common.models import RAGChunk, RAGSearchRequest, RAGSearchResponse
from mavik_common.errors import OpenSearchError, ValidationError
from mavik_aws_clients import OpenSearchClient, BedrockClient

logger = logging.getLogger(__name__)


class VectorSearchService:
    """Handles vector search and document retrieval."""
    
    def __init__(
        self,
        opensearch_client: OpenSearchClient,
        bedrock_client: BedrockClient,
        index_name: str = "mavik-documents",
        embedding_model: str = "amazon.titan-embed-text-v2:0",
    ):
        """Initialize vector search service.
        
        Args:
            opensearch_client: OpenSearch client instance
            bedrock_client: Bedrock client for embeddings
            index_name: OpenSearch index name
            embedding_model: Bedrock embedding model ID
        """
        self.opensearch_client = opensearch_client
        self.bedrock_client = bedrock_client
        self.index_name = index_name
        self.embedding_model = embedding_model
    
    async def search_documents(
        self,
        request: RAGSearchRequest,
    ) -> RAGSearchResponse:
        """Search documents using vector similarity and text matching.
        
        Args:
            request: Search request with query and filters
            
        Returns:
            Search response with ranked chunks
            
        Raises:
            ValidationError: If request validation fails
            OpenSearchError: If search fails
        """
        try:
            if not request.query.strip():
                raise ValidationError("Search query cannot be empty")
            
            logger.info(f"Searching documents: '{request.query}' (limit: {request.limit})")
            
            # Generate query embedding
            query_embedding = await self._generate_embedding(request.query)
            
            # Build OpenSearch query
            search_query = self._build_search_query(
                query_text=request.query,
                query_embedding=query_embedding,
                filters=request.filters,
                use_vector_search=request.use_vector_search,
                use_text_search=request.use_text_search,
            )
            
            # Execute search
            search_results = await self.opensearch_client.search(
                index_name=self.index_name,
                query=search_query,
                size=request.limit,
                source=[
                    "chunk_id", "document_id", "content", "page_number", 
                    "chunk_index", "source_type", "metadata"
                ],
                highlight={
                    "fields": {
                        "content": {
                            "fragment_size": 150,
                            "number_of_fragments": 3
                        }
                    }
                }
            )
            
            # Process results into RAG chunks
            chunks = self._process_search_results(search_results, request.include_metadata)
            
            # Calculate total results
            total_results = search_results.get("hits", {}).get("total", {}).get("value", 0)
            
            logger.info(f"Search returned {len(chunks)} chunks out of {total_results} total")
            
            return RAGSearchResponse(
                chunks=chunks,
                total_results=total_results,
                query=request.query,
                search_time_ms=search_results.get("took", 0),
            )
            
        except Exception as e:
            logger.error(f"Document search failed: {e}")
            if isinstance(e, (ValidationError, OpenSearchError)):
                raise
            raise OpenSearchError(f"Search operation failed: {e}")
    
    async def index_chunks(self, chunks: List[RAGChunk]) -> Dict[str, Any]:
        """Index document chunks in OpenSearch.
        
        Args:
            chunks: List of RAG chunks to index
            
        Returns:
            Indexing results summary
            
        Raises:
            OpenSearchError: If indexing fails
        """
        try:
            if not chunks:
                raise ValidationError("No chunks provided for indexing")
            
            logger.info(f"Indexing {len(chunks)} chunks")
            
            # Generate embeddings for all chunks
            chunk_embeddings = await self._generate_embeddings_batch(
                [chunk.content for chunk in chunks]
            )
            
            # Prepare documents for bulk indexing
            documents = []
            doc_ids = []
            
            for chunk, embedding in zip(chunks, chunk_embeddings):
                doc = {
                    "chunk_id": chunk.chunk_id,
                    "document_id": chunk.document_id,
                    "content": chunk.content,
                    "page_number": chunk.page_number,
                    "chunk_index": chunk.chunk_index,
                    "source_type": chunk.source_type,
                    "metadata": chunk.metadata,
                    "content_embedding": embedding,
                    "indexed_at": chunk.created_at.isoformat() if chunk.created_at else None,
                }
                
                documents.append(doc)
                doc_ids.append(chunk.chunk_id)
            
            # Bulk index documents
            result = await self.opensearch_client.bulk_index(
                index_name=self.index_name,
                documents=documents,
                doc_ids=doc_ids,
            )
            
            # Process results
            indexed_count = len(documents)
            failed_count = 0
            
            if result.get("errors"):
                failed_items = [
                    item for item in result.get("items", [])
                    if "index" in item and "error" in item["index"]
                ]
                failed_count = len(failed_items)
                indexed_count -= failed_count
                
                if failed_items:
                    logger.warning(f"Failed to index {failed_count} chunks")
            
            logger.info(f"Successfully indexed {indexed_count} chunks")
            
            return {
                "indexed_count": indexed_count,
                "failed_count": failed_count,
                "total_count": len(chunks),
            }
            
        except Exception as e:
            logger.error(f"Chunk indexing failed: {e}")
            if isinstance(e, (ValidationError, OpenSearchError)):
                raise
            raise OpenSearchError(f"Indexing operation failed: {e}")
    
    async def delete_document_chunks(self, document_id: str) -> Dict[str, Any]:
        """Delete all chunks for a document.
        
        Args:
            document_id: Document ID to delete chunks for
            
        Returns:
            Deletion results summary
        """
        try:
            logger.info(f"Deleting chunks for document: {document_id}")
            
            # Search for chunks to delete
            search_query = {
                "query": {
                    "term": {
                        "document_id": document_id
                    }
                }
            }
            
            # Use delete by query
            result = await self.opensearch_client.client.delete_by_query(
                index=self.index_name,
                body=search_query,
                refresh=True,
            )
            
            deleted_count = result.get("deleted", 0)
            logger.info(f"Deleted {deleted_count} chunks for document {document_id}")
            
            return {
                "deleted_count": deleted_count,
                "document_id": document_id,
            }
            
        except Exception as e:
            logger.error(f"Chunk deletion failed for {document_id}: {e}")
            raise OpenSearchError(f"Failed to delete chunks: {e}")
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        try:
            embedding = await self.bedrock_client.get_embeddings(
                text=text,
                model_id=self.embedding_model,
            )
            return embedding
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise OpenSearchError(f"Failed to generate embedding: {e}")
    
    async def _generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts in parallel."""
        
        # Limit concurrent requests to avoid rate limits
        semaphore = asyncio.Semaphore(5)
        
        async def generate_single(text: str) -> List[float]:
            async with semaphore:
                return await self._generate_embedding(text)
        
        try:
            embeddings = await asyncio.gather(
                *[generate_single(text) for text in texts],
                return_exceptions=True
            )
            
            # Handle any exceptions
            valid_embeddings = []
            for i, embedding in enumerate(embeddings):
                if isinstance(embedding, Exception):
                    logger.error(f"Failed to generate embedding for text {i}: {embedding}")
                    # Use zero vector as fallback
                    valid_embeddings.append([0.0] * 1536)  # Titan embedding dimension
                else:
                    valid_embeddings.append(embedding)
            
            return valid_embeddings
            
        except Exception as e:
            logger.error(f"Batch embedding generation failed: {e}")
            raise OpenSearchError(f"Failed to generate embeddings: {e}")
    
    def _build_search_query(
        self,
        query_text: str,
        query_embedding: List[float],
        filters: Optional[Dict[str, Any]] = None,
        use_vector_search: bool = True,
        use_text_search: bool = True,
    ) -> Dict[str, Any]:
        """Build OpenSearch query combining vector and text search."""
        
        must_queries = []
        
        # Vector similarity search
        if use_vector_search:
            vector_query = {
                "knn": {
                    "content_embedding": {
                        "vector": query_embedding,
                        "k": 100,  # Retrieve more candidates for reranking
                    }
                }
            }
            must_queries.append(vector_query)
        
        # Text search with BM25
        if use_text_search:
            text_query = {
                "multi_match": {
                    "query": query_text,
                    "fields": ["content^2", "metadata.title^3"],
                    "type": "best_fields",
                    "fuzziness": "AUTO",
                }
            }
            must_queries.append(text_query)
        
        # Build main query
        if len(must_queries) == 1:
            main_query = must_queries[0]
        elif len(must_queries) > 1:
            main_query = {
                "bool": {
                    "should": must_queries,
                    "minimum_should_match": 1,
                }
            }
        else:
            main_query = {"match_all": {}}
        
        # Apply filters
        if filters:
            filter_clauses = []
            
            # Document ID filter
            if "document_ids" in filters and filters["document_ids"]:
                filter_clauses.append({
                    "terms": {
                        "document_id": filters["document_ids"]
                    }
                })
            
            # Source type filter
            if "source_types" in filters and filters["source_types"]:
                filter_clauses.append({
                    "terms": {
                        "source_type": filters["source_types"]
                    }
                })
            
            # MNPI classification filter
            if "mnpi_classification" in filters:
                filter_clauses.append({
                    "term": {
                        "metadata.mnpi_classification": filters["mnpi_classification"]
                    }
                })
            
            # Deal ID filter
            if "deal_id" in filters:
                filter_clauses.append({
                    "term": {
                        "metadata.deal_id": filters["deal_id"]
                    }
                })
            
            # Date range filter
            if "date_range" in filters:
                date_range = filters["date_range"]
                range_filter = {"range": {"indexed_at": {}}}
                
                if "start_date" in date_range:
                    range_filter["range"]["indexed_at"]["gte"] = date_range["start_date"]
                if "end_date" in date_range:
                    range_filter["range"]["indexed_at"]["lte"] = date_range["end_date"]
                
                filter_clauses.append(range_filter)
            
            # Combine with main query
            if filter_clauses:
                main_query = {
                    "bool": {
                        "must": [main_query],
                        "filter": filter_clauses,
                    }
                }
        
        return main_query
    
    def _process_search_results(
        self,
        search_results: Dict[str, Any],
        include_metadata: bool = True,
    ) -> List[RAGChunk]:
        """Process OpenSearch results into RAG chunks."""
        
        chunks = []
        hits = search_results.get("hits", {}).get("hits", [])
        
        for hit in hits:
            source = hit["_source"]
            score = hit["_score"]
            
            # Extract highlights
            highlights = []
            if "highlight" in hit:
                content_highlights = hit["highlight"].get("content", [])
                highlights.extend(content_highlights)
            
            # Create RAG chunk
            chunk = RAGChunk(
                chunk_id=source["chunk_id"],
                document_id=source["document_id"],
                content=source["content"],
                page_number=source.get("page_number"),
                chunk_index=source.get("chunk_index", 0),
                source_type=source.get("source_type", "unknown"),
                metadata=source.get("metadata", {}) if include_metadata else {},
                relevance_score=score,
                highlights=highlights,
            )
            
            chunks.append(chunk)
        
        return chunks
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of search service."""
        try:
            # Check OpenSearch connectivity
            opensearch_healthy = await self.opensearch_client.health_check()
            
            # Check if index exists
            index_exists = await self.opensearch_client.client.indices.exists(
                index=self.index_name
            )
            
            # Get index stats if it exists
            index_stats = {}
            if index_exists:
                try:
                    stats_response = await self.opensearch_client.client.indices.stats(
                        index=self.index_name
                    )
                    index_stats = {
                        "document_count": stats_response["indices"][self.index_name]["total"]["docs"]["count"],
                        "index_size": stats_response["indices"][self.index_name]["total"]["store"]["size_in_bytes"],
                    }
                except Exception as e:
                    logger.warning(f"Failed to get index stats: {e}")
            
            return {
                "opensearch_healthy": opensearch_healthy,
                "index_exists": index_exists,
                "index_name": self.index_name,
                "index_stats": index_stats,
                "embedding_model": self.embedding_model,
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "opensearch_healthy": False,
                "error": str(e),
            }