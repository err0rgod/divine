import os
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import base64
from sarvamai import AsyncSarvamAI

from Client import chatbot
import tts11
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sarvam_client = AsyncSarvamAI(api_subscription_key=os.getenv("SARVAM_API_KEY"))

class ChatRequest(BaseModel):
    message: str
    language: str = "en"

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        user_message = request.message
        
        print(f"\nCalling Model ({request.language}).......")
        response_text = await asyncio.to_thread(chatbot.getResponse, user_message, request.language)
        
        print(f"\nUser: {user_message}")
        print(f"Assistant: {response_text}")
        
        audio_b64 = None
        mime_type = "audio/mpeg"
        try:
            print("Generating audio with ElevenLabs...")
            audio_bytes = await asyncio.to_thread(tts11.tts, response_text)
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        except Exception as tts_error:
            print(f"ElevenLabs TTS failed: {tts_error}. Falling back to Sarvam TTS...")
            try:
                target_language = "hi-IN" if request.language == "hi" else "en-IN"
                tts_response = await sarvam_client.text_to_speech.convert(
                    text=response_text,
                    target_language_code=target_language,
                    speaker="anushka"
                )
                audio_b64 = tts_response.audios[0]
                mime_type = "audio/wav"
            except Exception as sarvam_error:
                print(f"Sarvam fallback TTS also failed: {sarvam_error}")
        
        return {
            "text": response_text,
            "audioBase64": audio_b64,
            "mimeType": mime_type
        }
    except Exception as e:
        print(f"Server error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/clear")
def clear_chat_endpoint():
    chatbot.clear()
    return {"status": "cleared"}

@app.websocket("/api/stt")
async def stt_endpoint(websocket: WebSocket, lang: str = "en"):
    await websocket.accept()
    
    language_code = "hi-IN" if lang == "hi" else "en-IN"
    
    try:
        async with sarvam_client.speech_to_text_streaming.connect(
            model="saaras:v3",
            mode="transcribe",
            language_code=language_code,
            high_vad_sensitivity=True,
            input_audio_codec="pcm_s16le"
        ) as sarvam_ws:
            
            async def receive_from_client():
                try:
                    while True:
                        message = await websocket.receive()
                        if "bytes" in message:
                            base64_data = base64.b64encode(message["bytes"]).decode("utf-8")
                            await sarvam_ws.transcribe(
                                audio=base64_data,
                                encoding="pcm_s16le",
                                sample_rate=16000
                            )
                        elif "text" in message and message["text"] == "STOP":
                            await sarvam_ws.flush()
                            # Do not break here, wait for sarvam to send the final response
                except WebSocketDisconnect:
                    pass
                except Exception as e:
                    print(f"Client to Sarvam error: {e}")
            
            async def receive_from_sarvam():
                try:
                    while True:
                        response = await sarvam_ws.recv()
                        if response:
                            is_final = getattr(response.data, 'is_final', False)
                            transcript = getattr(response.data, 'transcript', '').strip()
                            
                            # Print to Render logs for debugging!
                            print(f"Sarvam STT: transcript='{transcript}', is_final={is_final}")
                            
                            if transcript:
                                await websocket.send_json({
                                    "is_final": is_final,
                                    "transcript": transcript
                                })
                except Exception as e:
                    print(f"Sarvam to Client error: {e}")
                    
            client_task = asyncio.create_task(receive_from_client())
            sarvam_task = asyncio.create_task(receive_from_sarvam())
            
            done, pending = await asyncio.wait(
                [client_task, sarvam_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            for p in pending:
                p.cancel()
                
    except Exception as e:
        print(f"WebSocket Error: {e}")
    finally:
        try:
            await websocket.close()
        except:
            pass

# Mount frontend/dist directory if it exists
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'dist')

if os.path.isdir(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
else:
    @app.get("/")
    def read_root():
        return {"message": "Frontend build not found. Please run 'npm run build' in the frontend directory."}

if __name__ == "__main__":
    import uvicorn
    # Make sure to bind to 0.0.0.0 and PORT env variable for Render
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
