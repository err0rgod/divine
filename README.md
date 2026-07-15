# Divine Gateway

Divine is a lightweight, zero-dependency local proxy designed to intercept Anthropic API traffic (such as requests from Claude Code) and route it to alternative LLM providers. 

By translating the Anthropic Messages protocol into the standard OpenAI Chat Completions protocol, Divine allows you to use cheaper, local, or alternative models while preserving native features like Server-Sent Events (SSE) streaming and tool calling.

## Design Philosophy

Unlike monolithic proxy solutions that require heavy web frameworks, Divine is built on a minimalist philosophy:
- **Zero Heavy Dependencies:** Runs on standard Python libraries (`http.server`, `json`) and `requests`. No ASGI/WSGI servers, no complex ORMs, and no bloated routing frameworks.
- **Micro-Script Architecture:** Each provider is isolated in its own dedicated proxy script (e.g., `mistral_proxy.py`). If one provider's API changes, it does not affect the rest of the gateway.
- **Highly Hackable:** The codebase is designed to be easily read and modified by anyone familiar with basic Python HTTP handlers.

## Features

- **True Real-Time Streaming:** Implements a robust `requests.iter_lines()` streaming engine that safely handles chunked encoding and mid-stream provider disconnects, guaranteeing that the target client (e.g., Claude Code) receives the Anthropic `message_stop` signal properly without hanging.
- **Protocol Translation:** Automatically translates Anthropic tool usage, system prompts, and thinking blocks into OpenAI-compatible formats, and reformats the responses back to Anthropic structures.
- **Provider Support:** Natively includes proxy scripts for DeepSeek, Mistral, Cerebras, Groq, NVIDIA, Bluesmind, AgentRouter, and Forge AI.
- **Automated Key Management:** Reads API credentials securely from a local `.env` file and synchronizes them to a strict `proxy_keys.json` configuration to prevent accidental leaks.

## Setup and Installation

### 1. Prerequisites
Ensure you have Python 3.8+ installed. Install the minimal requirements:
```bash
pip install requests python-dotenv
```

### 2. Configuration
Create a `.env` file in the root directory and add your API keys:
```env
DEEPSEEK_API_KEY=your_key_here
MISTRAL_API_KEY=your_key_here
# Add other provider keys as needed
```

When you run the main application, it will automatically parse the `.env` file and generate a `.gitignore`-protected `proxy_keys.json` file in the `config/` directory.

### 3. Running the Proxy
You can start a specific proxy directly from the `proxy/` directory. For example, to run the DeepSeek proxy (which defaults to port 8000):
```bash
python proxy/deepseek_proxy.py
```

### 4. Connecting a Client (Claude Code)
To route Claude Code traffic through the Divine Gateway, set the Anthropic base URL environment variable to point to your running proxy port.

**macOS/Linux:**
```bash
export ANTHROPIC_BASE_URL="http://localhost:8000"
export ANTHROPIC_AUTH_TOKEN="local-proxy"
claude
```

**Windows (PowerShell):**
```powershell
$env:ANTHROPIC_BASE_URL="http://localhost:8000"
$env:ANTHROPIC_AUTH_TOKEN="local-proxy"
claude
```

## Architecture

The system operates via standard `http.server.BaseHTTPRequestHandler` instances. 
1. The proxy listens for `POST` requests to `/v1/messages` (Anthropic's endpoint).
2. It parses the incoming Anthropic JSON and runs it through a translation function (e.g., `anthropic_to_openai_request`).
3. It opens a chunked streaming connection to the target provider.
4. It intercepts the SSE stream, converting OpenAI `delta` events into Anthropic `content_block_delta` events, and flushes them to the client socket in real-time.

## Roadmap & V2 Architecture

Divine v1.0 represents the stable, decoupled micro-script phase of the project. As the project evolves, the roadmap for V2 includes adapting advanced features while maintaining our lightweight, standard-library-first philosophy:

1. **Unified Master Proxy:** 
   Consolidating the individual proxy scripts into a single, dynamic `divine_proxy.py` router. Instead of spinning up different ports for different providers, a single port will dynamically route traffic based on dashboard configuration, reducing port conflicts and unifying the translation logic.
2. **Native Model Discovery:** 
   Implementing a handler for the `/v1/models` endpoint to automatically inject available gateway models into Claude Code's native `/model` CLI dropdown, allowing seamless model switching without restarting the proxy.
3. **Lightweight Messaging Bridge:** 
   Developing a standard-library polling daemon to interface with Discord and Telegram APIs. This will allow headless execution of Claude Code sessions via mobile devices without introducing heavy ASGI webhooks.

## License

This project is provided as-is for educational and development purposes. Please review the terms of service of the target API providers before routing production traffic.
