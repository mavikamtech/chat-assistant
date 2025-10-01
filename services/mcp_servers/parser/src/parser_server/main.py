"""FastAPI server for Parser MCP service with WebSocket support."""

import logging
import asyncio
from datetime import datetime
from typing import Any, Dict, Optional
import json
import tempfile
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from mavik_common.models import (
    ParserRequest, ParserResponse, ParserUploadRequest, ParserUploadResponse,
    MCPRequest, MCPResponse, ParsedDocument
)
from mavik_common.errors import ValidationError, DocumentProcessingError, format_error_response
from mavik_config.settings import get_settings
from mavik_aws_clients import TextractClient, S3Client

from .document_parser import DocumentParser, DocumentFormatDetector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global variables for dependency injection
settings = get_settings()
app = FastAPI(
    title="Mavik Parser MCP Server",
    description="Document parsing service using AWS Textract and local parsers",
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
textract_client: Optional[TextractClient] = None
s3_client: Optional[S3Client] = None
document_parser: Optional[DocumentParser] = None


async def initialize_services():
    """Initialize AWS clients and document parser."""
    global textract_client, s3_client, document_parser

    try:
        logger.info("Initializing Parser MCP services...")

        # Initialize AWS clients
        textract_client = TextractClient()
        s3_client = S3Client()

        # Initialize document parser
        document_parser = DocumentParser(
            textract_client=textract_client,
            s3_client=s3_client,
            use_local_fallback=True,
        )

        logger.info("Parser MCP services initialized successfully")

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
    logger.info("Shutting down Parser MCP server...")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        health_status = {
            "service": "parser-mcp-server",
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
        }

        # Check service capabilities if available
        if document_parser:
            parser_health = await document_parser.health_check()
            health_status["capabilities"] = parser_health

        return health_status

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "service": "parser-mcp-server",
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
        )


@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    document_id: Optional[str] = None,
    extract_tables: bool = True,
    extract_forms: bool = True,
    extract_signatures: bool = False,
    s3_upload: bool = False,
    s3_bucket: Optional[str] = None,
    s3_prefix: str = "uploads/",
):
    """Upload and parse document via HTTP."""

    if not document_parser:
        raise HTTPException(status_code=503, detail="Parser service not available")

    # Generate document ID if not provided
    if not document_id:
        document_id = f"upload_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{file.filename}"

    # Validate file format
    if not DocumentFormatDetector.is_supported(file.filename):
        raise HTTPException(status_code=400, detail=f"Unsupported file format: {file.filename}")

    # Save uploaded file temporarily
    temp_file = None
    try:
        # Create temporary file with original extension
        file_suffix = Path(file.filename).suffix
        with tempfile.NamedTemporaryFile(suffix=file_suffix, delete=False) as temp:
            temp_file = temp.name

            # Copy uploaded content
            content = await file.read()
            temp.write(content)

        # Parse document
        parsed_doc = await document_parser.parse_document(
            document_source=temp_file,
            document_id=document_id,
            parser_options={
                "extract_tables": extract_tables,
                "extract_forms": extract_forms,
                "extract_signatures": extract_signatures,
            }
        )

        # Optionally upload to S3 and include location
        uploaded_s3_uri: Optional[str] = None
        if s3_upload:
            if not s3_client:
                raise HTTPException(status_code=503, detail="S3 client not available for upload")
            try:
                bucket = s3_bucket or settings.s3_bucket_documents
                ext = Path(file.filename).suffix
                # ensure prefix formatting
                prefix = s3_prefix.strip("/")
                key = f"{prefix}/{document_id}{ext}" if prefix else f"{document_id}{ext}"
                logger.info(f"Uploading parsed upload to s3://{bucket}/{key}")
                await s3_client.upload_file(
                    file_path=temp_file,
                    bucket_name=bucket,
                    s3_key=key,
                    metadata={"ContentType": file.content_type or "application/octet-stream"}
                )
                uploaded_s3_uri = f"s3://{bucket}/{key}"
            except Exception as e:
                logger.error(f"S3 upload failed for {document_id}: {e}")
                err_payload = format_error_response(e)
                return JSONResponse(status_code=502, content=err_payload)

        return {
            "document_id": document_id,
            "filename": file.filename,
            "parsed_document": parsed_doc.dict(),
            "processing_time": datetime.utcnow().isoformat(),
            "success": True,
            "s3_uri": uploaded_s3_uri,
        }

    except Exception as e:
        logger.error(f"Document upload parsing failed: {type(e).__name__}: {e}")
        if isinstance(e, (ValidationError, DocumentProcessingError)):
            # Return structured error
            err_payload = format_error_response(e)
            return JSONResponse(status_code=400, content=err_payload)
        # Unknown error
        err_payload = format_error_response(e)
        return JSONResponse(status_code=500, content=err_payload)

    finally:
        # Clean up temporary file
        if temp_file:
            try:
                Path(temp_file).unlink()
            except:
                pass


@app.websocket("/mcp")
async def websocket_endpoint(websocket: WebSocket):
    """Main MCP WebSocket endpoint."""
    await websocket.accept()
    logger.info("Parser MCP WebSocket connection established")

    try:
        while True:
            # Receive MCP request
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=settings.parser_timeout_seconds
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
                        "message": f"Request timeout after {settings.parser_timeout_seconds} seconds",
                    }
                )
                await websocket.send_text(error_response.json())
                break

    except WebSocketDisconnect:
        logger.info("Parser MCP WebSocket disconnected")
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
        if request.method == "parser/parse_document":
            return await handle_parse_request(request)
        elif request.method == "parser/upload_document":
            return await handle_upload_request(request)
        elif request.method == "parser/get_capabilities":
            return await handle_capabilities_request(request)
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


async def handle_parse_request(request: MCPRequest) -> MCPResponse:
    """Handle document parsing request."""

    if not document_parser:
        return MCPResponse(
            id=request.id,
            error={
                "code": "SERVICE_UNAVAILABLE",
                "message": "Document parser service not available",
            }
        )

    try:
        # Parse request
        parse_request = ParserRequest(**request.params)

        # Parse document
        parsed_doc = await document_parser.parse_document(
            document_source=parse_request.document_source,
            document_id=parse_request.document_id,
            parser_options=parse_request.options,
        )

        # Create response
        response = ParserResponse(
            document_id=parse_request.document_id,
            parsed_document=parsed_doc,
            processing_timestamp=datetime.utcnow(),
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
    except DocumentProcessingError as e:
        return MCPResponse(
            id=request.id,
            error={
                "code": "PROCESSING_ERROR",
                "message": str(e),
            }
        )


async def handle_upload_request(request: MCPRequest) -> MCPResponse:
    """Handle document upload and parsing request."""

    if not document_parser or not s3_client:
        return MCPResponse(
            id=request.id,
            error={
                "code": "SERVICE_UNAVAILABLE",
                "message": "Document parser or S3 service not available",
            }
        )

    try:
        # Parse upload request
        upload_request = ParserUploadRequest(**request.params)

        # Download file from S3 to temporary location
        with tempfile.NamedTemporaryFile(
            suffix=Path(upload_request.filename).suffix,
            delete=False
        ) as temp_file:
            temp_path = temp_file.name

        try:
            # Download from S3
            await s3_client.download_file(
                bucket=upload_request.s3_bucket,
                key=upload_request.s3_key,
                filename=temp_path,
            )

            # Parse document
            parsed_doc = await document_parser.parse_document(
                document_source=temp_path,
                document_id=upload_request.document_id,
                parser_options=upload_request.options,
            )

            # Create response
            response = ParserUploadResponse(
                document_id=upload_request.document_id,
                filename=upload_request.filename,
                parsed_document=parsed_doc,
                s3_location=f"s3://{upload_request.s3_bucket}/{upload_request.s3_key}",
                processing_timestamp=datetime.utcnow(),
            )

            return MCPResponse(
                id=request.id,
                result=response.dict(),
            )

        finally:
            # Clean up temporary file
            try:
                Path(temp_path).unlink()
            except:
                pass

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


async def handle_capabilities_request(request: MCPRequest) -> MCPResponse:
    """Handle capabilities inquiry request."""

    if not document_parser:
        return MCPResponse(
            id=request.id,
            error={
                "code": "SERVICE_UNAVAILABLE",
                "message": "Document parser service not available",
            }
        )

    try:
        capabilities = await document_parser.health_check()

        return MCPResponse(
            id=request.id,
            result={
                "capabilities": capabilities,
                "server_info": {
                    "version": "1.0.0",
                    "service": "parser-mcp-server",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            },
        )

    except Exception as e:
        return MCPResponse(
            id=request.id,
            error={
                "code": "INTERNAL_ERROR",
                "message": f"Failed to get capabilities: {e}",
            }
        )


def handle_list_tools_request(request: MCPRequest) -> MCPResponse:
    """Handle list tools request."""

    tools = [
        {
            "name": "parser_parse_document",
            "description": "Parse document from file path or S3 location using Textract or local parsers",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "document_source": {
                        "type": "string",
                        "description": "Document source (file path or s3://bucket/key)"
                    },
                    "document_id": {
                        "type": "string",
                        "description": "Unique document identifier"
                    },
                    "options": {
                        "type": "object",
                        "description": "Parser options",
                        "properties": {
                            "extract_tables": {
                                "type": "boolean",
                                "description": "Extract table data",
                                "default": True
                            },
                            "extract_forms": {
                                "type": "boolean",
                                "description": "Extract form key-value pairs",
                                "default": True
                            },
                            "extract_signatures": {
                                "type": "boolean",
                                "description": "Detect signatures",
                                "default": False
                            }
                        }
                    }
                },
                "required": ["document_source", "document_id"]
            }
        },
        {
            "name": "parser_upload_document",
            "description": "Parse document uploaded to S3",
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
                        "description": "Unique document identifier"
                    },
                    "filename": {
                        "type": "string",
                        "description": "Original filename"
                    },
                    "options": {
                        "type": "object",
                        "description": "Parser options"
                    }
                },
                "required": ["s3_bucket", "s3_key", "document_id", "filename"]
            }
        },
        {
            "name": "parser_get_capabilities",
            "description": "Get parser capabilities and supported formats",
            "inputSchema": {
                "type": "object",
                "properties": {}
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
        "parser_server.main:app",
        host="0.0.0.0",
        port=8002,
        log_level="info",
        reload=False,
    )
