"""FastAPI server for RAG MCP service with WebSocket support."""

import logging
import asyncio
from datetime import datetime
from typing import Any, Dict, Optional
import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from mavik_common.models import (
    RAGSearchRequest, RAGSearchResponse, RAGIndexRequest, RAGIndexResponse,
    RAGDeleteRequest, RAGDeleteResponse, MCPRequest, MCPResponse,
    RAGChunk, DocumentMetadata
)
from mavik_common.errors import ValidationError, OpenSearchError, DocumentProcessingError
from mavik_config.settings import get_settings
from mavik_aws_clients import OpenSearchClient, BedrockClient, S3Client, TextractClient

from .document_processor import DocumentProcessor, DocumentIndexer
from .vector_search import VectorSearchService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global variables for dependency injection
settings = get_settings()
app = FastAPI(
    title="Mavik RAG MCP Server",
    description="Document search and retrieval service using OpenSearch and Bedrock",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
opensearch_client: Optional[OpenSearchClient] = None
bedrock_client: Optional[BedrockClient] = None
s3_client: Optional[S3Client] = None
textract_client: Optional[TextractClient] = None
document_processor: Optional[DocumentProcessor] = None
document_indexer: Optional[DocumentIndexer] = None
vector_search: Optional[VectorSearchService] = None


async def initialize_services():
    """Initialize AWS clients and services."""
    global opensearch_client, bedrock_client, s3_client, textract_client
    global document_processor, document_indexer, vector_search
    
    try:
        logger.info("Initializing RAG MCP services...")
        
        # Initialize AWS clients
        opensearch_client = OpenSearchClient()
        bedrock_client = BedrockClient()
        s3_client = S3Client()
        textract_client = TextractClient()
        
        # Initialize document services
        document_processor = DocumentProcessor()
        document_indexer = DocumentIndexer(
            opensearch_client=opensearch_client,
            s3_client=s3_client,
        )
        
        # Initialize vector search
        vector_search = VectorSearchService(
            opensearch_client=opensearch_client,
            bedrock_client=bedrock_client,
            index_name=settings.opensearch_index_name,
        )
        
        logger.info("RAG MCP services initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise


@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    await initialize_services()


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("Shutting down RAG MCP server...")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        health_status = {
            "service": "rag-mcp-server",
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
        }
        
        # Check service dependencies if available
        if vector_search:
            search_health = await vector_search.health_check()
            health_status["dependencies"] = {
                "opensearch": search_health.get("opensearch_healthy", False),
                "index_exists": search_health.get("index_exists", False),
            }
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "service": "rag-mcp-server",
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
        )


@app.websocket("/mcp")
async def websocket_endpoint(websocket: WebSocket):
    """Main MCP WebSocket endpoint."""
    await websocket.accept()
    logger.info("RAG MCP WebSocket connection established")
    
    try:
        while True:
            # Receive MCP request
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=settings.rag_timeout_seconds
                )
                
                # Parse MCP request
                try:
                    request_data = json.loads(data)
                    mcp_request = MCPRequest(**request_data)
                except (json.JSONDecodeError, PydanticValidationError) as e:
                    error_response = MCPResponse(
                        id=request_data.get("id", "unknown") if isinstance(request_data, dict) else "unknown",
                        error={
                            "code": "INVALID_REQUEST",
                            "message": f"Invalid MCP request format: {e}",
                        }
                    )
                    await websocket.send_text(error_response.json())
                    continue
                
                # Process MCP request
                response = await process_mcp_request(mcp_request)
                
                # Send response
                await websocket.send_text(response.json())
                
            except asyncio.TimeoutError:
                logger.warning("WebSocket timeout waiting for request")
                error_response = MCPResponse(
                    id="timeout",
                    error={
                        "code": "TIMEOUT",
                        "message": f"Request timeout after {settings.rag_timeout_seconds} seconds",
                    }
                )
                await websocket.send_text(error_response.json())
                break
                
    except WebSocketDisconnect:
        logger.info("RAG MCP WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            error_response = MCPResponse(
                id="error",
                error={
                    "code": "INTERNAL_ERROR",
                    "message": f"WebSocket error: {e}",
                }
            )
            await websocket.send_text(error_response.json())
        except:
            pass  # Connection might be closed


async def process_mcp_request(request: MCPRequest) -> MCPResponse:
    """Process incoming MCP request and return response."""
    
    try:
        logger.info(f"Processing MCP request: {request.method}")
        
        # Route request to appropriate handler
        if request.method == "rag/search":
            return await handle_search_request(request)
        elif request.method == "rag/index":
            return await handle_index_request(request)
        elif request.method == "rag/delete":
            return await handle_delete_request(request)
        elif request.method == "rag/process_document":
            return await handle_process_document_request(request)
        elif request.method == "list_tools":
            return handle_list_tools_request(request)
        else:
            return MCPResponse(
                id=request.id,
                error={
                    "code": "METHOD_NOT_FOUND",
                    "message": f"Unknown method: {request.method}",
                }
            )
            
    except Exception as e:
        logger.error(f"Error processing MCP request {request.id}: {e}")
        return MCPResponse(
            id=request.id,
            error={
                "code": "INTERNAL_ERROR",
                "message": f"Request processing failed: {e}",
            }
        )


async def handle_search_request(request: MCPRequest) -> MCPResponse:
    """Handle document search request."""
    
    if not vector_search:
        return MCPResponse(
            id=request.id,
            error={
                "code": "SERVICE_UNAVAILABLE",
                "message": "Vector search service not available",
            }
        )
    
    try:
        # Parse search request
        search_request = RAGSearchRequest(**request.params)
        
        # Perform search
        search_response = await vector_search.search_documents(search_request)
        
        return MCPResponse(
            id=request.id,
            result=search_response.dict(),
        )
        
    except ValidationError as e:
        return MCPResponse(
            id=request.id,
            error={
                "code": "VALIDATION_ERROR",
                "message": str(e),
            }
        )
    except OpenSearchError as e:
        return MCPResponse(
            id=request.id,
            error={
                "code": "SEARCH_ERROR",
                "message": str(e),
            }
        )


async def handle_index_request(request: MCPRequest) -> MCPResponse:
    """Handle document indexing request."""
    
    if not vector_search:
        return MCPResponse(
            id=request.id,
            error={
                "code": "SERVICE_UNAVAILABLE",
                "message": "Vector search service not available",
            }
        )
    
    try:
        # Parse index request
        index_request = RAGIndexRequest(**request.params)
        
        # Convert to RAG chunks
        chunks = [RAGChunk(**chunk_data) for chunk_data in index_request.chunks]
        
        # Index chunks
        result = await vector_search.index_chunks(chunks)
        
        # Create response
        response = RAGIndexResponse(
            indexed_count=result["indexed_count"],
            failed_count=result["failed_count"],
            total_count=result["total_count"],
        )
        
        return MCPResponse(
            id=request.id,
            result=response.dict(),
        )
        
    except ValidationError as e:
        return MCPResponse(
            id=request.id,
            error={
                "code": "VALIDATION_ERROR",
                "message": str(e),
            }
        )
    except OpenSearchError as e:
        return MCPResponse(
            id=request.id,
            error={
                "code": "INDEX_ERROR",
                "message": str(e),
            }
        )


async def handle_delete_request(request: MCPRequest) -> MCPResponse:
    """Handle document deletion request."""
    
    if not vector_search:
        return MCPResponse(
            id=request.id,
            error={
                "code": "SERVICE_UNAVAILABLE",
                "message": "Vector search service not available",
            }
        )
    
    try:
        # Parse delete request
        delete_request = RAGDeleteRequest(**request.params)
        
        # Delete document chunks
        result = await vector_search.delete_document_chunks(delete_request.document_id)
        
        # Create response
        response = RAGDeleteResponse(
            document_id=delete_request.document_id,
            deleted_count=result["deleted_count"],
        )
        
        return MCPResponse(
            id=request.id,
            result=response.dict(),
        )
        
    except ValidationError as e:
        return MCPResponse(
            id=request.id,
            error={
                "code": "VALIDATION_ERROR",
                "message": str(e),
            }
        )
    except OpenSearchError as e:
        return MCPResponse(
            id=request.id,
            error={
                "code": "DELETE_ERROR",
                "message": str(e),
            }
        )


async def handle_process_document_request(request: MCPRequest) -> MCPResponse:
    """Handle document processing request."""
    
    if not document_processor or not document_indexer:
        return MCPResponse(
            id=request.id,
            error={
                "code": "SERVICE_UNAVAILABLE",
                "message": "Document processing services not available",
            }
        )
    
    try:
        # Extract parameters
        params = request.params
        s3_bucket = params.get("s3_bucket")
        s3_key = params.get("s3_key")
        document_id = params.get("document_id")
        
        if not all([s3_bucket, s3_key, document_id]):
            return MCPResponse(
                id=request.id,
                error={
                    "code": "VALIDATION_ERROR",
                    "message": "Missing required parameters: s3_bucket, s3_key, document_id",
                }
            )
        
        # Process document
        logger.info(f"Processing document: {document_id} from s3://{s3_bucket}/{s3_key}")
        
        # Index document (this will handle processing internally)
        result = await document_indexer.index_document(
            document_id=document_id,
            s3_bucket=s3_bucket,
            s3_key=s3_key,
            metadata=params.get("metadata", {}),
        )
        
        return MCPResponse(
            id=request.id,
            result={
                "document_id": document_id,
                "processed": True,
                "chunk_count": result.get("chunk_count", 0),
                "indexing_result": result,
            },
        )
        
    except ValidationError as e:
        return MCPResponse(
            id=request.id,
            error={
                "code": "VALIDATION_ERROR",
                "message": str(e),
            }
        )
    except DocumentProcessingError as e:
        return MCPResponse(
            id=request.id,
            error={
                "code": "PROCESSING_ERROR",
                "message": str(e),
            }
        )


def handle_list_tools_request(request: MCPRequest) -> MCPResponse:
    """Handle list tools request."""
    
    tools = [
        {
            "name": "rag_search",
            "description": "Search documents using vector similarity and text matching",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query text"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 10
                    },
                    "filters": {
                        "type": "object",
                        "description": "Optional search filters"
                    },
                    "use_vector_search": {
                        "type": "boolean",
                        "description": "Enable vector similarity search",
                        "default": True
                    },
                    "use_text_search": {
                        "type": "boolean", 
                        "description": "Enable text-based search",
                        "default": True
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "rag_index",
            "description": "Index document chunks for search",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "chunks": {
                        "type": "array",
                        "description": "List of document chunks to index",
                        "items": {
                            "type": "object"
                        }
                    }
                },
                "required": ["chunks"]
            }
        },
        {
            "name": "rag_delete",
            "description": "Delete document chunks from index",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "Document ID to delete chunks for"
                    }
                },
                "required": ["document_id"]
            }
        },
        {
            "name": "rag_process_document",
            "description": "Process and index a document from S3",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "s3_bucket": {
                        "type": "string",
                        "description": "S3 bucket containing the document"
                    },
                    "s3_key": {
                        "type": "string",
                        "description": "S3 key (path) to the document"
                    },
                    "document_id": {
                        "type": "string", 
                        "description": "Unique identifier for the document"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Optional document metadata"
                    }
                },
                "required": ["s3_bucket", "s3_key", "document_id"]
            }
        }
    ]
    
    return MCPResponse(
        id=request.id,
        result={"tools": tools},
    )


if __name__ == "__main__":
    import uvicorn
    
    # Run server
    uvicorn.run(
        "rag_server.main:app",
        host="0.0.0.0",
        port=8001,
        log_level="info",
        reload=False,
    )