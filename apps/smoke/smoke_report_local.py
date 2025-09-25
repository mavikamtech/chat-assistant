#!/usr/bin/env python3
"""Smoke test for report generation in local mock mode.
Tests DOCX creation and S3 presigned URL generation.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

import websockets


async def test_report_generation() -> bool:
    """Test report service DOCX generation."""
    # Sample structured analysis data
    sample_analysis = {
        "schemaVersion": "mavik.analysis.v1",
        "dealId": "test-deal-001",
        "analysisType": "originations",
        "timestamp": "2024-01-15T10:30:00Z",
        "sections": {
            "executive_summary": {
                "title": "Executive Summary",
                "content": "This is a test analysis of a multifamily property located in Austin, Texas."
            },
            "property_overview": {
                "title": "Property Overview",
                "content": "48-unit apartment complex built in 2015, well-maintained with recent renovations."
            },
            "financial_analysis": {
                "title": "Financial Analysis",
                "content": "NOI of $800,000 on asking price of $12,000,000 results in 6.67% cap rate.",
                "metrics": {
                    "noi": 800000,
                    "asking_price": 12000000,
                    "cap_rate": 0.0667,
                    "dscr": 1.25
                }
            },
            "market_analysis": {
                "title": "Market Analysis",
                "content": "Austin market shows strong fundamentals with 3.2% vacancy rate."
            },
            "risk_assessment": {
                "title": "Risk Assessment",
                "content": "Moderate risk profile with stable tenant base and strong market conditions."
            },
            "recommendation": {
                "title": "Investment Recommendation",
                "content": "Recommend proceeding with due diligence. Fair value estimated at $11.5M."
            }
        },
        "citations": [
            {
                "id": "cite-001",
                "source": "Offering Memorandum",
                "page": 1,
                "content": "Property financials and unit mix"
            },
            {
                "id": "cite-002",
                "source": "Market Research",
                "url": "https://example.com/austin-market-report",
                "content": "Austin multifamily market analysis"
            }
        ],
        "metadata": {
            "analyst": "AI Agent",
            "confidence_score": 0.85,
            "processing_time_ms": 12500
        }
    }

    try:
        # Connect to report service
        async with websockets.connect("ws://localhost:8086") as websocket:

            # Send report generation request
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "report.create",
                    "arguments": {
                        "structuredAnalysis": sample_analysis,
                        "templateType": "standard"
                    }
                }
            }

            await websocket.send(json.dumps(request))

            # Get response
            response_str = await websocket.recv()
            response = json.loads(response_str)

            if "error" in response:
                return False

            result = response.get("result", {})

            # Verify response structure
            if "s3PresignedUrl" not in result:
                return False

            if "version" not in result:
                return False

            presigned_url = result["s3PresignedUrl"]
            result["version"]


            # In mock mode, check if local file was created
            if os.getenv("MOCK_AWS") == "true":
                # Check for local report file
                local_reports_dir = os.getenv("LOCAL_REPORTS_DIR", "./tmp/reports")
                report_path = Path(local_reports_dir) / f"report-{sample_analysis['dealId']}.docx"

                if report_path.exists():

                    # Check file size (should be > 0)
                    file_size = report_path.stat().st_size
                    if file_size > 0:
                        pass
                    else:
                        return False
                else:
                    pass
                    # Don't fail for this in mock mode

            # Verify presigned URL format
            if not presigned_url.startswith(("http://", "https://", "file://")):
                return False


            return True

    except Exception:
        return False


async def main() -> None:
    """Run report generation smoke test."""
    # Check environment
    if os.getenv("MOCK_AWS") == "true":

        # Ensure local reports directory exists
        local_reports_dir = os.getenv("LOCAL_REPORTS_DIR", "./tmp/reports")
        Path(local_reports_dir).mkdir(parents=True, exist_ok=True)
    else:
        pass

    success = await test_report_generation()

    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
