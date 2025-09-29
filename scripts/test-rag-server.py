#!/usr/bin/env python3
"""
Test script for RAG MCP Server
Tests document processing, vector search, and MCP protocol compliance
"""

import asyncio
import json
import websockets
import aiohttp
from datetime import datetime

async def test_rag_server():
    """Test RAG MCP Server functionality"""
    
    print("🔍 Testing RAG MCP Server...")
    
    base_url = "http://localhost:8001"
    ws_url = "ws://localhost:8001/mcp"
    
    # Test 1: Health check
    print("\n1. Health Check...")
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{base_url}/health") as response:
                health_data = await response.json()
                print(f"   ✅ Health Status: {health_data['status']}")
                print(f"   📊 OpenSearch: {health_data.get('opensearch_connected', 'Unknown')}")
        except Exception as e:
            print(f"   ❌ Health check failed: {e}")
            return False
    
    # Test 2: Capabilities endpoint
    print("\n2. Capabilities Check...")
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{base_url}/capabilities") as response:
                capabilities = await response.json()
                print(f"   ✅ Tools available: {len(capabilities['tools'])}")
                for tool in capabilities['tools']:
                    print(f"      - {tool['name']}: {tool['description'][:50]}...")
        except Exception as e:
            print(f"   ❌ Capabilities check failed: {e}")
            return False
    
    # Test 3: Document upload via HTTP
    print("\n3. Document Upload Test...")
    test_document = {
        "content": "This is a test commercial real estate offering memorandum. The property is located at 123 Main Street and has excellent investment potential with a projected cap rate of 6.5%.",
        "filename": "test_om.txt",
        "document_type": "offering_memorandum"
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                f"{base_url}/api/upload",
                json=test_document
            ) as response:
                upload_result = await response.json()
                print(f"   ✅ Document uploaded: {upload_result.get('document_id', 'Unknown ID')}")
                document_id = upload_result.get("document_id")
        except Exception as e:
            print(f"   ❌ Document upload failed: {e}")
            return False
    
    # Test 4: WebSocket MCP Protocol
    print("\n4. MCP Protocol Test...")
    try:
        async with websockets.connect(ws_url) as websocket:
            # Test search_documents method
            search_request = {
                "jsonrpc": "2.0",
                "id": "test_001",
                "method": "search_documents", 
                "params": {
                    "query": "investment potential cap rate",
                    "limit": 5,
                    "document_types": ["offering_memorandum"]
                }
            }
            
            await websocket.send(json.dumps(search_request))
            response = await websocket.recv()
            result = json.loads(response)
            
            if result.get("result", {}).get("success"):
                documents = result["result"]["data"]["documents"]
                print(f"   ✅ Search returned {len(documents)} documents")
                if documents:
                    print(f"      Top result score: {documents[0].get('score', 'N/A')}")
            else:
                print(f"   ⚠️ Search returned no results: {result.get('error', 'Unknown error')}")
                
    except Exception as e:
        print(f"   ❌ WebSocket MCP test failed: {e}")
        return False
    
    # Test 5: Document processing with chunks
    print("\n5. Document Processing Test...")
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                f"{base_url}/api/process",
                json={
                    "document_id": document_id if 'document_id' in locals() else "test_doc",
                    "chunk_size": 500,
                    "overlap_size": 100
                }
            ) as response:
                process_result = await response.json()
                print(f"   ✅ Document processed into {process_result.get('chunks_created', 0)} chunks")
        except Exception as e:
            print(f"   ❌ Document processing failed: {e}")
            return False
    
    print("\n🎉 RAG MCP Server tests completed successfully!")
    return True

if __name__ == "__main__":
    asyncio.run(test_rag_server())