from flask import Flask, render_template, request, redirect, url_for, session, flash , jsonify
from models import db, User, Resume, UserEmotionData, SessionSummary
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

load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///project_db.sqlite3'
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

with app.app_context():
    db.create_all()


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
    return render_template('profile.html')


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
    resume_path = user_resume.resume_path
    if not resume_path:
        flash('Please upload a resume first.', 'error')
        return redirect(url_for('dashboard'))
    
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

    functions.initialize(default_resume_path, resume_text, analysis, career_paths, skill_keywords)
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

from flask import jsonify

@app.route('/start-interview', methods=['GET', 'POST'])
def start_interview():
    if 'user_id' not in session:
        flash('Please log in.', 'error')
        return redirect(url_for('login'))
    
    user_resume = Resume.query.filter_by(user_id=session['user_id']).first()
    resume_path = user_resume.resume_path
    if not resume_path:
        flash('Please upload a resume first.', 'error')
        return redirect(url_for('dashboard'))
    
    chat_history = session.get('chat_history', [])

    if not chat_history:
        message = "Hello! I'm the AI interviewer. Are you ready DAIICT?"
        chat_history = [("AI", message)]

    if request.method == 'POST':
        user_message = request.form['message']
        chat_history.append(("User", user_message))
        
        ai_response = ""
        #ai_response = functions.generate_response(user_message)
        #chat_history.append(("AI", ai_response))
        
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
            emotion_data = UserEmotionData(
                user_id=user_id,
                emotion=detected_emotion,
                confidence=probability
            )
            db.session.add(emotion_data)
            db.session.commit()
    
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
    
    # Clean up and save metrics if the tracker exists
    if metrics_tracker is not None:
        metrics_tracker.close()  # Stop thread and save metrics
        metrics_tracker = None
    
    return jsonify({'success': True, 'message': 'Video analysis ended and metrics saved'})

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
        
        return jsonify({
            'success': True,
            'metrics': metrics_tracker.metrics
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Video analysis not started'
        })

if __name__ == '__main__':
    app.run(debug=True)
