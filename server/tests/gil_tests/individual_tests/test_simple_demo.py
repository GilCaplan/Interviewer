#!/usr/bin/env python3
"""
Simple demo test for testing the new test runner structure
"""

def run_all_tests():
    """Demo test that always passes"""
    print("Running demo test...")
    print("✅ Passed: 5")
    print("❌ Failed: 0") 
    print("📊 Pass Rate: 100.0%")
    return (100.0, 5, 5)

if __name__ == "__main__":
    result = run_all_tests()
    print(f"Demo test completed with result: {result}")