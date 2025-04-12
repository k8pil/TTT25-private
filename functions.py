import os
import random
import pytesseract
from PIL import Image
import fitz
from roadmap_interactive import handle_roadmap_interactive

HAS_ROADMAP_INTERACTIVE = True
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


default_resume_path = ""
resume_text = ""
analysis = {}
career_paths = []
skill_keywords = []

skills = []
education = []
experience = []


def initialize(a,b,c,d,e):
    global default_resume_path
    global resume_text
    global analysis
    global career_paths
    global skill_keywords

    default_resume_path = a
    resume_text = b
    analysis = c
    career_paths = d
    skill_keywords = e

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
    
    return True

def get_matching_career_paths(limit=3):

    global skills
    global education
    global experience
    global analysis

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
    for path, score in scored_paths[:limit]:
        match_percentage = min(95, max(60, score))  # Limit percentage between 60% and 95%
        path_copy = path.copy()
        path_copy["match_score"] = match_percentage
        results.append(path_copy)
    
    return results

def generate_roadmap(career_path):

    global skills
    global education
    global experience

    """Generate a career roadmap for the selected path"""
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

    resume_path = default_resume_path
    if not os.path.exists(resume_path):
        print(f"\nDefault resume file not found at: {resume_path}")
        print("Please update the default_resume_path in the code.")
        return
        
    message = "\nAnalyzing your resume... This may take a moment."
    print(message)
    success = analyze_resume(resume_path)
    
    if not success:
        print("Failed to analyze resume. Please check the file format.")
        return
    
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
        return
    
    message = "\nBased on your skills and experience, here are the top career paths for you:"
    print(message)
    
    for i, path in enumerate(career_paths, 1):
        path_info = f"\n{i}. {path['title']} (Match: {path['match_score']}%)"
        print(path_info)
        
        description = f"   Description: {path['description']}"
        print(description)
        
        skills = f"   Skills needed: {', '.join(path['skills_needed'])}"
        print(skills)
        
        growth = f"   Growth potential: {path['growth_potential']}"
        print(growth)
        
        salary = f"   Salary range: {path['salary_range']}"
        print(salary)
        print() # Add space between options
    
    while True:
        print("\nWhat would you like to do next?")
        print("1. Get a detailed roadmap for one of the career paths")
        print("2. Ask a question about a career path")
        print("3. Analyze a different resume")
        print("4. Resume improvement tips")
        print("5. Exit")
        
        choice = input("> ").strip()
        
        if choice == '1':
            print(f"\nWhich career path would you like a roadmap for? (1-{len(career_paths)})")
            path_choice = input("> ").strip()
            
            try:
                path_index = int(path_choice) - 1
                if 0 <= path_index < len(career_paths):
                    selected_path = career_paths[path_index]
                    roadmap = generate_roadmap(selected_path)
                    
                    print(f"\n{roadmap['title']}")
                    print(f"\n{roadmap['overview']}")
                    
                    for step in roadmap['steps']:
                        step_header = f"\n{step['timeframe']} - {step['focus']}:"
                        print(step_header)
                        for task in step['tasks']:
                            print(f"• {task}")
                    
                    print("\nAdditional Resources:")
                    for resource in roadmap['additional_resources']:
                        print(f"• {resource}")
                            
                    # Add custom prompt interaction after showing roadmap
                    print("\nYou can now ask specific questions about this career path. Type 'back' to return to the main menu.")
                    
                    # Use the imported handle_roadmap_interactive function if available
                    if HAS_ROADMAP_INTERACTIVE:
                        handle_roadmap_interactive(
                            career_path=selected_path,
                            roadmap=roadmap,
                            use_speech=False, 
                            speak_function=lambda x: print(x)
                        )
                    else:
                        # Fall back to the built-in custom prompt handling
                        while True:
                            custom_prompt = input("\nYour question > ").strip()
                            
                            if custom_prompt.lower() == 'back':
                                break
                            
                            # Process the custom prompt
                            print(f"\nAnswering your question about the {selected_path['title']} career path:")
                            
                            # Extract keywords from the prompt
                            keywords = custom_prompt.lower().split()
                            
                            # Handle different types of questions
                            if any(word in keywords for word in ["salary", "pay", "money", "compensation", "earn"]):
                                answer = f"The typical salary range for a {selected_path['title']} is {selected_path['salary_range']} depending on location, experience, and company size."
                                print(answer)
                            
                            elif any(word in keywords for word in ["skill", "skills", "learn", "require", "need"]):
                                answer = f"The key skills needed for a {selected_path['title']} position are:"
                                print(answer)
                                for skill in selected_path['skills_needed']:
                                    print(f"• {skill}")
                            
                            elif any(word in keywords for word in ["time", "long", "years", "month", "duration"]):
                                answer = f"For a {selected_path['title']} career path:"
                                print(answer)
                                for step in roadmap['steps']:
                                    print(f"• {step['timeframe']}: {step['focus']}")
                            
                            elif any(word in keywords for word in ["growth", "future", "potential", "prospect", "advance"]):
                                answer = f"The {selected_path['title']} position has {selected_path['growth_potential']} growth potential in the current job market."
                                print(answer)
                                
                            elif any(word in keywords for word in ["trend", "industry", "emerging", "technology", "tech", "current"]):
                                answer = f"Current industry trends for {selected_path['title']} roles:"
                                print(answer)
                                
                                industry_trends = {
                                    "Data Scientist": [
                                        "• Increased focus on ethical AI and responsible data usage",
                                        "• Growing demand for real-time analytics and stream processing", 
                                        "• AutoML tools enabling wider adoption of machine learning",
                                        "• Integration of AI with IoT and edge computing"
                                    ],
                                    "Software Engineer": [
                                        "• Shift towards microservices architecture",
                                        "• Adoption of serverless computing and cloud-native development",
                                        "• Growing importance of DevSecOps practices",
                                        "• Increased use of low-code/no-code platforms"
                                    ],
                                    "UX/UI Designer": [
                                        "• Dark mode and adaptive interfaces becoming standard",
                                        "• Voice user interfaces and conversational UI",
                                        "• AR/VR experiences entering mainstream applications",
                                        "• Greater focus on accessibility and inclusive design"
                                    ],
                                    "Product Manager": [
                                        "• Increased adoption of data-driven decision making",
                                        "• Remote-first product development processes",
                                        "• Integration of AI in product feature development",
                                        "• Focus on privacy-centric product design"
                                    ],
                                    "DevOps Engineer": [
                                        "• GitOps for infrastructure and deployment automation",
                                        "• Platform engineering and internal developer platforms",
                                        "• FinOps for cloud cost optimization",
                                        "• Increased emphasis on observability beyond monitoring"
                                    ]
                                }
                                
                                if selected_path['title'] in industry_trends:
                                    for trend in industry_trends[selected_path['title']]:
                                        print(trend)
                                else:
                                    general_trends = [
                                        "• Remote and hybrid work environments becoming permanent",
                                        "• Increased emphasis on cybersecurity across all roles",
                                        "• Growing importance of soft skills alongside technical expertise",
                                        "• Continuous learning becoming essential for career longevity"
                                    ]
                                    for trend in general_trends:
                                        print(trend)
                            
                            elif any(word in keywords for word in ["certif", "qualif", "degree", "education"]):
                                answer = f"Recommended certifications for a {selected_path['title']}:"
                                print(answer)
                                
                                cert_recommendations = {
                                    "Data Scientist": ["• AWS Certified Data Analytics", "• Google Professional Data Engineer", "• IBM Data Science Professional", "• Microsoft Certified: Azure Data Scientist"],
                                    "Software Engineer": ["• AWS Certified Developer", "• Microsoft Certified: Azure Developer", "• Oracle Certified Professional Java SE", "• Certified Kubernetes Administrator"],
                                    "UX/UI Designer": ["• Google UX Design Certificate", "• Adobe Certified Expert", "• Interaction Design Foundation Certification", "• Certified User Experience Professional"],
                                    "Product Manager": ["• Professional Scrum Product Owner", "• Certified Product Manager", "• Agile Certified Product Manager", "• Product Management Certificate (PMC)"],
                                    "DevOps Engineer": ["• AWS Certified DevOps Engineer", "• Docker Certified Associate", "• Kubernetes Certified Administrator", "• Red Hat Certified Engineer"]
                                }
                                
                                if selected_path['title'] in cert_recommendations:
                                    for cert in cert_recommendations[selected_path['title']]:
                                        print(cert)
                            
                            elif any(word in keywords for word in ["project", "portfolio", "showcase", "demonstrate"]):
                                answer = f"Project ideas to build your portfolio for a {selected_path['title']} role:"
                                print(answer)
                                
                                project_ideas = {
                                    "Data Scientist": ["• Predictive model using public datasets", "• Data visualization dashboard", "• Natural language processing application", "• Recommendation system"],
                                    "Software Engineer": ["• Full-stack web application", "• Mobile app with backend integration", "• API service with documentation", "• Command-line tool for developers"],
                                    "UX/UI Designer": ["• Redesign of popular app", "• Design system with components", "• User research case study", "• Interactive prototype with user testing"],
                                    "Product Manager": ["• Product requirement document (PRD)", "• Product roadmap", "• Market analysis report", "• User persona development"],
                                    "DevOps Engineer": ["• CI/CD pipeline implementation", "• Infrastructure as code project", "• Container orchestration solution", "• Monitoring and alerting system"]
                                }
                                
                                if selected_path['title'] in project_ideas:
                                    for idea in project_ideas[selected_path['title']]:
                                        print(idea)
                                else:
                                    general_ideas = ["• Open source contributions", "• Personal project showcasing core skills", "• Documentation of technical processes"]
                                    for idea in general_ideas:
                                        print(idea)
                            
                            else:
                                # For any other question, provide a general response based on the roadmap
                                answer = f"To succeed as a {selected_path['title']}, focus on building the core skills mentioned in the roadmap and follow the progression timeline. Network with professionals in the field, keep learning, and build practical projects to demonstrate your abilities."
                                print(answer)
            except ValueError:
                print("\nInvalid input. Please enter a number.")
        
        elif choice == '2':
            print("\nWhat question do you have about these career paths?")
            question = input("> ").strip()
            
            # Simple Q&A system
            keywords = question.lower().split()
            if any(word in keywords for word in ["salary", "pay", "money", "earning"]):
                answer = "Salary ranges vary by location, experience, and company size. Generally:"
                print(f"\n{answer}")
                for path in career_paths:
                    path_info = f"- {path['title']}: {path['salary_range']}"
                    print(path_info)
            
            elif any(word in keywords for word in ["skill", "skills", "learn", "require"]):
                answer = "Here are the key skills for each recommended career path:"
                print(f"\n{answer}")
                for path in career_paths:
                    path_info = f"- {path['title']}: {', '.join(path['skills_needed'])}"
                    print(path_info)
            
            elif any(word in keywords for word in ["time", "long", "years", "month"]):
                answer = "Career progression timeframes vary by individual, but generally:"
                print(f"\n{answer}")
                timeframes = [
                    "- Entry level: 0-2 years experience",
                    "- Mid-level: 2-5 years experience",
                    "- Senior level: 5+ years experience",
                    "- Leadership/Management: Often 7+ years experience"
                ]
                for timeframe in timeframes:
                    print(timeframe)
            
            elif any(word in keywords for word in ["growth", "future", "potential", "prospect"]):
                for path in career_paths:
                    growth_info = f"{path['title']} has {path['growth_potential']} growth potential with increasing demand for skilled professionals."
                    print(f"\n{growth_info}")
            
            else:
                answer = "For more specific information about any career path, I recommend:"
                print(f"\n{answer}")
                recommendations = [
                    "1. Researching industry reports and job market trends",
                    "2. Networking with professionals in your desired field",
                    "3. Looking at job postings to understand current requirements",
                    "4. Consulting with a career counselor for personalized advice"
                ]
                for rec in recommendations:
                    print(rec)
        
        elif choice == '3':
            break  # Go back to resume selection
        
        elif choice == '4':
            provide_resume_tips()
        
        elif choice == '5':
            print("\nThank you for using the Career Path Advisor. Goodbye!")
            return
        
        else:
            print("\nInvalid choice. Please try again.")

def provide_resume_tips():

    global skills
    global education
    global experience

    """Provides personalized resume improvement tips based on the analyzed resume"""
    print("\n===== RESUME IMPROVEMENT TIPS =====")
    
    # Check if resume was analyzed
    if not hasattr('resume_text') or not resume_text:
        print("Please analyze a resume first to get personalized tips.")
        return
    
    # General Structure and Formatting Tips
    print("\n1. Structure and Formatting:")
    structure_tips = [
        "• Use a clean, professional template with consistent formatting",
        "• Keep your resume to 1-2 pages maximum",
        "• Use bullet points instead of paragraphs for better readability",
        "• Include clear section headings (Experience, Education, Skills, etc.)",
        "• Use a professional font (Arial, Calibri, Times New Roman) at 10-12pt size"
    ]
    for tip in structure_tips:
        print(tip)
        
    # Content Recommendations based on analysis
    print("\n2. Content Improvements:")
    
    # Check if we have skills data
    if hasattr('analysis') and 'skills' in analysis and analysis['skills']:
        # Skills recommendations
        skill_count = len(analysis['skills'])
        
        if skill_count < 5:
            print("• Your resume would benefit from listing more relevant skills")
            print("• Consider adding both technical and soft skills specific to your target roles")
        elif skill_count > 15:
            print("• Consider focusing on your most relevant skills rather than listing too many")
            print("• Prioritize skills mentioned in job descriptions for your target roles")
        else:
            print("• You have a good number of skills listed, make sure they're aligned with your target roles")
        
        # Check if we have some common keywords
        tech_keywords = ["python", "java", "javascript", "data", "sql", "cloud", "aws", "azure"]
        soft_keywords = ["communication", "leadership", "teamwork", "problem solving"]
        
        user_skills_lower = [s.lower() for s in analysis['skills']]
        
        has_tech = any(tech in user_skills_lower for tech in tech_keywords)
        has_soft = any(soft in user_skills_lower for soft in soft_keywords)
        
        if not has_tech and not has_soft:
            print("• Consider adding both technical skills and soft skills to create a balanced profile")
        elif not has_soft:
            print("• Consider adding soft skills like communication, leadership, or problem-solving")
        elif not has_tech:
            print("• Consider highlighting more technical skills relevant to your field")
            
    else:
        print("• Make sure to clearly list your relevant skills in a dedicated section")
        print("• Include both technical skills and soft skills")
    
    # Experience content recommendations
    if hasattr('analysis') and 'experience' in analysis:
        exp_count = len(analysis['experience'])
        
        if exp_count == 0:
            print("• Your resume needs more detailed work experience")
            print("• Include internships, part-time work, or relevant projects if you're early in your career")
        else:
            print("• Quantify your achievements with specific metrics and results")
            print("• Use strong action verbs at the beginning of each bullet point")
            print("• Focus on accomplishments rather than just listing responsibilities")
    
    # Achievement emphasis
    print("\n3. Achievement Emphasis:")
    achievement_tips = [
        "• For each role, highlight 2-3 key achievements rather than just listing duties",
        "• Quantify results whenever possible (e.g., 'Increased sales by 20%' rather than 'Increased sales')",
        "• Use the CAR formula: Challenge, Action, Result for impactful bullet points",
        "• Highlight awards, recognitions, or successful projects"
    ]
    for tip in achievement_tips:
        print(tip)
    
    # Keyword optimization for ATS
    print("\n4. ATS Optimization:")
    ats_tips = [
        "• Include keywords from job descriptions for roles you're targeting",
        "• Use standard section headings that ATS systems can recognize",
        "• Avoid using tables, headers/footers, or complex formatting that ATS might not read properly",
        "• Submit in PDF format unless another format is specifically requested",
        "• Include a skills section that clearly lists relevant technologies and abilities"
    ]
    for tip in ats_tips:
        print(tip)
    
    # Modern resume practices
    print("\n5. Modern Resume Practices:")
    modern_tips = [
        "• Include a brief professional summary or objective at the top",
        "• Add a link to your LinkedIn profile and any relevant professional portfolios",
        "• For technical roles, include a link to your GitHub or other code repositories",
        "• Consider removing outdated information like 'References available upon request'",
        "• For many fields, traditional objectives are being replaced with professional summaries"
    ]
    for tip in modern_tips:
        print(tip)
    
    # Tailoring tips
    print("\n6. Tailoring Your Resume:")
    tailoring_tips = [
        "• Customize your resume for each job application",
        "• Match your skills and experiences to the specific job requirements",
        "• Research the company and incorporate relevant keywords and values",
        "• Highlight experiences most relevant to the target position",
        "• Consider having different versions of your resume for different types of roles"
    ]
    for tip in tailoring_tips:
        print(tip)
