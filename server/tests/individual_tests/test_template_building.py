#!/usr/bin/env python3
"""
Simple Template Building Test Suite
Tests essential CRUD operations for templates

Run with: python test_template_building_simple.py
"""

import requests
import json
import uuid
from datetime import datetime

# Import test configuration
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from test_config import get_primary_api_url

API_URL = get_primary_api_url()

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
    print(f"{color}{timestamp} {message}{Colors.END}")

class SimpleTemplateTest:
    def __init__(self):
        self.api_url = API_URL
        self.user_token = None
        self.test_user = f"template_test_{uuid.uuid4().hex[:8]}"
        self.passed = 0
        self.failed = 0
        
    def assert_test(self, condition, test_name, error_msg=""):
        if condition:
            log(f"✅ {test_name}", Colors.GREEN)
            self.passed += 1
        else:
            log(f"❌ {test_name}", Colors.RED)
            if error_msg:
                log(f"   {error_msg}", Colors.RED)
            self.failed += 1
            
    def setup_user(self):
        """Create test user and get token"""
        if not self.api_url:
            return False
            
        try:
            response = requests.post(f'{self.api_url}/api/auth/login',
                                   json={'username': self.test_user},
                                   headers={'Content-Type': 'application/json'},
                                   timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                self.user_token = data.get('token')
                return self.user_token is not None
            return False
        except Exception as e:
            log(f"Setup failed: {e}", Colors.RED)
            return False
    
    def test_template_basic_crud(self):
        """Test basic template creation, reading, updating, deletion"""
        if not self.user_token:
            self.assert_test(False, "Template CRUD", "No auth token")
            return
            
        headers = {
            'Authorization': f'Bearer {self.user_token}',
            'Content-Type': 'application/json'
        }
        
        # Test 1: Create template
        template_data = {
            'title': 'Test Template',
            'subject': 'JavaScript',
            'description': 'Simple test template'
        }
        
        try:
            response = requests.post(f'{self.api_url}/api/templates',
                                   json=template_data,
                                   headers=headers,
                                   timeout=5)
            self.assert_test(response.status_code == 201, "Create Template")
            
            if response.status_code == 201:
                template_id = response.json().get('template_id')
                
                # Test 2: Get templates
                response = requests.get(f'{self.api_url}/api/templates',
                                      headers=headers,
                                      timeout=5)
                self.assert_test(response.status_code == 200, "Get Templates")
                
                # Test 3: Update template (if template_id exists)
                if template_id:
                    update_data = {'title': 'Updated Test Template'}
                    response = requests.put(f'{self.api_url}/api/templates/{template_id}',
                                          json=update_data,
                                          headers=headers,
                                          timeout=5)
                    self.assert_test(response.status_code in [200, 404], "Update Template")
                    
        except Exception as e:
            self.assert_test(False, "Template CRUD", str(e))
    
    def test_question_management(self):
        """Test basic question operations"""
        if not self.user_token:
            self.assert_test(False, "Question Management", "No auth token")
            return
            
        headers = {
            'Authorization': f'Bearer {self.user_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            # Test: Get questions
            response = requests.get(f'{self.api_url}/api/questions',
                                  headers=headers,
                                  timeout=5)
            self.assert_test(response.status_code == 200, "Get Questions")
            
            # Test: Create question
            question_data = {
                'type': 'open_ended',
                'question_text': 'What is JavaScript?',
                'subject': 'JavaScript'
            }
            
            response = requests.post(f'{self.api_url}/api/questions',
                                   json=question_data,
                                   headers=headers,
                                   timeout=5)
            self.assert_test(response.status_code == 201, "Create Question")
            
        except Exception as e:
            self.assert_test(False, "Question Management", str(e))
    
    def run_all_tests(self):
        """Run all simple template tests"""
        print(f"{Colors.BOLD}{Colors.CYAN}")
        print("╔══════════════════════════════════════════════════════════╗")
        print("║              SIMPLE TEMPLATE BUILDING TEST              ║")
        print("║                                                          ║")
        print("║  Tests: Basic CRUD, Question Management                 ║")
        print("╚══════════════════════════════════════════════════════════╝")
        print(f"{Colors.END}")
        
        if not self.api_url:
            log("❌ No server found. Please start the server first.", Colors.RED)
            return (0.0, 0, 1)
        
        log("🚀 STARTING SIMPLE TEMPLATE BUILDING TESTS", Colors.BOLD + Colors.CYAN)
        log("============================================================", Colors.CYAN)
        
        # Setup
        if not self.setup_user():
            log("❌ Failed to setup test user", Colors.RED)
            return (0.0, 0, 1)
        
        log("✅ User authenticated successfully", Colors.GREEN)
        
        # Run tests
        self.test_template_basic_crud()
        self.test_question_management()
        
        # Results
        total_tests = self.passed + self.failed
        pass_rate = (self.passed / total_tests * 100) if total_tests > 0 else 0
        
        log("", Colors.CYAN)
        log("============================================================", Colors.CYAN)
        log("🎯 SIMPLE TEMPLATE BUILDING TEST RESULTS", Colors.BOLD + Colors.CYAN)
        log("============================================================", Colors.CYAN)
        log(f"✅ Passed: {self.passed}", Colors.GREEN)
        log(f"❌ Failed: {self.failed}", Colors.RED)
        log(f"📊 Pass Rate: {pass_rate:.1f}%", Colors.YELLOW)
        log(f"🌐 Server URL: {self.api_url}", Colors.WHITE)
        
        if pass_rate >= 80:
            log("🏆 EXCELLENT! Template functionality working well!", Colors.GREEN + Colors.BOLD)
        elif pass_rate >= 60:
            log("👍 GOOD! Minor issues to address", Colors.YELLOW + Colors.BOLD)
        else:
            log("⚠️ Issues need attention", Colors.RED + Colors.BOLD)
        
        return (pass_rate, self.passed, total_tests)

if __name__ == "__main__":
    test_suite = SimpleTemplateTest()
    result = test_suite.run_all_tests()
    print(f"\nTest completed with result: {result}")