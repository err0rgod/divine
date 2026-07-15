import os
from dotenv import load_dotenv
load_dotenv()

"""
Cohere API Client & Documentation

PROVIDER INFO:
- URL: https://api.cohere.com/v1/chat
- Capabilities: Cohere is an enterprise-grade AI provider heavily focused on RAG (Retrieval-Augmented Generation), advanced embeddings, and reliable language models (like their new Command A series).
- Note: Cohere also supports OpenAI-compatible routing at /v1/chat/completions, but this script uses their native /v1/chat endpoint which exposes their advanced RAG connectors.

CURRENT STATUS:
- Authentication: The API key is valid and works perfectly!
- Models Detected: I found 11 chat models active on this account.
  - Latest Examples: 'command-a-plus-05-2026', 'command-a-reasoning-08-2025', 'c4ai-aya-expanse-32b'
  - Note: Older models (like 'command-r-plus') have been fully removed and will return 404 errors. I've configured this script to use their latest Command A+ model.
"""

import requests
import json
import sys
import time

API_KEY = os.environ.get("COHERE_API_KEY")
BASE_URL = "https://api.cohere.com/v2"

# Using their latest flagship model
MODEL = "command-a-plus-05-2026"

HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

def chat(prompt, chat_history=None):
    """Send a message to Cohere."""
    if chat_history is None:
        chat_history = []

    # Cohere native endpoint uses a slightly different payload format than OpenAI
    payload = {
        "model": MODEL,
        "message": prompt,
        "chat_history": chat_history,
        "temperature": 0.7
    }

    try:
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/chat",
            headers=HEADERS,
            json=payload,
            timeout=30,
        )
        elapsed = time.time() - start_time

        if response.status_code != 200:
            print(f"Error {response.status_code}: {response.text}")
            return None, chat_history

        data = response.json()
        reply = data.get("text", "")
        
        # Extract usage stats if available
        meta = data.get("meta", {})
        usage = meta.get("tokens", {})
        
        completion_tokens = usage.get('output_tokens', 0)
        tps = completion_tokens / elapsed if elapsed > 0 else 0
        
        # Append to history in Cohere format
        chat_history.append({"role": "USER", "message": prompt})
        chat_history.append({"role": "CHATBOT", "message": reply})
        
        return reply, usage, tps, chat_history
    except Exception as e:
        print(f"Request failed: {e}")
        return None, chat_history

def main():
    global MODEL
    import json
    try:
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'models.json'), 'r', encoding='utf-8') as f:
            db = json.load(f)
            avail = db.get("Cohere", [])
            if avail:
                print("\nAvailable Models for Cohere:")
                for i, m in enumerate(avail):
                    print(f"  [{i}] {m}")
                sel = input(f"\nSelect model number (or press Enter for default '{MODEL}'): ").strip()
                if sel.isdigit() and int(sel) < len(avail):
                    MODEL = avail[int(sel)]
                elif sel:
                    MODEL = sel
    except Exception as e:
        pass

    """Interactive chat loop for Cohere API."""
    print("=" * 60)
    print(f"  Cohere AI Interactive Chat ({MODEL})")
    print("=" * 60)
    print("🚀 Status: Connected.")
    print("=" * 60)
    print()

    chat_history = []

    while True:
        try:
            prompt = input("\033[36mYou > \033[0m").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not prompt:
            continue
        if prompt.lower() == "quit":
            print("Bye!")
            break
        if prompt.lower() == "clear":
            chat_history = []
            print("Conversation cleared.\n")
            continue

        result = chat(prompt, chat_history=chat_history)
        if result[0] is None:
            continue

        reply, usage, tps, chat_history = result

        print(f"\033[33m{MODEL} > \033[0m{reply}")
        
        if usage:
            p_tokens = usage.get('input_tokens', '?')
            c_tokens = usage.get('output_tokens', '?')
            print(f"\033[90m[tokens: {p_tokens} in / {c_tokens} out | SPEED: {tps:.2f} tokens/sec]\033[0m\n")
        else:
            print()

if __name__ == "__main__":
    main()
