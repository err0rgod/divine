import os
from dotenv import load_dotenv
load_dotenv()

"""
Bluesmind API Client & Provider Documentation

PROVIDER INFO:
- URL: https://api.bluesminds.com/v1
- Endpoint Style: Standard OpenAI format (/chat/completions)
- WAF/Protection: No strict client fingerprinting (unlike AgentRouter, you don't need codex_cli_rs headers).
- Credits: $100 available.

AVAILABLE MODELS (Tested & Verified):
1. 'qwen2.5' - Best for general purpose reasoning (likely the 72B instruction-tuned version).
2. 'qwen3.6-35b-coding' - Specialized for heavy coding tasks.
3. 'qwen3.6-35b-fp8' - 8-bit quantized version of Qwen (faster/cheaper but slight precision drop).
4. 'rollama3-8b' - A lightweight Llama 3 8B fine-tune, good for basic chatting or fast summaries.

Note: Hidden/Premium models (like gpt-4o or claude-3-5) are NOT supported here (returns 503 model_not_found). 
We recommend using Bluesmind for fast, cheap parallel tasks to save premium AgentRouter credits.
"""

import requests
import json
import sys

API_KEY_STRING = os.environ.get("BLUESMIND_API_KEYS", os.environ.get("BLUESMIND_API_KEY", ""))
KEYS = [k.strip() for k in API_KEY_STRING.split(",") if k.strip()]
BASE_URL = "https://api.bluesminds.com/v1"
MODEL = "qwen2.5"

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {KEYS[0] if KEYS else ''}"
}

def get_models():
    """Fetch the list of available models from Bluesmind."""
    try:
        response = requests.get(f"{BASE_URL}/models", headers=HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "data" in data:
                return [model["id"] for model in data["data"]]
        return []
    except Exception:
        return []

def chat(prompt, max_tokens=1024, conversation=None, model=MODEL):
    """Send a message to a Bluesmind model."""
    if conversation is None:
        conversation = []

    conversation.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": conversation,
    }

    import random
    if not KEYS:
        print("Error: No Bluesmind API key configured.")
        return None, conversation
        
    selected_key = random.choice(KEYS)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {selected_key}"
    }

    try:
        response = requests.post(
            f"{BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=120,
        )

        if response.status_code != 200:
            print(f"Error {response.status_code}: {response.text}")
            return None, conversation

        data = response.json()
        reply = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        conversation.append({"role": "assistant", "content": reply})
        return reply, usage, conversation
    except Exception as e:
        print(f"Request failed: {e}")
        return None, conversation

def main():
    """Interactive chat loop for Bluesmind."""
    global MODEL
    import json
    try:
        with open('../models.json' if os.path.exists('../models.json') else 'models.json', 'r') as f:
            db = json.load(f)
            avail = db.get("Bluesmind", [])
            if avail:
                print("\nAvailable Models for Bluesmind:")
                for i, m in enumerate(avail):
                    print(f"  [{i}] {m}")
                sel = input(f"\nSelect model number (or press Enter for default '{MODEL}'): ").strip()
                if sel.isdigit() and int(sel) < len(avail):
                    MODEL = avail[int(sel)]
                elif sel:
                    MODEL = sel
    except Exception as e:
        pass

    print("=" * 60)
    print(f"  Bluesmind Interactive Chat ({MODEL})")
    print("=" * 60)
    print(f"🚀 Status: Connected. Key Pool Size: {len(KEYS)}")
    print("=" * 60)
    print("  Type 'quit' to exit | 'clear' to reset conversation")
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

        reply, usage, conversation = result

        print(f"\033[33m{MODEL} > \033[0m{reply}")
        print(f"\033[90m[tokens: {usage.get('prompt_tokens', '?')} in / {usage.get('completion_tokens', '?')} out]\033[0m\n")

if __name__ == "__main__":
    main()
