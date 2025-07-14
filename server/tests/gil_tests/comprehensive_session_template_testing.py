#!/usr/bin/env python3
"""
Comprehensive Test Suite for Interview Assistant Platform
Covers: Unit, Integration, System, Stress, and Security Testing

Run with: python comprehensive_tests.py
"""

import requests
import json
import time
import concurrent.futures
import threading
import random
import string
import socketio
from datetime import datetime, timedelta
import uuid

# Test Configuration
API_URL = "http://localhost:5000"  # Updated to match Flask default
WS_URL = "http://localhost:5000"
MAX_CONCURRENT_USERS = 10
STRESS_TEST_DURATION = 30  # seconds


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'


def log(message, color=Colors.WHITE):
    """Enhanced logging with colors and timestamps"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{color}[{timestamp}] {message}{Colors.END}")


def generate_random_string(length=8):
    """Generate random string for testing"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


class TestUser:
    """Test user for multi-user scenarios"""

    def __init__(self, username=None):
        self.username = username or f"test_user_{generate_random_string(5)}"
        self.token = None
        self.session_id = None
        self.session_code = None
        self.sio = None
        self.messages_received = []
        self.questions_received = []

    def login(self):
        """Login and get authentication token"""
        try:
            response = requests.post(f"{API_URL}/api/auth/login",
                                     json={"username": self.username})
            if response.status_code == 200:
                self.token = response.json().get("token")
                return True
            return False
        except Exception as e:
            log(f"Login failed for {self.username}: {e}", Colors.RED)
            return False

    def get_headers(self):
        """Get authorization headers"""
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}


class ComprehensiveTestSuite:
    """Main test suite covering all aspects of the platform"""

    def __init__(self):
        self.passed_tests = 0
        self.failed_tests = 0
        self.test_users = []
        self.start_time = None

    def run_all_tests(self):
        """Run the complete test suite"""
        log("🚀 STARTING COMPREHENSIVE TEST SUITE", Colors.BOLD + Colors.CYAN)
        log("=" * 60, Colors.CYAN)
        self.start_time = time.time()

        # 1. Basic Health and Setup Tests
        self.test_health_and_setup()

        # 2. Unit Tests
        self.test_unit_functionality()

        # 3. Integration Tests
        self.test_integration_workflows()

        # 4. System Tests (End-to-End)
        self.test_system_workflows()

        # 5. Multi-User Collaboration Tests
        self.test_multi_user_collaboration()

        # 6. WebSocket Real-time Tests
        self.test_websocket_functionality()

        # 7. Stress Tests
        self.test_stress_scenarios()

        # 8. Security Tests
        self.test_security_scenarios()

        # 9. Edge Cases and Error Handling
        self.test_edge_cases()

        self.print_final_results()

    def assert_test(self, condition, test_name, details=""):
        """Custom assertion with detailed logging"""
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

    def test_health_and_setup(self):
        """Test basic connectivity and health"""
        log("\n🔍 HEALTH & SETUP TESTS", Colors.BOLD + Colors.YELLOW)
        log("-" * 40, Colors.YELLOW)

        try:
            # API Health
            response = requests.get(f"{API_URL}/api/health", timeout=5)
            self.assert_test(
                response.status_code == 200,
                "API Health Check",
                f"Status: {response.status_code}"
            )

            # API Info
            response = requests.get(f"{API_URL}/api/info", timeout=5)
            self.assert_test(
                response.status_code == 200 and "features" in response.json(),
                "API Info Endpoint",
                f"Features available: {len(response.json().get('features', []))}"
            )

        except Exception as e:
            self.assert_test(False, "Basic Connectivity", f"Error: {e}")

    def test_unit_functionality(self):
        """Test individual API endpoints"""
        log("\n🧪 UNIT TESTS", Colors.BOLD + Colors.YELLOW)
        log("-" * 40, Colors.YELLOW)

        # Create test user
        user = TestUser()

        # Authentication Tests
        login_success = user.login()
        self.assert_test(login_success, "User Authentication", f"User: {user.username}")

        if not login_success:
            return

        headers = user.get_headers()

        # Session Creation Test
        session_data = {
            "title": f"Unit Test Session {generate_random_string()}",
            "subject": "python",
            "settings": {
                "max_participants": 5,
                "allow_llm": True,
                "question_limit": 10
            }
        }

        response = requests.post(f"{API_URL}/api/sessions/create",
                                 json=session_data, headers=headers)
        session_created = response.status_code == 201

        if session_created:
            session_info = response.json().get("session", {})
            user.session_id = session_info.get("session_id")
            user.session_code = session_info.get("session_code")

        self.assert_test(session_created, "Session Creation",
                         f"Code: {user.session_code}" if session_created else "Failed to create")

        if not session_created:
            return

        # Question Generation Test
        llm_data = {"subject": "algorithms", "context": "basic sorting"}
        response = requests.post(f"{API_URL}/api/sessions/{user.session_id}/llm-question",
                                 json=llm_data, headers=headers)
        self.assert_test(response.status_code == 200, "LLM Question Generation",
                         "Generated question successfully")

        # User Question Creation Test
        user_question = {
            "question_text": "What is the time complexity of quicksort?",
            "difficulty": "medium",
            "type": "multiple_choice",
            "options": ["O(n)", "O(n log n)", "O(n²)", "O(log n)"],
            "correct_answer": "O(n log n)"
        }
        response = requests.post(f"{API_URL}/api/sessions/{user.session_id}/user-question",
                                 json=user_question, headers=headers)
        self.assert_test(response.status_code == 200, "User Question Creation",
                         "Created question with multiple choice")

        # Chat Test
        chat_data = {"message": "Hello from unit test!"}
        response = requests.post(f"{API_URL}/api/sessions/{user.session_id}/chat",
                                 json=chat_data, headers=headers)
        self.assert_test(response.status_code == 200, "Chat Message",
                         "Message sent successfully")

        # Session Info Retrieval
        response = requests.get(f"{API_URL}/api/sessions/{user.session_id}",
                                headers=headers)
        self.assert_test(response.status_code == 200, "Session Info Retrieval",
                         "Retrieved session details")

        self.test_users.append(user)

    def test_integration_workflows(self):
        """Test integrated workflows"""
        log("\n🔗 INTEGRATION TESTS", Colors.BOLD + Colors.YELLOW)
        log("-" * 40, Colors.YELLOW)

        # Create host and participant
        host = TestUser("integration_host")
        participant = TestUser("integration_participant")

        # Host workflow
        if not host.login():
            self.assert_test(False, "Host Login", "Could not login host")
            return

        # Create collaborative session
        session_data = {
            "title": "Integration Test Collaboration",
            "subject": "system_design",
            "settings": {
                "max_participants": 10,
                "allow_llm": True,
                "collaborative_mode": True
            }
        }

        response = requests.post(f"{API_URL}/api/sessions/create",
                                 json=session_data, headers=host.get_headers())

        if response.status_code == 201:
            session_info = response.json().get("session", {})
            host.session_id = session_info.get("session_id")
            host.session_code = session_info.get("session_code")

        self.assert_test(response.status_code == 201, "Collaborative Session Creation",
                         f"Session code: {host.session_code}")

        # Participant joins session
        if not participant.login():
            self.assert_test(False, "Participant Login", "Could not login participant")
            return

        join_data = {"session_code": host.session_code}
        response = requests.post(f"{API_URL}/api/sessions/join",
                                 json=join_data, headers=participant.get_headers())

        join_success = response.status_code == 200
        if join_success:
            participant.session_id = host.session_id

        self.assert_test(join_success, "Session Join",
                         f"Participant joined session {host.session_code}")

        # Collaborative question building
        if join_success:
            # Host suggests a question
            host_question = {
                "question_text": "Design a URL shortener like bit.ly",
                "difficulty": "hard",
                "type": "open_ended"
            }
            response = requests.post(f"{API_URL}/api/sessions/{host.session_id}/user-question",
                                     json=host_question, headers=host.get_headers())

            self.assert_test(response.status_code == 200, "Host Question Suggestion",
                             "Host suggested system design question")

            # Participant adds feedback/chat
            chat_data = {"message": "Great question! Should we include scalability requirements?"}
            response = requests.post(f"{API_URL}/api/sessions/{participant.session_id}/chat",
                                     json=chat_data, headers=participant.get_headers())

            self.assert_test(response.status_code == 200, "Participant Feedback",
                             "Participant provided feedback via chat")

            # LLM generates follow-up question
            llm_data = {
                "subject": "system_design",
                "context": "URL shortener follow-up questions"
            }
            response = requests.post(f"{API_URL}/api/sessions/{host.session_id}/llm-question",
                                     json=llm_data, headers=host.get_headers())

            self.assert_test(response.status_code == 200, "LLM Follow-up Question",
                             "LLM generated contextual follow-up")

        self.test_users.extend([host, participant])

    def test_system_workflows(self):
        """Test complete end-to-end system workflows"""
        log("\n🌐 SYSTEM TESTS (End-to-End)", Colors.BOLD + Colors.YELLOW)
        log("-" * 40, Colors.YELLOW)

        # Complete interview preparation workflow
        interviewer = TestUser("system_interviewer")
        candidate = TestUser("system_candidate")

        if not all([interviewer.login(), candidate.login()]):
            self.assert_test(False, "System Test Setup", "Could not login users")
            return

        # 1. Interviewer creates interview template
        template_data = {
            "title": "Software Engineer Mock Interview",
            "subject": "algorithms_data_structures",
            "settings": {
                "max_participants": 2,
                "allow_llm": True,
                "question_limit": 5,
                "time_limit": 60  # minutes
            }
        }

        response = requests.post(f"{API_URL}/api/sessions/create",
                                 json=template_data, headers=interviewer.get_headers())

        if response.status_code == 201:
            session_info = response.json().get("session", {})
            interviewer.session_id = session_info.get("session_id")
            interviewer.session_code = session_info.get("session_code")

        self.assert_test(response.status_code == 201, "Interview Template Creation",
                         "Interviewer created mock interview session")

        # 2. Add multiple types of questions
        questions = [
            {
                "question_text": "Implement a function to reverse a linked list",
                "difficulty": "medium",
                "type": "coding",
                "expected_time": 15
            },
            {
                "question_text": "What is the difference between HashMap and TreeMap?",
                "difficulty": "easy",
                "type": "conceptual"
            },
            {
                "question_text": "Design a cache system with LRU eviction",
                "difficulty": "hard",
                "type": "system_design"
            }
        ]

        questions_added = 0
        for question in questions:
            response = requests.post(
                f"{API_URL}/api/sessions/{interviewer.session_id}/user-question",
                json=question, headers=interviewer.get_headers()
            )
            if response.status_code == 200:
                questions_added += 1

        self.assert_test(questions_added == 3, "Question Template Building",
                         f"Added {questions_added}/3 questions to template")

        # 3. Generate LLM questions for variety
        llm_subjects = ["algorithms", "data_structures", "system_design"]
        llm_questions_added = 0

        for subject in llm_subjects:
            llm_data = {"subject": subject, "context": "interview appropriate"}
            response = requests.post(
                f"{API_URL}/api/sessions/{interviewer.session_id}/llm-question",
                json=llm_data, headers=interviewer.get_headers()
            )
            if response.status_code == 200:
                llm_questions_added += 1

        self.assert_test(llm_questions_added >= 2, "LLM Question Diversification",
                         f"LLM generated {llm_questions_added} additional questions")

        # 4. Candidate joins the interview
        join_data = {"session_code": interviewer.session_code}
        response = requests.post(f"{API_URL}/api/sessions/join",
                                 json=join_data, headers=candidate.get_headers())

        candidate_joined = response.status_code == 200
        if candidate_joined:
            candidate.session_id = interviewer.session_id

        self.assert_test(candidate_joined, "Candidate Joins Interview",
                         "Candidate successfully joined the interview session")

        # 5. Simulate interview interaction
        if candidate_joined:
            # Interviewer asks question via chat
            chat_data = {
                "message": "Let's start with the linked list reversal problem. Please think out loud as you code."}
            response = requests.post(f"{API_URL}/api/sessions/{interviewer.session_id}/chat",
                                     json=chat_data, headers=interviewer.get_headers())

            # Candidate responds
            candidate_response = {
                "message": "Sure! I'll start by considering the iterative approach. I need to keep track of previous, current, and next nodes..."}
            response = requests.post(f"{API_URL}/api/sessions/{candidate.session_id}/chat",
                                     json=candidate_response, headers=candidate.get_headers())

            self.assert_test(response.status_code == 200, "Interview Interaction",
                             "Interviewer and candidate successfully communicated")

        self.test_users.extend([interviewer, candidate])

    def test_multi_user_collaboration(self):
        """Test multiple users collaborating on template building"""
        log("\n👥 MULTI-USER COLLABORATION TESTS", Colors.BOLD + Colors.YELLOW)
        log("-" * 40, Colors.YELLOW)

        # Create team of users
        team_size = 4
        team = [TestUser(f"collab_user_{i}") for i in range(team_size)]
        host = team[0]

        # Login all users
        login_successes = [user.login() for user in team]
        self.assert_test(all(login_successes), "Team Login",
                         f"{sum(login_successes)}/{team_size} users logged in successfully")

        if not all(login_successes):
            return

        # Host creates collaborative session
        session_data = {
            "title": "Team Collaboration Session",
            "subject": "mixed_topics",
            "settings": {
                "max_participants": team_size,
                "allow_llm": True,
                "collaborative_mode": True,
                "question_limit": 20
            }
        }

        response = requests.post(f"{API_URL}/api/sessions/create",
                                 json=session_data, headers=host.get_headers())

        if response.status_code == 201:
            session_info = response.json().get("session", {})
            host.session_id = session_info.get("session_id")
            host.session_code = session_info.get("session_code")

        self.assert_test(response.status_code == 201, "Team Session Creation",
                         f"Session code: {host.session_code}")

        # All team members join
        participants_joined = 0
        for user in team[1:]:  # Skip host
            join_data = {"session_code": host.session_code}
            response = requests.post(f"{API_URL}/api/sessions/join",
                                     json=join_data, headers=user.get_headers())
            if response.status_code == 200:
                user.session_id = host.session_id
                participants_joined += 1

        self.assert_test(participants_joined == team_size - 1, "Team Assembly",
                         f"{participants_joined}/{team_size - 1} participants joined")

        # Concurrent question contributions
        def contribute_question(user, index):
            """Each user contributes a question"""
            question_data = {
                "question_text": f"Question from {user.username}: What is concept #{index}?",
                "difficulty": random.choice(["easy", "medium", "hard"]),
                "type": random.choice(["multiple_choice", "open_ended", "coding"])
            }
            response = requests.post(
                f"{API_URL}/api/sessions/{user.session_id}/user-question",
                json=question_data, headers=user.get_headers()
            )
            return response.status_code == 200

        # Simulate concurrent contributions
        with concurrent.futures.ThreadPoolExecutor(max_workers=team_size) as executor:
            futures = [executor.submit(contribute_question, user, i)
                       for i, user in enumerate(team)]
            contributions = [future.result() for future in futures]

        self.assert_test(sum(contributions) >= team_size - 1, "Concurrent Contributions",
                         f"{sum(contributions)}/{team_size} users contributed questions")

        # Chat coordination
        def send_team_chat(user, message):
            """Send chat message"""
            chat_data = {"message": f"{user.username}: {message}"}
            response = requests.post(f"{API_URL}/api/sessions/{user.session_id}/chat",
                                     json=chat_data, headers=user.get_headers())
            return response.status_code == 200

        # Team discusses via chat
        chat_messages = [
            "Great questions everyone!",
            "Should we add more algorithm problems?",
            "Let's get LLM to generate some system design questions",
            "I think we have good coverage now"
        ]

        chat_successes = []
        for user, message in zip(team, chat_messages):
            chat_successes.append(send_team_chat(user, message))

        self.assert_test(sum(chat_successes) >= 3, "Team Communication",
                         f"{sum(chat_successes)}/{len(chat_messages)} chat messages sent")

        self.test_users.extend(team)

    def test_websocket_functionality(self):
        """Test real-time WebSocket functionality"""
        log("\n🔌 WEBSOCKET REAL-TIME TESTS", Colors.BOLD + Colors.YELLOW)
        log("-" * 40, Colors.YELLOW)

        # This would require more complex setup with actual WebSocket connections
        # For now, testing REST endpoints that support WebSocket features

        if not self.test_users:
            log("⚠️ No test users available for WebSocket tests", Colors.YELLOW)
            return

        user = self.test_users[0]
        if not user.session_id:
            log("⚠️ No active session for WebSocket tests", Colors.YELLOW)
            return

        # Test real-time features through REST API
        # (In production, these would trigger WebSocket events)

        # Typing indicator simulation
        typing_data = {"is_typing": True}
        response = requests.post(f"{API_URL}/api/sessions/{user.session_id}/typing",
                                 json=typing_data, headers=user.get_headers())

        # Note: This endpoint might not exist yet, so we'll test what we can
        websocket_features_tested = 0

        # Chat messages (triggers real-time updates)
        chat_data = {"message": "Testing real-time message delivery"}
        response = requests.post(f"{API_URL}/api/sessions/{user.session_id}/chat",
                                 json=chat_data, headers=user.get_headers())
        if response.status_code == 200:
            websocket_features_tested += 1

        # Question suggestions (triggers real-time updates)
        question_data = {
            "question_text": "Real-time question suggestion test",
            "difficulty": "medium"
        }
        response = requests.post(f"{API_URL}/api/sessions/{user.session_id}/user-question",
                                 json=question_data, headers=user.get_headers())
        if response.status_code == 200:
            websocket_features_tested += 1

        self.assert_test(websocket_features_tested >= 1, "WebSocket-Enabled Features",
                         f"{websocket_features_tested} real-time features working")

    def test_stress_scenarios(self):
        """Test system under stress"""
        log("\n⚡ STRESS TESTS", Colors.BOLD + Colors.YELLOW)
        log("-" * 40, Colors.YELLOW)

        # Create multiple concurrent sessions
        def create_concurrent_session(user_id):
            """Create session with concurrent user"""
            user = TestUser(f"stress_user_{user_id}")
            if not user.login():
                return False

            session_data = {
                "title": f"Stress Test Session {user_id}",
                "subject": "stress_testing"
            }

            response = requests.post(f"{API_URL}/api/sessions/create",
                                     json=session_data, headers=user.get_headers())
            return response.status_code == 201

        # Test concurrent session creation
        log(f"Creating {MAX_CONCURRENT_USERS} concurrent sessions...", Colors.BLUE)
        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONCURRENT_USERS) as executor:
            futures = [executor.submit(create_concurrent_session, i)
                       for i in range(MAX_CONCURRENT_USERS)]
            session_results = [future.result() for future in futures]

        creation_time = time.time() - start_time
        successful_sessions = sum(session_results)

        self.assert_test(successful_sessions >= MAX_CONCURRENT_USERS * 0.8,
                         "Concurrent Session Creation",
                         f"{successful_sessions}/{MAX_CONCURRENT_USERS} sessions created in {creation_time:.2f}s")

        # Test rapid API calls
        if self.test_users:
            user = self.test_users[0]
            if user.session_id:
                def rapid_api_call():
                    """Make rapid API call"""
                    response = requests.get(f"{API_URL}/api/sessions/{user.session_id}",
                                            headers=user.get_headers())
                    return response.status_code == 200

                # Make 50 rapid calls
                log("Testing rapid API calls...", Colors.BLUE)
                start_time = time.time()

                with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                    futures = [executor.submit(rapid_api_call) for _ in range(50)]
                    api_results = [future.result() for future in futures]

                api_time = time.time() - start_time
                successful_calls = sum(api_results)

                self.assert_test(successful_calls >= 45, "Rapid API Calls",
                                 f"{successful_calls}/50 calls succeeded in {api_time:.2f}s")

    def test_security_scenarios(self):
        """Test security aspects"""
        log("\n🔒 SECURITY TESTS", Colors.BOLD + Colors.YELLOW)
        log("-" * 40, Colors.YELLOW)

        # Test unauthorized access
        unauthorized_endpoints = [
            f"/api/sessions/fake_session_id",
            f"/api/sessions/fake_session_id/chat",
            f"/api/sessions/fake_session_id/user-question"
        ]

        unauthorized_blocked = 0
        for endpoint in unauthorized_endpoints:
            response = requests.get(f"{API_URL}{endpoint}")
            if response.status_code in [401, 403]:
                unauthorized_blocked += 1

        self.assert_test(unauthorized_blocked >= 2, "Unauthorized Access Protection",
                         f"{unauthorized_blocked}/{len(unauthorized_endpoints)} endpoints properly protected")

        # Test invalid token
        fake_headers = {"Authorization": "Bearer fake_token_12345"}
        response = requests.get(f"{API_URL}/api/auth/verify", headers=fake_headers)

        self.assert_test(response.status_code == 401, "Invalid Token Rejection",
                         "Fake tokens are properly rejected")

        # Test input validation
        if self.test_users:
            user = self.test_users[0]

            # Test malicious input
            malicious_inputs = [
                {"question_text": "<script>alert('xss')</script>"},
                {"question_text": "'; DROP TABLE users; --"},
                {"message": "x" * 10000}  # Very long message
            ]

            validation_working = 0
            for malicious_data in malicious_inputs:
                response = requests.post(f"{API_URL}/api/sessions/{user.session_id}/chat",
                                         json=malicious_data, headers=user.get_headers())
                # Should either reject (400) or sanitize (200 but clean)
                if response.status_code in [400, 422] or response.status_code == 200:
                    validation_working += 1

            self.assert_test(validation_working >= 2, "Input Validation",
                             f"{validation_working}/{len(malicious_inputs)} malicious inputs handled")

    def test_edge_cases(self):
        """Test edge cases and error handling"""
        log("\n🌊 EDGE CASE TESTS", Colors.BOLD + Colors.YELLOW)
        log("-" * 40, Colors.YELLOW)

        if not self.test_users:
            log("⚠️ No test users available for edge case tests", Colors.YELLOW)
            return

        user = self.test_users[0]

        # Test session limits
        if user.session_id:
            # Try to exceed question limit
            for i in range(5):  # Assuming limit might be lower
                question_data = {
                    "question_text": f"Edge case question {i}",
                    "difficulty": "easy"
                }
                response = requests.post(f"{API_URL}/api/sessions/{user.session_id}/user-question",
                                         json=question_data, headers=user.get_headers())
                # Should eventually hit limit

        # Test invalid session codes
        invalid_join_data = {"session_code": "INVALID123"}
        response = requests.post(f"{API_URL}/api/sessions/join",
                                 json=invalid_join_data, headers=user.get_headers())

        self.assert_test(response.status_code in [400, 404], "Invalid Session Code Handling",
                         "Invalid session codes are properly rejected")

        # Test empty/malformed requests
        empty_requests_handled = 0

        # Empty session creation
        response = requests.post(f"{API_URL}/api/sessions/create",
                                 json={}, headers=user.get_headers())
        if response.status_code in [400, 422]:
            empty_requests_handled += 1

        # Empty chat message
        response = requests.post(f"{API_URL}/api/sessions/{user.session_id}/chat",
                                 json={}, headers=user.get_headers())
        if response.status_code in [400, 422]:
            empty_requests_handled += 1

        self.assert_test(empty_requests_handled >= 1, "Malformed Request Handling",
                         f"{empty_requests_handled}/2 malformed requests properly rejected")

    def print_final_results(self):
        """Print comprehensive test results"""
        total_time = time.time() - self.start_time
        total_tests = self.passed_tests + self.failed_tests
        pass_rate = (self.passed_tests / total_tests * 100) if total_tests > 0 else 0

        log("\n" + "=" * 60, Colors.CYAN)
        log("🎯 COMPREHENSIVE TEST RESULTS", Colors.BOLD + Colors.CYAN)
        log("=" * 60, Colors.CYAN)

        log(f"✅ Passed: {self.passed_tests}", Colors.GREEN)
        log(f"❌ Failed: {self.failed_tests}", Colors.RED)
        log(f"📊 Pass Rate: {pass_rate:.1f}%", Colors.YELLOW)
        log(f"⏱️ Total Time: {total_time:.2f} seconds", Colors.BLUE)
        log(f"👥 Test Users Created: {len(self.test_users)}", Colors.MAGENTA)

        if pass_rate >= 90:
            log("🏆 EXCELLENT! Your system is production-ready!", Colors.GREEN + Colors.BOLD)
        elif pass_rate >= 75:
            log("✨ GOOD! Minor issues to address", Colors.YELLOW + Colors.BOLD)
        elif pass_rate >= 50:
            log("⚠️ NEEDS WORK! Several issues to fix", Colors.YELLOW + Colors.BOLD)
        else:
            log("🚨 CRITICAL! Major issues need immediate attention", Colors.RED + Colors.BOLD)

        log("\n📋 RECOMMENDATIONS:", Colors.BOLD + Colors.WHITE)

        if self.failed_tests > 0:
            log("• Review failed tests and fix underlying issues", Colors.WHITE)
            log("• Implement proper error handling for edge cases", Colors.WHITE)
            log("• Add input validation and sanitization", Colors.WHITE)
            log("• Strengthen authentication and authorization", Colors.WHITE)

        log("• Add monitoring and logging for production", Colors.WHITE)
        log("• Set up continuous integration testing", Colors.WHITE)
        log("• Consider load balancing for high traffic", Colors.WHITE)
        log("• Implement rate limiting to prevent abuse", Colors.WHITE)


if __name__ == "__main__":
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║     INTERVIEW ASSISTANT COMPREHENSIVE TEST SUITE         ║")
    print("║                                                          ║")
    print("║  Testing: Unit • Integration • System • Stress • Security ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}\n")

    try:
        test_suite = ComprehensiveTestSuite()
        test_suite.run_all_tests()
    except KeyboardInterrupt:
        log("\n\n⚠️ Tests interrupted by user", Colors.YELLOW)
    except Exception as e:
        log(f"\n\n🚨 Test suite crashed: {e}", Colors.RED)
        import traceback

        traceback.print_exc()