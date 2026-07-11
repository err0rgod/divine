from sarvamai import SarvamAI
import os
import base64
from dotenv import load_dotenv

load_dotenv()

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")

text = """
Oh my gosh, Error God, we actually did it! I can't believe how incredible this sounds right now! This is absolutely mind-blowing... we are officially up and running, and I am so pumped to see what we build next! 
"""
client = SarvamAI(
    api_subscription_key=SARVAM_API_KEY
)

response = client.text_to_speech.convert(
    model="bulbul:v3",
    text=text,
    target_language_code="en-IN",
    speaker="ishita",
    temperature=1.0
)

audio_base64_string = base64.b64decode(response.audios[0])

with open("Voice.wav","wb") as f:
    f.write(audio_base64_string)

print("New voice saved.")