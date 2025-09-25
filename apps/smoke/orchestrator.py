#!/usr/bin/env python3
"""Orchestrator smoke test - Verifies that the system can start and respond to basic requests."""

import asyncio
import json
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import websockets
except ImportError:
    sys.exit(1)


async def test_orchestrator_connection():
    """Test basic connection to orchestrator service."""
    try:

        # Try to connect to the orchestrator WebSocket
        uri = "ws://localhost:8000/ws/orchestrator"

        try:
            async with websockets.connect(uri, timeout=5) as websocket:

                # Send a simple test message
                test_message = {
                    "type": "health_check",
                    "timestamp": "2024-01-01T00:00:00Z"
                }

                await websocket.send(json.dumps(test_message))

                # Wait for response (with timeout)
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    json.loads(response)
                    return True

                except asyncio.TimeoutError:
                    return False

        except ConnectionRefusedError:
            return False

        except Exception:
            return False

    except Exception:
        return False


async def main():
    """Run the orchestrator smoke test."""
    success = await test_orchestrator_connection()

    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
