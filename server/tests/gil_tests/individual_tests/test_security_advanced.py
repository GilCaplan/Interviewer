#!/usr/bin/env python3
"""
Advanced Security Test Suite
Tests authentication edge cases, input validation, rate limiting evasion,
and other security vulnerabilities that could be exploited in production.

Run with: python test_security_advanced.py
"""

import os
# Set testing environment variables
os.environ['TESTING'] = 'true'
os.environ['TEST_MODE'] = '1'
os.environ['FLASK_ENV'] = 'testing'

import requests
import json
import time
import uuid
import base64
import hashlib
from datetime import datetime
import threading
import concurrent.futures

# Test Configuration
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

class SecurityTestSuite:
    def __init__(self):
        self.passed_tests = 0
        self.failed_tests = 0
        self.test_users = []
        self.test_sessions = []
        
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
    
    def create_test_user(self, username_suffix="", delay=0.1):
        """Create a test user with rate limiting consideration"""
        username = f"sec_test_user_{uuid.uuid4().hex[:8]}{username_suffix}"
        try:
            time.sleep(delay)  # Rate limiting protection
            response = requests.post(f"{API_URL}/api/auth/login",
                                   json={"username": username},
                                   timeout=10)
            
            if response.status_code == 200:
                auth_data = response.json()
                token = auth_data.get("token")
                user_id = auth_data.get("user", {}).get("user_id")
                self.test_users.append({"username": username, "token": token, "user_id": user_id})
                return {"username": username, "token": token, "user_id": user_id}
            return None
        except Exception as e:
            log(f"User creation failed: {e}", Colors.YELLOW)
            return None
    
    def test_authentication_edge_cases(self):
        log("\n🔐 Testing Authentication Edge Cases", Colors.BOLD + Colors.YELLOW)
        log("-" * 60, Colors.YELLOW)
        
        # Test 1: Invalid JSON payloads
        invalid_payloads = [
            '{"username":}',  # Invalid JSON
            '{"username": null}',  # Null username
            '{"username": ""}',  # Empty username
            '{"username": "   "}',  # Whitespace only
            '{"user": "test"}',  # Wrong field name
            '{}',  # Empty JSON
            '',  # Empty body
        ]
        
        security_violations = 0
        for i, payload in enumerate(invalid_payloads):
            try:
                response = requests.post(f"{API_URL}/api/auth/login",
                                       data=payload,
                                       headers={"Content-Type": "application/json"},
                                       timeout=5)
                
                # Should return 4xx error, not 5xx or 200
                if response.status_code >= 500:
                    security_violations += 1
                    log(f"Invalid payload {i} caused server error: {response.status_code}", Colors.YELLOW)
                elif response.status_code == 200:
                    security_violations += 1
                    log(f"Invalid payload {i} was accepted: {response.status_code}", Colors.YELLOW)
                
                time.sleep(0.1)  # Rate limiting protection
                
            except requests.exceptions.RequestException:
                pass  # Expected for malformed requests
        
        self.assert_test(security_violations == 0, "Invalid Authentication Payload Handling",
                        f"{len(invalid_payloads) - security_violations}/{len(invalid_payloads)} invalid payloads properly rejected")
        
        # Test 2: Token manipulation attempts
        user = self.create_test_user("_token_test", 0.2)
        if user:
            original_token = user["token"]
            
            # Test manipulated tokens
            manipulated_tokens = [
                original_token[:-5] + "XXXXX",  # Modified signature
                original_token + "extra",  # Extended token
                original_token[5:],  # Truncated token
                base64.b64encode(b"fake_token").decode(),  # Fake token
                "Bearer " + original_token,  # Wrong format
                "",  # Empty token
            ]
            
            token_security_violations = 0
            for token in manipulated_tokens:
                try:
                    response = requests.get(f"{API_URL}/api/sessions/list",
                                          headers={"Authorization": f"Bearer {token}"},
                                          timeout=5)
                    
                    if response.status_code == 200:
                        token_security_violations += 1
                        log(f"Manipulated token was accepted", Colors.RED)
                    
                    time.sleep(0.1)
                    
                except:
                    pass
            
            self.assert_test(token_security_violations == 0, "Token Manipulation Protection",
                            f"All {len(manipulated_tokens)} manipulated tokens properly rejected")
        else:
            self.assert_test(False, "Token Test User Creation", "Failed to create user for token testing")
        
        return True
    
    def test_input_validation_security(self):
        log("\n🛡️ Testing Input Validation Security", Colors.BOLD + Colors.YELLOW)
        log("-" * 60, Colors.YELLOW)
        
        user = self.create_test_user("_input_test", 0.2)
        if not user:
            self.assert_test(False, "Input Test User Creation", "Failed to create test user")
            return False
        
        # Test 1: XSS prevention in various fields
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "' OR '1'='1",
            "${7*7}",
            "{{7*7}}",
            "<%=7*7%>",
            "\"><script>alert('xss')</script>",
        ]
        
        xss_violations = 0
        
        # Test XSS in template creation
        for payload in xss_payloads[:4]:  # Test subset to avoid rate limiting
            try:
                template_data = {
                    "template_name": payload,
                    "description": f"XSS test: {payload}",
                    "subject": "general",
                    "difficulty": "easy"
                }
                
                response = requests.post(f"{API_URL}/api/templates",
                                       json=template_data,
                                       headers={"Authorization": f"Bearer {user['token']}"},
                                       timeout=10)
                
                if response.status_code == 201:
                    # Check if XSS payload was sanitized
                    template_id = response.json().get("template_id")
                    if template_id:
                        # Retrieve template to check sanitization
                        get_response = requests.get(f"{API_URL}/api/templates/{template_id}",
                                                  headers={"Authorization": f"Bearer {user['token']}"},
                                                  timeout=5)
                        
                        if get_response.status_code == 200:
                            template_data = get_response.json().get("template", {})
                            template_name = template_data.get("template_name", "")
                            
                            # Check if dangerous characters are still present
                            if "<script>" in template_name or "javascript:" in template_name:
                                xss_violations += 1
                                log(f"XSS payload not sanitized: {payload}", Colors.RED)
                        
                        # Cleanup
                        requests.delete(f"{API_URL}/api/templates/{template_id}",
                                      headers={"Authorization": f"Bearer {user['token']}"},
                                      timeout=5)
                
                time.sleep(0.2)  # Rate limiting protection
                
            except Exception as e:
                log(f"XSS test error: {e}", Colors.YELLOW)
        
        self.assert_test(xss_violations == 0, "XSS Prevention in Templates",
                        f"XSS payloads properly sanitized")
        
        # Test 2: SQL Injection-like attacks (NoSQL injection)
        injection_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "admin'; --",
            '{"$ne": null}',
            '{"$regex": ".*"}',
        ]
        
        injection_violations = 0
        
        # Test session creation with injection payloads
        for payload in injection_payloads[:3]:  # Test subset
            try:
                session_data = {
                    "title": payload,
                    "description": f"Injection test: {payload}",
                    "subject": "general"
                }
                
                response = requests.post(f"{API_URL}/api/sessions/create",
                                       json=session_data,
                                       headers={"Authorization": f"Bearer {user['token']}"},
                                       timeout=10)
                
                # Should either reject or sanitize, not cause server error
                if response.status_code >= 500:
                    injection_violations += 1
                    log(f"Injection payload caused server error: {payload}", Colors.RED)
                elif response.status_code == 201:
                    # Check if payload was sanitized
                    session_id = response.json().get("session", {}).get("session_id")
                    if session_id:
                        self.test_sessions.append(session_id)
                
                time.sleep(0.2)
                
            except Exception as e:
                log(f"Injection test error: {e}", Colors.YELLOW)
        
        self.assert_test(injection_violations == 0, "Injection Attack Prevention",
                        f"Injection payloads handled safely")
        
        return True
    
    def test_rate_limiting_bypass_attempts(self):
        log("\n⚡ Testing Rate Limiting Bypass Attempts", Colors.BOLD + Colors.YELLOW)
        log("-" * 60, Colors.YELLOW)
        
        # Test 1: Rapid authentication attempts
        rapid_requests = 0
        successful_requests = 0
        rate_limited_requests = 0
        
        start_time = time.time()
        
        for i in range(15):  # Try to exceed typical rate limits
            try:
                response = requests.post(f"{API_URL}/api/auth/login",
                                       json={"username": f"rate_test_user_{i}"},
                                       timeout=3)
                
                rapid_requests += 1
                
                if response.status_code == 200:
                    successful_requests += 1
                elif response.status_code == 429:  # Too Many Requests
                    rate_limited_requests += 1
                
                # No delay to test rate limiting
                
            except requests.exceptions.Timeout:
                pass  # Expected under rate limiting
            except Exception as e:
                log(f"Rate limit test error: {e}", Colors.YELLOW)
        
        total_time = time.time() - start_time
        
        # Rate limiting should kick in - not all requests should succeed
        rate_limiting_working = rate_limited_requests > 0 or successful_requests < rapid_requests * 0.8
        
        self.assert_test(rate_limiting_working, "Rate Limiting Protection",
                        f"{successful_requests}/{rapid_requests} requests succeeded, {rate_limited_requests} rate limited in {total_time:.2f}s")
        
        # Test 2: Different IP simulation (using different User-Agent headers)
        time.sleep(1)  # Cool down period
        
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "curl/7.68.0",
            "PostmanRuntime/7.26.8",
        ]
        
        bypass_attempts = 0
        for ua in user_agents:
            try:
                response = requests.post(f"{API_URL}/api/auth/login",
                                       json={"username": f"ua_test_{uuid.uuid4().hex[:4]}"},
                                       headers={"User-Agent": ua},
                                       timeout=5)
                
                if response.status_code == 200:
                    bypass_attempts += 1
                
                time.sleep(0.1)
                
            except Exception as e:
                log(f"User-Agent bypass test error: {e}", Colors.YELLOW)
        
        # Should still be rate limited even with different user agents
        bypass_protection = bypass_attempts < len(user_agents)
        
        self.assert_test(bypass_protection, "Rate Limit Bypass Protection",
                        f"User-Agent variation bypass attempts: {bypass_attempts}/{len(user_agents)}")
        
        return True
    
    def test_session_security_edge_cases(self):
        log("\n🔒 Testing Session Security Edge Cases", Colors.BOLD + Colors.YELLOW)
        log("-" * 60, Colors.YELLOW)
        
        # Create host and participant users
        host_user = self.create_test_user("_host", 0.3)
        participant_user = self.create_test_user("_participant", 0.3)
        
        if not host_user or not participant_user:
            self.assert_test(False, "Session Security Test Users", "Failed to create test users")
            return False
        
        # Test 1: Session code enumeration protection
        log("Testing session code enumeration protection...", Colors.BLUE)
        
        # Create a real session first
        session_data = {
            "title": "Security Test Session",
            "description": "Testing session security",
            "subject": "general"
        }
        
        response = requests.post(f"{API_URL}/api/sessions/create",
                               json=session_data,
                               headers={"Authorization": f"Bearer {host_user['token']}"},
                               timeout=10)
        
        real_session_code = None
        if response.status_code == 201:
            real_session_code = response.json().get("session", {}).get("session_code")
            session_id = response.json().get("session", {}).get("session_id")
            self.test_sessions.append(session_id)
        
        # Try to enumerate session codes
        enumeration_attempts = [
            "000000", "111111", "AAAAAA", "123456", 
            "ABCDEF", "XXXXXX", "000001", "999999"
        ]
        
        if real_session_code:
            enumeration_attempts.append(real_session_code)  # Include the real one
        
        successful_enumerations = 0
        for code in enumeration_attempts:
            try:
                response = requests.post(f"{API_URL}/api/sessions/join/{code}",
                                       headers={"Authorization": f"Bearer {participant_user['token']}"},
                                       timeout=5)
                
                if response.status_code == 200 and code != real_session_code:
                    successful_enumerations += 1
                    log(f"Successfully enumerated session code: {code}", Colors.RED)
                
                time.sleep(0.1)
                
            except Exception as e:
                log(f"Enumeration test error: {e}", Colors.YELLOW)
        
        self.assert_test(successful_enumerations == 0, "Session Code Enumeration Protection",
                        f"Prevented {len(enumeration_attempts)-1}/{len(enumeration_attempts)-1} enumeration attempts")
        
        # Test 2: Permission escalation attempts
        if real_session_code and len(self.test_sessions) > 0:
            session_id = self.test_sessions[-1]
            
            # Participant tries to perform host-only operations
            escalation_attempts = 0
            
            # Try to delete session (host-only)
            try:
                response = requests.delete(f"{API_URL}/api/sessions/{session_id}",
                                         headers={"Authorization": f"Bearer {participant_user['token']}"},
                                         timeout=5)
                
                if response.status_code == 200:
                    escalation_attempts += 1
                    log("Participant was able to delete session", Colors.RED)
                
            except Exception as e:
                log(f"Permission test error: {e}", Colors.YELLOW)
            
            # Try to clear all questions (host-only)
            try:
                response = requests.delete(f"{API_URL}/api/sessions/{session_id}/questions/clear",
                                         headers={"Authorization": f"Bearer {participant_user['token']}"},
                                         timeout=5)
                
                if response.status_code == 200:
                    escalation_attempts += 1
                    log("Participant was able to clear questions", Colors.RED)
                
            except Exception as e:
                log(f"Permission test error: {e}", Colors.YELLOW)
            
            self.assert_test(escalation_attempts == 0, "Permission Escalation Protection",
                            f"Prevented participant from performing host-only operations")
        else:
            self.assert_test(False, "Session Creation for Permission Test", "Failed to create test session")
        
        return True
    
    def test_data_exposure_prevention(self):
        log("\n🕵️ Testing Data Exposure Prevention", Colors.BOLD + Colors.YELLOW)
        log("-" * 60, Colors.YELLOW)
        
        user = self.create_test_user("_exposure", 0.3)
        if not user:
            self.assert_test(False, "Data Exposure Test User", "Failed to create test user")
            return False
        
        # Test 1: Error message information leakage
        log("Testing error message information leakage...", Colors.BLUE)
        
        # Try to access non-existent resources
        test_endpoints = [
            f"/api/sessions/nonexistent-session-id",
            f"/api/templates/nonexistent-template-id",
            f"/api/sessions/nonexistent-session-id/questions/1/start",
        ]
        
        information_leaks = 0
        for endpoint in test_endpoints:
            try:
                response = requests.get(f"{API_URL}{endpoint}",
                                      headers={"Authorization": f"Bearer {user['token']}"},
                                      timeout=5)
                
                if response.status_code >= 400:
                    response_text = response.text.lower()
                    
                    # Check for common information leaks
                    leak_indicators = [
                        "stack trace", "traceback", "exception",
                        "database", "mongodb", "sql", "internal server",
                        "file not found", "path", "/Users/", "/home/",
                        "secret", "password", "token"
                    ]
                    
                    for indicator in leak_indicators:
                        if indicator in response_text:
                            information_leaks += 1
                            log(f"Information leak detected in {endpoint}: {indicator}", Colors.RED)
                            break
                
                time.sleep(0.1)
                
            except Exception as e:
                log(f"Information leak test error: {e}", Colors.YELLOW)
        
        self.assert_test(information_leaks == 0, "Error Message Information Leakage Prevention",
                        f"No sensitive information leaked in error messages")
        
        # Test 2: Response header security
        log("Testing response header security...", Colors.BLUE)
        
        try:
            response = requests.get(f"{API_URL}/api/health", timeout=5)
            headers = response.headers
            
            security_headers_present = 0
            recommended_headers = [
                "X-Content-Type-Options",
                "X-Frame-Options", 
                "X-XSS-Protection",
                "Strict-Transport-Security",
                "Content-Security-Policy",
            ]
            
            for header in recommended_headers:
                if header in headers:
                    security_headers_present += 1
            
            # Check for information disclosure in headers
            sensitive_headers = ["Server", "X-Powered-By"]
            info_disclosure = 0
            
            for header in sensitive_headers:
                if header in headers:
                    header_value = headers[header].lower()
                    if any(tech in header_value for tech in ["flask", "python", "werkzeug", "nginx", "apache"]):
                        info_disclosure += 1
            
            self.assert_test(info_disclosure == 0, "Server Information Disclosure Prevention",
                            f"Server technology information properly hidden")
            
        except Exception as e:
            log(f"Header security test error: {e}", Colors.YELLOW)
            self.assert_test(False, "Response Header Security Test", f"Failed to test headers: {e}")
        
        return True
    
    def cleanup_test_data(self):
        """Clean up all test data created during security testing"""
        log("\n🧽 Cleaning up security test data", Colors.BLUE)
        
        cleanup_count = 0
        
        # Clean up sessions
        for session_id in self.test_sessions:
            try:
                if self.test_users:
                    requests.delete(f"{API_URL}/api/sessions/{session_id}",
                                  headers={"Authorization": f"Bearer {self.test_users[0]['token']}"},
                                  timeout=5)
                    cleanup_count += 1
            except:
                pass  # Ignore cleanup errors
        
        log(f"Cleaned up {cleanup_count} test objects", Colors.WHITE)
    
    def run_all_tests(self):
        log("🚀 STARTING ADVANCED SECURITY TEST SUITE", Colors.BOLD + Colors.CYAN)
        log("=" * 80, Colors.CYAN)
        
        start_time = time.time()
        
        try:
            # Run security test categories
            self.test_authentication_edge_cases()
            self.test_input_validation_security()
            self.test_rate_limiting_bypass_attempts()
            self.test_session_security_edge_cases()
            self.test_data_exposure_prevention()
            
        except Exception as e:
            log(f"Security test suite crashed: {e}", Colors.RED)
            import traceback
            traceback.print_exc()
        
        finally:
            # Always try to cleanup
            self.cleanup_test_data()
        
        # Print results
        total_time = time.time() - start_time
        total_tests = self.passed_tests + self.failed_tests
        pass_rate = (self.passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        log("\n" + "=" * 80, Colors.CYAN)
        log("🎯 ADVANCED SECURITY TEST RESULTS", Colors.BOLD + Colors.CYAN)
        log("=" * 80, Colors.CYAN)
        
        log(f"✅ Passed: {self.passed_tests}", Colors.GREEN)
        log(f"❌ Failed: {self.failed_tests}", Colors.RED)
        log(f"📊 Pass Rate: {pass_rate:.1f}%", Colors.YELLOW)
        log(f"⏱️ Total Time: {total_time:.2f} seconds", Colors.BLUE)
        log(f"👤 Test Users Created: {len(self.test_users)}", Colors.MAGENTA)
        log(f"🏢 Test Sessions Created: {len(self.test_sessions)}", Colors.MAGENTA)
        log(f"🌐 Server URL: {API_URL}", Colors.MAGENTA)
        
        if pass_rate >= 95:
            log("🏆 OUTSTANDING! Security measures are comprehensive and robust!", Colors.GREEN + Colors.BOLD)
        elif pass_rate >= 85:
            log("✨ EXCELLENT! Security is strong with minor areas for improvement", Colors.GREEN + Colors.BOLD)
        elif pass_rate >= 70:
            log("✅ GOOD! Security measures are adequate but could be enhanced", Colors.YELLOW + Colors.BOLD)
        elif pass_rate >= 50:
            log("⚠️ FAIR! Security has vulnerabilities that need attention", Colors.YELLOW + Colors.BOLD)
        else:
            log("🚨 POOR! Critical security vulnerabilities detected!", Colors.RED + Colors.BOLD)

if __name__ == "__main__":
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔════════════════════════════════════════════════════════════════════════╗")
    print("║                ADVANCED SECURITY TEST SUITE                           ║")
    print("║                                                                        ║")
    print("║  Tests: Auth Edge Cases, Input Validation, Rate Limiting, Data Exposure║")
    print("╚════════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}\n")
    
    # Find running server
    if find_running_server():
        test_suite = SecurityTestSuite()
        test_suite.run_all_tests()
    else:
        log("❌ No server found. Please start the server first.", Colors.RED)
        log("💡 Try: docker-compose up --build", Colors.BLUE)