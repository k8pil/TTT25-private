import os
import easyocr
import pytesseract
from PIL import Image
import re
import json
from typing import Dict, List, Optional, Any
from .utils import ensure_directory

class ResumeProcessor:
    def __init__(self, ai_client):
        """Initialize the resume processor."""
        self.reader = easyocr.Reader(['en'])  # Initialize EasyOCR for English
        self.ai_client = ai_client
        self.extracted_text = ""
        self.structured_data = {}
        
        # Create cache directory for processed resumes
        ensure_directory("cache/resumes")
    
    def extract_text_from_image(self, image_path: str) -> str:
        """Extract text from resume image using OCR."""
        try:
            # Try with EasyOCR first
            results = self.reader.readtext(image_path)
            text = ' '.join([result[1] for result in results])
            
            # If text is too short, try with pytesseract as fallback
            if len(text) < 100:
                image = Image.open(image_path)
                text = pytesseract.image_to_string(image)
                
            self.extracted_text = text
            return text
        except Exception as e:
            print(f"Error extracting text from image: {e}")
            return ""
    
    def parse_resume_with_ai(self) -> Dict:
        """Extract structured data from resume text using AI."""
        if not self.extracted_text:
            return {}
            
        try:
            prompt = f"""
            Extract the following information from this resume text. Format the response as JSON.
            If some information is not available, use null for that field.
            
            Resume text:
            {self.extracted_text}
            
            Information to extract:
            1. Name
            2. Email
            3. Phone
            4. LinkedIn
            5. GitHub/Portfolio
            6. Skills (as an array)
            7. Education (as an array of objects with institution, degree, field, year)
            8. Experience (as an array of objects with company, title, period, responsibilities)
            9. Projects (as an array of objects with name, description, technologies)
            10. Certifications (as an array)
            
            Return only the JSON without any explanation.
            """
            
            # Initialize Gemini model
            model = self.ai_client.GenerativeModel('gemini-1.5-flash')
            
            # Configure the model for JSON output
            generation_config = {
                "temperature": 0.2,
                "top_p": 0.8,
                "top_k": 40,
                "response_mime_type": "application/json"
            }
            
            # Generate response
            response = model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            # Extract and parse JSON from response
            response_text = response.text
            
            # Handle potential text wrapping around the JSON
            try:
                # Try to parse directly
                self.structured_data = json.loads(response_text)
            except json.JSONDecodeError:
                # If failed, try to extract JSON part using regex
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    try:
                        self.structured_data = json.loads(json_match.group(0))
                    except json.JSONDecodeError:
                        print("Failed to parse JSON from response")
                        return {}
                else:
                    print("No JSON content found in response")
                    return {}
            
            return self.structured_data
            
        except Exception as e:
            print(f"Error parsing resume with AI: {e}")
            return {}
    
    def process_resume(self, image_path: str) -> Dict:
        """Process resume image and return structured data."""
        text = self.extract_text_from_image(image_path)
        if text:
            structured_data = self.parse_resume_with_ai()
            return structured_data
        return {}
    
    def get_resume_summary(self) -> str:
        """Generate a summary of the resume for the interviewer's reference."""
        if not self.structured_data:
            return "No resume data available."
            
        try:
            prompt = f"""
            Create a concise summary of this candidate's profile based on their resume:
            {json.dumps(self.structured_data, indent=2)}
            
            Focus on:
            1. Their overall professional profile
            2. Key skills and technologies
            3. Most relevant experience
            4. Educational background
            
            Keep it under 250 words.
            """
            
            # Initialize Gemini model
            model = self.ai_client.GenerativeModel('gemini-1.5-flash')
            
            # Generate summary
            response = model.generate_content(prompt)
            
            return response.text
            
        except Exception as e:
            print(f"Error generating resume summary: {e}")
            return "Error generating resume summary." 