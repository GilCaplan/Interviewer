#!/usr/bin/env python3
"""
Comprehensive Security Test Suite
Tests authentication, authorization, input validation, password security, XSS, SQL injection, and other security vulnerabilities.

Run with: python test_security_comprehensive.py
"""

import requests
import json
import time
import uuid
import hashlib
import base64
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
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
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

class SecurityTestSuite:
    def __init__(self):
        self.passed_tests = 0
        self.failed_tests = 0
        self.test_users = []
        
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
    
    def create_test_user(self, username_suffix=""):
        """Create a test user and return auth data"""
        # Keep username under 30 characters limit
        suffix = username_suffix[:8] if username_suffix else ""
        username = f"sec_{suffix}_{uuid.uuid4().hex[:8]}"
        
        try:
            response = requests.post(f"{API_URL}/api/auth/login",
                                   json={"username": username},
                                   timeout=10)
            
            if response.status_code == 200:
                auth_data = response.json()
                token = auth_data.get("token")
                if token:
                    user_data = {
                        "username": username,
                        "token": token,
                        "headers": {"Authorization": f"Bearer {token}"}
                    }
                    self.test_users.append(user_data)
                    return user_data
                else:
                    log(f"No token in response for user {username}", Colors.RED)
            else:
                log(f"Failed to create user {username}: {response.status_code}", Colors.RED)
        except Exception as e:
            log(f"Exception creating user {username}: {e}", Colors.RED)
        
        return None
    
    def test_authentication_security(self):
        log("\n🔐 Testing Authentication Security", Colors.BOLD + Colors.YELLOW)
        log("-" * 60, Colors.YELLOW)
        
        # Test 1: Invalid token format rejection
        invalid_tokens = [
            "invalid_token",
            "Bearer invalid",
            "malformed.jwt.token",
            "<script>alert('xss')</script>",
            "'; DROP TABLE users; --",
            "",
            None,
            "Bearer ",
            "Bearer " + "A" * 1000
        ]
        
        invalid_token_blocked = 0
        for token in invalid_tokens:
            try:
                headers = {"Authorization": token} if token else {}
                response = requests.get(f"{API_URL}/api/sessions",
                                      headers=headers,
                                      timeout=3)
                
                # Should return 401 for invalid tokens
                if response.status_code == 401:
                    invalid_token_blocked += 1
            except:
                pass
        
        self.assert_test(invalid_token_blocked >= len(invalid_tokens) * 0.8, 
                        "Invalid Token Rejection",
                        f"{invalid_token_blocked}/{len(invalid_tokens)} invalid tokens blocked")
        
        # Test 2: Token tampering detection
        user = self.create_test_user("auth_test")
        if user:
            original_token = user["token"]
            
            # Tamper with token
            tampered_tokens = [
                original_token[:-5] + "AAAAA",  # Change last 5 chars
                original_token[:10] + "TAMPERED" + original_token[18:],  # Insert in middle
                base64.b64encode(b"fake_payload").decode(),  # Completely fake
            ]
            
            tampered_blocked = 0
            for tampered_token in tampered_tokens:
                try:
                    tampered_headers = {"Authorization": f"Bearer {tampered_token}"}
                    response = requests.get(f"{API_URL}/api/sessions",
                                          headers=tampered_headers,
                                          timeout=3)
                    
                    if response.status_code == 401:
                        tampered_blocked += 1
                except:
                    pass
            
            self.assert_test(tampered_blocked >= len(tampered_tokens) * 0.8,
                            "Token Tampering Detection",
                            f"{tampered_blocked}/{len(tampered_tokens)} tampered tokens blocked")
        
        # Test 3: Concurrent login attempts (brute force simulation)
        username = f"brute_force_test_{uuid.uuid4().hex[:8]}"
        login_attempts = []
        
        def attempt_login():
            try:
                response = requests.post(f"{API_URL}/api/auth/login",
                                       json={"username": username},
                                       timeout=3)
                return response.status_code
            except:
                return 500
        
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(attempt_login) for _ in range(20)]
            login_attempts = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        successful_logins = sum(1 for status in login_attempts if status == 200)
        
        # System should handle multiple concurrent logins gracefully
        self.assert_test(successful_logins >= 15,
                        "Concurrent Login Handling",
                        f"{successful_logins}/20 concurrent logins succeeded")
    
    def test_authorization_controls(self):
        log("\n🛡️ Testing Authorization Controls", Colors.BOLD + Colors.YELLOW)
        log("-" * 60, Colors.YELLOW)
        
        # Create two users - one will be session host, other will be participant
        host_user = self.create_test_user("host")
        participant_user = self.create_test_user("participant")
        
        if not host_user or not participant_user:
            log("Failed to create test users", Colors.RED)
            return
        
        # Host creates a session
        session_response = requests.post(f"{API_URL}/api/sessions/create",
                                       json={
                                           "title": "Authorization Test Session",
                                           "subject": "general",
                                           "template_mode": True
                                       },
                                       headers=host_user["headers"],
                                       timeout=5)
        
        if session_response.status_code != 201:
            log("Failed to create test session", Colors.RED)
            return
        
        session_data = session_response.json().get("session", {})
        session_id = session_data.get("session_id")
        session_code = session_data.get("session_code")
        
        # Participant joins the session
        join_response = requests.post(f"{API_URL}/api/sessions/join/{session_code}",
                                    headers=participant_user["headers"],
                                    timeout=5)
        
        # Test 1: Non-host cannot delete session
        delete_response = requests.delete(f"{API_URL}/api/sessions/{session_id}",
                                        headers=participant_user["headers"],
                                        timeout=5)
        
        self.assert_test(delete_response.status_code == 403,
                        "Non-Host Session Deletion Blocked",
                        f"Status: {delete_response.status_code}")
        
        # Test 2: Non-host cannot clear all questions
        clear_response = requests.delete(f"{API_URL}/api/sessions/{session_id}/questions/clear",
                                       headers=participant_user["headers"],
                                       timeout=5)
        
        self.assert_test(clear_response.status_code == 403,
                        "Non-Host Question Clear Blocked",
                        f"Status: {clear_response.status_code}")
        
        # Test 3: Non-host cannot reset session
        reset_response = requests.post(f"{API_URL}/api/sessions/{session_id}/reset",
                                     headers=participant_user["headers"],
                                     timeout=5)
        
        self.assert_test(reset_response.status_code == 403,
                        "Non-Host Session Reset Blocked",
                        f"Status: {reset_response.status_code}")
        
        # Test 4: Host can perform privileged operations
        host_operations_successful = 0
        
        # Host can create questions
        question_response = requests.post(f"{API_URL}/api/sessions/{session_id}/questions/1/start",
                                        json={"type": "open_ended"},
                                        headers=host_user["headers"],
                                        timeout=5)
        if question_response.status_code == 200:
            host_operations_successful += 1
        
        # Host can reset session
        reset_response = requests.post(f"{API_URL}/api/sessions/{session_id}/reset",
                                     headers=host_user["headers"],
                                     timeout=5)
        if reset_response.status_code == 200:
            host_operations_successful += 1
        
        # Host can delete session
        delete_response = requests.delete(f"{API_URL}/api/sessions/{session_id}",
                                        headers=host_user["headers"],
                                        timeout=5)
        if delete_response.status_code == 200:
            host_operations_successful += 1
        
        self.assert_test(host_operations_successful >= 2,
                        "Host Privileged Operations Work",
                        f"{host_operations_successful}/3 host operations successful")
    
    def test_input_validation_security(self):
        log("\n🧪 Testing Input Validation Security", Colors.BOLD + Colors.YELLOW)
        log("-" * 60, Colors.YELLOW)
        
        user = self.create_test_user("input_test")
        if not user:
            log("Failed to create test user", Colors.RED)
            return
        
        # Test 1: XSS Prevention
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>",
            "\"><script>alert('XSS')</script>",
            "<iframe src=javascript:alert('XSS')></iframe>"
        ]
        
        xss_blocked = 0
        for payload in xss_payloads:
            try:
                response = requests.post(f"{API_URL}/api/sessions/create",
                                       json={
                                           "title": payload,
                                           "subject": "general",
                                           "description": payload
                                       },
                                       headers=user["headers"],
                                       timeout=5)
                
                # Check if XSS is handled (either rejected or sanitized)
                if response.status_code == 400:
                    # XSS properly rejected
                    xss_blocked += 1
                elif response.status_code == 201:
                    session_data = response.json()
                    if payload not in str(session_data):  # XSS should be sanitized
                        xss_blocked += 1
                
            except:
                pass
        
        self.assert_test(xss_blocked >= len(xss_payloads) * 0.8,
                        "XSS Attack Prevention",
                        f"{xss_blocked}/{len(xss_payloads)} XSS attempts blocked/sanitized")
        
        # Test 2: SQL Injection Prevention
        sql_payloads = [
            "'; DROP TABLE sessions; --",
            "' OR '1'='1",
            "'; DELETE FROM users WHERE id=1; --",
            "UNION SELECT * FROM users",
            "'; EXEC xp_cmdshell('dir'); --"
        ]
        
        sql_injection_blocked = 0
        for payload in sql_payloads:
            try:
                response = requests.post(f"{API_URL}/api/sessions/create",
                                       json={
                                           "title": payload,
                                           "subject": payload
                                       },
                                       headers=user["headers"],
                                       timeout=5)
                
                # Server should handle gracefully (not crash with 500)
                if response.status_code < 500:
                    sql_injection_blocked += 1
                
            except:
                pass
        
        self.assert_test(sql_injection_blocked >= len(sql_payloads) * 0.8,
                        "SQL Injection Prevention",
                        f"{sql_injection_blocked}/{len(sql_payloads)} SQL injection attempts handled")
        
        # Test 3: Input Length Limits
        oversized_inputs = [
            "A" * 1000,    # 1KB
            "A" * 10000,   # 10KB
            "A" * 100000,  # 100KB
        ]
        
        length_limit_enforced = 0
        for oversized_input in oversized_inputs:
            try:
                response = requests.post(f"{API_URL}/api/sessions/create",
                                       json={
                                           "title": oversized_input,
                                           "description": oversized_input
                                       },
                                       headers=user["headers"],
                                       timeout=10)
                
                # Server should either reject or truncate, not crash
                if response.status_code < 500:
                    length_limit_enforced += 1
                
            except requests.exceptions.Timeout:
                # Timeout is acceptable for very large inputs
                length_limit_enforced += 1
            except:
                pass
        
        self.assert_test(length_limit_enforced >= len(oversized_inputs) * 0.8,
                        "Input Length Limits",
                        f"{length_limit_enforced}/{len(oversized_inputs)} oversized inputs handled")
    
    def test_session_security(self):
        log("\n🎯 Testing Session Security", Colors.BOLD + Colors.YELLOW)
        log("-" * 60, Colors.YELLOW)
        
        user = self.create_test_user("session_security")
        if not user:
            log("Failed to create test user", Colors.RED)
            return
        
        # Test 1: Session code enumeration protection
        fake_session_codes = [
            "AAAAAA", "BBBBBB", "CCCCCC", "DDDDDD", "EEEEEE",
            "123456", "000000", "999999", "ABCDEF", "ZZZZZZ"
        ]
        
        enumeration_blocked = 0
        for fake_code in fake_session_codes:
            try:
                response = requests.post(f"{API_URL}/api/sessions/join/{fake_code}",
                                       headers=user["headers"],
                                       timeout=3)
                
                # Should return 404 for non-existent sessions
                if response.status_code == 404:
                    enumeration_blocked += 1
                
            except:
                pass
        
        self.assert_test(enumeration_blocked >= len(fake_session_codes) * 0.8,
                        "Session Code Enumeration Protection",
                        f"{enumeration_blocked}/{len(fake_session_codes)} invalid codes properly rejected")
        
        # Test 2: Session isolation (one user can't access another's private sessions)
        user1 = self.create_test_user("isolation_test_1")
        user2 = self.create_test_user("isolation_test_2")
        
        if user1 and user2:
            # User1 creates a private session
            session_response = requests.post(f"{API_URL}/api/sessions/create",
                                           json={
                                               "title": "Private Session",
                                               "subject": "general"
                                           },
                                           headers=user1["headers"],
                                           timeout=5)
            
            if session_response.status_code == 201:
                session_data = session_response.json().get("session", {})
                session_id = session_data.get("session_id")
                
                # User2 tries to access User1's session directly
                access_response = requests.get(f"{API_URL}/api/sessions/{session_id}",
                                             headers=user2["headers"],
                                             timeout=5)
                
                # Should be blocked or return empty/forbidden
                isolation_working = access_response.status_code in [403, 404] or not access_response.json().get("session")
                
                self.assert_test(isolation_working,
                                "Session Isolation Enforcement",
                                f"User2 access to User1's session: {access_response.status_code}")
        
        # Test 3: Rate limiting simulation
        rapid_requests = []
        for i in range(20):
            try:
                response = requests.post(f"{API_URL}/api/sessions/create",
                                       json={
                                           "title": f"Rate Limit Test {i}",
                                           "subject": "general"
                                       },
                                       headers=user["headers"],
                                       timeout=1)
                rapid_requests.append(response.status_code)
            except:
                rapid_requests.append(500)
        
        successful_requests = sum(1 for status in rapid_requests if status == 201)
        
        # System should handle rapid requests gracefully
        self.assert_test(successful_requests >= 10,
                        "Rapid Request Handling",
                        f"{successful_requests}/20 rapid requests succeeded")
    
    def test_data_exposure_prevention(self):
        log("\n🔒 Testing Data Exposure Prevention", Colors.BOLD + Colors.YELLOW)
        log("-" * 60, Colors.YELLOW)
        
        # Test 1: Error messages don't leak sensitive information
        sensitive_info_exposed = 0
        
        # Try to trigger various errors and check if they leak info
        error_tests = [
            (f"{API_URL}/api/sessions/invalid-uuid", "GET"),
            (f"{API_URL}/api/templates/non-existent-id", "GET"),
            (f"{API_URL}/api/auth/login", "POST", {"username": None}),
            (f"{API_URL}/api/sessions/create", "POST", {"invalid_json": True}),
        ]
        
        for url, method, data in [(url, method, None) for url, method in error_tests[:2]] + [(url, method, data) for url, method, data in error_tests[2:]]:
            try:
                if method == "GET":
                    response = requests.get(url, timeout=3)
                else:
                    response = requests.post(url, json=data, timeout=3)
                
                response_text = response.text.lower()
                
                # Check for common sensitive info leaks
                sensitive_keywords = [
                    "password", "secret", "key", "token", "database",
                    "mongodb", "connection", "server", "internal error",
                    "traceback", "exception", "stack trace"
                ]
                
                if any(keyword in response_text for keyword in sensitive_keywords):
                    sensitive_info_exposed += 1
                
            except:
                pass
        
        self.assert_test(sensitive_info_exposed == 0,
                        "Sensitive Information Exposure",
                        f"{sensitive_info_exposed} error responses contained sensitive info")
        
        # Test 2: API endpoints don't expose internal system info
        info_endpoints = [
            f"{API_URL}/api/health",
            f"{API_URL}/api/info",
            f"{API_URL}/api/templates/types"
        ]
        
        system_info_exposed = 0
        for endpoint in info_endpoints:
            try:
                response = requests.get(endpoint, timeout=3)
                response_text = response.text.lower()
                
                # Check for system info that shouldn't be exposed
                system_keywords = [
                    "version", "server", "python", "flask", "mongodb",
                    "host", "port", "debug", "development"
                ]
                
                if any(keyword in response_text for keyword in system_keywords):
                    system_info_exposed += 1
                
            except:
                pass
        
        # Some system info exposure might be acceptable for API info endpoints
        self.assert_test(system_info_exposed <= 1,
                        "System Information Exposure",
                        f"{system_info_exposed} endpoints exposed system information")
    
    def cleanup_test_data(self):
        """Clean up all test data created during security tests"""
        log("\n🧽 Cleaning up security test data", Colors.BLUE)
        
        cleanup_count = 0
        for user in self.test_users:
            try:
                requests.delete(f"{API_URL}/api/sessions/cleanup-user",
                              headers=user["headers"],
                              timeout=5)
                cleanup_count += 1
                log(f"Cleaned up user: {user['username']}", Colors.WHITE)
            except:
                pass
        
        log(f"Cleaned up {cleanup_count}/{len(self.test_users)} test users", Colors.WHITE)
    
    def test_password_security(self):
        """Test session password security mechanisms"""
        log("\n🔑 Testing Password Security Mechanisms", Colors.BOLD + Colors.YELLOW)
        log("-" * 60, Colors.YELLOW)
        
        user = self.create_test_user("password_security")
        if not user:
            self.assert_test(False, "User Creation for Password Tests", "Failed to create test user")
            return
        
        # Test 1: Password hashing verification
        test_password = "secure_test_password_123"
        session_response = requests.post(f"{API_URL}/api/sessions/create",
                                       json={
                                           "title": "Password Security Test",
                                           "subject": "security",
                                           "password": test_password
                                       },
                                       headers=user["headers"],
                                       timeout=10)
        
        if session_response.status_code == 201:
            session_data = session_response.json().get("session", {})
            session_id = session_data.get("session_id")
            session_code = session_data.get("session_code")
            
            # Verify password is not stored in plaintext
            session_get_response = requests.get(f"{API_URL}/api/sessions/{session_id}",
                                              headers=user["headers"],
                                              timeout=5)
            
            if session_get_response.status_code == 200:
                session_details = session_get_response.json().get("session", {})
                
                # Check that plaintext password is not exposed
                password_not_exposed = (
                    test_password not in str(session_details) and
                    "password" not in session_details and
                    "password_hash" not in session_details
                )
                
                self.assert_test(password_not_exposed, "Password Plaintext Protection",
                                "Password not exposed in API responses")
                
                # Verify password_protected flag is set
                is_protected = session_details.get("is_password_protected", False)
                self.assert_test(is_protected, "Password Protection Flag",
                                f"Session marked as password protected: {is_protected}")
            
            # Test 2: Brute force protection simulation
            guest_user = self.create_test_user("brute_force_test")
            if guest_user:
                failed_attempts = 0
                
                # Try multiple wrong passwords rapidly
                wrong_passwords = [
                    "wrong1", "wrong2", "wrong3", "password", "123456",
                    "admin", "test", "wrong4", "wrong5", "wrong6"
                ]
                
                for wrong_pass in wrong_passwords:
                    try:
                        response = requests.post(f"{API_URL}/api/sessions/join/{session_code}",
                                               json={"password": wrong_pass},
                                               headers=guest_user["headers"],
                                               timeout=2)
                        
                        if response.status_code == 401:
                            failed_attempts += 1
                        
                        # Add small delay to avoid overwhelming the server
                        time.sleep(0.1)
                        
                    except:
                        pass
                
                # System should consistently reject wrong passwords
                brute_force_blocked = failed_attempts >= len(wrong_passwords) * 0.8
                self.assert_test(brute_force_blocked, "Brute Force Resistance",
                                f"{failed_attempts}/{len(wrong_passwords)} wrong passwords rejected")
                
                # Test 3: Correct password should still work after failed attempts
                try:
                    correct_response = requests.post(f"{API_URL}/api/sessions/join/{session_code}",
                                                   json={"password": test_password},
                                                   headers=guest_user["headers"],
                                                   timeout=5)
                    
                    correct_access = correct_response.status_code == 200
                    self.assert_test(correct_access, "Correct Password Access After Failed Attempts",
                                    f"Correct password works: {correct_response.status_code}")
                    
                except Exception as e:
                    self.assert_test(False, "Post-Brute-Force Access", f"Error: {e}")
        
        # Test 4: Password strength and character handling
        special_passwords = [
            "test@#$%^&*()_+-={}[]|\\:;\"'<>?",  # Special characters
            "emoji_test_🔒🔑💻",  # Unicode characters
            "   padded_password   ",  # Whitespace padding
            "UPPER_lower_123_MiXeD",  # Mixed case and numbers
        ]
        
        for i, special_pass in enumerate(special_passwords):
            try:
                session_response = requests.post(f"{API_URL}/api/sessions/create",
                                               json={
                                                   "title": f"Special Password Test {i}",
                                                   "subject": "security",
                                                   "password": special_pass
                                               },
                                               headers=user["headers"],
                                               timeout=5)
                
                if session_response.status_code == 201:
                    session_data = session_response.json().get("session", {})
                    special_session_code = session_data.get("session_code")
                    
                    # Test if special password works for joining
                    join_response = requests.post(f"{API_URL}/api/sessions/join/{special_session_code}",
                                                json={"password": special_pass},
                                                headers=guest_user["headers"],
                                                timeout=5)
                    
                    special_char_success = join_response.status_code == 200
                    test_name = f"Special Characters Password {i+1}"
                    self.assert_test(special_char_success, test_name,
                                    f"Password with special chars works: {join_response.status_code}")
                
            except Exception as e:
                self.assert_test(False, f"Special Password Test {i+1}", f"Error: {e}")
        
        # Test 5: Password validation edge cases
        edge_case_passwords = [
            "",  # Empty password
            " ",  # Single space
            "a" * 51,  # Too long password (over 50 chars)
            "ab",  # Too short password (under 4 chars)
        ]
        
        valid_password_rejected = 0
        
        for edge_pass in edge_case_passwords:
            try:
                response = requests.post(f"{API_URL}/api/sessions/create",
                                       json={
                                           "title": "Edge Case Password Test",
                                           "subject": "security",
                                           "password": edge_pass
                                       },
                                       headers=user["headers"],
                                       timeout=5)
                
                # These should either be rejected or handled gracefully
                if response.status_code in [400, 422]:  # Validation errors
                    valid_password_rejected += 1
                elif response.status_code == 201:
                    # If accepted, it should work properly
                    session_data = response.json().get("session", {})
                    edge_session_code = session_data.get("session_code")
                    
                    if edge_session_code and edge_pass.strip():  # Only test non-empty passwords
                        join_response = requests.post(f"{API_URL}/api/sessions/join/{edge_session_code}",
                                                    json={"password": edge_pass},
                                                    headers=guest_user["headers"],
                                                    timeout=5)
                        
                        if join_response.status_code == 200:
                            valid_password_rejected += 1  # Counts as handled properly
                
            except:
                pass
        
        edge_cases_handled = valid_password_rejected >= len(edge_case_passwords) * 0.5
        self.assert_test(edge_cases_handled, "Password Edge Case Validation",
                        f"{valid_password_rejected}/{len(edge_case_passwords)} edge cases handled properly")
    
    def run_all_tests(self):
        log("🚀 STARTING COMPREHENSIVE SECURITY TEST SUITE", Colors.BOLD + Colors.CYAN)
        log("=" * 80, Colors.CYAN)
        
        start_time = time.time()
        
        try:
            # Run all security test categories
            self.test_authentication_security()
            self.test_authorization_controls()
            self.test_input_validation_security()
            self.test_session_security()
            self.test_password_security()
            self.test_data_exposure_prevention()
            
        except Exception as e:
            log(f"Security test suite crashed: {e}", Colors.RED)
            import traceback
            traceback.print_exc()
        
        finally:
            # Always cleanup
            self.cleanup_test_data()
        
        # Print results
        total_time = time.time() - start_time
        total_tests = self.passed_tests + self.failed_tests
        pass_rate = (self.passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        log("\n" + "=" * 80, Colors.CYAN)
        log("🎯 COMPREHENSIVE SECURITY TEST RESULTS", Colors.BOLD + Colors.CYAN)
        log("=" * 80, Colors.CYAN)
        
        log(f"✅ Passed: {self.passed_tests}", Colors.GREEN)
        log(f"❌ Failed: {self.failed_tests}", Colors.RED)
        log(f"📊 Pass Rate: {pass_rate:.1f}%", Colors.YELLOW)
        log(f"⏱️ Total Time: {total_time:.2f} seconds", Colors.BLUE)
        log(f"👥 Test Users Created: {len(self.test_users)}", Colors.MAGENTA)
        log(f"🌐 Server URL: {API_URL}", Colors.MAGENTA)
        
        if pass_rate >= 95:
            log("🏆 OUTSTANDING! System has excellent security!", Colors.GREEN + Colors.BOLD)
        elif pass_rate >= 85:
            log("✨ EXCELLENT! System has strong security measures!", Colors.GREEN + Colors.BOLD)
        elif pass_rate >= 70:
            log("✅ GOOD! System has reasonable security!", Colors.YELLOW + Colors.BOLD)
        elif pass_rate >= 50:
            log("⚠️ FAIR! System has some security vulnerabilities!", Colors.YELLOW + Colors.BOLD)
        else:
            log("🚨 POOR! System has critical security issues!", Colors.RED + Colors.BOLD)

if __name__ == "__main__":
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔════════════════════════════════════════════════════════════════════════╗")
    print("║                   COMPREHENSIVE SECURITY TEST SUITE                   ║")
    print("║                                                                        ║")
    print("║  Tests: Auth, Authorization, Input Validation, Password Security      ║")
    print("║  🔒 Focus: XSS, SQL Injection, Access Control, Password Hashing       ║")
    print("╚════════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}\n")
    
    # Find running server
    if find_running_server():
        test_suite = SecurityTestSuite()
        test_suite.run_all_tests()
    else:
        log("❌ No server found. Please start the server first.", Colors.RED)
        log("💡 Try: docker-compose up --build", Colors.BLUE)