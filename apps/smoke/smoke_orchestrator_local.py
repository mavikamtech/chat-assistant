#!/usr/bin/env python3
"""Smoke test for orchestrator in local mock mode.
Tests WebSocket streaming with tool invocation flow.
"""

import asyncio
import json
import os
import sys
import time

import websockets
from websockets.exceptions import ConnectionClosed


async def smoke_test_orchestrator() -> bool:
    """Test orchestrator WebSocket streaming with tool events."""
    orchestrator_url = "ws://localhost:8080/v1/chat/stream"


    try:
        # Connect to orchestrator WebSocket
        async with websockets.connect(orchestrator_url) as websocket:

            # Send initial chat message with fixture data
            test_message = {
                "type": "start_chat",
                "data": {
                    "dealId": "test-deal-001",
                    "persona": "originations",
                    "message": "Please analyze this offering memorandum for pre-screening.",
                    "attachments": [{
                        "type": "text",
                        "content": "Sample OM: 123 Main Street Apartment Complex\nGross Rental Income: $1,200,000\nOperating Expenses: $400,000\nNOI: $800,000\nAsking Price: $12,000,000\nProperty Type: Multifamily\nUnits: 48\nMarket: Austin, TX"
                    }]
                }
            }

            await websocket.send(json.dumps(test_message))

            # Collect events and verify expected flow
            events_received = []
            expected_events = ["tool_invoked", "tool_result", "token", "done"]
            timeout = 30  # 30 second timeout
            start_time = time.time()

            while time.time() - start_time < timeout:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    event = json.loads(message)
                    events_received.append(event)


                    # Check for completion
                    if event.get("type") == "done":
                        break

                    # Validate tool events
                    if event.get("type") == "tool_invoked":
                        event.get("data", {}).get("tool")

                    elif event.get("type") == "tool_result":
                        event.get("data", {}).get("success", False)

                    elif event.get("type") == "token":
                        event.get("data", {})

                except asyncio.TimeoutError:
                    break
                except ConnectionClosed:
                    return False

            # Verify we got expected event types
            received_types = {event.get("type") for event in events_received}
            missing_events = set(expected_events) - received_types

            if missing_events:
                return False


            # Verify tool invocation
            tool_events = [e for e in events_received if e.get("type") == "tool_invoked"]
            if not tool_events:
                return False


            # Verify streaming tokens
            token_events = [e for e in events_received if e.get("type") == "token"]
            if len(token_events) < 5:  # Expect reasonable token stream
                return False


            return True

    except Exception:
        return False


async def main() -> None:
    """Run smoke test."""
    # Check environment
    if os.getenv("MOCK_AWS") != "true":
        pass

    success = await smoke_test_orchestrator()

    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
