import os
import sys
import time
import subprocess
import tempfile
from typing import Optional


class SpeechInput:
    """
    Handles speech input for the Interview Advisor application.
    This class integrates with the audio_to_text.py script to capture
    spoken answers from the user.
    """

    def __init__(self, audio_script_path: str = "audio_to_text.py"):
        """
        Initialize the speech input integration.

        Args:
            audio_script_path: Path to the audio_to_text.py script
        """
        self.audio_script_path = audio_script_path
        # Default microphone index (NVIDIA Broadcast)
        self.default_device_index = 3
        self.duration = 120  # Default maximum recording duration (2 minutes)

        # Check if the audio script exists
        if not os.path.exists(self.audio_script_path):
            print(
                f"WARNING: Audio script not found at {self.audio_script_path}")
            print("Speech input will not be available")
            self.available = False
        else:
            self.available = True

    def is_available(self) -> bool:
        """Check if speech input is available."""
        return self.available

    def capture_speech(self, output_file: Optional[str] = None) -> Optional[str]:
        """
        Capture speech input from the user and convert it to text.

        Args:
            output_file: Optional path to save the text output

        Returns:
            Path to the text file containing the transcription, or None if failed
        """
        if not self.available:
            print("Speech input is not available")
            return None

        try:
            # Generate a temporary file name if not provided
            if output_file is None:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                output_file = f"answer_{timestamp}.txt"

            print("\n=== Speech Input Mode ===")
            print("Recording will start in 3 seconds...")
            print("Speak clearly into your microphone.")
            print("Press Enter when you're done speaking.")
            print(f"Maximum recording time: {self.duration} seconds")

            # Countdown
            for i in range(3, 0, -1):
                print(f"{i}...")
                time.sleep(1)

            # Build command
            cmd = [
                sys.executable,  # Current Python interpreter
                self.audio_script_path,
                "--text-output", output_file,
                "--max-duration", str(self.duration),
                "--device", str(self.default_device_index)
            ]

            # Run the audio_to_text.py script
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # Wait for the process to complete
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                print(f"Error recording speech: {stderr}")
                return None

            # Check if output file was created
            if not os.path.exists(output_file):
                print("Error: Output file was not created")
                return None

            print(
                f"\nSpeech successfully converted to text and saved to: {output_file}")
            return output_file

        except Exception as e:
            print(f"Error capturing speech: {e}")
            return None

    def set_device_index(self, device_index: int) -> None:
        """Set the microphone device index."""
        self.default_device_index = device_index

    def set_duration(self, duration: int) -> None:
        """Set the maximum recording duration in seconds."""
        self.duration = duration

    def list_microphones(self) -> None:
        """List available microphones."""
        try:
            cmd = [
                sys.executable,
                self.audio_script_path,
                "--list-devices-only"
            ]

            subprocess.run(cmd)
        except Exception as e:
            print(f"Error listing microphones: {e}")

    def transcribe_file(self, audio_file):
        """Transcribe an audio file."""
        try:
            # Call audio_to_text.py with transcribe-only option
            from ..audio_to_text import transcribe_audio_file

            transcript_file = transcribe_audio_file(audio_file)
            if transcript_file:
                # Read the transcript from the file
                with open(transcript_file, 'r', encoding='utf-8') as f:
                    transcript = f.read()
                return transcript
            return None
        except Exception as e:
            print(f"Error transcribing audio file: {e}")
            return None

    def analyze_fluency(self, audio_file):
        """Analyze speech fluency from an audio file."""
        try:
            # Import speech fluency analyzer
            sys.path.append("Aurdio speech")
            try:
                from speech_fluency_analyzer import analyze_speech_fluency
            except ImportError:
                print("Warning: Could not import speech_fluency_analyzer")
                return None

            # Analyze the audio file
            analysis = analyze_speech_fluency(audio_file, verbose=True)

            return analysis
        except Exception as e:
            print(f"Error analyzing speech fluency: {e}")
            return None
