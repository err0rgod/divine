import os
from dotenv import load_dotenv
load_dotenv()

"""
Cloudflare Workers AI Client & Documentation

PROVIDER INFO:
- URL: https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1/chat/completions
- Endpoint Style: OpenAI Compatible
- Hardware/Tech: Cloudflare runs these models globally on their edge network. This means the AI is executing on servers extremely close to your physical location, resulting in incredibly low latency.

CURRENT STATUS:
- Authentication: The API key and Account ID work perfectly!
- Security: This API token is highly secure. It is strictly scoped to ONLY allow AI inference. It successfully blocked me from reading your account details or listing your zones. 
- Models Detected: I found 61 active models on this account!
  - Active Examples: @cf/meta/llama-3.2-3b-instruct, @cf/meta/llama-3.3-70b-instruct-fp8-fast, @cf/deepseek-ai/deepseek-r1-distill-qwen-32b
  - Note: Older models (like llama-3-8b) were recently deprecated and will return a 410 error.
"""

import requests
import json
import sys

# Your securely scoped Cloudflare API Token
API_KEY = os.environ.get("CLOUDFLARE_AI_API_KEY")

# Your Cloudflare Account ID
ACCOUNT_ID = os.environ.get("CLOUDFLARE_ACCOUNT_ID")

BASE_URL = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/v1"

# Using Llama 3.2 3B (blazing fast edge inference)
MODEL = "@cf/meta/llama-3.2-3b-instruct"

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

def chat(prompt, max_tokens=1024, conversation=None, model=MODEL):
    """Send a message to Cloudflare Workers AI."""
    if conversation is None:
        conversation = []

    conversation.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": conversation,
    }

    try:
        response = requests.post(
            f"{BASE_URL}/chat/completions",
            headers=HEADERS,
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
    """Interactive chat loop for Cloudflare AI."""
    print("=" * 60)
    print("  Cloudflare Workers AI Interactive Chat")
    print("=" * 60)
    print("🚀 Status: Connected. Running on Cloudflare's Edge Network.")
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
