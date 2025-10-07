"""
End-to-End Test: Frontend → Backend → MCP → Response
Simulates a full request from the frontend with a PDF upload
"""
import asyncio
import sys
import os
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_e2e_with_pdf():
    """Test complete flow with PDF upload"""

    print("=" * 70)
    print("END-TO-END TEST: PDF Upload -> Analysis -> Response")
    print("=" * 70)

    # Step 1: Get most recent PDF from S3
    print("\n[1] Finding most recent PDF in S3...")
    try:
        import boto3
        s3_client = boto3.client('s3', region_name=os.getenv('AWS_REGION', 'us-east-2'))

        response = s3_client.list_objects_v2(
            Bucket='mavik-uploads',
            Prefix='uploads/',
            MaxKeys=10
        )

        if 'Contents' not in response:
            print("[FAIL] No files found in S3")
            return False

        pdf_files = [obj for obj in response['Contents'] if obj['Key'].endswith('.pdf')]
        if not pdf_files:
            print("[FAIL] No PDF files found")
            return False

        latest_pdf = sorted(pdf_files, key=lambda x: x['LastModified'], reverse=True)[0]
        file_url = f"s3://mavik-uploads/{latest_pdf['Key']}"
        print(f"[OK] Using: {file_url}")

    except Exception as e:
        print(f"[FAIL] S3 Error: {e}")
        return False

    # Step 2: Initialize the orchestrator state
    print("\n[2] Initializing orchestrator state...")

    initial_state = {
        "conversation_id": "test-e2e-123",
        "user_message": "Please analyze this commercial real estate offering memorandum and provide a detailed pre-screening analysis.",
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

    print(f"[OK] State initialized with message: {initial_state['user_message'][:50]}...")

    # Step 3: Run through the orchestrator graph
    print("\n[3] Running orchestrator graph...")

    try:
        from orchestrator.graph import create_graph
        graph = create_graph()

        final_state = None
        step_count = 0

        async for chunk in graph.astream(initial_state):
            step_count += 1
            for node_name, state_update in chunk.items():
                print(f"\n  [Step {step_count}] Node: {node_name}")

                # Show tool calls
                if "tool_calls" in state_update and state_update["tool_calls"]:
                    for tool_call in state_update["tool_calls"][-1:]:  # Show only the latest
                        status = tool_call.get("status", "unknown")
                        tool_name = tool_call.get("tool", "unknown")
                        summary = tool_call.get("summary", "")

                        if status == "started":
                            print(f"    > {tool_name}: started")
                        elif status == "completed":
                            duration_ms = tool_call.get("duration_ms", 0)
                            print(f"    > {tool_name}: completed in {duration_ms}ms")
                            print(f"      {summary}")
                        elif status == "failed":
                            print(f"    > {tool_name}: FAILED - {summary}")

                # Show answer
                if "answer" in state_update and state_update["answer"]:
                    answer = state_update["answer"]
                    print(f"    [ANSWER] {answer[:200]}...")

                # Show sections
                if "sections" in state_update and state_update["sections"]:
                    sections = state_update["sections"]
                    print(f"    [SECTIONS] Generated {len(sections)} sections")

                # Show docx
                if "docx_url" in state_update and state_update["docx_url"]:
                    print(f"    [DOCX] {state_update['docx_url']}")

                final_state = state_update

        print(f"\n[OK] Orchestrator completed in {step_count} steps")

    except Exception as e:
        print(f"[FAIL] Orchestrator error: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Step 4: Verify results
    print("\n[4] Verifying results...")

    if not final_state:
        print("[FAIL] No final state returned")
        return False

    # Check if PDF was extracted
    if final_state.get("pdf_text"):
        text_len = len(final_state["pdf_text"])
        print(f"[OK] PDF extracted: {text_len} characters")
    else:
        print("[WARN] No PDF text extracted")

    # Check intent classification
    intent = final_state.get("intent", "unknown")
    print(f"[OK] Intent classified as: {intent}")

    # Check tool calls
    tool_calls = final_state.get("tool_calls", [])
    completed_tools = [tc for tc in tool_calls if tc.get("status") == "completed"]
    failed_tools = [tc for tc in tool_calls if tc.get("status") == "failed"]

    print(f"[OK] Tools executed:")
    print(f"     - Completed: {len(completed_tools)}")
    print(f"     - Failed: {len(failed_tools)}")

    if failed_tools:
        print("\n[WARN] Failed tools:")
        for tool in failed_tools:
            print(f"     - {tool['tool']}: {tool.get('summary', 'Unknown error')}")

    # Check response
    if final_state.get("answer"):
        answer_len = len(final_state["answer"])
        print(f"\n[OK] Answer generated: {answer_len} characters")
        print(f"\nFirst 300 characters:")
        print("-" * 70)
        print(final_state["answer"][:300])
        print("-" * 70)
    elif final_state.get("sections"):
        section_count = len(final_state["sections"])
        print(f"\n[OK] Sections generated: {section_count}")
        if section_count > 0:
            print(f"\nFirst section:")
            print("-" * 70)
            section = final_state["sections"][0]
            print(f"Title: {section.get('title', 'Unknown')}")
            print(f"Content: {section.get('content', '')[:200]}...")
            print("-" * 70)
    else:
        print("[FAIL] No answer or sections generated")
        return False

    print("\n" + "=" * 70)
    print("[SUCCESS] End-to-end test passed!")
    print("=" * 70)
    return True


async def test_e2e_without_pdf():
    """Test complete flow without PDF (simple question)"""

    print("\n\n" + "=" * 70)
    print("END-TO-END TEST: Simple Question -> Response")
    print("=" * 70)

    # Step 1: Initialize state
    print("\n[1] Initializing orchestrator state...")

    initial_state = {
        "conversation_id": "test-e2e-456",
        "user_message": "What is DSCR and why is it important in commercial real estate?",
        "file_url": None,
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

    print(f"[OK] Question: {initial_state['user_message']}")

    # Step 2: Run orchestrator
    print("\n[2] Running orchestrator graph...")

    try:
        from orchestrator.graph import create_graph
        graph = create_graph()

        final_state = None
        step_count = 0

        async for chunk in graph.astream(initial_state):
            step_count += 1
            for node_name, state_update in chunk.items():
                print(f"  [Step {step_count}] {node_name}")
                final_state = state_update

        print(f"[OK] Completed in {step_count} steps")

    except Exception as e:
        print(f"[FAIL] Orchestrator error: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Step 3: Verify results
    print("\n[3] Verifying results...")

    if not final_state or not final_state.get("answer"):
        print("[FAIL] No answer generated")
        return False

    answer = final_state["answer"]
    print(f"[OK] Answer generated: {len(answer)} characters")
    print(f"\nAnswer:")
    print("-" * 70)
    print(answer[:500])
    print("-" * 70)

    print("\n" + "=" * 70)
    print("[SUCCESS] Simple question test passed!")
    print("=" * 70)
    return True


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("MAVIK AI - END-TO-END TESTING SUITE")
    print("=" * 70)

    # Test 1: With PDF
    test1_success = asyncio.run(test_e2e_with_pdf())

    # Test 2: Without PDF
    test2_success = asyncio.run(test_e2e_without_pdf())

    # Summary
    print("\n\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Test 1 (With PDF):    {'[PASS]' if test1_success else '[FAIL]'}")
    print(f"Test 2 (Simple Q&A):  {'[PASS]' if test2_success else '[FAIL]'}")
    print("=" * 70)

    if test1_success and test2_success:
        print("\n[SUCCESS] All tests passed!")
        sys.exit(0)
    else:
        print("\n[FAILED] Some tests failed")
        sys.exit(1)
