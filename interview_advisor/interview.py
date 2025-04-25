import os
import json
import time
from typing import Dict, List, Tuple, Optional, Any
from .utils import read_text_file, save_json_file, ensure_directory


class Interview:
    def __init__(self, ai_client, tts_service, resume_data=None):
        """Initialize the interview with AI client and resume data."""
        self.ai_client = ai_client
        self.tts_service = tts_service
        self.resume_data = resume_data or {}
        self.conversation_history = []
        self.introduction = ""
        self.current_question_index = 0
        self.interview_start_time = None
        self.interview_end_time = None

        # Create interview data directory
        ensure_directory("cache/interviews")

        # Initialize the interview session ID
        self.session_id = f"interview_{int(time.time())}"
        self.session_dir = f"cache/interviews/{self.session_id}"
        ensure_directory(self.session_dir)

    def start_interview(self) -> str:
        """Start the interview with an introduction question."""
        self.interview_start_time = time.time()

        # Generate introduction question
        intro_question = self._generate_introduction_question()

        # Add to conversation history
        self.conversation_history.append({
            "role": "interviewer",
            "content": intro_question,
            "timestamp": time.time()
        })

        # Save the conversation history
        self._save_conversation()

        # Convert to speech if TTS is available
        if self.tts_service:
            try:
                self.tts_service.text_to_speech(intro_question)
            except Exception as e:
                print(f"Warning: Could not convert text to speech: {e}")

        return intro_question

    def process_answer(self, answer_text: str) -> str:
        """Process the candidate's answer and generate the next question."""
        # Process the answer
        if self.current_question_index == 0:
            # If this is the answer to the intro question, save it as introduction
            self.introduction = answer_text

        # Add to conversation history
        self.conversation_history.append({
            "role": "candidate",
            "content": answer_text,
            "timestamp": time.time()
        })

        # Generate the next question
        next_question = self._generate_next_question(answer_text)

        # Add to conversation history
        self.conversation_history.append({
            "role": "interviewer",
            "content": next_question,
            "timestamp": time.time()
        })

        # Increment question index
        self.current_question_index += 1

        # Save the conversation history
        self._save_conversation()

        # Convert to speech if TTS is available
        if self.tts_service:
            try:
                self.tts_service.text_to_speech(next_question)
            except Exception as e:
                print(f"Warning: Could not convert text to speech: {e}")

        return next_question

    def end_interview(self) -> Tuple[str, str]:
        """End the interview, record the end time, and return closing statement + transcript."""
        self.interview_end_time = time.time()

        # Generate standard closing statement
        closing = self._generate_closing_statement()

        # Format the conversation history into a transcript string
        transcript = "Interview Transcript:\n\n"
        for entry in self.conversation_history:
            role = entry["role"].capitalize()
            transcript += f"{role}: {entry['content']}\n\n"

        # Add final closing statement to history (optional, might duplicate)
        self.conversation_history.append({
            "role": "interviewer",
            "content": closing,
            "timestamp": time.time()
        })

        # Save the complete conversation history
        self._save_conversation()

        # Convert closing to speech if TTS is available
        if self.tts_service:
            try:
                self.tts_service.text_to_speech(closing)
            except Exception as e:
                print(f"Warning: Could not convert closing text to speech: {e}")

        return closing, transcript

    def _generate_introduction_question(self) -> str:
        """Generate the introduction question based on the resume."""
        try:
            name = self.resume_data.get('name', 'the candidate')

            # Create a personalized introduction
            system_prompt = """You are an experienced HR interviewer conducting a job interview. 
            Your tone is professional, friendly, and engaging. Start with a warm introduction 
            and then ask the candidate to introduce themselves."""

            user_prompt = f"""Based on the following resume information, create a personalized 
            introduction and opening question for {name}.
            
            Resume data: {json.dumps(self.resume_data, indent=2)}
            
            Format your response as a natural introduction followed by asking the candidate to 
            introduce themselves and briefly describe their background and interests.
            Keep it conversational and under 150 words.
            
            {system_prompt}
            """

            # Initialize Gemini model
            model = self.ai_client.GenerativeModel('gemini-1.5-flash')

            # Generate introduction
            print("[DEBUG Interview] Generating introduction question...")
            print(f"[DEBUG Interview] Prompt for intro question:\n---\n{user_prompt[:500]}...\n---")
            response = model.generate_content(user_prompt)
            
            # Debug the raw response
            try:
                raw_response_text = response.text
                print(f"[DEBUG Interview] Raw AI response for intro: {raw_response_text[:200]}...")
            except Exception as e:
                raw_response_text = f"Error accessing response text: {e}"
                print(f"[DEBUG Interview] Error accessing AI response text: {e}")
                # Try printing the whole response object for more clues
                try:
                    print(f"[DEBUG Interview] Full AI response object: {response}")
                except Exception as e_inner:
                    print(f"[DEBUG Interview] Could not print full response object: {e_inner}")

            return raw_response_text

        except Exception as e:
            print(f"[DEBUG Interview] Error in _generate_introduction_question: {e}")
            print(f"Error generating introduction question: {e}")
            # Return the fallback question
            fallback_question = "Hello! Thank you for joining us today. Could you please introduce yourself and tell me a bit about your background and experience?"
            print(f"[DEBUG Interview] Returning fallback question: {fallback_question}")
            return fallback_question

    def _generate_next_question(self, previous_answer: str) -> str:
        """Generate the next interview question based on the conversation history and resume."""
        try:
            # First analyze the previous answer for factual errors and inappropriate language
            analysis_prompt = f"""
            Analyze the following answer from a job interview candidate:
            
            "{previous_answer}"
            
            Analyze for:
            1. Factual errors or incorrect technical information
            2. Inappropriate language, profanity, or offensive content
            
            Return a JSON object with these fields:
            - "has_factual_errors": true/false
            - "factual_error_details": description of errors if any (empty string if none)
            - "has_inappropriate_language": true/false
            - "inappropriate_language_details": description of inappropriate content if any (empty string if none)
            
            Response format should be valid JSON only.
            """

            # Initialize Gemini model
            model = self.ai_client.GenerativeModel('gemini-1.5-flash')
            generation_config = {
                "temperature": 0.1,
                "response_mime_type": "application/json"
            }

            # Analyze the answer
            analysis_response = model.generate_content(
                analysis_prompt,
                generation_config=generation_config
            )

            # Extract analysis results
            try:
                analysis = json.loads(analysis_response.text)
            except:
                # Fallback if JSON parsing fails
                analysis = {
                    "has_factual_errors": False,
                    "factual_error_details": "",
                    "has_inappropriate_language": False,
                    "inappropriate_language_details": ""
                }

            # If there are issues with the answer, address them instead of asking the next question
            if analysis.get("has_factual_errors") or analysis.get("has_inappropriate_language"):
                correction_prompt = ""

                if analysis.get("has_inappropriate_language"):
                    correction_prompt = f"""
                    As an interviewer, respond in a stern, professional tone to the following inappropriate language
                    used by a candidate during an interview:
                    
                    Candidate's statement: "{previous_answer}"
                    
                    Issue: {analysis.get("inappropriate_language_details")}
                    
                    Your response should:
                    1. Express clear disapproval in an angry but still professional tone
                    2. Explain why such language is inappropriate in a professional setting
                    3. Give the candidate a chance to reformulate their answer
                    4. Be direct and firm while maintaining professionalism
                    
                    Keep your response under 100 words.
                    """
                elif analysis.get("has_factual_errors"):
                    correction_prompt = f"""
                    As an interviewer, respond to the following factual errors or incorrect information
                    provided by a candidate during an interview:
                    
                    Candidate's statement: "{previous_answer}"
                    
                    Issues identified: {analysis.get("factual_error_details")}
                    
                    Your response should:
                    1. Politely point out the inaccuracies
                    2. Provide the correct information
                    3. Ask the candidate if they'd like to revise their answer
                    4. Be constructive and educational rather than judgmental
                    
                    Keep your response under 100 words.
                    """

                if correction_prompt:
                    correction_response = model.generate_content(
                        correction_prompt)
                    return correction_response.text

            # Create a prompt with conversation history for the next question
            system_prompt = """You are an experienced HR interviewer conducting a job interview.
            Ask insightful, relevant questions based on the candidate's resume and previous answers.
            Your questions should help evaluate the candidate's skills, experience, and fit for roles
            matching their background. Be conversational but professional. Ask only ONE question at a time.
            Don't repeat questions already asked. Vary between technical, behavioral, and situational questions."""

            # Add resume context
            resume_context = f"Here is the candidate's resume information: {json.dumps(self.resume_data, indent=2)}\n\n"

            # Add conversation history
            conversation = "Here's our conversation so far:\n\n"
            for entry in self.conversation_history:
                role = entry["role"].capitalize()
                conversation += f"{role}: {entry['content']}\n\n"

            # Combine all the context
            prompt = f"""{system_prompt}

{resume_context}

{conversation}

Based on the resume and our conversation so far, generate the next interview question.
Ask only ONE clear, specific question. Ensure it flows naturally from the previous conversation.
Keep your question under 100 words.
"""

            # Generate next question
            response = model.generate_content(prompt)

            return response.text

        except Exception as e:
            print(f"Error generating next question: {e}")
            return "That's interesting. Could you tell me more about your most recent project and the technologies you used?"

    def _generate_closing_statement(self) -> str:
        """Generate a closing statement for the interview."""
        try:
            candidate_name = self.resume_data.get('Name', 'there')
            
            # Create prompt for closing statement, incorporating name
            prompt = f"""You are an experienced HR interviewer concluding a job interview.
            Create a warm, professional closing statement addressed to {candidate_name}, thanking them for their time.
            Mention that you've gathered valuable insights about their experience and skills.
            Inform them about next steps in general terms (e.g., 'the team will review', 'we will be in touch').
            
            Generate the closing statement.
            Keep it warm, professional, and under 100 words.
            """

            # Initialize Gemini model
            model = self.ai_client.GenerativeModel('gemini-1.5-flash')

            # Generate closing statement
            response = model.generate_content(prompt)

            return response.text

        except Exception as e:
            print(f"Error generating closing statement: {e}")
            # Update fallback message as well
            candidate_name_fallback = self.resume_data.get('Name', 'you')
            return f"Thank {candidate_name_fallback} for taking the time to interview with us today. We appreciate your thoughtful responses and sharing your experience. Our team will review the interview and be in touch regarding next steps. Have a great day!"

    def _save_conversation(self) -> None:
        """Save the conversation history to a JSON file."""
        try:
            save_json_file(
                {"conversation": self.conversation_history},
                os.path.join(self.session_dir, "conversation.json")
            )
        except Exception as e:
            print(f"Error saving conversation: {e}")

    def load_answer_from_file(self, file_path: str) -> str:
        """Load the candidate's answer from a text file."""
        answer_text = read_text_file(file_path)
        return self.process_answer(answer_text)

    def get_interview_duration(self) -> float:
        """Get the duration of the interview in minutes."""
        if not self.interview_start_time:
            return 0

        end_time = self.interview_end_time or time.time()
        return (end_time - self.interview_start_time) / 60
