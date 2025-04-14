"""
API routes for Interview Advisor application
"""

import os
import time
import json
from flask import Blueprint, request, jsonify

# Create blueprint
api_bp = Blueprint('api', __name__)

# Mock session storage (in-memory)
active_sessions = {}


@api_bp.route('/session', methods=['POST'])
def create_session():
    """Create a new session (without database)."""
    try:
        print("Received request to create new session")
        data = request.get_json()
        print(f"Request data: {data}")

        # Validate request
        if not data:
            print("Error: No JSON data in request")
            return jsonify({"error": "Invalid request. No JSON data provided"}), 400

        resume_id = data.get('resume_id', 'default')
        print(f"Using resume_id: {resume_id}")

        # Create unique session ID
        session_id = f"session_{int(time.time())}"
        print(f"Generated session_id: {session_id}")

        # Store session in memory
        active_sessions[session_id] = {
            "resume_id": resume_id,
            "start_time": time.time(),
            "end_time": None,
            "metrics": {
                "posture": [],
                "audio": []
            }
        }

        print(f"Session {session_id} successfully created")
        return jsonify({
            "status": "success",
            "message": "Session created",
            "session_id": session_id
        })

    except Exception as e:
        print(f"Exception in create_session: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@api_bp.route('/session/<session_id>/end', methods=['POST'])
def end_session(session_id):
    """End a session."""
    try:
        data = request.get_json() or {}
        questions_count = data.get('questions_count', 0)

        if session_id in active_sessions:
            active_sessions[session_id]["end_time"] = time.time()
            active_sessions[session_id]["questions_count"] = questions_count
            return jsonify({
                "status": "success",
                "message": "Session ended"
            })
        else:
            return jsonify({"error": "Session not found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route('/session/<session_id>/posture-metrics', methods=['POST'])
def save_posture_metrics(session_id):
    """Save posture metrics (without database)."""
    try:
        data = request.get_json()

        # Validate request
        if not data:
            return jsonify({"error": "Invalid request. Metrics data is required"}), 400

        if session_id not in active_sessions:
            return jsonify({"error": "Session not found"}), 404

        # Just log the metrics instead of saving to database
        print(f"Received posture metrics for session {session_id}: {data}")

        # Store in memory
        metrics = {
            "timestamp": time.time(),
            "hand_detected": data.get("handDetected", False),
            "hand_detection_duration": data.get("handDetectionDuration", 0),
            "not_facing_camera": data.get("notFacingCamera", False),
            "not_facing_duration": data.get("notFacingDuration", 0),
            "bad_posture_detected": data.get("badPostureDetected", False),
            "bad_posture_duration": data.get("badPostureDuration", 0)
        }

        active_sessions[session_id]["metrics"]["posture"].append(metrics)

        return jsonify({
            "status": "success",
            "message": "Posture metrics received"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route('/session/<session_id>/audio-metrics', methods=['POST'])
def save_audio_metrics(session_id):
    """Save audio metrics (without database)."""
    try:
        data = request.get_json()

        # Validate request
        if not data:
            return jsonify({"error": "Invalid request. Metrics data is required"}), 400

        if session_id not in active_sessions:
            return jsonify({"error": "Session not found"}), 404

        # Just log the metrics instead of saving to database
        print(f"Received audio metrics for session {session_id}: {data}")

        # Store in memory
        metrics = {
            "timestamp": time.time(),
            "fluency_score": data.get("fluency_score", 0),
            "is_stuttering": data.get("is_stuttering", False),
            "word_count": data.get("word_count", 0),
            "filler_word_count": data.get("filler_word_count", 0),
            "speech_rate": data.get("speech_rate", 0),
            "transcript": data.get("transcription", "")
        }

        active_sessions[session_id]["metrics"]["audio"].append(metrics)

        return jsonify({
            "status": "success",
            "message": "Audio metrics received"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route('/sessions', methods=['GET'])
def get_sessions():
    """Get all sessions."""
    try:
        sessions_list = [
            {
                "session_id": session_id,
                "start_time": session_data["start_time"],
                "end_time": session_data["end_time"],
                "resume_id": session_data["resume_id"]
            }
            for session_id, session_data in active_sessions.items()
        ]
        return jsonify(sessions_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route('/session/<session_id>', methods=['GET'])
def get_session(session_id):
    """Get a specific session."""
    try:
        if session_id in active_sessions:
            session_data = active_sessions[session_id]
            return jsonify({
                "session_id": session_id,
                "start_time": session_data["start_time"],
                "end_time": session_data["end_time"],
                "resume_id": session_data["resume_id"]
            })
        else:
            return jsonify({"error": "Session not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route('/session/<session_id>/metrics', methods=['GET'])
def get_session_metrics(session_id):
    """Get all metrics for a specific session."""
    try:
        if session_id in active_sessions:
            return jsonify(active_sessions[session_id]["metrics"])
        else:
            return jsonify({"error": "Session not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
