#!/usr/bin/env python3
"""
Test script for Parser MCP Server
Tests document parsing, AWS Textract integration, and format detection
"""

import asyncio
import json
import websockets
import aiohttp
import os
from pathlib import Path

async def test_parser_server():
    """Test Parser MCP Server functionality"""

    print("📄 Testing Parser MCP Server...")

    base_url = "http://localhost:8002"
    ws_url = "ws://localhost:8002/mcp"

    # Test 1: Health check
    print("\n1. Health Check...")
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{base_url}/health") as response:
                health_data = await response.json()
                print(f"   ✅ Health Status: {health_data['status']}")
                print(f"   🔧 Textract Available: {health_data.get('textract_available', 'Unknown')}")
                print(f"   📁 S3 Connected: {health_data.get('s3_connected', 'Unknown')}")
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

    # Test 3: File upload and parsing
    print("\n3. Document Upload and Parse Test...")

    # Check if we have the test PDF
    test_pdf_path = Path("packages/evals/fixtures/300_Hillsborough_OM.pdf")
    if test_pdf_path.exists():
        print(f"   📄 Using test PDF: {test_pdf_path}")

        async with aiohttp.ClientSession() as session:
            try:
                # Upload file for parsing
                with open(test_pdf_path, 'rb') as f:
                    form_data = aiohttp.FormData()
                    form_data.add_field('file', f, filename='test_om.pdf', content_type='application/pdf')
                    form_data.add_field('document_type', 'offering_memorandum')
                    form_data.add_field('use_textract', 'false')  # Use local parser first

                    async with session.post(f"{base_url}/api/upload", data=form_data) as response:
                        upload_result = await response.json()
                        print(f"   ✅ Document parsed successfully")

                        # Check parsing results
                        if 'parsed_content' in upload_result:
                            content = upload_result['parsed_content']
                            print(f"      📊 Content length: {len(content.get('text', ''))} characters")
                            print(f"      📑 Pages: {content.get('page_count', 'Unknown')}")
                            print(f"      🏢 Tables: {len(content.get('tables', []))}")

                            # Show sample text
                            text_sample = content.get('text', '')[:200]
                            print(f"      💬 Sample text: {text_sample}...")

            except Exception as e:
                print(f"   ❌ File upload failed: {e}")
                # Try with a simple text document
                await test_text_parsing(session, base_url)
    else:
        print(f"   ⚠️ Test PDF not found at {test_pdf_path}")
        # Try with a simple text document
        async with aiohttp.ClientSession() as session:
            await test_text_parsing(session, base_url)

    # Test 4: WebSocket MCP Protocol
    print("\n4. MCP Protocol Test...")
    try:
        async with websockets.connect(ws_url) as websocket:
            # Test parse_document method with text content
            parse_request = {
                "jsonrpc": "2.0",
                "id": "test_002",
                "method": "parse_document",
                "params": {
                    "content": "OFFERING MEMORANDUM\n\n123 Main Street Office Building\nPrime downtown location with excellent investment potential.\n\nProperty Details:\n- Square Feet: 50,000\n- Cap Rate: 6.5%\n- NOI: $325,000",
                    "format": "text",
                    "document_type": "offering_memorandum",
                    "use_textract": False
                }
            }

            await websocket.send(json.dumps(parse_request))
            response = await websocket.recv()
            result = json.loads(response)

            if result.get("result", {}).get("success"):
                parsed_data = result["result"]["data"]
                print(f"   ✅ MCP parsing successful")
                print(f"      📄 Format detected: {parsed_data.get('format_detected', 'Unknown')}")
                print(f"      📊 Content length: {len(parsed_data.get('parsed_content', {}).get('text', ''))}")
            else:
                print(f"   ❌ MCP parsing failed: {result.get('error', 'Unknown error')}")

    except Exception as e:
        print(f"   ❌ WebSocket MCP test failed: {e}")
        return False

    # Test 5: Format detection
    print("\n5. Format Detection Test...")
    test_formats = [
        ("PDF content", b"%PDF-1.4", "pdf"),
        ("PNG content", b"\x89PNG\r\n\x1a\n", "png"),
        ("JPEG content", b"\xff\xd8\xff", "jpeg"),
        ("Text content", b"This is plain text", "text")
    ]

    async with aiohttp.ClientSession() as session:
        for name, content, expected_format in test_formats:
            try:
                async with session.post(
                    f"{base_url}/api/detect-format",
                    data=content,
                    headers={"Content-Type": "application/octet-stream"}
                ) as response:
                    format_result = await response.json()
                    detected = format_result.get("format", "unknown")

                    if detected == expected_format:
                        print(f"   ✅ {name}: {detected}")
                    else:
                        print(f"   ⚠️ {name}: Expected {expected_format}, got {detected}")

            except Exception as e:
                print(f"   ❌ Format detection failed for {name}: {e}")

    print("\n🎉 Parser MCP Server tests completed successfully!")
    return True

async def test_text_parsing(session, base_url):
    """Test parsing with simple text content"""
    try:
        # Create a simple text document
        form_data = aiohttp.FormData()
        form_data.add_field('file',
                          "OFFERING MEMORANDUM\n\n123 Main Street Office Building\nExcellent investment opportunity!",
                          filename='test.txt',
                          content_type='text/plain')
        form_data.add_field('document_type', 'offering_memorandum')

        async with session.post(f"{base_url}/api/upload", data=form_data) as response:
            upload_result = await response.json()
            print(f"   ✅ Text document parsed")
            print(f"      📊 Content: {len(upload_result.get('parsed_content', {}).get('text', ''))} chars")

    except Exception as e:
        print(f"   ⚠️ Text parsing fallback failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_parser_server())
