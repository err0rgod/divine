import os
import random
from dotenv import load_dotenv
load_dotenv()

"""
Forge AI API Client & Documentation

PROVIDER INFO:
- Base URL: https://forge-gateway-api.fly.dev/v1
- Endpoint Style: Fully OpenAI Compatible
- Capabilities: Unified API gateway providing access to cutting-edge open and proprietary models.

CURRENT STATUS:
- Authentication: Requires API key. Supports multiple comma-separated keys for load balancing.
- Available Models: gpt-5.6-luna, claude-sonnet-5, deepseek-v4-pro, grok-4.5, and more.
"""

import requests
import time
import sys

# Support fetching multiple keys separated by commas for load-balancing
KEYS_STRING = os.environ.get("FORGE_AI_API_KEYS", os.environ.get("FORGE_AI_API_KEY", ""))
KEYS = [k.strip() for k in KEYS_STRING.split(",") if k.strip()]

BASE_URL = "https://forge-gateway-api.fly.dev/v1"

# Default Model
MODEL = "gpt-5.6-luna"

def chat(prompt, max_tokens=1024, conversation=None, model=MODEL):
    """Send a message to Forge AI using round-robin/random API keys."""
    if not KEYS:
        print("Error: No Forge AI API key configured in .env")
        return None, conversation
        
    if conversation is None:
        conversation = []

    conversation.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": conversation,
    }
    
    # Pick a random key from the pool to avoid rate limits
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
    """Interactive chat loop for Forge AI."""
    print("=" * 60)
    print(f"  Forge AI Interactive Chat ({MODEL})")
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
