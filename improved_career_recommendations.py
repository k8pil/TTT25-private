"""
Improved Career Recommendation System

This module provides enhanced career recommendation functionality
while maintaining the same UI layout and field structure.
"""

import os
import json
import re
from typing import Dict, List, Any, Optional

# Assuming you have a Google AI client set up in your main application
# If using a different AI service, you'll need to modify this

def parse_llm_career_recommendations(llm_response: str) -> List[Dict[str, Any]]:
    """
    Parse the LLM response text into structured career recommendations.
    Handles variations in formatting more robustly.
    
    Args:
        llm_response: Raw text response from the LLM
        
    Returns:
        List of dictionaries containing structured career recommendations
    """
    recommendations = []
    
    # Split the response into potential recommendation blocks based on the title pattern
    # Use regex to find the start of each recommendation block
    # Look for "Role Title (Match: X%)"
    pattern = r"^\s*(.*?)\s*\(Match:\s*(\d+)%\)"
    
    # Find all matches which mark the start of a recommendation
    matches = list(re.finditer(pattern, llm_response, re.MULTILINE))
    
    for i, match in enumerate(matches):
        role_title = match.group(1).strip()
        match_percentage = int(match.group(2))
        
        # Get the text block for this recommendation
        start_index = match.end()
        end_index = matches[i+1].start() if i + 1 < len(matches) else len(llm_response)
        recommendation_text = llm_response[start_index:end_index].strip()
        
        # Initialize the recommendation dictionary with defaults
        current_rec = {
            'role': role_title,
            'match': match_percentage,
            'description': None,
            'skills_needed': None,
            'growth_potential': None,
            'salary_range': None
        }
        
        # Parse the individual fields within this block
        lines = recommendation_text.split('\n')
        for line in lines:
            line = line.strip()
            if not line: continue
            
            if line.startswith('Description:'):
                current_rec['description'] = line.split('Description:', 1)[1].strip()
            elif line.startswith('Skills needed:'):
                current_rec['skills_needed'] = line.split('Skills needed:', 1)[1].strip()
            elif line.startswith('Growth potential:'):
                current_rec['growth_potential'] = line.split('Growth potential:', 1)[1].strip()
            elif line.startswith('Salary range:'):
                current_rec['salary_range'] = line.split('Salary range:', 1)[1].strip()
        
        # Only add if we successfully parsed the role title
        if current_rec['role']:
            recommendations.append(current_rec)
            
    # If parsing failed completely, maybe log or return an empty list
    if not recommendations:
         print("Warning: Failed to parse any recommendations from LLM response:")
         print(llm_response[:500] + "...") # Log the beginning of the problematic response
            
    return recommendations

def generate_improved_career_prompt(resume_data: Dict[str, Any], user_profile: Optional[Dict[str, Any]] = None) -> str:
    """
    Generate a prompt for the LLM that will result in better career recommendations
    while maintaining the exact same field structure.
    
    Args:
        resume_data: Extracted data from the user's resume
        user_profile: Additional user profile information if available
        
    Returns:
        Prompt string for the LLM
    """
    # Convert resume data to string representation
    resume_str = json.dumps(resume_data, indent=2)
    profile_str = json.dumps(user_profile, indent=2) if user_profile else "Not provided"
    
    prompt = f"""
    Based on the following resume data, generate 3 personalized career path recommendations.
    Resume data: {resume_str}
    User profile (if available): {profile_str}
    
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
    
    ===== EXAMPLE OF A THIRD GOOD RECOMMENDATION =====
    
    Customer Experience Specialist (Match: 89%)
    
    Description: Create excellent customer experiences while resolving complex issues across multiple channels.
    
    Skills needed: Communication, Problem-solving, CRM systems, Patience, Active listening, Conflict resolution
    
    Growth potential: High
    
    Salary range: $40,000 - $68,000
    
    ===== GENERATE THREE RECOMMENDATIONS =====
    Please generate THREE career recommendations that follow this exact format, with the following constraints:
    1. Use realistic match percentages based on actual skills overlap (don't give everyone 60%)
    2. Recommend attainable roles based on the person's experience level
    3. Ensure all required fields are included with the exact naming shown in the examples
    4. Keep descriptions concise but specific to the role
    5. Only include careers that are logical progressions from their current experience
    """
    
    return prompt

def get_career_recommendations(ai_client, resume_data: Dict[str, Any], user_profile: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Generate improved career recommendations using the LLM while maintaining the same UI format.
    
    Args:
        ai_client: AI client to use for generating recommendations
        resume_data: Extracted data from the user's resume
        user_profile: Additional user profile information if available
        
    Returns:
        List of dictionaries containing structured career recommendations
    """
    try:
        # Generate the prompt
        prompt = generate_improved_career_prompt(resume_data, user_profile)
        
        # Call the LLM
        recommendation_model = ai_client.GenerativeModel('gemini-1.5-flash')
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
        ]
        
        response = recommendation_model.generate_content(
            prompt,
            safety_settings=safety_settings
        )
        
        # Parse the response
        recommendations = parse_llm_career_recommendations(response.text)
        
        return recommendations
    except Exception as e:
        print(f"Error generating career recommendations: {e}")
        # Return a fallback recommendation
        return [{
            "role": "Error generating recommendations",
            "match": 0,
            "description": "There was an error generating career recommendations. Please try again later.",
            "skills_needed": "N/A",
            "growth_potential": "N/A",
            "salary_range": "N/A"
        }]

# Example of how to use this in your Flask route
"""
@app.route('/career-roadmap')
def career_roadmap():
    # Get the user's resume data
    user_id = session['user_id']
    user_resume = Resume.query.filter_by(user_id=user_id).first()
    
    # Extract resume data (replace with your actual extraction logic)
    resume_data = extract_resume_data(user_resume.resume_path)
    
    # Get user profile data if available
    user_profile = get_user_profile(user_id)
    
    # Generate improved career recommendations
    recommendations = get_career_recommendations(ai_client, resume_data, user_profile)
    
    # Render the template with the recommendations
    return render_template('career_roadmap.html', recommendations=recommendations)
""" 