import os
import random
import pytesseract
from PIL import Image
import fitz
from roadmap_interactive import handle_roadmap_interactive
import datetime
import sqlite3

HAS_ROADMAP_INTERACTIVE = True
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Database setup
def get_db_connection():
    # Use the same eye.sqlite database that the rest of the app uses
    instance_path = os.path.join(os.getcwd(), 'instance')
    os.makedirs(instance_path, exist_ok=True)
    db_path = os.path.join(instance_path, 'eye.sqlite')
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # This enables column access by name
    return conn

def initialize_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create resume_data table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS resume_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        resume_path TEXT NOT NULL,
        resume_text TEXT,
        skills TEXT,
        education TEXT,
        experience TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create career_paths table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS career_matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        resume_id INTEGER,
        career_path TEXT,
        match_score INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (resume_id) REFERENCES resume_data(id)
    )
    ''')
    
    conn.commit()
    conn.close()
    
    print("Resume database tables initialized in eye.sqlite")

# Call initialize_db when the module is imported
initialize_db()

default_resume_path = ""
resume_text = ""
analysis = {}
career_paths = []
skill_keywords = []

skills = []
education = []
experience = []
current_user_id = None

def initialize(a, b, c, d, e, user_id=None):
    global default_resume_path
    global resume_text
    global analysis
    global career_paths
    global skill_keywords
    global current_user_id

    default_resume_path = a
    resume_text = b
    analysis = c
    career_paths = d
    skill_keywords = e
    current_user_id = user_id

def extract_text_from_image(image_path):

    global resume_text
    global skills
    global education
    global experience
    global analysis
    global skill_keywords

    """Extract text from an image using OCR"""
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        print("Text: ", text)
        return text
    except Exception as e:
        print(f"Error extracting text from image: {e}")
        return ""

def extract_text_from_pdf(pdf_path):

    global resume_text
    """Extract text from a PDF file"""
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        
        # Fallback: Try to use OCR on the PDF pages
        try:
            doc = fitz.open(pdf_path)
            text = ""
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                pix = page.get_pixmap()
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                text += pytesseract.image_to_string(img)
            return text
        except Exception as e2:
            print(f"Fallback extraction failed: {e2}")
            return ""

def analyze_resume(resume_path):
    global resume_text
    global skills
    global education
    global experience
    global analysis
    global skill_keywords
    global current_user_id

    """Analyze the resume text to extract skills, education, and experience"""
    # Extract text based on file type
    if resume_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
        resume_text = extract_text_from_image(resume_path)
    elif resume_path.lower().endswith('.pdf'):
        resume_text = extract_text_from_pdf(resume_path)
    else:
        print("Unsupported file format. Please provide a PDF or image file.")
        return False
    
    if not resume_text.strip():
        print("Could not extract text from the resume. Please try another file.")
        return False
    
    # Simple extraction of skills, education, and experience
    skills = []
    for skill in skill_keywords:
        if skill in resume_text.lower():
            skills.append(skill.title())
    
    # Simple education extraction
    education = []
    edu_keywords = ["bachelor", "master", "phd", "doctorate", "degree", "diploma", "certificate"]
    lines = resume_text.split("\n")
    for line in lines:
        for keyword in edu_keywords:
            if keyword in line.lower() and len(line.split()) > 3:
                education.append(line.strip())
                break
    
    # Simple experience extraction
    experience = []
    exp_keywords = ["experience", "work", "job", "position", "role", "company", "employer"]
    in_exp_section = False
    exp_buffer = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check if this is an experience section header
        if any(keyword in line.lower() for keyword in exp_keywords) and len(line.split()) < 5:
            in_exp_section = True
            if exp_buffer:
                experience.append(" ".join(exp_buffer))
                exp_buffer = []
            continue
        
        # If we're in the experience section, collect lines
        if in_exp_section and len(line.split()) > 3:
            exp_buffer.append(line)
            
            # If buffer is getting too large, add it to experience
            if len(exp_buffer) > 5:
                experience.append(" ".join(exp_buffer))
                exp_buffer = []
    
    # Add any remaining buffer
    if exp_buffer:
        experience.append(" ".join(exp_buffer))
    
    # If no experience was found through sections, try to find role/company pairs
    if not experience:
        for i, line in enumerate(lines):
            if any(title in line.lower() for title in ["developer", "engineer", "manager", "analyst", "designer"]):
                if i < len(lines) - 1:
                    experience.append(f"{line.strip()} - {lines[i+1].strip()}")
    
    # Limit the number of items
    skills = list(set(skills))[:10]  # Remove duplicates and limit to 10
    education = list(set(education))[:3]  # Remove duplicates and limit to 3
    experience = experience[:3]  # Limit to 3 experiences
    
    analysis = {
        "skills": skills,
        "education": education,
        "experience": experience
    }
    
    # Save to database
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Convert lists to strings for database storage
        skills_str = "|".join(skills) if skills else ""
        education_str = "|".join(education) if education else ""
        experience_str = "|".join(experience) if experience else ""
        
        # Insert into resume_data table
        cursor.execute('''
        INSERT INTO resume_data (user_id, resume_path, resume_text, skills, education, experience)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (current_user_id, resume_path, resume_text, skills_str, education_str, experience_str))
        
        conn.commit()
        resume_id = cursor.lastrowid
        conn.close()
        
        print(f"Resume data saved to database with ID: {resume_id}")
    except Exception as e:
        print(f"Error saving resume data to database: {str(e)}")
    
    return True

def get_matching_career_paths(limit=3):
    global skills
    global education
    global experience
    global analysis
    global current_user_id

    """Get the most suitable career paths based on resume analysis"""
    if not analysis:
        return []
    
    scored_paths = []
    for path in career_paths:
        score = 0
        
        # Score based on skill matches
        for skill in analysis["skills"]:
            if skill.lower() in [s.lower() for s in path["skills_needed"]]:
                score += 10
            
            # Partial matches
            for needed_skill in path["skills_needed"]:
                if skill.lower() in needed_skill.lower() or needed_skill.lower() in skill.lower():
                    score += 5
        
        # Add some randomness to make it more interesting
        score += random.randint(0, 20)
        
        scored_paths.append((path, score))
    
    # Sort by score descending
    scored_paths.sort(key=lambda x: x[1], reverse=True)
    
    # Return the top matches with match percentage
    results = []
    
    # Get the latest resume ID from the database
    resume_id = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get the most recent resume for the current user
        cursor.execute('''
        SELECT id FROM resume_data 
        WHERE user_id = ? 
        ORDER BY created_at DESC LIMIT 1
        ''', (current_user_id,))
        
        row = cursor.fetchone()
        if row:
            resume_id = row[0]
        
        conn.close()
    except Exception as e:
        print(f"Error retrieving resume ID from database: {str(e)}")
    
    # Save matches to database
    for path, score in scored_paths[:limit]:
        match_percentage = min(95, max(60, score))  # Limit percentage between 60% and 95%
        path_copy = path.copy()
        path_copy["match_score"] = match_percentage
        results.append(path_copy)
        
        # Save to database if we have a resume_id
        if resume_id and current_user_id:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                # Insert career match
                cursor.execute('''
                INSERT INTO career_matches (user_id, resume_id, career_path, match_score)
                VALUES (?, ?, ?, ?)
                ''', (current_user_id, resume_id, path['title'], match_percentage))
                
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"Error saving career match to database: {str(e)}")
    
    return results

def generate_roadmap(career_path):

    global skills
    global education
    global experience
    global roadmap
    global career_paths

    """Generate a career roadmap for the selected path"""
    # If career_path is a string (path name), find the matching career path object
    if isinstance(career_path, str):
        # Check if it's a known career path
        matching_path = None
        for path in career_paths:
            if path["title"].lower() == career_path.lower():
                matching_path = path
                break
        
        # If no match found, create a generic roadmap
        if not matching_path:
            roadmap = {
                "title": f"Career Roadmap for {career_path}",
                "overview": f"This roadmap will help you become a successful {career_path} professional based on your current skills and experience.",
                "steps": [
                    {
                        "timeframe": "0-6 months",
                        "focus": "Building foundation",
                        "tasks": [
                            "Learn fundamental concepts and principles",
                            "Complete relevant online courses or certifications",
                            "Build small portfolio projects",
                            "Join professional communities"
                        ]
                    },
                    {
                        "timeframe": "6-12 months",
                        "focus": "Gaining practical experience",
                        "tasks": [
                            "Contribute to collaborative or open-source projects",
                            "Network with professionals in the field",
                            "Apply for entry-level positions or internships",
                            "Develop specialized skills"
                        ]
                    },
                    {
                        "timeframe": "1-2 years",
                        "focus": "Specialization and growth",
                        "tasks": [
                            "Specialize in a high-demand area of the field",
                            "Take on leadership roles in projects",
                            "Mentor juniors in your field",
                            "Seek a promotion or more advanced role"
                        ]
                    },
                    {
                        "timeframe": "3-5 years",
                        "focus": "Career advancement",
                        "tasks": [
                            "Become an expert in your specialized area",
                            "Build a personal brand through speaking, writing, or teaching",
                            "Consider management or technical leadership roles",
                            "Stay updated with industry trends and technologies"
                        ]
                    }
                ],
                "additional_resources": [
                    "Online learning platforms: Coursera, Udemy, edX",
                    "Professional certifications relevant to this field",
                    "Industry conferences and meetups",
                    "Books and blogs by industry leaders"
                ]
            }
            return roadmap
        
        # Use the matching path for roadmap generation
        career_path = matching_path

    # Original implementation for dictionary input
    roadmap = {
        "title": f"Career Roadmap for {career_path['title']}",
        "overview": f"This roadmap will help you become a successful {career_path['title']} based on your current skills and experience.",
        "steps": [
            {
                "timeframe": "0-6 months",
                "focus": "Building foundation",
                "tasks": [
                    f"Learn/improve {skill}" for skill in career_path["skills_needed"][:2]
                ] + [
                    "Complete an online course or certification",
                    "Build a portfolio project"
                ]
            },
            {
                "timeframe": "6-12 months",
                "focus": "Gaining practical experience",
                "tasks": [
                    f"Master {skill}" for skill in career_path["skills_needed"][2:4]
                ] + [
                    "Contribute to open-source projects",
                    "Network with professionals in the field",
                    "Apply for entry-level positions or internships"
                ]
            },
            {
                "timeframe": "1-2 years",
                "focus": "Specialization and growth",
                "tasks": [
                    "Specialize in a high-demand area of the field",
                    "Take on leadership roles in projects",
                    "Mentor juniors in your field",
                    "Seek a promotion or more advanced role"
                ]
            },
            {
                "timeframe": "3-5 years",
                "focus": "Career advancement",
                "tasks": [
                    "Become an expert in your specialized area",
                    "Build a personal brand through speaking, writing, or teaching",
                    "Consider management or technical leadership roles",
                    "Stay updated with industry trends and technologies"
                ]
            }
        ],
        "additional_resources": [
            "Online learning platforms: Coursera, Udemy, edX",
            "Professional certifications relevant to this field",
            "Industry conferences and meetups",
            "Books and blogs by industry leaders"
        ]
    }
    
    return roadmap

def run():
    global skills
    global education
    global experience
    global default_resume_path
    global analysis
    global current_user_id

    resume_path = default_resume_path
    if not os.path.exists(resume_path):
        print(f"\nDefault resume file not found at: {resume_path}")
        print("Please update the default_resume_path in the code.")
        return []
        
    message = "\nAnalyzing your resume... This may take a moment."
    print(message)
    
    # Check if we already have this resume analyzed in the database
    resume_already_analyzed = False
    
    if current_user_id:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check if we have an entry for this resume
            cursor.execute('''
            SELECT id, skills, education, experience 
            FROM resume_data 
            WHERE user_id = ? AND resume_path = ? 
            ORDER BY created_at DESC LIMIT 1
            ''', (current_user_id, resume_path))
            
            row = cursor.fetchone()
            if row:
                resume_already_analyzed = True
                # Load data from database
                resume_id = row[0]
                
                # Convert database strings back to lists
                skills = row[1].split('|') if row[1] else []
                education = row[2].split('|') if row[2] else []
                experience = row[3].split('|') if row[3] else []
                
                analysis = {
                    "skills": skills,
                    "education": education,
                    "experience": experience
                }
                
                print(f"\nLoaded resume analysis from database (ID: {resume_id})")
            
            conn.close()
        except Exception as e:
            print(f"Error checking database for existing resume: {str(e)}")
    
    # If not found in database, analyze the resume
    if not resume_already_analyzed:
        success = analyze_resume(resume_path)
        
        if not success:
            print("Failed to analyze resume. Please check the file format.")
            return []
    
    # Display the analysis
    message = "\nHere's what I found in your resume:"
    print(message)

    print(analysis)
    
    if analysis["skills"]:
        skill_text = ", ".join(analysis["skills"])
        message = f"\nSkills: {skill_text}"
        print(message)
    else:
        message = "\nI couldn't identify specific skills in your resume."
        print(message)
    
    if analysis["education"]:
        message = "\nEducation:"
        print(message)
        for edu in analysis["education"]:
            message = f"- {edu}"
            print(message)
    else:
        message = "\nI couldn't identify your education details."
        print(message)
    
    if analysis["experience"]:
        message = "\nExperience:"
        print(message)
        for exp in analysis["experience"]:
            message = f"- {exp}"
            print(message)
    else:
        message = "\nI couldn't identify your work experience details."
        print(message)
    
    # Get matching career paths
    career_paths = get_matching_career_paths()
    
    if not career_paths:
        message = "\nI couldn't determine suitable career paths based on your resume. Please try a different resume or add more details to your current one."
        print(message)
        return []
    
    message = "\nBased on your skills and experience, here are the top career paths for you:"
    print(message)
    
    career_paths_list = []
    for i, path in enumerate(career_paths, 1):
        item = []
        path_info = f"{path['title']} (Match: {path['match_score']}%)"
        item.append(path_info)
        
        description = f"Description: {path['description']}"
        item.append(description)
        
        skills = f"Skills needed: {', '.join(path['skills_needed'])}"
        item.append(skills)
        
        growth = f"Growth potential: {path['growth_potential']}"
        item.append(growth)
        
        salary = f"Salary range: {path['salary_range']}"
        item.append(salary)

        career_paths_list.append(item)
    
    return career_paths_list

def provide_resume_tips():

    global skills
    global education
    global experiencec

    """Provides personalized resume improvement tips based on the analyzed resume"""
    print("\n===== RESUME IMPROVEMENT TIPS =====")
    
    # Check if resume was analyzed
    if not resume_text:
        print("Please analyze a resume first to get personalized tips.")
    
    # General Structure and Formatting Tips
    print("\n1. Structure and Formatting:")
    structure_tips = [
        "Use a clean, professional template with consistent formatting",
        "Keep your resume to 1-2 pages maximum",
        "Use bullet points instead of paragraphs for better readability",
        "Include clear section headings (Experience, Education, Skills, etc.)",
        "Use a professional font (Arial, Calibri, Times New Roman) at 10-12pt size"
    ]
        
    # Content Recommendations based on analysis
    print("\n2. Content Improvements:")
    content_improvement_tips = []
    # Check if we have skills data
    if analysis['skills']:
        # Skills recommendations
        skill_count = len(analysis['skills'])
    
        if skill_count < 5:
            content_improvement_tips.append("Your resume would benefit from listing more relevant skills")
            content_improvement_tips.append("Consider adding both technical and soft skills specific to your target roles")
        elif skill_count > 15:
            content_improvement_tips.append("Consider focusing on your most relevant skills rather than listing too many")
            content_improvement_tips.append("Prioritize skills mentioned in job descriptions for your target roles")
        else:
            content_improvement_tips.append("You have a good number of skills listed, make sure they're aligned with your target roles")
        
        # Check if we have some common keywords
        tech_keywords = ["python", "java", "javascript", "data", "sql", "cloud", "aws", "azure"]
        soft_keywords = ["communication", "leadership", "teamwork", "problem solving"]
        
        user_skills_lower = [s.lower() for s in analysis['skills']]
        
        has_tech = any(tech in user_skills_lower for tech in tech_keywords)
        has_soft = any(soft in user_skills_lower for soft in soft_keywords)
        
        # balance between technical and soft skills
        tech_and_soft_skill_tips = []
        if not has_tech and not has_soft:
            tech_and_soft_skill_tips.append("Consider adding both technical skills and soft skills to create a balanced profile")
        elif not has_soft:
            tech_and_soft_skill_tips.append("Consider adding soft skills like communication, leadership, or problem-solving")
        elif not has_tech:
            tech_and_soft_skill_tips.append("Consider highlighting more technical skills relevant to your field")
            
    else:
        content_improvement_tips.append("Make sure to clearly list your relevant skills in a dedicated section")
        content_improvement_tips.append("Include both technical skills and soft skills")
    
    # Experience content recommendations
    if analysis['experience']:
        exp_count = len(analysis['experience'])
        
        experience_tips = []
        if exp_count == 0:
            experience_tips.append("Your resume needs more detailed work experience")
            experience_tips.append("Include internships, part-time work, or relevant projects if you're early in your career")
        else:
            experience_tips.append("Quantify your achievements with specific metrics and results")
            experience_tips.append("Use strong action verbs at the beginning of each bullet point")
            experience_tips.append("Focus on accomplishments rather than just listing responsibilities")
    
    # Achievement emphasis
    print("\n3. Achievement Emphasis:")
    achievement_tips = [
        "For each role, highlight 2-3 key achievements rather than just listing duties",
        "Quantify results whenever possible (e.g., 'Increased sales by 20%' rather than 'Increased sales')",
        "Use the CAR formula: Challenge, Action, Result for impactful bullet points",
        "Highlight awards, recognitions, or successful projects"
    ]
    
    # Keyword optimization for ATS
    print("\n4. ATS Optimization:")
    ats_tips = [
        "Include keywords from job descriptions for roles you're targeting",
        "Use standard section headings that ATS systems can recognize",
        "Avoid using tables, headers/footers, or complex formatting that ATS might not read properly",
        "Submit in PDF format unless another format is specifically requested",
        "Include a skills section that clearly lists relevant technologies and abilities"
    ]
    
    # Modern resume practices
    print("\n5. Modern Resume Practices:")
    modern_tips = [
        "Include a brief professional summary or objective at the top",
        "Add a link to your LinkedIn profile and any relevant professional portfolios",
        "For technical roles, include a link to your GitHub or other code repositories",
        "Consider removing outdated information like 'References available upon request'",
        "For many fields, traditional objectives are being replaced with professional summaries"
    ]
    
    # Tailoring tips
    print("\n6. Tailoring Your Resume:")
    tailoring_tips = [
        "Customize your resume for each job application",
        "Match your skills and experiences to the specific job requirements",
        "Research the company and incorporate relevant keywords and values",
        "Highlight experiences most relevant to the target position",
        "Consider having different versions of your resume for different types of roles"
    ]
    
    return structure_tips, content_improvement_tips, tech_and_soft_skill_tips, experience_tips, achievement_tips, ats_tips, modern_tips, tailoring_tips

def save_emotion(emotion, confidence=1.0, user_id=None):
    """Save emotion data to the eye.sqlite database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if emotions table exists, create if not
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS emotions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            emotion TEXT NOT NULL,
            confidence REAL DEFAULT 1.0
        )
        ''')
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO emotions (user_id, timestamp, emotion, confidence) VALUES (?, ?, ?, ?)",
            (user_id, timestamp, emotion, confidence)
        )
        conn.commit()
        emotion_id = cursor.lastrowid
        conn.close()
        
        print(f"Emotion data saved to database (ID: {emotion_id})")
        return True
    except Exception as e:
        print(f"Error saving emotion data: {str(e)}")
        return False

