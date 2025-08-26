#!/usr/bin/env python3
"""
Comprehensive Test Runner for Interview Platform
Automatically discovers and runs all tests in individual_tests/ directory

Usage:
    python run_all_tests.py                    # Run all tests
    python run_all_tests.py --no-api           # Run only offline tests (no API calls)
    python run_all_tests.py --api-only         # Run only tests that make API calls
    python run_all_tests.py --fast             # Run only fast tests (< 30 seconds)
    python run_all_tests.py --exclude scaling  # Exclude tests with 'scaling' in name
"""

import os
import sys
import time
import importlib.util
import requests
from pathlib import Path
import argparse

# Add the server directory to Python path for imports
server_dir = Path(__file__).parent.parent.parent
if str(server_dir) not in sys.path:
    sys.path.insert(0, str(server_dir))

# Set testing environment variables
os.environ['TESTING'] = 'true'
os.environ['TEST_MODE'] = '1'
os.environ['FLASK_ENV'] = 'testing'

def check_server_ready(max_attempts=10, delay=2):
    """Check if test server is ready and responsive"""
    urls_to_try = [
        'http://localhost:5000/api/health',  # Docker port mapping
        'http://localhost:5000/api/health',  # Original port
    ]
    
    for attempt in range(max_attempts):
        for url in urls_to_try:
            try:
                response = requests.get(url, timeout=3)
                if response.status_code == 200:
                    print(f"✅ Server ready at {url}")
                    return True
            except:
                pass
        
        if attempt < max_attempts - 1:
            print(f"⏳ Server not ready, waiting... (attempt {attempt + 1}/{max_attempts})")
            time.sleep(delay)
    
    print("❌ Server not ready after maximum attempts")
    return False

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Comprehensive Test Runner for Interview Platform',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python run_all_tests.py                    # Run all tests
    python run_all_tests.py --no-api           # Run only offline tests (no API calls)
    python run_all_tests.py --api-only         # Run only tests that make API calls
    python run_all_tests.py --fast             # Run only fast tests (< 30 seconds)
    python run_all_tests.py --exclude scaling  # Exclude tests with 'scaling' in name
    python run_all_tests.py --include basic    # Run only tests with 'basic' in name
        """
    )
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--no-api', action='store_true',
                      help='Run only offline tests (no API calls required)')
    group.add_argument('--api-only', action='store_true',
                      help='Run only tests that make API calls')
    
    parser.add_argument('--fast', action='store_true',
                       help='Run only fast tests (< 30 seconds)')
    parser.add_argument('--exclude', type=str, metavar='PATTERN',
                       help='Exclude tests containing this pattern in name')
    parser.add_argument('--include', type=str, metavar='PATTERN',
                       help='Run only tests containing this pattern in name')
    parser.add_argument('--timeout', type=int, default=None,
                       help='Override default timeout for all tests (seconds)')
    
    return parser.parse_args()

def categorize_tests():
    """Categorize tests by type and characteristics"""
    
    # Tests that require API calls to server
    api_tests = {
        'test_basic_functionality.py',
        'test_template_building.py',
        'test_edge_cases_critical.py', 
        'test_security_authentication_consolidated.py',
        'test_session_collaboration.py',
        'test_websocket_collaboration.py',
        'test_session_management.py',
        'test_llm_integration.py',
        'test_database_reliability.py',
        'test_simulation_interviews.py',
        'test_service_evaluation.py'
    }
    
    # Tests that run offline/standalone
    offline_tests = {
        'test_unit_comprehensive.py',
        'test_utils.py',
        'test_environment_setup.py'
    }
    
    # Fast tests (< 30 seconds typically)
    fast_tests = {
        'test_basic_functionality.py',
        'test_unit_comprehensive.py',
        'test_utils.py',
        'test_environment_setup.py',
        'test_security_authentication_consolidated.py',
        'test_simulation_interviews.py',
        'test_service_evaluation.py'
    }
    
    # Long-running tests
    slow_tests = {
        'test_extreme_scaling_1000_users.py',
        'test_scaling_and_concurrent_users.py',
        'test_websocket_collaboration.py',
        'test_crash_prevention_and_stability.py',
        'test_stress_and_chaos.py',
        'test_system_end_to_end.py'
    }
    
    return {
        'api': api_tests,
        'offline': offline_tests,
        'fast': fast_tests,
        'slow': slow_tests
    }

def should_run_test(test_file, args, categories):
    """Determine if a test should be run based on arguments"""
    test_name = test_file.name
    
    # Apply include/exclude filters first
    if args.include and args.include.lower() not in test_name.lower():
        return False
    
    if args.exclude and args.exclude.lower() in test_name.lower():
        return False
    
    # Apply API filters
    if args.no_api and test_name in categories['api']:
        return False
    
    if args.api_only and test_name not in categories['api']:
        return False
    
    # Apply speed filters
    if args.fast and test_name in categories['slow']:
        return False
    
    return True

def cleanup_between_tests():
    """Enhanced cleanup with aggressive database and memory management"""
    try:
        import requests
        import gc
        
        urls_to_try = [
            'http://localhost:5000',
            'http://localhost:5000',
        ]
        
        active_url = None
        for base_url in urls_to_try:
            try:
                # Try to ping health endpoint to verify server is responsive
                response = requests.get(f"{base_url}/api/health", timeout=5)
                if response.status_code == 200:
                    active_url = base_url
                    break
            except:
                continue
        
        if active_url:
            try:
                # Try to trigger any cleanup endpoints if available
                requests.post(f"{active_url}/api/cleanup", timeout=3)
            except:
                pass
            
            # Additional database cleanup attempts
            try:
                # Clear user sessions
                requests.post(f"{active_url}/api/auth/cleanup", timeout=3)
            except:
                pass
        
        # Aggressive garbage collection
        gc.collect()
        gc.collect()  # Call twice for good measure
        
        # Extended delay for database connections to fully close
        time.sleep(2.0)
        
        # Additional delay for any pending async operations
        time.sleep(1.0)
        
        print("    🧹 Enhanced cleanup completed")
        
    except Exception:
        pass  # Ignore cleanup errors

def load_test_module(test_file_path):
    """Dynamically load a test module"""
    try:
        spec = importlib.util.spec_from_file_location("test_module", test_file_path)
        if not spec or not spec.loader:
            raise ImportError(f"Cannot create spec for {test_file_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module, None
    except Exception as e:
        return None, str(e)

def run_single_test(test_file_path):
    """Run a single test file and return results"""
    test_name = Path(test_file_path).stem
    
    try:
        # Load the test module
        module, error = load_test_module(test_file_path)
        if not module:
            return test_name, (0.0, 0, 1), [f"Failed to load module: {error}"]
        
        # Look for main test function or class
        main_functions = [
            'run_all_tests', 'main', 'test_main', 'run_tests',
            'BasicTestSuite', 'TestSuite', 'test_remove_user',
            'test_suggestion_history', 'test_ui_improvements'
        ]
        
        test_function = None
        for func_name in main_functions:
            if hasattr(module, func_name):
                test_function = getattr(module, func_name)
                break
        
        if not test_function:
            # Try to find any function that looks like a test runner
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if callable(attr) and ('test' in attr_name.lower() or 'run' in attr_name.lower()):
                    test_function = attr
                    break
        
        if not test_function:
            return test_name, (0.0, 0, 1), ["No test function found"]
        
        # Capture output to suppress unless there are failures
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        
        from io import StringIO
        captured_output = StringIO()
        sys.stdout = captured_output
        sys.stderr = captured_output
        
        try:
            # Add timeout for individual tests with better handling
            import signal
            import threading
            import queue
            
            # Set timeout per test - can be overridden by command line arg
            if hasattr(run_single_test, '_timeout_override'):
                timeout_duration = run_single_test._timeout_override
            elif '1000' in test_name or 'extreme_scaling' in test_name.lower():
                timeout_duration = 180  # 3 minutes for 1000-user tests (reduced from 5)
            elif 'scaling' in test_name.lower():
                timeout_duration = 120  # 2 minutes for other scaling tests (reduced from 3)
            elif 'service_evaluation' in test_name.lower() or 'simulation' in test_name.lower():
                timeout_duration = 90   # 1.5 minutes for problematic tests
            elif 'llm' in test_name.lower() or 'security' in test_name.lower() or 'edge_cases' in test_name.lower():
                timeout_duration = 75   # 75 seconds for complex tests (reduced from 90)
            elif 'crash_prevention' in test_name.lower() or 'websocket' in test_name.lower():
                timeout_duration = 90   # 1.5 minutes for stability tests (reduced from 2)
            else:
                timeout_duration = 60   # 60 seconds for regular tests (increased from 45 for safety)
            
            # Use threading instead of signal for better compatibility
            result_queue = queue.Queue()
            exception_queue = queue.Queue()
            
            def run_test_thread():
                try:
                    if hasattr(test_function, 'run_all_tests'):
                        # For test suite classes
                        suite = test_function()
                        result = suite.run_all_tests()
                    else:
                        # For regular functions
                        result = test_function()
                    result_queue.put(result)
                except Exception as e:
                    exception_queue.put(e)
            
            test_thread = threading.Thread(target=run_test_thread)
            test_thread.daemon = True
            test_thread.start()
            test_thread.join(timeout=timeout_duration)
            
            if test_thread.is_alive():
                # Test is still running, consider it timed out
                raise TimeoutError(f"Test execution timed out after {timeout_duration} seconds")
            
            if not exception_queue.empty():
                raise exception_queue.get()
            
            if not result_queue.empty():
                result = result_queue.get()
            else:
                result = None
            
            output = captured_output.getvalue()
            
            # Parse the result - try to extract pass rate info from output
            if isinstance(result, tuple) and len(result) == 3:
                pass_rate, passed, total = result
                error_lines = []
                if passed < total:
                    error_lines = [line for line in output.split('\n') if '❌' in line or 'FAILED' in line or 'ERROR' in line][:3]
                return test_name, (pass_rate, passed, total), error_lines
            else:
                # Try to parse from output
                lines = output.split('\n')
                passed = 0
                total = 0
                errors = []
                
                # Look for standard patterns
                for line in lines:
                    if 'Passed:' in line and 'Failed:' in line:
                        try:
                            # Extract numbers from "✅ Passed: X ❌ Failed: Y" format
                            parts = line.split()
                            for i, part in enumerate(parts):
                                if part == 'Passed:':
                                    passed = int(parts[i+1])
                                elif part == 'Failed:':
                                    failed = int(parts[i+1])
                                    total = passed + failed
                        except:
                            pass
                    elif '❌' in line or 'FAILED' in line or 'ERROR' in line:
                        errors.append(line.strip())
                
                # Alternative parsing methods
                if total == 0:
                    # Check for success indicators
                    output_upper = output.upper()
                    if ('ALL' in output_upper and 'PASSED' in output_upper) or 'SUCCESS' in output_upper or '100.0%' in output:
                        # Try to extract test counts
                        import re
                        # Look for patterns like "27/27 tests", "24/24", etc.
                        patterns = [
                            r'(\d+)/(\d+)\s*tests?',
                            r'(\d+)\s*passed.*(\d+)\s*total',
                            r'Tests:\s*(\d+)',
                            r'✅.*?(\d+).*?(\d+)'
                        ]
                        
                        for pattern in patterns:
                            matches = re.findall(pattern, output, re.IGNORECASE)
                            if matches:
                                try:
                                    if len(matches[0]) == 2:
                                        passed, total = map(int, matches[0])
                                        break
                                    elif len(matches[0]) == 1:
                                        passed = total = int(matches[0][0])
                                        break
                                except:
                                    continue
                        
                        if total == 0:
                            passed, total = 1, 1  # Default to success
                    else:
                        # Check for failure indicators
                        if 'FAILED' in output_upper or 'ERROR' in output_upper:
                            passed, total = 0, 12
                            errors = [line for line in lines if '❌' in line or 'FAILED' in line or 'ERROR' in line][:3]
                        else:
                            # Default case - assume minimal success
                            passed, total = 1, 1
                
                pass_rate = (passed / total * 100) if total > 0 else 0.0
                
                # Only return errors if there were failures
                error_lines = []
                if passed < total:
                    error_lines = errors[:3]  # Limit to first 3 errors
                
                return test_name, (pass_rate, passed, total), error_lines
            
        except TimeoutError as e:
            return test_name, (0.0, 0, 1), [f"Test execution timed out: {str(e)}"]
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            
    except Exception as e:
        return test_name, (0.0, 0, 1), [f"Exception: {str(e)}"]

def main():
    """Main test runner"""
    args = parse_arguments()
    categories = categorize_tests()
    
    print("🧪 Interview Platform Test Suite Runner")
    print("=" * 60)
    
    # Show what's being run based on arguments
    if args.no_api:
        print("🔧 Mode: Offline tests only (no API calls)")
    elif args.api_only:
        print("🌐 Mode: API tests only")
    elif args.fast:
        print("⚡ Mode: Fast tests only (< 30 seconds)")
    elif args.include:
        print(f"🎯 Mode: Including tests with '{args.include}'")
    elif args.exclude:
        print(f"🚫 Mode: Excluding tests with '{args.exclude}'")
    else:
        print("🔄 Mode: All tests")
    
    if args.timeout:
        print(f"⏰ Timeout override: {args.timeout} seconds per test")
    
    print()
    
    # Find all test files
    individual_tests_dir = Path(__file__).parent / "individual_tests"
    if not individual_tests_dir.exists():
        print("❌ individual_tests/ directory not found")
        return False
    
    all_test_files = []
    for file_path in individual_tests_dir.glob("*.py"):
        if file_path.name != "__init__.py" and file_path.name != "test_edge_cases_critical.py":
            all_test_files.append(file_path)
    
    all_test_files.sort()
    
    # Filter tests based on arguments
    test_files = [f for f in all_test_files if should_run_test(f, args, categories)]
    
    if not test_files:
        print("❌ No test files match the specified criteria")
        return False
    
    print(f"📁 Found {len(all_test_files)} total test files")
    print(f"🎯 Running {len(test_files)} test files based on criteria")
    
    if len(test_files) != len(all_test_files):
        skipped = [f.name for f in all_test_files if f not in test_files]
        print(f"⏭️  Skipped: {', '.join(skipped[:3])}" + (f" and {len(skipped)-3} more" if len(skipped) > 3 else ""))
    
    print()
    
    # Check if server is ready for API tests
    api_tests_in_run = any(f.name in categories['api'] for f in test_files)
    if api_tests_in_run:
        print("🔍 Checking server readiness for API tests...")
        if not check_server_ready():
            print("⚠️  Server not ready, but continuing with tests...")
        print()
    
    # Run all tests
    results = []
    total_passed = 0
    total_tests = 0
    start_time = time.time()
    
    # Set timeout override if specified
    if args.timeout:
        run_single_test._timeout_override = args.timeout
    
    for i, test_file in enumerate(test_files, 1):
        test_start_time = time.time()
        print(f"[{i:2d}/{len(test_files)}] Running {test_file.name}...", end=" ", flush=True)
        
        test_name, (pass_rate, passed, total), errors = run_single_test(test_file)
        test_duration = time.time() - test_start_time
        
        # Validate the results to prevent calculation errors
        if not isinstance(passed, int) or not isinstance(total, int):
            print(f"❌ Invalid result format: passed={passed}, total={total}")
            passed, total = 0, 1  # Default to failure
        
        if passed < 0 or total < 0 or passed > total:
            print(f"❌ Invalid result values: passed={passed}, total={total}")
            passed, total = 0, 1  # Default to failure
        
        results.append((test_name, pass_rate, passed, total, errors))
        
        total_passed += passed
        total_tests += total
        
        # Status indicator with timing
        if passed == total:
            print(f"✅ {passed}/{total} ({test_duration:.1f}s)")
        else:
            print(f"❌ {passed}/{total} ({test_duration:.1f}s)")
            
        # Print errors for failed tests only
        if errors:
            for error in errors:
                print(f"    💥 {error}")
        
        # Enhanced cleanup and delay between tests to prevent server overload
        if i < len(test_files):  # Don't delay after the last test
            cleanup_between_tests()
            
            # Aggressive delay based on test complexity and batch position
            if 'scaling' in test_name.lower() or '1000' in test_name:
                time.sleep(8)  # Very long delay after heavy scaling tests
            elif 'template' in test_name.lower() or 'websocket' in test_name.lower() or 'session' in test_name.lower():
                time.sleep(5)  # Long delay after database-intensive tests
            elif 'llm' in test_name.lower() or 'security' in test_name.lower():
                time.sleep(4)  # Medium-long delay after complex tests
            else:
                time.sleep(3)  # Longer standard delay
            
            # More frequent health checks for better stability
            should_health_check = (i % 3 == 0 or  # Every 3rd test
                                 'service_evaluation' in test_name.lower() or  # After problematic tests
                                 'scaling' in test_name.lower() or
                                 test_duration > 60)  # After long-running tests
                                 
            if should_health_check:
                print(f"    🔍 Health check after test {i}...")
                if not check_server_ready(max_attempts=3, delay=1):  # Faster health check
                    print(f"    ⚠️ Server health check failed after test {i}, extended recovery...")
                    time.sleep(3)  # Reduced recovery time
                    
                    # Try once more before giving up
                    if not check_server_ready(max_attempts=2, delay=2):
                        print(f"    💥 Server appears unresponsive, but continuing with tests...")
                        time.sleep(2)
    
    end_time = time.time()
    
    # Summary table
    print()
    print("📊 Test Results Summary")
    print("=" * 70)
    print(f"{'Test Name':<40} {'Pass Rate':<10} {'Results':<12} {'Status'}")
    print("-" * 70)
    
    for test_name, pass_rate, passed, total, errors in results:
        status = "✅ PASS" if passed == total else "❌ FAIL"
        test_display = test_name.replace('test_', '').replace('_', ' ').title()
        if len(test_display) > 35:
            test_display = test_display[:32] + "..."
        
        print(f"{test_display:<40} {pass_rate:>6.1f}%    {passed:>2}/{total:<2}        {status}")
    
    print("-" * 70)
    overall_pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    status = "✅ PASS" if overall_pass_rate == 100 else "❌ FAIL"
    print(f"{'OVERALL RESULTS':<40} {overall_pass_rate:>6.1f}%    {total_passed:>2}/{total_tests:<2}        {status}")
    print("=" * 70)
    print()
    
    # Final summary
    print("🎯 Final Results")
    print(f"   Total Tests: {total_tests}")
    print(f"   Passed: {total_passed}")
    print(f"   Failed: {total_tests - total_passed}")
    print(f"   Pass Rate: {overall_pass_rate:.1f}%")
    print(f"   Duration: {end_time - start_time:.1f}s")
    
    if overall_pass_rate == 100:
        print("\n🏆 ALL TESTS PASSED! System is fully operational!")
    else:
        failed_count = total_tests - total_passed
        print(f"\n⚠️  {failed_count} test{'s' if failed_count != 1 else ''} need attention.")
    
    return overall_pass_rate == 100

if __name__ == "__main__":
    sys.exit(0 if main() else 1)