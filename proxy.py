import http.server
import socketserver
import urllib.request
import json
import os

PORT = 8000
CONFIG_FILE = "proxy_config.json"

def get_config():
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            config = get_config()
            provider_name = config.get("provider", "agentrouter")
            provider_cfg = config.get(provider_name, {})
            
            target_url = provider_cfg.get("url")
            api_key = provider_cfg.get("key")
            target_model = config.get("model")
            custom_headers = provider_cfg.get("headers", {})
            
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else b""
            
            # Rewrite model
            data = json.loads(body.decode('utf-8'))
            original_model = data.get("model", "")
            data["model"] = target_model
            
            # Auto-Repair Agent Router's malformed tool_use IDs
            if "messages" in data:
                for msg in data["messages"]:
                    if isinstance(msg.get("content"), list):
                        for block in msg["content"]:
                            if block.get("type") == "tool_use":
                                if not block.get("id"):
                                    block["id"] = "toolu_repaired_" + block.get("name", "unknown")
                            elif block.get("type") == "tool_result":
                                if not block.get("tool_use_id"):
                                    block["tool_use_id"] = "toolu_repaired_unknown"
                                    
            print(f"[Proxy -> {provider_name.upper()}] Model: {original_model} => {target_model}")
            body = json.dumps(data).encode('utf-8')
            
            path = self.path
            url = target_url + path.replace('/v1', '', 1)

            req = urllib.request.Request(url, data=body, method="POST")
            req.add_header("Content-Type", "application/json")
            req.add_header("x-api-key", api_key)
            req.add_header("Authorization", f"Bearer {api_key}")
            
            for k, v in custom_headers.items():
                req.add_header(k, v)

            with urllib.request.urlopen(req, timeout=120) as response:
                self.send_response(response.status)
                for key, val in response.getheaders():
                    if key.lower() not in ['transfer-encoding', 'connection']:
                        self.send_header(key, val)
                self.end_headers()
                
                while True:
                    chunk = response.read(4096)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        except (ConnectionResetError, BrokenPipeError):
            print(f"[Proxy -> {provider_name.upper()}] Client disconnected before receiving the response.")
        except urllib.error.HTTPError as e:
            try:
                error_body = e.read()
                print(f"[Proxy -> {provider_name.upper()}] HTTP {e.code} Error! Response: {error_body.decode('utf-8', errors='ignore')}")
                self.send_response(e.code)
                for key, val in e.headers.items():
                    if key.lower() not in ['transfer-encoding', 'connection']:
                        self.send_header(key, val)
                self.end_headers()
                self.wfile.write(error_body)
            except (ConnectionResetError, BrokenPipeError):
                pass
        except Exception as e:
            print(f"[Proxy Error] {e}")
            try:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
            except (ConnectionResetError, BrokenPipeError):
                pass

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

if __name__ == "__main__":
    with ThreadedHTTPServer(("", PORT), ProxyHandler) as httpd:
        print(f"Omni-Route Dynamic Proxy running at http://localhost:{PORT}")
        print(f"Reading configuration dynamically from {CONFIG_FILE}")
        httpd.serve_forever()
