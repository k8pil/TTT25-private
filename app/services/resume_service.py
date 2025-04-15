"""
Resume Service for the Interview Advisor application
"""

import os
import sys
import json
import time
from typing import Dict, List, Any, Optional
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up Google Gemini
google_api_key = os.getenv("GOOGLE_API_KEY")
if google_api_key:
    genai.configure(api_key=google_api_key)


class ResumeService:
    def __init__(self):
        """Initialize the resume service"""
        self.ai_client = genai
        self.resume_data = {}
        self.resume_text = ""
        self.resume_id = None

        # Create resume directory
        os.makedirs("cache/resumes", exist_ok=True)

    def get_resume_data(self, resume_id: str) -> Dict[str, Any]:
        """Get resume data for a specific resume ID"""
        self.resume_id = resume_id

        # Check if the resume file exists
        resume_path = os.path.join("uploads", resume_id)
        if not os.path.exists(resume_path):
            print(f"Resume file not found: {resume_path}")
            return {}

        # Extract text from the resume file
        try:
            self.resume_text = self.extract_text_from_file(resume_path)
            self.resume_data = self.parse_resume_with_ai()
            return self.resume_data
        except Exception as e:
            print(f"Error processing resume: {e}")
            return {}

    def extract_text_from_file(self, file_path: str) -> str:
        """Extract text from a file (PDF, image, etc.)"""
        try:
            # Determine file type based on extension
            file_ext = os.path.splitext(file_path)[1].lower()

            if file_ext == '.pdf':
                return self.extract_text_from_pdf(file_path)
            elif file_ext in ['.png', '.jpg', '.jpeg']:
                return self.extract_text_from_image(file_path)
            else:
                # For text files, just read the content
                with open(file_path, 'r', encoding='utf-8') as file:
                    return file.read()
        except Exception as e:
            print(f"Error extracting text from file: {e}")
            return ""

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from a PDF file"""
        try:
            # This would typically use a PDF extraction library like PyPDF2 or pdfminer
            # For now, return a placeholder
            return f"[PDF Text extraction not implemented. Would extract text from {pdf_path}]"
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            return ""

    def extract_text_from_image(self, image_path: str) -> str:
        """Extract text from an image file using OCR"""
        try:
            # This would typically use an OCR library like pytesseract
            # For now, return a placeholder
            return f"[Image OCR not implemented. Would extract text from {image_path}]"
        except Exception as e:
            print(f"Error extracting text from image: {e}")
            return ""

    def parse_resume_with_ai(self) -> Dict[str, Any]:
        """Parse resume text using AI to extract structured information"""
        try:
            if not self.resume_text:
                print("No resume text to parse")
                return {}

            # Create a prompt for the AI
            prompt = f"""Extract structured information from the following resume text.
            
            Resume text:
            {self.resume_text}
            
            Extract and return ONLY the following information in JSON format:
            - name: The candidate's full name
            - email: Email address if present
            - phone: Phone number if present
            - education: List of education entries (institution, degree, field, dates)
            - experience: List of work experiences (company, position, dates, responsibilities)
            - skills: List of technical and soft skills
            - certifications: List of certifications if any
            - languages: List of languages the candidate knows
            - summary: A brief summary of the candidate's profile
            
            Return ONLY valid JSON without any additional text.
            """

            # Generate structured data using AI
            model = self.ai_client.GenerativeModel('gemini-1.5-flash')
            generation_config = {
                "temperature": 0.1,
                "response_mime_type": "application/json"
            }

            response = model.generate_content(
                prompt,
                generation_config=generation_config
            )

            # Parse the JSON response
            try:
                resume_data = json.loads(response.text)

                # Save the parsed data
                self._save_resume_data(resume_data)

                return resume_data
            except json.JSONDecodeError:
                print("Error parsing AI response as JSON")
                # Try to extract JSON from the text
                import re
                json_match = re.search(r'(\{.*\})', response.text, re.DOTALL)
                if json_match:
                    try:
                        resume_data = json.loads(json_match.group(1))
                        self._save_resume_data(resume_data)
                        return resume_data
                    except:
                        pass

                # Return empty dict if parsing fails
                return {}

        except Exception as e:
            print(f"Error parsing resume with AI: {e}")
            return {}

    def get_resume_summary(self) -> str:
        """Get a summary of the resume"""
        try:
            if not self.resume_data:
                return "No resume data available."

            # Create a prompt for the AI
            prompt = f"""Create a concise summary of the candidate's profile based on their resume.
            
            Resume data: {json.dumps(self.resume_data, indent=2)}
            
            The summary should highlight key qualifications, experience, skills, and education.
            Keep it under 150 words and focus on the most relevant aspects for job interviews.
            """

            # Generate summary using AI
            model = self.ai_client.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)

            return response.text

        except Exception as e:
            print(f"Error generating resume summary: {e}")
            return "Could not generate resume summary due to an error."

    def _save_resume_data(self, resume_data: Dict[str, Any]) -> None:
        """Save the parsed resume data to a file"""
        try:
            if self.resume_id:
                filepath = os.path.join(
                    "cache/resumes", f"{self.resume_id}.json")
                with open(filepath, 'w', encoding='utf-8') as file:
                    json.dump(resume_data, file, indent=2)
        except Exception as e:
            print(f"Error saving resume data: {e}")

    def save_resume_text(self, text: str) -> str:
        """Save resume text and generate a resume ID"""
        try:
            # Generate a resume ID
            resume_id = f"resume_{int(time.time())}.txt"

            # Save the text
            filepath = os.path.join("uploads", resume_id)
            with open(filepath, 'w', encoding='utf-8') as file:
                file.write(text)

            # Set as current resume
            self.resume_id = resume_id
            self.resume_text = text

            return resume_id
        except Exception as e:
            print(f"Error saving resume text: {e}")
            return ""
