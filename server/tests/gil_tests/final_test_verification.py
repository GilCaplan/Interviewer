#!/usr/bin/env python3
"""
Final comprehensive test verification to ensure 100% pass rate
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
    """Run comprehensive verification of all test files"""
    print("🎯 FINAL TEST VERIFICATION - COMPREHENSIVE CHECK")
    print("=" * 60)
    
    # Find all test files
    individual_tests_dir = Path("individual_tests")
    test_files = []
    for file_path in individual_tests_dir.glob("*.py"):
        if file_path.name != "__init__.py":
            test_files.append(file_path)
    
    test_files.sort()
    
    print(f"📁 Found {len(test_files)} test files")
    print()
    
    total_passed = 0
    total_tests = 0
    results = []
    failed_tests = []
    
    for i, test_file in enumerate(test_files, 1):
        print(f"[{i:2d}/{len(test_files)}] {test_file.name:<40}", end=" ")
        
        try:
            test_name, (pass_rate, passed, total), errors = run_single_test(test_file)
            results.append((test_name, pass_rate, passed, total, len(errors) > 0))
            
            total_passed += passed
            total_tests += total
            
            if passed == total:
                print(f"✅ {passed}/{total}")
            else:
                print(f"❌ {passed}/{total}")
                failed_tests.append(test_file.name)
                if errors:
                    print(f"    💥 {errors[0][:80]}...")
                    
        except Exception as e:
            print(f"❌ EXCEPTION: {str(e)[:50]}...")
            results.append((test_file.stem, 0.0, 0, 1, True))
            total_tests += 1
            failed_tests.append(test_file.name)
    
    # Final Summary
    overall_pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    
    print(f"\n🎯 FINAL VERIFICATION RESULTS")
    print("=" * 60)
    print(f"   Test Files: {len(test_files)}")
    print(f"   Total Tests: {total_tests}")
    print(f"   Passed: {total_passed}")
    print(f"   Failed: {total_tests - total_passed}")
    print(f"   Pass Rate: {overall_pass_rate:.1f}%")
    
    if overall_pass_rate == 100.0:
        print(f"\n🏆 PERFECT! 100% PASS RATE ACHIEVED!")
        print(f"🎉 ALL {total_tests} TESTS PASSING SUCCESSFULLY!")
        success = True
    else:
        print(f"\n⚠️ {len(failed_tests)} test files still have issues:")
        for failed_test in failed_tests:
            print(f"   ❌ {failed_test}")
        success = False
    
    print(f"\n📊 Test Distribution:")
    categories = {}
    for test_name, pass_rate, passed, total, has_errors in results:
        category = test_name.split('_')[1] if '_' in test_name else 'other'
        if category not in categories:
            categories[category] = {'passed': 0, 'total': 0}
        categories[category]['passed'] += passed
        categories[category]['total'] += total
    
    for category, stats in sorted(categories.items()):
        cat_pass_rate = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
        status = "✅" if cat_pass_rate == 100 else "❌"
        print(f"   {status} {category.title():<20} {cat_pass_rate:>6.1f}% ({stats['passed']}/{stats['total']})")
    
    return success

if __name__ == "__main__":
    success = main()
    exit_code = 0 if success else 1
    print(f"\n{'🎯 VERIFICATION COMPLETE: SUCCESS' if success else '🔄 VERIFICATION COMPLETE: ISSUES REMAIN'}")
    sys.exit(exit_code)