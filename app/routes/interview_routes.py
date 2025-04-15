"""
Interview routes for Interview Advisor application
"""

from app.services.interview_service import InterviewService
import os
import sys
import json
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for

# Create blueprint
interview_bp = Blueprint('interview', __name__)

# Import interview service (to be implemented)

# Global interview service instance
interview_service = None


@interview_bp.route('/')
def interview_page():
    """Render the interview page"""
    return render_template('interview.html')


@interview_bp.route('/start', methods=['POST'])
def start_interview():
    """Start an interview session"""
    global interview_service

    try:
        # Get resume_id from request
        data = request.get_json() or {}
        resume_id = data.get('resume_id', 'default')

        # Initialize interview service
        interview_service = InterviewService(resume_id)

        # Start the interview
        intro_question = interview_service.start_interview()

        # Store session ID
        session['interview_session_id'] = interview_service.session_id

        return jsonify({
            "success": True,
            "session_id": interview_service.session_id,
            "question": intro_question
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@interview_bp.route('/answer', methods=['POST'])
def process_answer():
    """Process an interview answer and get next question"""
    global interview_service

    try:
        # Check if interview is in progress
        if not interview_service:
            return jsonify({"error": "No interview in progress"}), 400

        # Get answer from request
        data = request.get_json() or {}
        answer = data.get('answer', '')

        if not answer:
            return jsonify({"error": "Answer is required"}), 400

        # Process the answer and get next question
        next_question = interview_service.process_answer(answer)

        return jsonify({
            "success": True,
            "question": next_question
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@interview_bp.route('/end', methods=['POST'])
def end_interview():
    """End the interview and get recommendations"""
    global interview_service

    try:
        # Check if interview is in progress
        if not interview_service:
            return jsonify({"error": "No interview in progress"}), 400

        # End the interview
        closing_statement = interview_service.end_interview()

        # Get recommendations
        recommendations = interview_service.get_recommendations()

        # Clear the interview service
        session_id = interview_service.session_id
        interview_service = None

        return jsonify({
            "success": True,
            "session_id": session_id,
            "closing": closing_statement,
            "recommendations": recommendations
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@interview_bp.route('/audio', methods=['POST'])
def process_audio():
    """Process audio answer"""
    global interview_service

    try:
        # Check if interview is in progress
        if not interview_service:
            return jsonify({"error": "No interview in progress"}), 400

        # Check if audio file was uploaded
        if 'audio' not in request.files:
            return jsonify({"error": "No audio file"}), 400

        audio_file = request.files['audio']

        # Save the audio file temporarily
        filename = f"audio_{int(time.time())}.wav"
        filepath = os.path.join('uploads', filename)
        audio_file.save(filepath)

        # Process the audio file
        text = interview_service.process_audio(filepath)

        return jsonify({
            "success": True,
            "text": text
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
