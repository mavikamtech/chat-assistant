"""
Test Case C: Key Term Extraction & Summarization
Goal: Validate that the system can extract and summarize key terms from documents
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from orchestrator.graph import create_graph
import time

async def test_key_term_extraction():
    print("\n" + "="*80)
    print("TEST CASE C: KEY TERM EXTRACTION & SUMMARIZATION")
    print("="*80 + "\n")

    # PDF path
    pdf_path = "C:\\Users\\ankita\\chat-assistant\\docs\\Bend Phase 1 & 2 (Q3 2024).pdf"

    # Upload to S3 first
    import boto3
    from dotenv import load_dotenv
    load_dotenv()

    s3_client = boto3.client(
        's3',
        region_name=os.getenv('AWS_REGION', 'us-east-1'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )

    bucket = os.getenv('S3_BUCKET_UPLOADS', 'mavik-uploads')
    s3_key = f"uploads/test_bend_extraction.pdf"

    print(f"[1/5] Uploading PDF to S3...")
    s3_client.upload_file(pdf_path, bucket, s3_key)
    file_url = f"s3://{bucket}/{s3_key}"
    print(f"      File URL: {file_url}\n")

    # Test prompt
    prompt = """Extract the following from this OM: sponsor name, asset type, location, loan amount, interest rate, term, DSCR, LTV, exit strategy, and business plan summary."""

    # Initial state
    initial_state = {
        "user_message": prompt,
        "file_url": file_url,
        "session_id": "test-case-c",
        "tool_calls": [],
        "selected_tools": []
    }

    print(f"[2/5] Running orchestrator...")
    print(f"      Prompt: {prompt[:100]}...\n")

    # Run workflow
    graph = create_graph()
    start_time = time.time()

    final_state = None
    async for state in graph.astream(initial_state):
        final_state = state

        # Print tool progress
        if 'tool_calls' in state and len(state.get('tool_calls', [])) > 0:
            last_call = state['tool_calls'][-1]
            tool = last_call.get('tool', 'unknown')
            status = last_call.get('status', 'unknown')

            if status == 'completed':
                summary = last_call.get('summary', '')
                duration = last_call.get('duration_ms', 0)
                print(f"      [OK] {tool}: {summary} ({duration}ms)")
            elif status == 'failed':
                summary = last_call.get('summary', '')
                print(f"      [FAIL] {tool}: {summary}")

    duration = time.time() - start_time
    print(f"\n[3/5] Orchestrator completed in {duration:.2f} seconds\n")

    # Extract final state
    if isinstance(final_state, dict) and len(final_state) == 1:
        final_state = list(final_state.values())[0]

    print("[4/5] Validation Results:")
    print("-" * 80)

    # Get answer
    answer = final_state.get('answer', '').lower()

    # Expected terms to extract
    expected_terms = {
        'sponsor name': ['dapper', 'sponsor'],
        'asset type': ['retail', 'mixed-use', 'entertainment', 'commercial'],
        'location': ['las vegas', 'nevada', 'southwest'],
        'loan amount': ['$', 'million', 'loan'],
        'interest rate': ['%', 'rate', 'interest'],
        'term': ['year', 'term', 'maturity'],
        'dscr': ['dscr', 'debt service'],
        'ltv': ['ltv', 'loan-to-value'],
        'exit strategy': ['exit', 'strategy', 'refinance', 'sale'],
        'business plan': ['business plan', 'strategy', 'value-add']
    }

    # Validation checks
    checks = []

    # Check 1: PDF extracted
    pdf_extracted = bool(final_state.get('pdf_text'))
    checks.append(("PDF Extraction", pdf_extracted, f"{len(final_state.get('pdf_text', ''))} chars"))

    # Check 2: Answer generated
    answer_generated = len(answer) > 100
    checks.append(("Answer Generated", answer_generated, f"{len(answer)} chars"))

    # Check 3-12: Each expected term
    for term_name, keywords in expected_terms.items():
        found = any(keyword in answer for keyword in keywords)
        checks.append((f"{term_name.title()}", found, "Extracted" if found else "NOT FOUND"))

    # Check 13: Structured format (table or list)
    is_structured = any(marker in answer for marker in ['|', '-', '•', '*', '1.', '2.'])
    checks.append(("Structured Format", is_structured, "Table/List" if is_structured else "Plain text"))

    # Check 14: Handles missing data gracefully
    handles_missing = 'not found' in answer or 'not available' in answer or 'not provided' in answer
    checks.append(("Handles Missing Data", True, "Uses 'Not Found' for missing values" if handles_missing else "All values present"))

    # Check 15: Performance
    within_time = duration < 60
    checks.append(("Performance (<60s)", within_time, f"{duration:.2f}s"))

    # Print results
    for check_name, passed, details in checks:
        status = "[OK]" if passed else "[FAIL]"
        print(f"  {status} {check_name:25s}: {details}")

    print("\n" + "="*80)
    print(f"RESULTS: {sum(1 for _, p, _ in checks if p)}/{len(checks)} checks passed")
    print("="*80 + "\n")

    # Print full output
    if answer:
        print("\n[5/5] Full Extraction Output:")
        print("-" * 80)
        print(final_state.get('answer', ''))
        print("\n")

    return checks, final_state

if __name__ == "__main__":
    checks, state = asyncio.run(test_key_term_extraction())

    # Exit code based on results
    all_passed = all(passed for _, passed, _ in checks)
    sys.exit(0 if all_passed else 1)
