#!/usr/bin/env python3
"""
Debug script to examine suggestion storage in MongoDB
"""
import requests
import json

def debug_suggestion_storage():
    api_url = 'http://localhost:5000' 
    
    print("🔍 DEBUGGING SUGGESTION STORAGE")
    print("=" * 40)
    
    # Login and create session
    response = requests.post(f'{api_url}/api/auth/login', json={'username': 'debug_user'})
    token = response.json()['token']
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    response = requests.post(f'{api_url}/api/sessions/create', json={
        'title': 'Debug Session',
        'subject': 'general', 
        'template_mode': True,
        'settings': {'max_participants': 10, 'max_questions': 15}
    }, headers=headers)
    
    session_id = response.json()['session']['session_id']
    print(f"✅ Session created: {session_id}")
    
    # Create question
    response = requests.post(f'{api_url}/api/sessions/{session_id}/questions/1/start',
                           json={'type': 'open_ended'}, headers=headers)
    question_id = response.json()['question']['question_id']
    print(f"✅ Question created: {question_id}")
    
    # Check session state after question creation
    response = requests.get(f'{api_url}/api/sessions/{session_id}/debug', headers=headers)
    if response.status_code == 200:
        debug_response = response.json()
        debug_data = debug_response.get('debug', {})
        questions_queue = debug_data.get('queue_details', [])
        print(f"📊 Questions in queue after creation: {len(questions_queue)}")
        
        if questions_queue:
            question = questions_queue[0]
            print(f"   Question ID: {question.get('question_id')}")
            print(f"   Status: {question.get('status')}")
            print(f"   Collaboration notes: {len(question.get('collaboration_notes', []))}")
    
    # Make suggestion
    response = requests.post(f'{api_url}/api/sessions/{session_id}/questions/{question_id}/suggest',
                           json={
                               'field': 'question_text',
                               'suggested_value': 'Test suggestion value',
                               'current_value': ''
                           }, headers=headers)
    
    if response.status_code == 200:
        suggestion_id = response.json()['suggestion']['suggestion_id']
        print(f"✅ Suggestion created: {suggestion_id}")
        
        # Check session state after suggestion
        response = requests.get(f'{api_url}/api/sessions/{session_id}/debug', headers=headers)
        if response.status_code == 200:
            debug_response = response.json()
            debug_data = debug_response.get('debug', {})
            questions_queue = debug_data.get('queue_details', [])
            print(f"📊 Questions in queue after suggestion: {len(questions_queue)}")
            
            if questions_queue:
                question = questions_queue[0]
                notes = question.get('collaboration_notes', [])
                print(f"   Collaboration notes: {len(notes)}")
                
                for i, note in enumerate(notes):
                    if note.get('type') == 'field_suggestion':
                        suggestion_data = note.get('suggestion_data', {})
                        print(f"   Note {i+1}: Status={suggestion_data.get('status')}, Field={suggestion_data.get('field')}")
        
        # Accept suggestion
        response = requests.put(f'{api_url}/api/sessions/{session_id}/questions/{question_id}/suggestions/{suggestion_id}',
                              json={'action': 'accept'}, headers=headers)
        
        if response.status_code == 200:
            print(f"✅ Suggestion accepted")
            
            # Check session state after acceptance  
            response = requests.get(f'{api_url}/api/sessions/{session_id}/debug', headers=headers)
            if response.status_code == 200:
                debug_response = response.json()
                debug_data = debug_response.get('debug', {})
                questions_queue = debug_data.get('queue_details', [])
                ready_questions = debug_data.get('ready_details', [])  
                print(f"📊 Questions in queue after acceptance: {len(questions_queue)}")
                print(f"📊 Ready questions after acceptance: {len(ready_questions)}")
                
                # Check all questions for suggestions
                all_questions = questions_queue + ready_questions
                for i, question in enumerate(all_questions):
                    notes = question.get('collaboration_notes', [])
                    print(f"   Question {i+1}: {len(notes)} notes")
                    
                    for j, note in enumerate(notes):
                        if note.get('type') == 'field_suggestion':
                            suggestion_data = note.get('suggestion_data', {})
                            status = suggestion_data.get('status')
                            field = suggestion_data.get('field')
                            handled_at = suggestion_data.get('handled_at')
                            print(f"     Note {j+1}: Status={status}, Field={field}, Handled={bool(handled_at)}")
            
            # Test suggestion history endpoint
            response = requests.get(f'{api_url}/api/sessions/{session_id}/suggestions/history', headers=headers)
            if response.status_code == 200:
                history_data = response.json()
                suggestions = history_data.get('suggestion_history', [])
                print(f"📊 Suggestion history endpoint returned: {len(suggestions)} suggestions")
                
                if suggestions:
                    for i, suggestion in enumerate(suggestions):
                        print(f"   History {i+1}: Status={suggestion.get('status')}, Field={suggestion.get('field')}")
                else:
                    print("❌ No suggestions found in history!")
            else:
                print(f"❌ History endpoint failed: {response.status_code}")
    
    # Cleanup
    try:
        requests.delete(f'{api_url}/api/sessions/{session_id}', headers=headers)
    except:
        pass

if __name__ == "__main__":
    debug_suggestion_storage()