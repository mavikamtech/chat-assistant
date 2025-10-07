"""
Test Case B: Real-Time Financial Analysis
Goal: Validate dynamic data retrieval and calculation logic
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from orchestrator.graph import create_graph
import time
import re

async def test_sofr_calculation():
    print("\n" + "="*80)
    print("TEST CASE B: REAL-TIME FINANCIAL ANALYSIS (SOFR)")
    print("="*80 + "\n")

    # Test prompt
    prompt = """What is the latest overnight SOFR rate? Based on that, calculate the interest cost on a $25M loan with a 2.5% spread. Show the formula and result."""

    # Initial state
    initial_state = {
        "user_message": prompt,
        "file_url": None,
        "session_id": "test-case-b",
        "tool_calls": [],
        "selected_tools": []
    }

    print(f"[1/4] Running orchestrator...")
    print(f"      Prompt: {prompt}\n")

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
    print(f"\n[2/4] Orchestrator completed in {duration:.2f} seconds\n")

    # Extract final state
    if isinstance(final_state, dict) and len(final_state) == 1:
        final_state = list(final_state.values())[0]

    print("[3/4] Validation Results:")
    print("-" * 80)

    # Get answer
    answer = final_state.get('answer', '').lower()

    # Validation checks
    checks = []

    # Check 1: Answer generated
    answer_generated = len(answer) > 50
    checks.append(("Answer Generated", answer_generated, f"{len(answer)} chars"))

    # Check 2: SOFR rate mentioned
    has_sofr_rate = 'sofr' in answer and any(re.search(r'\d+\.?\d*\s*%', answer))
    checks.append(("SOFR Rate Mentioned", has_sofr_rate, "Found" if has_sofr_rate else "NOT FOUND"))

    # Check 3: Formula shown
    has_formula = any(keyword in answer for keyword in ['formula', '×', '*', 'principal', 'interest ='])
    checks.append(("Formula Shown", has_formula, "Included" if has_formula else "NOT FOUND"))

    # Check 4: Calculation result
    # Looking for something like $1,958,000 or 1.958M or similar
    has_result = any(keyword in answer for keyword in ['$', 'million', 'annual interest', 'interest cost'])
    checks.append(("Calculation Result", has_result, "Included" if has_result else "NOT FOUND"))

    # Check 5: Source citation (web search)
    web_results = final_state.get('web_results', [])
    has_source = len(web_results) > 0 or 'source' in answer or 'ny fed' in answer or 'federal reserve' in answer
    checks.append(("Source Citation", has_source, f"{len(web_results)} web results" if web_results else "Mentioned in answer"))

    # Check 6: Math appears correct (basic check)
    # For $25M at ~7.8% (5.3% SOFR + 2.5%), interest should be ~$1.95M
    # Check if answer has a number in 1-2 million range
    numbers_in_millions = re.findall(r'\$?(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:million|M)', answer, re.IGNORECASE)
    if numbers_in_millions and isinstance(numbers_in_millions, list) and len(numbers_in_millions) > 0:
        # Convert to float
        amount_str = numbers_in_millions[0]
        if isinstance(amount_str, tuple):
            amount_str = amount_str[0]
        amount = float(str(amount_str).replace(',', ''))
        math_reasonable = 1.5 <= amount <= 2.5  # Reasonable range
        checks.append(("Math Reasonable", math_reasonable, f"~${amount}M annual interest"))
    else:
        checks.append(("Math Reasonable", False, "Could not extract amount"))

    # Check 7: Clear explanation
    has_explanation = len(answer) > 100  # Reasonable length for explanation
    checks.append(("Clear Explanation", has_explanation, "Provided" if has_explanation else "Too brief"))

    # Check 8: Performance
    within_time = duration < 30
    checks.append(("Performance (<30s)", within_time, f"{duration:.2f}s"))

    # Print results
    for check_name, passed, details in checks:
        status = "[OK]" if passed else "[FAIL]"
        print(f"  {status} {check_name:20s}: {details}")

    print("\n" + "="*80)
    print(f"RESULTS: {sum(1 for _, p, _ in checks if p)}/{len(checks)} checks passed")
    print("="*80 + "\n")

    # Print full output
    if answer:
        print("\n[4/4] Full Output:")
        print("-" * 80)
        print(final_state.get('answer', ''))
        print("\n")

    return checks, final_state

if __name__ == "__main__":
    checks, state = asyncio.run(test_sofr_calculation())

    # Exit code based on results
    all_passed = all(passed for _, passed, _ in checks)
    sys.exit(0 if all_passed else 1)
