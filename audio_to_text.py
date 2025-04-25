import speech_recognition as sr
import os
import time
import wave
import pyaudio
import argparse
import threading
from datetime import datetime


def list_devices():
    """List all available audio input devices and exit."""
    p = pyaudio.PyAudio()
    print("\nAvailable audio devices:")
    for i in range(p.get_device_count()):
        dev_info = p.get_device_info_by_index(i)
        if dev_info.get('maxInputChannels') > 0:  # Only show input devices
            print(f"{i}: {dev_info.get('name')}")
    p.terminate()
    return True


def record_audio_to_file(output_audio_file=None, max_duration=60, device_index=3):
    """
    Record audio to a WAV file until the user presses Enter.

    Args:
        output_audio_file: Path to save the audio. If None, generates a filename.
        max_duration: Maximum recording duration in seconds
        device_index: The index of the microphone to use

    Returns:
        Path to the audio file
    """
    # List available audio devices
    p = pyaudio.PyAudio()
    print("\nAvailable audio devices:")
    for i in range(p.get_device_count()):
        dev_info = p.get_device_info_by_index(i)
        if dev_info.get('maxInputChannels') > 0:  # Only show input devices
            print(f"{i}: {dev_info.get('name')}")

    # Verify device index is valid
    if device_index >= p.get_device_count():
        print(f"ERROR: Device index {device_index} is out of range!")
        print(f"Please choose a value between 0 and {p.get_device_count()-1}")
        p.terminate()
        return None

    device_info = p.get_device_info_by_index(device_index)
    if device_info.get('maxInputChannels') == 0:
        print(f"ERROR: Device {device_index} has no input channels!")
        p.terminate()
        return None

    print(f"\nUsing microphone: {device_info.get('name')}")

    # If no output file is provided, generate one
    if output_audio_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_audio_file = f"audio_{timestamp}.wav"

    # Audio parameters
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    CHUNK = 1024

    print("\n=== Audio Recorder ===")
    print(f"Recording to file: {output_audio_file}")
    print("Speak your response clearly into the microphone.")
    print("Press Enter to stop recording.")
    print(f"Maximum recording time: {max_duration} seconds")

    # Variables to track recording state
    stop_recording = threading.Event()

    # Function to wait for Enter key
    def wait_for_enter():
        input("Press Enter to stop recording...\n")
        stop_recording.set()

    # Function for timeout
    def timeout_handler():
        time.sleep(max_duration)
        if not stop_recording.is_set():
            print("\nMaximum recording time reached.")
            stop_recording.set()

    # Start thread to wait for Enter key
    enter_thread = threading.Thread(target=wait_for_enter)
    enter_thread.daemon = True
    enter_thread.start()

    # Start timeout thread
    timeout_thread = threading.Thread(target=timeout_handler)
    timeout_thread.daemon = True
    timeout_thread.start()

    # Open audio stream
    try:
        stream = p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        input_device_index=device_index,
                        frames_per_buffer=CHUNK)

        print("Recording started...")

        # Record audio
        frames = []
        while not stop_recording.is_set():
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)

        print("Recording stopped.")

        # Stop and close the stream
        stream.stop_stream()
        stream.close()
        p.terminate()

        # Save the recorded audio to a WAV file
        wf = wave.open(output_audio_file, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()

        print(f"Audio saved to: {output_audio_file}")
        return output_audio_file

    except Exception as e:
        print(f"Error during recording: {e}")
        p.terminate()
        return None


def transcribe_audio_file(audio_file, output_text_file=None):
    """
    Transcribe an audio file to text.

    Args:
        audio_file: Path to the audio file to transcribe
        output_text_file: Path to save the text output. If None, generates a filename.

    Returns:
        Path to the text file containing the transcription
    """
    if not os.path.exists(audio_file):
        print(f"ERROR: Audio file {audio_file} does not exist!")
        return None

    # If no output file is provided, generate one
    if output_text_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_text_file = f"transcript_{timestamp}.txt"

    print("\n=== Transcribing Audio to Text ===")
    print(f"Transcribing: {audio_file}")
    print(f"Output: {output_text_file}")

    r = sr.Recognizer()
    transcribed_text = None
    error_message = None

    try:
        with sr.AudioFile(audio_file) as source:
            # Optional: Adjust for ambient noise - can sometimes help/hurt
            # try:
            #     print("Adjusting for ambient noise...")
            #     r.adjust_for_ambient_noise(source, duration=0.5)
            # except Exception as noise_e:
            #     print(f"Warning: Could not adjust for ambient noise: {noise_e}")

            print("Reading audio data...")
            audio_data = r.record(source)
            print("Audio data read successfully.")

            # --- Attempt Google Web Speech API --- 
            try:
                print("Attempting transcription via Google Web Speech API...")
                text = r.recognize_google(audio_data, language="en-US")
                print("Google API transcription successful!")
                transcribed_text = text
            except sr.UnknownValueError:
                error_message = "Google Web Speech API could not understand the audio."
                print(error_message)
            except sr.RequestError as e:
                error_message = f"Could not request results from Google Web Speech API; {e}"
                print(error_message)
            except Exception as e:
                error_message = f"Unexpected error during Google API transcription: {e}"
                print(error_message)
                import traceback
                traceback.print_exc()
            
            # --- Potential Fallback (Example: Sphinx - requires pocketsphinx package) ---
            # if not transcribed_text:
            #     try:
            #         print("Attempting transcription via CMU Sphinx (Offline)...")
            #         # Requires `pip install pocketsphinx`
            #         text = r.recognize_sphinx(audio_data, language="en-US")
            #         print("Sphinx transcription successful!")
            #         transcribed_text = text
            #     except sr.UnknownValueError:
            #         error_message = "CMU Sphinx could not understand the audio."
            #         print(error_message)
            #     except sr.RequestError as e: # Should not happen for offline
            #         error_message = f"Error with CMU Sphinx; {e}"
            #         print(error_message)
            #     except Exception as e:
            #         error_message = f"Unexpected error during Sphinx transcription: {e}"
            #         print(error_message)
            #         import traceback
            #         traceback.print_exc()

    except ValueError as ve:
         error_message = f"Audio file format error: {ve}. Ensure it is a compatible WAV/AIFF/FLAC."
         print(error_message)
    except Exception as e:
        error_message = f"Error opening or processing audio file {audio_file}: {e}"
        print(error_message)
        import traceback
        traceback.print_exc()

    # Save or return results
    if transcribed_text:
        print("\nTranscription:")
        print("-" * 50)
        print(transcribed_text)
        print("-" * 50)
        try:
            with open(output_text_file, "w", encoding="utf-8") as file:
                file.write(transcribed_text)
            print(f"Transcription saved to: {output_text_file}")
            return output_text_file
        except Exception as e:
            print(f"Error saving transcription to file: {e}")
            # Return None even if transcription worked but saving failed
            return None 
    else:
        print(f"Failed to transcribe audio. Last error: {error_message}")
        # Optionally save the error message to the output file?
        # try:
        #     with open(output_text_file, "w", encoding="utf-8") as file:
        #         file.write(f"Transcription Failed: {error_message}")
        # except Exception as e:
        #     pass # Ignore error saving the error
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Record audio and convert to text")
    parser.add_argument("--audio-output", "-a", type=str,
                        help="Audio output file path (default: auto-generated)")
    parser.add_argument("--text-output", "-t", type=str,
                        help="Text output file path (default: auto-generated)")
    parser.add_argument("--max-duration", "-m", type=int, default=60,
                        help="Maximum recording duration in seconds (default: 60)")
    parser.add_argument("--device", "-d", type=int, default=3,
                        help="Microphone device index (default: 3 for NVIDIA Broadcast)")
    parser.add_argument("--transcribe-only", "-T", type=str,
                        help="Skip recording and only transcribe the specified audio file")
    parser.add_argument("--list-devices-only", "-L", action="store_true",
                        help="Only list available audio devices and exit")

    args = parser.parse_args()

    try:
        # Just list devices if requested
        if args.list_devices_only:
            list_devices()
            return

        if args.transcribe_only:
            # Only transcribe the specified audio file
            output_file = transcribe_audio_file(
                args.transcribe_only, args.text_output)
        else:
            # Record audio to file
            audio_file = record_audio_to_file(
                args.audio_output, args.max_duration, args.device)

            if audio_file:
                # Transcribe audio to text
                output_file = transcribe_audio_file(
                    audio_file, args.text_output)
            else:
                output_file = None

        if output_file:
            print(
                f"\nYou can now use this file with the Interview Advisor by selecting option 3 and entering: {output_file}")

    except KeyboardInterrupt:
        print("\nProgram interrupted by user. Exiting...")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
