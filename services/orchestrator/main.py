#!/usr/bin/env python3
"""Main orchestrator service for Mavik AI.
Handles incoming requests and orchestrates MCP tools.
"""

import json
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import uvicorn
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.responses import JSONResponse
except ImportError:
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Mavik AI Orchestrator",
    description="AI Underwriting & Strategy System Orchestrator",
    version="0.1.0"
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return JSONResponse({
        "service": "mavik-ai-orchestrator",
        "status": "healthy",
        "version": "0.1.0"
    })


@app.get("/health")
async def health():
    """Detailed health check."""
    return JSONResponse({
        "service": "mavik-ai-orchestrator",
        "status": "healthy",
        "version": "0.1.0",
        "timestamp": "2024-01-01T00:00:00Z"
    })


@app.websocket("/ws/orchestrator")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for orchestrator communication."""
    await websocket.accept()
    logger.info("WebSocket connection established")

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            logger.info(f"Received message: {data}")

            try:
                message = json.loads(data)

                # Handle different message types
                if message.get("type") == "health_check":
                    response = {
                        "type": "health_check_response",
                        "status": "healthy",
                        "timestamp": "2024-01-01T00:00:00Z",
                        "orchestrator": "ready"
                    }
                    await websocket.send_text(json.dumps(response))
                    logger.info("Sent health check response")

                else:
                    # Default response for unknown message types
                    response = {
                        "type": "response",
                        "status": "received",
                        "original_message": message,
                        "note": "Message received but not yet processed (system in development)"
                    }
                    await websocket.send_text(json.dumps(response))
                    logger.info(f"Sent default response for message type: {message.get('type')}")

            except json.JSONDecodeError:
                error_response = {
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": "2024-01-01T00:00:00Z"
                }
                await websocket.send_text(json.dumps(error_response))
                logger.warning("Received invalid JSON")

    except WebSocketDisconnect:
        logger.info("WebSocket connection closed")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            error_response = {
                "type": "error",
                "message": str(e),
                "timestamp": "2024-01-01T00:00:00Z"
            }
            await websocket.send_text(json.dumps(error_response))
        except Exception as send_error:
            logger.error(f"Failed to send error response: {send_error}")
            # Connection might be closed, nothing more we can do


def main():
    """Run the orchestrator service."""
    logger.info("Starting Mavik AI Orchestrator...")

    # Configuration
    host = "127.0.0.1"
    port = 8000

    logger.info(f"Server will start at http://{host}:{port}")
    logger.info(f"WebSocket endpoint: ws://{host}:{port}/ws/orchestrator")
    logger.info("Health check: http://{host}:{port}/health")

    # Start the server
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )


if __name__ == "__main__":
    main()
