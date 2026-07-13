# Divine Superpowers Implementation Plan

This document outlines the architecture and implementation steps for adding "superpowers" to the Divine AI engine. 
These features will be planned iteratively and executed in a single batch later.

## 1. File Uploads & Basic Text Parsing
- **Frontend Design**: Add a sleek "paperclip" icon inside the chat input box. When files are selected, they appear as floating thumbnail "chips" above the text area with an "X" to remove them before sending.
- **Backend Flow**: A `POST /api/upload` endpoint in FastAPI handles the files and saves them to a `context/uploads/` directory on the hard drive.
- **Basic Parsing**: For standard text files (`.txt`, `.py`, `.json`, etc.), the backend automatically extracts the raw text and injects it invisibly into the user's prompt as context (e.g., `[Attached File: script.py] \n ...contents...`).

## 2. OCR & Image Vision
- **Multimodal Models**: If the user selects a model with vision capabilities (e.g., Gemini 1.5 Pro), inject the image directly as base64 into the JSON payload natively.
- **Text-Only Models**: If a text-only model is selected, intercept the image, run it through a lightweight Python OCR library (like `pytesseract` or `easyocr`) to extract the text, and silently inject the text into the prompt.

## 3. PDF Handling & RAG (Document Parsing)
**Primary Strategy (Cohere API):**
- Leverage Cohere's native superpower for document handling. When large documents are uploaded, we pass them directly into Cohere's RAG/Document endpoints, allowing their engine to handle the heavy lifting, chunking, and grounding natively.

**Fallback Strategy (Local Chunking):**
- If Cohere is unavailable or a different provider is strictly required, we will fallback to a famous open-source chunking/splitting strategy (e.g., recursive character splitting via a lightweight library like `langchain-text-splitters` or similar). We will extract the text, chunk it, and dynamically inject the most relevant chunks into the context window.

## 4. Web Search (The "Beast Mode" Pipeline)
Instead of basic DuckDuckGo, we will build an advanced agentic scraping pipeline:
1. **The Trigger**: The model realizes it needs external information (e.g., "Who is Nirbhay Katiyar?") and invokes a search command.
2. **Exa Search (The Finder)**: We query Exa Search, which is purpose-built for AI, to find the absolute best, most relevant top 5 URLs.
3. **Firecrawl (The Deep Scraper)**: We pass those 5 URLs to Firecrawl. Firecrawl will bypass JS/captchas and aggressively scrape the inner contents of those pages, returning clean, LLM-ready markdown.
4. **Jina AI (The Reader)**: We use Jina AI (`r.jina.ai`) as an ultra-fast secondary reader. If Firecrawl hits a roadblock on a specific URL, Jina instantly converts the URL into markdown. 
5. **Context Injection**: All of this scraped data is formatted and injected into the prompt, allowing the model to answer perfectly based on real-time data.

## 5. Local File Creation & Management
- **The Protocol**: The model outputs strict XML tags: `<create_file path="D:/my_projects/frontend/styles.css">...code...</create_file>`. 
- **Specific Path Generation**: The system supports absolute and relative paths. The user can dictate exactly where the file should be created anywhere on their machine, and the backend handles the directory creation automatically.
- **Frontend UI Integration**: Instead of a wall of code, the UI swaps the XML for an interactive widget: `✅ Created styles.css (Open | Revert)`.

## 6. "Agent Loop" Mode (Autonomous Execution)
- **The Switch**: We add a "Loop" toggle next to the Reasoning switch in the header.
- **The Behavior**: When turned ON, the model doesn't just reply once. It enters a self-reflective loop on the backend. It will iteratively perform Web Searches, read files, generate code, and evaluate its own results. 
- **Real-Time Visibility**: Instead of blocking the user with a generic loading spinner, the UI will stream live "thought logs" of exactly what the agent is doing in the background (e.g., *`> Searching web for Nirbhay Katiyar...`*, *`> Running script... Error found, rewriting code...`*). You can watch its entire thought process unfold live until it delivers the final perfect result.

## 7. Command Line Execution (Terminal Agent)
- **The Protocol**: The model can output a strict XML tag: `<execute_cmd>python test.py</execute_cmd>`.
- **Backend Execution**: FastAPI intercepts this tag and safely runs the subprocess in a dedicated directory. It captures `stdout` and `stderr` (the console output/errors) and silently feeds it back to the AI.
- **Synergy with Agent Loop**: Combined with the Agent Loop, the model can write code, run it, observe the crash logs, and fix the bugs entirely on its own before replying to you.

## 8. Long-Term Persistent Memory (The Brain)
- **Memory Store**: We create a local `memory.json` or SQLite database.
- **The Protocol**: The model uses a `<save_memory>` tag when it learns something important (e.g. user preferences, API keys, project architecture). 
- **Context Injection**: Every new chat session silently reads from this memory bank and injects it into the system prompt. The model will never forget your preferences across different sessions or days.
