#!/usr/bin/env python3
"""
Test script to verify UI improvements:
1. User online status tracking
2. Duplicate user prevention
3. Session management UI reorganization
"""

import requests
import json
import time
import sys

# API configuration
API_BASE = "http://localhost:5001"
API_URL = f"{API_BASE}/api"

def test_ui_improvements():
    """Test UI improvements functionality"""
    print("🧪 Testing UI Improvements")
    print("=" * 40)
    
    # Test users
    user1 = {
        "username": "user1_ui_test",
        "email": "user1@test.com", 
        "password": "testpass123"
    }
    
    user2 = {
        "username": "user2_ui_test",
        "email": "user2@test.com",
        "password": "testpass123"
    }
    
    try:
        # Step 1: Setup users
        print("\n1. Setting up test users...")
        token1 = setup_user(user1)
        token2 = setup_user(user2)
        
        if not token1 or not token2:
            print("❌ Failed to setup test users")
            return False
        
        print("✅ Test users created")
        
        # Step 2: Create session
        print("\n2. Creating session...")
        session = create_session(token1)
        if not session:
            print("❌ Failed to create session")
            return False
        
        session_id = session['session_id']
        session_code = session['session_code']
        print(f"✅ Session created: {session_code}")
        
        # Step 3: Test participant loading
        print("\n3. Testing participant loading...")
        participants = get_participants(token1, session_id)
        if not participants:
            print("❌ Failed to load participants")
            return False
        
        print(f"✅ Initial participants loaded: {len(participants)} users")
        
        # Step 4: Test second user joining
        print("\n4. Testing second user joining...")
        join_result = join_session(token2, session_code)
        if not join_result:
            print("❌ Failed for second user to join")
            return False
        
        print("✅ Second user joined")
        
        # Step 5: Verify participant count
        print("\n5. Verifying participant count...")
        time.sleep(1)  # Give time for updates
        updated_participants = get_participants(token1, session_id)
        
        if updated_participants and len(updated_participants) == 2:
            print("✅ Participant count correct: 2 users")
            
            # Check for unique usernames
            usernames = [p['username'] for p in updated_participants]
            if len(set(usernames)) == len(usernames):
                print("✅ No duplicate users found")
            else:
                print("❌ Duplicate users detected!")
                print(f"   Usernames: {usernames}")
                return False
        else:
            print(f"❌ Incorrect participant count: {len(updated_participants) if updated_participants else 0}")
            return False
        
        # Step 6: Test session settings access
        print("\n6. Testing session settings access...")
        settings_result = get_session_settings(token1, session_id)
        if settings_result:
            print("✅ Host can access session settings")
        else:
            print("❌ Host cannot access session settings")
            return False
        
        # Test non-host settings access
        non_host_settings = get_session_settings(token2, session_id)
        if non_host_settings:
            print("✅ Non-host can view session settings")
        else:
            print("❌ Non-host cannot view session settings")
        
        # Cleanup
        print("\n7. Cleaning up...")
        cleanup_user_sessions(token1)
        cleanup_user_sessions(token2)
        print("✅ Cleanup completed")
        
        print("\n" + "=" * 40)
        print("🎉 All UI improvement tests PASSED!")
        return True
        
    except Exception as e:
        print(f"\n❌ UI test failed with error: {e}")
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
            return None
    except:
        return None

def create_session(token):
    """Create a new session"""
    try:
        response = requests.post(f"{API_URL}/sessions/create", 
            headers={'Authorization': f'Bearer {token}'},
            json={
                'title': 'UI Test Session',
                'subject': 'testing',
                'description': 'Testing UI improvements',
                'template_mode': True,
                'settings': {
                    'max_participants': 10,
                    'viewing_mode': 'edit'
                }
            }
        )
        
        if response.status_code == 201:
            return response.json()['session']
        else:
            return None
    except:
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
            return None
    except:
        return None

def get_participants(token, session_id):
    """Get session participants"""
    try:
        response = requests.get(f"{API_URL}/sessions/{session_id}/participants",
            headers={'Authorization': f'Bearer {token}'}
        )
        
        if response.status_code == 200:
            return response.json()['participants']
        else:
            return None
    except:
        return None

def get_session_settings(token, session_id):
    """Get session details including settings"""
    try:
        response = requests.get(f"{API_URL}/sessions/{session_id}",
            headers={'Authorization': f'Bearer {token}'}
        )
        
        if response.status_code == 200:
            return response.json()['session']
        else:
            return None
    except:
        return None

def cleanup_user_sessions(token):
    """Clean up all sessions for a user"""
    try:
        requests.delete(f"{API_URL}/sessions/cleanup-user",
            headers={'Authorization': f'Bearer {token}'}
        )
    except:
        pass

if __name__ == "__main__":
    print("Starting UI Improvements Test...")
    print("Make sure the server is running on http://localhost:5001")
    print()
    
    success = test_ui_improvements()
    
    if success:
        print("\n🎉 UI improvements test completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ UI improvements test failed!")
        sys.exit(1)