import os
from dotenv import load_dotenv
load_dotenv()

"""
Open Router API Client & Provider Documentation

PROVIDER INFO:
- URL: https://openrouter.ai/api/v1/chat/completions
- Endpoint Style: OpenAI Compatible AND Anthropic Compatible! (Universal Translator)
- WAF/Protection: None. Highly reliable API gateway.
- Special Headers:
  - HTTP-Referer (Optional but recommended: to identify your app)
  - X-Title (Optional but recommended: to identify your app)

CURRENT STATUS:
- Authentication: The API key works perfectly!
- Account Tier: Free Tier. The key has 'is_free_tier: true', meaning there is no paid balance.
- Because it's on the Free Tier, you must append ':free' to the model names or use models explicitly listed as free on OpenRouter.

WHY OPEN ROUTER IS SPECIAL:
Unlike NVIDIA NIM or Bluesmind, Open Router has a built-in translation engine. If you point Claude Code's Anthropic-style requests to Open Router, it will seamlessly translate them to OpenAI-style models in the background without throwing 404 errors!

AVAILABLE FREE MODELS (26 Models Detected):
tencent/hy3:free, poolside/laguna-xs-2.1:free, cohere/north-mini-code:free, nvidia/nemotron-3.5-content-safety:free, nvidia/nemotron-3-ultra-550b-a55b:free, nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free, poolside/laguna-m.1:free, google/gemma-4-26b-a4b-it:free, google/gemma-4-31b-it:free, google/lyria-3-pro-preview, google/lyria-3-clip-preview, nvidia/nemotron-3-super-120b-a12b:free, openrouter/free, liquid/lfm-2.5-1.2b-thinking:free, liquid/lfm-2.5-1.2b-instruct:free, nvidia/nemotron-3-nano-30b-a3b:free, nvidia/nemotron-nano-12b-v2-vl:free, qwen/qwen3-next-80b-a3b-instruct:free, nvidia/nemotron-nano-9b-v2:free, openai/gpt-oss-120b:free, openai/gpt-oss-20b:free, qwen/qwen3-coder:free, cognitivecomputations/dolphin-mistral-24b-venice-edition:free, meta-llama/llama-3.3-70b-instruct:free, meta-llama/llama-3.2-3b-instruct:free, nousresearch/hermes-3-llama-3.1-405b:free
"""

import requests
import json
import sys
import time

API_KEY = os.environ.get("OPENROUTER_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1"

# Using a free model because the key is on the free tier
MODEL = "meta-llama/llama-3.2-3b-instruct:free"

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}",
    "HTTP-Referer": "https://github.com/err0rgod",
    "X-Title": "Divine Project"
}

def chat(prompt, max_tokens=1024, conversation=None, model=MODEL):
    """Send a message to Open Router."""
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
            avail = db.get("OpenRouter", [])
            if avail:
                print("\nAvailable Models for OpenRouter:")
                for i, m in enumerate(avail):
                    print(f"  [{i}] {m}")
                sel = input(f"\nSelect model number (or press Enter for default '{MODEL}'): ").strip()
                if sel.isdigit() and int(sel) < len(avail):
                    MODEL = avail[int(sel)]
                elif sel:
                    MODEL = sel
    except Exception as e:
        pass

    """Interactive chat loop for Open Router."""
    print("=" * 60)
    print("  Open Router Interactive Chat")
    print("=" * 60)
    print("⚠️  Status: Using Free Tier models only (e.g. ':free' suffix)")
    print("=" * 60)
    print()

    if not API_KEY:
        print("⚠️  Please set OPENROUTER_API_KEY in your .env file first!")
        return

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
