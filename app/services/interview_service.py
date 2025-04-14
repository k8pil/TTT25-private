"""
Interview Service for the Interview Advisor application
"""

import os
import sys
import time
import json
from typing import Dict, List, Any, Optional

# Import TTS service
from app.services.tts_service import TTSService


class InterviewService:
    def __init__(self, resume_id=None):
        """Initialize the interview service"""
        self.resume_id = resume_id
        self.session_id = f"interview_{int(time.time())}"
        self.conversation_history = []
        self.current_question_index = 0
        self.interview_start_time = None
        self.interview_end_time = None

        # Simple mock resume data
        self.resume_data = {
            "name": "Candidate",
            "skills": ["Python", "JavaScript", "Flask", "React"],
            "experience": [
                {"position": "Software Developer",
                    "company": "Tech Company", "years": 2}
            ],
            "education": [
                {"degree": "Computer Science", "institution": "University"}
            ]
        }

        # Set up TTS service
        try:
            self.tts_service = TTSService(silent_mode=True)
        except Exception as e:
            print(f"Warning: Could not initialize TTS service: {e}")
            self.tts_service = None

        # Create session directory
        self.session_dir = f"cache/interviews/{self.session_id}"
        os.makedirs(self.session_dir, exist_ok=True)

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

    def end_interview(self) -> str:
        """End the interview and record the end time."""
        self.interview_end_time = time.time()

        # Add closing statement
        closing = self._generate_closing_statement()

        # Add to conversation history
        self.conversation_history.append({
            "role": "interviewer",
            "content": closing,
            "timestamp": time.time()
        })

        # Save the conversation history
        self._save_conversation()

        # Convert to speech if TTS is available
        if self.tts_service:
            try:
                self.tts_service.text_to_speech(closing)
            except Exception as e:
                print(f"Warning: Could not convert text to speech: {e}")

        return closing

    def get_recommendations(self) -> Dict[str, Any]:
        """Generate recommendations based on the interview."""
        # Mock recommendations
        return {
            "strengths": ["Good communication skills", "Technical knowledge"],
            "areas_for_improvement": ["More detailed examples", "Deeper technical explanations"],
            "communication_rating": 8,
            "technical_rating": 7,
            "recommendations": ["Practice more technical interviews", "Prepare more specific examples"]
        }

    def process_audio(self, audio_path: str) -> str:
        """Process audio file to extract text."""
        return "Audio transcription placeholder. This would be the transcribed text from the audio file."

    def _generate_introduction_question(self) -> str:
        """Generate the introduction question based on the resume."""
        name = self.resume_data.get('name', 'the candidate')
        return f"Hello, and welcome to your interview! My name is AI Interviewer. Could you please introduce yourself and tell me a bit about your background and experience?"

    def _generate_next_question(self, previous_answer: str) -> str:
        """Generate the next interview question based on the conversation history."""
        # List of generic interview questions
        questions = [
            "Can you tell me about a challenging project you worked on?",
            "What are your key technical skills and how have you applied them in your work?",
            "How do you approach problem-solving in your work?",
            "Can you describe your experience working in a team?",
            "What are your career goals for the next few years?",
            "How do you stay updated with the latest technologies in your field?",
            "Can you describe a situation where you had to learn a new technology quickly?",
            "How do you handle tight deadlines and pressure?",
            "What do you consider your greatest professional achievement?",
            "Why are you interested in this position/company?"
        ]

        # Pick a question based on the current index
        if self.current_question_index < len(questions):
            return questions[self.current_question_index]
        else:
            return "Can you tell me more about your approach to continuous learning and skill development?"

    def _generate_closing_statement(self) -> str:
        """Generate a closing statement for the interview."""
        return "Thank you for participating in this interview. We've covered a good range of topics, and I appreciate your thoughtful responses. We'll be in touch soon about next steps. Do you have any questions for me before we conclude?"

    def _save_conversation(self) -> None:
        """Save the conversation history to a file."""
        try:
            filepath = os.path.join(self.session_dir, "conversation.json")
            with open(filepath, 'w', encoding='utf-8') as file:
                json.dump(self.conversation_history, file, indent=2)
        except Exception as e:
            print(f"Error saving conversation: {e}")

    def get_interview_duration(self) -> float:
        """Get the duration of the interview in seconds."""
        if not self.interview_start_time:
            return 0

        end_time = self.interview_end_time or time.time()
        return end_time - self.interview_start_time
