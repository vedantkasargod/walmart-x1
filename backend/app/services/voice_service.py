# file: backend/app/services/voice_service.py
import os
import logging
from elevenlabs.client import ElevenLabs

from dotenv import load_dotenv

load_dotenv()

# --- Initialize the ElevenLabs Client ---
try:
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
    if not ELEVENLABS_API_KEY:
        raise ValueError("ElevenLabs API key not found in environment variables.")
    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    logging.info("ElevenLabs client initialized successfully.")
except Exception as e:
    logging.error(f"Failed to initialize ElevenLabs client: {e}")
    client = None

# --- Define our chosen voice ---
RACHEL_VOICE_ID = "kdmDKE6EkgrWrrykO9Qt"



def text_to_speech_stream(text: str):
    """
    Takes text and returns a raw audio generator from ElevenLabs.
    """
    if not client:
        raise ConnectionError("ElevenLabs client is not available.")
    
    logging.info(f"Generating speech for text: '{text}'")
    try:
        # This creates a generator that yields audio chunks as they are generated.
        audio_stream_generator = client.text_to_speech.convert(
            voice_id=RACHEL_VOICE_ID,
            text=text,
            model_id="eleven_multilingual_v2",
        )
        
        # --- THE FIX ---
        # Return the raw generator directly. Do not use the stream() helper.
        return audio_stream_generator
        # --- END OF FIX ---

    except Exception as e:
        logging.error(f"ElevenLabs TTS error: {e}")
        raise e 