#!/usr/bin/env python3
import requests
import json

# Test the template creation with questions directly
API_URL = "http://localhost:5001"

# Create a test user
user_response = requests.post(f"{API_URL}/api/auth/login", json={"username": "debug_template_test"})
if user_response.status_code != 200:
    print("Failed to create user")
    exit(1)

token = user_response.json().get("token")
headers = {"Authorization": f"Bearer {token}"}

# Create template with questions like the E2E test
template_data = {
    "template_name": "Debug Template",
    "description": "Test template creation",
    "subject": "python",
    "difficulty": "medium",
    "is_public": False,
    "questions": [
        {
            "question_text": "What is the difference between list and tuple in Python?",
            "type": "multiple_choice",
            "options": ["Lists are mutable, tuples are immutable", "Both are the same", "Tuples are faster", "Lists are immutable"],
            "correct_answer": "Lists are mutable, tuples are immutable",
            "explanation": "Lists can be modified after creation, tuples cannot"
        },
        {
            "question_text": "Implement a function to check if a number is prime",
            "type": "coding",
            "language": "python",
            "starter_code": "def is_prime(n):\n    # Your code here\n    pass",
            "solution": "def is_prime(n):\n    if n < 2: return False\n    for i in range(2, int(n**0.5) + 1):\n        if n % i == 0: return False\n    return True",
            "test_cases": [
                {"input": "5", "expected": "True"},
                {"input": "4", "expected": "False"}
            ]
        },
        {
            "question_text": "What is Python?",
            "type": "open_ended"
        }
    ]
}

create_response = requests.post(f"{API_URL}/api/templates", json=template_data, headers=headers)
print(f"Create response: {create_response.status_code}")
print(f"Create content: {create_response.text}")

if create_response.status_code == 201:
    template_info = create_response.json()
    template_id = template_info.get("template", {}).get("template_id")
    print(f"Template ID: {template_id}")
    
    # Get the template to see if questions were saved
    get_response = requests.get(f"{API_URL}/api/templates/{template_id}", headers=headers)
    if get_response.status_code == 200:
        template = get_response.json().get("template", {})
        questions = template.get("questions", [])
        print(f"Questions in template: {len(questions)}")
        if questions:
            print(f"First question: {questions[0]}")
    else:
        print(f"Failed to get template: {get_response.status_code}")