#!/usr/bin/env python3
"""
Debug script to check what individual test files are returning
"""

import os
import sys
from pathlib import Path

# Set testing environment variables
os.environ['TESTING'] = 'true'
os.environ['TEST_MODE'] = '1'
os.environ['FLASK_ENV'] = 'testing'

sys.path.append('.')
from run_all_tests import run_single_test

def main():
    """Debug individual test results"""
    print("🔍 Debugging Test Results")
    print("=" * 50)
    
    # Test with just a few files to see what they return
    test_files = [
        "individual_tests/test_simple_demo.py",
        "individual_tests/test_basic_functionality.py",
        "individual_tests/test_unit_comprehensive.py"
    ]
    
    total_passed = 0
    total_tests = 0
    
    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"\n🧪 Testing {test_file}")
            try:
                test_name, (pass_rate, passed, total), errors = run_single_test(test_file)
                print(f"   Raw result: test_name='{test_name}', pass_rate={pass_rate}, passed={passed}, total={total}")
                print(f"   Errors: {errors}")
                
                # Check for invalid values
                if not isinstance(passed, int) or not isinstance(total, int):
                    print(f"   ⚠️  INVALID TYPES: passed type={type(passed)}, total type={type(total)}")
                
                if passed < 0 or total < 0 or passed > total:
                    print(f"   ⚠️  INVALID VALUES: passed={passed}, total={total}")
                
                total_passed += passed
                total_tests += total
                
                print(f"   Running totals: total_passed={total_passed}, total_tests={total_tests}")
                
            except Exception as e:
                print(f"   ❌ Exception: {e}")
                import traceback
                traceback.print_exc()
    
    print(f"\n📊 Final Totals:")
    print(f"   Total Passed: {total_passed}")
    print(f"   Total Tests: {total_tests}")
    if total_tests > 0:
        pass_rate = (total_passed / total_tests * 100)
        print(f"   Pass Rate: {pass_rate:.1f}%")
        print(f"   Failed: {total_tests - total_passed}")

if __name__ == "__main__":
    main()