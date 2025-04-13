from flask import Flask, render_template, request, redirect, url_for, session, flash , jsonify
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
#from body_language_decoder import BodyLanguageDecoder
import sqlite3
from interview_advisor.integration import mainmenu, getresumesir
import glob
import requests
import json
import subprocess

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

load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv('SECRET_KEY') or 'dev_secret_key_for_testing_only'

# Ensure instance directory exists
instance_path = os.path.join(os.getcwd(), 'instance')
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
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # Suppress TensorFlow warnings

def build_model():
    model = Sequential()
    model.add(Conv2D(32, kernel_size=(3, 3), activation='relu', input_shape=(48,48,1)))
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
emotion_dict = {0: "Angry", 1: "Disgusted", 2: "Fearful", 3: "Happy", 4: "Neutral", 5: "Sad", 6: "Surprised"}
# Load face cascade classifier
cascade_file_paths = [
    'haarcascade_frontalface_default.xml',
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'haarcascade_frontalface_default.xml'),
    os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_default.xml')
]
facecasc = None
for cascade_path in cascade_file_paths:
    if os.path.exists(cascade_path):
        facecasc = cv2.CascadeClassifier(cascade_path)
        if not facecasc.empty():
            break

#decoder = BodyLanguageDecoder(model_path='Body_language.pkl')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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
            max_eye_contact_loss = max(max_eye_contact_loss, metric.loss_eye_contact_count)
            max_looking_away = max(max_looking_away, metric.looking_away_duration)
            max_bad_posture_duration = max(max_bad_posture_duration, metric.bad_posture_duration)
            
            # Update min values (only if not zero to avoid skewing data)
            if metric.loss_eye_contact_count > 0:
                min_eye_contact_loss = min(min_eye_contact_loss, metric.loss_eye_contact_count)
            if metric.looking_away_duration > 0:
                min_looking_away = min(min_looking_away, metric.looking_away_duration)
            if metric.bad_posture_duration > 0:
                min_bad_posture_duration = min(min_bad_posture_duration, metric.bad_posture_duration)
        
        # Calculate averages
        avg_eye_contact_loss = round(total_eye_contact_loss / total_interviews)
        avg_looking_away = round(total_looking_away / total_interviews, 1)
        avg_bad_posture_count = round(total_bad_posture_count / total_interviews)
        avg_bad_posture_duration = round(total_bad_posture_duration / total_interviews, 1)
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
        looking_away_ratio = round((latest_metric.looking_away_duration / estimated_total_time) * 100) if latest_metric else 0
        
        # Calculate focus rate
        focus_rate = 100 - looking_away_ratio
        
        # Calculate posture quality
        posture_quality = round(100 - ((latest_metric.bad_posture_duration / estimated_total_time) * 100)) if latest_metric else 0
        
        # Calculate hand movement frequency (movements per minute)
        hand_frequency = round((latest_metric.hand_detection_count / (estimated_total_time / 60)), 1) if latest_metric else 0
        
        # Calculate overall confidence score (weighted average of key metrics)
        confidence_score = round(
            (focus_rate * 0.4) +  # 40% weight to focus
            (posture_quality * 0.4) +  # 40% weight to posture
            (min(100, 100 - (hand_frequency * 3)) * 0.2)  # 20% weight to hand movement
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
            'avg_looking_away_ratio': round((avg_looking_away / 180) * 100),  # Assuming avg interview is 3 min
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
        
        analytics['improvement_areas'] = ", ".join(improvement_areas) if improvement_areas else "None"
    
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
    
@app.route('/start-guidance')
def start_guidance():
    if 'user_id' not in session:
        flash('Please log in.', 'error')
        return redirect(url_for('login'))
    user_resume = Resume.query.filter_by(user_id=session['user_id']).first()
    if not user_resume:
        flash('Please upload a resume first.', 'error')
        return redirect(url_for('dashboard'))
    resume_path = user_resume.resume_path

    default_resume_path = resume_path
    resume_text = ""
    analysis = {}
    career_paths = [
                {
                    "title": "Data Scientist",
                    "description": "Use data to solve complex problems and provide actionable insights using statistical, machine learning, and data visualization techniques.",
                    "skills_needed": ["Python", "R", "Statistics", "Machine Learning", "Data Visualization", "SQL", "Big Data Tools"],
                    "growth_potential": "High",
                    "salary_range": "$90,000 - $150,000"
                },
                {
                    "title": "Software Engineer",
                    "description": "Design, develop, test, and maintain software systems and applications for various platforms.",
                    "skills_needed": ["Programming", "Algorithms", "System Design", "Testing", "Debugging", "Version Control", "APIs"],
                    "growth_potential": "High",
                    "salary_range": "$80,000 - $140,000"
                },
                {
                    "title": "UX/UI Designer",
                    "description": "Create intuitive and visually appealing digital experiences by focusing on usability and user interaction design.",
                    "skills_needed": ["UI Design", "UX Research", "Prototyping", "Visual Design", "HTML/CSS", "Figma", "Adobe XD"],
                    "growth_potential": "Medium",
                    "salary_range": "$70,000 - $120,000"
                },
                {
                    "title": "Product Manager",
                    "description": "Lead product development cycles, define product vision, manage teams, and drive product strategy to meet user needs and business goals.",
                    "skills_needed": ["Product Strategy", "User Stories", "Agile/Scrum", "Market Analysis", "Communication", "Leadership"],
                    "growth_potential": "High",
                    "salary_range": "$90,000 - $160,000"
                },
                {
                    "title": "DevOps Engineer",
                    "description": "Develop, maintain, and optimize cloud-based infrastructure and deployment pipelines for efficient software delivery.",
                    "skills_needed": ["Linux", "Cloud Platforms", "CI/CD", "Automation", "Docker", "Kubernetes", "Monitoring Tools"],
                    "growth_potential": "Very High",
                    "salary_range": "$85,000 - $145,000"
                },
                {
                    "title": "Cybersecurity Analyst",
                    "description": "Protect digital systems, networks, and data from cyber threats by monitoring systems and implementing security measures.",
                    "skills_needed": ["Network Security", "Firewalls", "Incident Response", "Penetration Testing", "SIEM", "Python"],
                    "growth_potential": "High",
                    "salary_range": "$85,000 - $140,000"
                },
                {
                    "title": "AI/ML Engineer",
                    "description": "Design and implement machine learning algorithms and artificial intelligence solutions for real-world applications.",
                    "skills_needed": ["Deep Learning", "NLP", "TensorFlow", "PyTorch", "Python", "Data Engineering", "Model Deployment"],
                    "growth_potential": "Very High",
                    "salary_range": "$100,000 - $170,000"
                },
                {
                    "title": "Digital Marketing Manager",
                    "description": "Plan and execute digital marketing strategies to promote products and services and optimize online presence.",
                    "skills_needed": ["SEO", "SEM", "Google Analytics", "Email Marketing", "Content Strategy", "Social Media"],
                    "growth_potential": "High",
                    "salary_range": "$65,000 - $120,000"
                },
                {
                    "title": "Graphic Designer",
                    "description": "Create visual concepts and designs for print and digital media to communicate ideas that inspire and inform.",
                    "skills_needed": ["Adobe Photoshop", "Illustrator", "Typography", "Branding", "Layout Design", "Color Theory"],
                    "growth_potential": "Medium",
                    "salary_range": "$50,000 - $90,000"
                },
                {
                    "title": "Biomedical Engineer",
                    "description": "Combine engineering principles with medical sciences to develop equipment, devices, and software used in healthcare.",
                    "skills_needed": ["Biology", "Electrical Engineering", "Medical Devices", "Matlab", "3D Modeling", "Regulatory Standards"],
                    "growth_potential": "High",
                    "salary_range": "$75,000 - $130,000"
                },
                {
                    "title": "Mechanical Engineer",
                    "description": "Design and develop mechanical systems and devices, applying physics and materials science.",
                    "skills_needed": ["CAD", "SolidWorks", "Thermodynamics", "Mechanics", "MATLAB", "Manufacturing Processes"],
                    "growth_potential": "Medium",
                    "salary_range": "$70,000 - $120,000"
                },
                {
                    "title": "Civil Engineer",
                    "description": "Design, construct, and maintain infrastructure projects such as roads, bridges, and buildings.",
                    "skills_needed": ["AutoCAD", "Structural Analysis", "Project Management", "Construction Materials", "Site Planning"],
                    "growth_potential": "Medium",
                    "salary_range": "$65,000 - $110,000"
                },
                {
                    "title": "Psychologist",
                    "description": "Study cognitive, emotional, and social behaviors and help clients improve their mental health through therapy.",
                    "skills_needed": ["Counseling", "Behavioral Analysis", "Clinical Psychology", "Ethics", "Communication"],
                    "growth_potential": "Medium",
                    "salary_range": "$60,000 - $110,000"
                },
                {
                    "title": "Teacher / Educator",
                    "description": "Educate and inspire students by delivering curriculum and supporting learning across various subjects.",
                    "skills_needed": ["Curriculum Development", "Classroom Management", "Assessment", "Subject Expertise", "Empathy"],
                    "growth_potential": "Medium",
                    "salary_range": "$40,000 - $85,000"
                },
                {
                    "title": "Environmental Scientist",
                    "description": "Study the environment and develop strategies to reduce environmental problems and promote sustainability.",
                    "skills_needed": ["Ecology", "GIS", "Data Analysis", "Field Research", "Environmental Policy", "Lab Skills"],
                    "growth_potential": "High",
                    "salary_range": "$60,000 - $100,000"
                },
                {
                    "title": "Financial Analyst",
                    "description": "Analyze financial data to guide investment and business decisions.",
                    "skills_needed": ["Excel", "Financial Modeling", "Accounting", "Data Interpretation", "SQL", "Economics"],
                    "growth_potential": "High",
                    "salary_range": "$70,000 - $120,000"
                },
                {
                    "title": "Blockchain Developer",
                    "description": "Build decentralized applications and smart contracts using blockchain technology.",
                    "skills_needed": ["Solidity", "Ethereum", "Smart Contracts", "Cryptography", "Node.js", "Distributed Systems"],
                    "growth_potential": "Very High",
                    "salary_range": "$100,000 - $180,000"
                },
                {
                    "title": "Cloud Solutions Architect",
                    "description": "Design scalable and secure cloud architectures tailored to business needs.",
                    "skills_needed": ["AWS/Azure/GCP", "System Design", "Networking", "Security", "DevOps", "Cloud Automation"],
                    "growth_potential": "Very High",
                    "salary_range": "$120,000 - $200,000"
                },
                {
                    "title": "Entrepreneur / Startup Founder",
                    "description": "Identify problems, build businesses, and create value through innovative solutions.",
                    "skills_needed": ["Leadership", "Business Strategy", "Fundraising", "Marketing", "Product Development", "Resilience"],
                    "growth_potential": "Unlimited",
                    "salary_range": "Variable (Startup Equity or $0 - $1M+)"
                },
                {
                    "title": "Content Creator / Influencer",
                    "description": "Create digital content (videos, blogs, social posts) to engage audiences and build a personal brand.",
                    "skills_needed": ["Content Strategy", "Video Editing", "SEO", "Social Media", "Creativity", "Branding"],
                    "growth_potential": "High",
                    "salary_range": "$30,000 - $250,000+"
                }
                ]
    skill_keywords = [
            "python", "java", "javascript", "c++", "c#", "php", "ruby", "swift", "kotlin", "golang",
            "html", "css", "sql", "nosql", "mongodb", "mysql", "postgresql", "react", "angular", "vue",
            "node.js", "express", "django", "flask", "spring", "machine learning", "ai", "data science",
            "data analysis", "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy", "tableau",
            "power bi", "aws", "azure", "gcp", "docker", "kubernetes", "jenkins", "git", "jira",
            "agile", "scrum", "project management", "product management", "ux", "ui", "figma",
            "sketch", "adobe xd", "photoshop", "illustrator", "leadership", "communication",
            "problem solving", "critical thinking", "teamwork", "customer service", "marketing",
            "sales", "finance", "accounting", "human resources", "operations", "devops", "cloud"
        ]

    functions.initialize(default_resume_path, resume_text, analysis, career_paths, skill_keywords, session['user_id'])
    career_paths_list = functions.run()
    print(career_paths_list)

    print("Vars:")
    print(default_resume_path)
    print(resume_text)
    print(analysis)
    print(career_paths)
    print(skill_keywords)

    structure_tips, content_improvement_tips, tech_and_soft_skill_tips, experience_tips, achievement_tips, ats_tips, modern_tips, tailoring_tips = [], [], [], [], [], [], [], []
    structure_tips, content_improvement_tips, tech_and_soft_skill_tips, experience_tips, achievement_tips, ats_tips, modern_tips, tailoring_tips = functions.provide_resume_tips()

    roadmap_dict = {}
    print("Roadmap Dict ke liye career_paths_list:")
    print(career_paths_list)
    for path in career_paths_list:
        roadmap_dict[path[0]] = functions.generate_roadmap(path[0][:-13])

    return render_template('guidance.html', user_resume=user_resume, career_paths_list=career_paths_list, structure_tips=structure_tips, content_improvement_tips=content_improvement_tips, tech_and_soft_skill_tips=tech_and_soft_skill_tips, experience_tips=experience_tips, achievement_tips=achievement_tips, ats_tips=ats_tips, modern_tips=modern_tips, tailoring_tips=tailoring_tips, roadmap_dict=roadmap_dict)

# Function to get menu options as a formatted string for the interviewer's chat
def get_formatted_menu():
    menu_items = mainmenu()
    menu_text = "Please select an option:<br><br>"
    
    for i, item in enumerate(menu_items, 1):
        menu_text += f"{i}. {item}<br>"
    
    return menu_text

# Function to get formatted resume analysis for the chat interface
def get_resume_analysis_for_chat():
    """
    Retrieves the most recent resume analysis and formats it for display in the chat interface.
    Returns a string with proper line breaks that will render in the chat.
    """
    try:
        # Find the most recent analysis file in the cache directory
        analysis_dir = "cache/resume_analysis"
        if not os.path.exists(analysis_dir):
            return "No resume analysis found. Please analyze your resume first."
        
        # Get the most recent analysis file
        analysis_files = glob.glob(f"{analysis_dir}/analysis_*.txt")
        if not analysis_files:
            return "No resume analysis found. Please analyze your resume first."
        
        # Sort by modification time (most recent first)
        most_recent_file = max(analysis_files, key=os.path.getmtime)
        
        # Read the file contents
        with open(most_recent_file, 'r', encoding='utf-8') as f:
            analysis_text = f.read()
        
        # Format the text with proper line breaks
        formatted_text = "📋 RESUME ANALYSIS RESULTS\n\n" + analysis_text
        
        return formatted_text
    
    except Exception as e:
        print(f"Error retrieving resume analysis: {e}")
        return "There was an error retrieving your resume analysis."

# Function to start a new interview and return the first question
def start_new_interview():
    """
    Starts a new interview session and returns the initial interview question.
    Uses ElevenLabs TTS if available.
    """
    try:
        # Default introduction message
        intro_message = "Hello! I'm your AI interviewer today. I'll be asking you some questions based on your resume. Let's get started with your introduction. Could you please tell me a bit about yourself and your background?"
        
        # Future integration - this would ideally connect to the interview_advisor module
        # to get a more personalized introduction based on the resume
        
        # Convert to speech if TTS is available
        if TTS_AVAILABLE and tts_service:
            try:
                # This would play the audio on the server, which isn't ideal for web
                # In a real implementation, we would generate audio files and serve them to the client
                tts_service.text_to_speech(intro_message)
                print("TTS audio generated successfully")
            except Exception as e:
                print(f"TTS Error: {e}")
        
        # Format the intro message with line breaks instead of HTML
        formatted_intro = intro_message
        
        # Store interview state in session
        session['interview_active'] = True
        session['interview_step'] = 1
        
        return formatted_intro
    
    except Exception as e:
        print(f"Error starting interview: {e}")
        return "There was an error starting the interview. Please try again."

# Function to process an interview response and get the next question
def process_interview_response(user_response):
    """
    Processes a user's interview response and returns the next appropriate question.
    Uses ElevenLabs TTS if available.
    """
    try:
        # Get current interview step
        interview_step = session.get('interview_step', 0)
        
        # Define a list of interview questions
        interview_questions = [
            "Great! Now, could you tell me about your most challenging project and how you overcame obstacles?",
            "Thank you for sharing that. What would you say are your top three technical skills, and how have you applied them in your work?",
            "Interesting! Now, how do you stay updated with the latest trends and technologies in your field?",
            "That's helpful to know. Could you describe a situation where you had to work with a difficult team member? How did you handle it?",
            "Now, looking at your experience with [project mentioned in resume], what was your specific contribution to the team?",
            "Where do you see yourself professionally in the next 3-5 years?",
            "Thank you for all your responses. Is there anything else you'd like to add or any questions you have for me?"
        ]
        
        # Increment the interview step
        interview_step += 1
        session['interview_step'] = interview_step
        
        # Check if we've reached the end of the interview
        if interview_step >= len(interview_questions):
            end_message = "Thank you for completing this interview! I hope you found it helpful. You can select another option from the menu or start a new interview if you'd like to practice more."
            session['interview_active'] = False
            session['interview_step'] = 0
            
            # Convert to speech if TTS is available
            if TTS_AVAILABLE and tts_service:
                try:
                    tts_service.text_to_speech(end_message)
                except Exception as e:
                    print(f"TTS Error: {e}")
            
            return end_message
        
        # Get the next question
        next_question = interview_questions[interview_step - 1]
        
        # Convert to speech if TTS is available
        if TTS_AVAILABLE and tts_service:
            try:
                tts_service.text_to_speech(next_question)
            except Exception as e:
                print(f"TTS Error: {e}")
        
        # Return the question as plain text
        return next_question
    
    except Exception as e:
        print(f"Error processing interview response: {e}")
        return "There was an error processing your response. Please try again."

def generate_response(user_message):
    menu_items = mainmenu()
    response = ""
    
    # Check if we're in an active interview session
    if session.get('interview_active', False):
        # If we're in an active interview, process the user's response
        return process_interview_response(user_message)
    
    # Loop through each menu item to check if the user selected one
    for i, item in enumerate(menu_items, 1):
        # Check if the message contains either the menu item name or its number
        if item.lower() in user_message.lower() or str(i) == user_message.strip():
            # Handle "Upload Resume" option specially
            if i == 1 or "upload resume" in item.lower():
                # Get the resume directory using getresumesir()
                resume_dir = getresumesir()
                
                # Get user's resume from the database
                if 'user_id' in session:
                    user_resume = Resume.query.filter_by(user_id=session['user_id']).first()
                    if user_resume:
                        resume_path = user_resume.resume_path
                        # Format the response with the resume path
                        return f"Processing resume from: {resume_path}<br><br>Resume directory: {resume_dir}<br><br>Resume uploaded successfully! You can now proceed with the interview."
                    else:
                        return "No resume found. Please upload a resume on the dashboard first."
                else:
                    return "Please log in to access your resume."
            
            # Handle "Start Interview" option specially
            if i == 2 or "start interview" in item.lower():
                return start_new_interview()
            
            # Handle "Process Interview Answer" option
            if i == 3 or "process interview answer" in item.lower():
                if session.get('interview_active', False):
                    return "Please type your answer to the current question in the chat."
                else:
                    return "No active interview. Please start an interview first by selecting option 2."
            
            # Handle "End Interview" option
            if i == 4 or "end interview" in item.lower():
                if session.get('interview_active', False):
                    session['interview_active'] = False
                    session['interview_step'] = 0
                    return "Interview ended. Thank you for participating!"
                else:
                    return "No active interview to end. Please start an interview first by selecting option 2."
            
            # Handle "Resume Analysis" option specially
            if i == 5 or "resume analysis" in item.lower():
                # Return the formatted resume analysis for the chat
                return get_resume_analysis_for_chat()
            
            # Handle "Change TTS Voice" option
            if i == 6 or "change tts voice" in item.lower():
                if TTS_AVAILABLE and tts_service:
                    # This would ideally connect to the voice selection functionality
                    return "Voice change functionality is available. In a full implementation, you would be able to select from different voices here."
                else:
                    return "TTS is not available in this environment."
            
            # Handle "Test Audio" option
            if item.lower() == "test audio" or "test audio" in item.lower():
                if TTS_AVAILABLE and tts_service:
                    try:
                        tts_service.test_audio()
                        return "Audio test initiated. You should hear a test message if your audio is working correctly."
                    except Exception as e:
                        return f"Error testing audio: {e}"
                else:
                    return "TTS is not available in this environment."
            
            # Return standard response for other options
            return f"You selected: {item}<br><br>Processing your request..."
    
    # If no valid option was selected, prompt the user again
    response = "Please select a valid option from the menu:<br><br>"
    for i, item in enumerate(menu_items, 1):
        response += f"{i}. {item}<br>"
    
    return response

@app.route('/start-interview', methods=['GET', 'POST'])
def start_interview():
    if 'user_id' not in session:
        flash('Please log in.', 'error')
        return redirect(url_for('login'))
    
    user_resume = Resume.query.filter_by(user_id=session['user_id']).first()
    if not user_resume:
        flash('Please upload a resume first.', 'error')
        return redirect(url_for('dashboard'))
    resume_path = user_resume.resume_path
    
    chat_history = session.get('chat_history', [])

    if not chat_history:
        # First, process the resume with the LLM
        resume_dir = getresumesir()
        
        # This ensures the resume directory exists and is prepared
        if not os.path.exists(resume_dir):
            os.makedirs(resume_dir, exist_ok=True)
        
        # Process the resume with the LLM (this would ideally use the resume processor from interview_advisor)
        processing_message = f"Processing your resume from: {resume_path}<br><br>Please wait..."
        chat_history = [("AI", processing_message)]
        
        try:
            # Here we would normally use the interview_advisor.resume_processor to process the resume
            # But for now, we'll just simulate this step
            
            # After successful processing, display the main menu
            interviewer_message = get_formatted_menu()
            chat_history = [("AI", f"Your resume has been successfully processed!<br><br>{interviewer_message}")]
        except Exception as e:
            chat_history = [("AI", f"There was an error processing your resume: {str(e)}<br><br>Please try again later.")]
            
        # Save the chat history to the session
        session['chat_history'] = chat_history

    if request.method == 'POST':
        user_message = request.form['message']
        chat_history.append(("User", user_message))
        
        ai_response = ""
        ai_response = generate_response(user_message)
        chat_history.append(("AI", ai_response))
        
        session['chat_history'] = chat_history
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'response': ai_response})
    
    return render_template('interview.html', user_resume=user_resume, chat_history=chat_history)


@app.route('/clear-chat-history', methods=['GET', 'POST'])
def clear_chat_history():
    session['chat_history'] = []
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
        cropped_img = np.expand_dims(np.expand_dims(cv2.resize(roi_gray, (48, 48)), -1), 0)
        
        # Make prediction
        prediction = model.predict(cropped_img)
        maxindex = int(np.argmax(prediction))
        probability = float(prediction[0][maxindex])
        detected_emotion = emotion_dict[maxindex]
        
        # Add text to the image
        cv2.putText(frame, detected_emotion, (x+20, y-60), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
        
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
            
            print(f"Final eye metrics saved to database for session {metrics_tracker.session_id}")
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
    metrics_data = EyeMetrics.query.filter_by(user_id=user_id).order_by(EyeMetrics.timestamp.desc()).limit(10).all()
    
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
    
    try:
        # Get the audio file from the request
        audio_file = request.files['audio']
        print(f"Received audio file: {audio_file.filename}, size: {audio_file.content_length} bytes")
        
        # Save the audio file temporarily
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        audio_filename = f"recording_{timestamp}.wav"
        audio_path = os.path.join('temp_audio', audio_filename)
        
        # Ensure temp directory exists with proper permissions
        os.makedirs('temp_audio', exist_ok=True)
        print(f"Saving audio to: {os.path.abspath(audio_path)}")
        
        # Save the file
        audio_file.save(audio_path)
        print(f"Audio file saved successfully")
        
        # Transcribe audio to text using audio_to_text.py functionality
        try:
            # Import functionality from audio_to_text.py
            from audio_to_text import transcribe_audio_file
            
            # Generate output filename
            text_filename = f"transcript_{timestamp}.txt"
            text_path = os.path.join('temp_audio', text_filename)
            
            print(f"Transcribing audio to {text_path}")
            # Transcribe audio
            output_file = transcribe_audio_file(audio_path, text_path)
            
            # Read transcribed text
            if output_file and os.path.exists(output_file):
                with open(output_file, 'r', encoding='utf-8') as file:
                    transcribed_text = file.read().strip()
                print(f"Transcription successful: '{transcribed_text}'")
            else:
                transcribed_text = "Sorry, I couldn't transcribe your audio. Please try again."
                print("Transcription failed - no output file")
            
            # Return the transcribed text
            print(f"Returning transcribed text: {transcribed_text}")
            return jsonify({
                'success': True,
                'transcribed_text': transcribed_text
            })
            
            # Cleanup temporary files
            try:
                os.remove(audio_path)
                if output_file and os.path.exists(output_file):
                    os.remove(output_file)
            except Exception as e:
                print(f"Error cleaning up temporary files: {e}")
                
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False, 
                'error': f'Error transcribing audio: {str(e)}'
            })
    
    except Exception as e:
        import traceback
        print(f"Server error: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        })

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
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Return the stdout output
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running run_interview_advisor.py: {e}")
        print(f"Error output: {e.stderr}")
        return None
    except Exception as e:
        print(f"Unexpected error running run_interview_advisor.py: {e}")
        return None

if __name__ == '__main__':
    app.run(debug=True)
