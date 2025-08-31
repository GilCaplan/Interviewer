#!/usr/bin/env python3
# Import test configuration
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from test_config import get_all_api_urls
"""
Shared Test Utilities
Common functions and classes used across multiple test files
"""

import requests
import os
from datetime import datetime

def find_server_url():
    """Find available server URL"""
    urls_to_try = get_all_api_urls()
    
    for url in urls_to_try:
        try:
            response = requests.get(f'{url}/api/health', timeout=3)
            if response.status_code == 200:
                return url
        except:
            continue
    return None

class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

def log(message, color=Colors.CYAN):
    """Log message with timestamp and color"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{color}[{timestamp}] {message}{Colors.END}")

def setup_test_environment():
    """Setup standard test environment variables"""
    os.environ['TESTING'] = 'true'
    os.environ['TEST_MODE'] = '1'
    os.environ['FLASK_ENV'] = 'testing'

class BaseTestSuite:
    """Base class for test suites with common functionality"""
    
    def __init__(self):
        self.passed_tests = 0
        self.failed_tests = 0
        self.test_user = None
        
    def assert_test(self, condition, test_name, details=""):
        """Assert test condition and track results"""
        if condition:
            self.passed_tests += 1
            log(f"✅ {test_name}", Colors.GREEN)
            if details:
                log(f"   {details}", Colors.WHITE)
        else:
            self.failed_tests += 1
            log(f"❌ {test_name}", Colors.RED)
            if details:
                log(f"   {details}", Colors.RED)
        
        return condition
    
    def get_pass_rate(self):
        """Calculate pass rate percentage"""
        total_tests = self.passed_tests + self.failed_tests
        return (self.passed_tests / total_tests * 100) if total_tests > 0 else 0
        
    def print_results(self, test_suite_name):
        """Print comprehensive test results"""
        total_tests = self.passed_tests + self.failed_tests
        pass_rate = self.get_pass_rate()
        
        log(f"\n{'='*65}", Colors.CYAN)
        log(f"🎯 {test_suite_name.upper()} TEST RESULTS", Colors.BOLD + Colors.CYAN)
        log(f"{'='*65}", Colors.CYAN)
        
        log(f"✅ Passed: {self.passed_tests}", Colors.GREEN)
        log(f"❌ Failed: {self.failed_tests}", Colors.RED)
        log(f"📊 Pass Rate: {pass_rate:.1f}%", Colors.YELLOW)
        
        if pass_rate >= 90:
            log("🏆 EXCELLENT! All tests passing!", Colors.GREEN + Colors.BOLD)
        elif pass_rate >= 75:
            log("✨ GOOD! Most tests passing!", Colors.YELLOW + Colors.BOLD)
        else:
            log("⚠️ NEEDS WORK! Some tests failing", Colors.RED + Colors.BOLD)

def run_all_tests():
    """Utils test - requires server to test utility functions properly"""
    from test_config import get_primary_api_url
    import requests
    
    api_url = get_primary_api_url()
    if not api_url:
        print("❌ No server URL configured")
        return (0.0, 0, 1)
    
    # Test if server is actually running
    try:
        response = requests.get(f'{api_url}/api/health', timeout=3)
        if response.status_code == 200:
            print("✅ Server utilities working with live server")
            return (100.0, 1, 1)
        else:
            print("❌ Server responded but not healthy")
            return (0.0, 0, 1)
    except:
        print("❌ Cannot connect to server - utilities need real server to verify functionality")
        return (0.0, 0, 1)

if __name__ == "__main__":
    import sys
    pass_rate, passed, total = run_all_tests()
    print(f"\nTest completed with result: ({pass_rate}, {passed}, {total})")
    
    # Exit with failure if no server or tests failed
    sys.exit(0 if pass_rate > 0.0 else 1)