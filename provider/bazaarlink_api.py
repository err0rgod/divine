import os
from dotenv import load_dotenv
load_dotenv()

"""
Bazaarlink.ai API Client & Documentation

PROVIDER INFO:
- Base URL: https://bazaarlink.ai/api/v1
- Endpoint Style: Fully OpenAI Compatible
- Note: This is an AI API Gateway. Note that the endpoint does NOT use the 'api.' subdomain (unlike the models endpoint).

CURRENT STATUS:
- Authentication: The API key is valid and works perfectly!
- Available Models: The API returned 339 models!
- Limit: As noted in 'working.txt', this has a strict 10 RPM (Requests Per Minute) limit. Be careful not to loop requests.
- Recommended Model: The user noted to use 'auto:free' or specific models. In testing, 'qwen3.7-plus' worked instantly.
"""

import requests
import json
import sys

API_KEY = os.environ.get("BAZAARLINK_API_API_KEY")
BASE_URL = "https://bazaarlink.ai/api/v1"

# The user explicitly noted to use 'auto:free' in working.txt, but specific models also work.
MODEL = "auto:free"

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

def chat(prompt, max_tokens=1024, conversation=None, model=MODEL):
    """Send a message to Bazaarlink.ai."""
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
    global MODEL
    import json
    try:
        with open('../models.json' if os.path.exists('../models.json') else 'models.json', 'r') as f:
            db = json.load(f)
            avail = db.get("Bazaarlink", [])
            if avail:
                print("\nAvailable Models for Bazaarlink:")
                for i, m in enumerate(avail):
                    print(f"  [{i}] {m}")
                sel = input(f"\nSelect model number (or press Enter for default '{MODEL}'): ").strip()
                if sel.isdigit() and int(sel) < len(avail):
                    MODEL = avail[int(sel)]
                elif sel:
                    MODEL = sel
    except Exception as e:
        pass

    """Interactive chat loop for Bazaarlink."""
    print("=" * 60)
    print("  Bazaarlink AI Gateway Interactive Chat")
    print("=" * 60)
    print("⚠️  Warning: Strict 10 RPM Limit. Do not spam requests.")
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
