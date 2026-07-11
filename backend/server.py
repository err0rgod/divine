import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio

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

class ChatRequest(BaseModel):
    message: str

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        user_message = request.message
        
        print("\nCalling Model.......")
        response_text = await asyncio.to_thread(chatbot.getResponse, user_message)
        
        print(f"\nUser: {user_message}")
        print(f"Assistant: {response_text}")
        
        # Get audio bytes from ElevenLabs
        print("Generating audio...")
        audio_bytes = await asyncio.to_thread(tts11.tts, response_text)
        
        return Response(
            content=audio_bytes, 
            media_type="audio/mpeg",
            headers={
                "X-Response-Text": response_text.replace("\n", " ").replace("\r", "")
            }
        )
    except Exception as e:
        print(f"Server error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
