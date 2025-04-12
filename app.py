from flask import Flask, render_template, request, redirect, url_for, session, flash
from models import db, User, Resume
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from datetime import datetime, UTC
import os
import functions
import sys



load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///project_db.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

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
    functions.run()

    print("Vars:")
    print(default_resume_path)
    print(resume_text)
    print(analysis)
    print(career_paths)
    print(skill_keywords)


    
    return render_template('guidance.html', user_resume=user_resume)

@app.route('/start-interview')
def start_interview():
    if 'user_id' not in session:
        flash('Please log in.', 'error')
        return redirect(url_for('login'))
    user_resume = Resume.query.filter_by(user_id=session['user_id']).first()
    resume_path = user_resume.resume_path
    if not resume_path:
        flash('Please upload a resume first.', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('interview.html', user_resume=user_resume)


if __name__ == '__main__':
    app.run(debug=True)
