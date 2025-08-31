#!/usr/bin/env python3
"""
WebSocket Stress Test for Real-time Collaboration Features
Tests: Real-time chat, question suggestions, typing indicators, session updates

Requirements: pip install python-socketio requests

Run with: python websocket_stress_test.py
"""

try:
    import socketio
except ImportError:
    print("❌ CRITICAL: python-socketio not available. Cannot test WebSocket functionality.")
    print("Install with: pip install python-socketio[client]")
    import sys
    sys.exit(1)
import requests
import time
import threading
import random
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# Import test configuration
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from test_config import get_primary_api_url

# Configuration
API_URL = get_primary_api_url()
WS_URL = get_primary_api_url()
NUM_CONCURRENT_USERS = 5
TEST_DURATION = 10  # seconds
MESSAGE_FREQUENCY = 2  # messages per second per user (reduced frequency for more users)

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

def log(message, color=Colors.CYAN):
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"{color}[{timestamp}] {message}{Colors.END}")

class WebSocketTestUser:
    """Individual user for WebSocket testing"""

    def __init__(self, user_id):
        self.user_id = user_id
        self.username = f"ws_user_{user_id}"
        self.token = None
        self.session_id = None
        self.session_code = None
        self.sio = socketio.Client(logger=False, engineio_logger=False)

        # Statistics
        self.messages_sent = 0
        self.messages_received = 0
        self.questions_sent = 0
        self.questions_received = 0
        self.events_received = 0
        self.connection_errors = 0
        self.connected = False

        # Setup event handlers
        self.setup_handlers()

    def setup_handlers(self):
        """Setup WebSocket event handlers"""

        @self.sio.event
        def connect():
            self.connected = True
            log(f"🔌 {self.username} connected", Colors.GREEN)

        @self.sio.event
        def disconnect():
            self.connected = False
            log(f"🔌 {self.username} disconnected", Colors.RED)

        @self.sio.event
        def connected(data):
            log(f"✅ {self.username} received connected event", Colors.GREEN)

        @self.sio.event
        def new_chat_message(data):
            self.messages_received += 1
            self.events_received += 1
            if data.get('username') != self.username:  # Don't count own messages
                log(f"💬 {self.username} received: {data.get('message', '')[:30]}...", Colors.BLUE)

        @self.sio.event
        def new_question_suggestion(data):
            self.questions_received += 1
            self.events_received += 1
            log(f"❓ {self.username} received question suggestion", Colors.YELLOW)

        @self.sio.event
        def user_joined_room(data):
            self.events_received += 1
            log(f"👋 {self.username} saw user join: {data.get('username')}", Colors.CYAN)

        @self.sio.event
        def user_left_room(data):
            self.events_received += 1
            log(f"👋 {self.username} saw user leave: {data.get('username')}", Colors.CYAN)

        @self.sio.event
        def user_typing(data):
            self.events_received += 1
            # Don't log typing events (too noisy)

        @self.sio.event
        def error(data):
            self.connection_errors += 1
            log(f"❌ {self.username} error: {data}", Colors.RED)

    def login(self):
        """Login and get authentication token"""
        try:
            response = requests.post(f"{API_URL}/api/auth/login",
                                   json={"username": self.username})
            if response.status_code == 200:
                self.token = response.json().get("token")
                return True
            return False
        except Exception as e:
            log(f"❌ Login failed for {self.username}: {e}", Colors.RED)
            return False

    def connect_websocket(self):
        """Connect to WebSocket server"""
        try:
            # Connect with authentication
            headers = {}
            if self.token:
                headers['Authorization'] = f'Bearer {self.token}'

            self.sio.connect(WS_URL, headers=headers)
            time.sleep(0.1)  # Wait for connection
            return self.connected
        except Exception as e:
            log(f"❌ WebSocket connection failed for {self.username}: {e}", Colors.RED)
            return False

    def join_session_room(self, session_id):
        """Join a session room for real-time updates"""
        try:
            self.session_id = session_id
            self.sio.emit('join_session_room', {'session_id': session_id})
            return True
        except Exception as e:
            log(f"❌ Failed to join session room: {e}", Colors.RED)
            return False

    def send_chat_message(self, message):
        """Send a chat message via WebSocket"""
        try:
            self.sio.emit('send_chat_message', {
                'session_id': self.session_id,
                'message': message
            })
            self.messages_sent += 1
            return True
        except Exception as e:
            self.connection_errors += 1
            return False

    def suggest_question(self, question_text):
        """Suggest a question via WebSocket"""
        try:
            self.sio.emit('suggest_question', {
                'session_id': self.session_id,
                'question_text': question_text,
                'difficulty': random.choice(['easy', 'medium', 'hard']),
                'type': random.choice(['multiple_choice', 'open_ended', 'coding'])
            })
            self.questions_sent += 1
            return True
        except Exception as e:
            self.connection_errors += 1
            return False

    def send_typing_indicator(self, is_typing):
        """Send typing indicator"""
        try:
            self.sio.emit('typing_indicator', {
                'session_id': self.session_id,
                'is_typing': is_typing
            })
            return True
        except Exception as e:
            self.connection_errors += 1
            return False

    def disconnect(self):
        """Disconnect from WebSocket"""
        try:
            if self.connected:
                self.sio.disconnect()
        except Exception as e:
            log(f"❌ Disconnect error for {self.username}: {e}", Colors.RED)

class WebSocketStressTest:
    """Main WebSocket stress testing class"""

    def __init__(self):
        self.users = []
        self.session_id = None
        self.session_code = None
        self.test_running = False
        self.start_time = None

        # Global statistics
        self.total_messages_sent = 0
        self.total_messages_received = 0
        self.total_questions_sent = 0
        self.total_questions_received = 0
        self.total_events_received = 0
        self.total_errors = 0

    def setup_test_session(self):
        """Create a test session for WebSocket testing"""
        log("🏗️ Setting up test session...", Colors.YELLOW)

        # Create host user for session creation
        host_user = WebSocketTestUser(999)  # Special ID for host
        if not host_user.login():
            log("❌ Failed to login host user", Colors.RED)
            return False

        # Create session
        session_data = {
            "title": "WebSocket Stress Test Session",
            "subject": "websocket_testing",
            "settings": {
                "max_participants": NUM_CONCURRENT_USERS + 5,
                "allow_llm": True,
                "collaborative_mode": True
            }
        }

        headers = {"Authorization": f"Bearer {host_user.token}"}
        response = requests.post(f"{API_URL}/api/sessions/create",
                               json=session_data, headers=headers)

        if response.status_code == 201:
            session_info = response.json().get("session", {})
            self.session_id = session_info.get("session_id")
            self.session_code = session_info.get("session_code")
            log(f"✅ Created session: {self.session_code}", Colors.GREEN)
            return True
        else:
            log(f"❌ Failed to create session: {response.status_code}", Colors.RED)
            return False

    def create_test_users(self):
        """Create and login test users"""
        log(f"👥 Creating {NUM_CONCURRENT_USERS} test users...", Colors.YELLOW)

        self.users = []
        for i in range(NUM_CONCURRENT_USERS):
            user = WebSocketTestUser(i)
            if user.login():
                # Join the session as a participant
                if self.join_user_to_session(user):
                    self.users.append(user)
                else:
                    log(f"❌ Failed to join user {i} to session", Colors.RED)
            else:
                log(f"❌ Failed to create user {i}", Colors.RED)

        log(f"✅ Created {len(self.users)} users successfully", Colors.GREEN)
        return len(self.users) > 0

    def join_user_to_session(self, user):
        """Join a user to the test session"""
        try:
            headers = {"Authorization": f"Bearer {user.token}"}
            response = requests.post(f"{API_URL}/api/sessions/join/{self.session_code}",
                                   headers=headers)
            return response.status_code == 200
        except Exception as e:
            log(f"❌ Failed to join user to session: {e}", Colors.RED)
            return False

    def connect_users_to_websocket(self):
        """Connect all users to WebSocket and join session"""
        log("🔌 Connecting users to WebSocket...", Colors.YELLOW)

        connected_users = 0
        for user in self.users:
            if user.connect_websocket():
                if user.join_session_room(self.session_id):
                    connected_users += 1
                    time.sleep(0.1)  # Stagger connections
                else:
                    user.disconnect()

        log(f"✅ {connected_users}/{len(self.users)} users connected to WebSocket", Colors.GREEN)
        return connected_users > 0

    def simulate_user_activity(self, user, duration):
        """Simulate realistic user activity for one user"""
        end_time = time.time() + duration

        messages = [
            "Hello everyone!",
            "Great question!",
            "I think we should add more algorithm problems",
            "What about system design questions?",
            "Let's focus on the fundamentals",
            "This is a good collaborative approach",
            "I suggest we add some coding challenges",
            "How about behavioral questions too?",
            "We're making good progress!",
            "Let's wrap up soon"
        ]

        questions = [
            "What is the time complexity of merge sort?",
            "Explain the difference between REST and GraphQL",
            "How would you design a chat application?",
            "What are the principles of SOLID design?",
            "Implement a binary search algorithm",
            "Describe the CAP theorem",
            "What is dependency injection?",
            "How do you handle race conditions?",
            "Explain microservices architecture",
            "What is the difference between SQL and NoSQL?"
        ]

        message_interval = 1.0 / MESSAGE_FREQUENCY
        last_message_time = 0

        while time.time() < end_time and self.test_running:
            current_time = time.time()

            # Send messages at specified frequency
            if current_time - last_message_time >= message_interval:
                if random.random() < 0.7:  # 70% chance to send chat message
                    message = random.choice(messages)
                    user.send_chat_message(f"{message} (from {user.username})")
                else:  # 30% chance to suggest question
                    question = random.choice(questions)
                    user.suggest_question(question)

                last_message_time = current_time

            # Occasionally send typing indicators
            if random.random() < 0.1:  # 10% chance per iteration
                user.send_typing_indicator(True)
                time.sleep(0.5)
                user.send_typing_indicator(False)

            time.sleep(0.1)  # Small delay between actions

    def run_stress_test(self):
        """Run the main stress test"""
        log("🚀 Starting WebSocket stress test...", Colors.BOLD + Colors.CYAN)

        self.test_running = True
        self.start_time = time.time()

        # Start user activity simulation
        with ThreadPoolExecutor(max_workers=NUM_CONCURRENT_USERS) as executor:
            futures = [
                executor.submit(self.simulate_user_activity, user, TEST_DURATION)
                for user in self.users
            ]

            # Monitor progress
            for i in range(TEST_DURATION):
                time.sleep(1)
                if i % 10 == 0:  # Update every 10 seconds
                    self.print_live_stats()

            # Wait for all users to finish
            for future in futures:
                future.result()

        self.test_running = False

    def print_live_stats(self):
        """Print live statistics during test"""
        elapsed = time.time() - self.start_time

        # Aggregate stats
        total_sent = sum(u.messages_sent + u.questions_sent for u in self.users)
        total_received = sum(u.messages_received + u.questions_received for u in self.users)
        total_events = sum(u.events_received for u in self.users)
        total_errors = sum(u.connection_errors for u in self.users)
        connected = sum(1 for u in self.users if u.connected)

        log(f"📊 [{elapsed:.0f}s] Connected: {connected}/{len(self.users)} | "
            f"Sent: {total_sent} | Received: {total_received} | "
            f"Events: {total_events} | Errors: {total_errors}", Colors.BLUE)

    def cleanup(self):
        """Disconnect all users and cleanup"""
        log("🧹 Cleaning up...", Colors.YELLOW)

        for user in self.users:
            user.disconnect()

        # Wait a moment for disconnections
        time.sleep(1)

    def print_final_results(self):
        """Print comprehensive final results"""
        total_time = time.time() - self.start_time

        # Aggregate all statistics
        stats = {
            'messages_sent': sum(u.messages_sent for u in self.users),
            'messages_received': sum(u.messages_received for u in self.users),
            'questions_sent': sum(u.questions_sent for u in self.users),
            'questions_received': sum(u.questions_received for u in self.users),
            'events_received': sum(u.events_received for u in self.users),
            'connection_errors': sum(u.connection_errors for u in self.users),
            'final_connected': sum(1 for u in self.users if u.connected)
        }

        total_sent = stats['messages_sent'] + stats['questions_sent']
        total_received = stats['messages_received'] + stats['questions_received']

        # Calculate rates
        messages_per_second = total_sent / total_time if total_time > 0 else 0
        events_per_second = stats['events_received'] / total_time if total_time > 0 else 0
        error_rate = stats['connection_errors'] / total_sent * 100 if total_sent > 0 else 0

        # Delivery rate (approximate - doesn't account for cross-user messaging)
        delivery_rate = (total_received / total_sent * 100) if total_sent > 0 else 0

        log("\n" + "=" * 60, Colors.CYAN)
        log("🎯 WEBSOCKET STRESS TEST RESULTS", Colors.BOLD + Colors.CYAN)
        log("=" * 60, Colors.CYAN)

        log(f"⏱️ Duration: {total_time:.2f} seconds", Colors.WHITE)
        log(f"👥 Users: {len(self.users)} (Connected at end: {stats['final_connected']})", Colors.WHITE)
        log(f"📤 Messages sent: {stats['messages_sent']}", Colors.GREEN)
        log(f"❓ Questions sent: {stats['questions_sent']}", Colors.GREEN)
        log(f"📥 Messages received: {stats['messages_received']}", Colors.BLUE)
        log(f"❓ Questions received: {stats['questions_received']}", Colors.BLUE)
        log(f"🎉 Total events: {stats['events_received']}", Colors.YELLOW)
        log(f"❌ Connection errors: {stats['connection_errors']}", Colors.RED)

        log(f"\n📊 Performance Metrics:", Colors.BOLD + Colors.WHITE)
        log(f"📈 Messages/second: {messages_per_second:.2f}", Colors.CYAN)
        log(f"📈 Events/second: {events_per_second:.2f}", Colors.CYAN)
        log(f"📈 Error rate: {error_rate:.2f}%", Colors.YELLOW if error_rate < 5 else Colors.RED)
        log(f"📈 Delivery rate: {delivery_rate:.1f}%", Colors.GREEN if delivery_rate > 80 else Colors.YELLOW)

        # Performance assessment
        log(f"\n🏆 Assessment:", Colors.BOLD + Colors.WHITE)
        if error_rate < 1 and delivery_rate > 95:
            log("🌟 EXCELLENT! WebSocket performance is outstanding", Colors.GREEN + Colors.BOLD)
        elif error_rate < 5 and delivery_rate > 80:
            log("✅ GOOD! WebSocket performance is solid", Colors.GREEN)
        elif error_rate < 10 and delivery_rate > 60:
            log("⚠️ ACCEPTABLE! Some optimization needed", Colors.YELLOW)
        else:
            log("🚨 POOR! Significant issues with WebSocket performance", Colors.RED)

        # Recommendations
        log(f"\n💡 Recommendations:", Colors.BOLD + Colors.WHITE)
        if error_rate > 5:
            log("• Investigate connection stability issues", Colors.WHITE)
            log("• Consider connection pooling and retry logic", Colors.WHITE)
        if delivery_rate < 90:
            log("• Check message delivery guarantees", Colors.WHITE)
            log("• Verify room join/leave logic", Colors.WHITE)
        if messages_per_second < 50:
            log("• Consider WebSocket performance optimization", Colors.WHITE)
            log("• Review server-side event handling", Colors.WHITE)

        log("• Monitor WebSocket connections in production", Colors.WHITE)
        log("• Implement heartbeat/ping-pong for connection health", Colors.WHITE)
        log("• Add rate limiting to prevent abuse", Colors.WHITE)

    def run_full_test(self):
        """Run the complete WebSocket stress test"""
        try:
            if not self.setup_test_session():
                return False

            if not self.create_test_users():
                return False

            if not self.connect_users_to_websocket():
                return False

            self.run_stress_test()
            self.print_final_results()
            return True

        except KeyboardInterrupt:
            log("\n⚠️ Test interrupted by user", Colors.YELLOW)
            return False
        except Exception as e:
            log(f"\n🚨 Test failed with error: {e}", Colors.RED)
            import traceback
            traceback.print_exc()
            return False
        finally:
            self.cleanup()

def test_websocket_collaboration():
    """
    Test function for WebSocket collaboration functionality
    Returns True if test passes, False if it fails
    """
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║          WEBSOCKET COLLABORATION TEST                    ║")
    print("║                                                          ║")
    print(f"║  Users: {NUM_CONCURRENT_USERS:<3} | Duration: {TEST_DURATION:<3}s | Frequency: {MESSAGE_FREQUENCY}/s per user  ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}\n")

    test = WebSocketStressTest()
    success = test.run_full_test()

    if success:
        log("\n✅ WebSocket collaboration test PASSED!", Colors.GREEN + Colors.BOLD)
        return True
    else:
        log("\n❌ WebSocket collaboration test FAILED!", Colors.RED + Colors.BOLD)
        return False

if __name__ == "__main__":
    import sys
    success = test_websocket_collaboration()
    sys.exit(0 if success else 1)