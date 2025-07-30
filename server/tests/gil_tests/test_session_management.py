#!/usr/bin/env python3
"""
Session Management Test Suite
Tests session cleanup, question removal, validation, password protection, and security features

Run with: python test_session_management.py
"""

import requests
import json
import time
import uuid
from datetime import datetime

# Test Configuration
API_URLS = ["http://localhost:5000", "http://localhost:5001"]
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

class SessionManagementTestSuite:
    def __init__(self):
        self.passed_tests = 0
        self.failed_tests = 0
        self.test_user = None
        self.test_sessions = []  # Track sessions for cleanup
        
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
    
    def setup_test_user(self):
        """Create and authenticate a test user"""
        username = f"session_mgmt_test_{uuid.uuid4().hex[:8]}"
        
        try:
            response = requests.post(f"{API_URL}/api/auth/login",
                                   json={"username": username},
                                   timeout=5)
            
            if response.status_code == 200:
                auth_data = response.json()
                token = auth_data.get("token")
                
                self.test_user = {
                    "username": username,
                    "token": token,
                    "headers": {"Authorization": f"Bearer {token}"}
                }
                
                log(f"Created test user: {username}", Colors.BLUE)
                return True
            else:
                log(f"Failed to create test user: {response.status_code}", Colors.RED)
                return False
                
        except Exception as e:
            log(f"Error creating test user: {e}", Colors.RED)
            return False
    
    def create_test_session(self, title_suffix="", password=None):
        """Helper to create a test session"""
        session_data = {
            "title": f"Session Management Test {title_suffix}",
            "subject": "general",
            "description": "Test session for management features",
            "template_mode": True,
            "settings": {
                "max_participants": 10,
                "max_questions": 15,
                "allow_llm": True,
                "allow_user_questions": True
            }
        }
        
        # Add password if provided
        if password:
            session_data["password"] = password
        
        try:
            response = requests.post(f"{API_URL}/api/sessions/create",
                                   json=session_data,
                                   headers=self.test_user["headers"],
                                   timeout=10)
            
            if response.status_code == 201:
                session_info = response.json().get("session", {})
                session_id = session_info.get("session_id")
                self.test_sessions.append(session_id)
                return session_id, session_info
            else:
                log(f"Failed to create session: {response.status_code}", Colors.RED)
                return None, None
                
        except Exception as e:
            log(f"Error creating session: {e}", Colors.RED)
            return None, None
    
    def create_test_question(self, session_id, question_number=1, question_type="open_ended"):
        """Helper to create a test question"""
        try:
            # Start question building
            response = requests.post(f"{API_URL}/api/sessions/{session_id}/questions/{question_number}/start",
                                   json={"type": question_type},
                                   headers=self.test_user["headers"],
                                   timeout=10)
            
            if response.status_code == 200:
                question_info = response.json().get("question", {})
                question_id = question_info.get("question_id")
                
                # Add some content to the question
                content_data = {
                    "field": "question_text",
                    "value": f"Test question {question_number} content"
                }
                
                requests.put(f"{API_URL}/api/sessions/{session_id}/questions/{question_id}/update",
                           json=content_data,
                           headers=self.test_user["headers"],
                           timeout=10)
                
                return question_id, question_info
            else:
                return None, None
                
        except Exception as e:
            log(f"Error creating question: {e}", Colors.RED)
            return None, None
    
    def test_input_validation_and_sanitization(self):
        log("\n🛡️ Testing Input Validation and Sanitization", Colors.BOLD + Colors.YELLOW)
        log("-" * 50, Colors.YELLOW)
        
        if not self.test_user:
            log("No test user available", Colors.RED)
            return False
        
        # Test 1: Session creation with malicious input
        malicious_session_data = {
            "title": "<script>alert('xss')</script>Malicious Title",
            "subject": "javascript'; DROP TABLE sessions; --",
            "description": "<img src=x onerror=alert('xss')>",
            "template_mode": True
        }
        
        try:
            response = requests.post(f"{API_URL}/api/sessions/create",
                                   json=malicious_session_data,
                                   headers=self.test_user["headers"],
                                   timeout=10)
            
            if response.status_code == 201:
                # If malicious input is accepted, check sanitization
                session_info = response.json().get("session", {})
                title = session_info.get("title", "")
                subject = session_info.get("subject", "")
                description = session_info.get("description", "")
                
                # Check that HTML/script tags are properly escaped
                script_escaped = "&lt;script&gt;" in title and "&lt;" in title
                sql_injection_handled = "DROP TABLE" not in subject
                img_tag_escaped = "&lt;img" in description and "onerror" not in description
                
                malicious_input_sanitized = script_escaped and sql_injection_handled and img_tag_escaped
                self.assert_test(malicious_input_sanitized, "Malicious Input Handling", 
                                f"Input accepted and properly sanitized: {response.status_code}")
                
                # Clean up
                session_id = session_info.get("session_id")
                if session_id:
                    self.test_sessions.append(session_id)
                
            elif response.status_code == 400:
                # If malicious input is rejected, that's also good security
                self.assert_test(True, "Malicious Input Handling", 
                                f"Malicious input properly rejected: {response.status_code}")
            else:
                self.assert_test(False, "Malicious Input Handling", 
                                f"Unexpected status: {response.status_code}")
                
        except Exception as e:
            self.assert_test(False, "Input Validation Test", f"Error: {e}")
        
        # Test 2: Invalid session code format
        try:
            response = requests.post(f"{API_URL}/api/sessions/join/INVALID123456789",
                                   headers=self.test_user["headers"],
                                   timeout=5)
            
            # Should handle invalid session codes gracefully
            self.assert_test(response.status_code in [400, 404], "Invalid Session Code Handling",
                            f"Status: {response.status_code}")
            
        except Exception as e:
            self.assert_test(False, "Session Code Validation", f"Error: {e}")
        
        # Test 3: Question content validation
        session_id, _ = self.create_test_session("Validation")
        if session_id:
            question_id, _ = self.create_test_question(session_id, 1, "open_ended")
            if question_id:
                # Test extremely long content
                long_content = "A" * 10000  # Very long string
                
                try:
                    response = requests.put(f"{API_URL}/api/sessions/{session_id}/questions/{question_id}/update",
                                          json={"field": "question_text", "value": long_content},
                                          headers=self.test_user["headers"],
                                          timeout=10)
                    
                    if response.status_code == 200:
                        # Check if content was truncated
                        session_response = requests.get(f"{API_URL}/api/sessions/{session_id}",
                                                      headers=self.test_user["headers"])
                        if session_response.status_code == 200:
                            session_data = session_response.json().get("session", {})
                            questions = (session_data.get("template_data", {}).get("questions_queue", []) + 
                                       session_data.get("template_data", {}).get("ready_questions", []))
                            
                            if questions:
                                content_length = len(questions[0].get("user_content", {}).get("question_text", ""))
                                content_truncated = content_length < len(long_content)
                                self.assert_test(content_truncated, "Content Length Validation",
                                                f"Content truncated to {content_length} chars")
                    
                except Exception as e:
                    self.assert_test(False, "Content Validation", f"Error: {e}")
        
        return True
    
    def test_question_management(self):
        log("\n📝 Testing Question Management", Colors.BOLD + Colors.YELLOW)
        log("-" * 50, Colors.YELLOW)
        
        if not self.test_user:
            log("No test user available", Colors.RED)
            return False
        
        # Create test session
        session_id, session_info = self.create_test_session("Question Management")
        if not session_id:
            self.assert_test(False, "Session Creation for Question Tests", "Failed to create session")
            return False
        
        # Test 1: Create multiple questions
        question_ids = []
        for i in range(1, 4):  # Create 3 questions
            question_id, _ = self.create_test_question(session_id, i, "open_ended")
            if question_id:
                question_ids.append(question_id)
        
        self.assert_test(len(question_ids) == 3, "Multiple Question Creation",
                        f"Created {len(question_ids)} questions")
        
        # Test 2: Update question content
        if question_ids:
            try:
                update_data = {
                    "field": "question_text",
                    "value": "Updated question content with special chars: é, ñ, 中文"
                }
                
                response = requests.put(f"{API_URL}/api/sessions/{session_id}/questions/{question_ids[0]}/update",
                                      json=update_data,
                                      headers=self.test_user["headers"],
                                      timeout=10)
                
                update_success = response.status_code == 200
                self.assert_test(update_success, "Question Content Update",
                                f"Status: {response.status_code}")
                
            except Exception as e:
                self.assert_test(False, "Question Update", f"Error: {e}")
        
        # Test 3: Question finalization
        if question_ids:
            try:
                response = requests.post(f"{API_URL}/api/sessions/{session_id}/questions/{question_ids[0]}/finalize",
                                       headers=self.test_user["headers"],
                                       timeout=10)
                
                finalize_success = response.status_code == 200
                self.assert_test(finalize_success, "Question Finalization",
                                f"Status: {response.status_code}")
                
                if not finalize_success:
                    error_data = response.text
                    log(f"Finalization error: {error_data}", Colors.YELLOW)
                
            except Exception as e:
                self.assert_test(False, "Question Finalization", f"Error: {e}")
        
        # Test 4: Individual question removal
        if len(question_ids) >= 2:
            try:
                response = requests.delete(f"{API_URL}/api/sessions/{session_id}/questions/{question_ids[1]}",
                                         headers=self.test_user["headers"],
                                         timeout=10)
                
                removal_success = response.status_code == 200
                self.assert_test(removal_success, "Individual Question Removal",
                                f"Status: {response.status_code}")
                
                # Verify question was removed
                session_response = requests.get(f"{API_URL}/api/sessions/{session_id}",
                                              headers=self.test_user["headers"])
                if session_response.status_code == 200:
                    session_data = session_response.json().get("session", {})
                    all_questions = (session_data.get("template_data", {}).get("questions_queue", []) + 
                                   session_data.get("template_data", {}).get("ready_questions", []))
                    
                    question_removed = not any(q.get("question_id") == question_ids[1] for q in all_questions)
                    self.assert_test(question_removed, "Question Removal Verification",
                                    f"Question {question_ids[1][:8]}... removed")
                
            except Exception as e:
                self.assert_test(False, "Question Removal", f"Error: {e}")
        
        return True
    
    def test_session_cleanup_operations(self):
        log("\n🗑️ Testing Session Cleanup Operations", Colors.BOLD + Colors.YELLOW)
        log("-" * 50, Colors.YELLOW)
        
        if not self.test_user:
            log("No test user available", Colors.RED)
            return False
        
        # Test 1: Clear all questions from session
        session_id, _ = self.create_test_session("Cleanup Test")
        if session_id:
            # Add some questions first
            for i in range(1, 4):
                self.create_test_question(session_id, i, "open_ended")
            
            try:
                response = requests.delete(f"{API_URL}/api/sessions/{session_id}/questions/clear",
                                         headers=self.test_user["headers"],
                                         timeout=10)
                
                clear_success = response.status_code == 200
                self.assert_test(clear_success, "Clear All Questions",
                                f"Status: {response.status_code}")
                
                # Verify all questions were cleared
                if clear_success:
                    session_response = requests.get(f"{API_URL}/api/sessions/{session_id}",
                                                  headers=self.test_user["headers"])
                    if session_response.status_code == 200:
                        session_data = session_response.json().get("session", {})
                        questions_queue = session_data.get("template_data", {}).get("questions_queue", [])
                        ready_questions = session_data.get("template_data", {}).get("ready_questions", [])
                        
                        all_cleared = len(questions_queue) == 0 and len(ready_questions) == 0
                        self.assert_test(all_cleared, "Questions Cleared Verification",
                                        f"Queue: {len(questions_queue)}, Ready: {len(ready_questions)}")
                
            except Exception as e:
                self.assert_test(False, "Clear All Questions", f"Error: {e}")
        
        # Test 2: Session reset
        session_id2, _ = self.create_test_session("Reset Test")
        if session_id2:
            # Add content to session
            self.create_test_question(session_id2, 1, "multiple_choice")
            
            try:
                response = requests.post(f"{API_URL}/api/sessions/{session_id2}/reset",
                                       headers=self.test_user["headers"],
                                       timeout=10)
                
                reset_success = response.status_code == 200
                self.assert_test(reset_success, "Session Reset",
                                f"Status: {response.status_code}")
                
                # Verify session was reset
                if reset_success:
                    session_response = requests.get(f"{API_URL}/api/sessions/{session_id2}",
                                                  headers=self.test_user["headers"])
                    if session_response.status_code == 200:
                        session_data = session_response.json().get("session", {})
                        template_data = session_data.get("template_data", {})
                        
                        questions_empty = len(template_data.get("questions_queue", [])) == 0
                        ready_empty = len(template_data.get("ready_questions", [])) == 0
                        counter_reset = template_data.get("current_question_number", -1) == 0
                        
                        reset_complete = questions_empty and ready_empty and counter_reset
                        self.assert_test(reset_complete, "Session Reset Verification",
                                        "Session returned to fresh state")
                
            except Exception as e:
                self.assert_test(False, "Session Reset", f"Error: {e}")
        
        # Test 3: Individual session deletion
        session_id3, session_info = self.create_test_session("Delete Test")
        if session_id3:
            try:
                response = requests.delete(f"{API_URL}/api/sessions/{session_id3}",
                                         headers=self.test_user["headers"],
                                         timeout=10)
                
                delete_success = response.status_code == 200
                self.assert_test(delete_success, "Individual Session Deletion",
                                f"Status: {response.status_code}")
                
                # Verify session was deleted - should get 404 now
                if delete_success:
                    verify_response = requests.get(f"{API_URL}/api/sessions/{session_id3}",
                                                 headers=self.test_user["headers"])
                    session_deleted = verify_response.status_code == 404
                    self.assert_test(session_deleted, "Session Deletion Verification",
                                    f"Session no longer accessible (404)")
                    
                    # Remove from our tracking list since it's deleted
                    if session_id3 in self.test_sessions:
                        self.test_sessions.remove(session_id3)
                
            except Exception as e:
                self.assert_test(False, "Session Deletion", f"Error: {e}")
        
        return True
    
    def test_user_session_cleanup(self):
        log("\n🧹 Testing User Session Cleanup", Colors.BOLD + Colors.YELLOW)
        log("-" * 50, Colors.YELLOW)
        
        if not self.test_user:
            log("No test user available", Colors.RED)
            return False
        
        # Create multiple sessions for cleanup test
        session_ids = []
        for i in range(3):
            session_id, _ = self.create_test_session(f"Cleanup {i+1}")
            if session_id:
                session_ids.append(session_id)
        
        self.assert_test(len(session_ids) >= 2, "Multiple Sessions Created",
                        f"Created {len(session_ids)} sessions for cleanup test")
        
        # Test cleanup all user sessions
        try:
            response = requests.delete(f"{API_URL}/api/sessions/cleanup-user",
                                     headers=self.test_user["headers"],
                                     timeout=15)
            
            cleanup_success = response.status_code == 200
            
            if cleanup_success:
                cleanup_data = response.json()
                deleted_count = cleanup_data.get("deleted_sessions", 0)
                
                self.assert_test(deleted_count >= len(session_ids), "User Sessions Cleanup",
                                f"Deleted {deleted_count} sessions")
                
                # Verify sessions are no longer accessible
                if session_ids:
                    deleted_verified = 0
                    for sid in session_ids[:2]:  # Check first 2
                        verify_response = requests.get(f"{API_URL}/api/sessions/{sid}",
                                                     headers=self.test_user["headers"])
                        if verify_response.status_code == 404:
                            deleted_verified += 1
                    
                    self.assert_test(deleted_verified >= 1, "Cleanup Verification",
                                    f"{deleted_verified} sessions confirmed deleted")
                
                # Clear our tracking list since all sessions are deleted
                self.test_sessions.clear()
                
            else:
                self.assert_test(False, "User Sessions Cleanup",
                                f"Status: {response.status_code}")
                
        except Exception as e:
            self.assert_test(False, "User Sessions Cleanup", f"Error: {e}")
        
        return cleanup_success
    
    def test_permissions_and_security(self):
        log("\n🔒 Testing Permissions and Security", Colors.BOLD + Colors.YELLOW)
        log("-" * 50, Colors.YELLOW)
        
        if not self.test_user:
            log("No test user available", Colors.RED)
            return False
        
        # Create a session as host
        session_id, _ = self.create_test_session("Security Test")
        if not session_id:
            return False
        
        # Create another user to test non-host permissions
        guest_username = f"guest_user_{uuid.uuid4().hex[:6]}"
        try:
            response = requests.post(f"{API_URL}/api/auth/login",
                                   json={"username": guest_username},
                                   timeout=5)
            
            if response.status_code == 200:
                guest_token = response.json().get("token")
                guest_headers = {"Authorization": f"Bearer {guest_token}"}
                
                # Test 1: Non-host cannot delete session
                response = requests.delete(f"{API_URL}/api/sessions/{session_id}",
                                         headers=guest_headers,
                                         timeout=10)
                
                delete_blocked = response.status_code == 403
                self.assert_test(delete_blocked, "Non-host Session Deletion Blocked",
                                f"Status: {response.status_code}")
                
                # Test 2: Non-host cannot clear questions
                response = requests.delete(f"{API_URL}/api/sessions/{session_id}/questions/clear",
                                         headers=guest_headers,
                                         timeout=10)
                
                clear_blocked = response.status_code == 403
                self.assert_test(clear_blocked, "Non-host Question Clear Blocked",
                                f"Status: {response.status_code}")
                
                # Test 3: Non-host cannot reset session
                response = requests.post(f"{API_URL}/api/sessions/{session_id}/reset",
                                       headers=guest_headers,
                                       timeout=10)
                
                reset_blocked = response.status_code == 403
                self.assert_test(reset_blocked, "Non-host Session Reset Blocked",
                                f"Status: {response.status_code}")
                
                # Test 4: Invalid token access
                invalid_headers = {"Authorization": "Bearer invalid_token_123"}
                response = requests.get(f"{API_URL}/api/sessions/{session_id}",
                                      headers=invalid_headers,
                                      timeout=5)
                
                invalid_token_blocked = response.status_code in [401, 403]
                self.assert_test(invalid_token_blocked, "Invalid Token Blocked",
                                f"Status: {response.status_code}")
                
            else:
                self.assert_test(False, "Guest User Creation", "Failed to create guest user")
                
        except Exception as e:
            self.assert_test(False, "Security Tests", f"Error: {e}")
        
        return True
    
    def test_debug_functionality(self):
        log("\n🐛 Testing Debug Functionality", Colors.BOLD + Colors.YELLOW)
        log("-" * 50, Colors.YELLOW)
        
        if not self.test_user:
            log("No test user available", Colors.RED)
            return False
        
        # Create session with questions for debug testing
        session_id, _ = self.create_test_session("Debug Test")
        if session_id:
            # Add questions in different states
            question_id1, _ = self.create_test_question(session_id, 1, "open_ended")
            question_id2, _ = self.create_test_question(session_id, 2, "multiple_choice")
            
            # Finalize one question
            if question_id1:
                requests.post(f"{API_URL}/api/sessions/{session_id}/questions/{question_id1}/finalize",
                            headers=self.test_user["headers"],
                            timeout=10)
            
            # Test debug endpoint
            try:
                response = requests.get(f"{API_URL}/api/sessions/{session_id}/debug",
                                      headers=self.test_user["headers"],
                                      timeout=10)
                
                debug_success = response.status_code == 200
                
                if debug_success:
                    debug_data = response.json().get("debug", {})
                    
                    # Check debug information completeness
                    has_session_id = "session_id" in debug_data
                    has_queue_info = "questions_in_queue" in debug_data
                    has_ready_info = "questions_ready" in debug_data
                    has_question_ids = "queue_question_ids" in debug_data
                    has_details = "queue_details" in debug_data
                    
                    debug_complete = all([has_session_id, has_queue_info, has_ready_info, 
                                        has_question_ids, has_details])
                    
                    self.assert_test(debug_complete, "Debug Endpoint Completeness",
                                    f"All debug fields present: {debug_complete}")
                    
                    # Check data accuracy
                    total_questions = debug_data.get("questions_in_queue", 0) + debug_data.get("questions_ready", 0)
                    self.assert_test(total_questions >= 1, "Debug Data Accuracy",
                                    f"Found {total_questions} total questions")
                    
                else:
                    self.assert_test(False, "Debug Endpoint Access",
                                    f"Status: {response.status_code}")
                
            except Exception as e:
                self.assert_test(False, "Debug Functionality", f"Error: {e}")
        
        return True
    
    def test_password_protection(self):
        """Test session password protection functionality"""
        log("\n🔐 Testing Session Password Protection", Colors.BOLD + Colors.YELLOW)
        log("-" * 50, Colors.YELLOW)
        
        if not self.test_user:
            log("No test user available", Colors.RED)
            return False
        
        # Test 1: Create password-protected session
        test_password = "test_password_123"
        session_id, session_info = self.create_test_session("Password Protected", test_password)
        
        self.assert_test(session_id is not None, "Password-Protected Session Creation",
                        f"Session created with password protection")
        
        if not session_id:
            return False
        
        # Test 2: Verify session shows as password protected
        session_code = session_info.get("session_code")
        if session_code:
            try:
                response = requests.get(f"{API_URL}/api/sessions/{session_id}",
                                      headers=self.test_user["headers"],
                                      timeout=10)
                
                if response.status_code == 200:
                    session_data = response.json().get("session", {})
                    is_password_protected = session_data.get("is_password_protected", False)
                    
                    self.assert_test(is_password_protected, "Password Protection Flag",
                                    f"Session marked as password protected: {is_password_protected}")
                    
                    # Verify password hash is not exposed
                    password_not_exposed = "password" not in session_data
                    password_hash_not_exposed = "password_hash" not in session_data
                    
                    # Also check that the actual test password is not in any field values
                    test_password_not_exposed = True
                    for key, value in session_data.items():
                        if isinstance(value, str) and test_password in value:
                            test_password_not_exposed = False
                            break
                    
                    password_security_good = password_not_exposed and password_hash_not_exposed and test_password_not_exposed
                    self.assert_test(password_security_good, "Password Hash Security",
                                    f"Password data not exposed: password={password_not_exposed}, hash={password_hash_not_exposed}, plaintext={test_password_not_exposed}")
                
            except Exception as e:
                self.assert_test(False, "Session Data Verification", f"Error: {e}")
        
        # Test 3: Create guest user to test password access
        guest_username = f"password_test_guest_{uuid.uuid4().hex[:6]}"
        try:
            response = requests.post(f"{API_URL}/api/auth/login",
                                   json={"username": guest_username},
                                   timeout=5)
            
            if response.status_code == 200:
                guest_token = response.json().get("token")
                guest_headers = {"Authorization": f"Bearer {guest_token}"}
                
                # Test 4: Join without password should fail
                response = requests.post(f"{API_URL}/api/sessions/join/{session_code}",
                                       json={},
                                       headers=guest_headers,
                                       timeout=10)
                
                join_blocked = response.status_code == 401
                self.assert_test(join_blocked, "Password Required Check",
                                f"Join without password blocked: {response.status_code}")
                
                if join_blocked:
                    error_data = response.json()
                    password_error = "password" in error_data.get("error", "").lower()
                    self.assert_test(password_error, "Password Error Message",
                                    "Error message indicates password required")
                
                # Test 5: Join with wrong password should fail
                response = requests.post(f"{API_URL}/api/sessions/join/{session_code}",
                                       json={"password": "wrong_password"},
                                       headers=guest_headers,
                                       timeout=10)
                
                wrong_password_blocked = response.status_code == 401
                self.assert_test(wrong_password_blocked, "Wrong Password Blocked",
                                f"Wrong password blocked: {response.status_code}")
                
                # Test 6: Join with correct password should succeed
                response = requests.post(f"{API_URL}/api/sessions/join/{session_code}",
                                       json={"password": test_password},
                                       headers=guest_headers,
                                       timeout=10)
                
                correct_password_success = response.status_code == 200
                self.assert_test(correct_password_success, "Correct Password Access",
                                f"Correct password allows access: {response.status_code}")
                
                if correct_password_success:
                    join_data = response.json()
                    session_returned = "session" in join_data
                    self.assert_test(session_returned, "Session Data Returned",
                                    "Session data provided after successful password verification")
                
            else:
                self.assert_test(False, "Guest User Creation", "Failed to create guest user for password testing")
                
        except Exception as e:
            self.assert_test(False, "Password Protection Tests", f"Error: {e}")
        
        # Test 7: Password validation edge cases
        # Test empty password
        try:
            response = requests.post(f"{API_URL}/api/sessions/join/{session_code}",
                                   json={"password": ""},
                                   headers=guest_headers,
                                   timeout=10)
            
            empty_password_blocked = response.status_code == 401
            self.assert_test(empty_password_blocked, "Empty Password Blocked",
                            f"Empty password blocked: {response.status_code}")
            
        except Exception as e:
            self.assert_test(False, "Empty Password Test", f"Error: {e}")
        
        # Test 8: Password with special characters
        special_password = "test@#$%^&*()_+-={}[]|\\:;\"'<>?,./"
        session_id_special, session_info_special = self.create_test_session("Special Chars", special_password)
        
        if session_id_special:
            session_code_special = session_info_special.get("session_code")
            try:
                response = requests.post(f"{API_URL}/api/sessions/join/{session_code_special}",
                                       json={"password": special_password},
                                       headers=guest_headers,
                                       timeout=10)
                
                special_chars_success = response.status_code == 200
                self.assert_test(special_chars_success, "Special Characters Password",
                                f"Special characters in password work: {response.status_code}")
                
            except Exception as e:
                self.assert_test(False, "Special Characters Test", f"Error: {e}")
        
        # Test 9: Long password handling
        long_password = "a" * 49  # Just under the 50 character limit
        session_id_long, session_info_long = self.create_test_session("Long Password", long_password)
        
        if session_id_long:
            session_code_long = session_info_long.get("session_code")
            try:
                response = requests.post(f"{API_URL}/api/sessions/join/{session_code_long}",
                                       json={"password": long_password},
                                       headers=guest_headers,
                                       timeout=10)
                
                long_password_success = response.status_code == 200
                self.assert_test(long_password_success, "Long Password Support",
                                f"Long password (49 chars) works: {response.status_code}")
                
            except Exception as e:
                self.assert_test(False, "Long Password Test", f"Error: {e}")
        
        # Test 10: Non-password protected session still works
        session_id_public, session_info_public = self.create_test_session("Public Session")
        
        if session_id_public:
            session_code_public = session_info_public.get("session_code")
            try:
                response = requests.post(f"{API_URL}/api/sessions/join/{session_code_public}",
                                       json={},
                                       headers=guest_headers,
                                       timeout=10)
                
                public_access_success = response.status_code == 200
                self.assert_test(public_access_success, "Public Session Access",
                                f"Public session accessible without password: {response.status_code}")
                
                if public_access_success:
                    session_data = response.json().get("session", {})
                    not_password_protected = not session_data.get("is_password_protected", True)
                    self.assert_test(not_password_protected, "Public Session Flag",
                                    "Public session not marked as password protected")
                
            except Exception as e:
                self.assert_test(False, "Public Session Test", f"Error: {e}")
        
        return True
    
    def cleanup_test_data(self):
        """Clean up any remaining test sessions"""
        log("\n🧽 Cleaning up test data", Colors.BLUE)
        
        if self.test_user and self.test_sessions:
            for session_id in self.test_sessions[:]:  # Copy list to avoid modification during iteration
                try:
                    requests.delete(f"{API_URL}/api/sessions/{session_id}",
                                  headers=self.test_user["headers"],
                                  timeout=5)
                    log(f"Cleaned up session: {session_id[:8]}...", Colors.WHITE)
                except:
                    pass  # Ignore cleanup errors
        
        # Final cleanup - delete all user sessions
        if self.test_user:
            try:
                requests.delete(f"{API_URL}/api/sessions/cleanup-user",
                              headers=self.test_user["headers"],
                              timeout=10)
                log("Final cleanup completed", Colors.WHITE)
            except:
                pass
    
    def run_all_tests(self):
        log("🚀 STARTING SESSION MANAGEMENT TEST SUITE", Colors.BOLD + Colors.CYAN)
        log("=" * 70, Colors.CYAN)
        
        start_time = time.time()
        
        try:
            # Setup
            if not self.setup_test_user():
                log("Failed to setup test user. Aborting tests.", Colors.RED)
                return
            
            # Run test categories
            self.test_input_validation_and_sanitization()
            self.test_question_management()
            self.test_session_cleanup_operations()
            self.test_user_session_cleanup()
            self.test_permissions_and_security()
            self.test_password_protection()
            self.test_debug_functionality()
            
        except Exception as e:
            log(f"Test suite crashed: {e}", Colors.RED)
            import traceback
            traceback.print_exc()
        
        finally:
            # Always try to cleanup
            self.cleanup_test_data()
        
        # Print results
        total_time = time.time() - start_time
        total_tests = self.passed_tests + self.failed_tests
        pass_rate = (self.passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        log("\n" + "=" * 70, Colors.CYAN)
        log("🎯 SESSION MANAGEMENT TEST RESULTS", Colors.BOLD + Colors.CYAN)
        log("=" * 70, Colors.CYAN)
        
        log(f"✅ Passed: {self.passed_tests}", Colors.GREEN)
        log(f"❌ Failed: {self.failed_tests}", Colors.RED)
        log(f"📊 Pass Rate: {pass_rate:.1f}%", Colors.YELLOW)
        log(f"⏱️ Total Time: {total_time:.2f} seconds", Colors.BLUE)
        log(f"🌐 Server URL: {API_URL}", Colors.MAGENTA)
        
        if pass_rate >= 90:
            log("🏆 EXCELLENT! Session management is working perfectly!", Colors.GREEN + Colors.BOLD)
        elif pass_rate >= 75:
            log("✨ GOOD! Minor issues to address", Colors.YELLOW + Colors.BOLD)
        elif pass_rate >= 50:
            log("⚠️ FAIR! Several issues need attention", Colors.YELLOW + Colors.BOLD)
        else:
            log("🚨 POOR! Major issues need immediate attention", Colors.RED + Colors.BOLD)

if __name__ == "__main__":
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║                   SESSION MANAGEMENT TEST SUITE                  ║")
    print("║                                                                  ║")
    print("║  Tests: Validation, Questions, Cleanup, Security, Passwords     ║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}\n")
    
    # Find running server
    if find_running_server():
        test_suite = SessionManagementTestSuite()
        test_suite.run_all_tests()
    else:
        log("❌ No server found. Please start the server first.", Colors.RED)
        log("💡 Try: docker-compose up --build", Colors.BLUE)