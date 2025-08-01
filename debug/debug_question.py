#!/usr/bin/env python3
import requests
import uuid

# Test the specific failing scenario
API_URL = 'http://localhost:5001'

# Create user
username = f'debug_user_{uuid.uuid4().hex[:8]}'
auth_response = requests.post(f'{API_URL}/api/auth/login', json={'username': username}, timeout=10)
print(f'Auth response: {auth_response.status_code}')

if auth_response.status_code == 200:
    auth_data = auth_response.json()
    token = auth_data.get('token')
    headers = {'Authorization': f'Bearer {token}'}
    
    # Create session
    session_data = {
        'title': 'Debug Session',
        'description': 'Testing question creation',
        'subject': 'general'
    }
    
    session_response = requests.post(f'{API_URL}/api/sessions/create', json=session_data, headers=headers, timeout=10)
    print(f'Session creation response: {session_response.status_code}')
    
    if session_response.status_code == 201:
        session_info = session_response.json()
        session_id = session_info.get('session', {}).get('session_id')
        print(f'Session ID: {session_id}')
        
        # Get session data to check settings
        get_response = requests.get(f'{API_URL}/api/sessions/{session_id}', headers=headers, timeout=10)
        if get_response.status_code == 200:
            session_data = get_response.json().get('session', {})
            max_questions = session_data.get('settings', {}).get('max_questions', 'NOT SET')
            print(f'Max questions setting: {max_questions}')
        
        # Try to start question
        start_response = requests.post(f'{API_URL}/api/sessions/{session_id}/questions/1/start', 
                                     json={'type': 'open_ended'}, 
                                     headers=headers, 
                                     timeout=10)
        print(f'Question start response: {start_response.status_code}')
        if start_response.status_code != 200:
            print(f'Error: {start_response.text}')
        else:
            print('Question created successfully!')
    else:
        print(f'Session creation failed: {session_response.text}')
else:
    print(f'Auth failed: {auth_response.text}')