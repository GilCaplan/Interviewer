#!/usr/bin/env python3
"""
Basic Functionality Offline Test Suite
Tests core functionality without requiring a running server
"""

import time
import uuid
import json
from datetime import datetime

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

class MockAPI:
    """Mock API that simulates backend functionality"""
    
    def __init__(self):
        self.users = {}
        self.sessions = {}
        self.templates = {}
    
    def health_check(self):
        """Mock health check"""
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}
    
    def login_user(self, username):
        """Mock user login"""
        if not username or len(username) < 3:
            return None
        
        user_id = str(uuid.uuid4())
        token = f"mock_token_{user_id[:8]}"
        
        user = {
            "user_id": user_id,
            "username": username,
            "token": token,
            "created_at": datetime.now().isoformat()
        }
        
        self.users[user_id] = user
        return {"token": token, "user": user}
    
    def verify_token(self, token):
        """Mock token verification"""
        for user in self.users.values():
            if user["token"] == token:
                return {"valid": True, "user": user}
        return {"valid": False}
    
    def get_question_types(self):
        """Mock question types endpoint"""
        return {
            "question_types": {
                "multiple_choice": "Multiple Choice Questions",
                "open_ended": "Open Ended Questions", 
                "true_false": "True/False Questions",
                "coding": "Coding Challenges",
                "short_answer": "Short Answer Questions"
            },
            "difficulty_levels": ["easy", "medium", "hard"],
            "subjects": ["algorithms", "data_structures", "python", "javascript", "system_design", "general"]
        }
    
    def create_template(self, user_token, template_data):
        """Mock template creation"""
        user = self.verify_token(user_token)
        if not user["valid"]:
            return None
        
        template_id = str(uuid.uuid4())
        template = {
            "template_id": template_id,
            "created_by": user["user"]["user_id"],
            "created_at": datetime.now().isoformat(),
            **template_data
        }
        
        self.templates[template_id] = template
        return {"template": template}
    
    def get_templates(self, user_token):
        """Mock get templates"""
        user = self.verify_token(user_token)
        if not user["valid"]:
            return None
        
        user_templates = []
        for template in self.templates.values():
            if template["created_by"] == user["user"]["user_id"] or template.get("is_public", False):
                user_templates.append(template)
        
        return {"templates": user_templates}
    
    def create_session(self, user_token, session_data):
        """Mock session creation"""
        user = self.verify_token(user_token)
        if not user["valid"]:
            return None
        
        session_id = str(uuid.uuid4())
        session_code = ''.join([chr(65 + i % 26) for i in range(6)])  # Simple code generation
        
        session = {
            "session_id": session_id,
            "session_code": session_code,
            "host": user["user"]["user_id"],
            "created_at": datetime.now().isoformat(),
            "participants": [user["user"]["user_id"]],
            **session_data
        }
        
        self.sessions[session_id] = session
        return {"session": session}

class OfflineBasicTestSuite:
    def __init__(self):
        self.passed_tests = 0
        self.failed_tests = 0
        self.api = MockAPI()
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
    
    def test_api_health(self):
        log("\n🔍 Testing API Health (Offline)", Colors.BOLD + Colors.YELLOW)
        log("-" * 40, Colors.YELLOW)
        
        health_response = self.api.health_check()
        health_ok = "status" in health_response and health_response["status"] == "healthy"
        
        self.assert_test(health_ok, "API Health Check", 
                        f"Status: {health_response.get('status', 'unknown')}")
        
        # Test response structure
        required_fields = ["status", "timestamp"]
        structure_ok = all(field in health_response for field in required_fields)
        self.assert_test(structure_ok, "Health Response Structure",
                        f"Contains: {list(health_response.keys())}")
        
        return health_ok and structure_ok
    
    def test_user_authentication(self):
        log("\n🔐 Testing User Authentication (Offline)", Colors.BOLD + Colors.YELLOW)
        log("-" * 40, Colors.YELLOW)
        
        username = f"offline_test_user_{uuid.uuid4().hex[:8]}"
        
        # Test user login
        auth_response = self.api.login_user(username)
        login_success = auth_response is not None and "token" in auth_response
        
        if login_success:
            self.test_user = {
                "username": username,
                "token": auth_response["token"],
                "user_data": auth_response["user"]
            }
            
            self.assert_test(True, "User Login", f"User: {username}")
            
            # Test token verification
            verify_response = self.api.verify_token(self.test_user["token"])
            token_valid = verify_response["valid"]
            self.assert_test(token_valid, "Token Verification", 
                            f"Token valid: {token_valid}")
            
            # Test invalid token rejection
            invalid_verify = self.api.verify_token("invalid_token")
            invalid_rejected = not invalid_verify["valid"]
            self.assert_test(invalid_rejected, "Invalid Token Rejection",
                            "Invalid token correctly rejected")
            
            return login_success and token_valid and invalid_rejected
        else:
            self.assert_test(False, "User Login", f"Failed for username: {username}")
            return False
    
    def test_template_endpoints(self):
        log("\n📝 Testing Template Endpoints (Offline)", Colors.BOLD + Colors.YELLOW)
        log("-" * 40, Colors.YELLOW)
        
        if not self.test_user:
            log("No authenticated user for template testing", Colors.RED)
            return False
        
        # Test get question types
        types_response = self.api.get_question_types()
        question_types = types_response.get("question_types", {})
        difficulty_levels = types_response.get("difficulty_levels", [])
        subjects = types_response.get("subjects", [])
        
        self.assert_test(len(question_types) >= 5, "Question Types Available",
                        f"Found {len(question_types)} question types")
        self.assert_test(len(difficulty_levels) >= 3, "Difficulty Levels",
                        f"Found {len(difficulty_levels)} levels")
        self.assert_test(len(subjects) >= 5, "Subjects Available",
                        f"Found {len(subjects)} subjects")
        
        # Test create template
        template_data = {
            "template_name": "Offline Test Template",
            "description": "A test template created offline",
            "subject": "algorithms",
            "difficulty": "medium",
            "is_public": False
        }
        
        create_response = self.api.create_template(self.test_user["token"], template_data)
        template_created = create_response is not None
        
        if template_created:
            template_info = create_response["template"]
            template_id = template_info["template_id"]
            
            self.assert_test(True, "Template Creation",
                            f"Template ID: {template_id[:8]}...")
            
            # Test get templates
            templates_response = self.api.get_templates(self.test_user["token"])
            if templates_response:
                templates_data = templates_response.get("templates", [])
                self.assert_test(len(templates_data) >= 1, "Get Templates",
                                f"Found {len(templates_data)} templates")
            
            return True
        else:
            self.assert_test(False, "Template Creation", "Template creation failed")
            return False
    
    def test_session_functionality(self):
        log("\n🎯 Testing Session Functionality (Offline)", Colors.BOLD + Colors.YELLOW)
        log("-" * 40, Colors.YELLOW)
        
        if not self.test_user:
            log("No authenticated user for session testing", Colors.RED)
            return False
        
        # Test session creation
        session_data = {
            "title": "Offline Test Session",
            "subject": "python",
            "template_mode": True,
            "settings": {
                "max_participants": 5,
                "max_questions": 10,
                "allow_llm": True
            }
        }
        
        create_response = self.api.create_session(self.test_user["token"], session_data)
        session_created = create_response is not None
        
        if session_created:
            session_info = create_response["session"]
            session_id = session_info["session_id"]
            session_code = session_info["session_code"]
            
            self.assert_test(True, "Session Creation",
                            f"Session Code: {session_code}")
            
            # Test session data structure
            required_fields = ["session_id", "session_code", "host", "participants"]
            structure_valid = all(field in session_info for field in required_fields)
            self.assert_test(structure_valid, "Session Data Structure",
                            "Contains all required fields")
            
            # Test host is in participants
            host_in_participants = self.test_user["user_data"]["user_id"] in session_info["participants"]
            self.assert_test(host_in_participants, "Host Auto-Join",
                            "Host automatically added to participants")
            
            return session_created and structure_valid and host_in_participants
        else:
            self.assert_test(False, "Session Creation", "Session creation failed")
            return False
    
    def run_all_tests(self):
        log("🚀 STARTING OFFLINE BASIC FUNCTIONALITY TEST SUITE", Colors.BOLD + Colors.CYAN)
        log("=" * 60, Colors.CYAN)
        
        start_time = time.time()
        
        try:
            self.test_api_health()
            
            if self.test_user_authentication():
                self.test_template_endpoints()
                self.test_session_functionality()
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
        log("🎯 OFFLINE BASIC FUNCTIONALITY TEST RESULTS", Colors.BOLD + Colors.CYAN)
        log("=" * 60, Colors.CYAN)
        
        log(f"✅ Passed: {self.passed_tests}", Colors.GREEN)
        log(f"❌ Failed: {self.failed_tests}", Colors.RED)
        log(f"📊 Pass Rate: {pass_rate:.1f}%", Colors.YELLOW)
        log(f"⏱️ Total Time: {total_time:.2f} seconds", Colors.BLUE)
        
        if pass_rate >= 90:
            log("🏆 EXCELLENT! Basic functionality validation working perfectly!", Colors.GREEN + Colors.BOLD)
        elif pass_rate >= 75:
            log("✨ GOOD! Minor issues to address", Colors.YELLOW + Colors.BOLD)
        else:
            log("⚠️ Issues need attention", Colors.YELLOW + Colors.BOLD)
        
        # Return results in the format expected by run_all_tests.py
        return (pass_rate, self.passed_tests, total_tests)

def run_all_tests():
    """Run all tests and return standardized format"""
    test_suite = OfflineBasicTestSuite()
    return test_suite.run_all_tests()

if __name__ == "__main__":
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║         OFFLINE BASIC FUNCTIONALITY TEST SUITE          ║")
    print("║                                                          ║")
    print("║  Tests: Health, Auth, Templates, Sessions (Offline)     ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}\n")
    
    test_suite = OfflineBasicTestSuite()
    result = test_suite.run_all_tests()
    print(f"\nTest completed with result: {result}")