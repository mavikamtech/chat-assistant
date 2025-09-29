"""
FastAPI server for FinDB MCP service.

Provides WebSocket-based MCP protocol endpoints and HTTP REST API
for financial database operations including comparable property analysis,
market data queries, cap rate analysis, and property valuation.
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog
from pydantic import BaseModel, ValidationError as PydanticValidationError

# Import models and service
from mavik_common.models import (
    FinDBQuery, FinDBResponse, MCPRequest, MCPResponse, MCPErrorResponse,
    FinDBQueryType, PropertyData, CompsRequest, MarketDataRequest
)
from mavik_common.errors import FinDBError, ValidationError, MCPError
from mavik_config.settings import get_settings
from .financial_database import FinDBService

# Configure structured logging
logging.basicConfig(level=logging.INFO)
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="FinDB MCP Server",
    description="Financial Database MCP Server for real estate market data and analysis",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global service instance
findb_service: Optional[FinDBService] = None

# Request models for HTTP endpoints
class CompsAnalysisRequest(BaseModel):
    """HTTP request model for comparable analysis."""
    property_id: str
    radius_miles: Optional[float] = 5.0
    max_results: Optional[int] = 10
    property_type: Optional[str] = None
    min_size: Optional[int] = None
    max_size: Optional[int] = None

class MarketDataHTTPRequest(BaseModel):
    """HTTP request model for market data."""
    property_type: str
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    start_date: datetime
    end_date: datetime

class PropertyValuationHTTPRequest(BaseModel):
    """HTTP request model for property valuation."""
    property_id: str
    market_cap_rate: Optional[float] = None
    valuation_date: Optional[datetime] = None

# Connection manager for WebSocket connections
class ConnectionManager:
    """Manages WebSocket connections for MCP protocol."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_ids: Dict[WebSocket, str] = {}
        self.logger = logger.bind(component="connection_manager")
    
    async def connect(self, websocket: WebSocket) -> str:
        """Accept and track new WebSocket connection."""
        await websocket.accept()
        connection_id = str(uuid.uuid4())
        self.active_connections.append(websocket)
        self.connection_ids[websocket] = connection_id
        
        self.logger.info("WebSocket connected", connection_id=connection_id)
        return connection_id
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection."""
        connection_id = self.connection_ids.get(websocket, "unknown")
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.connection_ids:
            del self.connection_ids[websocket]
        
        self.logger.info("WebSocket disconnected", connection_id=connection_id)
    
    async def send_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send message to specific WebSocket."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            connection_id = self.connection_ids.get(websocket, "unknown")
            self.logger.error("Failed to send message", 
                            connection_id=connection_id, error=str(e))

manager = ConnectionManager()

@app.on_event("startup")
async def startup_event():
    """Initialize the FinDB service on startup."""
    global findb_service
    
    try:
        settings = get_settings()
        findb_service = FinDBService(settings)
        logger.info("FinDB MCP Server started successfully")
    except Exception as e:
        logger.error("Failed to start FinDB service", error=str(e))
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global findb_service
    
    if findb_service:
        await findb_service.cleanup()
        logger.info("FinDB MCP Server shutdown complete")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    if not findb_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        health_status = await findb_service.health_check()
        
        if health_status["status"] == "healthy":
            return JSONResponse(content=health_status)
        else:
            raise HTTPException(status_code=503, detail=health_status)
    
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=503, detail=f"Health check failed: {e}")

@app.get("/capabilities")
async def get_capabilities():
    """Get MCP server capabilities."""
    return {
        "tools": [
            {
                "name": "find_comparable_properties",
                "description": "Find comparable properties based on criteria",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "property_id": {"type": "string"},
                        "radius_miles": {"type": "number", "default": 5.0},
                        "max_results": {"type": "integer", "default": 10},
                        "property_filter": {"type": "object"}
                    },
                    "required": ["property_id"]
                }
            },
            {
                "name": "get_market_data",
                "description": "Get market data and statistics for a geographic area",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "property_type": {"type": "string"},
                        "city": {"type": "string"},
                        "state": {"type": "string"},
                        "start_date": {"type": "string", "format": "date"},
                        "end_date": {"type": "string", "format": "date"}
                    },
                    "required": ["property_type", "start_date", "end_date"]
                }
            },
            {
                "name": "analyze_property_value",
                "description": "Perform comprehensive property valuation analysis",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "property_id": {"type": "string"},
                        "market_cap_rate": {"type": "number"}
                    },
                    "required": ["property_id"]
                }
            },
            {
                "name": "analyze_cap_rates",
                "description": "Analyze cap rates for a specific market area",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "property_type": {"type": "string"},
                        "city": {"type": "string"},
                        "state": {"type": "string"}
                    },
                    "required": ["property_type", "city", "state"]
                }
            },
            {
                "name": "analyze_market_trends",
                "description": "Perform market trend analysis over time periods",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "property_type": {"type": "string"},
                        "city": {"type": "string"},
                        "state": {"type": "string"},
                        "start_date": {"type": "string", "format": "date"},
                        "end_date": {"type": "string", "format": "date"}
                    },
                    "required": ["property_type", "start_date", "end_date"]
                }
            }
        ],
        "server_info": {
            "name": "findb-mcp-server",
            "version": "0.1.0",
            "description": "Financial Database MCP Server"
        }
    }

# WebSocket MCP Protocol Handler
@app.websocket("/mcp")
async def websocket_mcp_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for MCP protocol communication."""
    connection_id = await manager.connect(websocket)
    
    try:
        while True:
            # Receive MCP message
            data = await websocket.receive_text()
            
            try:
                # Parse MCP request
                mcp_request = MCPRequest.model_validate(json.loads(data))
                
                # Process the request
                response = await process_mcp_request(mcp_request, connection_id)
                
                # Send response
                await manager.send_message(websocket, response.model_dump())
                
            except PydanticValidationError as e:
                # Invalid MCP request format
                error_response = MCPErrorResponse(
                    id=None,
                    error={
                        "code": -32600,
                        "message": "Invalid Request",
                        "data": str(e)
                    }
                )
                await manager.send_message(websocket, error_response.model_dump())
                
            except Exception as e:
                logger.error("Error processing MCP request", 
                           connection_id=connection_id, error=str(e))
                
                error_response = MCPErrorResponse(
                    id=getattr(mcp_request, 'id', None) if 'mcp_request' in locals() else None,
                    error={
                        "code": -32603,
                        "message": "Internal Error",
                        "data": str(e)
                    }
                )
                await manager.send_message(websocket, error_response.model_dump())
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error("WebSocket connection error", 
                    connection_id=connection_id, error=str(e))
        manager.disconnect(websocket)

async def process_mcp_request(request: MCPRequest, connection_id: str) -> MCPResponse:
    """Process an MCP request and return appropriate response."""
    if not findb_service:
        raise MCPError("FinDB service not initialized")
    
    method = request.method
    params = request.params or {}
    
    logger.info("Processing MCP request", 
               connection_id=connection_id, 
               method=method)
    
    try:
        if method == "find_comparable_properties":
            # Create FinDBQuery for comps analysis
            query = FinDBQuery(
                query_id=str(uuid.uuid4()),
                query_type=FinDBQueryType.COMPS,
                target_property=PropertyData(
                    property_id=params["property_id"],
                    # Other fields would be fetched from database
                ),
                radius_miles=params.get("radius_miles", 5.0),
                max_results=params.get("max_results", 10),
                property_filter=params.get("property_filter")
            )
            
            result = await findb_service.process_query(query)
            
            return MCPResponse(
                id=request.id,
                result={
                    "success": result.success,
                    "data": result.result.model_dump() if result.result else None,
                    "error": result.error_message
                }
            )
        
        elif method == "get_market_data":
            # Create market data query
            market_request = MarketDataRequest(**params)
            
            query = FinDBQuery(
                query_id=str(uuid.uuid4()),
                query_type=FinDBQueryType.MARKET_DATA,
                market_request=market_request
            )
            
            result = await findb_service.process_query(query)
            
            return MCPResponse(
                id=request.id,
                result={
                    "success": result.success,
                    "data": result.result.model_dump() if result.result else None,
                    "error": result.error_message
                }
            )
        
        elif method == "analyze_property_value":
            # Property valuation query
            from packages.common.models import PropertyValuationRequest
            
            valuation_request = PropertyValuationRequest(
                property_id=params["property_id"],
                market_cap_rate=params.get("market_cap_rate"),
                valuation_date=datetime.now()
            )
            
            query = FinDBQuery(
                query_id=str(uuid.uuid4()),
                query_type=FinDBQueryType.VALUATION,
                valuation_request=valuation_request
            )
            
            result = await findb_service.process_query(query)
            
            return MCPResponse(
                id=request.id,
                result={
                    "success": result.success,
                    "data": result.result.model_dump() if result.result else None,
                    "error": result.error_message
                }
            )
        
        elif method == "analyze_cap_rates":
            # Cap rate analysis query
            from packages.common.models import CapRateAnalysisRequest
            
            cap_rate_request = CapRateAnalysisRequest(
                property_type=params["property_type"],
                city=params["city"],
                state=params["state"]
            )
            
            query = FinDBQuery(
                query_id=str(uuid.uuid4()),
                query_type=FinDBQueryType.CAP_RATE_ANALYSIS,
                cap_rate_request=cap_rate_request
            )
            
            result = await findb_service.process_query(query)
            
            return MCPResponse(
                id=request.id,
                result={
                    "success": result.success,
                    "data": result.result.model_dump() if result.result else None,
                    "error": result.error_message
                }
            )
        
        elif method == "analyze_market_trends":
            # Market trend analysis query
            from packages.common.models import TrendAnalysisRequest
            
            trend_request = TrendAnalysisRequest(
                property_type=params["property_type"],
                city=params.get("city"),
                state=params.get("state"),
                start_date=datetime.fromisoformat(params["start_date"]),
                end_date=datetime.fromisoformat(params["end_date"])
            )
            
            query = FinDBQuery(
                query_id=str(uuid.uuid4()),
                query_type=FinDBQueryType.TREND_ANALYSIS,
                trend_request=trend_request
            )
            
            result = await findb_service.process_query(query)
            
            return MCPResponse(
                id=request.id,
                result={
                    "success": result.success,
                    "data": result.result.model_dump() if result.result else None,
                    "error": result.error_message
                }
            )
        
        else:
            return MCPResponse(
                id=request.id,
                error={
                    "code": -32601,
                    "message": f"Method not found: {method}",
                    "data": None
                }
            )
    
    except Exception as e:
        logger.error("Error processing MCP method", 
                    method=method, error=str(e))
        
        return MCPResponse(
            id=request.id,
            error={
                "code": -32603,
                "message": "Internal Error",
                "data": str(e)
            }
        )

# HTTP REST API Endpoints
@app.post("/api/comparable-analysis")
async def comparable_analysis_endpoint(request: CompsAnalysisRequest):
    """HTTP endpoint for comparable property analysis."""
    if not findb_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        # Create FinDB query
        query = FinDBQuery(
            query_id=str(uuid.uuid4()),
            query_type=FinDBQueryType.COMPS,
            target_property=PropertyData(property_id=request.property_id),
            radius_miles=request.radius_miles,
            max_results=request.max_results
        )
        
        result = await findb_service.process_query(query)
        
        if result.success:
            return result.result.model_dump()
        else:
            raise HTTPException(status_code=400, detail=result.error_message)
    
    except Exception as e:
        logger.error("Error in comparable analysis endpoint", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/market-data")
async def market_data_endpoint(request: MarketDataHTTPRequest):
    """HTTP endpoint for market data analysis."""
    if not findb_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        # Create market data request
        market_request = MarketDataRequest(
            property_type=request.property_type,
            city=request.city,
            state=request.state,
            zip_code=request.zip_code,
            start_date=request.start_date,
            end_date=request.end_date
        )
        
        query = FinDBQuery(
            query_id=str(uuid.uuid4()),
            query_type=FinDBQueryType.MARKET_DATA,
            market_request=market_request
        )
        
        result = await findb_service.process_query(query)
        
        if result.success:
            return result.result.model_dump()
        else:
            raise HTTPException(status_code=400, detail=result.error_message)
    
    except Exception as e:
        logger.error("Error in market data endpoint", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/property-valuation")
async def property_valuation_endpoint(request: PropertyValuationHTTPRequest):
    """HTTP endpoint for property valuation."""
    if not findb_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        from packages.common.models import PropertyValuationRequest
        
        valuation_request = PropertyValuationRequest(
            property_id=request.property_id,
            market_cap_rate=request.market_cap_rate,
            valuation_date=request.valuation_date or datetime.now()
        )
        
        query = FinDBQuery(
            query_id=str(uuid.uuid4()),
            query_type=FinDBQueryType.VALUATION,
            valuation_request=valuation_request
        )
        
        result = await findb_service.process_query(query)
        
        if result.success:
            return result.result.model_dump()
        else:
            raise HTTPException(status_code=400, detail=result.error_message)
    
    except Exception as e:
        logger.error("Error in property valuation endpoint", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    
    # Run the server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8003,
        reload=True,
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "level": "INFO",
                "handlers": ["default"],
            },
        }
    )