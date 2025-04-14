"""
Text-to-Speech Service for the Interview Advisor application
"""

import os
import time
from typing import Optional, List


class TTSService:
    def __init__(self, silent_mode=False):
        """Initialize the TTS service."""
        self.silent_mode = silent_mode
        self.cache_dir = "cache/audio"
        os.makedirs(self.cache_dir, exist_ok=True)
        print("TTS service initialized")

    def text_to_speech(self, text: str, play_audio: bool = True) -> Optional[str]:
        """Convert text to speech (simplified mock implementation)."""
        if not self.silent_mode:
            print(f"TTS would say: {text}")
        return None

    def set_voice(self, voice_name: str) -> bool:
        """Set the voice (mock implementation)."""
        print(f"Voice set to: {voice_name}")
        return True

    def get_voice_names(self) -> List[str]:
        """Get list of available voice names (mock implementation)."""
        return ["Voice 1", "Voice 2", "Voice 3"]

    def get_available_voices(self) -> List[str]:
        """Alias for get_voice_names."""
        return self.get_voice_names()

    def test_audio(self) -> bool:
        """Test audio generation and playback (mock implementation)."""
        print("Audio test successful")
        return True
