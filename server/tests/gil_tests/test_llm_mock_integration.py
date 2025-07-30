#!/usr/bin/env python3
"""
Mock LLM Integration Test Suite
Tests the mock LLM functionality for question generation and suggestions

Run with: python test_llm_mock_integration.py
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
API_URL = "http://localhost:5001"

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

class LLMTestSuite:
    def __init__(self):
        self.passed_tests = 0
        self.failed_tests = 0
        self.test_user = None
        self.test_session_id = None
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
    
    def setup_test_environment(self):
        log("\n🏗️ Setting Up Test Environment", Colors.BOLD + Colors.YELLOW)
        log("-" * 40, Colors.YELLOW)
        
        # Create test user
        username = f"llm_test_user_{uuid.uuid4().hex[:8]}"
        response = requests.post(f"{API_URL}/api/auth/login", json={"username": username})
        
        if response.status_code == 200:
            self.test_user = {
                "username": username,
                "token": response.json().get("token"),
                "headers": {"Authorization": f"Bearer {response.json().get('token')}"}
            }
            
        self.assert_test(self.test_user is not None, "Test User Creation", f"User: {username}")
        
        if not self.test_user:
            return False
        
        # Create test session with LLM enabled
        session_data = {
            "title": "LLM Integration Test Session",
            "subject": "algorithms",
            "template_mode": True,
            "settings": {
                "max_participants": 5,
                "max_questions": 25,
                "allow_llm": True,
                "allow_user_questions": True
            }
        }
        
        response = requests.post(f"{API_URL}/api/sessions/create",
                               json=session_data,
                               headers=self.test_user["headers"])
        
        session_created = response.status_code == 201
        if session_created:
            session_info = response.json().get("session", {})
            self.test_session_id = session_info.get("session_id")
        
        self.assert_test(session_created, "LLM Test Session Creation",
                        f"Session ID: {self.test_session_id[:8]}..." if session_created else "Failed")
        
        return session_created
    
    def test_mock_llm_subjects(self):
        log("\n🧠 Testing Mock LLM for Different Subjects", Colors.BOLD + Colors.YELLOW)
        log("-" * 40, Colors.YELLOW)
        
        subjects_to_test = ["python", "javascript", "algorithms", "system_design"]
        successful_generations = 0
        
        for i, subject in enumerate(subjects_to_test, 1):
            # Start a unique question for this subject
            response = requests.post(f"{API_URL}/api/sessions/{self.test_session_id}/questions/{i}/start",
                                   json={"type": "open_ended"},
                                   headers=self.test_user["headers"])
            
            if response.status_code == 200:
                question_id = response.json().get("question", {}).get("question_id")
                self.test_question_ids.append(question_id)
                
                # Request LLM suggestion for this subject
                llm_data = {
                    "field": "question_text",
                    "context": f"Generate a {subject} question for beginners"
                }
                
                response = requests.post(f"{API_URL}/api/sessions/{self.test_session_id}/questions/{question_id}/llm-suggest",
                                       json=llm_data,
                                       headers=self.test_user["headers"])
                
                if response.status_code == 200:
                    suggestion = response.json().get("suggestion", {})
                    suggested_text = suggestion.get("suggested_value", "")
                    
                    # Verify suggestion contains relevant content
                    has_content = len(suggested_text) > 10
                    if has_content:
                        successful_generations += 1
                        log(f"   📝 {subject}: {suggested_text[:50]}...", Colors.BLUE)
        
        success_rate = successful_generations / len(subjects_to_test)
        self.assert_test(success_rate >= 0.75, "Subject-Specific LLM Generation",
                        f"{successful_generations}/{len(subjects_to_test)} subjects generated successfully")
        
        return success_rate >= 0.75
    
    def test_question_type_specific_llm(self):
        log("\n🎯 Testing LLM for Different Question Types", Colors.BOLD + Colors.YELLOW)
        log("-" * 40, Colors.YELLOW)
        
        question_types = [
            {"type": "multiple_choice", "expected_fields": ["options", "correct_answer"]},
            {"type": "coding", "expected_fields": ["starter_code", "language"]},
            {"type": "true_false", "expected_fields": ["correct_answer"]},
            {"type": "short_answer", "expected_fields": ["expected_keywords"]}
        ]
        
        successful_types = 0
        
        for i, type_config in enumerate(question_types):
            question_type = type_config["type"]
            question_number = i + 10  # Start from question 10 to avoid conflicts
            
            # Start building a question of this type
            response = requests.post(f"{API_URL}/api/sessions/{self.test_session_id}/questions/{question_number}/start",
                                   json={"type": question_type},
                                   headers=self.test_user["headers"])
            
            if response.status_code == 200:
                question_id = response.json().get("question", {}).get("question_id")
                
                # Request LLM suggestion for question text
                llm_data = {
                    "field": "question_text",
                    "context": f"Generate a {question_type} question about data structures"
                }
                
                response = requests.post(f"{API_URL}/api/sessions/{self.test_session_id}/questions/{question_id}/llm-suggest",
                                       json=llm_data,
                                       headers=self.test_user["headers"])
                
                if response.status_code == 200:
                    suggestion = response.json().get("suggestion", {})
                    full_llm_response = suggestion.get("full_llm_response", {})
                    
                    # Check if LLM response includes type-specific fields
                    type_specific_content = any(field in full_llm_response for field in type_config["expected_fields"])
                    
                    if type_specific_content:
                        successful_types += 1
                        log(f"   🎭 {question_type}: Generated with appropriate fields", Colors.BLUE)
        
        success_rate = successful_types / len(question_types)
        self.assert_test(success_rate >= 0.5, "Question Type-Specific LLM",
                        f"{successful_types}/{len(question_types)} types handled correctly")
        
        return success_rate >= 0.5
    
    def test_context_awareness(self):
        log("\n🎭 Testing LLM Context Awareness", Colors.BOLD + Colors.YELLOW)
        log("-" * 40, Colors.YELLOW)
        
        if not self.test_question_ids:
            log("No question IDs available for context testing", Colors.YELLOW)
            return False
        
        question_id = self.test_question_ids[0]
        
        # Test different context scenarios
        context_tests = [
            {"context": "beginner level", "expected_keyword": "beginner"},
            {"context": "advanced level", "expected_keyword": "advanced"},
            {"context": "question 5", "expected_keyword": "5"},
            {"context": "practical application", "expected_content": True}
        ]
        
        context_successes = 0
        
        for test_case in context_tests:
            llm_data = {
                "field": "question_text",
                "context": test_case["context"]
            }
            
            response = requests.post(f"{API_URL}/api/sessions/{self.test_session_id}/questions/{question_id}/llm-suggest",
                                   json=llm_data,
                                   headers=self.test_user["headers"])
            
            if response.status_code == 200:
                suggestion = response.json().get("suggestion", {})
                suggested_text = suggestion.get("suggested_value", "").lower()
                context_used = suggestion.get("context_used", "").lower()
                
                # Check if context is reflected in response
                if "expected_keyword" in test_case:
                    keyword_found = test_case["expected_keyword"].lower() in suggested_text or test_case["expected_keyword"].lower() in context_used
                    if keyword_found:
                        context_successes += 1
                        log(f"   🎯 Context '{test_case['context']}': Keyword found", Colors.BLUE)
                elif test_case.get("expected_content"):
                    if len(suggested_text) > 20:  # Has substantial content
                        context_successes += 1
                        log(f"   🎯 Context '{test_case['context']}': Generated content", Colors.BLUE)
        
        success_rate = context_successes / len(context_tests)
        self.assert_test(success_rate >= 0.5, "LLM Context Awareness",
                        f"{context_successes}/{len(context_tests)} context tests passed")
        
        return success_rate >= 0.5
    
    def test_llm_field_suggestions(self):
        log("\n📝 Testing LLM Field-Specific Suggestions", Colors.BOLD + Colors.YELLOW)
        log("-" * 40, Colors.YELLOW)
        
        # Create a multiple choice question to test field suggestions
        response = requests.post(f"{API_URL}/api/sessions/{self.test_session_id}/questions/20/start",
                               json={"type": "multiple_choice"},
                               headers=self.test_user["headers"])
        
        if response.status_code != 200:
            self.assert_test(False, "MC Question Creation for Field Testing", "Failed to create question")
            return False
        
        question_id = response.json().get("question", {}).get("question_id")
        
        # Test suggestions for different fields
        field_tests = [
            {"field": "question_text", "context": "algorithms"},
            {"field": "options", "context": "multiple choice answers"},
            {"field": "explanation", "context": "why this answer is correct"},
            {"field": "hints", "context": "help for solving"}
        ]
        
        field_successes = 0
        
        for test_case in field_tests:
            llm_data = {
                "field": test_case["field"],
                "context": test_case["context"]
            }
            
            response = requests.post(f"{API_URL}/api/sessions/{self.test_session_id}/questions/{question_id}/llm-suggest",
                                   json=llm_data,
                                   headers=self.test_user["headers"])
            
            if response.status_code == 200:
                suggestion = response.json().get("suggestion", {})
                suggested_value = suggestion.get("suggested_value", "")
                field_name = suggestion.get("field", "")
                
                # Verify field matches and has content
                field_correct = field_name == test_case["field"]
                has_content = len(str(suggested_value)) > 5
                
                if field_correct and has_content:
                    field_successes += 1
                    log(f"   📋 {test_case['field']}: Generated appropriate content", Colors.BLUE)
        
        success_rate = field_successes / len(field_tests)
        self.assert_test(success_rate >= 0.5, "Field-Specific LLM Suggestions",
                        f"{field_successes}/{len(field_tests)} field suggestions successful")
        
        return success_rate >= 0.5
    
    def test_llm_suggestion_storage(self):
        log("\n💾 Testing LLM Suggestion Storage and Retrieval", Colors.BOLD + Colors.YELLOW)
        log("-" * 40, Colors.YELLOW)
        
        if not self.test_question_ids:
            return False
        
        question_id = self.test_question_ids[0]
        
        # Make multiple LLM suggestions
        suggestions_made = 0
        for i in range(3):
            llm_data = {
                "field": "question_text",
                "context": f"suggestion attempt {i+1}"
            }
            
            response = requests.post(f"{API_URL}/api/sessions/{self.test_session_id}/questions/{question_id}/llm-suggest",
                                   json=llm_data,
                                   headers=self.test_user["headers"])
            
            if response.status_code == 200:
                suggestions_made += 1
        
        # Retrieve session data to check if suggestions were stored
        response = requests.get(f"{API_URL}/api/sessions/{self.test_session_id}",
                               headers=self.test_user["headers"])
        
        if response.status_code == 200:
            session_data = response.json().get("session", {})
            questions_queue = session_data.get("template_data", {}).get("questions_queue", [])
            
            # Find our question and check suggestions
            target_question = None
            for q in questions_queue:
                if q.get("question_id") == question_id:
                    target_question = q
                    break
            
            if target_question:
                llm_suggestions = target_question.get("llm_suggestions", [])
                suggestions_stored = len(llm_suggestions)
                
                self.assert_test(suggestions_stored >= suggestions_made * 0.7,
                                "LLM Suggestion Storage",
                                f"{suggestions_stored} suggestions stored from {suggestions_made} requests")
                
                # Check suggestion structure
                if llm_suggestions:
                    first_suggestion = llm_suggestions[0]
                    has_required_fields = all(field in first_suggestion for field in 
                                            ["suggestion_id", "field", "suggested_value", "generated_at"])
                    
                    self.assert_test(has_required_fields, "Suggestion Data Structure",
                                    "Suggestions contain required metadata fields")
                    
                    return suggestions_stored >= 1 and has_required_fields
        
        return False
    
    def test_llm_error_handling(self):
        log("\n🛡️ Testing LLM Error Handling", Colors.BOLD + Colors.YELLOW)
        log("-" * 40, Colors.YELLOW)
        
        if not self.test_question_ids:
            return False
        
        question_id = self.test_question_ids[0]
        
        # Test invalid field name
        invalid_field_data = {
            "field": "nonexistent_field",
            "context": "test"
        }
        
        response = requests.post(f"{API_URL}/api/sessions/{self.test_session_id}/questions/{question_id}/llm-suggest",
                               json=invalid_field_data,
                               headers=self.test_user["headers"])
        
        # Should either handle gracefully (200) or reject appropriately (400)
        graceful_handling = response.status_code in [200, 400]
        self.assert_test(graceful_handling, "Invalid Field Handling",
                        f"Response code: {response.status_code}")
        
        # Test empty context
        empty_context_data = {
            "field": "question_text",
            "context": ""
        }
        
        response = requests.post(f"{API_URL}/api/sessions/{self.test_session_id}/questions/{question_id}/llm-suggest",
                               json=empty_context_data,
                               headers=self.test_user["headers"])
        
        empty_context_handled = response.status_code == 200
        self.assert_test(empty_context_handled, "Empty Context Handling",
                        "LLM handles empty context gracefully")
        
        return graceful_handling and empty_context_handled
    
    def run_all_tests(self):
        log("🚀 STARTING MOCK LLM INTEGRATION TEST SUITE", Colors.BOLD + Colors.CYAN)
        log("=" * 60, Colors.CYAN)
        
        start_time = time.time()
        
        try:
            if not self.setup_test_environment():
                log("Cannot proceed without test environment", Colors.RED)
                return
            
            self.test_mock_llm_subjects()
            self.test_question_type_specific_llm()
            self.test_context_awareness()
            self.test_llm_field_suggestions()
            self.test_llm_suggestion_storage()
            self.test_llm_error_handling()
            
        except Exception as e:
            log(f"Test suite crashed: {e}", Colors.RED)
            import traceback
            traceback.print_exc()
        
        # Print results
        total_time = time.time() - start_time
        total_tests = self.passed_tests + self.failed_tests
        pass_rate = (self.passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        log("\n" + "=" * 60, Colors.CYAN)
        log("🎯 MOCK LLM INTEGRATION TEST RESULTS", Colors.BOLD + Colors.CYAN)
        log("=" * 60, Colors.CYAN)
        
        log(f"✅ Passed: {self.passed_tests}", Colors.GREEN)
        log(f"❌ Failed: {self.failed_tests}", Colors.RED)
        log(f"📊 Pass Rate: {pass_rate:.1f}%", Colors.YELLOW)
        log(f"⏱️ Total Time: {total_time:.2f} seconds", Colors.BLUE)
        
        if pass_rate >= 90:
            log("🏆 EXCELLENT! Mock LLM integration is working perfectly!", Colors.GREEN + Colors.BOLD)
        elif pass_rate >= 75:
            log("✨ GOOD! Minor LLM integration issues to address", Colors.YELLOW + Colors.BOLD)
        else:
            log("🚨 NEEDS WORK! LLM integration has significant issues", Colors.RED + Colors.BOLD)
        
        log("\n💡 MOCK LLM NOTES:", Colors.BOLD + Colors.WHITE)
        log("• This tests the mock LLM system (no real API calls)", Colors.WHITE)
        log("• No tokens consumed or charges incurred", Colors.WHITE)
        log("• Ready for real LLM integration when needed", Colors.WHITE)

if __name__ == "__main__":
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║              MOCK LLM INTEGRATION TEST SUITE             ║")
    print("║                                                          ║")
    print("║  Tests: Subject Awareness, Question Types, Context       ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}\n")
    
    test_suite = LLMTestSuite()
    test_suite.run_all_tests()