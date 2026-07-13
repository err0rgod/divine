from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional
import sys
import os

# Add the root directory to path so we can import engine
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.orchestrator import engine

app = FastAPI()

# We will serve templates directly for the stunning UI
templates = Jinja2Templates(directory="dashboard/templates")

class ChatRequest(BaseModel):
    provider: str
    model: str
    prompt: str
    history: List[dict]

# Hardcoded quick list of top models for the UI dropdown
UI_PROVIDERS = {
    "Auto-Select": ["Omni-Route (Meta-Router)"],
    "Mistral": ["codestral-latest", "mistral-large-latest", "open-mistral-nemo"],
    "Groq": ["llama-3.1-8b-instant", "llama-3.3-70b-versatile", "mixtral-8x7b-32768"],
    "Cerebras": ["llama3.1-8b", "llama3.1-70b"],
    "NVIDIA": ["meta/llama-3.1-70b-instruct", "meta/llama-3.1-405b-instruct"],
    "Cohere": ["command-r-plus-08-2024", "command-r-08-2024"],
    "Bazaarlink": ["auto:free"],
    "Google": ["gemini-1.5-pro", "gemini-1.5-flash"],
    "OpenRouter": ["anthropic/claude-3.5-sonnet", "google/gemini-pro"]
}

@app.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "providers": UI_PROVIDERS})

@app.get("/api/providers")
async def get_providers():
    return JSONResponse(content=UI_PROVIDERS)

@app.post("/api/chat")
async def process_chat(req: ChatRequest):
    messages = req.history.copy()
    messages.append({"role": "user", "content": req.prompt})

    provider = req.provider
    model = req.model

    auto_selected = False
    
    # Trigger Meta-Router if Auto-Select is chosen
    if provider == "Auto-Select":
        provider, model = engine.auto_route(messages)
        auto_selected = True

    response = engine.chat(provider_name=provider, model_name=model, messages=messages)
    
    if response["success"]:
        return {
            "success": True,
            "reply": response["content"],
            "provider_used": provider,
            "model_used": model,
            "auto_selected": auto_selected,
            "usage": response.get("usage", {})
        }
    else:
        return {
            "success": False,
            "error": response["error"]
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=5000, reload=True)
