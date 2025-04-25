import os
import time
import requests
import subprocess
from typing import Optional, List
import platform
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import pygame for silent audio playback
try:
    import pygame
    PYGAME_AVAILABLE = True
    # Initialize pygame mixer
    pygame.mixer.init()
except ImportError:
    PYGAME_AVAILABLE = False
    print("Warning: pygame not available. Using fallback methods.")


class TTSService:
    def __init__(self, silent_mode=False):
        """Initialize the TTS service with ElevenLabs API.

        Args:
            silent_mode: If True, suppresses error messages (useful for presentations)
        """
        self.silent_mode = silent_mode
        # Use the directly provided API key instead of environment variable
        self.api_key = os.getenv("ELEVENLABS_API")
        if not self.api_key:
            raise ValueError("ELEVENLABS_API environment variable not set.")

        self.cache_dir = "cache/audio"

        # Create cache directory
        os.makedirs(self.cache_dir, exist_ok=True)

        # ElevenLabs API base URL
        self.base_url = "https://api.elevenlabs.io/v1"

        # Set up headers for API requests
        self.headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        # Get available voices
        self.available_voices = self._get_voices()

        # Set default voice to Roger if available, otherwise use the first voice
        self.current_voice = None
        if self.available_voices:
            # Try to find Roger
            roger_voices = [
                v for v in self.available_voices if v["name"] == "Roger"]

            if roger_voices:
                self.current_voice = roger_voices[0]
                self._log("Default voice set to: Roger")
            else:
                # If Roger not found, use the first available voice
                self.current_voice = self.available_voices[0]
                self._log(
                    f"Voice 'Roger' not found. Default voice set to: {self.current_voice['name']}")
        else:
            self._log_error(
                "No voices available from the API. Check your API key and internet connection.")

        self._log("ElevenLabs TTS service initialized successfully")

    def _log(self, message):
        """Log a message only if not in silent mode."""
        if not self.silent_mode:
            print(message)

    def _log_error(self, message):
        """Always log error messages, even in silent mode."""
        print(f"Error: {message}")

    def _get_voices(self) -> List[dict]:
        """Get available voices directly from the ElevenLabs API."""
        try:
            url = f"{self.base_url}/voices"
            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                voices_data = response.json()
                return voices_data.get("voices", [])
            else:
                error_msg = f"Error fetching voices: {response.status_code} - {response.text}"
                self._log_error(error_msg)
                return []
        except requests.exceptions.Timeout:
            self._log_error("Timeout while connecting to ElevenLabs API")
            return []
        except requests.exceptions.ConnectionError:
            self._log_error(
                "Connection error while connecting to ElevenLabs API")
            return []
        except Exception as e:
            self._log_error(f"Error fetching voices: {e}")
            return []

    def get_voice_names(self) -> List[str]:
        """Get list of available voice names."""
        try:
            if not self.available_voices:
                self.available_voices = self._get_voices()

            return [voice["name"] for voice in self.available_voices]
        except Exception as e:
            self._log_error(f"Error getting voice names: {e}")
            return []

    def get_available_voices(self) -> List[str]:
        """Alias for get_voice_names - get list of available voice names."""
        return self.get_voice_names()

    def set_voice(self, voice_name: str) -> bool:
        """Set the current voice by name."""
        try:
            voice_names = self.get_voice_names()

            if not voice_names:
                self._log_error("No voices available")
                return False

            matching_voices = [
                v for v in self.available_voices if v["name"] == voice_name]

            if matching_voices:
                self.current_voice = matching_voices[0]
                self._log(f"Voice changed to '{voice_name}'")
                return True

            # If requested voice not found, use first available
            self._log(
                f"Voice '{voice_name}' not found. Using '{self.available_voices[0]['name']}' instead.")
            self.current_voice = self.available_voices[0]
            return False
        except Exception as e:
            self._log_error(f"Error setting voice: {e}")
            return False

    def text_to_speech(self, text: str, play_audio: bool = True) -> Optional[str]:
        """Convert text to speech using ElevenLabs API directly."""
        if not text or len(text.strip()) == 0:
            self._log_error("Empty text provided for TTS")
            return None

        if not self.current_voice:
            self._log_error("No voice selected")
            return None

        # Print information about the current process
        print(f"Generating speech for text (length: {len(text)})")
        print(f"Using voice: {self.current_voice.get('name', 'Unknown')}")

        # Create output file path with timestamp to prevent conflicts
        timestamp = int(time.time())
        temp_file = os.path.join(self.cache_dir, f"tts_{timestamp}.mp3")

        try:
            # Prepare API endpoint
            voice_id = self.current_voice["voice_id"]
            url = f"{self.base_url}/text-to-speech/{voice_id}?output_format=mp3_44100_128"

            # Prepare payload
            payload = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                    "style": 0.0,
                    "use_speaker_boost": True
                }
            }

            print("Sending request to ElevenLabs API...")

            # Send request to ElevenLabs API
            response = requests.post(
                url, headers=self.headers, json=payload, timeout=30)

            print(f"Response status code: {response.status_code}")

            # Check if the request was successful
            if response.status_code == 200:
                # Write the audio content to the file
                with open(temp_file, 'wb') as file:
                    file.write(response.content)
                print(f"Audio generated successfully and saved to {temp_file}")

                # Play the audio if requested
                if play_audio:
                    self._play_audio(temp_file)

                # Clean up old files
                self.cleanup_cache()

                return temp_file
            else:
                self._log_error(
                    f"Error generating speech: {response.status_code} - {response.text}")
                return None

        except requests.exceptions.Timeout:
            self._log_error("Timeout while connecting to ElevenLabs API")
            return None
        except requests.exceptions.ConnectionError:
            self._log_error(
                "Connection error while connecting to ElevenLabs API")
            return None
        except Exception as e:
            self._log_error(f"Error generating speech: {e}")
            return None

    def _play_audio(self, audio_file: str) -> None:
        """Play audio file silently in background without UI."""
        if not os.path.exists(audio_file):
            self._log_error(f"Audio file not found: {audio_file}")
            return

        print(f"Playing audio silently: {audio_file}")

        # Try pygame first (completely UI-less)
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.music.load(audio_file)
                pygame.mixer.music.play()
                print("Playing with pygame (no UI)")
                return
            except Exception as e:
                print(f"Pygame playback error: {e}")

        # Fallback methods if pygame fails
        try:
            # Windows-specific approach
            if platform.system() == 'Windows':
                # Use hidden PowerShell command
                cmd = f'powershell -WindowStyle Hidden -Command "(New-Object Media.SoundPlayer \'{audio_file}\').PlaySync();"'
                subprocess.Popen(cmd, shell=True,
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL,
                                 creationflags=subprocess.CREATE_NO_WINDOW)
                print("Playing with hidden PowerShell")
            # macOS approach
            elif platform.system() == 'Darwin':
                subprocess.Popen(['afplay', audio_file],
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
                print("Playing with afplay")
            # Linux approach
            elif platform.system() == 'Linux':
                subprocess.Popen(['aplay', audio_file],
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
                print("Playing with aplay")
            else:
                self._log_error(f"Unsupported platform: {platform.system()}")
        except Exception as e:
            self._log_error(f"Audio playback error: {e}")

    def cleanup_cache(self, max_files: int = 20) -> None:
        """Clean up old cached audio files."""
        try:
            if not os.path.exists(self.cache_dir):
                return

            files = os.listdir(self.cache_dir)
            audio_files = [os.path.join(self.cache_dir, f)
                           for f in files if f.endswith('.mp3')]

            # Sort by modification time (oldest first)
            audio_files.sort(key=lambda x: os.path.getmtime(x))

            # Remove oldest files if there are too many
            if len(audio_files) > max_files:
                for file_path in audio_files[:-max_files]:
                    try:
                        os.remove(file_path)
                    except Exception:
                        # Silently continue if a file can't be deleted
                        pass

        except Exception as e:
            self._log_error(f"Error cleaning up cache: {e}")

    def test_audio(self) -> bool:
        """Test audio generation and playback with a short text sample.

        Returns:
            bool: True if successful, False otherwise
        """
        print("\n=== Testing TTS Audio ===")
        print("Generating a test audio file...")

        test_text = "This is a test of the speech system. If you can hear this, audio is working correctly."

        try:
            audio_file = self.text_to_speech(test_text, play_audio=True)
            if audio_file:
                print("Test completed. Check if you heard the audio message.")
                return True
            else:
                print("Failed to generate test audio.")
                return False
        except Exception as e:
            print(f"Error during audio test: {e}")
            return False
