import http.server
import socketserver
import json
import os
import requests
from translator import anthropic_to_openai_request, openai_to_anthropic_response, handle_openai_stream

PORT = 8000

PROVIDERS = {
    "deepseek": {"url": "https://api.deepseek.com/chat/completions", "key_name": "DeepSeek"},
    "mistral": {"url": "https://api.mistral.ai/v1/chat/completions", "key_name": "Mistral"},
    "groq": {"url": "https://api.groq.com/openai/v1/chat/completions", "key_name": "Groq"},
    "cerebras": {"url": "https://api.cerebras.ai/v1/chat/completions", "key_name": "Cerebras"},
    "nvidia": {"url": "https://integrate.api.nvidia.com/v1/chat/completions", "key_name": "Nvidia"},
    "forge_ai": {"url": "https://forge-gateway-api.fly.dev/v1/chat/completions", "key_name": "ForgeAI"},
    "bluesmind": {"url": "https://api.bluesmind.ai/v1/chat/completions", "key_name": "Bluesmind"},
    "agentrouter": {"url": "https://api.agentrouter.ai/v1/chat/completions", "key_name": "AgentRouter"}
}

def load_keys():
    try:
        with open("D:/divine/config/proxy_keys.json", "r") as f:
            return json.load(f).get("keys", {})
    except Exception:
        return {}

def load_config():
    try:
        with open("D:/divine/config/proxy_config.json", "r") as f:
            return json.load(f)
    except Exception:
        return {"target_model": "deepseek-coder", "default_provider": "deepseek"}

class MasterProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        if self.path.endswith("/v1/models"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            # Future: Native Model Discovery
            # We can dynamically inject models here based on config!
            models_resp = {
                "object": "list",
                "data": [
                    {"id": "claude-3-7-sonnet-20250219", "type": "model", "created_at": 1739923200},
                    {"id": "claude-3-5-sonnet-20241022", "type": "model", "created_at": 1729555200}
                ]
            }
            self.wfile.write(json.dumps(models_resp).encode('utf-8'))
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Divine Master Proxy is running!")

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length) if length > 0 else b""
            req_json = json.loads(body.decode('utf-8'))
            
            config = load_config()
            keys = load_keys()
            
            orig_model = req_json.get("model", "claude-3-5-sonnet-20241022")
            is_anthropic = self.path.split("?")[0].endswith("/v1/messages")
            is_stream = req_json.get("stream", False)
            
            # --- DYNAMIC ROUTING LOGIC ---
            # If the user sets model to "groq/llama3-8b-8192", we extract "groq"
            if "/" in orig_model:
                provider_id, target_model = orig_model.split("/", 1)
            else:
                provider_id = config.get("default_provider", "deepseek")
                target_model = config.get("target_model", orig_model)
                
            if provider_id not in PROVIDERS:
                self.send_error(400, f"Unknown provider: {provider_id}")
                return
                
            provider_info = PROVIDERS[provider_id]
            api_url = provider_info["url"]
            key_list = keys.get(provider_info["key_name"], [])
            api_key = key_list[0] if key_list else ""
            
            print(f"[Master Proxy] Routing to {provider_id.upper()} using model {target_model}")
            
            # --- TRANSLATE REQUEST ---
            if is_anthropic:
                target_req = anthropic_to_openai_request(req_json, target_model)
            else:
                target_req = req_json.copy()
                target_req["model"] = target_model
                
            target_req["stream"] = is_stream
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Accept": "text/event-stream" if is_stream else "application/json"
            }
            
            # --- EXECUTE REQUEST ---
            response = requests.post(api_url, json=target_req, headers=headers, stream=is_stream, timeout=120)
            
            if response.status_code != 200:
                self.send_response(response.status_code)
                for k, v in response.headers.items():
                    if k.lower() not in ['transfer-encoding', 'connection', 'content-length', 'content-encoding']:
                        self.send_header(k, v)
                self.end_headers()
                self.wfile.write(response.content)
                return
                
            # --- HANDLE RESPONSE ---
            if is_stream:
                handle_openai_stream(self, response, orig_model, is_anthropic)
                return
                
            resp_json = response.json()
            if is_anthropic:
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
    print("========================================")
    print(f" DIVINE MASTER PROXY (V2)")
    print(f" Port: {PORT}")
    print("========================================")
    
    with ThreadedHTTPServer(("", PORT), MasterProxyHandler) as httpd:
        httpd.serve_forever()
