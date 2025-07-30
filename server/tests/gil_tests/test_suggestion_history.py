#!/usr/bin/env python3
"""
Test suite for suggestion history functionality
Tests that accepted/rejected suggestions are properly stored and can be retrieved by hosts.
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

class SuggestionHistoryTestSuite:
    def __init__(self):
        self.passed_tests = 0
        self.failed_tests = 0
        
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
        """Create and authenticate a test user"""
        username = f"hist_{username_suffix}_{uuid.uuid4().hex[:6]}"
        
        try:
            response = requests.post(f"{API_URL}/api/auth/login",
                                   json={"username": username},
                                   timeout=10)
            
            if response.status_code == 200:
                auth_data = response.json()
                return {
                    "username": username,
                    "token": auth_data.get("token"),
                    "headers": {"Authorization": f"Bearer {auth_data.get('token')}"}
                }
            else:
                log(f"Authentication failed for {username}: {response.status_code} - {response.text}", Colors.RED)
                return None
        except Exception as e:
            log(f"Authentication error for {username}: {e}", Colors.RED)
            return None
    
    def create_test_session(self, user):
        """Create a test session for suggestion testing"""
        session_data = {
            "title": f"Suggestion History Test Session by {user['username']}",
            "subject": "general",
            "description": "Testing suggestion history functionality",
            "template_mode": True,
            "settings": {
                "max_participants": 10,
                "max_questions": 20,
                "allow_llm": True,
                "allow_user_questions": True
            }
        }
        
        response = requests.post(f"{API_URL}/api/sessions/create",
                               json=session_data,
                               headers=user["headers"],
                               timeout=15)
        
        if response.status_code == 201:
            session_info = response.json().get("session", {})
            return session_info.get("session_id"), session_info
        return None, None
    
    def test_suggestion_history_workflow(self):
        log("\\n📜 Testing Complete Suggestion History Workflow", Colors.BOLD + Colors.YELLOW)
        log("-" * 60, Colors.YELLOW)
        
        # Create host and participant users
        host = self.create_test_user("host")
        participant = self.create_test_user("participant")
        
        self.assert_test(host is not None, "Host User Creation")
        self.assert_test(participant is not None, "Participant User Creation")
        
        if not host or not participant:
            return False
        
        # Host creates session
        session_id, session_info = self.create_test_session(host)
        session_code = session_info.get("session_code") if session_info else None
        
        self.assert_test(session_id is not None, "Session Creation",
                        f"Session code: {session_code}")
        
        if not session_id:
            return False
        
        # Participant joins session
        response = requests.post(f"{API_URL}/api/sessions/join/{session_code}",
                               headers=participant["headers"],
                               timeout=15)
        
        self.assert_test(response.status_code == 200, "Participant Session Join")
        
        # Host creates a question
        response = requests.post(f"{API_URL}/api/sessions/{session_id}/questions/1/start",
                               json={"type": "open_ended"},
                               headers=host["headers"],
                               timeout=15)
        
        self.assert_test(response.status_code == 200, "Question Creation")
        
        if response.status_code != 200:
            return False
        
        question_id = response.json().get("question", {}).get("question_id")
        log(f"Debug - Question ID created: {question_id}", Colors.WHITE)
        
        # Check if question exists in session before making suggestions
        debug_response = requests.get(f"{API_URL}/api/sessions/{session_id}/debug",
                                    headers=host["headers"],
                                    timeout=15)
        if debug_response.status_code == 200:
            debug_data = debug_response.json()
            log(f"Debug - After question creation - Questions queue: {len(debug_data.get('questions_queue', []))}", Colors.WHITE)
        
        # Participant makes multiple suggestions
        suggestions_made = []
        
        # Suggestion 1: question_text
        suggestion_1_data = {
            "field": "question_text",
            "suggested_value": "What is the time complexity of quicksort algorithm?",
            "current_value": ""
        }
        response = requests.post(f"{API_URL}/api/sessions/{session_id}/questions/{question_id}/suggest",
                               json=suggestion_1_data,
                               headers=participant["headers"],
                               timeout=15)
        
        if response.status_code == 200:
            suggestion_1_id = response.json().get("suggestion", {}).get("suggestion_id")
            suggestions_made.append(("question_text", suggestion_1_id))
        
        # Suggestion 2: sample_answer  
        suggestion_2_data = {
            "field": "sample_answer",
            "suggested_value": "O(n log n) average case, O(n²) worst case",
            "current_value": ""
        }
        response = requests.post(f"{API_URL}/api/sessions/{session_id}/questions/{question_id}/suggest",
                               json=suggestion_2_data,
                               headers=participant["headers"],
                               timeout=15)
        
        if response.status_code == 200:
            suggestion_2_id = response.json().get("suggestion", {}).get("suggestion_id")
            suggestions_made.append(("sample_answer", suggestion_2_id))
        
        # Suggestion 3: grading_criteria
        suggestion_3_data = {
            "field": "grading_criteria", 
            "suggested_value": "- Correct time complexity (3 pts)\\n- Explanation of algorithm (2 pts)",
            "current_value": ""
        }
        response = requests.post(f"{API_URL}/api/sessions/{session_id}/questions/{question_id}/suggest",
                               json=suggestion_3_data,
                               headers=participant["headers"],
                               timeout=15)
        
        if response.status_code == 200:
            suggestion_3_id = response.json().get("suggestion", {}).get("suggestion_id")
            suggestions_made.append(("grading_criteria", suggestion_3_id))
        
        self.assert_test(len(suggestions_made) >= 2, "Multiple Suggestions Created",
                        f"Created {len(suggestions_made)}/3 suggestions")
        
        # Host accepts some suggestions and rejects others
        handled_suggestions = 0
        
        for i, (field, suggestion_id) in enumerate(suggestions_made):
            action = "accept" if i % 2 == 0 else "reject"  # Accept even indices, reject odd
            
            response = requests.put(f"{API_URL}/api/sessions/{session_id}/questions/{question_id}/suggestions/{suggestion_id}",
                                  json={"action": action},
                                  headers=host["headers"],
                                  timeout=15)
            
            if response.status_code == 200:
                handled_suggestions += 1
                log(f"   {action.title()}ed suggestion for {field}", Colors.WHITE)
        
        self.assert_test(handled_suggestions >= 2, "Suggestions Handled by Host",
                        f"Handled {handled_suggestions}/{len(suggestions_made)} suggestions")
        
        # Wait a moment for database updates
        time.sleep(0.5)
        
        # Debug: Check session data before fetching history
        debug_response = requests.get(f"{API_URL}/api/sessions/{session_id}/debug",
                                    headers=host["headers"],
                                    timeout=15)
        if debug_response.status_code == 200:
            debug_data = debug_response.json()
            log(f"Debug - Questions queue length: {len(debug_data.get('questions_queue', []))}", Colors.WHITE)
            log(f"Debug - Ready questions length: {len(debug_data.get('ready_questions', []))}", Colors.WHITE)
        
        # Test suggestion history endpoint
        response = requests.get(f"{API_URL}/api/sessions/{session_id}/suggestions/history",
                              headers=host["headers"],
                              timeout=15)
        
        self.assert_test(response.status_code == 200, "Suggestion History API Access")
        
        if response.status_code == 200:
            history_data = response.json()
            suggestion_history = history_data.get("suggestion_history", [])
            total_suggestions = history_data.get("total_suggestions", 0)
            
            # Debug log
            log(f"Debug - History response: {json.dumps(history_data, indent=2)[:500]}...", Colors.WHITE)
            
            self.assert_test(len(suggestion_history) >= 2, "Suggestion History Contains Handled Suggestions",
                            f"Found {len(suggestion_history)} handled suggestions")
            
            self.assert_test(total_suggestions == len(suggestion_history), "Total Count Matches History Length")
            
            # Verify suggestion history contains expected data
            if suggestion_history:
                first_suggestion = suggestion_history[0]
                required_fields = ["question_number", "question_id", "suggestion_id", "field", 
                                 "suggested_value", "author", "status", "handled_by", "timestamp", "handled_at"]
                
                missing_fields = [field for field in required_fields if field not in first_suggestion]
                self.assert_test(len(missing_fields) == 0, "Suggestion History Contains All Required Fields",
                                f"Missing fields: {missing_fields}" if missing_fields else "All fields present")
                
                # Check that only handled suggestions are in history
                statuses = [s.get("status") for s in suggestion_history]
                valid_statuses = all(status in ["accept", "reject"] for status in statuses)
                self.assert_test(valid_statuses, "History Contains Only Handled Suggestions",
                                f"Statuses found: {statuses}")
                
                # Check that suggestions are sorted by handled_at (most recent first)
                handled_times = [s.get("handled_at") for s in suggestion_history if s.get("handled_at")]
                is_sorted = all(handled_times[i] >= handled_times[i+1] for i in range(len(handled_times)-1))
                self.assert_test(is_sorted, "Suggestion History Sorted by Handled Time")
        
        # Test that non-host cannot access suggestion history
        response = requests.get(f"{API_URL}/api/sessions/{session_id}/suggestions/history",  
                              headers=participant["headers"],
                              timeout=15)
        
        self.assert_test(response.status_code == 403, "Non-Host Cannot Access Suggestion History",
                        f"Response status: {response.status_code}")
        
        # Cleanup: Delete the test session
        try:
            requests.delete(f"{API_URL}/api/sessions/{session_id}",
                          headers=host["headers"], timeout=10)
        except:
            pass  # Ignore cleanup errors
        
        return True
    
    def test_suggestion_history_edge_cases(self):
        log("\\n🔍 Testing Suggestion History Edge Cases", Colors.BOLD + Colors.YELLOW)
        log("-" * 60, Colors.YELLOW)
        
        # Create test user
        host = self.create_test_user("edge_case_host")
        self.assert_test(host is not None, "Edge Case Host User Creation")
        
        if not host:
            return False
        
        # Create session  
        session_id, session_info = self.create_test_session(host)
        self.assert_test(session_id is not None, "Edge Case Session Creation")
        
        if not session_id:
            return False
        
        # Test empty suggestion history
        response = requests.get(f"{API_URL}/api/sessions/{session_id}/suggestions/history",
                              headers=host["headers"],
                              timeout=15)
        
        self.assert_test(response.status_code == 200, "Empty Suggestion History Request")
        
        if response.status_code == 200:
            history_data = response.json()
            suggestion_history = history_data.get("suggestion_history", [])
            total_suggestions = history_data.get("total_suggestions", 0)
            
            self.assert_test(len(suggestion_history) == 0, "Empty History Returns Empty List")
            self.assert_test(total_suggestions == 0, "Empty History Returns Zero Count")
        
        # Test suggestion history for non-existent session
        fake_session_id = str(uuid.uuid4())
        response = requests.get(f"{API_URL}/api/sessions/{fake_session_id}/suggestions/history",
                              headers=host["headers"], 
                              timeout=15)
        
        self.assert_test(response.status_code == 404, "Non-Existent Session Returns 404")
        
        # Cleanup
        try:
            requests.delete(f"{API_URL}/api/sessions/{session_id}",
                          headers=host["headers"], timeout=10)
        except:
            pass
        
        return True
    
    def run_all_tests(self):
        log("🧪 STARTING SUGGESTION HISTORY TEST SUITE", Colors.BOLD + Colors.CYAN)
        log("=" * 80, Colors.CYAN)
        
        start_time = time.time()
        
        try:
            self.test_suggestion_history_workflow()
            self.test_suggestion_history_edge_cases()
            
        except Exception as e:
            log(f"Test suite crashed: {e}", Colors.RED)
            import traceback
            traceback.print_exc()
        
        # Print results
        total_time = time.time() - start_time
        total_tests = self.passed_tests + self.failed_tests
        pass_rate = (self.passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        log("\\n" + "=" * 80, Colors.CYAN)
        log("🎯 SUGGESTION HISTORY TEST RESULTS", Colors.BOLD + Colors.CYAN)
        log("=" * 80, Colors.CYAN)
        
        log(f"✅ Passed: {self.passed_tests}", Colors.GREEN)
        log(f"❌ Failed: {self.failed_tests}", Colors.RED)
        log(f"📊 Pass Rate: {pass_rate:.1f}%", Colors.YELLOW)
        log(f"⏱️ Total Time: {total_time:.2f} seconds", Colors.BLUE)
        log(f"🌐 Server URL: {API_URL}", Colors.MAGENTA)
        
        if pass_rate >= 90:
            log("🏆 EXCELLENT! Suggestion history functionality works perfectly!", Colors.GREEN + Colors.BOLD)
        elif pass_rate >= 75:
            log("✨ GOOD! Suggestion history works with minor issues", Colors.GREEN + Colors.BOLD)
        elif pass_rate >= 60:
            log("✅ FAIR! Suggestion history has some limitations", Colors.YELLOW + Colors.BOLD)
        else:
            log("🚨 POOR! Suggestion history has serious issues", Colors.RED + Colors.BOLD)

if __name__ == "__main__":
    print(f"\\n{Colors.BOLD}{Colors.CYAN}")
    print("╔════════════════════════════════════════════════════════════════════════╗")
    print("║                    SUGGESTION HISTORY TEST SUITE                       ║")
    print("║                                                                        ║")
    print("║  Tests: History API, Host Access, Data Structure, Edge Cases          ║")
    print("╚════════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}\\n")
    
    # Find running server
    if find_running_server():
        test_suite = SuggestionHistoryTestSuite()
        test_suite.run_all_tests()
    else:
        log("❌ No server found. Please start the server first.", Colors.RED)
        log("💡 Try: docker-compose up --build", Colors.BLUE)