#!/usr/bin/env python

"""
Sample Integration Script

This script demonstrates how to integrate the Interview Advisor with a main site.
"""

import sys
import os
from flask import Flask, render_template, request, jsonify, redirect, url_for
from interview_advisor.integration import mainmenu, getresumesir, list_available_resumes, get_resume_path
from interview_advisor.api import api_app

# Initialize Flask app
app = Flask(__name__)

# Register API blueprint
app.register_blueprint(api_app, url_prefix='/api')

# Function to get menu options as a formatted string for the interviewer's chat


def get_formatted_menu():
    menu_items = mainmenu()
    menu_text = "Please select an option:\n\n"

    for i, item in enumerate(menu_items, 1):
        menu_text += f"{i}. {item}\n"

    return menu_text


@app.route('/')
def home():
    """Render home page with menu options."""
    # Get menu options
    menu_items = mainmenu()

    # Get formatted menu for interviewer chat
    interviewer_message = get_formatted_menu()

    # Get available resumes
    resume_dir = getresumesir()
    resumes = list_available_resumes()

    # Return rendered template (in a real application)
    # return render_template('home.html', menu_items=menu_items, resumes=resumes)

    # For demo purposes, return JSON response
    return jsonify({
        'menu_items': menu_items,
        'interviewer_message': interviewer_message,
        'resume_directory': resume_dir,
        'available_resumes': resumes
    })


@app.route('/upload_resume', methods=['POST'])
def upload_resume():
    """Handle resume upload."""
    if 'resume' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['resume']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if file:
        # Get the resume directory
        resume_dir = getresumesir()

        # Save the file
        filename = os.path.join(resume_dir, file.filename)
        file.save(filename)

        return jsonify({'success': True, 'resume_id': file.filename})

    return jsonify({'error': 'File upload failed'}), 500


@app.route('/start_interview/<resume_id>')
def start_interview(resume_id):
    """Start an interview session using the specified resume."""
    # Get the full path to the resume
    resume_path = get_resume_path(resume_id)

    if not resume_path:
        return jsonify({'error': 'Resume not found'}), 404

    # In a real application, you would initialize the interview session here
    # and return the appropriate response

    return jsonify({
        'success': True,
        'message': f'Interview started with resume: {resume_id}',
        'resume_path': resume_path
    })


@app.route('/menu')
def get_menu():
    """Return the menu options as JSON."""
    return jsonify(mainmenu())


if __name__ == '__main__':
    # Run the Flask app
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
