"""
Simple test for PDF upload flow
Tests: Frontend upload -> S3 -> Textract -> Response
"""
import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

async def main():
    print("Testing PDF Flow...")
    print("-" * 60)

    # Get latest PDF from S3
    import boto3
    s3 = boto3.client('s3', region_name=os.getenv('AWS_REGION', 'us-east-2'))

    response = s3.list_objects_v2(Bucket='mavik-uploads', Prefix='uploads/', MaxKeys=5)
    pdfs = [o for o in response.get('Contents', []) if o['Key'].endswith('.pdf')]

    if not pdfs:
        print("ERROR: No PDFs found in S3")
        return

    latest = sorted(pdfs, key=lambda x: x['LastModified'], reverse=True)[0]
    file_url = f"s3://mavik-uploads/{latest['Key']}"

    print(f"Using: {file_url}")
    print()

    # Initialize state
    state = {
        "conversation_id": "test-123",
        "user_message": "Analyze this PDF",
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

    print("Running orchestrator...")
    step = 0
    final_state = None

    try:
        async for chunk in graph.astream(state):
            step += 1
            for node_name, state_update in chunk.items():
                print(f"  Step {step}: {node_name}")

                # Check for errors in tool calls
                if "tool_calls" in state_update:
                    for tc in state_update["tool_calls"]:
                        if tc.get("status") == "failed":
                            print(f"    ERROR: {tc.get('tool')} failed - {tc.get('summary')}")
                        elif tc.get("status") == "completed":
                            print(f"    OK: {tc.get('tool')} - {tc.get('summary')}")

                final_state = state_update

        print()
        print("=" * 60)
        print("RESULTS")
        print("=" * 60)

        if final_state:
            # Check PDF extraction
            if final_state.get("pdf_text"):
                text_len = len(final_state["pdf_text"])
                print(f"PDF Text: {text_len} characters")
                print(f"Sample: {final_state['pdf_text'][:200]}...")
            else:
                print("WARNING: No PDF text extracted")

            # Check intent
            print(f"Intent: {final_state.get('intent', 'unknown')}")

            # Check answer/sections
            if final_state.get("answer"):
                print(f"Answer: {final_state['answer'][:200]}...")
            elif final_state.get("sections"):
                print(f"Sections: {len(final_state['sections'])} generated")
            else:
                print("WARNING: No answer or sections")

            print()
            print("SUCCESS: Flow completed")
        else:
            print("ERROR: No final state")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
