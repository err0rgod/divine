import http.server
import socketserver
import urllib.request
import json
import os

PORT = 8000
AGENTROUTER_API_URL = "https://agentrouter.org/v1/chat/completions"
DEFAULT_TARGET_MODEL = "claude-opus-4-8"

def load_keys():
    try:
        with open("D:/divine/config/proxy_keys.json", "r") as f:
            data = json.load(f)
            return data.get("keys", {}).get("AgentRouter", [])
    except Exception:
        return []

AGENTROUTER_API_KEYS = load_keys()

def get_target_model(default):
    try:
        import json
        with open("D:/divine/config/proxy_config.json", "r") as f:
            val = json.load(f).get("target_model")
            return val if val else default
    except Exception:
        return default

def anthropic_to_openai_request(anthropic_data):
    req = {
        "model": get_target_model(DEFAULT_TARGET_MODEL),
        "messages": [],
    }
    
    system_prompt = anthropic_data.get("system")
    if system_prompt:
        if isinstance(system_prompt, str):
            req["messages"].append({"role": "system", "content": system_prompt})
        elif isinstance(system_prompt, list):
            sys_text = "\n".join(b["text"] for b in system_prompt if b.get("type") == "text")
            req["messages"].append({"role": "system", "content": sys_text})
            
    if "max_tokens" in anthropic_data:
        req["max_tokens"] = anthropic_data["max_tokens"]
    if "temperature" in anthropic_data:
        req["temperature"] = anthropic_data["temperature"]
        
    if "tools" in anthropic_data:
        req["tools"] = []
        for t in anthropic_data["tools"]:
            req["tools"].append({
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema", {})
                }
            })
            
    for msg in anthropic_data.get("messages", []):
        role = msg["role"]
        content = msg["content"]
        
        if isinstance(content, str):
            req["messages"].append({"role": role, "content": content})
            continue
            
        text_content = ""
        tool_calls = []
        
        for block in content:
            if block["type"] == "text":
                text_content += block["text"]
            elif block["type"] == "tool_use":
                tool_calls.append({
                    "id": block["id"],
                    "type": "function",
                    "function": {
                        "name": block["name"],
                        "arguments": json.dumps(block["input"])
                    }
                })
            elif block["type"] == "tool_result":
                tool_msg = {
                    "role": "tool",
                    "tool_call_id": block["tool_use_id"],
                    "content": ""
                }
                if isinstance(block.get("content"), str):
                    tool_msg["content"] = block["content"]
                elif isinstance(block.get("content"), list):
                    texts = [b["text"] for b in block["content"] if b["type"] == "text"]
                    tool_msg["content"] = "\n".join(texts)
                req["messages"].append(tool_msg)
                
        if role == "assistant":
            ast_msg = {"role": "assistant"}
            if text_content:
                ast_msg["content"] = text_content
            else:
                ast_msg["content"] = ""
            if tool_calls:
                ast_msg["tool_calls"] = tool_calls
            req["messages"].append(ast_msg)
        elif role == "user":
            if text_content:
                req["messages"].append({"role": "user", "content": text_content})
                
    return req

def openai_to_anthropic_response(resp, original_model):
    choice = resp["choices"][0]
    msg = choice["message"]
    
    anthropic_content = []
    if msg.get("content"):
        anthropic_content.append({"type": "text", "text": msg["content"]})
        
    if msg.get("tool_calls"):
        for tc in msg["tool_calls"]:
            anthropic_content.append({
                "type": "tool_use",
                "id": tc["id"],
                "name": tc["function"]["name"],
                "input": json.loads(tc["function"]["arguments"])
            })
            
    finish_reason = choice.get("finish_reason")
    stop_reason = "end_turn"
    if finish_reason == "tool_calls":
        stop_reason = "tool_use"
    elif finish_reason == "length":
        stop_reason = "max_tokens"
        
    return {
        "id": "msg_ar_" + resp.get("id", "123"),
        "type": "message",
        "role": "assistant",
        "model": original_model,
        "content": anthropic_content,
        "stop_reason": stop_reason,
        "usage": {
            "input_tokens": resp.get("usage", {}).get("prompt_tokens", 0),
            "output_tokens": resp.get("usage", {}).get("completion_tokens", 0)
        }
    }


def handle_openai_stream(handler, response, original_model, is_anthropic):
    handler.send_response(200)
    handler.send_header("Content-Type", "text/event-stream")
    handler.send_header("Cache-Control", "no-cache")
    handler.send_header("Connection", "keep-alive")
    handler.end_headers()
    
    if not is_anthropic:
        try:
        for line in response.iter_lines():
            if not line: continue
            line = line.decode('utf-8', errors='ignore').strip()
            if not line or not line.startswith("data: "):
                continue
                
            data_str = line[6:]
            if data_str == "[DONE]":
                break
                
            try:
                chunk = json.loads(data_str)
            except:
                continue
                
            if not chunk.get("choices"):
                continue
                
            delta = chunk["choices"][0].get("delta", {})
            finish_reason = chunk["choices"][0].get("finish_reason")
            
            if "content" in delta and delta["content"] is not None:
                content = delta["content"]
                if not in_text_block:
                    current_block_index += 1
                    in_text_block = True
                    t_start = {"type": "content_block_start", "index": current_block_index, "content_block": {"type": "text", "text": ""}}
                    handler.wfile.write(f"event: content_block_start\ndata: {json.dumps(t_start)}\n\n".encode('utf-8'))
                
                t_delta = {"type": "content_block_delta", "index": current_block_index, "delta": {"type": "text_delta", "text": content}}
                handler.wfile.write(f"event: content_block_delta\ndata: {json.dumps(t_delta)}\n\n".encode('utf-8'))
                handler.wfile.flush()
                
            if "tool_calls" in delta:
                if in_text_block:
                    in_text_block = False
                    t_stop = {"type": "content_block_stop", "index": current_block_index}
                    handler.wfile.write(f"event: content_block_stop\ndata: {json.dumps(t_stop)}\n\n".encode('utf-8'))
                    
                for tc in delta["tool_calls"]:
                    tc_index = tc["index"]
                    if tc_index not in active_tools:
                        current_block_index += 1
                        active_tools[tc_index] = current_block_index
                        
                        t_id = tc.get("id", "call_" + os.urandom(4).hex())
                        t_name = tc.get("function", {}).get("name", "unknown")
                        
                        tl_start = {"type": "content_block_start", "index": current_block_index, "content_block": {"type": "tool_use", "id": t_id, "name": t_name, "input": {}}}
                        handler.wfile.write(f"event: content_block_start\ndata: {json.dumps(tl_start)}\n\n".encode('utf-8'))
                        
                    if "function" in tc and "arguments" in tc["function"]:
                        args_str = tc["function"]["arguments"]
                        if args_str:
                            tl_delta = {"type": "content_block_delta", "index": active_tools[tc_index], "delta": {"type": "input_json_delta", "partial_json": args_str}}
                            handler.wfile.write(f"event: content_block_delta\ndata: {json.dumps(tl_delta)}\n\n".encode('utf-8'))
                            handler.wfile.flush()
                            
            if finish_reason:
                if in_text_block:
                    t_stop = {"type": "content_block_stop", "index": current_block_index}
                    handler.wfile.write(f"event: content_block_stop\ndata: {json.dumps(t_stop)}\n\n".encode('utf-8'))
                    in_text_block = False
                    
                for tc_index in active_tools:
                    tl_stop = {"type": "content_block_stop", "index": active_tools[tc_index]}
                    handler.wfile.write(f"event: content_block_stop\ndata: {json.dumps(tl_stop)}\n\n".encode('utf-8'))
                    
                stop_reason_str = "end_turn"
                if finish_reason == "tool_calls": stop_reason_str = "tool_use"
                elif finish_reason == "length": stop_reason_str = "max_tokens"
                
                m_delta = {"type": "message_delta", "delta": {"stop_reason": stop_reason_str, "stop_sequence": None}, "usage": {"output_tokens": 0}}
                handler.wfile.write(f"event: message_delta\ndata: {json.dumps(m_delta)}\n\n".encode('utf-8'))
                handler.wfile.write(b'event: message_stop\ndata: {"type": "message_stop"}\n\n')
                handler.wfile.flush()
                sent_stop = True
                break
    except Exception as stream_err:
        print(f"[Proxy Stream Warning] Upstream disconnected early: {stream_err}")

    if not sent_stop:
        if in_text_block:
            t_stop = {"type": "content_block_stop", "index": current_block_index}
            handler.wfile.write(f"event: content_block_stop\ndata: {json.dumps(t_stop)}\n\n".encode('utf-8'))
            
        for tc_index in active_tools:
            tl_stop = {"type": "content_block_stop", "index": active_tools[tc_index]}
            handler.wfile.write(f"event: content_block_stop\ndata: {json.dumps(tl_stop)}\n\n".encode('utf-8'))
            
        m_delta = {"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence": None}, "usage": {"output_tokens": 0}}
        handler.wfile.write(f"event: message_delta\ndata: {json.dumps(m_delta)}\n\n".encode('utf-8'))
        handler.wfile.write(b'event: message_stop\ndata: {"type": "message_stop"}\n\n')
        handler.wfile.flush()

class AgentRouterProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        if self.path.endswith("/v1/models"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            models_resp = {
                "object": "list",
                "data": [
                    {"id": "claude-3-7-sonnet-20250219", "type": "model", "created_at": 1739923200},
                    {"id": "claude-3-5-sonnet-20241022", "type": "model", "created_at": 1729555200},
                    {"id": "claude-3-5-haiku-20241022", "type": "model", "created_at": 1729555200},
                    {"id": "claude-haiku-4-5-20251001", "type": "model", "created_at": 1735689600},
                    {"id": "claude-3-opus-20240229", "type": "model", "created_at": 1709164800}
                ]
            }
            self.wfile.write(json.dumps(models_resp).encode('utf-8'))
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"AgentRouter Proxy is running!")

    def do_POST(self):
        try:
            import requests
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length) if length > 0 else b""
            req_json = json.loads(body.decode('utf-8'))
            
            orig_model = req_json.get("model", "claude-3-5-sonnet")
            is_anthropic = self.path.split("?")[0].endswith("/v1/messages")
            is_stream = req_json.get("stream", False)
            
            if is_anthropic and "anthropic_to_mistral_request" in globals():
                target_req = anthropic_to_mistral_request(req_json)
            elif is_anthropic and "anthropic_to_agentrouter_request" in globals():
                target_req = anthropic_to_agentrouter_request(req_json)
            elif is_anthropic and "anthropic_to_openai_request" in globals():
                target_req = anthropic_to_openai_request(req_json)
            else:
                target_req = req_json.copy()
                if "get_target_model" in globals():
                    target_req["model"] = get_target_model(DEFAULT_TARGET_MODEL)
            
            target_req["stream"] = is_stream
            
            # Hotfix: Ensure model is string
            if ": " in target_req.get("model", ""): target_req["model"] = target_req["model"].split(": ")[1]
            
            # ZHIPU/GLM SAFETY PATCH
            if is_anthropic:
                for m in target_req.get("messages", []):
                    if m.get("role") == "assistant" and "content" not in m:
                        m["content"] = ""
                    if isinstance(m.get("content"), list):
                        m["content"] = "\n".join([str(item) for item in m["content"]])
            
            # Key resolution
            if 'MISTRAL_API_KEYS' in globals(): key = MISTRAL_API_KEYS[0] if MISTRAL_API_KEYS else ""
            elif 'AGENTROUTER_API_KEYS' in globals(): key = AGENTROUTER_API_KEYS[0] if AGENTROUTER_API_KEYS else ""
            else: key = API_KEYS[0] if 'API_KEYS' in globals() and API_KEYS else ""
            
            # URL resolution
            if 'MISTRAL_API_URL' in globals(): api_url = MISTRAL_API_URL
            elif 'AGENTROUTER_API_URL' in globals(): api_url = AGENTROUTER_API_URL
            else: api_url = API_URL
            
            headers = {
                "Authorization": f"Bearer {key}",
                "Accept": "text/event-stream" if is_stream else "application/json"
            }
            
            response = requests.post(api_url, json=target_req, headers=headers, stream=is_stream, timeout=120)
            
            if response.status_code != 200:
                self.send_response(response.status_code)
                for k, v in response.headers.items():
                    if k.lower() not in ['transfer-encoding', 'connection', 'content-length', 'content-encoding']:
                        self.send_header(k, v)
                self.end_headers()
                self.wfile.write(response.content)
                return
                
            if is_stream:
                handle_openai_stream(self, response, orig_model, is_anthropic)
                return
                
            resp_json = response.json()
            if is_anthropic and "mistral_to_anthropic_response" in globals():
                final_resp = mistral_to_anthropic_response(resp_json, orig_model)
            elif is_anthropic and "agentrouter_to_anthropic_response" in globals():
                final_resp = agentrouter_to_anthropic_response(resp_json, orig_model)
            elif is_anthropic and "openai_to_anthropic_response" in globals():
                final_resp = openai_to_anthropic_response(resp_json, orig_model)
            else:
                final_resp = resp_json
                
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(final_resp).encode('utf-8'))
            
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())

    def handle_one_request(self):
        try:
            super().handle_one_request()
        except ConnectionResetError:
            pass

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

if __name__ == "__main__":
    if not AGENTROUTER_API_KEYS:
        print("[WARNING] No AgentRouter API keys found in config/proxy_keys.json!")
    with ThreadedHTTPServer(("", PORT), AgentRouterProxyHandler) as httpd:
        print(f"AgentRouter Translation Proxy running at http://localhost:{PORT}/v1/messages")
        print(f"Targeting Model: {DEFAULT_TARGET_MODEL}")
        print(f"Loaded {len(AGENTROUTER_API_KEYS)} API Keys for Fallback!")
        httpd.serve_forever()
