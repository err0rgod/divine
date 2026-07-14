import os
from dotenv import load_dotenv
load_dotenv()

"""
NVIDIA NIM API Client & Provider Documentation

PROVIDER INFO:
- URL: https://integrate.api.nvidia.com/v1
- Endpoint Style: OpenAI Compatible (/chat/completions)
- WAF/Protection: None. Standard Bearer token (API Key starts with `nvapi-`).

FREE TIER DETAILS (Researched & Verified):
- Credits: 1,000 free inference credits per month. (Credits are spent per-token. Smaller models burn fewer credits per token than massive 70B models).
- Rate Limits: STRICT 40 Requests Per Minute (RPM) limit. 
- Use Case: Designed for prototyping and development, not high-volume production.
- Model Catalog (121 Models Available):
  01-ai/yi-large, abacusai/dracarys-llama-3.1-70b-instruct, adept/fuyu-8b, ai21labs/jamba-1.5-large-instruct, aisingapore/sea-lion-7b-instruct, baai/bge-m3, bigcode/starcoder2-15b, bytedance/seed-oss-36b-instruct, databricks/dbrx-instruct, deepseek-ai/deepseek-coder-6.7b-instruct, deepseek-ai/deepseek-v4-flash, deepseek-ai/deepseek-v4-pro, google/codegemma-1.1-7b, google/codegemma-7b, google/deplot, google/diffusiongemma-26b-a4b-it, google/gemma-2-2b-it, google/gemma-2b, google/gemma-3-12b-it, google/gemma-3-4b-it, google/gemma-3n-e2b-it, google/gemma-3n-e4b-it, google/gemma-4-31b-it, google/recurrentgemma-2b, ibm/granite-3.0-3b-a800m-instruct, ibm/granite-3.0-8b-instruct, ibm/granite-34b-code-instruct, ibm/granite-8b-code-instruct, meta/codellama-70b, meta/llama-3.1-70b-instruct, meta/llama-3.1-8b-instruct, meta/llama-3.2-11b-vision-instruct, meta/llama-3.2-1b-instruct, meta/llama-3.2-3b-instruct, meta/llama-3.2-90b-vision-instruct, meta/llama-3.3-70b-instruct, meta/llama-4-maverick-17b-128e-instruct, meta/llama-guard-4-12b, meta/llama2-70b, microsoft/kosmos-2, microsoft/phi-3-vision-128k-instruct, microsoft/phi-3.5-moe-instruct, microsoft/phi-4-mini-instruct, microsoft/phi-4-multimodal-instruct, minimaxai/minimax-m2.7, minimaxai/minimax-m3, mistralai/codestral-22b-instruct-v0.1, mistralai/ministral-14b-instruct-2512, mistralai/mistral-7b-instruct-v0.3, mistralai/mistral-large, mistralai/mistral-large-2-instruct, mistralai/mistral-large-3-675b-instruct-2512, mistralai/mistral-medium-3.5-128b, mistralai/mistral-nemotron, mistralai/mistral-small-4-119b-2603, mistralai/mixtral-8x22b-v0.1, mistralai/mixtral-8x7b-instruct-v0.1, moonshotai/kimi-k2.6, nv-mistralai/mistral-nemo-12b-instruct, nvidia/ai-synthetic-video-detector, nvidia/cosmos-reason2-8b, nvidia/embed-qa-4, nvidia/gliner-pii, nvidia/ising-calibration-1-35b-a3b, nvidia/llama-3.1-nemoguard-8b-content-safety, nvidia/llama-3.1-nemoguard-8b-topic-control, nvidia/llama-3.1-nemotron-51b-instruct, nvidia/llama-3.1-nemotron-70b-instruct, nvidia/llama-3.1-nemotron-nano-8b-v1, nvidia/llama-3.1-nemotron-nano-vl-8b-v1, nvidia/llama-3.1-nemotron-safety-guard-8b-v3, nvidia/llama-3.1-nemotron-ultra-253b-v1, nvidia/llama-3.2-nemoretriever-1b-vlm-embed-v1, nvidia/llama-3.2-nv-embedqa-1b-v1, nvidia/llama-3.3-nemotron-super-49b-v1, nvidia/llama-3.3-nemotron-super-49b-v1.5, nvidia/llama-nemotron-embed-1b-v2, nvidia/llama-nemotron-embed-vl-1b-v2, nvidia/llama3-chatqa-1.5-70b, nvidia/mistral-nemo-minitron-8b-8k-instruct, nvidia/nemoretriever-parse, nvidia/nemotron-3-content-safety, nvidia/nemotron-3-nano-30b-a3b, nvidia/nemotron-3-nano-omni-30b-a3b-reasoning, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b, nvidia/nemotron-3.5-content-safety, nvidia/nemotron-4-340b-instruct, nvidia/nemotron-4-340b-reward, nvidia/nemotron-content-safety-reasoning-4b, nvidia/nemotron-mini-4b-instruct, nvidia/nemotron-nano-12b-v2-vl, nvidia/nemotron-nano-3-30b-a3b, nvidia/nemotron-parse, nvidia/neva-22b, nvidia/nv-embed-v1, nvidia/nv-embedcode-7b-v1, nvidia/nv-embedqa-e5-v5, nvidia/nv-embedqa-mistral-7b-v2, nvidia/nvclip, nvidia/nvidia-nemotron-nano-9b-v2, nvidia/riva-translate-4b-instruct, nvidia/riva-translate-4b-instruct-v1.1, nvidia/vila, openai/gpt-oss-120b, openai/gpt-oss-20b, qwen/qwen3-next-80b-a3b-instruct, qwen/qwen3.5-122b-a10b, qwen/qwen3.5-397b-a17b, sarvamai/sarvam-m, snowflake/arctic-embed-l, stepfun-ai/step-3.5-flash, stepfun-ai/step-3.7-flash, stockmark/stockmark-2-100b-instruct, upstage/solar-10.7b-instruct, writer/palmyra-creative-122b, writer/palmyra-fin-70b-32k, writer/palmyra-med-70b, writer/palmyra-med-70b-32k, z-ai/glm-5.2, zyphra/zamba2-7b-instruct

Note: Because of the 40 RPM limit, this is a great secondary provider to put in our Omni-Route pool, but it cannot be the sole provider for a fast-chatting agent.
"""

import requests
import json
import sys

# Replace this with your actual NVIDIA NIM API key when you have it.
API_KEY = os.environ.get("NVIDIA_NIM_API_KEY")
BASE_URL = "https://integrate.api.nvidia.com/v1"
MODEL = "meta/llama-3.1-8b-instruct"

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

def get_models():
    """Fetch the list of available models from NVIDIA NIM."""
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
    """Send a message to NVIDIA NIM."""
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
            avail = db.get("NVIDIA", [])
            if avail:
                print("\nAvailable Models for NVIDIA:")
                for i, m in enumerate(avail):
                    print(f"  [{i}] {m}")
                sel = input(f"\nSelect model number (or press Enter for default '{MODEL}'): ").strip()
                if sel.isdigit() and int(sel) < len(avail):
                    MODEL = avail[int(sel)]
                elif sel:
                    MODEL = sel
    except Exception as e:
        pass

    """Interactive chat loop for NVIDIA NIM."""
    print("=" * 60)
    print("  NVIDIA NIM Interactive Chat")
    print("=" * 60)
    
    if not API_KEY or API_KEY == "nvapi-YOUR_KEY_HERE":
        print("⚠️  Please set NVIDIA_NIM_API_KEY in your .env file or script first!")
        return

    print("Fetching available models...")
    models = get_models()
    if models:
        # Just show the first 10 so we don't flood the terminal
        print(f"Available models (showing first 10): {', '.join(models[:10])}...")
    
    print("=" * 60)
    print("  Type 'quit' to exit | 'clear' to reset")
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
