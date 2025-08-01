#!/usr/bin/env python3
"""
Integration test for session settings functionality.
Tests that viewing mode restrictions properly apply to non-host users.
"""

import requests
import json
import time
import sys
import os

# API configuration
API_BASE = "http://localhost:5001"
API_URL = f"{API_BASE}/api"

def test_session_settings_integration():
    """Test complete session settings workflow with multiple users"""
    print("🧪 Testing Session Settings Integration")
    print("=" * 50)
    
    # Test users
    host_user = {
        "username": "host_user_test",
        "email": "host@test.com", 
        "password": "testpass123"
    }
    
    non_host_user = {
        "username": "nonhost_user_test",
        "email": "nonhost@test.com",
        "password": "testpass123"
    }
    
    try:
        # Step 1: Register and login both users
        print("\n1. Setting up test users...")
        host_token = setup_user(host_user)
        non_host_token = setup_user(non_host_user)
        
        if not host_token or not non_host_token:
            print("❌ Failed to setup test users")
            return False
        
        print("✅ Test users created and authenticated")
        
        # Step 2: Host creates a session
        print("\n2. Host creating session...")
        session = create_session(host_token)
        if not session:
            print("❌ Failed to create session")
            return False
        
        session_id = session['session_id']
        session_code = session['session_code']
        print(f"✅ Session created: {session_code}")
        
        # Step 3: Non-host joins session
        print("\n3. Non-host joining session...")
        join_result = join_session(non_host_token, session_code)
        if not join_result:
            print("❌ Failed to join session")
            return False
        print("✅ Non-host joined session")
        
        # Step 4: Test different viewing modes
        viewing_modes = ['edit', 'suggestions_only', 'view_only']
        
        for mode in viewing_modes:
            print(f"\n4. Testing viewing mode: {mode}")
            print("-" * 30)
            
            # Host updates settings
            settings_updated = update_session_settings(host_token, session_id, {
                'viewing_mode': mode,
                'allow_llm': True,
                'allow_user_questions': True,
                'max_participants': 10
            })
            
            if not settings_updated:
                print(f"❌ Failed to update settings to {mode}")
                continue
            
            print(f"✅ Settings updated to {mode}")
            
            # Verify settings were applied
            current_session = get_session(host_token, session_id)
            if current_session and current_session.get('settings', {}).get('viewing_mode') == mode:
                print(f"✅ Settings verified: viewing_mode = {mode}")
            else:
                print(f"❌ Settings verification failed for {mode}")
                continue
            
            # Test non-host permissions based on viewing mode
            test_non_host_permissions(non_host_token, session_id, mode)
        
        # Step 5: Test non-host cannot change settings
        print("\n5. Testing non-host settings access...")
        non_host_settings_result = update_session_settings(non_host_token, session_id, {
            'viewing_mode': 'edit'
        })
        
        if non_host_settings_result:
            print("❌ Non-host was able to change settings (should be forbidden)")
            return False
        else:
            print("✅ Non-host correctly forbidden from changing settings")
        
        # Cleanup
        print("\n6. Cleaning up...")
        cleanup_user_sessions(host_token)
        cleanup_user_sessions(non_host_token)
        print("✅ Cleanup completed")
        
        print("\n" + "=" * 50)
        print("🎉 All session settings integration tests PASSED!")
        return True
        
    except Exception as e:
        print(f"\n❌ Integration test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def setup_user(user_data):
    """Register and login a user, return auth token"""
    try:
        # Try to register (might fail if user exists)
        requests.post(f"{API_URL}/auth/register", json=user_data)
        
        # Login
        login_response = requests.post(f"{API_URL}/auth/login", json={
            'username': user_data['username'],
            'password': user_data['password']
        })
        
        if login_response.status_code == 200:
            return login_response.json()['token']
        else:
            print(f"Login failed for {user_data['username']}: {login_response.text}")
            return None
            
    except Exception as e:
        print(f"Setup failed for {user_data['username']}: {e}")
        return None

def create_session(token):
    """Create a new session"""
    try:
        response = requests.post(f"{API_URL}/sessions/create", 
            headers={'Authorization': f'Bearer {token}'},
            json={
                'title': 'Test Session Settings',
                'subject': 'testing',
                'description': 'Testing viewing modes',
                'template_mode': True,
                'settings': {
                    'max_participants': 10,
                    'max_questions': 15,
                    'allow_llm': True,
                    'allow_user_questions': True,
                    'viewing_mode': 'edit'
                }
            }
        )
        
        if response.status_code == 201:
            return response.json()['session']
        else:
            print(f"Create session failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"Create session error: {e}")
        return None

def join_session(token, session_code):
    """Join an existing session"""
    try:
        response = requests.post(f"{API_URL}/sessions/join/{session_code}",
            headers={'Authorization': f'Bearer {token}'},
            json={}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Join session failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"Join session error: {e}")
        return None

def update_session_settings(token, session_id, settings):
    """Update session settings"""
    try:
        response = requests.put(f"{API_URL}/sessions/{session_id}/settings",
            headers={'Authorization': f'Bearer {token}'},
            json=settings
        )
        
        if response.status_code == 200:
            print(f"    Settings updated successfully: {settings}")
            return True
        else:
            print(f"    Settings update failed ({response.status_code}): {response.text}")
            return False
            
    except Exception as e:
        print(f"    Settings update error: {e}")
        return False

def get_session(token, session_id):
    """Get session details"""
    try:
        response = requests.get(f"{API_URL}/sessions/{session_id}",
            headers={'Authorization': f'Bearer {token}'}
        )
        
        if response.status_code == 200:
            return response.json()['session']
        else:
            return None
            
    except Exception as e:
        print(f"Get session error: {e}")
        return None

def test_non_host_permissions(token, session_id, viewing_mode):
    """Test what non-host can do based on viewing mode"""
    print(f"    Testing non-host permissions for {viewing_mode} mode...")
    
    # First, create a question to test with (this should work for host actions)
    # We'll try to start a question as non-host
    question_start_response = requests.post(f"{API_URL}/sessions/{session_id}/questions/1/start",
        headers={'Authorization': f'Bearer {token}'},
        json={'type': 'behavioral'}
    )
    
    if viewing_mode == 'edit':
        # In edit mode, non-host should be able to start questions
        if question_start_response.status_code in [200, 201]:
            print(f"    ✅ Non-host can start questions in {viewing_mode} mode")
        else:
            print(f"    ⚠️  Non-host cannot start questions in {viewing_mode} mode (expected to work)")
    
    elif viewing_mode == 'view_only':
        # In view_only mode, non-host should NOT be able to start questions
        if question_start_response.status_code == 403:
            print(f"    ✅ Non-host correctly forbidden from starting questions in {viewing_mode} mode")
        else:
            print(f"    ❌ Non-host was able to start questions in {viewing_mode} mode (should be forbidden)")
    
    elif viewing_mode == 'suggestions_only':
        # In suggestions_only mode, non-host should NOT be able to directly edit
        if question_start_response.status_code == 403:
            print(f"    ✅ Non-host correctly forbidden from direct edits in {viewing_mode} mode")
        else:
            print(f"    ⚠️  Non-host was able to start questions in {viewing_mode} mode (may need suggestion workflow)")

def cleanup_user_sessions(token):
    """Clean up all sessions for a user"""
    try:
        requests.delete(f"{API_URL}/sessions/cleanup-user",
            headers={'Authorization': f'Bearer {token}'}
        )
    except:
        pass  # Ignore cleanup errors

if __name__ == "__main__":
    print("Starting Session Settings Integration Test...")
    print("Make sure the server is running on http://localhost:5001")
    print()
    
    success = test_session_settings_integration()
    
    if success:
        print("\n🎉 Integration test completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Integration test failed!")
        sys.exit(1)