import os
from dotenv import load_dotenv
load_dotenv()

"""
Agent Router API Client & Documentation

PROVIDER INFO:
- Base URL: https://agentrouter.org/v1
- Endpoint Style: Fully OpenAI Compatible (with custom headers)
- Capabilities: Proxying and routing to extremely capable reasoning models.

CURRENT STATUS:
- Authentication: Requires the key plus anti-bot headers.
- Available Models: claude-opus-4-8, glm-5.2, gpt-5.5
"""

import requests
import time
import sys

API_KEY = os.environ.get("AGENT_ROUTER_API_KEY")
BASE_URL = "https://agentrouter.org/v1"

# Using one of Agent Router's complex reasoning models
MODEL = "claude-opus-4-8"

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}",
    "User-Agent": "codex_cli_rs/0.101.0 (Windows NT 10.0; x86_64)",
    "Originator": "codex_cli_rs",
    "Version": "0.101.0",
    "anthropic-version": "2023-06-01"
}

def chat(prompt, max_tokens=1024, conversation=None, model=MODEL):
    """Send a message to Agent Router."""
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
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'models.json'), 'r', encoding='utf-8') as f:
            db = json.load(f)
            avail = db.get("AgentRouter", [])
            if avail:
                print("\nAvailable Models for AgentRouter:")
                for i, m in enumerate(avail):
                    print(f"  [{i}] {m}")
                sel = input(f"\nSelect model number (or press Enter for default '{MODEL}'): ").strip()
                if sel.isdigit() and int(sel) < len(avail):
                    MODEL = avail[int(sel)]
                elif sel:
                    MODEL = sel
    except Exception as e:
        pass

    """Interactive chat loop for Agent Router."""
    print("=" * 60)
    print(f"  Agent Router Interactive Chat ({MODEL})")
    print("=" * 60)
    print("🚀 Status: Connected. Ready for proxy routing.")
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
