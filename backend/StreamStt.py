import asyncio
from sarvamai import AsyncSarvamAI
import pyaudio
import os 
import base64
import tts11
from dotenv import load_dotenv
from Client import Chatbot

# creating a instance of Chatbot from client
chatbot = Chatbot()
load_dotenv()

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")

# specifying audio capture params for pyaudio 
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1024

client = AsyncSarvamAI(api_subscription_key=SARVAM_API_KEY)


async def mic_streamer(ws, p, stream ):
    # continously record audio and stream to api key
    print("Mic is LIve speak....")
    try:
        while True:
            # converting raw audio stream to base64 encoded ones
            raw_data  = stream.read(CHUNK, exception_on_overflow=False)
            base64_data = base64.b64encode(raw_data).decode("utf-8")
            await ws.transcribe(
                audio= base64_data,
                encoding = "audio/wav",
                sample_rate = RATE
            )
            await asyncio.sleep(0.01)
    except Exception as e:
        print(f"MIC problem : {e}")

conversation_task = None
assistant_speaking = False

async def handle_conversation(transcript):
    global assistant_speaking
    try:
        assistant_speaking = True
        print("\nCalling Model.......")
        responseText = await asyncio.to_thread(chatbot.getResponse, transcript)
        print(f"\nUser: {transcript}")
        print(f"Assistant: {responseText}")
        
        await asyncio.to_thread(tts11.tts, responseText)
    except Exception as e:
        print(f"Conversation error: {e}")
    finally:
        assistant_speaking = False
        print("\n Speak.....")

# websocket receiver 
async def text_receiver(ws):
    global conversation_task, assistant_speaking
    # cont listen and transcribe from sarvam
    try:
        while True:
            response = await ws.recv()
            
            if assistant_speaking:
                continue
                
            if response:
                is_final = getattr(response.data, 'is_final', False)
                if not is_final:
                    continue
                
                transcript = getattr(response.data, 'transcript', '').strip()
                if not transcript:
                    continue

                if conversation_task and not conversation_task.done():
                    continue

                conversation_task = asyncio.create_task(handle_conversation(transcript))

    except Exception as e:
        print(f"receiver error: {e}")

# main async func handler to gather stream and receive
async def main():
    p = pyaudio.PyAudio()
    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )

    async with client.speech_to_text_streaming.connect(
        model="saaras:v3",
        mode="transcribe",
        language_code="en-IN",
        high_vad_sensitivity=True
    ) as ws:
        stream_task = asyncio.create_task(mic_streamer(ws,p,stream))
        receive_task =  asyncio.create_task(text_receiver(ws))

        try:
            await asyncio.gather(stream_task, receive_task)
        except KeyboardInterrupt:
            print("\n Stopping live stream.")
        finally:
            stream_task.cancel()
            receive_task.cancel()
            stream.start_stream()
            stream.close()
            p.terminate()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram exited cleanly.")