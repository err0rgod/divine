from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.orchestrator import engine

app = FastAPI()
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

class ChatRequest(BaseModel):
    provider: str
    model: str
    prompt: str
    history: List[dict]

import json

def load_verified_models():
    """Dynamically parses models.json to ensure only verified, online models are selectable."""
    try:
        with open("models.json", "r", encoding="utf-8") as f:
            providers_map = json.load(f)
    except Exception as e:
        print(f"Error loading models.json: {e}")
        # Ultimate fallback
        providers_map = {
            "Auto-Select": ["Divine (Meta-Router)"],
            "Mistral": ["codestral-latest", "mistral-large-latest"]
        }
        
    return providers_map

# Load dynamically on startup
UI_PROVIDERS = load_verified_models()

@app.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    # Reload models on page refresh so it's always up to date if models.txt changes
    latest_providers = load_verified_models()
    return templates.TemplateResponse("index.html", {"request": request, "providers": latest_providers})

@app.get("/api/providers")
async def get_providers():
    return JSONResponse(content=load_verified_models())

@app.post("/api/chat")
async def process_chat(req: ChatRequest):
    # Clean up history to ensure only 'role' and 'content' are sent to the API
    messages = [{"role": msg["role"], "content": msg["content"]} for msg in req.history]
    messages.append({"role": "user", "content": req.prompt})

    provider = req.provider
    model = req.model

    auto_selected = False
    
    if provider == "Auto-Select":
        provider, model = engine.auto_route(messages)
        auto_selected = True

    response = engine.chat(provider_name=provider, model_name=model, messages=messages)
    
    if response["success"]:
        return {
            "success": True,
            "reply": response["content"],
            "provider_used": response["provider"],
            "model_used": response["model"],
            "auto_selected": auto_selected,
            "failover_occurred": response.get("failover_occurred", False),
            "original_provider": response.get("original_provider", ""),
            "usage": response.get("usage", {})
        }
    else:
        return {
            "success": False,
            "error": response["error"]
        }

CONTEXT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "context")
CHATS_DIR = os.path.join(CONTEXT_DIR, "chats")
os.makedirs(CHATS_DIR, exist_ok=True)

# Legacy migration
legacy_file = os.path.join(CONTEXT_DIR, "chats.json")
if os.path.exists(legacy_file):
    try:
        with open(legacy_file, "r", encoding="utf-8") as f:
            legacy_chats = json.load(f)
        for chat in legacy_chats:
            chat_id = chat.get("id")
            if chat_id:
                with open(os.path.join(CHATS_DIR, f"{chat_id}.json"), "w", encoding="utf-8") as f2:
                    json.dump(chat, f2, indent=4)
        os.remove(legacy_file)
    except Exception as e:
        print(f"Migration error: {e}")

@app.get("/api/history")
async def get_history():
    chats = []
    try:
        for filename in os.listdir(CHATS_DIR):
            if filename.endswith(".json"):
                with open(os.path.join(CHATS_DIR, filename), "r", encoding="utf-8") as f:
                    chats.append(json.load(f))
    except Exception as e:
        print(f"Error loading chats: {e}")
    return JSONResponse(content=chats)

@app.post("/api/history/{chat_id}")
async def save_history(chat_id: str, req: Request):
    try:
        chat_data = await req.json()
        filepath = os.path.join(CHATS_DIR, f"{chat_id}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(chat_data, f, indent=4)
        return {"success": True}
    except Exception as e:
        print(f"Error saving chat {chat_id}: {e}")
        return {"success": False, "error": str(e)}

@app.delete("/api/history/{chat_id}")
async def delete_history(chat_id: str):
    try:
        filepath = os.path.join(CHATS_DIR, f"{chat_id}.json")
        if os.path.exists(filepath):
            os.remove(filepath)
        return {"success": True}
    except Exception as e:
        print(f"Error deleting chat {chat_id}: {e}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=5000, reload=True)
