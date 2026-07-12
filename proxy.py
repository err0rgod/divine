import http.server
import socketserver
import urllib.request
import json

PORT = 8000
TARGET_URL = "https://agentrouter.org/v1"
API_KEY = "sk-q8fB6Ufp6kyyMs27WtsEFUcYf3I1OTRkCbS5QTNbwkhfQ69G"

class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else b""
        
        try:
            # Parse the request body to intercept and change the model name
            data = json.loads(body.decode('utf-8'))
            
            # Map standard Anthropic model to AgentRouter custom model
            original_model = data.get("model", "")
            data["model"] = "claude-opus-4-8"
            
            print(f"[Proxy] Intercepted request for {original_model}, rewriting to claude-opus-4-8")
            body = json.dumps(data).encode('utf-8')
        except Exception as e:
            print(f"[Proxy] Warning: Could not parse body as JSON: {e}")

        # Construct the target URL
        path = self.path
        url = TARGET_URL + path.replace('/v1', '', 1)

        # Prepare headers for AgentRouter
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("x-api-key", API_KEY)
        req.add_header("anthropic-version", "2023-06-01")
        
        # Inject the required client fingerprint headers
        req.add_header("User-Agent", "codex_cli_rs/0.101.0 (Windows NT 10.0; x86_64)")
        req.add_header("Originator", "codex_cli_rs")
        req.add_header("Version", "0.101.0")

        try:
            print(f"[Proxy] Forwarding to {url}")
            with urllib.request.urlopen(req, timeout=120) as response:
                self.send_response(response.status)
                for key, val in response.getheaders():
                    # Skip hop-by-hop headers and chunked transfer encoding
                    if key.lower() not in ['transfer-encoding', 'connection']:
                        self.send_header(key, val)
                self.end_headers()
                
                # Stream the response back to Claude Code
                while True:
                    chunk = response.read(4096)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        except urllib.error.HTTPError as e:
            print(f"[Proxy] HTTP Error: {e.code}")
            self.send_response(e.code)
            for key, val in e.headers.items():
                if key.lower() not in ['transfer-encoding', 'connection']:
                    self.send_header(key, val)
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            print(f"[Proxy] Error: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())

    def do_GET(self):
        # Handle GET requests (like /v1/models if Claude Code checks it)
        url = TARGET_URL + self.path.replace('/v1', '', 1)
        req = urllib.request.Request(url, method="GET")
        req.add_header("Authorization", f"Bearer {API_KEY}")
        req.add_header("User-Agent", "codex_cli_rs/0.101.0 (Windows NT 10.0; x86_64)")
        req.add_header("Originator", "codex_cli_rs")
        req.add_header("Version", "0.101.0")
        
        try:
            print(f"[Proxy] Forwarding GET to {url}")
            with urllib.request.urlopen(req, timeout=60) as response:
                self.send_response(response.status)
                for key, val in response.getheaders():
                    if key.lower() not in ['transfer-encoding', 'connection']:
                        self.send_header(key, val)
                self.end_headers()
                
                # Read the body
                body = response.read()
                
                # If it's a models list, inject a fake standard model so Claude Code is happy
                if "/models" in url:
                    try:
                        data = json.loads(body.decode('utf-8'))
                        if "data" in data:
                            data["data"].append({
                                "id": "claude-3-5-sonnet-20241022", 
                                "object": "model", 
                                "created": 1626777600,
                                "owned_by": "custom"
                            })
                            body = json.dumps(data).encode('utf-8')
                    except Exception as e:
                        print(f"[Proxy] Warning: Could not inject model into /models: {e}")
                        
                self.wfile.write(body)
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

with ThreadedHTTPServer(("", PORT), ProxyHandler) as httpd:
    print(f"Agent Router Proxy running at http://localhost:{PORT}")
    print("Point Claude Code to: http://localhost:8000/v1")
    httpd.serve_forever()
