from elevenlabs import VoiceSettings
import os

from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv
from Client import generate_voicesettings

load_dotenv()

client = ElevenLabs(api_key=os.getenv("ELEVEN_LABS_API"))

def tts(prompt : str):
    audio_generator = client.text_to_speech.convert(
        text=prompt,
        voice_id="EXAVITQu4vr4xnSDxMaL",
        model_id="eleven_v3",
        voice_settings=generate_voicesettings(prompt)
    )
    
    # Read the generator into bytes
    audio_bytes = b"".join(audio_generator)
    return audio_bytes
