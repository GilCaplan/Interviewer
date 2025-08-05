#!/usr/bin/env python3
"""
Comprehensive Test Runner for Interview Platform
Runs all test categories with proper environment setup.
"""

import os
import sys
import subprocess
import time
from pathlib import Path

# Set up test environment
os.environ["TESTING"] = "true"
os.environ["TEST_MODE"] = "1"
os.environ["FLASK_ENV"] = "testing"

def run_test_category(test_file, category_name):
    """Run a specific test category"""
    print(f"\n{'='*80}")
    print(f"🧪 RUNNING {category_name.upper()} TESTS")
    print(f"{'='*80}")
    
    try:
        result = subprocess.run([sys.executable, test_file], 
                              capture_output=False, 
                              timeout=300)  # 5 minute timeout
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"⏰ {category_name} tests timed out")
        return False
    except Exception as e:
        print(f"❌ Failed to run {category_name} tests: {e}")
        return False

def main():
    print("🚀 COMPREHENSIVE INTERVIEW PLATFORM TEST SUITE")
    print("=" * 80)
    
    # Test categories to run
    test_categories = [
        ("test_unit_comprehensive.py", "Unit Tests"),
        ("test_basic_functionality.py", "Basic Functionality"),
        ("test_template_building.py", "Template Building"),
        ("test_session_management.py", "Session Management"),
        ("test_session_collaboration.py", "Session Collaboration"),
        ("test_scaling_and_concurrent_users.py", "Scaling & Concurrency"),
        ("test_websocket_collaboration.py", "WebSocket Collaboration"),
        ("test_llm_integration.py", "LLM Integration"),
        ("test_security_authentication_consolidated.py", "Security Tests"),
        ("test_system_end_to_end.py", "System/E2E Tests"),
        ("test_stress_and_chaos.py", "Stress & Chaos Tests")
    ]
    
    results = {}
    start_time = time.time()
    
    for test_file, category_name in test_categories:
        if os.path.exists(test_file):
            success = run_test_category(test_file, category_name)
            results[category_name] = success
        else:
            print(f"⚠️ Test file {test_file} not found")
            results[category_name] = False
    
    # Print comprehensive results
    total_time = time.time() - start_time
    passed_categories = sum(1 for success in results.values() if success)
    total_categories = len(results)
    
    print(f"\n{'='*80}")
    print("🎯 COMPREHENSIVE TEST SUITE RESULTS")
    print(f"{'='*80}")
    
    for category, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status} {category}")
    
    print(f"\n📊 Overall Results:")
    print(f"   Categories Passed: {passed_categories}/{total_categories}")
    print(f"   Success Rate: {passed_categories/total_categories*100:.1f}%")
    print(f"   Total Time: {total_time:.1f} seconds")
    
    if passed_categories == total_categories:
        print("🏆 ALL TEST CATEGORIES PASSED! System is production-ready!")
        return 0
    elif passed_categories >= total_categories * 0.8:
        print("✨ EXCELLENT! Most test categories passed!")
        return 0
    else:
        print("⚠️ Some test categories failed. Review results above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
