#!/usr/bin/env python3
"""
Multi-User Session Collaboration Test Suite
Tests concurrent users building templates together, session limits, and real-time collaboration

Run with: python test_session_collaboration.py
"""

import requests
import json
import time
import uuid
import threading
import random
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Test Configuration
API_URL = "http://localhost:5001"
MAX_CONCURRENT_USERS = 8
SESSION_TEST_DURATION = 30  # seconds
QUESTION_BUILDING_DELAY = 2  # seconds between actions

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

class CollaborationTestUser:
    def __init__(self, user_id):
        self.user_id = user_id
        self.username = f"collab_user_{user_id}"
        self.token = None
        self.session_id = None
        self.session_code = None
        
        # Activity tracking
        self.actions_performed = 0
        self.questions_started = 0
        self.questions_updated = 0
        self.llm_requests = 0
        self.chat_messages = 0
        self.collaboration_notes = 0
        self.errors_encountered = 0
        
    def login(self):
        try:
            response = requests.post(f"{API_URL}/api/auth/login",
                                   json={"username": self.username})
            if response.status_code == 200:
                self.token = response.json().get("token")
                return True
            return False
        except Exception as e:
            log(f"❌ Login failed for {self.username}: {e}", Colors.RED)
            return False
    
    def get_headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}
    
    def join_session(self, session_code):
        try:
            response = requests.post(f"{API_URL}/api/sessions/join/{session_code}",
                                   json={},
                                   headers=self.get_headers())
            if response.status_code == 200:
                session_data = response.json().get("session", {})
                self.session_id = session_data.get("session_id")
                self.session_code = session_code
                return True
            return False
        except Exception as e:
            self.errors_encountered += 1
            return False
    
    def send_chat_message(self, message):
        try:
            response = requests.post(f"{API_URL}/api/sessions/{self.session_id}/chat",
                                   json={"message": f"{self.username}: {message}"},
                                   headers=self.get_headers())
            if response.status_code == 200:
                self.chat_messages += 1
                self.actions_performed += 1
                return True
            return False
        except Exception as e:
            self.errors_encountered += 1
            return False
    
    def start_question_building(self, question_number, question_type):
        try:
            response = requests.post(f"{API_URL}/api/sessions/{self.session_id}/questions/{question_number}/start",
                                   json={"type": question_type},
                                   headers=self.get_headers())
            if response.status_code == 200:
                self.questions_started += 1
                self.actions_performed += 1
                return response.json().get("question", {}).get("question_id")
            return None
        except Exception as e:
            self.errors_encountered += 1
            return None
    
    def update_question_content(self, question_id, field, value):
        try:
            response = requests.put(f"{API_URL}/api/sessions/{self.session_id}/questions/{question_id}/update",
                                  json={"field": field, "value": value},
                                  headers=self.get_headers())
            if response.status_code == 200:
                self.questions_updated += 1
                self.actions_performed += 1
                return True
            return False
        except Exception as e:
            self.errors_encountered += 1
            return False
    
    def request_llm_suggestion(self, question_id, field="question_text", context=""):
        try:
            response = requests.post(f"{API_URL}/api/sessions/{self.session_id}/questions/{question_id}/llm-suggest",
                                   json={"field": field, "context": context},
                                   headers=self.get_headers())
            if response.status_code == 200:
                self.llm_requests += 1
                self.actions_performed += 1
                return response.json().get("suggestion", {})
            return None
        except Exception as e:
            self.errors_encountered += 1
            return None
    
    def add_collaboration_note(self, question_id, note):
        try:
            response = requests.post(f"{API_URL}/api/sessions/{self.session_id}/questions/{question_id}/note",
                                   json={"note": note, "field_reference": "general"},
                                   headers=self.get_headers())
            if response.status_code == 200:
                self.collaboration_notes += 1
                self.actions_performed += 1
                return True
            return False
        except Exception as e:
            self.errors_encountered += 1
            return False

class SessionCollaborationTestSuite:
    def __init__(self):
        self.passed_tests = 0
        self.failed_tests = 0
        self.host_user = CollaborationTestUser(999)  # Special ID for host
        self.collaboration_users = []
        self.session_id = None
        self.session_code = None
        self.test_question_ids = []
        
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
    
    def setup_host_and_session(self):
        log("\n🏗️ Setting Up Host and Session", Colors.BOLD + Colors.YELLOW)
        log("-" * 40, Colors.YELLOW)
        
        # Login host
        host_login = self.host_user.login()
        self.assert_test(host_login, "Host Login", f"User: {self.host_user.username}")
        
        if not host_login:
            return False
        
        # Create collaborative template building session
        session_data = {
            "title": "Multi-User Template Building Test",
            "subject": "algorithms",
            "description": "Testing concurrent template building",
            "template_mode": True,
            "settings": {
                "max_participants": MAX_CONCURRENT_USERS + 2,
                "max_questions": 15,
                "allow_llm": True,
                "allow_user_questions": True,
                "question_numbering": True
            }
        }
        
        response = requests.post(f"{API_URL}/api/sessions/create",
                               json=session_data,
                               headers=self.host_user.get_headers())
        
        session_created = response.status_code == 201
        if session_created:
            session_info = response.json().get("session", {})
            self.session_id = session_info.get("session_id")
            self.session_code = session_info.get("session_code")
            self.host_user.session_id = self.session_id
            self.host_user.session_code = self.session_code
        
        self.assert_test(session_created, "Collaborative Session Creation",
                        f"Session Code: {self.session_code}" if session_created else "Failed")
        
        return session_created
    
    def create_collaboration_users(self):
        log(f"\n👥 Creating {MAX_CONCURRENT_USERS} Collaboration Users", Colors.BOLD + Colors.YELLOW)
        log("-" * 40, Colors.YELLOW)
        
        self.collaboration_users = []
        successful_logins = 0
        
        for i in range(MAX_CONCURRENT_USERS):
            user = CollaborationTestUser(i)
            if user.login():
                self.collaboration_users.append(user)
                successful_logins += 1
        
        self.assert_test(successful_logins >= MAX_CONCURRENT_USERS * 0.8,
                        "User Creation",
                        f"{successful_logins}/{MAX_CONCURRENT_USERS} users logged in successfully")
        
        return successful_logins > 0
    
    def test_concurrent_session_joining(self):
        log("\n🚪 Testing Concurrent Session Joining", Colors.BOLD + Colors.YELLOW)
        log("-" * 40, Colors.YELLOW)
        
        def join_session_worker(user):
            return user.join_session(self.session_code)
        
        # Join sessions concurrently
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_USERS) as executor:
            futures = [executor.submit(join_session_worker, user) for user in self.collaboration_users]
            join_results = [future.result() for future in as_completed(futures)]
        
        join_time = time.time() - start_time
        successful_joins = sum(join_results)
        
        self.assert_test(successful_joins >= len(self.collaboration_users) * 0.8,
                        "Concurrent Session Joining",
                        f"{successful_joins}/{len(self.collaboration_users)} users joined in {join_time:.2f}s")
        
        return successful_joins > 0
    
    def test_session_participant_limits(self):
        log("\n👨‍👩‍👧‍👦 Testing Session Participant Limits", Colors.BOLD + Colors.YELLOW)
        log("-" * 40, Colors.YELLOW)
        
        # Get current session data
        response = requests.get(f"{API_URL}/api/sessions/{self.session_id}",
                               headers=self.host_user.get_headers())
        
        if response.status_code == 200:
            session_data = response.json().get("session", {})
            current_participants = len(session_data.get("participants", []))
            max_participants = session_data.get("settings", {}).get("max_participants", 0)
            
            self.assert_test(current_participants <= max_participants,
                            "Participant Limit Enforcement",
                            f"{current_participants}/{max_participants} participants in session")
            
            self.assert_test(current_participants >= 2,
                            "Multiple Users in Session",
                            f"{current_participants} users successfully joined")
            
            return True
        
        return False
    
    def test_concurrent_question_building(self):
        log("\n🔨 Testing Concurrent Question Building", Colors.BOLD + Colors.YELLOW)
        log("-" * 40, Colors.YELLOW)
        
        question_types = ["multiple_choice", "open_ended", "coding", "true_false", "short_answer"]
        
        def build_question_concurrently(user_index):
            if user_index >= len(self.collaboration_users):
                return False
            
            user = self.collaboration_users[user_index]
            question_number = user_index + 1
            question_type = question_types[user_index % len(question_types)]
            
            # Start building question
            question_id = user.start_question_building(question_number, question_type)
            if not question_id:
                return False
            
            # Track question ID for later use
            self.test_question_ids.append(question_id)
            
            time.sleep(0.5)  # Simulate thinking time
            
            # Update question content
            success = user.update_question_content(question_id, "question_text", 
                                                 f"Question {question_number} by {user.username}")
            
            # Add collaboration note
            user.add_collaboration_note(question_id, f"Note from {user.username}: This is question {question_number}")
            
            return success
        
        # Build questions concurrently
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=min(5, len(self.collaboration_users))) as executor:
            futures = [executor.submit(build_question_concurrently, i) 
                      for i in range(min(5, len(self.collaboration_users)))]
            build_results = [future.result() for future in as_completed(futures)]
        
        build_time = time.time() - start_time
        successful_builds = sum(build_results)
        
        self.assert_test(successful_builds >= 3,
                        "Concurrent Question Building",
                        f"{successful_builds}/{min(5, len(self.collaboration_users))} questions started in {build_time:.2f}s")
        
        return successful_builds > 0
    
    def test_llm_integration_concurrent(self):
        log("\n🤖 Testing Concurrent LLM Requests", Colors.BOLD + Colors.YELLOW)
        log("-" * 40, Colors.YELLOW)
        
        if not self.test_question_ids:
            log("No question IDs available for LLM testing", Colors.YELLOW)
            return False
        
        def request_llm_concurrently(user):
            if not self.test_question_ids:
                return False
            
            question_id = random.choice(self.test_question_ids)
            contexts = [
                "Make this question more challenging",
                "Add beginner-friendly context",
                "Focus on practical applications",
                "Include real-world examples"
            ]
            
            context = random.choice(contexts)
            suggestion = user.request_llm_suggestion(question_id, "question_text", context)
            
            return suggestion is not None
        
        # Make concurrent LLM requests
        llm_users = self.collaboration_users[:min(4, len(self.collaboration_users))]
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(request_llm_concurrently, user) for user in llm_users]
            llm_results = [future.result() for future in as_completed(futures)]
        
        llm_time = time.time() - start_time
        successful_llm = sum(llm_results)
        
        self.assert_test(successful_llm >= len(llm_users) * 0.7,
                        "Concurrent LLM Requests",
                        f"{successful_llm}/{len(llm_users)} LLM requests succeeded in {llm_time:.2f}s")
        
        return successful_llm > 0
    
    def test_real_time_collaboration(self):
        log("\n💬 Testing Real-Time Collaboration Features", Colors.BOLD + Colors.YELLOW)
        log("-" * 40, Colors.YELLOW)
        
        def simulate_user_activity(user, duration=10):
            end_time = time.time() + duration
            activities = 0
            
            messages = [
                "Great question!",
                "I think we should add more detail here",
                "What about edge cases?",
                "This looks good to me",
                "Maybe we can simplify this"
            ]
            
            while time.time() < end_time:
                # Send random chat message
                message = random.choice(messages)
                if user.send_chat_message(message):
                    activities += 1
                
                time.sleep(random.uniform(1, 3))
            
            return activities
        
        # Simulate concurrent user activity
        active_users = self.collaboration_users[:min(4, len(self.collaboration_users))]
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=len(active_users)) as executor:
            futures = [executor.submit(simulate_user_activity, user, 8) for user in active_users]
            activity_results = [future.result() for future in as_completed(futures)]
        
        collaboration_time = time.time() - start_time
        total_activities = sum(activity_results)
        
        self.assert_test(total_activities >= len(active_users) * 2,
                        "Real-Time Collaboration",
                        f"{total_activities} collaborative activities in {collaboration_time:.2f}s")
        
        return total_activities > 0
    
    def test_host_finalization_workflow(self):
        log("\n👑 Testing Host Finalization Workflow", Colors.BOLD + Colors.YELLOW)
        log("-" * 40, Colors.YELLOW)
        
        if not self.test_question_ids:
            log("No questions to finalize", Colors.YELLOW)
            return False
        
        # Host finalizes questions
        finalized_count = 0
        for question_id in self.test_question_ids[:3]:  # Finalize first 3 questions
            response = requests.post(f"{API_URL}/api/sessions/{self.session_id}/questions/{question_id}/finalize",
                                   json={},
                                   headers=self.host_user.get_headers())
            if response.status_code == 200:
                finalized_count += 1
        
        self.assert_test(finalized_count >= 2,
                        "Host Question Finalization",
                        f"{finalized_count}/{min(3, len(self.test_question_ids))} questions finalized")
        
        # Test template conversion
        if finalized_count >= 2:
            template_data = {
                "template_name": "Collaborative Test Template",
                "description": "Template created through collaborative session",
                "is_public": True,
                "tags": ["collaborative", "test", "algorithms"]
            }
            
            response = requests.post(f"{API_URL}/api/sessions/{self.session_id}/convert-to-template",
                                   json=template_data,
                                   headers=self.host_user.get_headers())
            
            conversion_success = response.status_code == 201
            self.assert_test(conversion_success, "Session to Template Conversion",
                            "Successfully converted collaborative session to template")
            
            return finalized_count >= 2 and conversion_success
        
        return finalized_count >= 2
    
    def collect_user_statistics(self):
        log("\n📊 Collecting User Activity Statistics", Colors.BOLD + Colors.YELLOW)
        log("-" * 40, Colors.YELLOW)
        
        total_actions = 0
        total_errors = 0
        
        # Collect stats from all users including host
        all_users = [self.host_user] + self.collaboration_users
        
        for user in all_users:
            user_total = (user.actions_performed + user.questions_started + 
                         user.questions_updated + user.llm_requests + 
                         user.chat_messages + user.collaboration_notes)
            total_actions += user_total
            total_errors += user.errors_encountered
            
            if user_total > 0:  # Only log active users
                log(f"👤 {user.username}: {user_total} actions, {user.errors_encountered} errors", Colors.BLUE)
        
        error_rate = (total_errors / total_actions * 100) if total_actions > 0 else 0
        
        self.assert_test(error_rate < 10,
                        "Overall Error Rate",
                        f"{error_rate:.1f}% error rate across all users")
        
        self.assert_test(total_actions >= MAX_CONCURRENT_USERS * 3,
                        "User Activity Level",
                        f"{total_actions} total actions performed")
        
        return total_actions, total_errors
    
    def run_all_tests(self):
        log("🚀 STARTING SESSION COLLABORATION TEST SUITE", Colors.BOLD + Colors.CYAN)
        log("=" * 60, Colors.CYAN)
        
        start_time = time.time()
        
        try:
            # Setup phase
            if not self.setup_host_and_session():
                log("Cannot proceed without host and session", Colors.RED)
                return
            
            if not self.create_collaboration_users():
                log("Cannot proceed without collaboration users", Colors.RED)
                return
            
            # Test concurrent operations
            self.test_concurrent_session_joining()
            self.test_session_participant_limits()
            self.test_concurrent_question_building()
            self.test_llm_integration_concurrent()
            self.test_real_time_collaboration()
            self.test_host_finalization_workflow()
            
            # Collect statistics
            total_actions, total_errors = self.collect_user_statistics()
            
        except Exception as e:
            log(f"Test suite crashed: {e}", Colors.RED)
            import traceback
            traceback.print_exc()
        
        # Print final results
        total_time = time.time() - start_time
        total_tests = self.passed_tests + self.failed_tests
        pass_rate = (self.passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        log("\n" + "=" * 60, Colors.CYAN)
        log("🎯 SESSION COLLABORATION TEST RESULTS", Colors.BOLD + Colors.CYAN)
        log("=" * 60, Colors.CYAN)
        
        log(f"✅ Passed: {self.passed_tests}", Colors.GREEN)
        log(f"❌ Failed: {self.failed_tests}", Colors.RED)
        log(f"📊 Pass Rate: {pass_rate:.1f}%", Colors.YELLOW)
        log(f"⏱️ Total Time: {total_time:.2f} seconds", Colors.BLUE)
        log(f"👥 Users Tested: {len(self.collaboration_users) + 1}", Colors.MAGENTA)
        
        if pass_rate >= 90:
            log("🏆 EXCELLENT! Multi-user collaboration is working perfectly!", Colors.GREEN + Colors.BOLD)
        elif pass_rate >= 75:
            log("✨ GOOD! Minor collaboration issues to address", Colors.YELLOW + Colors.BOLD)
        else:
            log("🚨 NEEDS WORK! Collaboration system has issues", Colors.RED + Colors.BOLD)

if __name__ == "__main__":
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║           SESSION COLLABORATION TEST SUITE               ║")
    print("║                                                          ║")
    print(f"║  Users: {MAX_CONCURRENT_USERS:<3} | Duration: {SESSION_TEST_DURATION:<3}s | Real-time Collaboration    ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}\n")
    
    test_suite = SessionCollaborationTestSuite()
    test_suite.run_all_tests()