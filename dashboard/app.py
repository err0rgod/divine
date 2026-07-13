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
templates = Jinja2Templates(directory="dashboard/templates")

class ChatRequest(BaseModel):
    provider: str
    model: str
    prompt: str
    history: List[dict]

def load_verified_models():
    """Dynamically parses models.txt to ensure only verified, online models are selectable."""
    providers_map = {"Auto-Select": ["Divine (Meta-Router)"]}
    try:
        with open("models.txt", "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        current_provider = None
        for line in lines:
            if line.startswith("PROVIDER:"):
                current_provider = line.split("PROVIDER:")[1].strip()
                if current_provider == "Mistral AI": current_provider = "Mistral"
                if current_provider == "Bazaarlink.ai": current_provider = "Bazaarlink"
                if current_provider == "Google AI Studio": current_provider = "Google"
                providers_map[current_provider] = []
            elif line.strip().startswith("-") and current_provider:
                model_name = line.replace("-", "").strip()
                providers_map[current_provider].append(model_name)
    except Exception as e:
        print(f"Error loading models.txt: {e}")
        # Ultimate fallback
        providers_map["Mistral"] = ["codestral-latest", "mistral-large-latest"]
        
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
    messages = req.history.copy()
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
