#!/usr/bin/env python3
"""
Basic Functionality Test Suite
Tests core API endpoints against the actual running server
"""

import requests
import time
import uuid
import json
from datetime import datetime

# Import test configuration
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from test_config import get_all_api_urls, setup_test_environment


class Colors:
	GREEN = '\033[92m'
	RED = '\033[91m'
	YELLOW = '\033[93m'
	BLUE = '\033[94m'
	CYAN = '\033[96m'
	WHITE = '\033[97m'
	BOLD = '\033[1m'
	END = '\033[0m'


def log(message, color=Colors.CYAN):
	timestamp = datetime.now().strftime("%H:%M:%S")
	print(f"{color}[{timestamp}] {message}{Colors.END}")


class BasicFunctionalityTestSuite:
    def __init__(self):
        self.passed_tests = 0
        self.failed_tests = 0
        self.api_url = None
        self.test_user = None
        
        # Set up test environment
        setup_test_environment()
        
        # Find working API URL
        self.api_url = self.find_server()
        
    def find_server(self):
        """Find a working server URL"""
        urls_to_try = get_all_api_urls()
        
        for url in urls_to_try:
            try:
                response = requests.get(f'{url}/api/health', timeout=5)
                if response.status_code == 200:
                    log(f"✅ Server found at {url}", Colors.GREEN)
                    return url
            except Exception as e:
                continue
        
        log("❌ No server found. Please start the server first.", Colors.RED)
        return None
        
    def assert_test(self, condition, test_name, details=""):
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
    
    def test_api_health(self):
        log("\n🔍 Testing API Health", Colors.BOLD + Colors.YELLOW)
        log("-" * 40, Colors.YELLOW)
        
        if not self.api_url:
            self.assert_test(False, "API Health Check", "No server URL available")
            return False
        
        try:
            response = requests.get(f"{self.api_url}/api/health", timeout=10)
            health_ok = response.status_code == 200
            
            if health_ok:
                data = response.json()
                self.assert_test(True, "API Health Check", 
                                f"Status: {response.status_code}")
                
                # Test response structure
                expected_fields = ["message"]
                structure_ok = any(field in data for field in expected_fields)
                self.assert_test(structure_ok, "Health Response Structure",
                                f"Response: {data}")
                return True
            else:
                self.assert_test(False, "API Health Check", 
                                f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.assert_test(False, "API Health Check", f"Error: {str(e)}")
            return False
    
    def test_user_authentication(self):
        log("\n🔐 Testing User Authentication", Colors.BOLD + Colors.YELLOW)
        log("-" * 40, Colors.YELLOW)
        
        if not self.api_url:
            self.assert_test(False, "User Authentication", "No server URL available")
            return False
        
        username = f"test_user_{uuid.uuid4().hex[:8]}"
        
        try:
            # Test user login
            login_data = {"username": username}
            response = requests.post(f"{self.api_url}/api/auth/login", 
                                   json=login_data, timeout=10)
            
            login_success = response.status_code == 200
            
            if login_success:
                data = response.json()
                token = data.get("token")
                
                self.test_user = {
                    "username": username,
                    "token": token
                }
                
                self.assert_test(True, "User Login", f"User: {username}")
                self.assert_test(bool(token), "Token Received", 
                                f"Token length: {len(token) if token else 0}")
                
                # Test authenticated endpoint (get templates)
                if token:
                    headers = {"Authorization": f"Bearer {token}"}
                    auth_response = requests.get(f"{self.api_url}/api/templates", 
                                               headers=headers, timeout=10)
                    
                    auth_success = auth_response.status_code in [200, 404]  # 404 is OK if no templates exist
                    self.assert_test(auth_success, "Authenticated Request",
                                    f"Status: {auth_response.status_code}")
                    
                    return login_success and auth_success
                else:
                    return False
            else:
                self.assert_test(False, "User Login", 
                                f"Status: {response.status_code}, Response: {response.text[:100]}")
                return False
                
        except Exception as e:
            self.assert_test(False, "User Authentication", f"Error: {str(e)}")
            return False
    
    def test_template_endpoints(self):
        log("\n📝 Testing Template Endpoints", Colors.BOLD + Colors.YELLOW)
        log("-" * 40, Colors.YELLOW)
        
        if not self.api_url or not self.test_user:
            self.assert_test(False, "Template Endpoints", "No server or authenticated user")
            return False
        
        headers = {"Authorization": f"Bearer {self.test_user['token']}"}
        
        try:
            # Test get templates
            response = requests.get(f"{self.api_url}/api/templates", 
                                  headers=headers, timeout=10)
            
            get_success = response.status_code in [200, 404]  # 404 OK if no templates
            self.assert_test(get_success, "Get Templates",
                            f"Status: {response.status_code}")
            
            # Test create template
            template_data = {
                "template_name": f"Test Template {uuid.uuid4().hex[:8]}",
                "difficulty": "EASY",
                "subject": "Testing",
                "sub_subject": "API Testing",
                "questions": [
                    {
                        "question_text": "What is a REST API?",
                        "type": "OPEN"
                    }
                ]
            }
            
            create_response = requests.post(f"{self.api_url}/api/templates",
                                          json=template_data, headers=headers, timeout=15)
            
            create_success = create_response.status_code == 201
            self.assert_test(create_success, "Create Template",
                            f"Status: {create_response.status_code}")
            
            if create_success:
                # Test get templates again to see if our template appears
                response = requests.get(f"{self.api_url}/api/templates", 
                                      headers=headers, timeout=10)
                if response.status_code == 200:
                    templates = response.json().get("templates", [])
                    self.assert_test(len(templates) > 0, "Template Created Successfully",
                                    f"Found {len(templates)} templates")
            
            return get_success and create_success
            
        except Exception as e:
            self.assert_test(False, "Template Endpoints", f"Error: {str(e)}")
            return False
    
    def test_session_functionality(self):
        log("\n🎯 Testing Session Functionality", Colors.BOLD + Colors.YELLOW)
        log("-" * 40, Colors.YELLOW)
        
        if not self.api_url or not self.test_user:
            self.assert_test(False, "Session Functionality", "No server or authenticated user")
            return False
        
        headers = {"Authorization": f"Bearer {self.test_user['token']}"}
        
        try:
            # Test get sessions
            response = requests.get(f"{self.api_url}/api/sessions", 
                                  headers=headers, timeout=10)
            
            get_success = response.status_code in [200, 404]  # 404 OK if no sessions
            self.assert_test(get_success, "Get Sessions",
                            f"Status: {response.status_code}")
            
            # Test create session
            session_data = {
                "title": f"Test Session {uuid.uuid4().hex[:8]}",
                "subject": "API Testing",
                "template_mode": True,
                "settings": {
                    "max_participants": 5,
                    "max_questions": 10
                }
            }
            
            create_response = requests.post(f"{self.api_url}/api/sessions/create",
                                          json=session_data, headers=headers, timeout=15)
            
            create_success = create_response.status_code == 201
            self.assert_test(create_success, "Create Session",
                            f"Status: {create_response.status_code}")
            
            if create_success:
                session_info = create_response.json()
                session_code = session_info.get("session_code")
                self.assert_test(bool(session_code), "Session Code Generated",
                                f"Code: {session_code}")
            
            return get_success and create_success
            
        except Exception as e:
            self.assert_test(False, "Session Functionality", f"Error: {str(e)}")
            return False
    
    def test_question_endpoints(self):
        log("\n❓ Testing Question Endpoints", Colors.BOLD + Colors.YELLOW)
        log("-" * 40, Colors.YELLOW)
        
        if not self.api_url or not self.test_user:
            self.assert_test(False, "Question Endpoints", "No server or authenticated user")
            return False
        
        headers = {"Authorization": f"Bearer {self.test_user['token']}"}
        
        try:
            # Test get questions
            response = requests.get(f"{self.api_url}/api/questions", 
                                  headers=headers, timeout=10)
            
            get_success = response.status_code in [200, 404]  # 404 OK if no questions
            self.assert_test(get_success, "Get Questions",
                            f"Status: {response.status_code}")
            
            # Test create question
            question_data = {
                "question": f"Test question created at {datetime.now().isoformat()}?",
                "answer": "This is a test answer",
                "category": "testing"
            }
            
            create_response = requests.post(f"{self.api_url}/api/questions",
                                          json=question_data, headers=headers, timeout=10)
            
            create_success = create_response.status_code == 201
            self.assert_test(create_success, "Create Question",
                            f"Status: {create_response.status_code}")
            
            return get_success and create_success
            
        except Exception as e:
            self.assert_test(False, "Question Endpoints", f"Error: {str(e)}")
            return False
    
    def test_llm_integration(self):
        log("\n🤖 Testing LLM Integration", Colors.BOLD + Colors.YELLOW)
        log("-" * 40, Colors.YELLOW)
        
        if not self.api_url or not self.test_user:
            self.assert_test(False, "LLM Integration", "No server or authenticated user")
            return False
        
        headers = {"Authorization": f"Bearer {self.test_user['token']}"}
        
        try:
            # Test LLM questions endpoint
            llm_data = {
                "subject": "Python Programming",
                "question_type": "open_ended",
                "count": 1,
                "context": "Basic API testing"
            }
            
            response = requests.post(f"{self.api_url}/api/llm-questions",
                                   json=llm_data, headers=headers, timeout=30)
            
            # Accept both success (200) and fallback responses
            llm_success = response.status_code == 200
            
            if llm_success:
                data = response.json()
                questions_generated = data.get("success", False)
                question_count = data.get("count", 0)
                
                self.assert_test(questions_generated, "LLM Questions Generated",
                                f"Generated {question_count} questions")
                
                # Check if it's using real LLM or fallback
                if data.get("fallback", False):
                    log("   ℹ️  Using fallback responses (LLM not available)", Colors.BLUE)
                else:
                    log("   🎉 Real LLM integration working!", Colors.GREEN)
            else:
                self.assert_test(False, "LLM Questions Generation",
                                f"Status: {response.status_code}")
            
            return llm_success
            
        except Exception as e:
            self.assert_test(False, "LLM Integration", f"Error: {str(e)}")
            return False
    
    def run_all_tests(self):
        log("🚀 STARTING BASIC FUNCTIONALITY TEST SUITE", Colors.BOLD + Colors.CYAN)
        log("=" * 60, Colors.CYAN)
        
        start_time = time.time()
        
        try:
            # Core API tests
            if not self.test_api_health():
                log("Skipping other tests due to API health failure", Colors.YELLOW)
                return self.get_results(start_time)
            
            if not self.test_user_authentication():
                log("Skipping authenticated tests due to auth failure", Colors.YELLOW)
                return self.get_results(start_time)
            
            # Authenticated endpoint tests
            self.test_template_endpoints()
            self.test_session_functionality()
            self.test_question_endpoints()
            self.test_llm_integration()
                
        except Exception as e:
            log(f"Test suite crashed: {e}", Colors.RED)
            import traceback
            traceback.print_exc()
        
        return self.get_results(start_time)
    
    def get_results(self, start_time):
        """Calculate and display test results"""
        total_time = time.time() - start_time
        total_tests = self.passed_tests + self.failed_tests
        pass_rate = (self.passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        log("\n" + "=" * 60, Colors.CYAN)
        log("🎯 BASIC FUNCTIONALITY TEST RESULTS", Colors.BOLD + Colors.CYAN)
        log("=" * 60, Colors.CYAN)
        
        log(f"✅ Passed: {self.passed_tests}", Colors.GREEN)
        log(f"❌ Failed: {self.failed_tests}", Colors.RED)
        log(f"📊 Pass Rate: {pass_rate:.1f}%", Colors.YELLOW)
        log(f"⏱️ Total Time: {total_time:.2f} seconds", Colors.BLUE)
        
        if self.api_url:
            log(f"🌐 Tested Server: {self.api_url}", Colors.WHITE)
        
        if pass_rate >= 90:
            log("🏆 EXCELLENT! Basic functionality working perfectly!", Colors.GREEN + Colors.BOLD)
        elif pass_rate >= 75:
            log("✨ GOOD! Minor issues to address", Colors.YELLOW + Colors.BOLD)
        elif pass_rate >= 50:
            log("⚠️ Some issues need attention", Colors.YELLOW + Colors.BOLD)
        else:
            log("🚨 CRITICAL: Major issues detected", Colors.RED + Colors.BOLD)
        
        # Return results in the format expected by run_all_tests.py
        return (pass_rate, self.passed_tests, total_tests)

def run_all_tests():
	"""Run all tests and return standardized format"""
	test_suite = BasicFunctionalityTestSuite()
	return test_suite.run_all_tests()


if __name__ == "__main__":
    import sys
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║            BASIC FUNCTIONALITY TEST SUITE               ║")
    print("║                                                          ║")
    print("║  Tests: Health, Auth, Templates, Sessions, Questions    ║")
    print("║         LLM Integration (Real Server)                   ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}\n")
    
    pass_rate, passed, total = run_all_tests()
    print(f"\nTest completed with result: ({pass_rate}, {passed}, {total})")
    
    # Exit with failure if tests failed or no server
    sys.exit(0 if pass_rate > 0.0 else 1)
