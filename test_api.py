import requests
import json
import time

# Test creating a session
try:
    print("Creating a new session...")
    response = requests.post(
        "http://localhost:5000/api/session",
        json={"resume_id": "test_resume"},
        headers={"Content-Type": "application/json"}
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")

    session_data = response.json()
    session_id = session_data.get("session_id")

    if session_id:
        # Test getting the session
        print("\nGetting session info...")
        response = requests.get(
            f"http://localhost:5000/api/session/{session_id}",
            headers={"Content-Type": "application/json"}
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")

        # Test sending posture metrics
        print("\nSending posture metrics...")
        response = requests.post(
            f"http://localhost:5000/api/session/{session_id}/posture-metrics",
            json={
                "handDetected": True,
                "handDetectionDuration": 5.2,
                "notFacingCamera": False,
                "notFacingDuration": 0,
                "badPostureDetected": True,
                "badPostureDuration": 3.5
            },
            headers={"Content-Type": "application/json"}
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")

        # Test getting all sessions
        print("\nGetting all sessions...")
        response = requests.get(
            "http://localhost:5000/api/sessions",
            headers={"Content-Type": "application/json"}
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")

except Exception as e:
    print(f"Error: {str(e)}")
