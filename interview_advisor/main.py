from .speech_integration import SpeechInput
from .utils import validate_api_keys, ensure_directory, read_text_file, DatabaseManager
from .recommendation import RecommendationEngine
from .interview import Interview
from .resume_processor import ResumeProcessor
import os
import sys
import time
import json
import argparse
from dotenv import load_dotenv
import google.generativeai as genai
from typing import Dict, List, Optional, Any

# Load environment variables from .env file
load_dotenv()

# Import modules

# Fixed path to resume
RESUME_PATH = r"C:\Users\adity\Videos\HACKATHON\Untitled.png"

# Import TTS service with maximum error handling
TTS_AVAILABLE = False
try:
    from .tts_service import TTSService
    TTS_AVAILABLE = True
    print("TTS module imported successfully")
except Exception as e:
    print(f"WARNING: TTS service could not be imported: {e}")
    print("Text-to-speech functionality will be disabled.")


class InterviewAdvisor:
    def __init__(self, no_database=False):
        """Initialize the Interview Advisor application."""
        # Check for required API keys
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            print("ERROR: GOOGLE_API_KEY not found in .env file")
            print("Please add it to your .env file")
            sys.exit(1)

        # Initialize Google Gemini API client
        try:
            genai.configure(api_key=google_api_key)
            self.ai_client = genai
            print("AI client initialized successfully")
        except Exception as e:
            print(f"ERROR: Failed to initialize AI client: {e}")
            sys.exit(1)

        # Initialize TTS service with maximum error handling
        self.tts_service = None
        if TTS_AVAILABLE:
            try:
                # Use silent mode for cleaner presentations
                self.tts_service = TTSService(silent_mode=True)
                print("TTS Service initialized successfully")
            except Exception as e:
                print(f"WARNING: Failed to initialize TTS service: {e}")
                print("Continuing without text-to-speech capability")
        else:
            print(
                "TTS Service not available - continuing without text-to-speech capability")

        # Initialize speech input
        try:
            self.speech_input = SpeechInput()
            if self.speech_input.is_available():
                print("Speech input initialized successfully")
            else:
                print(
                    "Speech input not available - continuing without speech input capability")
        except Exception as e:
            print(f"WARNING: Failed to initialize speech input: {e}")
            print("Continuing without speech input capability")
            self.speech_input = None

        # Initialize database manager
        self.db_manager = None
        if not no_database:
            try:
                self.db_manager = DatabaseManager()
                print("Database manager initialized successfully")
            except Exception as e:
                print(f"WARNING: Failed to initialize database: {e}")
                print("Continuing without database functionality")
        else:
            print("Database functionality disabled")

        # Initialize components
        self.resume_processor = ResumeProcessor(self.ai_client)
        self.recommendation_engine = RecommendationEngine(
            self.ai_client, self.tts_service)

        # Initialize interview session
        self.interview = None
        self.resume_data = {}
        self.current_session_id = None

        print("Interview Advisor initialized and ready to use")

    def run(self):
        """Run the main application."""
        print("\n========================================")
        print("🤖 Welcome to the Interview Advisor! 🤖")
        print("========================================\n")

        print("This application will help you practice interviews and get feedback on your performance.")
        print(f"Using resume from: {RESUME_PATH}")

        while True:
            print("\nMain Menu:")
            print("1. Upload Resume")
            print("2. Start Interview")
            print("3. Process Interview Answer")
            print("4. End Interview & Get Recommendations")
            print("5. Resume Analysis")
            if self.tts_service:
                print("6. Change TTS Voice")
                print("T. Test Audio")
            if self.speech_input and self.speech_input.is_available():
                print("7. Configure Speech Input")
            print("9. Exit")

            choice = input("\nEnter your choice: ")

            if choice.upper() == "T" and self.tts_service:
                self._test_tts_audio()
            elif choice == "1":
                self._upload_resume()
            elif choice == "2":
                self._start_interview()
            elif choice == "3":
                self._process_answer()
            elif choice == "4":
                self._end_interview()
            elif choice == "5":
                self._analyze_resume()
            elif choice == "6" and self.tts_service:
                self._change_tts_voice()
            elif choice == "7" and self.speech_input and self.speech_input.is_available():
                self._configure_speech_input()
            elif choice == "9":
                print("\nThank you for using Interview Advisor. Goodbye!")
                sys.exit(0)
            else:
                print("Invalid choice. Please try again.")

    def _upload_resume(self):
        """Upload and process a resume image."""
        print("\n--- Upload Resume ---")

        # Use fixed resume path instead of asking for input
        resume_path = RESUME_PATH

        if not os.path.exists(resume_path):
            print(f"Error: Resume file not found at {resume_path}")
            return

        print(f"\nProcessing resume from: {resume_path}...")

        try:
            # Extract text from resume image
            extracted_text = self.resume_processor.extract_text_from_image(
                resume_path)

            if not extracted_text:
                print("Error: Failed to extract text from resume")
                return

            print(
                f"Successfully extracted {len(extracted_text)} characters from resume")

            # Parse resume data with AI
            self.resume_data = self.resume_processor.parse_resume_with_ai()

            if not self.resume_data:
                print("Error: Failed to parse resume data")
                return

            # Get a summary of the resume
            resume_summary = self.resume_processor.get_resume_summary()

            print("\nResume Summary:")
            print("---------------")
            print(resume_summary)

            print("\nResume processed successfully!")

        except Exception as e:
            print(f"Error processing resume: {e}")

    def _start_interview(self):
        """Start a new interview session."""
        print("\n--- Start Interview ---")

        if not self.resume_data:
            print("No resume data loaded. Processing resume first...")
            self._upload_resume()

            if not self.resume_data:
                print("Error: Unable to load resume data. Interview canceled.")
                return

        # Initialize interview
        self.interview = Interview(
            self.ai_client, self.tts_service, self.resume_data)

        # Create session ID in database
        self.current_session_id = self.interview.session_id
        if self.db_manager:
            resume_id = self.resume_data.get("id", "unknown")
            self.db_manager.create_session(self.current_session_id, resume_id)
            print(
                f"Interview session {self.current_session_id} created in database")

        # Start interview with introduction question
        intro_question = self.interview.start_interview()

        print("\nInterviewer:")
        print(intro_question)

        print("\nTo answer this question, use option 3 from the main menu to process your answer.")

    def _process_answer(self):
        """Process an answer to the last interview question."""
        print("\n--- Process Answer ---")

        if not self.interview:
            print("No active interview. Please start an interview first.")
            return

        # Check if speech input is available
        if self.speech_input and self.speech_input.is_available():
            # Use speech input directly without showing menu
            print("\nRecording your answer now... (Press Enter when finished)")
            try:
                answer_path = self.speech_input.capture_speech()

                if answer_path:
                    self._process_answer_with_file(answer_path)
                else:
                    print("Speech input failed. Showing alternative options.")
                    self._show_answer_input_options()
            except KeyboardInterrupt:
                print("\nRecording canceled.")
                self._show_answer_input_options()
        else:
            # If speech input is not available, show input options
            self._show_answer_input_options()

    def _show_answer_input_options(self):
        """Show options for inputting an answer."""
        print("\nHow would you like to input your answer?")
        print("1. Record with speech recognition")
        print("2. Use a text file")
        print("3. Return to main menu")

        choice = input("\nEnter your choice: ")

        if choice == "1" and self.speech_input and self.speech_input.is_available():
            # Use speech input
            print("\nRecording your answer now... (Press Enter when finished)")
            try:
                answer_path = self.speech_input.capture_speech()

                if answer_path:
                    self._process_answer_with_file(answer_path)
            except KeyboardInterrupt:
                print("\nRecording canceled.")

        elif choice == "2":
            # Use text file
            file_path = input("\nEnter the path to your answer file: ")

            if not os.path.exists(file_path):
                print(f"Error: File not found at {file_path}")
                return

            self._process_answer_with_file(file_path)

        elif choice == "3":
            print("Returning to main menu...")
            return

        else:
            print("Invalid choice or speech recognition not available.")

    def _process_answer_with_file(self, answer_path):
        """Process an answer from a file."""
        try:
            # Check if this is an audio file that needs transcription
            if answer_path.endswith(('.wav', '.mp3', '.m4a')):
                if self.speech_input and self.speech_input.is_available():
                    print(f"Transcribing audio from {answer_path}...")

                    # Transcribe the audio
                    transcription = self.speech_input.transcribe_file(
                        answer_path)

                    if not transcription:
                        print("Error: Failed to transcribe audio")
                        return

                    # Analyze speech fluency if possible
                    try:
                        fluency_analysis = self.speech_input.analyze_fluency(
                            answer_path)

                        if fluency_analysis and self.db_manager and self.current_session_id:
                            self.db_manager.save_audio_metrics(
                                self.current_session_id, fluency_analysis)
                            print("Speech fluency metrics saved to database")

                            # Display fluency score
                            score = fluency_analysis.get("fluency_score", 0)
                            print(f"Fluency Score: {score}/100")
                            for reason in fluency_analysis.get("reasons", []):
                                print(f"- {reason}")
                    except Exception as e:
                        print(
                            f"Warning: Could not analyze speech fluency: {e}")

                    # Use the transcription as the answer
                    answer_text = transcription
                else:
                    print("Error: Speech recognition not available")
                    return
            else:
                # Read the text file
                answer_text = read_text_file(answer_path)

            if not answer_text:
                print("Error: Empty answer text")
                return

            print("\nYour answer:")
            print(answer_text)

            # Process the answer
            next_question = self.interview.process_answer(answer_text)

            print("\nInterviewer:")
            print(next_question)

        except Exception as e:
            print(f"Error processing answer: {e}")

    def _end_interview(self):
        """End the interview and generate recommendations."""
        print("\n--- End Interview & Get Recommendations ---")

        if not self.interview:
            print("No active interview. Please start an interview first.")
            return

        # End the interview
        closing = self.interview.end_interview()
        print("\nInterviewer:")
        print(closing)

        # Update database with session end
        if self.db_manager and self.current_session_id:
            questions_count = self.interview.current_question_index
            self.db_manager.end_session(
                self.current_session_id, questions_count)
            print(
                f"Interview session {self.current_session_id} updated in database")

        # Generate recommendations
        print("\nGenerating recommendations...")
        recommendations = self.recommendation_engine.generate_recommendations(
            self.resume_data,
            self.interview.conversation_history,
            self.interview.session_dir
        )

        # Save analysis to database
        if self.db_manager and self.current_session_id:
            self.db_manager.save_analysis_results(
                self.current_session_id, recommendations)
            print("Interview analysis saved to database")

        # Print a summary of the recommendations
        summary = self.recommendation_engine.get_recommendations_summary(
            recommendations)

        print("\n=== Interview Feedback Summary ===")
        print(summary)
        print("\nDetailed recommendations have been saved to:")
        print(f"{self.interview.session_dir}/recommendations.json")

        # Reset interview for next session
        self.interview = None
        self.current_session_id = None

    def _change_tts_voice(self):
        """Change the TTS voice."""
        print("\n--- Change TTS Voice ---")

        if not self.tts_service:
            print("Error: TTS service is not available")
            return

        try:
            # Get available voices
            voices = self.tts_service.get_available_voices()

            print("\nAvailable Voices:")
            for i, voice in enumerate(voices):
                print(f"{i+1}. {voice}")

            choice = input("\nEnter your choice (1-{}): ".format(len(voices)))

            try:
                index = int(choice) - 1
                if 0 <= index < len(voices):
                    voice = voices[index]
                    self.tts_service.set_voice(voice)
                    print(f"Voice changed to: {voice}")
                else:
                    print("Invalid choice. Voice not changed.")
            except ValueError:
                print("Invalid input. Voice not changed.")

        except Exception as e:
            print(f"Error changing voice: {e}")

    def _configure_speech_input(self):
        """Configure speech input options."""
        print("\n--- Configure Speech Input ---")

        if not self.speech_input or not self.speech_input.is_available():
            print("Error: Speech input is not available")
            return

        print("\nSpeech Input Settings:")
        print("1. List available microphones")
        print("2. Change microphone")
        print("3. Change maximum recording duration")
        print("4. Back to main menu")

        choice = input("\nEnter your choice (1-4): ")

        if choice == "1":
            # List available microphones
            self.speech_input.list_microphones()

        elif choice == "2":
            # Change microphone
            self.speech_input.list_microphones()
            device_index = input("\nEnter the device index to use: ")

            try:
                device_index = int(device_index)
                self.speech_input.set_device_index(device_index)
                print(f"Microphone changed to device index: {device_index}")
            except ValueError:
                print("Invalid input. Microphone not changed.")

        elif choice == "3":
            # Change maximum recording duration
            duration = input(
                "\nEnter maximum recording duration in seconds (default: 120): ")

            try:
                duration = int(duration)
                if duration > 0:
                    self.speech_input.set_duration(duration)
                    print(
                        f"Maximum recording duration changed to: {duration} seconds")
                else:
                    print("Invalid duration. Must be greater than 0.")
            except ValueError:
                print("Invalid input. Duration not changed.")

        elif choice == "4":
            # Back to main menu
            return

        else:
            print("Invalid choice. Please try again.")

    def _save_posture_metrics(self, metrics):
        """Save posture metrics to the database."""
        if not self.db_manager or not self.current_session_id:
            return

        try:
            # Prepare metrics for database
            db_metrics = {
                "hand_detected": metrics.get("isHandOnScreen", False),
                "hand_detection_duration": metrics.get("handDetectionDuration", 0),
                "not_facing_camera": metrics.get("notFacing", False),
                "not_facing_duration": metrics.get("notFacingDuration", 0),
                "bad_posture_detected": metrics.get("hasBadPosture", False),
                "bad_posture_duration": metrics.get("badPostureDuration", 0)
            }

            # Save to database
            self.db_manager.save_posture_metrics(
                self.current_session_id, db_metrics)
            print("Posture metrics saved to database")
        except Exception as e:
            print(f"Error saving posture metrics: {e}")

    def _analyze_resume(self):
        """Analyze resume and provide detailed recommendations."""
        print("\n--- Resume Analysis ---")

        if not self.resume_data:
            print("No resume data loaded. Processing resume first...")
            self._upload_resume()

            if not self.resume_data:
                print("Error: Unable to load resume data. Analysis canceled.")
                return

        print("\nAnalyzing resume for key insights and recommendations...")

        try:
            # Create a more concise prompt for resume analysis
            prompt = f"""
            Analyze this resume data and provide a concise report:
            
            {json.dumps(self.resume_data, indent=2)}
            
            Include:
            1. STRENGTHS (2-3 points)
            2. IMPROVEMENT AREAS (2-3 points)
            3. QUICK RECOMMENDATIONS (3-4 actionable tips)
            
            Keep the analysis brief and actionable. Focus on the most impactful aspects.
            """

            # Initialize Gemini model
            model = self.ai_client.GenerativeModel('gemini-1.5-flash')

            # Generate analysis
            response = model.generate_content(prompt)

            # Display the analysis
            print("\n=== RESUME ANALYSIS REPORT ===\n")
            print(response.text)

            # Save analysis to file
            ensure_directory("cache/resume_analysis")
            timestamp = int(time.time())
            file_path = f"cache/resume_analysis/analysis_{timestamp}.txt"

            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(response.text)
                print(f"\nAnalysis saved to: {file_path}")
            except Exception as e:
                print(f"Error saving analysis to file: {e}")

        except Exception as e:
            print(f"Error analyzing resume: {e}")

    def _test_tts_audio(self):
        """Test the TTS audio functionality."""
        print("\n--- Test TTS Audio ---")

        if not self.tts_service:
            print("Error: TTS service is not available")
            return

        try:
            success = self.tts_service.test_audio()

            if success:
                print("\nTTS test completed.")
                print("If you didn't hear any audio, check the following:")
                print("1. Make sure your system volume is turned up")
                print("2. Check if your audio devices are properly configured")
                print("3. Try changing the TTS voice using option 6")
            else:
                print("\nTTS test failed. Check error messages above.")
        except Exception as e:
            print(f"Error testing TTS audio: {e}")


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Interview Advisor")
    parser.add_argument("--no-database", action="store_true",
                        help="Disable database functionality")
    return parser.parse_args()


def main(no_database=False):
    """Run the main application."""
    advisor = InterviewAdvisor(no_database=no_database)
    advisor.run()


if __name__ == "__main__":
    args = parse_arguments()
    main(no_database=args.no_database)
