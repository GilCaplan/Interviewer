#!/usr/bin/env python3
"""
Debug script to test login functionality
"""
import requests
import json

def test_login():
    url = "http://localhost:5000/api/auth/login"
    data = {"username": "test_user_123"}
    headers = {"Content-Type": "application/json"}
    
    print("Testing login...")
    print(f"URL: {url}")
    print(f"Data: {data}")
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        try:
            response_data = response.json()
            print(f"Response JSON: {json.dumps(response_data, indent=2)}")
        except:
            print(f"Response Text: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_login()