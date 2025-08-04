#!/usr/bin/env python3
"""
Test script to verify remove user functionality works correctly
"""

import requests
import json
import time
import sys

# API configuration
API_BASE = "http://localhost:5001"
API_URL = f"{API_BASE}/api"

def test_remove_user():
    """Test remove user functionality"""
    print("🧪 Testing Remove User Functionality")
    print("=" * 45)
    
    # Test users
    host_user = {
        "username": "host_remove_test",
        "email": "host@test.com", 
        "password": "testpass123"
    }
    
    regular_user = {
        "username": "user_remove_test",
        "email": "user@test.com",
        "password": "testpass123"
    }
    
    try:
        # Step 1: Setup users
        print("\n1. Setting up test users...")
        host_token = setup_user(host_user)
        user_token = setup_user(regular_user)
        
        assert host_token and user_token, "❌ Failed to setup test users"
        
        print("✅ Test users created")
        
        # Step 2: Create session
        print("\n2. Creating session...")
        session = create_session(host_token)
        assert session, "❌ Failed to create session"
        
        session_id = session['session_id']
        session_code = session['session_code']
        print(f"✅ Session created: {session_code}")
        
        # Step 3: Regular user joins
        print("\n3. Regular user joining session...")
        join_result = join_session(user_token, session_code)
        assert join_result, "❌ Failed for user to join"
        
        print("✅ Regular user joined")
        
        # Step 4: Verify participant count before removal
        print("\n4. Verifying participants before removal...")
        participants = get_participants(host_token, session_id)
        assert participants and len(participants) == 2, f"❌ Expected 2 participants, got {len(participants) if participants else 0}"
        
        print(f"✅ Found {len(participants)} participants")
        
        # Step 5: Test non-host cannot remove users
        print("\n5. Testing non-host removal prevention...")
        remove_result = remove_user_from_session(user_token, session_id, host_user['username'])
        assert not remove_result, "❌ Non-host was able to remove users (should be forbidden)"
        
        print("✅ Non-host correctly forbidden from removing users")
        
        # Step 6: Test host can remove regular user
        print("\n6. Testing host removes regular user...")
        remove_result = remove_user_from_session(host_token, session_id, regular_user['username'])
        assert remove_result, "❌ Host failed to remove regular user"
        
        print("✅ Host successfully removed regular user")
        
        # Step 7: Verify participant count after removal
        print("\n7. Verifying participants after removal...")
        time.sleep(1)  # Give time for database update
        participants_after = get_participants(host_token, session_id)
        assert participants_after and len(participants_after) == 1, f"❌ Expected 1 participant after removal, got {len(participants_after) if participants_after else 0}"
        
        print(f"✅ Participant count correct after removal: {len(participants_after)}")
        
        # Step 8: Test cannot remove host
        print("\n8. Testing host cannot be removed...")
        remove_host_result = remove_user_from_session(host_token, session_id, host_user['username'])
        assert not remove_host_result, "❌ Host was able to remove themselves (should be forbidden)"
        
        print("✅ Host correctly cannot be removed")
        
        # Cleanup
        print("\n9. Cleaning up...")
        cleanup_user_sessions(host_token)
        cleanup_user_sessions(user_token)
        print("✅ Cleanup completed")
        
        print("\n" + "=" * 45)
        print("🎉 All remove user tests PASSED!")
        return True
        
    except Exception as e:
        print(f"\n❌ Remove user test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_all_tests():
    """Run all tests and return standardized format"""
    success = test_remove_user()
    if success:
        return (100.0, 8, 8)  # 8 test steps all passed
    else:
        return (0.0, 0, 8)  # All 8 test steps failed

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
                'title': 'Remove User Test Session',
                'subject': 'testing',
                'description': 'Testing remove user functionality',
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

def remove_user_from_session(token, session_id, username):
    """Remove a user from session"""
    try:
        response = requests.post(f"{API_URL}/sessions/{session_id}/remove-user",
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            json={'username': username}
        )
        
        if response.status_code == 200:
            return True
        else:
            print(f"    Remove failed ({response.status_code}): {response.text}")
            return False
    except Exception as e:
        print(f"    Remove error: {e}")
        return False

def cleanup_user_sessions(token):
    """Clean up all sessions for a user"""
    try:
        requests.delete(f"{API_URL}/sessions/cleanup-user",
            headers={'Authorization': f'Bearer {token}'}
        )
    except:
        pass

if __name__ == "__main__":
    print("Starting Remove User Test...")
    print("Make sure the server is running on http://localhost:5001")
    print()
    
    success = test_remove_user()
    
    if success:
        print("\n🎉 Remove user test completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Remove user test failed!")
        sys.exit(1)