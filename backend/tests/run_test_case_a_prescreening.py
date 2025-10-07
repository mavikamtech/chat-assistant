"""
Test Case A: Offering Memorandum Pre-Screening
Goal: Validate that the system can ingest an OM and generate a structured pre-screening memo
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from orchestrator.graph import create_graph
import time

async def test_prescreening():
    print("\n" + "="*80)
    print("TEST CASE A: OFFERING MEMORANDUM PRE-SCREENING")
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
    s3_key = f"uploads/test_bend_phase_1_2.pdf"

    print(f"[1/5] Uploading PDF to S3...")
    s3_client.upload_file(pdf_path, bucket, s3_key)
    file_url = f"s3://{bucket}/{s3_key}"
    print(f"      File URL: {file_url}\n")

    # Test prompt
    prompt = """Pre-screen this multifamily deal. Extract key metrics (DSCR, LTV, NOI, CapEx),
summarize the business plan, and flag any underwriting red flags. Format output as a Word memo."""

    # Initial state
    initial_state = {
        "user_message": prompt,
        "file_url": file_url,
        "session_id": "test-case-a",
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

    # Validation checks
    checks = []

    # Check 1: PDF extracted
    pdf_extracted = bool(final_state.get('pdf_text'))
    checks.append(("PDF Extraction", pdf_extracted, f"{len(final_state.get('pdf_text', ''))} chars extracted"))

    # Check 2: Answer generated
    answer = final_state.get('answer', '')
    answer_generated = len(answer) > 100
    checks.append(("Analysis Generated", answer_generated, f"{len(answer)} chars"))

    # Check 3: Contains key metrics
    has_dscr = 'dscr' in answer.lower() or 'debt service' in answer.lower()
    has_ltv = 'ltv' in answer.lower() or 'loan-to-value' in answer.lower()
    has_noi = 'noi' in answer.lower() or 'net operating income' in answer.lower()

    checks.append(("DSCR mentioned", has_dscr, "Found in analysis" if has_dscr else "NOT FOUND"))
    checks.append(("LTV mentioned", has_ltv, "Found in analysis" if has_ltv else "NOT FOUND"))
    checks.append(("NOI mentioned", has_noi, "Found in analysis" if has_noi else "NOT FOUND"))

    # Check 4: Business plan summary
    has_business_plan = any(keyword in answer.lower() for keyword in ['business plan', 'strategy', 'value-add', 'repositioning'])
    checks.append(("Business Plan", has_business_plan, "Included" if has_business_plan else "NOT FOUND"))

    # Check 5: Red flags
    has_red_flags = any(keyword in answer.lower() for keyword in ['risk', 'flag', 'concern', 'caution'])
    checks.append(("Risk Analysis", has_red_flags, "Included" if has_red_flags else "NOT FOUND"))

    # Check 6: Word document generated
    docx_url = final_state.get('docx_url')
    checks.append(("Word Document", bool(docx_url), docx_url if docx_url else "NOT GENERATED"))

    # Check 7: Performance (< 2 min)
    within_time = duration < 120
    checks.append(("Performance (<2min)", within_time, f"{duration:.2f}s"))

    # Print results
    for check_name, passed, details in checks:
        status = "[OK]" if passed else "[FAIL]"
        print(f"  {status} {check_name:20s}: {details}")

    print("\n" + "="*80)
    print(f"RESULTS: {sum(1 for _, p, _ in checks if p)}/{len(checks)} checks passed")
    print("="*80 + "\n")

    # Print sample output
    if answer:
        print("\n[5/5] Sample Output (first 500 chars):")
        print("-" * 80)
        print(answer[:500])
        print("...\n")

    return checks, final_state

if __name__ == "__main__":
    checks, state = asyncio.run(test_prescreening())

    # Exit code based on results
    all_passed = all(passed for _, passed, _ in checks)
    sys.exit(0 if all_passed else 1)
