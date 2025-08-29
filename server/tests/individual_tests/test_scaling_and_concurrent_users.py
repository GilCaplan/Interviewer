# Import test configuration
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from test_config import get_all_api_urls

#!/usr/bin/env python3
"""
Scaling and Concurrent Users Test Suite
Tests multi-host scenarios with multiple users per session, concurrent operations,
and system behavior under realistic collaborative workloads.

Run with: python test_scaling_and_concurrent_users.py
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
import threading
import concurrent.futures
from datetime import datetime
from queue import Queue

# Test Configuration
API_URLS = get_all_api_urls()
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

class TestUser:
    """Represents a test user with authentication"""
    def __init__(self, username_prefix="scale_test"):
        self.username = f"{username_prefix}_{uuid.uuid4().hex[:8]}"
        self.token = None
        self.headers = None
        self.user_id = None
        self.session_ids = []  # Track sessions created by this user
        
    def authenticate(self):
        """Login and get authentication token"""
        try:
            response = requests.post(f"{API_URL}/api/auth/login",
                                   json={"username": self.username},
                                   timeout=10)
            
            if response.status_code == 200:
                auth_data = response.json()
                self.token = auth_data.get("token")
                self.user_id = auth_data.get("user", {}).get("user_id")
                self.headers = {"Authorization": f"Bearer {self.token}"}
                return True
            return False
        except Exception as e:
            log(f"Authentication failed for {self.username}: {e}", Colors.RED)
            return False
    
    def create_session(self, title_suffix=""):
        """Create a new session as host"""
        session_data = {
            "title": f"Scale Test Session {title_suffix} by {self.username}",
            "subject": "general",
            "description": f"Scaling test session hosted by {self.username}",
            "template_mode": True,
            "settings": {
                "max_participants": 10,
                "max_questions": 20,
                "allow_llm": True,
                "allow_user_questions": True
            }
        }
        
        try:
            response = requests.post(f"{API_URL}/api/sessions/create",
                                   json=session_data,
                                   headers=self.headers,
                                   timeout=15)
            
            if response.status_code == 201:
                session_info = response.json().get("session", {})
                session_id = session_info.get("session_id")
                self.session_ids.append(session_id)
                return session_id, session_info
            return None, None
        except Exception as e:
            log(f"Session creation failed for {self.username}: {e}", Colors.RED)
            return None, None
    
    def join_session(self, session_code):
        """Join an existing session"""
        try:
            response = requests.post(f"{API_URL}/api/sessions/join/{session_code}",
                                   headers=self.headers,
                                   timeout=15)
            
            if response.status_code == 200:
                session_info = response.json().get("session", {})
                return session_info.get("session_id"), session_info
            return None, None
        except Exception as e:
            log(f"Session join failed for {self.username}: {e}", Colors.RED)
            return None, None
    
    def create_question(self, session_id, question_number, question_type="open_ended"):
        """Create and update a question"""
        try:
            # Start question building
            response = requests.post(f"{API_URL}/api/sessions/{session_id}/questions/{question_number}/start",
                                   json={"type": question_type},
                                   headers=self.headers,
                                   timeout=15)
            
            if response.status_code == 200:
                question_info = response.json().get("question", {})
                question_id = question_info.get("question_id")
                
                # Add content to the question
                content_data = {
                    "field": "question_text",
                    "value": f"Question {question_number} by {self.username}: This is a test question for scaling tests."
                }
                
                response = requests.put(f"{API_URL}/api/sessions/{session_id}/questions/{question_id}/update",
                                      json=content_data,
                                      headers=self.headers,
                                      timeout=15)
                
                return question_id if response.status_code == 200 else None
            return None
        except Exception as e:
            log(f"Question creation failed for {self.username}: {e}", Colors.RED)
            return None
    
    def finalize_question(self, session_id, question_id):
        """Finalize a question (host only)"""
        try:
            response = requests.post(f"{API_URL}/api/sessions/{session_id}/questions/{question_id}/finalize",
                                   headers=self.headers,
                                   timeout=15)
            return response.status_code == 200
        except Exception as e:
            log(f"Question finalization failed for {self.username}: {e}", Colors.RED)
            return False
    
    def cleanup_sessions(self):
        """Clean up all sessions created by this user"""
        try:
            response = requests.delete(f"{API_URL}/api/sessions/cleanup-user",
                                     headers=self.headers,
                                     timeout=15)
            return response.status_code == 200
        except:
            return False

class ScalingTestSuite:
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
    
    def create_test_users(self, count):
        """Create multiple authenticated test users"""
        users = []
        for i in range(count):
            user = TestUser(f"scale_user_{i}")
            if user.authenticate():
                users.append(user)
                self.test_users.append(user)
            else:
                log(f"Failed to create user {i+1}/{count}", Colors.RED)
        
        return users
    
    def test_multiple_hosts_single_session_each(self):
        log("\n👥 Testing Multiple Hosts with Single Sessions Each", Colors.BOLD + Colors.YELLOW)
        log("-" * 60, Colors.YELLOW)
        
        # Create 5 hosts, each with their own session
        host_count = 5
        hosts = self.create_test_users(host_count)
        
        self.assert_test(len(hosts) == host_count, "Multiple Host User Creation",
                        f"Created {len(hosts)}/{host_count} hosts")
        
        # Each host creates their own session
        session_results = []
        for i, host in enumerate(hosts):
            session_id, session_info = host.create_session(f"Host-{i+1}")
            if session_id:
                session_results.append((host, session_id, session_info))
                self.test_sessions.append(session_id)
        
        self.assert_test(len(session_results) == host_count, "Multiple Session Creation",
                        f"Created {len(session_results)}/{host_count} sessions")
        
        # Each host adds questions to their session
        questions_created = 0
        for host, session_id, _ in session_results:
            for q_num in range(1, 4):  # 3 questions per session
                question_id = host.create_question(session_id, q_num, "open_ended")
                if question_id:
                    questions_created += 1
        
        expected_questions = len(session_results) * 3
        self.assert_test(questions_created >= expected_questions * 0.8, "Host Question Creation",
                        f"Created {questions_created}/{expected_questions} questions")
        
        # Test concurrent question finalization
        finalization_results = []
        def finalize_questions_for_host(host, session_id):
            """Finalize all questions for a host's session"""
            session_response = requests.get(f"{API_URL}/api/sessions/{session_id}",
                                          headers=host.headers, timeout=10)
            if session_response.status_code == 200:
                session_data = session_response.json().get("session", {})
                questions_queue = session_data.get("template_data", {}).get("questions_queue", [])
                
                finalized_count = 0
                for question in questions_queue[:2]:  # Finalize first 2 questions
                    question_id = question.get("question_id")
                    if host.finalize_question(session_id, question_id):
                        finalized_count += 1
                
                return finalized_count
            return 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=host_count) as executor:
            futures = [executor.submit(finalize_questions_for_host, host, session_id) 
                      for host, session_id, _ in session_results]
            
            for future in concurrent.futures.as_completed(futures):
                finalization_results.append(future.result())
        
        total_finalized = sum(finalization_results)
        self.assert_test(total_finalized >= len(session_results) * 1.5, "Concurrent Question Finalization",
                        f"Finalized {total_finalized} questions across {len(session_results)} sessions")
        
        return True
    
    def test_single_host_multiple_participants(self):
        log("\n🏢 Testing Single Host with Multiple Participants", Colors.BOLD + Colors.YELLOW)
        log("-" * 60, Colors.YELLOW)
        
        # Create 1 host and many participants
        host = self.create_test_users(1)[0]
        participants = self.create_test_users(50)
        
        self.assert_test(len(participants) >= 40, "Participant User Creation",
                        f"Created {len(participants)}/50 participants")
        
        # Host creates a session
        session_id, session_info = host.create_session("Multi-Participant")
        session_code = session_info.get("session_code") if session_info else None
        
        self.assert_test(session_id is not None, "Host Session Creation",
                        f"Session code: {session_code}")
        
        if session_id:
            self.test_sessions.append(session_id)
        
        # All participants join the session concurrently
        join_results = []
        def participant_join(participant, session_code):
            """Participant joins session"""
            try:
                joined_session_id, _ = participant.join_session(session_code)
                return joined_session_id is not None
            except:
                return False
        
        if session_code:
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                futures = [executor.submit(participant_join, p, session_code) 
                          for p in participants]
                
                for future in concurrent.futures.as_completed(futures):
                    join_results.append(future.result())
        
        successful_joins = sum(join_results)
        self.assert_test(successful_joins >= 6, "Concurrent Session Joining",
                        f"{successful_joins}/8 participants joined successfully")
        
        # Host creates questions while participants are connected
        if session_id:
            host_questions = []
            for q_num in range(1, 6):  # 5 questions
                question_id = host.create_question(session_id, q_num, "multiple_choice")
                if question_id:
                    host_questions.append(question_id)
                time.sleep(0.1)  # Small delay to simulate real typing
            
            self.assert_test(len(host_questions) >= 4, "Host Question Creation with Participants",
                            f"Created {len(host_questions)}/5 questions")
            
            # Test concurrent question updates from multiple participants
            update_results = []
            def participant_attempt_update(participant, session_id, question_id):
                """Participant attempts to update question (should work for non-hosts too)"""
                try:
                    response = requests.put(f"{API_URL}/api/sessions/{session_id}/questions/{question_id}/update",
                                          json={"field": "question_text", "value": f"Updated by {participant.username}"},
                                          headers=participant.headers,
                                          timeout=10)
                    return response.status_code == 200
                except:
                    return False
            
            if host_questions:
                # Let 4 participants try to update the first question
                with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                    futures = [executor.submit(participant_attempt_update, p, session_id, host_questions[0]) 
                              for p in participants[:4]]
                    
                    for future in concurrent.futures.as_completed(futures):
                        update_results.append(future.result())
                
                successful_updates = sum(update_results)
                self.assert_test(successful_updates >= 2, "Concurrent Question Updates",
                                f"{successful_updates}/4 participant updates successful")
        
        return True
    
    def test_multiple_hosts_shared_sessions(self):
        log("\n🤝 Testing Multiple Hosts with Shared Sessions", Colors.BOLD + Colors.YELLOW)
        log("-" * 60, Colors.YELLOW)
        
        # Create extreme number of hosts
        hosts = self.create_test_users(500)
        
        self.assert_test(len(hosts) >= 400, "Multi-Host User Creation",
                        f"Created {len(hosts)}/500 hosts")
        
        # First host creates a session, others join as participants then become hosts
        session_results = []
        
        if hosts:
            # Host 1 creates the session
            session_id, session_info = hosts[0].create_session("Shared-Collaboration")
            session_code = session_info.get("session_code") if session_info else None
            
            if session_id:
                self.test_sessions.append(session_id)
                session_results.append((hosts[0], session_id, "creator"))
                
                # Other hosts join as participants
                for i, host in enumerate(hosts[1:], 2):
                    joined_session_id, _ = host.join_session(session_code)
                    if joined_session_id:
                        session_results.append((host, session_id, f"participant_{i}"))
        
        self.assert_test(len(session_results) >= 2, "Multi-Host Session Sharing",
                        f"{len(session_results)}/3 hosts in shared session")
        
        # Each host tries to contribute questions (some will fail due to permissions)
        contribution_results = []
        def host_contribute_questions(host, session_id, host_role, start_q_num):
            """Host contributes questions to shared session"""
            questions_created = 0
            for q_offset in range(3):  # Try to create 3 questions each
                q_num = start_q_num + q_offset
                question_id = host.create_question(session_id, q_num, "short_answer")
                if question_id:
                    questions_created += 1
                time.sleep(0.05)  # Small delay
            return questions_created, host_role
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(host_contribute_questions, host, session_id, role, i*3+1) 
                      for i, (host, session_id, role) in enumerate(session_results)]
            
            for future in concurrent.futures.as_completed(futures):
                contribution_results.append(future.result())
        
        total_contributions = sum(result[0] for result in contribution_results)
        self.assert_test(total_contributions >= 3, "Multi-Host Question Contributions",
                        f"Total questions created: {total_contributions}")
        
        # Test host-only operations (only original host should succeed)
        if session_results:
            original_host = session_results[0][0]  # First host is the creator
            session_id = session_results[0][1]
            
            # Original host should be able to finalize questions
            session_response = requests.get(f"{API_URL}/api/sessions/{session_id}",
                                          headers=original_host.headers, timeout=10)
            if session_response.status_code == 200:
                session_data = session_response.json().get("session", {})
                questions_queue = session_data.get("template_data", {}).get("questions_queue", [])
                
                finalized_by_host = 0
                for question in questions_queue[:2]:  # Try to finalize first 2
                    question_id = question.get("question_id")
                    if original_host.finalize_question(session_id, question_id):
                        finalized_by_host += 1
                
                self.assert_test(finalized_by_host >= 1, "Host-Only Operations",
                                f"Original host finalized {finalized_by_host} questions")
            
            # Non-host should not be able to delete session
            if len(session_results) > 1:
                non_host = session_results[1][0]
                try:
                    response = requests.delete(f"{API_URL}/api/sessions/{session_id}",
                                             headers=non_host.headers, timeout=10)
                    delete_blocked = response.status_code == 403
                    self.assert_test(delete_blocked, "Non-Host Delete Protection",
                                    f"Non-host delete blocked: {response.status_code}")
                except Exception as e:
                    self.assert_test(False, "Non-Host Delete Protection", f"Error: {e}")
        
        return True
    
    def test_concurrent_session_operations(self):
        log("\n⚡ Testing Concurrent Session Operations", Colors.BOLD + Colors.YELLOW)
        log("-" * 60, Colors.YELLOW)
        
        # Create multiple users for concurrent operations
        users = self.create_test_users(100)
        
        self.assert_test(len(users) >= 4, "Concurrent Test User Creation",
                        f"Created {len(users)}/6 users")
        
        # Test 1: Concurrent session creation
        session_creation_results = []
        def create_session_concurrently(user, session_suffix):
            """Create session concurrently"""
            session_id, session_info = user.create_session(f"Concurrent-{session_suffix}")
            return session_id is not None
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(create_session_concurrently, user, i) 
                      for i, user in enumerate(users[:4])]
            
            for future in concurrent.futures.as_completed(futures):
                session_creation_results.append(future.result())
        
        successful_creations = sum(session_creation_results)
        self.assert_test(successful_creations >= 3, "Concurrent Session Creation",
                        f"{successful_creations}/4 sessions created concurrently")
        
        # Test 2: Concurrent question creation in same session
        if users:
            main_host = users[0]
            session_id, session_info = main_host.create_session("Concurrent-Questions")
            
            if session_id:
                self.test_sessions.append(session_id)
                
                # Multiple users join the session
                session_code = session_info.get("session_code")
                join_count = 0
                for user in users[1:4]:  # 3 users join
                    if user.join_session(session_code)[0]:
                        join_count += 1
                
                self.assert_test(join_count >= 2, "Concurrent Session Joining for Question Test",
                                f"{join_count}/3 users joined")
                
                # All users try to create questions concurrently
                question_creation_results = []
                def create_question_concurrently(user, session_id, q_num):
                    """Create question concurrently"""
                    question_id = user.create_question(session_id, q_num, "true_false")
                    return question_id is not None
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                    futures = [executor.submit(create_question_concurrently, user, session_id, i+1) 
                              for i, user in enumerate(users[:4])]
                    
                    for future in concurrent.futures.as_completed(futures):
                        question_creation_results.append(future.result())
                
                successful_q_creations = sum(question_creation_results)
                self.assert_test(successful_q_creations >= 2, "Concurrent Question Creation",
                                f"{successful_q_creations}/4 questions created concurrently")
        
        # Test 3: Concurrent cleanup operations
        cleanup_results = []
        def cleanup_user_sessions(user):
            """Each user cleans up their own sessions"""
            return user.cleanup_sessions()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(users)) as executor:
            futures = [executor.submit(cleanup_user_sessions, user) for user in users]
            
            for future in concurrent.futures.as_completed(futures):
                cleanup_results.append(future.result())
        
        successful_cleanups = sum(cleanup_results)
        self.assert_test(successful_cleanups >= len(users) * 0.75, "Concurrent Session Cleanup",
                        f"{successful_cleanups}/{len(users)} users cleaned up successfully")
        
        return True
    
    def test_system_performance_under_load(self):
        log("\n🚀 Testing System Performance Under Load", Colors.BOLD + Colors.YELLOW)
        log("-" * 60, Colors.YELLOW)
        
        # Create extreme load: 1000 users, each with their own session
        load_users = self.create_test_users(1000)
        
        self.assert_test(len(load_users) >= 800, "Load Test User Creation",
                        f"Created {len(load_users)}/1000 users for load testing")
        
        # Measure session creation time under load
        start_time = time.time()
        
        def create_loaded_session(user, user_index):
            """Create session and add content under load"""
            session_start = time.time()
            
            # Create session
            session_id, session_info = user.create_session(f"Load-{user_index}")
            if not session_id:
                return False, 0, 0
            
            self.test_sessions.append(session_id)
            
            # Add multiple questions quickly
            questions_created = 0
            for q_num in range(1, 6):  # 5 questions per session
                question_id = user.create_question(session_id, q_num, "open_ended")
                if question_id:
                    questions_created += 1
                time.sleep(0.02)  # Small delay to simulate typing
            
            session_time = time.time() - session_start
            return True, questions_created, session_time
        
        # Execute massive load test with high concurrency
        load_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=500) as executor:
            futures = [executor.submit(create_loaded_session, user, i) 
                      for i, user in enumerate(load_users)]
            
            for future in concurrent.futures.as_completed(futures):
                load_results.append(future.result())
        
        total_load_time = time.time() - start_time
        
        # Analyze results
        successful_loads = sum(1 for success, _, _ in load_results if success)
        total_questions = sum(q_count for _, q_count, _ in load_results)
        avg_session_time = sum(s_time for _, _, s_time in load_results) / len(load_results) if load_results else 0
        
        self.assert_test(successful_loads >= len(load_users) * 0.8, "Load Test Success Rate",
                        f"{successful_loads}/{len(load_users)} sessions created under load")
        
        self.assert_test(total_questions >= len(load_users) * 3, "Load Test Question Creation",
                        f"{total_questions} questions created across all sessions")
        
        self.assert_test(avg_session_time < 10.0, "Session Creation Performance",
                        f"Average session creation time: {avg_session_time:.2f}s")
        
        self.assert_test(total_load_time < 60.0, "Overall Load Test Time",
                        f"Total load test completed in {total_load_time:.2f}s")
        
        return True
    
    def cleanup_all_test_data(self):
        """Clean up all test data created during scaling tests"""
        log("\n🧽 Cleaning up scaling test data", Colors.BLUE)
        
        cleanup_count = 0
        for user in self.test_users:
            try:
                if user.cleanup_sessions():
                    cleanup_count += 1
                log(f"Cleaned up sessions for user: {user.username}", Colors.WHITE)
            except:
                pass  # Ignore cleanup errors
        
        log(f"Cleaned up sessions for {cleanup_count}/{len(self.test_users)} users", Colors.WHITE)
    
    def run_all_tests(self):
        log("🚀 STARTING SCALING AND CONCURRENT USERS TEST SUITE", Colors.BOLD + Colors.CYAN)
        log("=" * 80, Colors.CYAN)
        
        start_time = time.time()
        
        try:
            # Run scaling test categories
            self.test_multiple_hosts_single_session_each()
            self.test_single_host_multiple_participants()
            self.test_multiple_hosts_shared_sessions()
            self.test_concurrent_session_operations()
            self.test_system_performance_under_load()
            
        except Exception as e:
            log(f"Scaling test suite crashed: {e}", Colors.RED)
            import traceback
            traceback.print_exc()
        
        finally:
            # Always try to cleanup
            self.cleanup_all_test_data()
        
        # Print results
        total_time = time.time() - start_time
        total_tests = self.passed_tests + self.failed_tests
        pass_rate = (self.passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        log("\n" + "=" * 80, Colors.CYAN)
        log("🎯 SCALING AND CONCURRENT USERS TEST RESULTS", Colors.BOLD + Colors.CYAN)
        log("=" * 80, Colors.CYAN)
        
        log(f"✅ Passed: {self.passed_tests}", Colors.GREEN)
        log(f"❌ Failed: {self.failed_tests}", Colors.RED)
        log(f"📊 Pass Rate: {pass_rate:.1f}%", Colors.YELLOW)
        log(f"⏱️ Total Time: {total_time:.2f} seconds", Colors.BLUE)
        log(f"👥 Test Users Created: {len(self.test_users)}", Colors.MAGENTA)
        log(f"🏢 Test Sessions Created: {len(self.test_sessions)}", Colors.MAGENTA)
        log(f"🌐 Server URL: {API_URL}", Colors.MAGENTA)
        
        if pass_rate >= 90:
            log("🏆 OUTSTANDING! System handles scaling and concurrency perfectly!", Colors.GREEN + Colors.BOLD)
        elif pass_rate >= 75:
            log("✨ EXCELLENT! System scales well with minor issues", Colors.GREEN + Colors.BOLD)
        elif pass_rate >= 60:
            log("✅ GOOD! System handles moderate load well", Colors.YELLOW + Colors.BOLD)
        elif pass_rate >= 40:
            log("⚠️ FAIR! System has scaling limitations", Colors.YELLOW + Colors.BOLD)
        else:
            log("🚨 POOR! System has serious scaling issues", Colors.RED + Colors.BOLD)

if __name__ == "__main__":
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔════════════════════════════════════════════════════════════════════════╗")
    print("║                SCALING AND CONCURRENT USERS TEST SUITE                 ║")
    print("║                                                                        ║")
    print("║  Tests: Multi-Host, Multi-User, Concurrent Ops, Performance Load      ║")
    print("╚════════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}\n")
    
    # Find running server
    if find_running_server():
        test_suite = ScalingTestSuite()
        test_suite.run_all_tests()
    else:
        log("❌ No server found. Please start the server first.", Colors.RED)
        log("💡 Try: docker-compose up --build", Colors.BLUE)