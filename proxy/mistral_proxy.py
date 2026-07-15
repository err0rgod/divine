import http.server
import socketserver
import urllib.request
import json
import os

#  $env:ANTHROPIC_API_KEY="dummy_key"
# $env:ANTHROPIC_BASE_URL="http://127.0.0.1:8000"

PORT = 6900  # using 6900 for proxy
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"
MISTRAL_API_KEYS = [
    "pasOCuI0UgqFN1ySWUduXaozqG29vQbh",
    "kryJyu02s1UGG47TH0RBfDs1NePDV26m"
]
DEFAULT_TARGET_MODEL = "codestral-latest"  # Codestral is great for coding and on free tier. 'mistral-large-latest' is also an option.

def get_target_model(default):
    try:
        import json
        with open("D:/divine/config/proxy_config.json", "r") as f:
            return json.load(f).get("target_model", default)
    except:
        return default

def anthropic_to_mistral_request(anthropic_data):
    mistral_req = {
        "model": get_target_model(DEFAULT_TARGET_MODEL),
        "messages": [],
    }
    
    # 1. Handle System Prompt
    system_prompt = anthropic_data.get("system")
    if system_prompt:
        if isinstance(system_prompt, str):
            mistral_req["messages"].append({"role": "system", "content": system_prompt})
        elif isinstance(system_prompt, list):
            # Anthropic sometimes passes system as a list of text blocks
            sys_text = "\n".join(b["text"] for b in system_prompt if b.get("type") == "text")
            mistral_req["messages"].append({"role": "system", "content": sys_text})
            
    # 2. Handle max tokens and temperature
    if "max_tokens" in anthropic_data:
        mistral_req["max_tokens"] = anthropic_data["max_tokens"]
    if "temperature" in anthropic_data:
        mistral_req["temperature"] = anthropic_data["temperature"]
        
    # 3. Handle Tools
    if "tools" in anthropic_data:
        mistral_req["tools"] = []
        for t in anthropic_data["tools"]:
            mistral_req["tools"].append({
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema", {})
                }
            })
            
    # 4. Handle Messages
    for msg in anthropic_data.get("messages", []):
        role = msg["role"]
        content = msg["content"]
        
        if isinstance(content, str):
            mistral_req["messages"].append({"role": role, "content": content})
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
                mistral_req["messages"].append(tool_msg)
                
        if role == "assistant":
            ast_msg = {"role": "assistant"}
            if text_content:
                ast_msg["content"] = text_content
            if tool_calls:
                ast_msg["tool_calls"] = tool_calls
            mistral_req["messages"].append(ast_msg)
        elif role == "user":
            if text_content:
                mistral_req["messages"].append({"role": "user", "content": text_content})
                
    return mistral_req

def mistral_to_anthropic_response(mistral_resp, original_model):
    choice = mistral_resp["choices"][0]
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
        "id": "msg_mistral_" + mistral_resp.get("id", "123"),
        "type": "message",
        "role": "assistant",
        "model": original_model,
        "content": anthropic_content,
        "stop_reason": stop_reason,
        "usage": {
            "input_tokens": mistral_resp.get("usage", {}).get("prompt_tokens", 0),
            "output_tokens": mistral_resp.get("usage", {}).get("completion_tokens", 0)
        }
    }

class MistralProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Mistral Proxy is running!")

    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else b""
            
            anthropic_req = json.loads(body.decode('utf-8'))
            original_model = anthropic_req.get("model", "claude-3-5-sonnet-20241022")
            
            # Convert Anthropic format to Mistral format
            mistral_req = anthropic_to_mistral_request(anthropic_req)
            mistral_body = json.dumps(mistral_req).encode('utf-8')
            
            print(f"[Mistral Proxy] Translated request for Mistral API (Target Model: {DEFAULT_TARGET_MODEL})")
            
            last_error = None
            for key in MISTRAL_API_KEYS:
                req = urllib.request.Request(MISTRAL_API_URL, data=mistral_body, method="POST")
                req.add_header("Content-Type", "application/json")
                req.add_header("Authorization", f"Bearer {key}")
                req.add_header("Accept", "application/json")
                
                try:
                    with urllib.request.urlopen(req, timeout=120) as response:
                        resp_body = response.read()
                        mistral_resp = json.loads(resp_body.decode('utf-8'))
                        
                        # Convert Mistral format back to Anthropic format for Claude Code
                        anthropic_resp = mistral_to_anthropic_response(mistral_resp, original_model)
                        final_body = json.dumps(anthropic_resp).encode('utf-8')
                        
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(final_body)
                        return  # Successfully completed, exit loop and function
                except urllib.error.HTTPError as e:
                    if e.code == 429:
                        print(f"[Mistral Proxy Warning] Key {key[:8]}... got HTTP 429 Rate Limit. Falling back to next key...")
                        last_error = e
                        continue  # Try next key
                    else:
                        error_body = e.read()
                        print(f"[Mistral Proxy Error] HTTP {e.code}: {error_body.decode('utf-8', errors='ignore')}")
                        self.send_response(e.code)
                        for k, v in e.headers.items():
                            if k.lower() not in ['transfer-encoding', 'connection']:
                                self.send_header(k, v)
                        self.end_headers()
                        self.wfile.write(error_body)
                        return
                        
            # If all keys were exhausted due to 429 Rate Limits
            if last_error:
                error_body = last_error.read() if not hasattr(last_error, 'read_body') else getattr(last_error, 'read_body')
                print("[Mistral Proxy Error] Exhausted all keys. Last error HTTP 429.")
                self.send_response(last_error.code)
                for k, v in last_error.headers.items():
                    if k.lower() not in ['transfer-encoding', 'connection']:
                        self.send_header(k, v)
                self.end_headers()
                # e.read() can only be read once, so if it was read we'd need to cache it, but HTTPError is a file-like object so it's already read.
                self.wfile.write(b'{"error": {"message": "Rate limit exceeded on all keys"}}')
                
        except Exception as e:
            print(f"[Proxy Error] {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

if __name__ == "__main__":
    with ThreadedHTTPServer(("", PORT), MistralProxyHandler) as httpd:
        print(f"Mistral Translation Proxy running at http://localhost:{PORT}")
        print(f"Targeting Mistral Free Tier Model: {DEFAULT_TARGET_MODEL}")
        print(f"Loaded {len(MISTRAL_API_KEYS)} API Keys for Fallback!")
        httpd.serve_forever()
