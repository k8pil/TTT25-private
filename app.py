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
                "description": "Use data to solve complex problems and provide insights.",
                "skills_needed": ["Python", "R", "Statistics", "Machine Learning", "Data Visualization"],
                "growth_potential": "High",
                "salary_range": "$90,000 - $150,000"
            },
            {
                "title": "Software Engineer",
                "description": "Design and build applications and systems.",
                "skills_needed": ["Programming", "Algorithms", "System Design", "Testing", "Debugging"],
                "growth_potential": "High",
                "salary_range": "$80,000 - $140,000"
            },
            {
                "title": "UX/UI Designer",
                "description": "Create intuitive and appealing user interfaces.",
                "skills_needed": ["UI Design", "User Research", "Prototyping", "Visual Design", "HTML/CSS"],
                "growth_potential": "Medium",
                "salary_range": "$70,000 - $120,000"
            },
            {
                "title": "Product Manager",
                "description": "Lead product development from conception to launch.",
                "skills_needed": ["Product Strategy", "User Stories", "Market Analysis", "Communication", "Leadership"],
                "growth_potential": "High",
                "salary_range": "$90,000 - $160,000"
            },
            {
                "title": "DevOps Engineer",
                "description": "Build and maintain infrastructure and deployment pipelines.",
                "skills_needed": ["Linux", "Cloud Platforms", "CI/CD", "Automation", "Docker/Kubernetes"],
                "growth_potential": "Very High",
                "salary_range": "$85,000 - $145,000"
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

if __name__ == '__main__':
    app.run(debug=True)
