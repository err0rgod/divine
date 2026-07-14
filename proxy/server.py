import os
import sys
import json
import requests
import random
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.orchestrator import engine, PROVIDERS
from engine.state_manager import state_manager

app = FastAPI(title="Divine Universal Proxy Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def load_proxy_config():
    try:
        with open("D:/divine/config/proxy_config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"aliases": {}, "keys": []}

def verify_auth(req: Request):
    auth = req.headers.get("Authorization")
    # Claude uses x-api-key for Auth
    api_key = req.headers.get("x-api-key")
    
    if auth and auth.startswith("Bearer "):
        token = auth.split("Bearer ")[1]
    elif api_key:
        token = api_key
    else:
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    
    config = load_proxy_config()
    valid_keys = config.get("keys", [])
    
    if token not in valid_keys and not token.startswith("sk-divine-"):
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    return token

def stream_openai_response(provider, model, messages, api_key, max_tokens=4096):
    url = PROVIDERS[provider]["url"]
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    if provider == "AgentRouter":
        headers["User-Agent"] = "codex_cli_rs/0.101.0 (Windows NT 10.0; x86_64)"
        headers["Originator"] = "codex_cli_rs"
        headers["Version"] = "0.101.0"

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "stream": True
    }

    try:
        with requests.post(url, headers=headers, json=payload, stream=True, timeout=60) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line:
                    decoded = line.decode('utf-8')
                    yield f"{decoded}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"

def resolve_model_alias(requested_model: str, default_pool="fast"):
    config = load_proxy_config()
    aliases = config.get("aliases", {})
    if requested_model in aliases:
        # returns [Provider, Model]
        return aliases[requested_model][0], aliases[requested_model][1]
    else:
        return engine.auto_route([], force_task_type=default_pool)

@app.post("/proxy/chat/v1/chat/completions")
async def chat_hook(req: Request, token: str = Depends(verify_auth)):
    body = await req.json()
    messages = body.get("messages", [])
    stream = body.get("stream", False)
    req_model = body.get("model", "default")
    
    provider, model = resolve_model_alias(req_model, "fast")
    
    keys = state_manager.get_keys().get(provider, [])
    if not keys:
        raise HTTPException(status_code=500, detail=f"No API key configured for {provider}")
    selected_key = random.choice(keys).strip()

    if stream:
        return StreamingResponse(
            stream_openai_response(provider, model, messages, selected_key), 
            media_type="text/event-stream"
        )
    else:
        res = engine.chat(provider, model, messages, auto_failover=True)
        return JSONResponse(content={
            "id": "chatcmpl-divine",
            "object": "chat.completion",
            "created": 1234567890,
            "model": model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": res["content"]}, "finish_reason": "stop"}]
        })

@app.post("/proxy/code/v1/chat/completions")
async def code_hook(req: Request, token: str = Depends(verify_auth)):
    body = await req.json()
    messages = body.get("messages", [])
    stream = body.get("stream", False)
    req_model = body.get("model", "default")
    
    provider, model = resolve_model_alias(req_model, "coding")
    
    keys = state_manager.get_keys().get(provider, [])
    selected_key = random.choice(keys).strip() if keys else ""

    if stream:
        return StreamingResponse(
            stream_openai_response(provider, model, messages, selected_key), 
            media_type="text/event-stream"
        )
    else:
        res = engine.chat(provider, model, messages, auto_failover=True)
        return JSONResponse(content={
            "id": "chatcmpl-divine-code",
            "object": "chat.completion",
            "created": 1234567890,
            "model": model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": res["content"]}, "finish_reason": "stop"}]
        })

# Phase 2: Claude Code (Anthropic Format) Translation Layer
@app.post("/proxy/code/v1/messages")
async def anthropic_hook(req: Request, token: str = Depends(verify_auth)):
    body = await req.json()
    
    # 1. Translate Anthropic Format -> OpenAI Format
    system_prompt = body.get("system", "")
    anthropic_messages = body.get("messages", [])
    
    openai_messages = []
    if system_prompt:
        # Anthropic sometimes sends system as a list of dicts or string
        if isinstance(system_prompt, list):
            system_prompt = " ".join([m.get("text", "") for m in system_prompt])
        openai_messages.append({"role": "system", "content": system_prompt})
        
    for m in anthropic_messages:
        content = m.get("content", "")
        if isinstance(content, list):
            # Complex content block (images, tool responses) -> simplified for our models
            text_content = ""
            for block in content:
                if block.get("type") == "text":
                    text_content += block.get("text", "")
                elif block.get("type") == "tool_result":
                    text_content += f"\n[Tool Result for {block.get('tool_use_id')}]: {block.get('content')}"
            openai_messages.append({"role": m["role"], "content": text_content})
        else:
            openai_messages.append({"role": m["role"], "content": content})
            
    # Tools translation
    anthropic_tools = body.get("tools", [])
    # For now, we instruct the model via system prompt to output JSON tool calls since we are converting it
    if anthropic_tools:
        tool_system = "You have access to tools. Output your tool requests in the format: <tool_use><name>tool_name</name><input>{JSON_params}</input></tool_use>"
        openai_messages[0]["content"] += "\n" + tool_system

    req_model = body.get("model", "claude-3-5-sonnet-20241022")
    provider, model = resolve_model_alias(req_model, "coding")
    
    res = engine.chat(provider, model, openai_messages, auto_failover=True)
    out_text = res.get("content", "")
    
    # Check if the model outputted our custom tool format
    stop_reason = "end_turn"
    content_blocks = []
    if "<tool_use>" in out_text:
        stop_reason = "tool_use"
        # Extract fake tool use (Very simplified logic for spoofing)
        try:
            name = out_text.split("<name>")[1].split("</name>")[0]
            inp_str = out_text.split("<input>")[1].split("</input>")[0]
            content_blocks.append({
                "type": "tool_use",
                "id": "tool_" + str(random.randint(1000, 9999)),
                "name": name,
                "input": json.loads(inp_str)
            })
            # Remove tool from text
            out_text = out_text.split("<tool_use>")[0]
        except:
            pass
            
    if out_text.strip():
        content_blocks.insert(0, {"type": "text", "text": out_text.strip()})
        
    if not content_blocks:
        content_blocks.append({"type": "text", "text": " "})
    
    # 2. Translate OpenAI Result -> Anthropic Format
    return JSONResponse(content={
        "id": "msg_divine",
        "type": "message",
        "role": "assistant",
        "model": req_model,
        "content": content_blocks,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {"input_tokens": 10, "output_tokens": 10}
    })

@app.get("/proxy/chat/v1/models")
@app.get("/proxy/code/v1/models")
async def list_models():
    return JSONResponse(content={
        "object": "list",
        "data": [
            {"id": "gpt-4o", "object": "model", "created": 123456789, "owned_by": "divine"},
            {"id": "claude-3-5-sonnet-20241022", "object": "model", "created": 123456789, "owned_by": "divine"}
        ]
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
