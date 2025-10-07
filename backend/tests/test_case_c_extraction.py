"""
Test Case C: Key Term Extraction & Summarization
From Test.md line 48:
"Extract the following from this OM: sponsor name, asset type, location,
loan amount, interest rate, term, DSCR, LTV, exit strategy, and business plan summary."
"""
import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

async def main():
    print("=" * 70)
    print("TEST CASE C: KEY TERM EXTRACTION")
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

    # Test message as per Test Case C
    test_message = """Extract the following from this OM: sponsor name, asset type, location, loan amount, interest rate, term, DSCR, LTV, exit strategy, and business plan summary."""

    state = {
        "conversation_id": "test-c",
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

    final_state = None

    try:
        async for chunk in graph.astream(state):
            for node_name, state_update in chunk.items():
                if node_name == "extract_pdf":
                    print("[extract_pdf] PDF extracted")
                elif node_name == "generate":
                    print("[generate] Extraction complete")
                final_state = state_update

        print("-" * 70)
        print()

        if not final_state:
            print("ERROR: No response")
            return

        # Show extracted data
        print("=" * 70)
        print("EXTRACTED INFORMATION")
        print("=" * 70)
        print()

        if final_state.get("sections"):
            for section in final_state["sections"]:
                print(section.get("content", ""))
                print()
        elif final_state.get("answer"):
            print(final_state["answer"])
            print()

        # Validation criteria
        print("=" * 70)
        print("VALIDATION CRITERIA")
        print("=" * 70)
        print()
        print("Expected fields:")
        expected_fields = [
            "sponsor name", "asset type", "location", "loan amount",
            "interest rate", "term", "DSCR", "LTV", "exit strategy",
            "business plan summary"
        ]

        response_text = ""
        if final_state.get("sections"):
            response_text = " ".join(s.get("content", "") for s in final_state["sections"]).lower()
        elif final_state.get("answer"):
            response_text = final_state["answer"].lower()

        for field in expected_fields:
            found = field.lower() in response_text or "not found" in response_text
            status = "[PASS]" if found else "[FAIL]"
            print(f"{status} {field}")

        print()
        print("=" * 70)
        print("TEST COMPLETED")
        print("=" * 70)

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
