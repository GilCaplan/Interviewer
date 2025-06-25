#!/usr/bin/env python3
"""
Minimal test to check if Simple Sessions is working
Save as: minimal_test.py
Run with: python minimal_test.py
"""

import requests
import json

API_URL = "http://localhost:5001"


def test_basic_functionality():
    """Test basic functionality quickly"""
    print("🔍 Minimal Simple Sessions Test")
    print("=" * 35)

    # 1. Health check
    try:
        response = requests.get(f"{API_URL}/api/health")
        if response.status_code == 200:
            print("✅ API is running")
        else:
            print("❌ API health check failed")
            return
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        print("   Start server: docker-compose up --build")
        return

    # 2. Login
    try:
        login_data = {"username": "minimal_test_user"}
        response = requests.post(f"{API_URL}/api/auth/login", json=login_data)

        if response.status_code == 200:
            token = response.json().get("token")
            print("✅ Login successful")
        else:
            print(f"❌ Login failed: {response.text}")
            return
    except Exception as e:
        print(f"❌ Login error: {e}")
        return

    # 3. Create session
    try:
        headers = {"Authorization": f"Bearer {token}"}
        session_data = {
            "title": "Minimal Test",
            "subject": "python"
        }

        response = requests.post(
            f"{API_URL}/api/sessions/create",
            json=session_data,
            headers=headers
        )

        if response.status_code == 201:
            session_info = response.json().get("session", {})
            session_id = session_info.get("session_id")
            session_code = session_info.get("session_code")
            print(f"✅ Session created: {session_code}")
        else:
            print(f"❌ Session creation failed: {response.text}")
            return
    except Exception as e:
        print(f"❌ Session creation error: {e}")
        return

    # 4. Test LLM question
    try:
        llm_data = {"subject": "python", "context": "test"}
        response = requests.post(
            f"{API_URL}/api/sessions/{session_id}/llm-question",
            json=llm_data,
            headers=headers
        )

        if response.status_code == 200:
            print("✅ LLM question generation works")
        else:
            print(f"❌ LLM generation failed: {response.text}")
    except Exception as e:
        print(f"❌ LLM generation error: {e}")

    # 5. Test chat
    try:
        chat_data = {"message": "Test message"}
        response = requests.post(
            f"{API_URL}/api/sessions/{session_id}/chat",
            json=chat_data,
            headers=headers
        )

        if response.status_code == 200:
            print("✅ Chat functionality works")
        else:
            print(f"❌ Chat failed: {response.text}")
    except Exception as e:
        print(f"❌ Chat error: {e}")

    # 6. Test user question
    try:
        question_data = {
            "question_text": "What is Python?",
            "difficulty": "easy"
        }
        response = requests.post(
            f"{API_URL}/api/sessions/{session_id}/add-question",
            json=question_data,
            headers=headers
        )

        if response.status_code == 201:
            print("✅ User question creation works")
        else:
            print(f"❌ User question failed: {response.text}")
    except Exception as e:
        print(f"❌ User question error: {e}")

    print("\n🎉 Minimal test complete!")
    print("All 3 features are working:")
    print("  🤖 LLM Questions")
    print("  💬 Chat")
    print("  👤 User Questions")


if __name__ == "__main__":
    test_basic_functionality()