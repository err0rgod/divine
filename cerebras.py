import os
from dotenv import load_dotenv
load_dotenv()

"""
Cerebras API Client & Documentation

PROVIDER INFO:
- URL: https://api.cerebras.ai/v1/chat/completions
- Endpoint Style: OpenAI Compatible
- Hardware: Cerebras runs on specialized WSE (Wafer-Scale Engine) AI supercomputer chips, NOT standard Nvidia GPUs.
- Defining Feature: BLISTERING SPEED. Cerebras is renowned for generating tokens at insane speeds (often 100+ to 1000+ tokens per second).

CURRENT STATUS:
- Authentication: The API key works perfectly!
- Available Models:
  1. 'gemma-4-31b' (Extremely fast, smart open-source model)
  2. 'gpt-oss-120b' (Massive 120B parameter model)
  3. 'zai-glm-4.7'
"""

import requests
import time
import sys

API_KEY = os.environ.get("CEREBRAS_API_KEY")
BASE_URL = "https://api.cerebras.ai/v1"

# Using Gemma 31B for balanced logic and blazing speed
MODEL = "gemma-4-31b"

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

def chat(prompt, max_tokens=1024, conversation=None, model=MODEL):
    """Send a message to Cerebras."""
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
    """Interactive chat loop for Cerebras."""
    print("=" * 60)
    print("  Cerebras AI Interactive Chat")
    print("=" * 60)
    print("🚀 Status: Connected. Prepare for high-speed generation.")
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
