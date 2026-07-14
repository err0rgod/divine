# Divine: The Meta-Router & Universal Proxy Gateway

Divine is an intelligent AI Orchestrator that unifies multiple AI model pools (Fast, Reasoning, Coding) and exposes them as a **Universal Proxy Gateway**. This allows you to hook up external applications (like Claude Code, Cursor, TypingMind) to your free local pools seamlessly.

---

## 🚀 1. Getting Started

Start the Divine TUI (Terminal User Interface) by running:
```bash
python main.py
```
This will launch both the **Web Dashboard (Port 8000)** and the **Proxy Server (Port 8001)**.

---

## 🎛️ 2. Web Dashboard Configuration

Open `http://127.0.0.1:8000` to access the Divine Dashboard. Here you can configure:
- **Routing Pools:** Assign specific AI models to `fast`, `reasoning`, or `coding` tasks.
- **Proxy Gateway:**
  - **Model Aliases:** Spoof requests. For example, if Claude Code asks for `claude-3-5-sonnet-20241022`, you can alias it to `Mistral, codestral-latest`.
  - **External App API Keys:** Generate custom keys (e.g. `sk-claudecode-123`) to authenticate and track external app usage.

---

## 🔌 3. Hooking up External Apps

By pointing your applications to `http://127.0.0.1:8001`, Divine acts as a middleman, translating requests into standard AI payloads and routing them to your configured models.

### Example A: Claude Code (Anthropic Format)
Claude Code officially only supports Anthropic models. Divine translates Anthropic API calls into OpenAI/Mistral format transparently!

**Windows (PowerShell):**
```powershell
$env:ANTHROPIC_BASE_URL="http://127.0.0.1:8001/proxy/code"
$env:ANTHROPIC_API_KEY="sk-claudecode-123"
claude
```

**Mac/Linux:**
```bash
export ANTHROPIC_BASE_URL="http://127.0.0.1:8001/proxy/code"
export ANTHROPIC_API_KEY="sk-claudecode-123"
claude
```

### Example B: Cursor / Codex CLI (OpenAI Format)
Cursor and other OpenAI-compatible apps can route to the generic chat or code endpoints.

**Windows (PowerShell):**
```powershell
$env:OPENAI_BASE_URL="http://127.0.0.1:8001/proxy/code/v1"
$env:OPENAI_API_KEY="sk-cursor-123"
```

**Mac/Linux:**
```bash
export OPENAI_BASE_URL="http://127.0.0.1:8001/proxy/code/v1"
export OPENAI_API_KEY="sk-cursor-123"
```

---

## 🧠 Architecture Overview
- **`proxy/server.py`**: The universal translation layer. Handles SSE streaming and tool translations.
- **`engine/orchestrator.py`**: The OmniEngine that intelligently routes requests to various providers (Groq, Mistral, OpenRouter, etc.).
- **`frontend/app.py`**: The GUI dashboard and settings API.
- **`config/`**: Securely stores your keys, routing configurations, and aliases.
