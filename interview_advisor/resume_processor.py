import os
import easyocr
import pytesseract
from PIL import Image
import re
import json
from typing import Dict, List, Optional, Any
from .utils import ensure_directory
# Import PyPDF2
try:
    from PyPDF2 import PdfReader
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    print("WARNING: PyPDF2 not installed. PDF resume processing will be disabled.")


class ResumeProcessor:
    def __init__(self, ai_client):
        """Initialize the resume processor."""
        try:
            self.reader = easyocr.Reader(['en'])  # Initialize EasyOCR for English
        except Exception as e:
            print(f"Warning: Could not initialize EasyOCR: {e}. OCR functionality may be limited.")
            self.reader = None
        self.ai_client = ai_client
        self.extracted_text = ""
        self.structured_data = {}

        # Create cache directory for processed resumes
        ensure_directory("cache/resumes")

    def extract_text_from_image(self, file_path: str) -> str:
        """Extract text from resume image using OCR."""
        if not self.reader:
            print("EasyOCR reader not available.")
            return ""
        try:
            # Try with EasyOCR first
            results = self.reader.readtext(file_path)
            text = ' '.join([result[1] for result in results])

            # If text is too short, try with pytesseract as fallback
            if len(text) < 100:
                print("EasyOCR text short, trying Pytesseract...")
                try:
                    image = Image.open(file_path)
                    text = pytesseract.image_to_string(image)
                except Exception as pe:
                    print(f"Pytesseract error: {pe}")
                    # Keep the short EasyOCR text if Pytesseract fails

            return text
        except Exception as e:
            print(f"Error extracting text from image {file_path}: {e}")
            # Attempt Pytesseract if EasyOCR failed completely
            try:
                print("EasyOCR failed, trying Pytesseract...")
                image = Image.open(file_path)
                text = pytesseract.image_to_string(image)
                return text
            except Exception as pe:
                 print(f"Pytesseract fallback also failed: {pe}")
                 return ""

    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from resume PDF using PyPDF2."""
        if not PYPDF2_AVAILABLE:
            print("PyPDF2 is not available. Cannot process PDF.")
            return ""
        try:
            text = ""
            with open(file_path, 'rb') as f:
                reader = PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() or ""
            return text
        except Exception as e:
            print(f"Error extracting text from PDF {file_path}: {e}")
            return ""

    def parse_resume_with_ai(self) -> Dict:
        """Extract structured data from resume text using AI."""
        if not self.extracted_text:
            print("No extracted text to parse.")
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

    def process_resume(self, file_path: str) -> Dict:
        """Process resume file (PDF or image) and return structured data."""
        self.extracted_text = ""
        self.structured_data = {}
        file_ext = os.path.splitext(file_path)[1].lower()

        print(f"Processing file: {file_path} with extension {file_ext}")

        if file_ext == '.pdf':
            self.extracted_text = self.extract_text_from_pdf(file_path)
        elif file_ext in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff']:
            self.extracted_text = self.extract_text_from_image(file_path)
        else:
            print(f"Warning: Unsupported file type '{file_ext}'. Attempting to read as text.")
            try:
                 with open(file_path, 'r', encoding='utf-8') as f:
                     self.extracted_text = f.read()
            except Exception as e:
                 print(f"Could not read file as text: {e}")
                 self.extracted_text = ""

        if self.extracted_text:
            print(f"Extracted text length: {len(self.extracted_text)}")
            self.structured_data = self.parse_resume_with_ai()
            # Optionally save structured data
            # save_path = os.path.join("cache/resumes", os.path.basename(file_path) + ".json")
            # save_json_file(self.structured_data, save_path)
            return self.structured_data
        else:
            print("Failed to extract text from resume.")
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
