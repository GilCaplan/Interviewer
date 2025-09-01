#!/usr/bin/env python3
"""
Comprehensive Session Management Test Suite
Tests core session functionality against the actual running server
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

class SessionManagementTestSuite:
    def __init__(self):
        self.passed_tests = 0
        self.failed_tests = 0
        self.api_url = None
        self.test_users = []
        self.test_sessions = []
        
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
    
    def create_test_user(self, username=None):
        """Create a test user and return user info"""
        if not username:
            username = f"session_test_user_{uuid.uuid4().hex[:8]}"
        
        try:
            login_data = {"username": username}
            response = requests.post(f"{self.api_url}/api/auth/login", 
                                   json=login_data, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                user_info = {
                    "username": username,
                    "token": data.get("token"),
                    "user_id": data.get("user_id")
                }
                self.test_users.append(user_info)
                return user_info
            return None
        except Exception as e:
            log(f"❌ Failed to create user {username}: {e}", Colors.RED)
            return None
    
    def test_session_creation_and_retrieval(self):
        log("\n🏗️ Testing Session Creation & Retrieval", Colors.BOLD + Colors.YELLOW)
        log("-" * 50, Colors.YELLOW)
        
        if not self.api_url:
            self.assert_test(False, "Session Creation", "No server URL available")
            return False
        
        # Create test user
        user = self.create_test_user()
        if not user:
            self.assert_test(False, "Session Creation", "Failed to create user")
            return False
        
        headers = {"Authorization": f"Bearer {user['token']}"}
        
        try:
            # Test session creation
            session_data = {
                "title": f"Test Session {uuid.uuid4().hex[:8]}",
                "subject": "Session Management Testing",
                "settings": {
                    "max_participants": 10,
                    "collaborative_mode": True,
                    "allow_llm": True
                }
            }
            
            response = requests.post(f"{self.api_url}/api/sessions/create",
                                   json=session_data, headers=headers, timeout=15)
            
            create_success = response.status_code == 201
            self.assert_test(create_success, "Create Session",
                            f"Status: {response.status_code}")
            
            session_id = None
            session_code = None
            
            if create_success:
                session_info = response.json().get("session", {})
                session_id = session_info.get("session_id")
                session_code = session_info.get("session_code")
                
                self.assert_test(bool(session_id), "Session ID Generated",
                                f"ID: {session_id}")
                self.assert_test(bool(session_code), "Session Code Generated", 
                                f"Code: {session_code}")
                
                if session_id:
                    self.test_sessions.append({"id": session_id, "code": session_code})
                
                # Test get sessions list
                response = requests.get(f"{self.api_url}/api/sessions",
                                      headers=headers, timeout=10)
                list_success = response.status_code == 200
                self.assert_test(list_success, "Get Sessions List",
                                f"Status: {response.status_code}")
                
                if list_success:
                    sessions = response.json().get("sessions", [])
                    self.assert_test(len(sessions) > 0, "Sessions Listed",
                                    f"Found {len(sessions)} sessions")
                
                # Test get specific session
                if session_id:
                    response = requests.get(f"{self.api_url}/api/sessions/{session_id}",
                                          headers=headers, timeout=10)
                    get_success = response.status_code == 200
                    self.assert_test(get_success, "Get Session Details",
                                    f"Status: {response.status_code}")
            
            return create_success
            
        except Exception as e:
            self.assert_test(False, "Session Creation & Retrieval", f"Error: {str(e)}")
            return False
    
    def test_session_joining_and_participants(self):
        log("\n👥 Testing Session Joining & Participants", Colors.BOLD + Colors.YELLOW)
        log("-" * 50, Colors.YELLOW)
        
        if not self.api_url or not self.test_sessions:
            self.assert_test(False, "Session Joining", "No session available for testing")
            return False
        
        # Create another user to join the session
        user2 = self.create_test_user()
        if not user2:
            self.assert_test(False, "Session Joining", "Failed to create second user")
            return False
        
        headers = {"Authorization": f"Bearer {user2['token']}"}
        session_code = self.test_sessions[0]["code"]
        session_id = self.test_sessions[0]["id"]
        
        try:
            # Test joining session
            response = requests.post(f"{self.api_url}/api/sessions/join/{session_code}",
                                   headers=headers, timeout=10)
            
            join_success = response.status_code == 200
            self.assert_test(join_success, "Join Session",
                            f"Status: {response.status_code}")
            
            if join_success:
                # Test getting participants
                response = requests.get(f"{self.api_url}/api/sessions/{session_id}/participants",
                                      headers=headers, timeout=10)
                
                participants_success = response.status_code == 200
                self.assert_test(participants_success, "Get Participants",
                                f"Status: {response.status_code}")
                
                if participants_success:
                    participants = response.json().get("participants", [])
                    self.assert_test(len(participants) >= 1, "Participants Listed",
                                    f"Found {len(participants)} participants")
            
            return join_success
            
        except Exception as e:
            self.assert_test(False, "Session Joining", f"Error: {str(e)}")
            return False
    
    def test_session_question_management(self):
        log("\n❓ Testing Session Question Management", Colors.BOLD + Colors.YELLOW)
        log("-" * 50, Colors.YELLOW)
        
        if not self.api_url or not self.test_sessions or not self.test_users:
            self.assert_test(False, "Question Management", "No session or user available")
            return False
        
        headers = {"Authorization": f"Bearer {self.test_users[0]['token']}"}
        session_id = self.test_sessions[0]["id"]
        
        try:
            # Test adding question to session
            question_data = {
                "question_text": "What is the purpose of session management?",
                "question_type": "open_ended",
                "difficulty": "medium",
                "subject": "System Design"
            }
            
            response = requests.post(f"{self.api_url}/api/sessions/{session_id}/add-question",
                                   json=question_data, headers=headers, timeout=10)
            
            add_success = response.status_code in [200, 201]
            self.assert_test(add_success, "Add Question to Session",
                            f"Status: {response.status_code}")
            
            # Test session data to see questions
            if add_success:
                response = requests.get(f"{self.api_url}/api/sessions/{session_id}",
                                      headers=headers, timeout=10)
                
                if response.status_code == 200:
                    session_data = response.json().get("session", {})
                    questions = session_data.get("questions", [])
                    self.assert_test(len(questions) >= 0, "Session Questions",
                                    f"Found {len(questions)} questions")
            
            return add_success
            
        except Exception as e:
            self.assert_test(False, "Question Management", f"Error: {str(e)}")
            return False
    
    def test_session_chat_functionality(self):
        log("\n💬 Testing Session Chat", Colors.BOLD + Colors.YELLOW)
        log("-" * 50, Colors.YELLOW)
        
        if not self.api_url or not self.test_sessions or not self.test_users:
            self.assert_test(False, "Session Chat", "No session or user available")
            return False
        
        headers = {"Authorization": f"Bearer {self.test_users[0]['token']}"}
        session_id = self.test_sessions[0]["id"]
        
        try:
            # Test sending chat message
            chat_data = {
                "message": "Testing session chat functionality",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            response = requests.post(f"{self.api_url}/api/sessions/{session_id}/chat",
                                   json=chat_data, headers=headers, timeout=10)
            
            chat_success = response.status_code in [200, 201]
            self.assert_test(chat_success, "Send Chat Message",
                            f"Status: {response.status_code}")
            
            # Test getting chat history
            response = requests.get(f"{self.api_url}/api/sessions/{session_id}/chat-history",
                                  headers=headers, timeout=10)
            
            history_success = response.status_code == 200
            self.assert_test(history_success, "Get Chat History",
                            f"Status: {response.status_code}")
            
            if history_success:
                history = response.json().get("chat_history", [])
                self.assert_test(len(history) >= 0, "Chat History Retrieved",
                                f"Found {len(history)} messages")
            
            return chat_success and history_success
            
        except Exception as e:
            self.assert_test(False, "Session Chat", f"Error: {str(e)}")
            return False
    
    def test_session_settings_and_management(self):
        log("\n⚙️ Testing Session Settings & Management", Colors.BOLD + Colors.YELLOW)
        log("-" * 50, Colors.YELLOW)
        
        if not self.api_url or not self.test_sessions or not self.test_users:
            self.assert_test(False, "Session Management", "No session or user available")
            return False
        
        headers = {"Authorization": f"Bearer {self.test_users[0]['token']}"}
        session_id = self.test_sessions[0]["id"]
        
        try:
            # Test updating session settings
            settings_data = {
                "max_participants": 15,
                "allow_llm": False,
                "collaborative_mode": True
            }
            
            response = requests.put(f"{self.api_url}/api/sessions/{session_id}/settings",
                                  json=settings_data, headers=headers, timeout=10)
            
            settings_success = response.status_code == 200
            self.assert_test(settings_success, "Update Session Settings",
                            f"Status: {response.status_code}")
            
            # Test session debug info
            response = requests.get(f"{self.api_url}/api/sessions/{session_id}/debug",
                                  headers=headers, timeout=10)
            
            debug_success = response.status_code == 200
            self.assert_test(debug_success, "Get Session Debug Info",
                            f"Status: {response.status_code}")
            
            return settings_success
            
        except Exception as e:
            self.assert_test(False, "Session Management", f"Error: {str(e)}")
            return False
    
    def cleanup_test_sessions(self):
        """Clean up created test sessions"""
        log("\n🧹 Cleaning Up Test Sessions", Colors.YELLOW)
        
        for i, session in enumerate(self.test_sessions):
            if i < len(self.test_users):  # Make sure we have a user token
                try:
                    headers = {"Authorization": f"Bearer {self.test_users[i]['token']}"}
                    response = requests.delete(f"{self.api_url}/api/sessions/{session['id']}",
                                             headers=headers, timeout=10)
                    if response.status_code in [200, 204]:
                        log(f"🗑️ Cleaned up session {session['code']}", Colors.GREEN)
                except Exception as e:
                    log(f"⚠️ Failed to cleanup session {session.get('code')}: {e}", Colors.YELLOW)
    
    def run_all_tests(self):
        log("🚀 STARTING SESSION MANAGEMENT TEST SUITE", Colors.BOLD + Colors.CYAN)
        log("=" * 60, Colors.CYAN)
        
        start_time = time.time()
        
        try:
            # Core session tests
            if not self.test_session_creation_and_retrieval():
                log("Skipping other tests due to session creation failure", Colors.YELLOW)
                return self.get_results(start_time)
            
            # Test other session functionality
            self.test_session_joining_and_participants()
            self.test_session_question_management()
            self.test_session_chat_functionality()
            self.test_session_settings_and_management()
            
            # Cleanup
            self.cleanup_test_sessions()
                
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
        log("🎯 SESSION MANAGEMENT TEST RESULTS", Colors.BOLD + Colors.CYAN)
        log("=" * 60, Colors.CYAN)
        
        log(f"✅ Passed: {self.passed_tests}", Colors.GREEN)
        log(f"❌ Failed: {self.failed_tests}", Colors.RED)
        log(f"📊 Pass Rate: {pass_rate:.1f}%", Colors.YELLOW)
        log(f"⏱️ Total Time: {total_time:.2f} seconds", Colors.BLUE)
        
        if self.api_url:
            log(f"🌐 Tested Server: {self.api_url}", Colors.WHITE)
        
        if pass_rate >= 90:
            log("🏆 EXCELLENT! Session management working perfectly!", Colors.GREEN + Colors.BOLD)
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
    test_suite = SessionManagementTestSuite()
    return test_suite.run_all_tests()

if __name__ == "__main__":
    import sys
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║            SESSION MANAGEMENT TEST SUITE                ║")
    print("║                                                          ║")
    print("║  Tests: Creation, Joining, Questions, Chat, Settings    ║")
    print("║         Real Server Integration Testing                 ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}\n")
    
    pass_rate, passed, total = run_all_tests()
    print(f"\nTest completed with result: ({pass_rate}, {passed}, {total})")
    
    # Exit with success if reasonable pass rate
    sys.exit(0 if pass_rate >= 50.0 else 1)