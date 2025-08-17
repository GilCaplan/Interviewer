#!/usr/bin/env python3
"""
Debug script to test question start endpoint
"""
import requests
import json

# Test with a real user session
def test_question_start():
    api_url = "http://localhost:5001"
    
    # First login to get a token
    login_response = requests.post(f"{api_url}/api/auth/login", json={
        "username": "host_user",
        "password": "password123"
    })
    
    if login_response.status_code != 200:
        print(f"Login failed: {login_response.status_code}")
        return
    
    token = login_response.json().get("access_token") or login_response.json().get("token")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create a session
    session_data = {
        "title": "Debug Session",
        "subject": "python", 
        "num_questions": 5,
        "difficulty": "medium",
        "template_mode": True
    }
    
    session_response = requests.post(f"{api_url}/api/sessions/create", json=session_data, headers=headers)
    if session_response.status_code != 201:
        print(f"Session creation failed: {session_response.status_code}")
        print(session_response.text)
        return
    
    session_info = session_response.json()
    session_id = session_info["session"]["session_id"]
    print(f"Created session: {session_id}")
    
    # Try to start a question
    question_data = {"type": "open_ended"}
    
    question_response = requests.post(
        f"{api_url}/api/sessions/{session_id}/questions/1/start",
        json=question_data,
        headers=headers
    )
    
    print(f"Question start response: {question_response.status_code}")
    print(f"Response text: {question_response.text}")
    
    if question_response.status_code == 200:
        print("SUCCESS!")
        question_info = question_response.json()
        print(json.dumps(question_info, indent=2))
    else:
        print("FAILED!")
        try:
            error_data = question_response.json()
            print(json.dumps(error_data, indent=2))
        except:
            print("Non-JSON response")

if __name__ == "__main__":
    test_question_start()