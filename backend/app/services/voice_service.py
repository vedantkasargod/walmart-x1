import os
import logging
import requests  # We will use the standard requests library
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv
import threading

load_dotenv()
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
RACHEL_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"

def text_to_speech_stream(text: str):
    """Generates speech using the ElevenLabs client and returns the audio stream."""
    logging.info(f"Generating speech for text: '{text}'")
    try:
        audio_stream = client.text_to_speech.convert(
            voice_id=RACHEL_VOICE_ID, text=text, model_id="eleven_multilingual_v2")
        return audio_stream
    except Exception as e:
        logging.error(f"ElevenLabs TTS error: {e}")
        raise e


def speech_to_text_http(audio_bytes: bytes) -> str:
    """
    Transcribes audio by sending a direct POST request to the ElevenLabs API,
    including all required fields like the model_id.
    """
    logging.info(f"Transcribing audio of size {len(audio_bytes)} bytes using direct HTTP request.")
    
    # The URL for the ElevenLabs Speech-to-Text API
    stt_url = "https://api.elevenlabs.io/v1/speech-to-text"
    
    # The required headers for authentication
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY
    }
    
    # --- START OF THE FIX ---
    # The data payload for the multipart form, including the required model_id.
    data = {
        'model_id': 'scribe_v1',
        'language_code':'eng'
    }
    
    # The files payload for the multipart form.
    files = {
        'file': ('user_audio.webm', audio_bytes, 'audio/webm')
    }
    # --- END OF THE FIX ---
    
    try:
        # Make the POST request with headers, data, AND files.
        response = requests.post(stt_url, headers=headers, data=data, files=files, timeout=30)
        
        # Check for a successful response.
        response.raise_for_status()
        
        # Parse the JSON response and extract the transcript.
        response_json = response.json()
        transcript = response_json.get("text", "")
        
        logging.info(f"ElevenLabs HTTP STT successful. Transcript: '{transcript}'")
        return transcript

    except requests.exceptions.HTTPError as http_err:
        # This will now give us a very clear error message from the API if something is wrong.
        logging.error(f"HTTP error occurred: {http_err} - Response: {http_err.response.text}")
        return ""
    except Exception as e:
        logging.error(f"An unexpected error occurred during transcription: {e}")
        return ""