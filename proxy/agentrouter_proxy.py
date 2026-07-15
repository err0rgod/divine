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
        with open("D:/divine/config/dashboard_config.json", "r") as f:
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
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else b""
            
            req_json = json.loads(body.decode('utf-8'))
            original_model = req_json.get("model", "claude-3-5-sonnet-20241022")
            
            is_anthropic = self.path.endswith("/v1/messages")
            is_stream = req_json.get("stream", False)
            
            if is_anthropic:
                req_data = anthropic_to_openai_request(req_json)
            else:
                req_data = req_json.copy()
                req_data["model"] = get_target_model(DEFAULT_TARGET_MODEL)
                
            # Disable stream for target API to avoid json.loads crashing on SSE
            req_data["stream"] = False
            req_body = json.dumps(req_data).encode('utf-8')
            
            print(f"[AgentRouter Proxy] Handling {'Anthropic' if is_anthropic else 'OpenAI'} request (Target Model: {DEFAULT_TARGET_MODEL})")
            
            if not AGENTROUTER_API_KEYS:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b'{"error": {"message": "No API keys found."}}')
                return

            last_error = None
            for key in AGENTROUTER_API_KEYS:
                req = urllib.request.Request(AGENTROUTER_API_URL, data=req_body, method="POST")
                req.add_header("Content-Type", "application/json")
                req.add_header("Authorization", f"Bearer {key}")
                req.add_header("Accept", "application/json")
                # AgentRouter specific anti-bot headers
                req.add_header("User-Agent", "codex_cli_rs/0.101.0 (Windows NT 10.0; x86_64)")
                req.add_header("Originator", "codex_cli_rs")
                req.add_header("Version", "0.101.0")
                req.add_header("anthropic-version", "2023-06-01")
                
                try:
                    with urllib.request.urlopen(req, timeout=120) as response:
                        resp_body = response.read()
                        resp_data = json.loads(resp_body.decode('utf-8'))
                        
                        if is_anthropic:
                            final_resp = openai_to_anthropic_response(resp_data, original_model)
                        else:
                            final_resp = resp_data
                            
                        # If the client requested stream, we must return a fake stream 
                        # to prevent the client from crashing due to content-type mismatch.
                        if is_stream:
                            self.send_response(200)
                            self.send_header("Content-Type", "text/event-stream")
                            self.end_headers()
                            
                            if is_anthropic:
                                msg_start = final_resp.copy()
                                msg_start["content"] = []
                                self.wfile.write(b'event: message_start\ndata: ' + json.dumps({"type": "message_start", "message": msg_start}).encode() + b'\n\n')
                                self.wfile.write(b'event: content_block_start\ndata: {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}}\n\n')
                                text_content = final_resp["content"][0]["text"] if final_resp.get("content") else ""
                                self.wfile.write(b'event: content_block_delta\ndata: {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": ' + json.dumps(text_content).encode() + b'}}\n\n')
                                self.wfile.write(b'event: content_block_stop\ndata: {"type": "content_block_stop", "index": 0}\n\n')
                                self.wfile.write(b'event: message_delta\ndata: {"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence": null}}\n\n')
                                self.wfile.write(b'event: message_stop\ndata: {"type": "message_stop"}\n\n')
                            else:
                                chunk = {
                                    "id": final_resp.get("id", "chatcmpl-123"),
                                    "object": "chat.completion.chunk",
                                    "created": final_resp.get("created", 0),
                                    "model": final_resp.get("model", "model"),
                                    "choices": [{"index": 0, "delta": {"content": final_resp["choices"][0]["message"].get("content", "")}, "finish_reason": None}]
                                }
                                self.wfile.write(b'data: ' + json.dumps(chunk).encode('utf-8') + b'\n\n')
                                end_chunk = chunk.copy()
                                end_chunk["choices"] = [{"index": 0, "delta": {}, "finish_reason": "stop"}]
                                self.wfile.write(b'data: ' + json.dumps(end_chunk).encode('utf-8') + b'\n\n')
                                self.wfile.write(b'data: [DONE]\n\n')
                            return

                        final_body = json.dumps(final_resp).encode('utf-8')
                        
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(final_body)
                        return
                except urllib.error.HTTPError as e:
                    if e.code == 429:
                        print(f"[AgentRouter Proxy Warning] Key {key[:8]}... got HTTP 429 Rate Limit. Falling back...")
                        last_error = e
                        continue
                    else:
                        error_body = e.read()
                        safe_err = error_body.decode('utf-8', errors='ignore').encode('ascii', errors='replace').decode('ascii')
                        print(f"[AgentRouter Proxy Error] HTTP {e.code}: {safe_err}")
                        self.send_response(e.code)
                        for k, v in e.headers.items():
                            if k.lower() not in ['transfer-encoding', 'connection']:
                                self.send_header(k, v)
                        self.end_headers()
                        self.wfile.write(error_body)
                        return
                        
            if last_error:
                print("[AgentRouter Proxy Error] Exhausted all keys. Last error HTTP 429.")
                self.send_response(last_error.code)
                for k, v in last_error.headers.items():
                    if k.lower() not in ['transfer-encoding', 'connection']:
                        self.send_header(k, v)
                self.end_headers()
                self.wfile.write(b'{"error": {"message": "Rate limit exceeded on all keys"}}')
                
        except Exception as e:
            print(f"[Proxy Error] {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

if __name__ == "__main__":
    if not AGENTROUTER_API_KEYS:
        print("[WARNING] No AgentRouter API keys found in config/dashboard_config.json!")
    with ThreadedHTTPServer(("", PORT), AgentRouterProxyHandler) as httpd:
        print(f"AgentRouter Translation Proxy running at http://localhost:{PORT}/v1/messages")
        print(f"Targeting Model: {DEFAULT_TARGET_MODEL}")
        print(f"Loaded {len(AGENTROUTER_API_KEYS)} API Keys for Fallback!")
        httpd.serve_forever()
