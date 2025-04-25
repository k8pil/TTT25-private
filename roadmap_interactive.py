"""
Enhanced implementation of the roadmap interactive feature for the career advisor.
This provides a more sophisticated prompt handling after showing a career roadmap.
"""


def handle_roadmap_interactive(career_path, roadmap, use_speech=False, speak_function=None):
    """
    Handle interactive prompts about a specific career roadmap with enhanced capabilities

    Args:
        career_path: Dictionary containing career path details
        roadmap: Dictionary containing roadmap details
        use_speech: Boolean indicating if speech is enabled
        speak_function: Function to use for speech output
    """
    print("\nYou can now ask specific questions about this career path. Type 'back' to return to the main menu.")

    # If no speak function is provided, create a simple one
    if speak_function is None:
        def speak_function(text):
            if use_speech:
                print(f"[Speaking]: {text}")

    # Define enhanced keyword sets for better question detection
    salary_keywords = ["salary", "pay", "money", "compensation",
                       "earn", "income", "wage", "payment", "remuneration", "benefits"]
    skills_keywords = ["skill", "skills", "learn", "require", "need",
                       "competency", "ability", "expertise", "proficiency", "capability"]
    time_keywords = ["time", "long", "years", "month", "duration",
                     "timeline", "period", "schedule", "roadmap", "plan"]
    growth_keywords = ["growth", "future", "potential", "prospect", "advance",
                       "promotion", "career", "progression", "opportunities", "advancement"]
    trend_keywords = ["trend", "industry", "emerging", "technology",
                      "tech", "current", "future", "evolving", "cutting-edge", "innovation"]
    education_keywords = ["certif", "qualif", "degree", "education",
                          "diploma", "training", "course", "learning", "study", "academic"]
    project_keywords = ["project", "portfolio", "showcase", "demonstrate",
                        "example", "work", "sample", "build", "create", "develop"]
    interview_keywords = ["interview", "question", "ask", "hiring",
                          "recruiter", "hr", "prepare", "common", "respond", "answer"]
    remote_keywords = ["remote", "work from home", "wfh", "telecommute",
                       "virtual", "online", "distance", "location", "flexibility", "hybrid"]

    # Advanced industry trends data
    industry_trends = {
        "Data Scientist": [
            "• Increased focus on ethical AI and responsible data usage",
            "• Growing demand for real-time analytics and stream processing",
            "• AutoML tools enabling wider adoption of machine learning",
            "• Integration of AI with IoT and edge computing",
            "• Rise of explainable AI (XAI) for transparency in models",
            "• Specialization in domain-specific data science applications",
            "• Growing importance of causal inference beyond correlation"
        ],
        "Software Engineer": [
            "• Shift towards microservices and serverless architectures",
            "• Adoption of containerization and Kubernetes for orchestration",
            "• Growing importance of DevSecOps practices",
            "• Increased use of low-code/no-code platforms",
            "• WebAssembly enabling new web application capabilities",
            "• Growing adoption of AI-assisted coding tools",
            "• Rise of event-driven and reactive programming paradigms"
        ],
        "UX/UI Designer": [
            "• Dark mode and adaptive interfaces becoming standard",
            "• Voice user interfaces and conversational UI",
            "• AR/VR experiences entering mainstream applications",
            "• Greater focus on accessibility and inclusive design",
            "• Design systems becoming essential for scalable teams",
            "• User research increasingly data-driven",
            "• Micro-interactions enhancing user engagement"
        ],
        "Product Manager": [
            "• Increased adoption of data-driven decision making",
            "• Remote-first product development processes",
            "• Integration of AI in product feature development",
            "• Focus on privacy-centric product design",
            "• Growing importance of product-led growth strategies",
            "• Rise of continuous discovery practices",
            "• Enhanced collaboration between product and engineering"
        ],
        "DevOps Engineer": [
            "• GitOps for infrastructure and deployment automation",
            "• Platform engineering and internal developer platforms",
            "• FinOps for cloud cost optimization",
            "• Increased emphasis on observability beyond monitoring",
            "• Security shifting further left in the development process",
            "• Infrastructure as Code (IaC) becoming standard practice",
            "• Growing adoption of service mesh architectures"
        ],
        "Cloud Architect": [
            "• Multi-cloud and hybrid cloud strategies",
            "• Serverless computing for cost optimization",
            "• Zero-trust security models becoming standard",
            "• Edge computing complementing centralized cloud",
            "• FinOps practices for cloud cost management",
            "• Automated cloud governance and compliance tools",
            "• Containerization of legacy applications"
        ],
        "Data Engineer": [
            "• Real-time data processing pipelines",
            "• Data mesh architectures for decentralization",
            "• Rise of data lakehouse architectures",
            "• Automated data quality and validation",
            "• Streaming data processing becoming mainstream",
            "• Growing focus on data governance and lineage",
            "• Python increasingly replacing legacy ETL tools"
        ],
        "Cybersecurity Specialist": [
            "• Zero-trust architecture implementation",
            "• Cloud security posture management",
            "• Automated security testing in CI/CD pipelines",
            "• AI-based threat detection and response",
            "• Growing focus on securing remote work environments",
            "• Rising importance of supply chain security",
            "• Increased adoption of security as code practices"
        ]
    }

    # Common interview questions by role
    interview_questions = {
        "Data Scientist": [
            "• How would you explain a complex statistical concept to a non-technical stakeholder?",
            "• How do you approach feature selection in your models?",
            "• Describe a time you had to work with messy, incomplete data",
            "• How do you evaluate model performance?",
            "• How do you stay current with the latest developments in data science?"
        ],
        "Software Engineer": [
            "• How do you approach debugging a complex issue?",
            "• Describe your experience with code reviews and process improvement",
            "• How do you ensure your code is maintainable and scalable?",
            "• How do you handle technical debt?",
            "• Explain how you've implemented testing in your projects"
        ],
        "UX/UI Designer": [
            "• Walk me through your design process",
            "• How do you incorporate user feedback into your designs?",
            "• How do you balance user needs with business objectives?",
            "• Describe a time when you had to defend a design decision",
            "• How do you approach designing for accessibility?"
        ],
        "Product Manager": [
            "• How do you prioritize features on your roadmap?",
            "• How do you gather and incorporate user feedback?",
            "• Describe how you work with engineering teams",
            "• How do you measure product success?",
            "• Tell me about a time you had to make a difficult product decision"
        ],
        "DevOps Engineer": [
            "• Describe your experience with CI/CD pipelines",
            "• How do you approach monitoring and alerting?",
            "• How have you implemented security in your DevOps processes?",
            "• Describe a challenging infrastructure problem you solved",
            "• How do you balance stability with the need for rapid deployments?"
        ]
    }

    # Remote work advice by role
    remote_work_advice = {
        "Data Scientist": [
            "• Set up a powerful local development environment for data processing",
            "• Leverage cloud computing resources for intensive modeling tasks",
            "• Use collaborative notebooks (like Google Colab or Deepnote) for sharing work",
            "• Schedule regular check-ins with stakeholders to ensure alignment",
            "• Build visualizations that can be easily shared and interpreted asynchronously"
        ],
        "Software Engineer": [
            "• Establish clear documentation practices for asynchronous work",
            "• Use feature flags for safer remote deployments",
            "• Set up proper testing environments accessible remotely",
            "• Adopt pair programming tools for collaborative coding sessions",
            "• Create clear status updates for asynchronous team communication"
        ],
        "UX/UI Designer": [
            "• Set up a robust design system for consistent remote collaboration",
            "• Use tools like Figma for real-time collaborative design",
            "• Establish clear processes for design reviews and feedback",
            "• Schedule regular user testing sessions with video recording",
            "• Create clear design handoff documentation for development teams"
        ],
        "Product Manager": [
            "• Create and maintain comprehensive, accessible roadmaps",
            "• Establish clear async communication channels for stakeholders",
            "• Use tools that allow for collaborative prioritization",
            "• Schedule regular but focused check-ins with team members",
            "• Develop dashboards for tracking product metrics remotely"
        ],
        "DevOps Engineer": [
            "• Ensure monitoring systems are accessible from anywhere",
            "• Document incident response procedures for distributed teams",
            "• Implement secure remote access to infrastructure",
            "• Automate as many routine tasks as possible",
            "• Set up clear on-call processes and rotation for distributed teams"
        ]
    }

    while True:
        custom_prompt = input("\nYour question > ").strip()

        if custom_prompt.lower() == 'back':
            break

        if not custom_prompt.strip():
            print(
                "Please ask a specific question about this career path or type 'back' to return.")
            continue

        # Process the custom prompt
        print(
            f"\nAnswering your question about the {career_path['title']} career path:")
        if use_speech:
            speak_function(
                f"Answering your question about the {career_path['title']} career path:")

        # Extract keywords from the prompt
        keywords = custom_prompt.lower().split()

        # Enhanced keyword matching with more comprehensive responses
        if any(word in keywords for word in salary_keywords):
            answer = f"The typical salary range for a {career_path['title']} is {career_path['salary_range']} depending on location, experience, and company size."
            additional_info = "Entry-level positions typically start at the lower end of this range, while senior roles with 5+ years of experience can exceed the upper range. Specialized skills or leadership responsibilities can also command higher compensation."
            print(answer)
            print(additional_info)
            if use_speech:
                speak_function(answer)
                speak_function(additional_info)

        elif any(word in keywords for word in skills_keywords):
            answer = f"The key skills needed for a {career_path['title']} position are:"
            print(answer)
            if use_speech:
                speak_function(answer)
            for skill in career_path['skills_needed']:
                print(f"• {skill}")
                if use_speech:
                    speak_function(f"• {skill}")

            # Additional context about skills
            additional_info = f"\nFor a {career_path['title']} role, it's recommended to focus on both technical and soft skills. Technical skills demonstrate your capabilities, while soft skills like communication and teamwork are equally important for career advancement."
            print(additional_info)
            if use_speech:
                speak_function(additional_info)

        elif any(word in keywords for word in time_keywords):
            answer = f"For a {career_path['title']} career path:"
            print(answer)
            if use_speech:
                speak_function(answer)
            for step in roadmap['steps']:
                print(f"• {step['timeframe']}: {step['focus']}")
                if use_speech:
                    speak_function(f"• {step['timeframe']}: {step['focus']}")

            # Additional context about timeline
            additional_info = f"\nThis timeline can vary based on your prior experience, learning capacity, and dedication. Some individuals progress faster with intensive learning and practical applications, while others prefer a more measured approach."
            print(additional_info)
            if use_speech:
                speak_function(additional_info)

        elif any(word in keywords for word in growth_keywords):
            answer = f"The {career_path['title']} position has {career_path['growth_potential']} growth potential in the current job market."
            print(answer)
            if use_speech:
                speak_function(answer)

            # Additional context about career growth
            additional_info = f"\nTypical career progression for a {career_path['title']} includes:"
            print(additional_info)
            if use_speech:
                speak_function(additional_info)

            progression_paths = {
                "Data Scientist": [
                    "• Junior Data Scientist → Data Scientist → Senior Data Scientist",
                    "• Potential specialization in ML Engineering, AI Research, or Data Leadership",
                    "• Possible paths to Data Science Manager, Director of Analytics, or Chief Data Officer"
                ],
                "Software Engineer": [
                    "• Junior Developer → Software Engineer → Senior Software Engineer",
                    "• Potential paths to Lead Developer, Software Architect, or Engineering Manager",
                    "• Can branch into DevOps, SRE, or specialized domains"
                ],
                "UX/UI Designer": [
                    "• Junior Designer → UX/UI Designer → Senior Designer",
                    "• Potential paths to Lead Designer, UX Manager, or Design Director",
                    "• Can specialize in Research, Interaction Design, or Product Design"
                ],
                "Product Manager": [
                    "• Associate PM → Product Manager → Senior PM",
                    "• Potential paths to Director of Product, VP of Product, or CPO",
                    "• Can specialize in specific product areas or move to strategic roles"
                ],
                "DevOps Engineer": [
                    "• Junior DevOps → DevOps Engineer → Senior DevOps Engineer",
                    "• Potential paths to DevOps Lead, Infrastructure Architect, or SRE Manager",
                    "• Can specialize in Cloud Architecture, Platform Engineering, or Technical Operations Director"
                ]
            }

            if career_path['title'] in progression_paths:
                for path in progression_paths[career_path['title']]:
                    print(path)
                    if use_speech:
                        speak_function(path)
            else:
                general_progression = [
                    "• Junior/Associate level → Mid-level → Senior level",
                    "• Potential paths to leadership, management, or specialized expert roles",
                    "• Opportunities to move into adjacent fields or entrepreneurship"
                ]
                for path in general_progression:
                    print(path)
                    if use_speech:
                        speak_function(path)

        elif any(word in keywords for word in trend_keywords):
            answer = f"Current industry trends for {career_path['title']} roles:"
            print(answer)
            if use_speech:
                speak_function(answer)

            if career_path['title'] in industry_trends:
                for trend in industry_trends[career_path['title']]:
                    print(trend)
                    if use_speech:
                        speak_function(trend)
            else:
                general_trends = [
                    "• Remote and hybrid work environments becoming permanent",
                    "• Increased emphasis on cybersecurity across all roles",
                    "• Growing importance of soft skills alongside technical expertise",
                    "• Continuous learning becoming essential for career longevity",
                    "• Increasing adoption of AI and automation tools across industries",
                    "• Greater focus on cross-functional collaboration",
                    "• Rising importance of data literacy in all tech roles"
                ]
                for trend in general_trends:
                    print(trend)
                    if use_speech:
                        speak_function(trend)

        elif any(word in keywords for word in education_keywords):
            answer = f"Recommended certifications and education for a {career_path['title']}:"
            print(answer)
            if use_speech:
                speak_function(answer)

            cert_recommendations = {
                "Data Scientist": [
                    "• AWS Certified Data Analytics or Google Professional Data Engineer",
                    "• IBM Data Science Professional Certificate",
                    "• Microsoft Certified: Azure Data Scientist Associate",
                    "• Specialized courses in ML, NLP, or Computer Vision",
                    "• Advanced degree in Data Science, Statistics, or related field (beneficial but not always required)"
                ],
                "Software Engineer": [
                    "• AWS Certified Developer or Microsoft Azure Developer",
                    "• Oracle Certified Professional Java SE Programmer",
                    "• Certified Kubernetes Administrator (CKA)",
                    "• Language-specific certifications (e.g., Python, JavaScript)",
                    "• Computer Science degree is beneficial but hands-on experience often matters more"
                ],
                "UX/UI Designer": [
                    "• Google UX Design Certificate",
                    "• Adobe Certified Expert in XD or Figma certification",
                    "• Interaction Design Foundation Certifications",
                    "• Nielsen Norman Group UX Certification",
                    "• Degrees in Design, HCI, or Psychology are beneficial but portfolios are often more important"
                ],
                "Product Manager": [
                    "• Professional Scrum Product Owner (PSPO)",
                    "• Certified Product Manager (AIPMM)",
                    "• Product School Certifications (PSC, PMC)",
                    "• Agile Certified Product Manager",
                    "• Business or technical background with product management training often preferred"
                ],
                "DevOps Engineer": [
                    "• AWS Certified DevOps Engineer Professional",
                    "• Docker Certified Associate",
                    "• Kubernetes Certified Administrator (CKA)",
                    "• Red Hat Certified Engineer (RHCE)",
                    "• Technical degree with DevOps experience often valued more than specific certifications"
                ]
            }

            if career_path['title'] in cert_recommendations:
                for cert in cert_recommendations[career_path['title']]:
                    print(cert)
                    if use_speech:
                        speak_function(cert)
            else:
                general_certs = [
                    "• Industry-specific certifications relevant to your field",
                    "• Project management certifications (e.g., PMP, CAPM)",
                    "• Cloud platform certifications (AWS, Azure, GCP)",
                    "• Agile and Scrum certifications",
                    "• Specialized technical training in relevant technologies"
                ]
                for cert in general_certs:
                    print(cert)
                    if use_speech:
                        speak_function(cert)

        elif any(word in keywords for word in project_keywords):
            answer = f"Project ideas to build your portfolio for a {career_path['title']} role:"
            print(answer)
            if use_speech:
                speak_function(answer)

            project_ideas = {
                "Data Scientist": [
                    "• Predictive model using public datasets with full documentation",
                    "• Interactive data visualization dashboard",
                    "• Natural language processing application (e.g., sentiment analyzer)",
                    "• Recommendation system implementation",
                    "• End-to-end machine learning pipeline with deployment",
                    "• Time series forecasting project with business applications"
                ],
                "Software Engineer": [
                    "• Full-stack web application with modern frameworks",
                    "• Mobile app with backend integration",
                    "• RESTful or GraphQL API service with documentation",
                    "• Command-line tool solving a specific problem",
                    "• Microservices project with containerization",
                    "• Open source contributions to established projects"
                ],
                "UX/UI Designer": [
                    "• Redesign of a popular app with detailed process documentation",
                    "• Design system with component library",
                    "• User research case study with methodology and findings",
                    "• Interactive prototype with user testing results",
                    "• Accessibility-focused design project",
                    "• Mobile app design with responsive considerations"
                ],
                "Product Manager": [
                    "• Detailed product requirement document (PRD) for a product",
                    "• Product roadmap with prioritization framework",
                    "• Market analysis report for a specific product category",
                    "• User persona development with research methodology",
                    "• Case study of a product launch or improvement",
                    "• Competitive analysis with actionable insights"
                ],
                "DevOps Engineer": [
                    "• CI/CD pipeline implementation for a sample application",
                    "• Infrastructure as code project using Terraform or similar",
                    "• Container orchestration solution with Kubernetes",
                    "• Monitoring and alerting system implementation",
                    "• Automated security scanning integration",
                    "• Disaster recovery plan and implementation"
                ]
            }

            if career_path['title'] in project_ideas:
                for idea in project_ideas[career_path['title']]:
                    print(idea)
                    if use_speech:
                        speak_function(idea)
            else:
                general_ideas = [
                    "• Open source contributions demonstrating your skills",
                    "• Personal project showcasing your core technical abilities",
                    "• Documentation of technical processes or solutions",
                    "• Sample work demonstrating problem-solving approach",
                    "• Projects showing collaboration and teamwork",
                    "• Case studies of challenges you've overcome"
                ]
                for idea in general_ideas:
                    print(idea)
                    if use_speech:
                        speak_function(idea)

        elif any(word in keywords for word in interview_keywords):
            answer = f"Common interview questions for {career_path['title']} positions:"
            print(answer)
            if use_speech:
                speak_function(answer)

            if career_path['title'] in interview_questions:
                for question in interview_questions[career_path['title']]:
                    print(question)
                    if use_speech:
                        speak_function(question)
            else:
                general_questions = [
                    "• Tell me about your background and experience in this field",
                    "• Describe a challenging project you worked on and how you approached it",
                    "• How do you stay current with developments in your field?",
                    "• Give an example of how you've handled a conflict with a team member",
                    "• What are your career goals and how does this position fit in?"
                ]
                for question in general_questions:
                    print(question)
                    if use_speech:
                        speak_function(question)

            additional_info = "\nWhen preparing for interviews, research the company thoroughly, practice your responses to common questions, prepare thoughtful questions to ask, and be ready to discuss your projects in detail."
            print(additional_info)
            if use_speech:
                speak_function(additional_info)

        elif any(word in keywords for word in remote_keywords):
            answer = f"Tips for remote work as a {career_path['title']}:"
            print(answer)
            if use_speech:
                speak_function(answer)

            if career_path['title'] in remote_work_advice:
                for tip in remote_work_advice[career_path['title']]:
                    print(tip)
                    if use_speech:
                        speak_function(tip)
            else:
                general_remote_tips = [
                    "• Establish a dedicated workspace with proper ergonomics",
                    "• Maintain a consistent schedule with clear boundaries",
                    "• Use collaboration tools effectively for communication",
                    "• Document your work thoroughly for asynchronous teams",
                    "• Schedule regular check-ins with teammates and managers"
                ]
                for tip in general_remote_tips:
                    print(tip)
                    if use_speech:
                        speak_function(tip)

        # Handle questions about alternatives or not wanting this career path
        elif any(word in custom_prompt.lower() for word in ["alternative", "alternatives", "other", "different", "instead"]) or \
                "not" in custom_prompt.lower() and any(word in custom_prompt.lower() for word in ["want", "like", "interested", "pursue", "follow"]):

            answer = f"If you're looking for alternatives to becoming a {career_path['title']}, here are some related career paths you might consider:"
            print(answer)
            if use_speech:
                speak_function(answer)

            # Define related alternative careers for each path
            alternative_careers = {
                "Data Scientist": [
                    "• Data Analyst - Less focus on advanced ML, more on business analytics",
                    "• Data Engineer - Focus on building data infrastructure rather than analysis",
                    "• Business Intelligence Analyst - More emphasis on dashboards and reporting",
                    "• Machine Learning Engineer - More software engineering, less statistical analysis",
                    "• Quantitative Analyst - Applying data science in finance specifically"
                ],
                "Software Engineer": [
                    "• DevOps Engineer - Focus on deployment and infrastructure",
                    "• QA/Test Engineer - Specialize in software quality and testing",
                    "• Technical Product Manager - Technical background with product focus",
                    "• Solutions Architect - Design systems rather than implementing code",
                    "• Technical Writer - Document software for users and developers"
                ],
                "UX/UI Designer": [
                    "• Graphic Designer - Focus on visual design without the UX research",
                    "• UX Researcher - Specialize in user research without the UI design component",
                    "• Product Designer - Broader product thinking with design elements",
                    "• Content Designer - Focus on the content strategy and writing",
                    "• Web Developer - Implement designs rather than creating them"
                ],
                "Product Manager": [
                    "• Project Manager - Focus on execution rather than product strategy",
                    "• Business Analyst - More analysis, less product ownership",
                    "• Marketing Manager - Focus on promotion rather than development",
                    "• Technical Program Manager - More technical coordination of complex projects",
                    "• Customer Success Manager - Work with customers after product release"
                ],
                "DevOps Engineer": [
                    "• Site Reliability Engineer - More focus on system reliability and performance",
                    "• System Administrator - Traditional IT infrastructure management",
                    "• Cloud Architect - Design cloud systems rather than day-to-day operations",
                    "• Security Engineer - Focus specifically on security aspects",
                    "• Database Administrator - Specialize in database systems"
                ]
            }

            # Display alternatives based on the current career path
            if career_path['title'] in alternative_careers:
                for alt in alternative_careers[career_path['title']]:
                    print(alt)
                    if use_speech:
                        speak_function(alt)
            else:
                # General alternatives for any career
                general_alternatives = [
                    "• Consider related roles that use similar skills but with different focus areas",
                    "• Look into adjacent fields that might better match your interests",
                    "• Explore specialized niches within the broader industry",
                    "• Consider consulting or freelancing for more variety",
                    "• Look into teaching or mentoring roles in your area of expertise"
                ]
                for alt in general_alternatives:
                    print(alt)
                    if use_speech:
                        speak_function(alt)

            additional_advice = "\nWhen considering alternative careers, assess which aspects of the original path appeal to you and which don't. This can help you find a better fit that leverages your existing skills and interests."
            print(additional_advice)
            if use_speech:
                speak_function(additional_advice)

        else:
            # For any other question, provide a general response based on the roadmap
            answer = f"To succeed as a {career_path['title']}, focus on building the core skills mentioned in the roadmap and follow the progression timeline. Network with professionals in the field, keep learning, and build practical projects to demonstrate your abilities."
            print(answer)
            if use_speech:
                speak_function(answer)

            additional_tip = f"\nFor more specific information about the {career_path['title']} role, try asking about salary, skills, timeline, growth potential, industry trends, certifications, project ideas, interview questions, or remote work tips."
            print(additional_tip)
            if use_speech:
                speak_function(additional_tip)


# Example usage - this will run if the script is executed directly
if __name__ == "__main__":
    # Sample career path
    sample_path = {
        "title": "Data Scientist",
        "description": "Use data to solve complex problems and provide insights.",
        "skills_needed": ["Python", "R", "Statistics", "Machine Learning", "Data Visualization", "SQL", "Big Data Tools"],
        "growth_potential": "High",
        "salary_range": "$90,000 - $150,000"
    }

    # Sample roadmap
    sample_roadmap = {
        "title": "Career Roadmap for Data Scientist",
        "overview": "This roadmap will help you become a successful Data Scientist based on your current skills and experience.",
        "steps": [
            {
                "timeframe": "0-6 months",
                "focus": "Building foundation",
                "tasks": ["Learn Python", "Learn Statistics fundamentals", "Complete an online course", "Build a portfolio project"]
            },
            {
                "timeframe": "6-12 months",
                "focus": "Gaining practical experience",
                "tasks": ["Master Machine Learning algorithms", "Contribute to open-source projects", "Network with professionals", "Apply for entry-level positions"]
            },
            {
                "timeframe": "1-2 years",
                "focus": "Specializing and growing",
                "tasks": ["Develop expertise in a specific domain", "Learn advanced techniques", "Take on increasingly complex projects", "Build your professional brand"]
            }
        ],
        "additional_resources": [
            "Online learning platforms: Coursera, Udemy, edX",
            "Professional certifications in data science",
            "Industry conferences and meetups",
            "Communities like Kaggle and GitHub for practice"
        ]
    }

    # Display the roadmap
    print(f"\n{sample_roadmap['title']}")
    print(f"\n{sample_roadmap['overview']}")

    for step in sample_roadmap['steps']:
        print(f"\n{step['timeframe']} - {step['focus']}:")
        for task in step['tasks']:
            print(f"• {task}")

    print("\nAdditional Resources:")
    for resource in sample_roadmap['additional_resources']:
        print(f"• {resource}")

    # Simple speak function for demonstration
    def simple_speak(text):
        print(f"[Speaking]: {text}")

    # Start interactive mode
    handle_roadmap_interactive(
        career_path=sample_path,
        roadmap=sample_roadmap,
        use_speech=True,
        speak_function=simple_speak
    )
