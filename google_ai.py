import os
from dotenv import load_dotenv
load_dotenv()

"""
Google AI Studio (Gemini) API Client & Provider Documentation

PROVIDER INFO:
- URL: https://generativelanguage.googleapis.com/v1beta/openai
- Endpoint Style: OpenAI Compatible! (/chat/completions)
- WAF/Protection: None. Uses standard Bearer token (API Key).

AVAILABLE MODELS:
- 'gemini-2.0-flash' (Fast, highly capable, massive context window)

CURRENT STATUS / WARNINGS:
- ⚠️ QUOTA EXCEEDED (429 Error): Your API key currently has a limit of 0 for the free tier. 
  This usually means either your Google Cloud Project (75811095121) needs billing enabled, 
  or your account/IP is in a region where Google does not offer the free tier. 
- Note: 'gemini-2.5-flash' returned a 404 error stating it's not available to new users.
"""

import requests
import json
import sys

API_KEY = os.environ.get("GOOGLE_AI_API_KEY")
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
MODEL = "gemini-2.0-flash"

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

def chat(prompt, max_tokens=1024, conversation=None, model=MODEL):
    """Send a message to Google AI Studio via OpenAI compatibility layer."""
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
    """Interactive chat loop for Google AI Studio."""
    print("=" * 60)
    print("  Google AI Studio Interactive Chat")
    print("=" * 60)
    print("⚠️  Warning: Currently hitting 429 Quota Exceeded on this API key.")
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
