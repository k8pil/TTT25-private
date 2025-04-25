"""
Main routes for Interview Advisor application
"""

import os
import time
from flask import Blueprint, render_template, redirect, url_for, request, jsonify

# Create blueprint
main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def home():
    """Render the home page"""
    return render_template('index.html')


@main_bp.route('/results')
def results():
    """Render the results page"""
    return render_template('results.html')


@main_bp.route('/upload-resume', methods=['POST'])
def upload_resume():
    """Handle resume upload"""
    if 'resume' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['resume']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Save the resume temporarily
    filename = f"resume_{int(time.time())}.pdf"
    filepath = os.path.join('uploads', filename)
    os.makedirs('uploads', exist_ok=True)
    file.save(filepath)

    return jsonify({"success": True, "resume_id": filename})
