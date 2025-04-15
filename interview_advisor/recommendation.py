import json
from typing import Dict, List, Optional
import time
import os
import re
from .utils import save_json_file


class RecommendationEngine:
    def __init__(self, ai_client, tts_service=None):
        """Initialize the recommendation engine."""
        self.ai_client = ai_client
        self.tts_service = tts_service

    def generate_recommendations(self, resume_data: Dict, conversation: List[Dict], session_dir: str) -> Dict:
        """Generate recommendations based on the resume and interview conversation."""
        try:
            # Create a conversation transcript in a readable format
            transcript = self._create_transcript(conversation)

            # Generate the recommendations
            recommendations = self._analyze_interview(resume_data, transcript)

            # Save recommendations to file
            save_path = os.path.join(session_dir, "recommendations.json")
            save_json_file(recommendations, save_path)

            # Format recommendations for display
            formatted_recommendations = self._format_recommendations(
                recommendations)

            # Generate TTS for the formatted recommendations
            if self.tts_service:
                self.tts_service.text_to_speech(formatted_recommendations)

            return recommendations

        except Exception as e:
            print(f"Error generating recommendations: {e}")
            return {"error": str(e)}

    def _create_transcript(self, conversation: List[Dict]) -> str:
        """Create a readable transcript from the conversation history."""
        transcript = ""

        for entry in conversation:
            role = entry["role"].capitalize()
            content = entry["content"]

            transcript += f"{role}: {content}\n\n"

        return transcript

    def _analyze_interview(self, resume_data: Dict, transcript: str) -> Dict:
        """Analyze the interview and generate recommendations."""
        try:
            # Format the prompt for the AI to analyze the interview
            system_prompt = """You are an expert career counselor with experience in HR and technical recruiting.
            Analyze this interview transcript and provide detailed, constructive feedback and recommendations.
            Your goal is to help the candidate improve their interview skills and career prospects."""

            user_prompt = f"""Below is a resume and transcript of a job interview.
            
            RESUME DATA:
            {json.dumps(resume_data, indent=2)}
            
            INTERVIEW TRANSCRIPT:
            {transcript}
            
            Please analyze this interview comprehensively and provide:
            
            1. STRENGTHS: Identify 3-5 key strengths demonstrated in the interview.
            
            2. AREAS FOR IMPROVEMENT: Identify 3-5 areas where the candidate could improve their interview performance.
            
            3. COMMUNICATION SKILLS: Evaluate how well the candidate communicated their experience and answered questions.
            
            4. TECHNICAL ASSESSMENT: Evaluate the candidate's technical knowledge based on their answers.
            
            5. SKILL RECOMMENDATIONS: Suggest 3-5 specific technical skills or technologies the candidate should learn to enhance their marketability based on current job market trends and their existing skillset.
            
            6. CAREER ADVICE: Provide 3-5 actionable pieces of career advice to help them advance.
            
            7. INTERVIEW PREPARATION TIPS: Provide 3-5 tips for better interview preparation next time.
            
            Format the response as a structured JSON object with these sections. For each point, provide a brief title and detailed explanation.
            
            {system_prompt}
            """

            # Initialize Gemini model with a preference for structured output
            model = self.ai_client.GenerativeModel('gemini-1.5-flash')

            # Configure the model for more structured output
            generation_config = {
                "temperature": 0.2,
                "top_p": 0.8,
                "top_k": 40,
                "response_mime_type": "application/json"
            }

            # Generate recommendations
            response = model.generate_content(
                user_prompt,
                generation_config=generation_config
            )

            # Extract and parse JSON from the response
            response_text = response.text

            # Try to parse JSON from the response
            try:
                # Try to parse directly
                recommendations = json.loads(response_text)
            except json.JSONDecodeError:
                # If failed, try to extract JSON part using regex
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    try:
                        recommendations = json.loads(json_match.group(0))
                    except json.JSONDecodeError:
                        print("Failed to parse JSON from recommendations response")
                        return self._create_fallback_recommendations()
                else:
                    print("No JSON content found in recommendations response")
                    return self._create_fallback_recommendations()

            return recommendations

        except Exception as e:
            print(f"Error analyzing interview: {e}")
            return self._create_fallback_recommendations()

    def _create_fallback_recommendations(self) -> Dict:
        """Create a fallback recommendations structure if analysis fails."""
        return {
            "error": "Error analyzing interview",
            "strengths": [],
            "areas_for_improvement": [],
            "communication_skills": {"rating": "Unable to assess", "feedback": "Error analyzing interview."},
            "technical_assessment": {"rating": "Unable to assess", "feedback": "Error analyzing interview."},
            "skill_recommendations": [],
            "career_advice": [],
            "interview_preparation_tips": []
        }

    def _format_recommendations(self, recommendations: Dict) -> str:
        """Format recommendations into a readable text for display and TTS."""
        try:
            formatted = "# Interview Feedback and Recommendations\n\n"

            # Strengths
            formatted += "## Strengths\n"
            for strength in recommendations.get("strengths", []):
                formatted += f"- **{strength.get('title')}**: {strength.get('explanation')}\n\n"

            # Areas for improvement
            formatted += "## Areas for Improvement\n"
            for area in recommendations.get("areas_for_improvement", []):
                formatted += f"- **{area.get('title')}**: {area.get('explanation')}\n\n"

            # Communication skills
            comm = recommendations.get("communication_skills", {})
            formatted += f"## Communication Skills\n**Rating**: {comm.get('rating', 'N/A')}\n{comm.get('feedback', '')}\n\n"

            # Technical assessment
            tech = recommendations.get("technical_assessment", {})
            formatted += f"## Technical Assessment\n**Rating**: {tech.get('rating', 'N/A')}\n{tech.get('feedback', '')}\n\n"

            # Skill recommendations
            formatted += "## Recommended Skills to Learn\n"
            for skill in recommendations.get("skill_recommendations", []):
                formatted += f"- **{skill.get('title')}**: {skill.get('explanation')}\n\n"

            # Career advice
            formatted += "## Career Advice\n"
            for advice in recommendations.get("career_advice", []):
                formatted += f"- **{advice.get('title')}**: {advice.get('explanation')}\n\n"

            # Interview preparation tips
            formatted += "## Interview Preparation Tips\n"
            for tip in recommendations.get("interview_preparation_tips", []):
                formatted += f"- **{tip.get('title')}**: {tip.get('explanation')}\n\n"

            # Simplify for TTS without markdown
            tts_text = formatted.replace("# ", "").replace(
                "## ", "").replace("**", "").replace("\n\n", "\n")

            return tts_text

        except Exception as e:
            print(f"Error formatting recommendations: {e}")
            return "Error formatting recommendations."

    def get_recommendations_summary(self, recommendations: Dict) -> str:
        """Generate a concise summary of the key recommendations."""
        try:
            system_prompt = """You are a professional career coach summarizing feedback after a job interview.
            Create a concise, encouraging summary highlighting key points."""

            user_prompt = f"""Here are detailed recommendations after a job interview:
            {json.dumps(recommendations, indent=2)}
            
            Please create a concise, encouraging summary (under 200 words) highlighting:
            1. One or two key strengths to continue leveraging
            2. One or two priority areas for improvement
            3. The most important skill recommendation
            4. The most valuable piece of career advice
            
            Keep the tone positive and actionable.
            
            {system_prompt}
            """

            # Initialize Gemini model
            model = self.ai_client.GenerativeModel('gemini-1.5-flash')

            # Generate summary
            response = model.generate_content(user_prompt)

            return response.text

        except Exception as e:
            print(f"Error generating recommendations summary: {e}")
            return "Unable to generate recommendations summary at this time."
