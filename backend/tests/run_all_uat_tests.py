"""
UAT Test Runner - Executes all test cases and generates comprehensive acceptance report
"""

import asyncio
import sys
import os
from datetime import datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import test modules
from run_test_case_a_prescreening import test_prescreening
from run_test_case_b_sofr import test_sofr_calculation
from run_test_case_c_extraction import test_key_term_extraction

async def run_all_tests():
    print("\n" + "="*100)
    print(" " * 30 + "MAVIK AI - UAT TEST SUITE")
    print(" " * 25 + f"Execution Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*100 + "\n")

    all_results = {}

    # Test Case A
    print("\n" + "#"*100)
    print("# RUNNING TEST CASE A: OFFERING MEMORANDUM PRE-SCREENING")
    print("#"*100)
    try:
        checks_a, state_a = await test_prescreening()
        all_results['Test Case A'] = {
            'checks': checks_a,
            'state': state_a,
            'passed': all(passed for _, passed, _ in checks_a)
        }
    except Exception as e:
        print(f"\n[ERROR] Test Case A failed with exception: {e}")
        all_results['Test Case A'] = {
            'checks': [],
            'state': None,
            'passed': False,
            'error': str(e)
        }

    # Test Case B
    print("\n" + "#"*100)
    print("# RUNNING TEST CASE B: REAL-TIME FINANCIAL ANALYSIS (SOFR)")
    print("#"*100)
    try:
        checks_b, state_b = await test_sofr_calculation()
        all_results['Test Case B'] = {
            'checks': checks_b,
            'state': state_b,
            'passed': all(passed for _, passed, _ in checks_b)
        }
    except Exception as e:
        print(f"\n[ERROR] Test Case B failed with exception: {e}")
        all_results['Test Case B'] = {
            'checks': [],
            'state': None,
            'passed': False,
            'error': str(e)
        }

    # Test Case C
    print("\n" + "#"*100)
    print("# RUNNING TEST CASE C: KEY TERM EXTRACTION & SUMMARIZATION")
    print("#"*100)
    try:
        checks_c, state_c = await test_key_term_extraction()
        all_results['Test Case C'] = {
            'checks': checks_c,
            'state': state_c,
            'passed': all(passed for _, passed, _ in checks_c)
        }
    except Exception as e:
        print(f"\n[ERROR] Test Case C failed with exception: {e}")
        all_results['Test Case C'] = {
            'checks': [],
            'state': None,
            'passed': False,
            'error': str(e)
        }

    # Generate summary report
    generate_summary_report(all_results)

    return all_results

def generate_summary_report(all_results):
    print("\n" + "="*100)
    print(" " * 35 + "UAT SUMMARY REPORT")
    print("="*100 + "\n")

    # Overall stats
    total_tests = len(all_results)
    passed_tests = sum(1 for result in all_results.values() if result['passed'])
    total_checks = sum(len(result.get('checks', [])) for result in all_results.values())
    passed_checks = sum(sum(1 for _, p, _ in result.get('checks', []) if p) for result in all_results.values())

    print(f"Overall Results:")
    print(f"  - Test Cases: {passed_tests}/{total_tests} passed ({passed_tests/total_tests*100:.1f}%)")
    print(f"  - Checks: {passed_checks}/{total_checks} passed ({passed_checks/total_checks*100 if total_checks > 0 else 0:.1f}%)")
    print()

    # Test-by-test breakdown
    print("Test Case Breakdown:")
    print("-" * 100)

    for test_name, result in all_results.items():
        if result.get('error'):
            print(f"\n{test_name}: [FAILED - Exception]")
            print(f"  Error: {result['error']}")
            continue

        checks = result.get('checks', [])
        test_passed = result.get('passed', False)
        status = "[PASS]" if test_passed else "[FAIL]"

        print(f"\n{test_name}: {status}")
        print(f"  Checks: {sum(1 for _, p, _ in checks if p)}/{len(checks)} passed")

        # Show failed checks
        failed = [(name, details) for name, passed, details in checks if not passed]
        if failed:
            print(f"  Failed Checks:")
            for name, details in failed:
                print(f"    - {name}: {details}")

    print("\n" + "="*100)

    # Functional Accuracy Section
    print("\n" + "="*100)
    print("FUNCTIONAL ACCURACY ASSESSMENT")
    print("="*100 + "\n")

    functional_criteria = [
        ("Key Metric Extraction", ["DSCR", "LTV", "NOI"], 'Test Case A'),
        ("Business Plan Summary", ["Business Plan"], 'Test Case A'),
        ("Red Flag Identification", ["Risk Analysis"], 'Test Case A'),
        ("Real-Time Data Accuracy", ["SOFR Rate Mentioned"], 'Test Case B'),
        ("Math Accuracy", ["Math Reasonable"], 'Test Case B'),
    ]

    for criterion, check_names, test_case in functional_criteria:
        test_result = all_results.get(test_case, {})
        checks = test_result.get('checks', [])

        relevant_checks = [(name, passed) for name, passed, _ in checks if any(cn in name for cn in check_names)]
        if relevant_checks:
            all_passed = all(passed for _, passed in relevant_checks)
            status = "[OK]" if all_passed else "[FAIL]"
            print(f"{status} {criterion:30s}: {sum(1 for _, p in relevant_checks if p)}/{len(relevant_checks)} checks passed")
        else:
            print(f"[N/A] {criterion:30s}: Not tested")

    # Output Quality Section
    print("\n" + "="*100)
    print("OUTPUT QUALITY ASSESSMENT")
    print("="*100 + "\n")

    quality_criteria = [
        ("Memo Format", ["Answer Generated"], 'Test Case A'),
        ("Clarity & Readability", ["Clear Explanation"], 'Test Case B'),
        ("Source Referencing", ["Source Citation"], 'Test Case B'),
        ("Completeness", ["Sponsor Name", "Asset Type", "Location"], 'Test Case C'),
    ]

    for criterion, check_names, test_case in quality_criteria:
        test_result = all_results.get(test_case, {})
        checks = test_result.get('checks', [])

        relevant_checks = [(name, passed) for name, passed, _ in checks if any(cn in name for cn in check_names)]
        if relevant_checks:
            all_passed = all(passed for _, passed in relevant_checks)
            status = "[OK]" if all_passed else "[FAIL]"
            print(f"{status} {criterion:30s}: {sum(1 for _, p in relevant_checks if p)}/{len(relevant_checks)} checks passed")
        else:
            print(f"[N/A] {criterion:30s}: Not tested")

    # System Behavior Section
    print("\n" + "="*100)
    print("SYSTEM BEHAVIOR ASSESSMENT")
    print("="*100 + "\n")

    system_criteria = [
        ("File Handling", ["PDF Extraction"], 'Test Case A'),
        ("Prompt Responsiveness", ["Answer Generated"], ['Test Case A', 'Test Case B', 'Test Case C']),
        ("Performance", ["Performance"], ['Test Case A', 'Test Case B', 'Test Case C']),
    ]

    for criterion, check_names, test_cases in system_criteria:
        if isinstance(test_cases, str):
            test_cases = [test_cases]

        all_checks = []
        for tc in test_cases:
            test_result = all_results.get(tc, {})
            checks = test_result.get('checks', [])
            relevant = [(name, passed) for name, passed, _ in checks if any(cn in name for cn in check_names)]
            all_checks.extend(relevant)

        if all_checks:
            all_passed = all(passed for _, passed in all_checks)
            status = "[OK]" if all_passed else "[FAIL]"
            print(f"{status} {criterion:30s}: {sum(1 for _, p in all_checks if p)}/{len(all_checks)} checks passed")
        else:
            print(f"[N/A] {criterion:30s}: Not tested")

    # Final recommendation
    print("\n" + "="*100)
    print("RECOMMENDATION")
    print("="*100 + "\n")

    overall_pass_rate = passed_checks / total_checks * 100 if total_checks > 0 else 0

    if overall_pass_rate >= 90:
        recommendation = "READY FOR PRODUCTION - System meets all critical acceptance criteria"
    elif overall_pass_rate >= 75:
        recommendation = "READY WITH MINOR FIXES - Address failed checks before production deployment"
    elif overall_pass_rate >= 50:
        recommendation = "NEEDS IMPROVEMENT - Significant issues require resolution"
    else:
        recommendation = "NOT READY - Major functionality gaps detected"

    print(f"Overall Score: {overall_pass_rate:.1f}%")
    print(f"Status: {recommendation}")
    print()

    # Save report to file
    save_report_to_file(all_results, overall_pass_rate, recommendation)

def save_report_to_file(all_results, overall_pass_rate, recommendation):
    """Save detailed report to markdown file"""

    report_path = os.path.join(os.path.dirname(__file__), '..', '..', 'tests', 'UAT_REPORT.md')

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# Mavik AI - UAT Acceptance Report\n\n")
        f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Overall Score**: {overall_pass_rate:.1f}%\n\n")
        f.write(f"**Status**: {recommendation}\n\n")
        f.write("---\n\n")

        f.write("## Executive Summary\n\n")

        total_tests = len(all_results)
        passed_tests = sum(1 for result in all_results.values() if result['passed'])
        total_checks = sum(len(result.get('checks', [])) for result in all_results.values())
        passed_checks = sum(sum(1 for _, p, _ in result.get('checks', []) if p) for result in all_results.values())

        f.write(f"- **Test Cases**: {passed_tests}/{total_tests} passed\n")
        f.write(f"- **Individual Checks**: {passed_checks}/{total_checks} passed\n\n")

        f.write("## Test Results\n\n")

        for test_name, result in all_results.items():
            f.write(f"### {test_name}\n\n")

            if result.get('error'):
                f.write(f"**Status**: ❌ FAILED (Exception)\n\n")
                f.write(f"**Error**: {result['error']}\n\n")
                continue

            checks = result.get('checks', [])
            test_passed = result.get('passed', False)
            status = "✅ PASSED" if test_passed else "❌ FAILED"

            f.write(f"**Status**: {status}\n\n")
            f.write(f"**Checks**: {sum(1 for _, p, _ in checks if p)}/{len(checks)} passed\n\n")

            f.write("| Check | Status | Details |\n")
            f.write("|-------|--------|----------|\n")

            for name, passed, details in checks:
                status_icon = "✅" if passed else "❌"
                f.write(f"| {name} | {status_icon} | {details} |\n")

            f.write("\n")

        f.write("## Recommendations\n\n")
        f.write(f"{recommendation}\n\n")

        # List failed checks
        failed_checks_all = []
        for test_name, result in all_results.items():
            if not result.get('error'):
                failed = [(test_name, name, details) for name, passed, details in result.get('checks', []) if not passed]
                failed_checks_all.extend(failed)

        if failed_checks_all:
            f.write("### Items Requiring Attention\n\n")
            for test_name, check_name, details in failed_checks_all:
                f.write(f"- **{test_name} - {check_name}**: {details}\n")
            f.write("\n")

    print(f"\n[REPORT SAVED] {report_path}\n")

if __name__ == "__main__":
    results = asyncio.run(run_all_tests())

    # Exit code
    all_passed = all(result['passed'] for result in results.values())
    sys.exit(0 if all_passed else 1)
