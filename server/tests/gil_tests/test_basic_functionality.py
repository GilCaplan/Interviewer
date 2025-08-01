#!/usr/bin/env python3
"""
Basic Functionality Test Suite
Tests core API endpoints and basic template building functionality

Run with: python test_basic_functionality.py
"""

import requests
import json
import time
import uuid
from datetime import datetime

# Test Configuration - Try both ports
API_URLS = ["http://localhost:5001", "http://localhost:5001"]
API_URL = None

class Colors:
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
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{color}[{timestamp}] {message}{Colors.END}")

def find_running_server():
    global API_URL
    for url in API_URLS:
        try:
            response = requests.get(f"{url}/api/health", timeout=3)
            if response.status_code == 200:
                API_URL = url
                log(f"Found server running on {url}", Colors.GREEN)
                return True
        except:
            continue
    
    log("No server found on any port", Colors.RED)
    return False

class BasicTestSuite:
    def __init__(self):
        self.passed_tests = 0
        self.failed_tests = 0
        self.test_user = None
        
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
    
    def test_server_connectivity(self):
        log("\n🔍 Testing Server Connectivity", Colors.BOLD + Colors.YELLOW)
        log("-" * 40, Colors.YELLOW)
        
        # Test health endpoint
        try:
            response = requests.get(f"{API_URL}/api/health", timeout=5)
            health_ok = response.status_code == 200
            
            if health_ok:
                health_data = response.json()
                self.assert_test(True, "API Health Check", 
                                f"Status: {health_data.get('status', 'unknown')}")
            else:
                self.assert_test(False, "API Health Check", f"Status: {response.status_code}")
                
        except Exception as e:
            self.assert_test(False, "API Health Check", f"Error: {e}")
            return False
        
        # Test info endpoint
        try:
            response = requests.get(f"{API_URL}/api/info", timeout=5)
            info_ok = response.status_code == 200
            
            if info_ok:
                info_data = response.json()
                features = info_data.get('features', [])
                self.assert_test(True, "API Info Endpoint", 
                                f"Features: {len(features)}")
            else:
                self.assert_test(False, "API Info Endpoint", f"Status: {response.status_code}")
                
        except Exception as e:
            self.assert_test(False, "API Info Endpoint", f"Error: {e}")
        
        return health_ok
    
    def test_user_authentication(self):
        log("\n🔐 Testing User Authentication", Colors.BOLD + Colors.YELLOW)
        log("-" * 40, Colors.YELLOW)
        
        username = f"basic_test_user_{uuid.uuid4().hex[:8]}"
        
        try:
            response = requests.post(f"{API_URL}/api/auth/login",
                                   json={"username": username},
                                   timeout=5)
            
            login_success = response.status_code == 200
            
            if login_success:
                auth_data = response.json()
                token = auth_data.get("token")
                
                self.test_user = {
                    "username": username,
                    "token": token,
                    "headers": {"Authorization": f"Bearer {token}"}
                }
                
                self.assert_test(True, "User Login", f"User: {username}")
                
                # Test token verification
                verify_response = requests.get(f"{API_URL}/api/auth/verify",
                                             headers=self.test_user["headers"],
                                             timeout=5)
                
                token_valid = verify_response.status_code == 200
                self.assert_test(token_valid, "Token Verification", 
                                f"Token valid: {token_valid}")
                
                return login_success and token_valid
            else:
                self.assert_test(False, "User Login", f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.assert_test(False, "User Login", f"Error: {e}")
            return False
    
    def test_template_endpoints(self):
        log("\n📝 Testing Template Endpoints", Colors.BOLD + Colors.YELLOW)
        log("-" * 40, Colors.YELLOW)
        
        if not self.test_user:
            log("No authenticated user for template testing", Colors.RED)
            return False
        
        # Test get question types endpoint
        try:
            response = requests.get(f"{API_URL}/api/templates/question-types",
                                  headers=self.test_user["headers"],
                                  timeout=5)
            
            if response.status_code == 200:
                types_data = response.json()
                question_types = types_data.get("question_types", {})
                difficulty_levels = types_data.get("difficulty_levels", [])
                subjects = types_data.get("subjects", [])
                
                self.assert_test(len(question_types) >= 5, "Question Types Available",
                                f"Found {len(question_types)} question types")
                self.assert_test(len(difficulty_levels) >= 3, "Difficulty Levels",
                                f"Found {len(difficulty_levels)} levels")
                self.assert_test(len(subjects) >= 5, "Subjects Available",
                                f"Found {len(subjects)} subjects")
            else:
                self.assert_test(False, "Question Types Endpoint", 
                                f"Status: {response.status_code}")
                
        except Exception as e:
            self.assert_test(False, "Question Types Endpoint", f"Error: {e}")
        
        # Test create template
        template_data = {
            "template_name": "Basic Test Template",
            "description": "A simple test template",
            "subject": "algorithms",
            "difficulty": "medium",
            "is_public": False
        }
        
        try:
            response = requests.post(f"{API_URL}/api/templates",
                                   json=template_data,
                                   headers=self.test_user["headers"],
                                   timeout=5)
            
            template_created = response.status_code == 201
            
            if template_created:
                template_info = response.json().get("template", {})
                template_id = template_info.get("template_id")
                
                self.assert_test(True, "Template Creation",
                                f"Template ID: {template_id[:8]}...")
                
                # Test get templates
                response = requests.get(f"{API_URL}/api/templates",
                                      headers=self.test_user["headers"],
                                      timeout=5)
                
                if response.status_code == 200:
                    templates_data = response.json().get("templates", [])
                    self.assert_test(len(templates_data) >= 1, "Get Templates",
                                    f"Found {len(templates_data)} templates")
                
                # Cleanup - delete the test template
                requests.delete(f"{API_URL}/api/templates/{template_id}",
                              headers=self.test_user["headers"])
                
                return True
            else:
                self.assert_test(False, "Template Creation", 
                                f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.assert_test(False, "Template Creation", f"Error: {e}")
            return False
    
    def test_session_functionality(self):
        log("\n🎯 Testing Session Functionality", Colors.BOLD + Colors.YELLOW)
        log("-" * 40, Colors.YELLOW)
        
        if not self.test_user:
            log("No authenticated user for session testing", Colors.RED)
            return False
        
        # Test session creation
        session_data = {
            "title": "Basic Test Session",
            "subject": "python",
            "template_mode": True,
            "settings": {
                "max_participants": 5,
                "max_questions": 10,
                "allow_llm": True
            }
        }
        
        try:
            response = requests.post(f"{API_URL}/api/sessions/create",
                                   json=session_data,
                                   headers=self.test_user["headers"],
                                   timeout=5)
            
            session_created = response.status_code == 201
            
            if session_created:
                session_info = response.json().get("session", {})
                session_id = session_info.get("session_id")
                session_code = session_info.get("session_code")
                
                self.assert_test(True, "Session Creation",
                                f"Session Code: {session_code}")
                
                # Test get session data
                response = requests.get(f"{API_URL}/api/sessions/{session_id}",
                                      headers=self.test_user["headers"],
                                      timeout=5)
                
                session_data_ok = response.status_code == 200
                self.assert_test(session_data_ok, "Get Session Data",
                                "Session data retrieved successfully")
                
                # Test list sessions
                response = requests.get(f"{API_URL}/api/sessions/list",
                                      headers=self.test_user["headers"],
                                      timeout=5)
                
                if response.status_code == 200:
                    sessions_list = response.json().get("sessions", [])
                    self.assert_test(len(sessions_list) >= 1, "List Sessions",
                                    f"Found {len(sessions_list)} sessions")
                
                return session_created and session_data_ok
            else:
                self.assert_test(False, "Session Creation", 
                                f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.assert_test(False, "Session Creation", f"Error: {e}")
            return False
    
    def test_mock_llm_basic(self):
        log("\n🤖 Testing Basic Mock LLM", Colors.BOLD + Colors.YELLOW)
        log("-" * 40, Colors.YELLOW)
        
        # Create a simple session first
        session_data = {
            "title": "LLM Test Session",
            "subject": "algorithms",
            "template_mode": True,
            "settings": {"allow_llm": True, "max_questions": 5}
        }
        
        try:
            # Create session
            response = requests.post(f"{API_URL}/api/sessions/create",
                                   json=session_data,
                                   headers=self.test_user["headers"],
                                   timeout=5)
            
            if response.status_code != 201:
                self.assert_test(False, "LLM Test Session Creation", "Failed to create session")
                return False
            
            session_id = response.json().get("session", {}).get("session_id")
            
            # Start building a question
            response = requests.post(f"{API_URL}/api/sessions/{session_id}/questions/1/start",
                                   json={"type": "open_ended"},
                                   headers=self.test_user["headers"],
                                   timeout=5)
            
            if response.status_code == 200:
                question_id = response.json().get("question", {}).get("question_id")
                
                self.assert_test(True, "Question Building Start",
                                f"Question ID: {question_id[:8]}...")
                
                # Test LLM suggestion
                llm_data = {
                    "field": "question_text",
                    "context": "Generate a basic algorithm question"
                }
                
                response = requests.post(f"{API_URL}/api/sessions/{session_id}/questions/{question_id}/llm-suggest",
                                       json=llm_data,
                                       headers=self.test_user["headers"],
                                       timeout=5)
                
                llm_success = response.status_code == 200
                
                if llm_success:
                    suggestion = response.json().get("suggestion", {})
                    suggested_text = suggestion.get("suggested_value", "")
                    
                    self.assert_test(len(suggested_text) > 10, "LLM Suggestion Quality",
                                    f"Generated: {suggested_text[:50]}...")
                else:
                    self.assert_test(False, "LLM Suggestion", 
                                    f"Status: {response.status_code}")
                
                return llm_success
            else:
                self.assert_test(False, "Question Building Start", 
                                f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.assert_test(False, "Mock LLM Test", f"Error: {e}")
            return False
    
    def run_all_tests(self):
        log("🚀 STARTING BASIC FUNCTIONALITY TEST SUITE", Colors.BOLD + Colors.CYAN)
        log("=" * 60, Colors.CYAN)
        
        start_time = time.time()
        
        try:
            self.test_server_connectivity()
            
            if self.test_user_authentication():
                self.test_template_endpoints()
                self.test_session_functionality()
                self.test_mock_llm_basic()
            else:
                log("Skipping other tests due to authentication failure", Colors.YELLOW)
                
        except Exception as e:
            log(f"Test suite crashed: {e}", Colors.RED)
            import traceback
            traceback.print_exc()
        
        # Print results
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
        log(f"🌐 Server URL: {API_URL}", Colors.MAGENTA)
        
        if pass_rate >= 90:
            log("🏆 EXCELLENT! Basic functionality is working perfectly!", Colors.GREEN + Colors.BOLD)
        elif pass_rate >= 75:
            log("✨ GOOD! Minor issues to address", Colors.YELLOW + Colors.BOLD)
        elif pass_rate >= 50:
            log("⚠️ FAIR! Several issues need attention", Colors.YELLOW + Colors.BOLD)
        else:
            log("🚨 POOR! Major issues need immediate attention", Colors.RED + Colors.BOLD)

if __name__ == "__main__":
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║              BASIC FUNCTIONALITY TEST SUITE              ║")
    print("║                                                          ║")
    print("║  Tests: Connectivity, Auth, Templates, Sessions, LLM     ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}\n")
    
    # Find running server
    if find_running_server():
        test_suite = BasicTestSuite()
        test_suite.run_all_tests()
    else:
        log("❌ No server found. Please start the server first.", Colors.RED)
        log("💡 Try: docker-compose up --build", Colors.BLUE)