from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional
import sys
import os
import shutil
import asyncio

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.orchestrator import engine
import engine.agent_tools as agent_tools

app = FastAPI()
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

class ChatRequest(BaseModel):
    chat_id: str
    provider: str
    model: str
    prompt: str
    history: List[dict]
    files: Optional[List[str]] = []
    loop: Optional[bool] = False

# Global log store for real-time Agent Loop UI updates
agent_logs = {}

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

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    uploads_dir = agent_tools.UPLOADS_DIR
    filepath = os.path.join(uploads_dir, file.filename)
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"success": True, "filename": file.filename, "filepath": filepath}

@app.get("/api/logs/{chat_id}")
async def get_logs(chat_id: str):
    if chat_id in agent_logs:
        logs = agent_logs[chat_id]
        agent_logs[chat_id] = [] # Clear fetched logs
        return {"logs": logs}
    return {"logs": []}

@app.post("/api/chat")
async def process_chat(req: ChatRequest):
    chat_id = req.chat_id
    if chat_id not in agent_logs:
        agent_logs[chat_id] = []

    # Inject Memory
    memory_context = agent_tools.load_memory()
    sys_prompt = "You are Divine, an advanced AI Agent."
    if memory_context:
        sys_prompt += f"\n\nHere is your long-term persistent memory:\n{memory_context}"
        
    # Inject File Contents
    file_context = ""
    for filepath in req.files:
        if os.path.exists(filepath):
            agent_logs[chat_id].append(f"> Parsing attached file: {os.path.basename(filepath)}...")
            content = agent_tools.extract_file_content(filepath, is_multimodal_model=False)
            file_context += f"\n\n[Attached File: {os.path.basename(filepath)}]\n{content}\n"
    
    if file_context:
        sys_prompt += f"\n\nContext Files provided by user:\n{file_context}"
        
    sys_prompt += """
    
SUPERPOWERS (Tools):
CRITICAL: You DO have access to the live internet and local file system. Do NOT ever apologize or say you cannot browse the web or run code. If you need information, you MUST use the tools below. To use a tool, strictly output its XML tag in your response.

1. Web Search: <search_web>query</search_web> (Use this aggressively for any real-time, unknown, or specific information!)
2. Read URL: <read_url>https://example.com</read_url> (Use this to scrape and read the direct content of a specific URL link provided by the user)
3. Run Terminal Command: <execute_cmd>command</execute_cmd>
4. Create File: <create_file path="/path/to/file">code</create_file>
5. Save Memory: <save_memory>fact</save_memory>
"""

    # Clean up history to ensure only 'role' and 'content' are sent to the API
    messages = [{"role": msg["role"], "content": msg["content"]} for msg in req.history]
    
    # Prepend System Prompt
    messages.insert(0, {"role": "system", "content": sys_prompt})
    
    messages.append({"role": "user", "content": req.prompt})

    provider = req.provider
    model = req.model

    auto_selected = False
    if provider == "Auto-Select":
        provider, model = engine.auto_route(messages)
        auto_selected = True

    max_loops = 5 if req.loop else 1
    loop_count = 0
    final_reply = ""
    usage_total = {"total_tokens": 0}
    failover_occurred = False
    original_provider = ""

    while loop_count < max_loops:
        loop_count += 1
        agent_logs[chat_id].append(f"> Generating response (Iteration {loop_count})...")
        
        response = engine.chat(provider_name=provider, model_name=model, messages=messages)
        
        if not response["success"]:
            return {"success": False, "error": response["error"]}
            
        reply_content = response["content"]
        if response.get("usage", {}).get("total_tokens"):
            usage_total["total_tokens"] += response["usage"]["total_tokens"]
        if response.get("failover_occurred"):
            failover_occurred = True
            original_provider = response.get("original_provider")
            
        messages.append({"role": "assistant", "content": reply_content})
        
        # Parse and execute tools
        tool_results = agent_tools.parse_and_execute_tags(reply_content)
        
        if tool_results:
            agent_logs[chat_id].append("> Tool execution detected...")
            observation_text = "Tool Execution Results:\n"
            for k, v in tool_results.items():
                agent_logs[chat_id].append(f"  - {k}")
                observation_text += f"[{k}]\n{v}\n\n"
            
            if req.loop:
                messages.append({"role": "user", "content": observation_text})
                agent_logs[chat_id].append("> Re-evaluating based on tool results...")
                continue # Loop again
            else:
                final_reply = reply_content + "\n\n" + observation_text
                break
        else:
            final_reply = reply_content
            break

    return {
        "success": True,
        "reply": final_reply,
        "provider_used": provider,
        "model_used": model,
        "auto_selected": auto_selected,
        "failover_occurred": failover_occurred,
        "original_provider": original_provider,
        "usage": usage_total
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

from engine.state_manager import state_manager

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/api/dashboard/stats")
async def get_dashboard_stats():
    return JSONResponse(content=state_manager.get_stats())

@app.get("/api/dashboard/keys")
async def get_dashboard_keys():
    return JSONResponse(content=state_manager.get_keys())

@app.post("/api/dashboard/keys")
async def update_dashboard_keys(req: Request):
    keys_dict = await req.json()
    state_manager.update_keys(keys_dict)
    return {"success": True}

@app.post("/api/dashboard/keys/test")
async def test_dashboard_keys(req: Request):
    data = await req.json()
    provider = data.get("provider")
    test_key = data.get("key") # Get the specific key to test
    
    if not test_key:
        return {"success": False, "error": "No key provided to test"}

    # Just run a quick deterministic chat through the orchestrator to test this key
    messages = [{"role": "user", "content": "Reply with 'OK' and nothing else."}]
    
    try:
        fallback_models = {
            "Groq": "llama-3.1-8b-instant",
            "Mistral": "mistral-large-latest",
            "Cerebras": "llama3.1-8b",
            "NVIDIA": "meta/llama-3.1-8b-instruct",
            "Bazaarlink": "auto:free",
            "Cohere": "command-r-08-2024",
            "Bluesmind": "meta/llama-3.1-8b-instruct",
            "AgentRouter": "gpt 5.5",
            "ForgeAI": "gpt-5.5",
            "DeepSeek": "deepseek-v4-flash"
        }
        
        test_model = fallback_models.get(provider, "test-model")
        
        # Test it directly without failover and using the explicit test_key
        response = engine.chat(provider_name=provider, model_name=test_model, messages=messages, max_tokens=10, auto_failover=False, test_key=test_key)
        return {"success": response.get("success", False), "error": response.get("error", "Unknown Error")}
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=5000, reload=True)
