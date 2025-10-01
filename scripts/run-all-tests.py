#!/usr/bin/env python3
"""
Master test runner for all Mavik AI services
Runs all test suites in proper order with comprehensive reporting
"""

import asyncio
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime

# Color codes for output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}{Colors.ENDC}")

def print_success(text):
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.OKBLUE}ℹ️  {text}{Colors.ENDC}")

def run_test_script(script_name, description):
    """Run a test script and return success status"""

    print_info(f"Running {description}...")

    script_path = Path("scripts") / script_name
    if not script_path.exists():
        print_error(f"Test script {script_name} not found")
        return False

    try:
        start_time = time.time()
        result = subprocess.run([sys.executable, str(script_path)],
                              capture_output=True, text=True, timeout=300)
        end_time = time.time()

        duration = end_time - start_time

        if result.returncode == 0:
            print_success(f"{description} completed successfully ({duration:.1f}s)")
            return True
        else:
            print_error(f"{description} failed ({duration:.1f}s)")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print_error(f"{description} timed out (>300s)")
        return False
    except Exception as e:
        print_error(f"{description} error: {e}")
        return False

def check_docker_services():
    """Check if Docker services are running"""

    print_info("Checking Docker services...")

    try:
        result = subprocess.run(["docker-compose", "ps"],
                              capture_output=True, text=True)

        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:  # Header + service lines
                services = [line for line in lines[1:] if line.strip()]
                running_services = [s for s in services if "Up" in s]

                print_success(f"Docker Compose services: {len(running_services)}/{len(services)} running")

                if len(running_services) < len(services):
                    print_warning("Some services are not running. Consider running 'docker-compose up -d'")

                return len(running_services) > 0
            else:
                print_warning("No Docker services found")
                return False
        else:
            print_warning("Docker Compose not running")
            return False

    except Exception as e:
        print_warning(f"Could not check Docker services: {e}")
        return False

def generate_test_report(results):
    """Generate a comprehensive test report"""

    print_header("TEST REPORT SUMMARY")

    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result['success'])
    failed_tests = total_tests - passed_tests

    print(f"📊 Total Tests: {total_tests}")
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(f"📈 Success Rate: {(passed_tests/total_tests)*100:.1f}%")

    print(f"\n{Colors.BOLD}Detailed Results:{Colors.ENDC}")

    for test_name, result in results.items():
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        duration = result.get('duration', 0)
        print(f"  {status} {test_name} ({duration:.1f}s)")

    # Generate recommendations
    print(f"\n{Colors.BOLD}Recommendations:{Colors.ENDC}")

    if failed_tests == 0:
        print("🎉 All tests passed! The system is ready for use.")
        print("   - You can proceed with development")
        print("   - Consider running integration tests regularly")
        print("   - Monitor service health in production")
    else:
        print("🔧 Some tests failed. Please address the following:")
        for test_name, result in results.items():
            if not result['success']:
                print(f"   - Fix issues in {test_name}")

        print("\n💡 Troubleshooting tips:")
        print("   - Check if all services are running: docker-compose ps")
        print("   - Review logs: docker-compose logs [service_name]")
        print("   - Restart services: docker-compose restart")
        print("   - Check TESTING.md for detailed guidance")

async def main():
    """Main test runner"""

    print_header("MAVIK AI - COMPREHENSIVE TEST SUITE")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Test configuration
    tests = [
        ("test-infrastructure.py", "Infrastructure & CDK"),
        ("test-rag-server.py", "RAG MCP Server"),
        ("test-parser-server.py", "Parser MCP Server"),
        ("test-findb-server.py", "FinDB MCP Server"),
        ("test-integration.py", "Integration & End-to-End")
    ]

    results = {}

    # Step 1: Check prerequisites
    print_header("PREREQUISITES CHECK")

    docker_running = check_docker_services()
    if not docker_running:
        print_warning("Docker services not running. Some tests may fail.")
        print_info("Start services with: docker-compose up -d")

    # Step 2: Run individual test suites
    print_header("RUNNING TEST SUITES")

    for script_name, description in tests:
        start_time = time.time()
        success = run_test_script(script_name, description)
        end_time = time.time()

        results[description] = {
            'success': success,
            'duration': end_time - start_time
        }

        # Short pause between tests
        if script_name != tests[-1][0]:  # Not the last test
            time.sleep(2)

    # Step 3: Generate report
    generate_test_report(results)

    # Step 4: Exit with appropriate code
    all_passed = all(result['success'] for result in results.values())

    print_header("TEST SUITE COMPLETED")
    print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if all_passed:
        print_success("All tests passed! 🎉")
        sys.exit(0)
    else:
        print_error("Some tests failed! Please review the report above.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
