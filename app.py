from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from models import db, User, Resume, UserEmotionData, SessionSummary, EyeMetrics, Performance
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from datetime import datetime, UTC
import os
import functions
import sys
from keras.models import Sequential
from keras.layers import Conv2D, MaxPooling2D, Dropout, Flatten, Dense
from tensorflow.keras.models import load_model
import numpy as np
import cv2
import base64
from video_analysis import InterviewMetricsTracker
# from body_language_decoder import BodyLanguageDecoder
import sqlite3
from interview_advisor.integration import get_menu_options, mainmenu, getresumesir
import glob
import requests
import json
import subprocess
# Import pydub
from pydub import AudioSegment
import re
from markupsafe import Markup

# Import the API blueprint
from interview_advisor.api import api_app as interview_advisor_api_blueprint

# Import the advanced Interview class and Resume Processor
from interview_advisor.interview import Interview
from interview_advisor.resume_processor import ResumeProcessor

# Import and configure Google Generative AI
import google.generativeai as genai

# Import TTS service for ElevenLabs integration
try:
    from interview_advisor.tts_service import TTSService
    TTS_AVAILABLE = True
    # Initialize TTS service
    tts_service = TTSService(silent_mode=False)
except Exception as e:
    print(f"WARNING: TTS service could not be imported: {e}")
    print("Text-to-speech functionality will be disabled.")
    TTS_AVAILABLE = False
    tts_service = None

# Add this near your other imports
from improved_career_recommendations import get_career_recommendations

load_dotenv()

# Configure Google AI Client
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
    # Initialize a basic client (specific model used within Interview class)
    ai_client = genai
else:
    print("WARNING: GOOGLE_API_KEY not found in .env. AI interview features may fail.")
    ai_client = None

app = Flask(__name__)

# Define UPLOAD_FOLDER using app.root_path *after* app is created
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Ensure the upload folder exists right after configuring it
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

app.secret_key = os.getenv('SECRET_KEY') or 'dev_secret_key_for_testing_only'

# Calculate instance path relative to project root (2 levels up from CWD)
# Note: This instance path calculation might still be fragile. Consider using app.instance_path
cwd = os.getcwd()
project_root = os.path.dirname(os.path.dirname(cwd))
instance_path = os.path.join(project_root, 'instance')

# Ensure instance directory exists
os.makedirs(instance_path, exist_ok=True)

# Define absolute paths for databases
main_db_path = os.path.join(instance_path, 'project_db.sqlite3')
eye_db_path = os.path.join(instance_path, 'eye.sqlite')

# Use absolute paths for all database URIs
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{main_db_path}'
app.config['SQLALCHEMY_BINDS'] = {
    'eye_metrics': f'sqlite:///{eye_db_path}'
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# UPLOAD_FOLDER config moved up

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # Suppress TensorFlow warnings

# Ensure the upload folder exists
# os.makedirs(UPLOAD_FOLDER, exist_ok=True) # Moved up

# Dictionary to hold active Interview instances (keyed by user_id or session_id)
active_interviews = {}

# Register the API blueprint with the /api prefix
app.register_blueprint(interview_advisor_api_blueprint, url_prefix='/api')

def build_model():
    model = Sequential()
    model.add(Conv2D(32, kernel_size=(3, 3),
              activation='relu', input_shape=(48, 48, 1)))
    model.add(Conv2D(64, kernel_size=(3, 3), activation='relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))
    model.add(Dropout(0.25))

    model.add(Conv2D(128, kernel_size=(3, 3), activation='relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))
    model.add(Conv2D(128, kernel_size=(3, 3), activation='relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))
    model.add(Dropout(0.25))

    model.add(Flatten())
    model.add(Dense(1024, activation='relu'))
    model.add(Dropout(0.5))
    model.add(Dense(7, activation='softmax'))

    return model


model = build_model()
model.load_weights('model.h5')

# Dictionary mapping emotion indices to labels
emotion_dict = {0: "Angry", 1: "Disgusted", 2: "Fearful",
                3: "Happy", 4: "Neutral", 5: "Sad", 6: "Surprised"}
# Load face cascade classifier
cascade_file_paths = [
    'haarcascade_frontalface_default.xml',
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 'haarcascade_frontalface_default.xml'),
    os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_default.xml')
]
facecasc = None
for cascade_path in cascade_file_paths:
    if os.path.exists(cascade_path):
        facecasc = cv2.CascadeClassifier(cascade_path)
        if not facecasc.empty():
            break

# decoder = BodyLanguageDecoder(model_path='Body_language.pkl')

db.init_app(app)

# Initialize databases on startup
with app.app_context():
    # Create tables in main database
    db.create_all()

    # Ensure eye metrics database exists
    try:
        # Create eye_metrics tables
        db.create_all(bind_key='eye_metrics')
        print(f"Eye metrics tables created in {eye_db_path}")
    except Exception as e:
        print(f"Error initializing eye_metrics database: {str(e)}")

        # Attempt manual initialization if SQLAlchemy fails
        try:
            # Make sure instance directory exists
            os.makedirs(instance_path, exist_ok=True)

            # Create the database file directly with SQLite
            conn = sqlite3.connect(eye_db_path)
            cursor = conn.cursor()

            # Create the eye_metrics table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS eye_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                session_id TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                hand_detection_count INTEGER DEFAULT 0,
                hand_detection_duration REAL DEFAULT 0.0,
                loss_eye_contact_count INTEGER DEFAULT 0,
                looking_away_duration REAL DEFAULT 0.0,
                bad_posture_count INTEGER DEFAULT 0,
                bad_posture_duration REAL DEFAULT 0.0,
                is_auto_save BOOLEAN DEFAULT 0
            )
            ''')

            conn.commit()
            conn.close()
            print(f"Manually created eye metrics table in {eye_db_path}")
        except Exception as e2:
            print(f"Failed manual database initialization: {str(e2)}")


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

        try:
            new_user = User(email=email, username=username,
                            password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash('Signup successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash('Username or email already exists.', 'error')
            print(e)
    return render_template('signup.html')


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please log in.', 'error')
        return redirect(url_for('home'))
    user = User.query.get(session['user_id'])
    return render_template('dashboard.html', user=user)


@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash('Please log in.', 'error')
        return redirect(url_for('home'))

    user = User.query.get(session['user_id'])

    # Fetch eye metrics data for the current user
    user_id = session['user_id']

    # Get all metrics records for this user
    metrics_data = EyeMetrics.query.filter_by(user_id=user_id).all()

    # Calculate analytics based on eye metrics data
    analytics = {}

    if metrics_data:
        # Initialize counters
        total_eye_contact_loss = 0
        total_looking_away = 0.0
        total_bad_posture_count = 0
        total_bad_posture_duration = 0.0
        total_hand_duration = 0.0
        total_interviews = len(metrics_data)

        # Max and min values
        max_eye_contact_loss = 0
        min_eye_contact_loss = float('inf')
        max_looking_away = 0.0
        min_looking_away = float('inf')
        max_bad_posture_duration = 0.0
        min_bad_posture_duration = float('inf')

        # Calculate totals and find max/min values
        for metric in metrics_data:
            # Add to totals
            total_eye_contact_loss += metric.loss_eye_contact_count
            total_looking_away += metric.looking_away_duration
            total_bad_posture_count += metric.bad_posture_count
            total_bad_posture_duration += metric.bad_posture_duration
            total_hand_duration += metric.hand_detection_duration

            # Update max values
            max_eye_contact_loss = max(
                max_eye_contact_loss, metric.loss_eye_contact_count)
            max_looking_away = max(
                max_looking_away, metric.looking_away_duration)
            max_bad_posture_duration = max(
                max_bad_posture_duration, metric.bad_posture_duration)

            # Update min values (only if not zero to avoid skewing data)
            if metric.loss_eye_contact_count > 0:
                min_eye_contact_loss = min(
                    min_eye_contact_loss, metric.loss_eye_contact_count)
            if metric.looking_away_duration > 0:
                min_looking_away = min(
                    min_looking_away, metric.looking_away_duration)
            if metric.bad_posture_duration > 0:
                min_bad_posture_duration = min(
                    min_bad_posture_duration, metric.bad_posture_duration)

        # Calculate averages
        avg_eye_contact_loss = round(total_eye_contact_loss / total_interviews)
        avg_looking_away = round(total_looking_away / total_interviews, 1)
        avg_bad_posture_count = round(
            total_bad_posture_count / total_interviews)
        avg_bad_posture_duration = round(
            total_bad_posture_duration / total_interviews, 1)
        avg_hand_duration = round(total_hand_duration / total_interviews, 1)

        # Handle case where min was never updated (no non-zero values)
        if min_eye_contact_loss == float('inf'):
            min_eye_contact_loss = 0
        if min_looking_away == float('inf'):
            min_looking_away = 0.0
        if min_bad_posture_duration == float('inf'):
            min_bad_posture_duration = 0.0

        # Get the most recent interview data for the current metrics
        latest_metric = metrics_data[0] if metrics_data else None

        # Calculate total time (estimated from durations or use a default)
        estimated_total_time = 180  # default 3 minutes if no data

        if latest_metric:
            # Try to estimate the interview duration from the metrics
            # Use hand, eye and posture durations to estimate the total time
            estimated_total_time = max(
                180,  # minimum 3 min
                latest_metric.hand_detection_duration + latest_metric.looking_away_duration + 60
            )

        # Calculate looking away ratio
        looking_away_ratio = round(
            (latest_metric.looking_away_duration / estimated_total_time) * 100) if latest_metric else 0

        # Calculate focus rate
        focus_rate = 100 - looking_away_ratio

        # Calculate posture quality
        posture_quality = round(
            100 - ((latest_metric.bad_posture_duration / estimated_total_time) * 100)) if latest_metric else 0

        # Calculate hand movement frequency (movements per minute)
        hand_frequency = round((latest_metric.hand_detection_count /
                               (estimated_total_time / 60)), 1) if latest_metric else 0

        # Calculate overall confidence score (weighted average of key metrics)
        confidence_score = round(
            (focus_rate * 0.4) +  # 40% weight to focus
            (posture_quality * 0.4) +  # 40% weight to posture
            # 20% weight to hand movement
            (min(100, 100 - (hand_frequency * 3)) * 0.2)
        )

        # Store all analytics in the dictionary
        analytics = {
            # Current session metrics (from latest interview)
            'eye_contact_loss': latest_metric.loss_eye_contact_count if latest_metric else 0,
            'looking_away': latest_metric.looking_away_duration if latest_metric else 0,
            'bad_posture_count': latest_metric.bad_posture_count if latest_metric else 0,
            'bad_posture_duration': latest_metric.bad_posture_duration if latest_metric else 0,
            'hand_duration': latest_metric.hand_detection_duration if latest_metric else 0,
            'total_time': estimated_total_time,

            # Calculated metrics
            'focus_rate': focus_rate,
            'looking_away_ratio': looking_away_ratio,
            'posture_quality': posture_quality,
            'hand_frequency': hand_frequency,
            'confidence_score': confidence_score,

            # Average metrics
            'avg_eye_contact_loss': avg_eye_contact_loss,
            'avg_looking_away': avg_looking_away,
            # Assuming avg interview is 3 min
            'avg_looking_away_ratio': round((avg_looking_away / 180) * 100),
            'avg_bad_posture_count': avg_bad_posture_count,
            'avg_bad_posture_duration': avg_bad_posture_duration,

            # Max metrics
            'max_eye_contact_loss': max_eye_contact_loss,
            'max_looking_away': round(max_looking_away, 1),
            'max_bad_posture_duration': round(max_bad_posture_duration, 1),

            # Min metrics
            'min_eye_contact_loss': min_eye_contact_loss,
            'min_looking_away': round(min_looking_away, 1),
            'min_bad_posture_duration': round(min_bad_posture_duration, 1),

            # Additional analytics
            'total_interviews': total_interviews
        }

        # Determine improvement areas (areas with the lowest scores)
        improvement_areas = []
        if focus_rate < 70:
            improvement_areas.append("Eye Contact")
        if posture_quality < 70:
            improvement_areas.append("Posture")
        if hand_frequency > 10:
            improvement_areas.append("Hand Movement")

        analytics['improvement_areas'] = ", ".join(
            improvement_areas) if improvement_areas else "None"

    return render_template('profile.html', user=user, analytics=analytics)


@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        flash('Please log in.', 'error')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    # Verify current password
    current_password = request.form['current_password']
    if not check_password_hash(user.password, current_password):
        flash('Current password is incorrect.', 'error')
        return redirect(url_for('profile'))

    # Update username if changed
    new_username = request.form['username']
    if new_username != user.username:
        # Check if username already exists
        existing_user = User.query.filter_by(username=new_username).first()
        if existing_user and existing_user.id != user.id:
            flash('Username already in use.', 'error')
            return redirect(url_for('profile'))
        user.username = new_username

    # Update email if changed
    new_email = request.form['email']
    if new_email != user.email:
        # Check if email already exists
        existing_user = User.query.filter_by(email=new_email).first()
        if existing_user and existing_user.id != user.id:
            flash('Email already in use.', 'error')
            return redirect(url_for('profile'))
        user.email = new_email

    # Update password if provided
    new_password = request.form['new_password']
    if new_password:
        user.password = generate_password_hash(new_password)

    # Save changes
    db.session.commit()
    flash('Profile updated successfully.', 'success')
    return redirect(url_for('profile'))


@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'user_id' not in session:
        flash('Please log in.', 'error')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    # Verify password
    password = request.form['password']
    if not check_password_hash(user.password, password):
        flash('Password is incorrect.', 'error')
        return redirect(url_for('profile'))

    try:
        # Delete associated data
        Resume.query.filter_by(user_id=user.id).delete()
        Performance.query.filter_by(user_id=user.id).delete()

        # Check if UserEmotionData and SessionSummary exist
        if hasattr(db.Model, 'UserEmotionData'):
            UserEmotionData.query.filter_by(user_id=user.id).delete()

        if hasattr(db.Model, 'SessionSummary'):
            SessionSummary.query.filter_by(user_id=user.id).delete()

        # Delete the user
        db.session.delete(user)
        db.session.commit()

        # Clear session
        session.clear()

        flash('Your account has been permanently deleted.', 'success')
        return redirect(url_for('home'))

    except Exception as e:
        db.session.rollback()
        print(f"Error deleting account: {e}")
        flash('An error occurred while deleting your account.', 'error')
        return redirect(url_for('profile'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['chat_history'] = []
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.', 'error')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))


@app.route('/upload_resume', methods=['POST'])
def upload_resume():
    if 'user_id' not in session:
        flash('Please log in.', 'error')
        return redirect(url_for('login'))

    file = request.files.get('resume')
    if file and file.filename:
        filename = secure_filename(file.filename)
        user_id = session['user_id']

        # Ensure the upload folder exists before saving
        upload_dir = app.config['UPLOAD_FOLDER']
        os.makedirs(upload_dir, exist_ok=True)

        # Optional: prepend user_id or timestamp to avoid collisions
        filename = f"user_{user_id}_" + filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        relative_path = os.path.join('static/uploads', filename)

        # Check if the user already has a resume
        existing_resume = Resume.query.filter_by(user_id=user_id).first()
        if existing_resume:
            existing_resume.resume_path = relative_path
        else:
            new_resume = Resume(user_id=user_id, resume_path=relative_path)
            db.session.add(new_resume)

        db.session.commit()
        flash('Resume uploaded successfully.', 'success')
        return redirect(url_for('dashboard'))

    flash('No file selected or invalid file.', 'error')
    return redirect(url_for('dashboard'))

# Add this function near other AI-related functions
def generate_improved_career_recommendations(resume_data, user_profile=None):
    """
    Generate improved career recommendations by providing the LLM with better examples.
    Maintains the exact same field structure as the original UI.
    """
    # Construct a prompt with high-quality examples that match the expected output format
    prompt = f"""
    Based on the following resume data, generate 3 personalized career path recommendations.
    Resume data: {resume_data}
    User profile (if available): {user_profile}
    
    IMPORTANT: Each recommendation MUST follow this EXACT format with these EXACT field names:
    
    Role Title (Match: X%)
    
    Description: [One sentence description of the role]
    
    Skills needed: [Comma-separated list of specific skills required]
    
    Growth potential: [High/Medium/Low]
    
    Salary range: $X - $Y
    
    ===== EXAMPLE OF A GOOD RECOMMENDATION =====
    
    Legal Assistant (Match: 87%)
    
    Description: Support attorneys by maintaining case files, managing schedules, and handling administrative tasks.
    
    Skills needed: Legal terminology, Document management, MS Office, Communication skills, Attention to detail
    
    Growth potential: High
    
    Salary range: $38,000 - $65,000
    
    ===== EXAMPLE OF ANOTHER GOOD RECOMMENDATION =====
    
    Community Outreach Coordinator (Match: 92%)
    
    Description: Develop and implement programs that connect organizations with the communities they serve.
    
    Skills needed: Event planning, Public speaking, Volunteer management, Cultural awareness, Fundraising basics
    
    Growth potential: Very High
    
    Salary range: $42,000 - $70,000
    
    ===== GENERATE THREE RECOMMENDATIONS =====
    Please generate THREE career recommendations that follow this exact format, with the following constraints:
    1. Use realistic match percentages based on actual skills overlap (don't give everyone 60%)
    2. Recommend attainable roles based on the person's experience level
    3. Ensure all required fields are included with the exact naming shown in the examples
    4. Keep descriptions concise but specific to the role
    5. Only include careers that are logical progressions from their current experience
    """
    
    try:
        # Use the AI client (assuming it's already set up elsewhere in your code)
        if ai_client:
            recommendation_model = ai_client.GenerativeModel('gemini-1.5-flash')
            safety_settings = [
                { "category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE" },
                { "category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE" },
                { "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE" },
                { "category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE" }
            ]
            
            response = recommendation_model.generate_content(
                prompt,
                safety_settings=safety_settings
            )
            
            # Parse the response and format it for the UI
            # This will depend on exactly how your UI expects the data
            # For now, just return the raw text from the LLM
            return response.text
        else:
            print("[ERROR] AI client not available for career recommendations")
            return "AI service unavailable. Please try again later."
    except Exception as e:
        print(f"[ERROR] Failed to generate career recommendations: {e}")
        return f"Error generating recommendations: {e}"

# Now we need to modify the route that handles career guidance
# Find the existing route (likely /start-guidance or similar) and add this function call

@app.route('/start-guidance')
def start_guidance():
    if 'user_id' not in session:
        flash('Please log in.', 'error')
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    # Get the user's resume
    user_resume = Resume.query.filter_by(user_id=user_id).first()
    if not user_resume:
        flash('Please upload a resume first.', 'error')
        return redirect(url_for('dashboard'))
    
    resume_path_rel = user_resume.resume_path
    resume_path_abs = os.path.join(app.root_path, resume_path_rel)
    
    # Extract resume data for improved recommendations
    resume_data = {}
    
    try:
        if os.path.exists(resume_path_abs):
            # This is simplified - in a real-world scenario, you would use your
            # existing resume parser or extraction logic here
            
            # If you have a ResumeProcessor class like in your original code:
            if 'ResumeProcessor' in locals() or 'ResumeProcessor' in globals():
                resume_processor = ResumeProcessor(ai_client=ai_client)
                resume_data = resume_processor.process_resume(resume_path_abs)
            else:
                # Simplified fallback if ResumeProcessor isn't available
                resume_data = {
                    "file_exists": True,
                    "file_path": resume_path_rel,
                    # Add any other data you can extract
                }
    except Exception as e:
        print(f"Error extracting resume data: {e}")
        # Proceed with empty resume_data rather than failing

    # Get user profile information if available
    user_profile = {
        "username": user.username if hasattr(user, 'username') else "",
        # Add any other profile fields you have
    }

    # Generate improved career recommendations
    career_paths = []
    
    if ai_client:
        try:
            # Get improved career recommendations
            career_paths = get_career_recommendations(ai_client, resume_data, user_profile)
        except Exception as e:
            print(f"Error getting career recommendations: {e}")
            # Use fallback or empty list
            career_paths = []
    else:
        print("AI client not available for career recommendations")

    # Convert career_paths (list of dictionaries) to career_paths_list (list of lists) format
    # that's expected by the template
    career_paths_list = []
    for path in career_paths:
        path_list = []
        # Format title with match percentage and remove markdown asterisks
        role_title = path.get('role', 'Unknown Role').strip().strip('*')
        path_list.append(f"{role_title} (Match: {path.get('match', 0)}%)")
        # Add description
        path_list.append(f"Description: {path.get('description', 'No description available')}")
        # Add skills needed
        path_list.append(f"Skills needed: {path.get('skills_needed', 'No skills information available')}")
        # Add growth potential
        path_list.append(f"Growth potential: {path.get('growth_potential', 'Unknown')}")
        # Add salary range
        path_list.append(f"Salary range: {path.get('salary_range', 'Not specified')}")
        
        career_paths_list.append(path_list)
    
    # Add fallback generic careers if no careers were generated
    if not career_paths_list:
        print("No career paths were generated. Adding fallback generic careers.")
        
        # Extract user skills from resume if available
        user_skills = []
        if resume_data and 'skills' in resume_data:
            user_skills = resume_data.get('skills', [])
        
        # Generate some generic career paths with reasonable defaults
        fallback_careers = [
            {
                "role": "Data Analyst",
                "match": 85,
                "description": "Analyze complex datasets to extract insights and support business decisions",
                "skills_needed": "SQL, Excel, Python, Data Visualization, Statistics",
                "growth_potential": "High",
                "salary_range": "$60,000 - $95,000"
            },
            {
                "role": "Software Developer",
                "match": 82,
                "description": "Design, code, and test software applications based on user requirements",
                "skills_needed": "Python, JavaScript, Git, Data Structures, Problem Solving",
                "growth_potential": "Very High",
                "salary_range": "$70,000 - $110,000"
            },
            {
                "role": "Digital Marketing Specialist",
                "match": 78,
                "description": "Create and implement online marketing strategies across multiple platforms",
                "skills_needed": "SEO, Social Media, Content Writing, Analytics, Campaign Management",
                "growth_potential": "High",
                "salary_range": "$55,000 - $85,000"
            }
        ]
        
        # Convert fallback careers to expected format
        for path in fallback_careers:
            path_list = []
            path_list.append(f"{path['role']} (Match: {path['match']}%)")
            path_list.append(f"Description: {path['description']}")
            path_list.append(f"Skills needed: {path['skills_needed']}")
            path_list.append(f"Growth potential: {path['growth_potential']}")
            path_list.append(f"Salary range: {path['salary_range']}")
            
            career_paths_list.append(path_list)
    
    # Initialize functions module with resume data before getting tips
    try:
        # Create dummy career paths data structure if none exists
        dummy_career_paths = []
        # Create default empty variables for initialization
        resume_text = ""
        analysis = {}
        skill_keywords = []
        
        # Create a comprehensive list of common skills to detect in resumes
        skill_keywords = [
            "python", "java", "javascript", "html", "css", "react", "node.js", "angular", "vue",
            "c++", "c#", "swift", "kotlin", "sql", "mysql", "postgresql", "mongodb", "nosql",
            "aws", "azure", "gcp", "cloud", "docker", "kubernetes", "devops", "ci/cd", "git",
            "machine learning", "artificial intelligence", "ai", "data science", "data analysis",
            "excel", "word", "powerpoint", "tableau", "power bi", "data visualization",
            "project management", "agile", "scrum", "leadership", "teamwork", "communication",
            "problem solving", "critical thinking", "time management", "customer service",
            "sales", "marketing", "seo", "sem", "digital marketing", "content writing",
            "accounting", "finance", "budgeting", "financial analysis", "human resources", "hr",
            "recruiting", "talent acquisition", "administrative", "office management",
            "research", "analytics", "statistics", "r", "spss", "product management",
            "ui/ux", "user experience", "user interface", "graphic design", "adobe",
            "photoshop", "illustrator", "indesign", "figma", "sketch", "wireframing",
            "networking", "security", "cybersecurity", "linux", "windows", "macos",
            "mobile development", "ios", "android", "flutter", "react native",
            "api", "rest", "graphql", "json", "xml", "testing", "qa", "quality assurance",
            "jira", "confluence", "trello", "asana", "ms project", "microsoft office"
        ]
        
        # Extract text from resume file if possible
        if os.path.exists(resume_path_abs):
            # Check if we can safely import PIL and use Tesseract
            try:
                # Check if Tesseract OCR is properly installed
                if resume_path_abs.lower().endswith(('.png', '.jpg', '.jpeg')):
                    from PIL import Image
                    import pytesseract
                    # Test Tesseract path - this will raise an exception if not configured
                    if not os.path.exists(pytesseract.pytesseract.tesseract_cmd):
                        print(f"Warning: Tesseract executable not found at {pytesseract.pytesseract.tesseract_cmd}")
                        # Try to find tesseract in PATH
                        pytesseract.pytesseract.tesseract_cmd = "tesseract"
                        # Test a basic call
                        pytesseract.get_tesseract_version()
                    
                    resume_text = functions.extract_text_from_image(resume_path_abs)
                elif resume_path_abs.lower().endswith('.pdf'):
                    resume_text = functions.extract_text_from_pdf(resume_path_abs)
            except (ImportError, Exception) as e:
                print(f"Warning: OCR dependencies issue - {str(e)}. Will proceed with empty text.")
                resume_text = ""
        
        # Initialize the functions module
        functions.initialize(resume_path_abs, resume_text, analysis, dummy_career_paths, skill_keywords, user_id)
        
        # Analyze the resume to get the data needed for tips
        functions.analyze_resume()
    except Exception as e:
        print(f"Error initializing functions module: {e}")
    
    # Get resume tips
    structure_tips, content_improvement_tips, tech_and_soft_skill_tips, experience_tips, achievement_tips, ats_tips, modern_tips, tailoring_tips = functions.provide_resume_tips()
    
    # Generate roadmaps for each career path
    roadmap_dict = {}
    try:
        for path_list in career_paths_list:
            try:
                # Extract the career title from the first item in the path list
                # Remove the match percentage part and any markdown asterisks
                career_title = path_list[0].split(' (Match:')[0].strip().strip('*')
                
                # Create a more compatible format for generate_roadmap
                # Check if we can extract skills from the skills needed field
                skills_needed = []
                if len(path_list) > 2:  # Ensure we have enough elements
                    # Extract skills from the skills field (format: "Skills needed: skill1, skill2, skill3")
                    skills_text = path_list[2].replace("Skills needed:", "").strip()
                    if skills_text and skills_text.lower() != "no skills information available":
                        skills_needed = [skill.strip() for skill in skills_text.split(",")]
                
                # If skills list is empty or too short, add some generic skills
                while len(skills_needed) < 4:
                    skills_needed.append(f"Skill {len(skills_needed) + 1}")
                
                # Create a career path dictionary compatible with generate_roadmap
                career_path_dict = {
                    "title": career_title, # Use the cleaned title
                    "skills_needed": skills_needed
                }
                
                # Generate roadmap and store it with the full path string (including match %) as key
                roadmap_dict[path_list[0]] = functions.generate_roadmap(career_path_dict)
            except Exception as inner_e:
                # If an individual roadmap fails, log the error but continue with others
                print(f"Error generating roadmap for '{path_list[0]}': {inner_e}")
                # Create a fallback generic roadmap
                roadmap_dict[path_list[0]] = {
                    "title": f"Career Roadmap for {career_title}", # Use cleaned title here too
                    "overview": "A strategic progression path for this career. Due to a technical issue, a generic roadmap is shown.",
                    "steps": [
                        {"timeframe": "0-6 months", "focus": "Learning fundamentals", "tasks": ["Learn industry basics", "Take introductory courses", "Build foundational skills", "Join professional communities"]},
                        {"timeframe": "6-12 months", "focus": "Gaining experience", "tasks": ["Apply skills in real projects", "Build portfolio", "Network with professionals", "Seek entry-level opportunities"]},
                        {"timeframe": "1-2 years", "focus": "Specialization", "tasks": ["Develop expertise in specific areas", "Take on more responsibility", "Mentor others", "Seek advancement"]},
                        {"timeframe": "3-5 years", "focus": "Leadership and mastery", "tasks": ["Become an industry leader", "Contribute to field knowledge", "Consider management roles", "Stay current with industry trends"]}
                    ],
                    "additional_resources": [
                        "Online courses and certifications",
                        "Industry books and publications",
                        "Professional associations and conferences",
                        "Networking events and communities"
                    ]
                }
        
    except Exception as e:
        print(f"Error generating roadmaps: {e}")
        import traceback
        traceback.print_exc()
    
    # Pass career_paths_list to the template instead of career_paths
    return render_template('guidance.html', 
                          user=user,
                          user_resume=user_resume, 
                          career_paths_list=career_paths_list,
                          structure_tips=structure_tips,
                          content_improvement_tips=content_improvement_tips,
                          tech_and_soft_skill_tips=tech_and_soft_skill_tips,
                          experience_tips=experience_tips,
                          achievement_tips=achievement_tips,
                          ats_tips=ats_tips,
                          modern_tips=modern_tips,
                          tailoring_tips=tailoring_tips,
                          roadmap_dict=roadmap_dict
                          )

# Function to get menu options as structured data
# Renamed from get_formatted_menu
def get_menu_data():
    return get_menu_options() # Return the list of dictionaries directly

# Function to get formatted resume analysis for the chat interface


def get_resume_analysis_for_chat(user_id):
    """
    Retrieves the user's resume, processes it, and asks the LLM for detailed 
    improvement recommendations.
    Formats the LLM response for HTML display.
    """
    print(f"[DEBUG] get_resume_analysis_for_chat called for user {user_id}")
    try:
        # 1. Find the user's resume
        user_resume = Resume.query.filter_by(user_id=user_id).first()
        if not user_resume:
            print(f"[DEBUG] No resume found in DB for user {user_id}")
            return "No resume found in your profile. Please upload one first."
        
        resume_path_rel = user_resume.resume_path
        resume_path_abs = os.path.join(app.root_path, resume_path_rel)
        print(f"[DEBUG] Found resume path: {resume_path_abs}")

        if not os.path.exists(resume_path_abs):
            print(f"[ERROR] Resume file not found at path: {resume_path_abs}")
            return "Error: Your resume file seems to be missing. Please re-upload it."

        # 2. Process the resume to get structured data
        if not ai_client:
            print("[ERROR] AI Client not configured for resume processing.")
            return "Error: AI Client is not configured. Cannot analyze resume."
            
        resume_processor = ResumeProcessor(ai_client=ai_client)
        print(f"[DEBUG] Processing resume: {resume_path_abs}")
        resume_data = resume_processor.process_resume(resume_path_abs)

        if not resume_data:
            print(f"[ERROR] Resume processing failed or returned empty data for {resume_path_abs}")
            return "Error: Failed to extract data from your resume. Check the file format or try re-uploading."
        
        print(f"[DEBUG] Resume processed successfully. Keys: {list(resume_data.keys())}")

        # 3. Construct prompt for LLM analysis
        # Ensure resume_data is converted to a string (JSON) for the prompt
        resume_data_json_str = json.dumps(resume_data, indent=2)
        
        prompt = f"""
You are an expert resume reviewer and career coach.
Analyze the following structured resume data extracted from a user's resume.
Provide detailed, actionable feedback and specific recommendations on how to improve the resume.

Focus on:
- Formatting and Readability: Is it clean, professional, and easy for recruiters/ATS to parse?
- Content Clarity: Are sections like Experience and Projects clear and impactful?
- Quantifiable Achievements: Does the user effectively demonstrate results with numbers or specific outcomes?
- Skills Section: Is it well-organized? Does it balance technical and soft skills? Are keywords relevant?
- Experience Section: Does it use action verbs? Does it follow the STAR method implicitly or explicitly?
- Tailoring: General advice on tailoring the resume for specific job applications.
- Missing Information: Are there obvious gaps (e.g., contact info, key sections)?
- Overall Impression: What is the overall effectiveness?

Structure your response clearly with headings (e.g., **Formatting**, **Content**, **Recommendations**).
Make the recommendations specific and easy to follow.

**Resume Data (JSON):**
```json
{resume_data_json_str}
```

**Generate your detailed analysis and recommendations:**
"""

        # 4. Call the LLM
        print("[DEBUG] Calling LLM for resume analysis and recommendations...")
        model = ai_client.GenerativeModel('gemini-1.5-flash') # Or your preferred model
        safety_settings = [
            { "category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE" },
            { "category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE" },
            { "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE" },
            { "category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE" }
        ]
        
        response = model.generate_content(prompt, safety_settings=safety_settings)
        analysis_text = response.text
        
        if not analysis_text.strip():
             print("[WARN] LLM returned empty response for resume analysis.")
             analysis_text = "The AI analysis returned an empty response. This might be due to content filtering or a temporary issue."
        else:
             print(f"[DEBUG] LLM analysis received: {analysis_text[:100]}...")

        # 5. Format for HTML display
        # Basic Formatting for HTML chat display
        formatted_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', analysis_text) # Bold
        formatted_text = re.sub(r'^\*\s+', r'• ', formatted_text, flags=re.MULTILINE) # Bullets
        formatted_text = re.sub(r'^(\d+)\.\s+', r'\1. ', formatted_text, flags=re.MULTILINE) # Numbered lists
        formatted_text = formatted_text.replace('\n', '<br>') # Newlines
        final_output = "<b>📄 AI Resume Analysis & Recommendations</b><br><br>" + formatted_text
        final_output = re.sub(r'(<br>\s*){2,}', '<br><br>', final_output) # Consolidate excessive breaks

        return final_output

    except Exception as e:
        print(f"[ERROR] Error in get_resume_analysis_for_chat: {e}")
        import traceback
        traceback.print_exc()
        return "An error occurred while analyzing your resume. Please check the server logs."

# === Updated generate_response (Handles only menu options) ===
def generate_response(user_message, user_id):
    # menu_items = mainmenu() # Original
    menu_options = get_menu_options() # Use the new function returning dictionaries
    response = ""

    # Check if an interview is already active for this user
    if user_id in active_interviews:
        # If interview active, this function shouldn't be called for processing answers
        # It should only handle menu commands *before* interview starts.
        # Let the /start-interview route handle answer processing.
        # We can maybe allow an "End Interview" command here.
        if "end interview" in user_message.lower() or "4" == user_message.strip():
            interview_instance = active_interviews.pop(user_id, None)
            if interview_instance:
                ai_response = interview_instance.end_interview()
                # Optionally: Trigger recommendations generation
                # recommendations = recommendation_module.generate_recommendations(interview_instance.conversation_history)
                return ai_response + "<br><br>Interview ended. Recommendations might be available later." # Placeholder
            else:
                 return "No active interview found to end."
        else:
            return "An interview is already in progress. Please respond to the question." # Or handle other specific commands

    # If interview is NOT active, check for menu commands using structured data
    action_selected = None
    for option in menu_options:
        # Check against text (case-insensitive) or action_id (menu number)
        if option['text'].lower() in user_message.lower() or option['action_id'] == user_message.strip():
            action_selected = option['action_id']
            selected_text = option['text'] # Store the text for potential use
            break # Found a match

    if action_selected:
        action_id_int = int(action_selected) # Convert action_id string to int for comparisons
        if action_id_int == 1: # Upload Resume
             return "Please upload your resume via the Dashboard."

        if action_id_int == 2: # Start Interview
            # Logic handled by /start-interview route, just give feedback
            return "Starting interview... (Handled by page logic)"

        if action_id_int == 5: # Resume Analysis
            # Pass user_id to the updated function
            return get_resume_analysis_for_chat(user_id)

        if action_id_int == 6: # Change TTS Voice
             return "TTS voice change functionality not fully implemented."

        if action_id_int == 7: # Test Audio
             return "TTS audio test functionality not fully implemented."

        # Options 3 (Process Answer) and 4 (End Interview) shouldn't be handled here
        # when no interview is active.

        # Other menu items (8: Configure Speech, 9: Exit)
        if action_id_int in [8, 9]:
            return f"Selected: {selected_text}. (Functionality not fully implemented)"

        # Fallthrough for invalid action_id if needed, though the structure implies valid IDs
        response = f"Debug: Matched action {action_selected}, but no handler." # Should not happen ideally

    # If no valid option was selected by text or ID
    if not action_selected:
        # Instead of returning a formatted string, return the structured options
        # The frontend JavaScript will handle displaying these as buttons/boxes
        # We might still need a text prompt
        # Returning a dictionary that the frontend can interpret
        return {"type": "menu", "options": menu_options, "prompt": "Please select a valid option:"}

    return response # Return the specific response string from the handlers above

# === Updated /start-interview Route ===
@app.route('/start-interview', methods=['GET', 'POST'])
def start_interview():
    if 'user_id' not in session:
        flash('Please log in.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = User.query.get(user_id) # <<< Add this line back

    user_resume = Resume.query.filter_by(user_id=user_id).first()
    if not user_resume:
        flash('Please upload a resume first.', 'error')
        return redirect(url_for('dashboard'))
    resume_path_rel = user_resume.resume_path
    resume_path_abs = os.path.join(app.root_path, resume_path_rel)

    chat_history = session.get('chat_history', [])
    initial_load = request.method == 'GET'
    response_data = None # Will hold data to send back (text or structured menu)

    if request.method == 'POST':
        user_message = request.form['message']
        print(f"[DEBUG] Received POST for user {user_id}. Message: '{user_message}'") # Debug
        chat_history.append(("User", user_message))

        if user_id in active_interviews:
            print(f"[DEBUG] User {user_id} found in active_interviews.") # Debug
            interview_instance = active_interviews[user_id]
            
            # Check if the message is the "End Interview" command ("4")
            is_end_command = user_message.strip() == '4'
            print(f"[DEBUG] Is message '4'? {is_end_command}") # Debug
            if is_end_command:
                print(f"[DEBUG] Ending interview for user {user_id} via command.") # Debug
                
                # 1. Get closing statement and transcript from Interview object
                closing_statement, transcript = interview_instance.end_interview()
                print(f"[DEBUG] Closing statement: {closing_statement[:100]}...") 
                print(f"[DEBUG] Transcript length: {len(transcript)}")

                # 2. Retrieve performance metrics (eye contact, etc.) for this user/session
                #    We need the session_id used by the InterviewMetricsTracker
                #    Assuming the Interview class might store a session_id, or we need to link it.
                #    For now, let's fetch the *latest* final (non-autosave) metric for the user.
                performance_metrics = "No performance metrics found."
                try:
                    latest_metric = EyeMetrics.query.filter_by(user_id=user_id, is_auto_save=False)\
                                                      .order_by(EyeMetrics.timestamp.desc()).first()
                    if latest_metric:
                        performance_metrics = f"""
Performance Metrics (Latest Session: {latest_metric.session_id}):
- Eye Contact Losses: {latest_metric.loss_eye_contact_count}
- Looking Away Duration: {latest_metric.looking_away_duration:.1f}s
- Bad Posture Count: {latest_metric.bad_posture_count}
- Bad Posture Duration: {latest_metric.bad_posture_duration:.1f}s
- Hand Movement Duration: {latest_metric.hand_detection_duration:.1f}s
"""
                        print("[DEBUG] Successfully fetched performance metrics.")
                    else:
                        print("[DEBUG] No final performance metrics found for user.")
                except Exception as e:
                    print(f"[DEBUG] Error fetching performance metrics: {e}")
                    performance_metrics = "Error fetching performance metrics."

                # 3. Construct the prompt for feedback and recommendations
                feedback_prompt = f"""
You are an expert interview coach reviewing a completed interview session.
Analyze the following interview transcript and performance metrics (if available).
Provide constructive feedback and actionable recommendations for the candidate to improve their interview skills.

Focus on:
- Clarity and conciseness of answers.
- Relevance of answers to the questions.
- Use of specific examples (STAR method if applicable).
- Professionalism and tone.
- Handling of technical/behavioral questions.
- Any insights from performance metrics (e.g., frequent looking away might suggest lack of confidence or preparation).

Structure your response:
1.  **Overall Summary:** A brief overview of the candidate's performance.
2.  **Strengths:** Mention specific positive aspects.
3.  **Areas for Improvement:** Provide specific, actionable feedback on weaknesses.
4.  **Performance Metrics Insights (if applicable):** Briefly comment on what the metrics might indicate.
5.  **Recommendations:** Suggest concrete steps the candidate can take (e.g., practice STAR method, research common questions, work on body language).

Keep the feedback professional, encouraging, and helpful.

**Interview Transcript:**
{transcript}

**Performance Metrics:**
{performance_metrics}

**Generate the feedback and recommendations:**
"""

                # 4. Call the AI with the feedback prompt
                ai_feedback = "Could not generate feedback at this time."
                if ai_client:
                    try:
                        print("[DEBUG] Calling AI for feedback...")
                        feedback_model = ai_client.GenerativeModel('gemini-1.5-flash')
                        # Add safety settings to potentially mitigate content filtering issues
                        safety_settings = [
                            { "category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE" },
                            { "category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE" },
                            { "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE" },
                            { "category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE" }
                        ]
                        feedback_response = feedback_model.generate_content(
                            feedback_prompt,
                            safety_settings=safety_settings
                        )
                        ai_feedback = feedback_response.text
                        # Check if feedback is empty even after successful call (e.g., filtering)
                        if not ai_feedback.strip():
                            ai_feedback = "Feedback generation resulted in an empty response (potentially due to content filtering)."
                            print("[DEBUG] AI Feedback was empty after successful call.")
                        else: 
                            print(f"[DEBUG] AI Feedback generated: {ai_feedback[:100]}...")
                    except Exception as e:
                        print(f"[DEBUG] Error calling AI for feedback: {e}")
                        # Provide a more informative error in the response
                        ai_feedback = f"Error generating feedback. Please check server logs. (Error: {e})"
                else:
                     print("[DEBUG] AI client not available for feedback generation.")
                     ai_feedback = "AI Client not configured, cannot generate feedback."
                 
                # Ensure ai_feedback is always a non-empty string before formatting
                if not ai_feedback:
                    ai_feedback = "Feedback could not be generated."

                # 5. Construct final response (Closing + Feedback + Menu)
                menu_text = get_menu_data()
                # Format feedback for HTML: Replace double newlines with paragraph breaks, single newlines with <br>
                # Ensure ai_feedback is treated as a string
                feedback_text = str(ai_feedback).strip()
                formatted_feedback = re.sub(r'\n\s*\n', '<br><br>', feedback_text) # Paragraphs
                formatted_feedback = re.sub(r'\n', '<br>', formatted_feedback) # Line breaks within paragraphs

                ai_response = f"{closing_statement}<br><br>--- Feedback ---<br>{formatted_feedback}<br><br>--- Menu ---<br>{menu_text}"
                
                # Where the interview is ended and closing statement/transcript are generated
                if is_end_command:
                    # ... existing code for ending interview ...
                    
                    # 5. Construct final response (Closing + Feedback + Menu)
                    # Wrap as composite response with both text and menu
                    response_data = {
                        "type": "composite",
                        "content": ai_response,
                        "menu": {
                            "options": get_menu_data(),
                            "prompt": "Interview ended. Select an option:"
                        }
                    }
                    
                    # Clean up active interview
                    active_interviews.pop(user_id, None) 
                    print(f"[DEBUG] Final response_data created for interview end")
            else:
                # Otherwise, process the answer normally
                print(f"[DEBUG] Processing answer normally for user {user_id}.") # Debug
                ai_response_text = interview_instance.process_answer(user_message)
                print(f"[DEBUG] Response from process_answer(): {ai_response_text[:100]}...") # Debug
                # Check if process_answer itself ended the interview
                if interview_instance.interview_end_time:
                    print(f"[DEBUG] Interview ended during process_answer for user {user_id}.") # Debug
                    active_interviews.pop(user_id, None)
                    # Combine text response with the menu options
                    response_data = {
                        "type": "composite", # Indicate both text and menu needed
                        "content": ai_response_text,
                        "menu": {
                            "options": get_menu_data(),
                            "prompt": "Interview ended. Select an option:"
                        }
                    }
                else:
                    # Just a text response
                    response_data = {"type": "text", "content": ai_response_text}
        
        else:
            print(f"[DEBUG] User {user_id} NOT found in active_interviews. Treating as menu command.") # Debug
            # Check if the command is specifically to start the interview
            if "start interview" in user_message.lower() or "2" == user_message.strip():
                 if ai_client:
                     error_occurred = False # Flag to track if setup failed
                     ai_response_text = None # Initialize ai_response_text
                     resume_data = {}       # Initialize resume_data
                     try:
                         resume_processor = ResumeProcessor(ai_client=ai_client)
                         user_resume = Resume.query.filter_by(user_id=user_id).first()
                         if not user_resume:
                             ai_response_text = "Error: Resume not found. Please upload first."
                             error_occurred = True 
                         else: 
                            resume_path_rel = user_resume.resume_path
                            resume_path_abs = os.path.join(app.root_path, resume_path_rel)
                            print(f"[DEBUG] Re-fetched absolute path for start: {resume_path_abs}")
                            
                            if os.path.exists(resume_path_abs):
                                print(f"Processing resume file: {resume_path_abs}")
                                # Call the AI to process resume
                                resume_data = resume_processor.process_resume(resume_path_abs)
                                print(f"Resume processed. Data keys: {list(resume_data.keys())}")
                                # Check if processing actually returned data
                                if not resume_data:
                                    print("[ERROR] Resume processing returned empty data.")
                                    ai_response_text = "Error processing resume data."
                                    error_occurred = True
                            else:
                                print(f"Error: Resume file not found at {resume_path_abs}")
                                ai_response_text = "Error: Could not find your resume file. Please re-upload."
                                error_occurred = True
                         
                         if not error_occurred: # Check the flag
                             print("[DEBUG] No errors during resume processing, proceeding to create Interview instance.")
                             interview_instance = Interview(ai_client=ai_client, tts_service=tts_service, resume_data=resume_data)
                             active_interviews[user_id] = interview_instance
                             # Call start_interview and store the response
                             ai_response_text = interview_instance.start_interview() 
                             print(f"[DEBUG] Interview started for user {user_id}. First question: {ai_response_text[:100]}...") # Log the actual question
                             response_data = {"type": "text", "content": ai_response_text}
                         else:
                             print("[DEBUG] Error occurred during resume processing or file handling, skipping Interview creation.")
                             # Minor improvement: Use specific error message if available
                             error_message = ai_response_text if ai_response_text else "An error occurred starting the interview."
                             response_data = {"type": "text", "content": error_message}

                     except Exception as e:
                         error_occurred = True # Set flag in except
                         print(f"[DEBUG] Exception during interview start: {e}")
                         ai_response_text = f"An error occurred while starting the interview: {e}"
                         response_data = {"type": "text", "content": ai_response_text}
                 else:
                     ai_response_text = "AI Client not configured. Cannot start AI interview."
                     print("[DEBUG] AI client not configured.")
                     response_data = {"type": "text", "content": ai_response_text}
            else:
                 # If not starting, handle other menu options via generate_response
                 # generate_response already returns structured data (text or menu dict)
                 response_data = generate_response(user_message, user_id)
                 print(f"[DEBUG] Handled by generate_response: {str(response_data)[:100]}...")

        # Removed chat_history append here, handled by JS now mostly
        # if ai_response_text: # Check if variable exists before appending
        #    chat_history.append(("AI", ai_response_text)) # This might duplicate messages shown via JSON

        # Keep session updated (though JS manages display primarily now)
        session['chat_history'] = chat_history 

        # Remove old jsonify logic
        # if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        #    final_response_to_send = ai_response_text or "" # Ensure we send at least an empty string
        #    print(f"[DEBUG] Sending JSON response: {{'response': '{final_response_to_send[:100]}...'}}") # Debug
        #    return jsonify({'response': final_response_to_send})

    # Handle GET request (initial page load)
    else: # This is the GET block
        # Initialize initial_menu_data to None here to avoid UnboundLocalError
        initial_menu_data = None
        
        if user_id in active_interviews:
            # If returning to an active interview, maybe resend the last question?
            # For now, just a notification
            chat_history.append(("AI", "Resuming interview..."))
        elif not chat_history: 
            # If no active interview and no chat history, set up initial menu data for template
            menu_options_data = get_menu_data()
            initial_prompt = "Welcome! Please select an option to begin."
            # Store initial menu info to pass to template
            initial_menu_data = {"type": "menu", "options": menu_options_data, "prompt": initial_prompt}
            # Optionally add a welcome message to history if desired, but menu is handled by JS
            # chat_history.append(("AI", initial_prompt)) # Maybe not needed if JS shows prompt
            session['chat_history'] = chat_history # Save potentially empty history
        else:
            initial_menu_data = None # No initial menu if history exists or interview active

        # Render the INTERVIEW template for GET requests
        return render_template('interview.html', # <<< FIX: Render interview.html
                               user=user, # Pass user object if needed by template
                               chat_history=chat_history, # Pass history for initial render
                               initial_menu=initial_menu_data) # Pass structured menu data (or None)

    # For POST requests, return the processed response_data as JSON
    # Ensure response_data is always a dictionary
    if not isinstance(response_data, dict):
         print(f"[WARN] response_data is not a dict: {response_data}. Wrapping as text error.")
         response_data = {"type": "text", "content": str(response_data or "Error: Invalid response generated.")}

    print(f"[DEBUG] Returning JSON response: {str(response_data)[:200]}...") # Debug
    return jsonify(response_data)


@app.route('/clear-chat-history', methods=['GET', 'POST'])
def clear_chat_history():
    if 'user_id' not in session:
        flash('Please log in.', 'error')
        return redirect(url_for('login'))
        
    # Clear chat history in session
    session['chat_history'] = []
    
    # If user has an active interview, consider ending it
    user_id = session['user_id']
    if user_id in active_interviews:
        # Optionally end the active interview
        active_interviews.pop(user_id, None)
        
    # Flash a message to confirm
    flash('Chat history cleared.', 'success')
    
    # Redirect back to the interview page
    return redirect(url_for('start_interview'))


@app.route('/process_image', methods=['POST'])
def process_image():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'User not logged in'})

    # Get the image data from the request
    data = request.json
    image_data = data.get('image', '')
    save_prediction = data.get('savePrediction', False)

    # Remove the data URL prefix
    image_data = image_data.split(',')[1]

    # Decode the base64 image
    image_bytes = base64.b64decode(image_data)
    np_arr = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    # Process the image
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = facecasc.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)

    prediction = None
    probability = 0
    detected_emotion = None

    # If faces are detected, focus on the largest face
    if len(faces) > 0:
        # Find the largest face
        largest_face = max(faces, key=lambda face: face[2] * face[3])
        x, y, w, h = largest_face

        # Draw rectangle around the face
        cv2.rectangle(frame, (x, y-50), (x+w, y+h+10), (255, 0, 0), 2)

        # Extract the face ROI
        roi_gray = gray[y:y + h, x:x + w]
        cropped_img = np.expand_dims(np.expand_dims(
            cv2.resize(roi_gray, (48, 48)), -1), 0)

        # Make prediction
        prediction = model.predict(cropped_img)
        maxindex = int(np.argmax(prediction))
        probability = float(prediction[0][maxindex])
        detected_emotion = emotion_dict[maxindex]

        # Add text to the image
        cv2.putText(frame, detected_emotion, (x+20, y-60),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

        # Save to database if requested (every 30 frames/~1 second)
        if save_prediction and detected_emotion:
            user_id = session.get('user_id')
            # Save using both methods for compatibility
            # 1. Using the UserEmotionData model
            emotion_data = UserEmotionData(
                user_id=user_id,
                emotion=detected_emotion,
                confidence=probability
            )
            db.session.add(emotion_data)
            db.session.commit()

            # 2. Using the functions.py save_emotion function
            try:
                functions.save_emotion(detected_emotion, probability, user_id)
            except Exception as e:
                print(f"Error using functions.save_emotion: {str(e)}")

    # Encode the processed image back to base64
    _, buffer = cv2.imencode('.jpg', frame)
    encoded_image = base64.b64encode(buffer).decode('utf-8')

    # Return the results
    return jsonify({
        'success': True,
        'annotated_image_base64': encoded_image,
        'prediction': detected_emotion,
        'probability': probability
    })

# Add a route to get emotion statistics for the current user


@app.route('/emotion_stats', methods=['GET'])
def emotion_stats():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'User not logged in'})

    user_id = session.get('user_id')

    # Get the latest session data (last hour)
    from datetime import timedelta
    one_hour_ago = datetime.now() - timedelta(hours=1)

    emotions = UserEmotionData.query.filter_by(user_id=user_id).filter(
        UserEmotionData.timestamp >= one_hour_ago
    ).all()

    # Calculate statistics
    emotion_counts = {"Angry": 0, "Disgusted": 0, "Fearful": 0, "Happy": 0,
                      "Neutral": 0, "Sad": 0, "Surprised": 0}

    for emotion_data in emotions:
        if emotion_data.emotion in emotion_counts:
            emotion_counts[emotion_data.emotion] += 1

    total = sum(emotion_counts.values())

    # Calculate percentages
    emotion_percentages = {}
    if total > 0:
        for emotion, count in emotion_counts.items():
            emotion_percentages[emotion] = round((count / total) * 100, 1)

    return jsonify({
        'success': True,
        'emotion_counts': emotion_counts,
        'emotion_percentages': emotion_percentages,
        'total_detections': total
    })


# Initialize the metrics tracker
metrics_tracker = None
# Route to start video analysis


@app.route('/start_video_analysis', methods=['GET'])
def start_video_analysis():
    global metrics_tracker

    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'User not logged in'})

    # Initialize the metrics tracker if it doesn't exist
    if metrics_tracker is None:
        metrics_tracker = InterviewMetricsTracker()
        metrics_tracker.start3()  # Start in background thread with simulation

    return jsonify({'success': True, 'message': 'Video analysis started'})

# Route to end video analysis


@app.route('/end_video_analysis', methods=['GET'])
def end_video_analysis():
    global metrics_tracker

    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'User not logged in'})

    if metrics_tracker is not None:
        # Save final metrics
        metrics_tracker.close()

        # Make sure instance directory exists
        instance_path = os.path.join(os.getcwd(), 'instance')
        os.makedirs(instance_path, exist_ok=True)

        # Ensure database file exists
        eye_db_path = os.path.join(instance_path, 'eye.sqlite')
        if not os.path.exists(eye_db_path):
            # Create the database file if it doesn't exist
            try:
                # Initialize eye.sqlite with the eye_metrics table
                conn = sqlite3.connect(eye_db_path)
                cursor = conn.cursor()

                # Create the eye_metrics table
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS eye_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    session_id TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    hand_detection_count INTEGER DEFAULT 0,
                    hand_detection_duration REAL DEFAULT 0.0,
                    loss_eye_contact_count INTEGER DEFAULT 0,
                    looking_away_duration REAL DEFAULT 0.0,
                    bad_posture_count INTEGER DEFAULT 0,
                    bad_posture_duration REAL DEFAULT 0.0,
                    is_auto_save BOOLEAN DEFAULT 0
                )
                ''')

                conn.commit()
                conn.close()
                print(f"Created database file: {eye_db_path}")
            except Exception as e:
                print(f"Error creating database file: {str(e)}")
                return jsonify({'success': False, 'error': f'Database error: {str(e)}'})

        # Save final metrics to our SQLAlchemy model
        try:
            # Create a final EyeMetrics record
            final_metrics = EyeMetrics(
                user_id=session['user_id'],
                session_id=metrics_tracker.session_id,
                hand_detection_count=metrics_tracker.metrics["handDetectionCount"],
                hand_detection_duration=metrics_tracker.metrics["handDetectionDuration"],
                loss_eye_contact_count=metrics_tracker.metrics["lossEyeContactCount"],
                looking_away_duration=metrics_tracker.metrics["lookingAwayDuration"],
                bad_posture_count=metrics_tracker.metrics["badPostureCount"],
                bad_posture_duration=metrics_tracker.metrics["badPostureDuration"],
                is_auto_save=False  # This is a final save, not an auto-save
            )

            # Add and commit
            db.session.add(final_metrics)
            db.session.commit()

            print(
                f"Final eye metrics saved to database for session {metrics_tracker.session_id}")
        except Exception as e:
            error_msg = str(e)
            print(f"Error saving final eye metrics: {error_msg}")
            db.session.rollback()

            # Additional debugging info
            if "no such table" in error_msg.lower():
                # The table doesn't exist, try to create it
                try:
                    with app.app_context():
                        db.create_all(bind_key='eye_metrics')
                        print("Created eye_metrics table")

                        # Try saving again
                        db.session.add(final_metrics)
                        db.session.commit()
                        print("Successfully saved metrics after creating table")
                except Exception as inner_e:
                    print(f"Failed to create table: {str(inner_e)}")

        # Clear the tracker
        metrics_tracker = None

        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Video analysis not started'})

# Route to get current metrics


@app.route('/video_metrics', methods=['GET'])
def get_video_metrics():
    global metrics_tracker

    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'User not logged in'})

    # Return current metrics if the tracker exists
    if metrics_tracker is not None:
        # Auto save metrics to database for persistence
        metrics_tracker.auto_save_metrics()

        # Make sure instance directory exists
        instance_path = os.path.join(os.getcwd(), 'instance')
        os.makedirs(instance_path, exist_ok=True)

        # Ensure database file exists
        eye_db_path = os.path.join(instance_path, 'eye.sqlite')
        if not os.path.exists(eye_db_path):
            # Create the database file if it doesn't exist
            try:
                # Initialize eye.sqlite with the eye_metrics table
                conn = sqlite3.connect(eye_db_path)
                cursor = conn.cursor()

                # Create the eye_metrics table
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS eye_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    session_id TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    hand_detection_count INTEGER DEFAULT 0,
                    hand_detection_duration REAL DEFAULT 0.0,
                    loss_eye_contact_count INTEGER DEFAULT 0,
                    looking_away_duration REAL DEFAULT 0.0,
                    bad_posture_count INTEGER DEFAULT 0,
                    bad_posture_duration REAL DEFAULT 0.0,
                    is_auto_save BOOLEAN DEFAULT 0
                )
                ''')

                conn.commit()
                conn.close()
                print(f"Created database file: {eye_db_path}")
            except Exception as e:
                print(f"Error creating database file: {str(e)}")
                # Continue anyway, as we'll still return the current metrics

        # Also save to our Flask SQLAlchemy model
        try:
            # Create a new EyeMetrics record
            eye_metrics = EyeMetrics(
                user_id=session['user_id'],
                session_id=metrics_tracker.session_id,
                hand_detection_count=metrics_tracker.metrics["handDetectionCount"],
                hand_detection_duration=metrics_tracker.metrics["handDetectionDuration"],
                loss_eye_contact_count=metrics_tracker.metrics["lossEyeContactCount"],
                looking_away_duration=metrics_tracker.metrics["lookingAwayDuration"],
                bad_posture_count=metrics_tracker.metrics["badPostureCount"],
                bad_posture_duration=metrics_tracker.metrics["badPostureDuration"],
                is_auto_save=True
            )

            # Check if there's an existing auto-save record for this session
            existing = EyeMetrics.query.filter_by(
                user_id=session['user_id'],
                session_id=metrics_tracker.session_id,
                is_auto_save=True
            ).first()

            if existing:
                # Update existing record instead of creating a new one
                existing.hand_detection_count = metrics_tracker.metrics["handDetectionCount"]
                existing.hand_detection_duration = metrics_tracker.metrics[
                    "handDetectionDuration"]
                existing.hand_detection_count = metrics_tracker.metrics["handDetectionCount"]
                existing.hand_detection_duration = metrics_tracker.metrics["handDetectionDuration"]
                existing.loss_eye_contact_count = metrics_tracker.metrics["lossEyeContactCount"]
                existing.looking_away_duration = metrics_tracker.metrics["lookingAwayDuration"]
                existing.bad_posture_count = metrics_tracker.metrics["badPostureCount"]
                existing.bad_posture_duration = metrics_tracker.metrics["badPostureDuration"]
                existing.timestamp = datetime.now()
            else:
                # Add new record
                db.session.add(eye_metrics)

            db.session.commit()
        except Exception as e:
            error_msg = str(e)
            print(f"Error saving to eye metrics database: {error_msg}")
            db.session.rollback()

            # Additional handling for common errors
            if "no such table" in error_msg.lower():
                # The table doesn't exist, try to create it
                try:
                    with app.app_context():
                        db.create_all(bind_key='eye_metrics')
                        print("Created eye_metrics table")

                        # Try saving again
                        if existing:
                            # Update record
                            existing.hand_detection_count = metrics_tracker.metrics["handDetectionCount"]
                            existing.hand_detection_duration = metrics_tracker.metrics[
                                "handDetectionDuration"]
                            existing.loss_eye_contact_count = metrics_tracker.metrics[
                                "lossEyeContactCount"]
                            existing.looking_away_duration = metrics_tracker.metrics[
                                "lookingAwayDuration"]
                            existing.bad_posture_count = metrics_tracker.metrics["badPostureCount"]
                            existing.bad_posture_duration = metrics_tracker.metrics["badPostureDuration"]
                            existing.timestamp = datetime.now()
                        else:
                            # Add new record
                            db.session.add(eye_metrics)

                        db.session.commit()
                        print("Successfully saved metrics after creating table")
                except Exception as inner_e:
                    print(f"Failed to create table: {str(inner_e)}")

        return jsonify({
            'success': True,
            'metrics': metrics_tracker.metrics
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Video analysis not started'
        })


@app.route('/view_eye_metrics')
def view_eye_metrics():
    if 'user_id' not in session:
        flash('Please log in.', 'error')
        return redirect(url_for('login'))

    # Query data from the eye_metrics table by user_id directly
    user_id = session['user_id']
    metrics_data = EyeMetrics.query.filter_by(user_id=user_id).order_by(
        EyeMetrics.timestamp.desc()).limit(10).all()

    # Format the data for display
    formatted_data = []
    for metric in metrics_data:
        formatted_data.append({
            'id': metric.id,
            'session_id': metric.session_id,
            'timestamp': metric.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'hand_detection_count': metric.hand_detection_count,
            'hand_detection_duration': f"{metric.hand_detection_duration:.2f}s",
            'loss_eye_contact_count': metric.loss_eye_contact_count,
            'looking_away_duration': f"{metric.looking_away_duration:.2f}s",
            'bad_posture_count': metric.bad_posture_count,
            'bad_posture_duration': f"{metric.bad_posture_duration:.2f}s",
            'is_auto_save': 'Yes' if metric.is_auto_save else 'No'
        })

    # Show the database file path
    instance_path = os.path.join(os.getcwd(), 'instance')
    db_path = os.path.join(instance_path, 'eye.sqlite')
    db_exists = os.path.exists(db_path)

    return jsonify({
        'success': True,
        'db_path': db_path,
        'db_exists': db_exists,
        'data': formatted_data
    })

# New route to process audio recordings


@app.route('/process_audio_recording', methods=['POST'])
def process_audio_recording():
    print("=== Processing audio recording ===")
    # Temporarily disabled user check for testing
    # if 'user_id' not in session:
    #     print("Error: User not logged in")
    #     return jsonify({'success': False, 'error': 'User not logged in'})

    if 'audio' not in request.files:
        print("Error: No audio file provided")
        return jsonify({'success': False, 'error': 'No audio file provided'})

    original_audio_path = None
    converted_audio_path = None
    output_text_file = None

    try:
        # Get the audio file from the request
        audio_file = request.files['audio']
        print(f"Received audio file: {audio_file.filename}, type: {audio_file.mimetype}, size: {audio_file.content_length} bytes")

        # Save the original audio file temporarily (likely WebM or similar)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_dir = 'temp_audio'
        os.makedirs(temp_dir, exist_ok=True)
        # Use a generic extension first, or determine from mimetype if possible
        original_filename = f"recording_original_{timestamp}.audio"
        original_audio_path = os.path.join(temp_dir, original_filename)
        print(f"Saving original audio to: {os.path.abspath(original_audio_path)}")
        audio_file.save(original_audio_path)
        print(f"Original audio file saved successfully")

        # Convert the saved audio to standard PCM WAV using pydub
        try:
            print("Attempting audio conversion to WAV...")
            # Load the audio file (pydub will try to auto-detect format)
            audio_segment = AudioSegment.from_file(original_audio_path)
            # Define the path for the converted WAV file
            converted_filename = f"recording_converted_{timestamp}.wav"
            converted_audio_path = os.path.join(temp_dir, converted_filename)
            print(f"Exporting converted WAV to: {os.path.abspath(converted_audio_path)}")
            # Export as WAV (16-bit PCM is standard for speech recognition)
            audio_segment.export(converted_audio_path, format="wav")
            print("Audio conversion successful!")
        except Exception as convert_e:
            print(f"Error converting audio with pydub: {convert_e}")
            print("Ensure FFmpeg is installed and in your system's PATH.")
            # Fallback: Try using the original file anyway? Or fail here?
            # For now, let's fail if conversion doesn't work.
            return jsonify({'success': False, 'error': f'Audio conversion failed: {convert_e}. Is FFmpeg installed?'})

        # Transcribe the *converted* WAV audio file
        try:
            from audio_to_text import transcribe_audio_file
            text_filename = f"transcript_{timestamp}.txt"
            text_path = os.path.join(temp_dir, text_filename)
            print(f"Transcribing converted WAV: {converted_audio_path}")
            output_text_file = transcribe_audio_file(converted_audio_path, text_path)

            if output_text_file and os.path.exists(output_text_file):
                with open(output_text_file, 'r', encoding='utf-8') as file:
                    transcribed_text = file.read().strip()
                print(f"Transcription successful: '{transcribed_text}'")
                return jsonify({'success': True, 'transcribed_text': transcribed_text})
            else:
                print("Transcription failed after conversion.")
                # Use the error message from transcribe_audio_file if possible, 
                # otherwise provide a generic message.
                # This requires transcribe_audio_file to potentially return the error.
                # For now:
                return jsonify({'success': False, 'error': "Transcription failed after audio conversion."})

        except Exception as trans_e:
            print(f"Error during transcription call: {trans_e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': f'Error calling transcription: {str(trans_e)}'})

    except Exception as e:
        import traceback
        print(f"Server error in /process_audio_recording: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'})
    
    finally:
        # Cleanup temporary files
        print("Cleaning up temporary audio files...")
        if original_audio_path and os.path.exists(original_audio_path):
            try:
                os.remove(original_audio_path)
                print(f"Removed: {original_audio_path}")
            except Exception as e:
                print(f"Error removing original file {original_audio_path}: {e}")
        if converted_audio_path and os.path.exists(converted_audio_path):
            try:
                os.remove(converted_audio_path)
                print(f"Removed: {converted_audio_path}")
            except Exception as e:
                print(f"Error removing converted file {converted_audio_path}: {e}")
        if output_text_file and os.path.exists(output_text_file):
            try:
                os.remove(output_text_file)
                print(f"Removed: {output_text_file}")
            except Exception as e:
                print(f"Error removing transcript file {output_text_file}: {e}")

# Helper function to run run_interview_advisor.py as a subprocess


def run_interview_advisor_process(text_input):
    """
    Run run_interview_advisor.py as a subprocess and pass the text input to it.
    Returns the response from the advisor.
    """
    try:
        # Construct the command
        cmd = [sys.executable, 'run_interview_advisor.py', '--input', text_input]

        # Run the process
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True)

        # Return the stdout output
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running run_interview_advisor.py: {e}")
        print(f"Error output: {e.stderr}")
        return None
    except Exception as e:
        print(f"Unexpected error running run_interview_advisor.py: {e}")
        return None

# Register custom Jinja filters
@app.template_filter('escapejs')
def escapejs_filter(val):
    """Escape string for JavaScript string literals."""
    if isinstance(val, Markup):
        val = val.unescape()
    val = val.replace('\\', '\\\\')
    val = val.replace('"', '\\"')
    val = val.replace("'", "\\'")
    val = val.replace('\n', '\\n')
    val = val.replace('\r', '\\r')
    val = val.replace('</', '<\\/')  # For closing script tags
    return val

if __name__ == '__main__':
    app.run(debug=True)
