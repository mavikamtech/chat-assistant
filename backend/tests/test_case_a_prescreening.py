"""
Test Case A: Offering Memorandum Pre-Screening
From Test.md line 16:
"Pre-screen this multifamily deal. Extract key metrics (DSCR, LTV, NOI, CapEx),
summarize the business plan, and flag any underwriting red flags."
"""
import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

async def main():
    print("=" * 70)
    print("TEST CASE A: PRE-SCREENING WITH METRICS EXTRACTION")
    print("=" * 70)

    # Get latest PDF
    import boto3
    s3 = boto3.client('s3', region_name=os.getenv('AWS_REGION', 'us-east-2'))
    response = s3.list_objects_v2(Bucket='mavik-uploads', Prefix='uploads/', MaxKeys=5)
    pdfs = [o for o in response.get('Contents', []) if o['Key'].endswith('.pdf')]

    if not pdfs:
        print("ERROR: No PDFs found")
        return

    latest = sorted(pdfs, key=lambda x: x['LastModified'], reverse=True)[0]
    file_url = f"s3://mavik-uploads/{latest['Key']}"

    print(f"\nPDF: {latest['Key'].split('/')[-1]}")
    print()

    # Test message as per Test Case A
    test_message = """Pre-screen this multifamily deal. Extract key metrics (DSCR, LTV, NOI, CapEx), summarize the business plan, and flag any underwriting red flags. Format output as a structured analysis."""

    state = {
        "conversation_id": "test-a",
        "user_message": test_message,
        "file_url": file_url,
        "tool_calls": [],
        "intent": "",
        "requires_pdf": False,
        "selected_tools": [],
        "pdf_text": None,
        "pdf_tables": [],
        "rag_results": [],
        "web_results": [],
        "finance_calcs": {},
        "sections": None,
        "answer": None,
        "docx_url": None
    }

    # Run orchestrator
    from orchestrator.graph import create_graph
    graph = create_graph()

    print("USER REQUEST:")
    print(test_message)
    print()
    print("Processing...")
    print("-" * 70)

    import time
    start_time = time.time()
    final_state = None

    try:
        async for chunk in graph.astream(state):
            for node_name, state_update in chunk.items():
                if node_name == "extract_pdf":
                    print("[extract_pdf] PDF extracted")
                elif node_name == "search_web":
                    print("[search_web] Web research complete")
                elif node_name == "generate":
                    print("[generate] Analysis complete")
                elif node_name == "create_docx":
                    print("[create_docx] Word document generated")
                final_state = state_update

        elapsed = time.time() - start_time
        print("-" * 70)
        print(f"Time: {elapsed:.1f}s")
        print()

        if not final_state:
            print("ERROR: No response")
            return

        # Show analysis
        print("=" * 70)
        print("PRE-SCREENING ANALYSIS")
        print("=" * 70)
        print()

        if final_state.get("sections"):
            for section in final_state["sections"][:3]:  # Show first 3 sections
                title = section.get("title", "")
                content = section.get("content", "")
                print(f"## {title}")
                print()
                # Show first 500 chars of each section
                preview = content[:500] + "..." if len(content) > 500 else content
                print(preview)
                print()
                print("-" * 70)
                print()

        # Check for DOCX
        if final_state.get("docx_url"):
            print(f"[DOCX] Report available: {final_state['docx_url'][:80]}...")
            print()

        # Validation
        print("=" * 70)
        print("VALIDATION CRITERIA")
        print("=" * 70)
        print()

        response_text = ""
        if final_state.get("sections"):
            response_text = " ".join(s.get("content", "") for s in final_state["sections"]).lower()

        checks = {
            "DSCR mentioned": "dscr" in response_text,
            "LTV mentioned": "ltv" in response_text,
            "NOI mentioned": "noi" in response_text,
            "CapEx mentioned": "capex" in response_text or "capital expenditure" in response_text,
            "Business plan summarized": "business plan" in response_text or "strategy" in response_text,
            "Red flags identified": "red flag" in response_text or "risk" in response_text or "concern" in response_text,
            "Structured format": len(final_state.get("sections", [])) > 3,
            "Completed in < 2 min": elapsed < 120
        }

        for check, passed in checks.items():
            status = "[PASS]" if passed else "[FAIL]"
            print(f"{status} {check}")

        print()
        print("=" * 70)
        print(f"TEST {'PASSED' if all(checks.values()) else 'PARTIALLY PASSED'}")
        print("=" * 70)

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
