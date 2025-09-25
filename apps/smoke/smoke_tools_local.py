#!/usr/bin/env python3
"""Smoke test for all MCP tools in local mock mode.
Tests basic connectivity and response structure.
"""

import asyncio
import json
import os
import sys
from typing import Any

import websockets


class MCPClient:
    """Simple MCP JSON-RPC client for testing."""

    def __init__(self, url: str, name: str):
        self.url = url
        self.name = name
        self.request_id = 0

    async def call_tool(self, tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        """Call MCP tool and return response."""
        try:
            async with websockets.connect(self.url) as websocket:
                # Send JSON-RPC request
                self.request_id += 1
                request = {
                    "jsonrpc": "2.0",
                    "id": self.request_id,
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": params
                    }
                }

                await websocket.send(json.dumps(request))
                response_str = await websocket.recv()
                response = json.loads(response_str)

                if "error" in response:
                    raise Exception(f"MCP Error: {response['error']}")

                return response.get("result", {})

        except Exception as e:
            raise Exception(f"Failed to call {tool_name} on {self.name}: {e}")


async def test_rag_service() -> bool:
    """Test RAG service basic functionality."""
    client = MCPClient("ws://localhost:8081", "RAG")

    try:
        result = await client.call_tool("rag.search", {
            "query": "test search query",
            "topK": 3,
            "filters": {}
        })

        # Verify response structure
        if "chunks" not in result:
            return False

        chunks = result["chunks"]
        if not isinstance(chunks, list):
            return False

        return True

    except Exception:
        return False


async def test_parser_service() -> bool:
    """Test Parser service basic functionality."""
    client = MCPClient("ws://localhost:8082", "Parser")

    try:
        result = await client.call_tool("parser.extract", {
            "s3Uri": "s3://test-bucket/test-doc.pdf",
            "dealId": "test-deal-001"
        })

        # Verify response structure
        required_fields = ["tables", "textSections", "confidence"]
        for field in required_fields:
            if field not in result:
                return False

        confidence = result.get("confidence", 0)
        if not isinstance(confidence, int | float) or confidence < 0 or confidence > 1:
            return False

        return True

    except Exception:
        return False


async def test_findb_service() -> bool:
    """Test FinDB service basic functionality."""
    client = MCPClient("ws://localhost:8083", "FinDB")

    try:
        result = await client.call_tool("findb.query", {
            "dealId": "test-deal-001"
        })

        # Verify response structure
        if "metrics" not in result:
            return False

        metrics = result["metrics"]
        if not isinstance(metrics, dict):
            return False

        # Check for some expected metrics
        expected_metrics = ["dscr", "ltv", "ltc", "debtYield"]
        [m for m in expected_metrics if m in metrics]

        return True

    except Exception:
        return False


async def test_web_service() -> bool:
    """Test Web service basic functionality."""
    client = MCPClient("ws://localhost:8084", "Web")

    try:
        result = await client.call_tool("web.search", {
            "queries": ["Austin Texas real estate market"],
            "allowlistGroup": "mavik-ai-web-research"
        })

        # Verify response structure
        if "results" not in result:
            return False

        results = result["results"]
        if not isinstance(results, list):
            return False

        # Check result structure
        if results:
            first_result = results[0]
            required_fields = ["title", "url", "snippet", "source", "credScore"]
            for field in required_fields:
                if field not in first_result:
                    return False

        return True

    except Exception:
        return False


async def test_calc_service() -> bool:
    """Test Calc service basic functionality."""
    client = MCPClient("ws://localhost:8085", "Calc")

    try:
        result = await client.call_tool("calc.compute", {
            "formula": "irr",
            "inputs": {
                "cashFlows": [-1000000, 100000, 120000, 140000, 160000, 1200000],
                "periods": [0, 1, 2, 3, 4, 5]
            }
        })

        # Verify response structure
        required_fields = ["value", "explain"]
        for field in required_fields:
            if field not in result:
                return False

        value = result.get("value")
        if not isinstance(value, int | float):
            return False

        explain = result.get("explain", {})
        if "formula" not in explain or "inputs" not in explain:
            return False

        return True

    except Exception:
        return False


async def main() -> None:
    """Run all MCP tool smoke tests."""
    # Check environment
    if os.getenv("MOCK_AWS") != "true":
        pass

    # Run all tests
    tests = [
        test_rag_service,
        test_parser_service,
        test_findb_service,
        test_web_service,
        test_calc_service,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            success = await test_func()
            if success:
                passed += 1
            else:
                failed += 1
        except Exception:
            failed += 1



    if failed == 0:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
