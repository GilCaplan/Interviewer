#!/usr/bin/env python3
"""
Simple test for suggestion history functionality
Based on the working test_field_suggestions.py pattern
"""
import requests
import json
import time

def test_suggestion_history_simple():
    api_url = 'http://localhost:5001'
    
    print("🧪 Testing Suggestion History Functionality")
    print("=" * 50)
    
    # Step 1: Login as host
    response = requests.post(f'{api_url}/api/auth/login', json={'username': 'test_host_history'})
    if response.status_code != 200:
        print(f'❌ Host login failed: {response.status_code}')
        return False
        
    host_token = response.json()['token']
    host_headers = {'Authorization': f'Bearer {host_token}', 'Content-Type': 'application/json'}
    print('✅ Host login successful')
    
    # Step 2: Login as participant
    response = requests.post(f'{api_url}/api/auth/login', json={'username': 'test_participant_history'})
    if response.status_code != 200:
        print(f'❌ Participant login failed: {response.status_code}')
        return False
        
    participant_token = response.json()['token']
    participant_headers = {'Authorization': f'Bearer {participant_token}', 'Content-Type': 'application/json'}
    print('✅ Participant login successful')
    
    # Step 3: Host creates session
    session_data = {
        'title': 'Suggestion History Test',
        'subject': 'general',
        'template_mode': True,
        'settings': {'max_participants': 10, 'max_questions': 15}
    }
    response = requests.post(f'{api_url}/api/sessions/create', json=session_data, headers=host_headers)
    if response.status_code != 201:
        print(f'❌ Session creation failed: {response.status_code}')
        return False
        
    session_id = response.json()['session']['session_id']
    session_code = response.json()['session']['session_code']
    print(f'✅ Session created: {session_code}')
    
    # Step 4: Participant joins session
    response = requests.post(f'{api_url}/api/sessions/join/{session_code}', headers=participant_headers)
    if response.status_code != 200:
        print(f'❌ Participant join failed: {response.status_code}')
        return False
    print('✅ Participant joined session')
    
    # Step 5: Host starts a question
    response = requests.post(f'{api_url}/api/sessions/{session_id}/questions/1/start', 
                           json={'type': 'open_ended'}, headers=host_headers)
    if response.status_code != 200:
        print(f'❌ Question creation failed: {response.status_code}')
        return False
        
    question_id = response.json()['question']['question_id']
    print(f'✅ Question created: {question_id}')
    
    # Step 6: Participant makes a suggestion
    suggestion_data = {
        'field': 'question_text',
        'suggested_value': 'What is the time complexity of quicksort?',
        'current_value': ''
    }
    response = requests.post(f'{api_url}/api/sessions/{session_id}/questions/{question_id}/suggest', 
                           json=suggestion_data, headers=participant_headers)
    
    if response.status_code != 200:
        print(f'❌ Suggestion creation failed: {response.status_code} - {response.text}')
        return False
        
    suggestion_id = response.json()['suggestion']['suggestion_id']
    print(f'✅ Suggestion created: {suggestion_id}')
    
    # Step 7: Host accepts the suggestion
    response = requests.put(f'{api_url}/api/sessions/{session_id}/questions/{question_id}/suggestions/{suggestion_id}',
                          json={'action': 'accept'}, headers=host_headers)
    if response.status_code != 200:
        print(f'❌ Accept suggestion failed: {response.status_code} - {response.text}')
        return False
    print('✅ Suggestion accepted successfully!')
    
    # Step 8: Wait for database update
    time.sleep(1)
    
    # Step 9: Test suggestion history endpoint
    response = requests.get(f'{api_url}/api/sessions/{session_id}/suggestions/history', headers=host_headers)
    
    if response.status_code != 200:
        print(f'❌ History endpoint failed: {response.status_code} - {response.text}')
        return False
    
    history_data = response.json()
    suggestion_history = history_data.get('suggestion_history', [])
    total_suggestions = history_data.get('total_suggestions', 0)
    
    print(f'✅ History endpoint accessible')
    print(f'📊 Found {len(suggestion_history)} suggestions in history')
    print(f'📊 Total suggestions reported: {total_suggestions}')
    
    if len(suggestion_history) == 0:
        print('⚠️ Warning: No suggestions found in history')
        print('🔍 Debugging session data...')
        
        # Debug: Check session data
        debug_response = requests.get(f'{api_url}/api/sessions/{session_id}/debug', headers=host_headers)
        if debug_response.status_code == 200:
            debug_data = debug_response.json()
            questions_queue = debug_data.get('questions_queue', [])
            ready_questions = debug_data.get('ready_questions', [])
            
            print(f'🔍 Questions in queue: {len(questions_queue)}')
            print(f'🔍 Ready questions: {len(ready_questions)}')
            
            # Check for collaboration notes in questions
            all_questions = questions_queue + ready_questions
            for i, q in enumerate(all_questions):
                notes = q.get('collaboration_notes', [])
                print(f'🔍 Question {i+1} has {len(notes)} collaboration notes')
                
                for j, note in enumerate(notes):
                    if note.get('type') == 'field_suggestion':
                        suggestion_data = note.get('suggestion_data', {})
                        print(f'   Note {j+1}: Status={suggestion_data.get("status", "unknown")}')
        else:
            print('❌ Could not access debug endpoint')
        
        return False
    else:
        print('✅ Suggestions found in history!')
        
        # Validate suggestion data
        first_suggestion = suggestion_history[0]
        required_fields = ['question_number', 'question_id', 'suggestion_id', 'field', 
                         'suggested_value', 'author', 'status', 'handled_by', 'timestamp', 'handled_at']
        
        missing_fields = [field for field in required_fields if first_suggestion.get(field) is None]
        if missing_fields:
            print(f'❌ Missing fields in suggestion: {missing_fields}')
            return False
        
        print('✅ All required fields present in suggestion history')
        
        if first_suggestion.get('status') in ['accept', 'reject']:
            print('✅ Suggestion status correctly recorded')
        else:
            print(f'❌ Invalid suggestion status: {first_suggestion.get("status")}')
            return False
    
    # Step 10: Test non-host access (should be denied)
    response = requests.get(f'{api_url}/api/sessions/{session_id}/suggestions/history', headers=participant_headers)
    if response.status_code == 403:
        print('✅ Non-host access properly denied')
    else:
        print(f'❌ Non-host access not properly restricted: {response.status_code}')
        return False
    
    # Cleanup
    try:
        requests.delete(f'{api_url}/api/sessions/{session_id}', headers=host_headers)
        print('🧹 Session cleaned up')
    except:
        pass
    
    print('\n🎉 All suggestion history tests passed!')
    return True

if __name__ == "__main__":
    success = test_suggestion_history_simple()
    if success:
        print("✅ SUCCESS: Suggestion history functionality working correctly!")
    else:
        print("❌ FAILURE: Suggestion history has issues that need fixing.")