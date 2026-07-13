# Omni-Route & Agent Router Configuration Context

## 🎯 Goal
To build **Omni-Route**, a 24/7 autonomous Orchestrator that pools API credits across multiple AI providers, automatically handles rate limits and failovers, and powers our local Agent Router (for Claude Code).

## 🏆 Milestones Completed
1. **Agent Router (Claude Code Proxy):** We successfully built `proxy.py` to transparently intercept, spoof headers, and patch tool-use logic so Claude Code works perfectly with Agent Router.
2. **Provider Arsenal Acquisition:** We vetted, mapped, and secured access to the following "God Tier" API providers, extracting 730+ active models:
   - **Mistral AI:** ~1B free tokens/mo (flagship: `codestral-latest`).
   - **NVIDIA NIM:** 1,000 free credits/mo (enterprise hardware).
   - **Groq:** LPU processing with extreme speeds (80+ tokens/sec).
   - **Cerebras:** High-speed wafer-scale hardware.
   - **Cohere:** Enterprise RAG models.
   - **OpenRouter:** Universal gateway with 160 explicitly free models.
   - **Google AI Studio:** 15 RPM / 1M TPM free tier.
   - **Exa Search & Jina AI:** Web search and markdown scraping.
   - **Bazaarlink.ai:** Emergency fallback gateway.
3. **Security & Refactoring:** We cleanly moved all API keys and Account IDs into `.gitignore` protected `.env` files. We wrote standalone test scripts for every provider and safely stored them in the `provider/` directory.

## 📁 Repository Structure
* `proxy.py`: Transparent interceptor proxy for Claude Code (spoofs headers, patches JSON tool-calls).
* `provider/`: Directory containing standalone test scripts for all verified API providers.
* `models.txt`: A dynamically generated manifest listing all 730+ verified models.
* `.env`: (Ignored by Git) Contains all API keys.
* `context.md`: This architecture and goal documentation.

## 🚀 The Roadmap: What's Next?

### Phase 1: Build the Core Orchestrator (`orchestrator.py`)
Create a central Python class (the "Traffic Cop") to unify all endpoints.
- **Task-based Routing:** Route coding tasks to Mistral (`codestral-latest`), speed tasks to Groq, and web searches to Exa/Jina.
- **Unified Interface:** Standardize inputs/outputs so the rest of the application interacts with one seamless `chat()` function regardless of the underlying provider.

### Phase 2: Credit-Pooling & Failover Engine
Wrap all API calls with dynamic fallback logic. If a primary provider hits a `429 Rate Limit` or `402 Insufficient Credits`, the Orchestrator instantly fails over to the next provider in the queue, ensuring 100% uptime and an endless pool of free tokens.

### Phase 3: Proxy Integration
Connect the Omni-Route Orchestrator directly to `proxy.py`. The proxy will send basic terminal UI requests to Agent Router but delegate heavy automation/backend tasks to Omni-Route.

### Phase 4: 24/7 Autonomous Loop
Create a persistent daemon/container allowing the agent to continuously pull tasks, research, and execute code 24/7, leveraging the massive pooled rate-limits from Mistral and Groq.
