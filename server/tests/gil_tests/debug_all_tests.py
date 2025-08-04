#!/usr/bin/env python3
"""
Debug script to check all test files for abnormal results
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
    """Debug all test results to find the problematic ones"""
    print("🔍 Debugging All Test Results")
    print("=" * 60)
    
    # Find all test files
    individual_tests_dir = Path("individual_tests")
    test_files = []
    for file_path in individual_tests_dir.glob("*.py"):
        if file_path.name != "__init__.py":
            test_files.append(file_path)
    
    test_files.sort()
    
    total_passed = 0
    total_tests = 0
    problematic_tests = []
    
    for i, test_file in enumerate(test_files, 1):
        print(f"[{i:2d}/{len(test_files)}] {test_file.name:<40}", end=" ")
        
        try:
            test_name, (pass_rate, passed, total), errors = run_single_test(test_file)
            
            # Check for abnormal values
            is_problematic = False
            
            if not isinstance(passed, int) or not isinstance(total, int):
                print(f"❌ INVALID TYPES: {type(passed)}, {type(total)}")
                is_problematic = True
            elif passed < 0 or total < 0:
                print(f"❌ NEGATIVE VALUES: {passed}/{total}")
                is_problematic = True
            elif passed > total:
                print(f"❌ IMPOSSIBLE: {passed}/{total}")
                is_problematic = True
            elif total > 100:  # Flag unusually high test counts
                print(f"⚠️  HIGH COUNT: {passed}/{total}")
                is_problematic = True
            else:
                print(f"✅ {passed}/{total}")
            
            if is_problematic:
                problematic_tests.append((test_file.name, passed, total, errors))
            
            # Use valid values for totals
            if isinstance(passed, int) and isinstance(total, int) and passed >= 0 and total >= 0 and passed <= total:
                total_passed += passed
                total_tests += total
                
        except Exception as e:
            print(f"❌ EXCEPTION: {str(e)[:50]}...")
            problematic_tests.append((test_file.name, "EXCEPTION", str(e), []))
    
    print(f"\n📊 Summary:")
    print(f"   Total Passed: {total_passed}")
    print(f"   Total Tests: {total_tests}")
    if total_tests > 0:
        pass_rate = (total_passed / total_tests * 100)
        print(f"   Pass Rate: {pass_rate:.1f}%")
        print(f"   Failed: {total_tests - total_passed}")
    
    if problematic_tests:
        print(f"\n🚨 Problematic Tests ({len(problematic_tests)}):")
        for test_name, passed, total, errors in problematic_tests:
            print(f"   {test_name}: passed={passed}, total={total}")
            if errors and len(errors) > 0:
                print(f"      First error: {errors[0][:80]}...")

if __name__ == "__main__":
    main()