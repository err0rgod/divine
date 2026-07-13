"""
Agent Router API Client & Provider Documentation

PROVIDER INFO:
- URL: https://agentrouter.org/v1
- Endpoint Style: OpenAI format (/chat/completions) and Anthropic format (/messages)
- WAF/Protection: STRICT. Requires specific client fingerprinting headers to avoid 'unauthorized_client_error'.
  Required Headers:
    - User-Agent: codex_cli_rs/0.101.0 (Windows NT 10.0; x86_64)
    - Originator: codex_cli_rs
    - Version: 0.101.0

AVAILABLE MODELS:
1. 'claude-opus-4-8' - Anthropic's Opus 4.8. (Heavy reasoning / architecture).
2. 'claude-opus-4-6' - Anthropic's Opus 4.6.
3. 'claude-opus-4-7' - Anthropic's Opus 4.7.
4. 'gpt-5.5' - OpenAI model alias.
5. 'glm-5.2' - ChatGLM alias.

Note: AgentRouter is our primary heavyweight model provider. Because of the WAF fingerprinting, 
we use the proxy.py script to bridge Claude Code CLI to this provider seamlessly.
"""

import requests
import json
import sys


API_KEY = ""
BASE_URL = "https://agentrouter.org/v1"
MODEL = "claude-opus-4-8"

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}",
    "User-Agent": "codex_cli_rs/0.101.0 (Windows NT 10.0; x86_64)",
    "Originator": "codex_cli_rs",
    "Version": "0.101.0",
}


def chat(prompt, max_tokens=1024, conversation=None):
    """Send a message to Claude Opus 4.8 via Agent Router."""
    if conversation is None:
        conversation = []

    conversation.append({"role": "user", "content": prompt})

    payload = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "messages": conversation,
    }

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


def main():
    """Interactive chat loop with Claude Opus 4.8."""
    print("=" * 60)
    print("  Claude Opus 4.8 via Agent Router")
    print("  Account: github_210841 | Key: err0rgodv1")
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

        print(f"\033[33mOpus 4.8 > \033[0m{reply}")
        print(f"\033[90m[tokens: {usage.get('prompt_tokens', '?')} in / {usage.get('completion_tokens', '?')} out]\033[0m\n")


if __name__ == "__main__":
    main()
