#!/usr/bin/env python3
"""
Session Management Offline Test Suite
Tests session management logic without requiring a running server
"""

import time
import uuid
from datetime import datetime, timedelta

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def log(message, color=Colors.CYAN):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{color}[{timestamp}] {message}{Colors.END}")

class SessionManager:
    """Mock session manager that tests the logic"""
    
    def __init__(self):
        self.sessions = {}
        self.participants = {}
    
    def generate_session_code(self):
        """Generate a 6-character session code"""
        import random
        import string
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    
    def create_session(self, host_id, title, subject="general"):
        """Create a new session"""
        session_id = str(uuid.uuid4())
        session_code = self.generate_session_code()
        
        session = {
            "session_id": session_id,
            "session_code": session_code,
            "title": title,
            "subject": subject,
            "host": host_id,
            "created_at": datetime.now(),
            "participants": [host_id],
            "questions": [],
            "settings": {
                "max_participants": 10,
                "max_questions": 20,
                "viewing_mode": "edit"
            }
        }
        
        self.sessions[session_id] = session
        return session
    
    def join_session(self, user_id, session_code):
        """Join a session by code"""
        for session in self.sessions.values():
            if session["session_code"] == session_code:
                if user_id not in session["participants"]:
                    if len(session["participants"]) < session["settings"]["max_participants"]:
                        session["participants"].append(user_id)
                        return session
                    else:
                        return None  # Session full
                return session  # Already joined
        return None  # Session not found
    
    def add_question(self, session_id, question_data):
        """Add a question to a session"""
        if session_id in self.sessions:
            question_id = str(uuid.uuid4())
            question = {
                "question_id": question_id,
                "question_number": len(self.sessions[session_id]["questions"]) + 1,
                "created_at": datetime.now(),
                **question_data
            }
            self.sessions[session_id]["questions"].append(question)
            return question
        return None
    
    def remove_participant(self, session_id, user_id, requesting_user_id):
        """Remove a participant from session (host only)"""
        if session_id not in self.sessions:
            return False
        
        session = self.sessions[session_id]
        
        # Only host can remove participants
        if requesting_user_id != session["host"]:
            return False
            
        # Cannot remove host
        if user_id == session["host"]:
            return False
            
        if user_id in session["participants"]:
            session["participants"].remove(user_id)
            return True
        
        return False
    
    def cleanup_session(self, session_id, requesting_user_id):
        """Delete a session (host only)"""
        if session_id not in self.sessions:
            return False
            
        session = self.sessions[session_id]
        
        # Only host can delete session
        if requesting_user_id != session["host"]:
            return False
            
        del self.sessions[session_id]
        return True

def test_session_management_offline():
    """Test session management logic offline"""
    log("🧪 TESTING SESSION MANAGEMENT LOGIC (OFFLINE)", Colors.BOLD + Colors.CYAN)
    log("=" * 60, Colors.CYAN)
    
    manager = SessionManager()
    passed = 0
    total = 0
    
    # Test 1: Session creation
    host_id = "host_user_123"
    session = manager.create_session(host_id, "Test Session", "algorithms")
    
    if (session and session["host"] == host_id and 
        len(session["session_code"]) == 6 and
        session["title"] == "Test Session"):
        log("✅ Session Creation", Colors.GREEN)
        passed += 1
    else:
        log("❌ Session Creation", Colors.RED)
    total += 1
    
    session_id = session["session_id"] if session else None
    session_code = session["session_code"] if session else None
    
    # Test 2: Session joining
    participant_id = "participant_456"
    joined_session = manager.join_session(participant_id, session_code)
    
    if (joined_session and participant_id in joined_session["participants"] and
        len(joined_session["participants"]) == 2):
        log("✅ Session Joining", Colors.GREEN)
        passed += 1
    else:
        log("❌ Session Joining", Colors.RED)
    total += 1
    
    # Test 3: Question management
    question_data = {
        "type": "open_ended",
        "question_text": "What is an algorithm?",
        "difficulty": "medium"
    }
    
    question = manager.add_question(session_id, question_data)
    
    if (question and question["question_text"] == "What is an algorithm?" and
        question["question_number"] == 1):
        log("✅ Question Management", Colors.GREEN)
        passed += 1
    else:
        log("❌ Question Management", Colors.RED)
    total += 1
    
    # Test 4: Participant removal (host privilege)
    removal_success = manager.remove_participant(session_id, participant_id, host_id)
    
    if removal_success and participant_id not in manager.sessions[session_id]["participants"]:
        log("✅ Participant Removal (Host)", Colors.GREEN)
        passed += 1
    else:
        log("❌ Participant Removal (Host)", Colors.RED)
    total += 1
    
    # Test 5: Participant removal (non-host denied)
    # Re-add participant first
    manager.join_session(participant_id, session_code)
    removal_denied = not manager.remove_participant(session_id, host_id, participant_id)
    
    if removal_denied:
        log("✅ Participant Removal Denied (Non-Host)", Colors.GREEN)
        passed += 1
    else:
        log("❌ Participant Removal Denied (Non-Host)", Colors.RED)
    total += 1
    
    # Test 6: Host cannot be removed
    host_removal_denied = not manager.remove_participant(session_id, host_id, host_id)
    
    if host_removal_denied:
        log("✅ Host Removal Protection", Colors.GREEN)
        passed += 1
    else:
        log("❌ Host Removal Protection", Colors.RED)
    total += 1
    
    # Test 7: Session cleanup (host only)
    cleanup_success = manager.cleanup_session(session_id, host_id)
    
    if cleanup_success and session_id not in manager.sessions:
        log("✅ Session Cleanup (Host)", Colors.GREEN)
        passed += 1
    else:
        log("❌ Session Cleanup (Host)", Colors.RED)
    total += 1
    
    # Test 8: Participant limits
    new_session = manager.create_session("new_host", "Limit Test")
    new_session_id = new_session["session_id"]
    new_session_code = new_session["session_code"]
    
    # Fill up to max participants
    participants_added = 0
    for i in range(15):  # Try to add more than max (10)
        user_id = f"user_{i}"
        result = manager.join_session(user_id, new_session_code)
        if result and user_id in result["participants"]:
            participants_added += 1
    
    # Should be limited to max_participants (10) including host (1) = 10 total
    current_count = len(manager.sessions[new_session_id]["participants"])
    if current_count <= new_session["settings"]["max_participants"]:
        log("✅ Participant Limit Enforcement", Colors.GREEN)
        passed += 1
    else:
        log("❌ Participant Limit Enforcement", Colors.RED)
    total += 1
    
    pass_rate = (passed / total * 100) if total > 0 else 0
    
    log(f"\n📊 Session Management Tests: {passed}/{total} passed ({pass_rate:.1f}%)", Colors.CYAN)
    
    return (pass_rate, passed, total)

def run_all_tests():
    """Run all tests and return standardized format"""
    return test_session_management_offline()

if __name__ == "__main__":
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║          SESSION MANAGEMENT OFFLINE TEST SUITE          ║")
    print("║                                                          ║")
    print("║  Tests: Creation, Joining, Questions, Permissions       ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}\n")
    
    result = test_session_management_offline()
    print(f"\nTest completed with result: {result}")