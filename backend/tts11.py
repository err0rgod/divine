from elevenlabs import VoiceSettings
import os
from elevenlabs.play import play
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv
from Client import generate_voicesettings

load_dotenv()

client = ElevenLabs(api_key=os.getenv("ELEVEN_LABS_API"))

def tts(prompt : str):
    audio = client.text_to_speech.convert(
        text=prompt,
        voice_id="EXAVITQu4vr4xnSDxMaL",
        model_id="eleven_v3",
        voice_settings=generate_voicesettings(prompt)
    )
    # play the converted speech using elevenlabs play func
    play(audio)