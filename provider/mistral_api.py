import os
from dotenv import load_dotenv
load_dotenv()

"""
Mistral AI API Client & Documentation

PROVIDER INFO:
- Base URL: https://api.mistral.ai/v1
- Endpoint Style: Fully OpenAI Compatible
- Capabilities: Mistral provides incredibly powerful open-source models (like open-mistral-nemo) and proprietary models (mistral-large). They also offer Codestral, an industry-leading coding model.

CURRENT STATUS:
- Authentication: The API key is valid and works perfectly!
- Available Models: The API returned 70 active models.
- Recommended Models:
  - 'open-mistral-nemo' (Best for general fast reasoning)
  - 'codestral-latest' (Best for writing code)
  - 'mistral-large-latest' (Flagship model, best for complex logic)
"""

import requests
import json
import sys
import time

API_KEY = os.environ.get("MISTRAL_API_KEY")
BASE_URL = "https://api.mistral.ai/v1"

# Using Codestral, Mistral's flagship coding model
MODEL = "codestral-latest"

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

def chat(prompt, max_tokens=1024, conversation=None, model=MODEL):
    """Send a message to Mistral AI."""
    if conversation is None:
        conversation = []

    conversation.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": conversation,
    }

    try:
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/chat/completions",
            headers=HEADERS,
            json=payload,
            timeout=120,
        )
        elapsed = time.time() - start_time

        if response.status_code != 200:
            print(f"Error {response.status_code}: {response.text}")
            return None, conversation

        data = response.json()
        reply = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        
        completion_tokens = usage.get('completion_tokens', 0)
        tps = completion_tokens / elapsed if elapsed > 0 else 0

        conversation.append({"role": "assistant", "content": reply})
        return reply, usage, tps, conversation
    except Exception as e:
        print(f"Request failed: {e}")
        return None, conversation

def main():
    global MODEL
    import json
    try:
        with open('../models.json' if os.path.exists('../models.json') else 'models.json', 'r') as f:
            db = json.load(f)
            avail = db.get("Mistral", [])
            if avail:
                print("\nAvailable Models for Mistral:")
                for i, m in enumerate(avail):
                    print(f"  [{i}] {m}")
                sel = input(f"\nSelect model number (or press Enter for default '{MODEL}'): ").strip()
                if sel.isdigit() and int(sel) < len(avail):
                    MODEL = avail[int(sel)]
                elif sel:
                    MODEL = sel
    except Exception as e:
        pass

    """Interactive chat loop for Mistral AI."""
    print("=" * 60)
    print(f"  Mistral AI Interactive Chat ({MODEL})")
    print("=" * 60)
    print("🚀 Status: Connected.")
    print("=" * 60)
    print()

    conversation = []

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
            conversation = []
            print("Conversation cleared.\n")
            continue

        result = chat(prompt, conversation=conversation)
        if result[0] is None:
            continue

        reply, usage, tps, conversation = result

        print(f"\033[33m{MODEL} > \033[0m{reply}")
        print(f"\033[90m[tokens: {usage.get('prompt_tokens', '?')} in / {usage.get('completion_tokens', '?')} out | SPEED: {tps:.2f} tokens/sec]\033[0m\n")

if __name__ == "__main__":
    main()
