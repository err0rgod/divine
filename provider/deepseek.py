import os
import random
from dotenv import load_dotenv
load_dotenv()

"""
DeepSeek API Client

PROVIDER INFO:
- Base URL: https://api.deepseek.com
- Endpoint Style: Fully OpenAI Compatible

Models:
    deepseek-v4-pro
    deepseek-v4-flash
    deepseek-chat
"""

import requests
import time
import sys

# Support fetching multiple keys separated by commas for load-balancing
KEYS_STRING = os.environ.get("DEEPSEEK_API_KEYS", os.environ.get("DEEPSEEK_API_KEY", ""))
KEYS = [k.strip() for k in KEYS_STRING.split(",") if k.strip()]

BASE_URL = "https://api.deepseek.com"

# Default Model
MODEL = "deepseek-v4-flash"

def chat(prompt, max_tokens=1024, conversation=None, model=MODEL):
    """Send a message to DeepSeek using round-robin/random API keys."""
    if not KEYS:
        print("Error: No DeepSeek API key configured in .env")
        return None, conversation
        
    if conversation is None:
        conversation = []

    conversation.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": conversation,
    }
    
    selected_key = random.choice(KEYS)
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {selected_key}"
    }

    try:
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60,
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
            avail = db.get("DeepSeek", [])
            if avail:
                print("\nAvailable Models for DeepSeek:")
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
    print(f"  DeepSeek Interactive Chat ({MODEL})")
    print("=" * 60)
    print(f"🚀 Status: Connected. Key Pool Size: {len(KEYS)}")
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
