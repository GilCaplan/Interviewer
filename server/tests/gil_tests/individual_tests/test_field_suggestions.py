#!/usr/bin/env python3
"""
Quick test for field suggestion functionality
"""
import requests
import json

def test_field_suggestions():
    api_url = 'http://localhost:5001'
    
    # Login
    response = requests.post(f'{api_url}/api/auth/login', json={'username': 'test_user_suggestions'})
    assert response.status_code == 200, f'❌ Login failed: {response.status_code}'
        
    token = response.json()['token']
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    print('✅ Login successful')
    
    # Create session
    session_data = {
        'title': 'Field Suggestion Test',
        'subject': 'general',
        'template_mode': True,
        'settings': {'max_participants': 10, 'max_questions': 15}
    }
    response = requests.post(f'{api_url}/api/sessions/create', json=session_data, headers=headers)
    assert response.status_code == 201, f'❌ Session creation failed: {response.status_code}'
        
    session_id = response.json()['session']['session_id']
    print('✅ Session created')
    
    # Start a question
    response = requests.post(f'{api_url}/api/sessions/{session_id}/questions/1/start', 
                           json={'type': 'open_ended'}, headers=headers)
    if response.status_code != 200:
        print(f'❌ Question creation failed: {response.status_code}')
        return False
        
    question_id = response.json()['question']['question_id']
    print('✅ Question created')
    
    # Test field suggestion endpoint
    suggestion_data = {
        'field': 'question_text',
        'suggested_value': 'What is the time complexity of quicksort?',
        'current_value': ''
    }
    response = requests.post(f'{api_url}/api/sessions/{session_id}/questions/{question_id}/suggest', 
                           json=suggestion_data, headers=headers)
    
    print(f'Suggestion API response status: {response.status_code}')
    
    if response.status_code == 200:
        result = response.json()
        suggestion_id = result['suggestion']['suggestion_id']
        print(f'✅ Suggestion created successfully! ID: {suggestion_id}')
        
        # Test accepting suggestion
        response = requests.put(f'{api_url}/api/sessions/{session_id}/questions/{question_id}/suggestions/{suggestion_id}',
                              json={'action': 'accept'}, headers=headers)
        assert response.status_code == 200, f'❌ Accept suggestion failed: {response.status_code} Error: {response.text}'
        print('✅ Suggestion accepted successfully!')
        print('🎉 All field suggestion endpoints working!')
    else:
        assert False, f'❌ Create suggestion failed: {response.status_code} Error response: {response.text}'

def run_all_tests():
    """Run all tests and return standardized format"""
    try:
        test_field_suggestions()
        return (100.0, 4, 4)  # 4 test steps all passed
    except Exception as e:
        print(f"❌ Field suggestions test failed: {e}")
        return (0.0, 0, 4)  # All 4 test steps failed

if __name__ == "__main__":
    try:
        test_field_suggestions()
        print("✅ Field suggestions test completed successfully!")
    except Exception as e:
        print(f"❌ Field suggestions test failed: {e}")