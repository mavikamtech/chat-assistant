"""AWS OpenSearch client for document search and retrieval."""

import logging
from typing import Any, Dict, List, Optional
import json

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..common.errors import (
    OpenSearchError,
    AWSServiceError,
)

logger = logging.getLogger(__name__)


class OpenSearchClient:
    """AWS OpenSearch client for document indexing and search."""
    
    def __init__(
        self,
        domain_endpoint: str,
        region_name: str = "us-east-1",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        use_ssl: bool = True,
        verify_certs: bool = True,
    ):
        """Initialize OpenSearch client.
        
        Args:
            domain_endpoint: OpenSearch domain endpoint
            region_name: AWS region
            aws_access_key_id: Optional explicit AWS credentials
            aws_secret_access_key: Optional explicit AWS credentials
            use_ssl: Whether to use SSL
            verify_certs: Whether to verify SSL certificates
        """
        self.domain_endpoint = domain_endpoint
        self.region_name = region_name
        
        try:
            # Set up AWS authentication
            if aws_access_key_id and aws_secret_access_key:
                credentials = boto3.Session(
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                    region_name=region_name,
                ).get_credentials()
            else:
                credentials = boto3.Session(region_name=region_name).get_credentials()
            
            awsauth = AWS4Auth(
                credentials.access_key,
                credentials.secret_key,
                region_name,
                "es",
                session_token=credentials.token,
            )
            
            # Initialize OpenSearch client
            self.client = OpenSearch(
                hosts=[{"host": domain_endpoint, "port": 443}],
                http_auth=awsauth,
                use_ssl=use_ssl,
                verify_certs=verify_certs,
                connection_class=RequestsHttpConnection,
                timeout=30,
                max_retries=3,
                retry_on_timeout=True,
            )
            
            logger.info(f"OpenSearch client initialized for domain: {domain_endpoint}")
            
        except Exception as e:
            raise AWSServiceError(f"Failed to initialize OpenSearch client: {e}")
    
    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def create_index(
        self,
        index_name: str,
        mapping: Optional[Dict[str, Any]] = None,
        settings: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Create an index with optional mapping and settings.
        
        Args:
            index_name: Name of the index
            mapping: Optional index mapping
            settings: Optional index settings
            
        Returns:
            True if created successfully
            
        Raises:
            OpenSearchError: For OpenSearch-specific errors
        """
        try:
            body = {}
            
            if settings:
                body["settings"] = settings
                
            if mapping:
                body["mappings"] = mapping
            
            logger.info(f"Creating index: {index_name}")
            response = self.client.indices.create(
                index=index_name,
                body=body,
                ignore=400,  # Ignore if index already exists
            )
            
            if response.get("acknowledged"):
                logger.info(f"Index created: {index_name}")
                return True
            else:
                logger.warning(f"Index creation not acknowledged: {index_name}")
                return False
                
        except Exception as e:
            raise OpenSearchError(f"Failed to create index {index_name}: {e}")
    
    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def index_document(
        self,
        index_name: str,
        document: Dict[str, Any],
        doc_id: Optional[str] = None,
    ) -> str:
        """Index a document.
        
        Args:
            index_name: Index name
            document: Document to index
            doc_id: Optional document ID
            
        Returns:
            Document ID
            
        Raises:
            OpenSearchError: For indexing errors
        """
        try:
            logger.debug(f"Indexing document to {index_name}")
            
            response = self.client.index(
                index=index_name,
                body=document,
                id=doc_id,
                refresh=True,  # Make document immediately searchable
            )
            
            document_id = response["_id"]
            logger.debug(f"Document indexed with ID: {document_id}")
            
            return document_id
            
        except Exception as e:
            raise OpenSearchError(f"Failed to index document: {e}")
    
    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def bulk_index(
        self,
        index_name: str,
        documents: List[Dict[str, Any]],
        doc_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Bulk index multiple documents.
        
        Args:
            index_name: Index name
            documents: List of documents to index
            doc_ids: Optional list of document IDs
            
        Returns:
            Bulk operation results
            
        Raises:
            OpenSearchError: For bulk indexing errors
        """
        try:
            body = []
            
            for i, document in enumerate(documents):
                # Add action metadata
                action = {"index": {"_index": index_name}}
                if doc_ids and i < len(doc_ids):
                    action["index"]["_id"] = doc_ids[i]
                
                body.append(action)
                body.append(document)
            
            logger.info(f"Bulk indexing {len(documents)} documents to {index_name}")
            
            response = self.client.bulk(
                body=body,
                refresh=True,
            )
            
            # Check for errors
            if response.get("errors"):
                errors = []
                for item in response.get("items", []):
                    if "index" in item and "error" in item["index"]:
                        errors.append(item["index"]["error"])
                
                if errors:
                    logger.warning(f"Bulk indexing errors: {errors}")
            
            logger.info(f"Bulk indexing completed: {len(documents)} documents")
            return response
            
        except Exception as e:
            raise OpenSearchError(f"Failed to bulk index documents: {e}")
    
    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def search(
        self,
        index_name: str,
        query: Dict[str, Any],
        size: int = 10,
        from_: int = 0,
        source: Optional[List[str]] = None,
        highlight: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Search documents in an index.
        
        Args:
            index_name: Index name to search
            query: Elasticsearch query DSL
            size: Number of results to return
            from_: Starting offset
            source: Fields to include in response
            highlight: Highlighting configuration
            
        Returns:
            Search results
            
        Raises:
            OpenSearchError: For search errors
        """
        try:
            body = {
                "query": query,
                "size": size,
                "from": from_,
            }
            
            if source:
                body["_source"] = source
                
            if highlight:
                body["highlight"] = highlight
            
            logger.debug(f"Searching index {index_name}")
            
            response = self.client.search(
                index=index_name,
                body=body,
            )
            
            hits = response.get("hits", {})
            total = hits.get("total", {}).get("value", 0)
            
            logger.debug(f"Search returned {total} total results, showing {len(hits.get('hits', []))}")
            
            return response
            
        except Exception as e:
            raise OpenSearchError(f"Search failed: {e}")
    
    async def vector_search(
        self,
        index_name: str,
        vector_field: str,
        query_vector: List[float],
        size: int = 10,
        filter_query: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Perform vector similarity search.
        
        Args:
            index_name: Index name
            vector_field: Name of the vector field
            query_vector: Query vector
            size: Number of results to return
            filter_query: Optional filter query
            
        Returns:
            Search results with similarity scores
            
        Raises:
            OpenSearchError: For vector search errors
        """
        try:
            query = {
                "knn": {
                    vector_field: {
                        "vector": query_vector,
                        "k": size,
                    }
                }
            }
            
            # Add filter if provided
            if filter_query:
                query = {
                    "bool": {
                        "must": [query],
                        "filter": filter_query,
                    }
                }
            
            body = {
                "query": query,
                "size": size,
            }
            
            logger.debug(f"Vector search in index {index_name}")
            
            response = self.client.search(
                index=index_name,
                body=body,
            )
            
            hits = response.get("hits", {})
            total = hits.get("total", {}).get("value", 0)
            
            logger.debug(f"Vector search returned {total} total results")
            
            return response
            
        except Exception as e:
            raise OpenSearchError(f"Vector search failed: {e}")
    
    async def get_document(
        self,
        index_name: str,
        doc_id: str,
        source: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get a document by ID.
        
        Args:
            index_name: Index name
            doc_id: Document ID
            source: Fields to include in response
            
        Returns:
            Document data or None if not found
            
        Raises:
            OpenSearchError: For retrieval errors
        """
        try:
            kwargs = {
                "index": index_name,
                "id": doc_id,
            }
            
            if source:
                kwargs["_source"] = source
            
            response = self.client.get(**kwargs)
            
            if response.get("found"):
                return response.get("_source")
            else:
                return None
                
        except Exception as e:
            if "not found" in str(e).lower():
                return None
            raise OpenSearchError(f"Failed to get document {doc_id}: {e}")
    
    async def delete_document(
        self,
        index_name: str,
        doc_id: str,
    ) -> bool:
        """Delete a document by ID.
        
        Args:
            index_name: Index name
            doc_id: Document ID
            
        Returns:
            True if deleted successfully
            
        Raises:
            OpenSearchError: For deletion errors
        """
        try:
            response = self.client.delete(
                index=index_name,
                id=doc_id,
                refresh=True,
            )
            
            return response.get("result") == "deleted"
            
        except Exception as e:
            raise OpenSearchError(f"Failed to delete document {doc_id}: {e}")
    
    async def delete_index(self, index_name: str) -> bool:
        """Delete an index.
        
        Args:
            index_name: Index name to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            response = self.client.indices.delete(
                index=index_name,
                ignore=[400, 404],  # Ignore if index doesn't exist
            )
            
            return response.get("acknowledged", False)
            
        except Exception as e:
            raise OpenSearchError(f"Failed to delete index {index_name}: {e}")
    
    async def health_check(self) -> bool:
        """Check OpenSearch cluster health.
        
        Returns:
            True if cluster is accessible
        """
        try:
            response = self.client.cluster.health()
            status = response.get("status")
            
            logger.debug(f"Cluster health status: {status}")
            return status in ["green", "yellow"]
            
        except Exception as e:
            logger.error(f"OpenSearch health check failed: {e}")
            return False