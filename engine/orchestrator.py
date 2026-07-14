import os
import requests
import json
import random
from dotenv import load_dotenv

load_dotenv('D:/divine/.env')

PROVIDERS = {
    "Groq": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "key": os.environ.get('GROQ_API_API_KEY')
    },
    "Mistral": {
        "url": "https://api.mistral.ai/v1/chat/completions",
        "key": os.environ.get('MISTRAL_API_API_KEY')
    },
    "Cerebras": {
        "url": "https://api.cerebras.ai/v1/chat/completions",
        "key": os.environ.get('CEREBRAS_API_KEY')
    },
    "NVIDIA": {
        "url": "https://integrate.api.nvidia.com/v1/chat/completions",
        "key": os.environ.get('NVIDIA_NIM_API_KEY')
    },
    "Bazaarlink": {
        "url": "https://bazaarlink.ai/api/v1/chat/completions",
        "key": os.environ.get('BAZAARLINK_API_API_KEY')
    },
    "Cohere": {
        "url": "https://api.cohere.com/v1/chat",  # Native endpoint
        "key": os.environ.get('COHERE_API_API_KEY')
    },
    "Bluesmind": {
        "url": "https://api.bluesminds.com/v1/chat/completions",
        "keys": [k.strip() for k in os.environ.get('BLUESMIND_API_KEYS', os.environ.get('BLUESMIND_API_KEY', '')).split(',') if k.strip()],
        "key": os.environ.get('BLUESMIND_API_KEY')
    },
    "AgentRouter": {
        "url": "https://agentrouter.org/v1/chat/completions",
        "key": os.environ.get('AGENT_ROUTER_API_KEY', 'err0rgodv1')
    },
    "ForgeAI": {
        "url": "https://forge-gateway-api.fly.dev/v1/chat/completions",
        "keys": [k.strip() for k in os.environ.get('FORGE_AI_API_KEYS', os.environ.get('FORGE_AI_API_KEY', '')).split(',') if k.strip()],
        "key": os.environ.get('FORGE_AI_API_KEY')
    },
    "FuturePPO": {
        "url": "https://api.futureppo.top/v1/chat/completions",
        "keys": [k.strip() for k in os.environ.get('FUTUREPPO_API_KEYS', os.environ.get('FUTUREPPO_API_KEY', '')).split(',') if k.strip()],
        "key": os.environ.get('FUTUREPPO_API_KEY')
    },
    "DeepSeek": {
        "url": "https://api.deepseek.com/chat/completions",
        "keys": [k.strip() for k in os.environ.get('DEEPSEEK_API_KEYS', os.environ.get('DEEPSEEK_API_KEY', '')).split(',') if k.strip()],
        "key": os.environ.get('DEEPSEEK_API_KEY')
    }
}

ROUTING_POOLS = {
    "coding": [
        ("Mistral", "codestral-latest"),
        ("Mistral", "mistral-large-latest"),
        ("ForgeAI", "gpt-5.3-codex"),
        ("NVIDIA", "qwen/qwen3.5-397b-a17b"),
        ("NVIDIA", "meta/llama-3.1-70b-instruct")
    ],
    "reasoning": [
        ("AgentRouter", "opus 4.8"),
        ("AgentRouter", "gpt 5.5"),
        ("AgentRouter", "glm 5.2"),
        ("ForgeAI", "claude-sonnet-4-6-thinking"),
        ("ForgeAI", "gpt-5.5"),
        ("NVIDIA", "deepseek-ai/deepseek-v4-pro"),
        ("NVIDIA", "z-ai/glm-5.2")
    ],
    "fast": [
        ("Cerebras", "gpt-oss-120b"),
        ("Cerebras", "gemma-4-31b"),
        ("Groq", "llama-3.3-70b-versatile"),
        ("Groq", "llama-3.1-8b-instant"),
        ("Mistral", "magistral-medium-latest"),
        ("NVIDIA", "meta/llama-3.1-8b-instruct"),
        ("NVIDIA", "moonshotai/kimi-k2.6")
    ],
    "rag": [
        ("Cohere", "command-a-plus-05-2026"),
        ("Cohere", "command-a-reasoning-08-2025")
    ],
    "fallback": [
        ("Bazaarlink", "auto:free"),
        ("Bluesmind", "meta/llama-3.1-8b-instruct")
    ]
}

class OmniEngine:
    def __init__(self):
        pass

    def search(self, query):
        """Web search using Exa, fallback to Jina."""
        exa_key = os.environ.get("EXA_SEARCH_API_KEY")
        if exa_key:
            try:
                headers = {"x-api-key": exa_key, "Content-Type": "application/json"}
                res = requests.post("https://api.exa.ai/search", headers=headers, json={"query": query}, timeout=10)
                if res.status_code == 200:
                    return {"source": "exa", "results": res.json().get("results", [])}
            except Exception as e:
                print("Exa failed:", e)
        
        # Fallback to Jina
        print("Falling back to Jina Search...")
        jina_key = os.environ.get("JINA_SEARCH_API_KEY")
        headers = {"Authorization": f"Bearer {jina_key}"} if jina_key else {}
        try:
            res = requests.get(f"https://s.jina.ai/{query}", headers=headers, timeout=10)
            if res.status_code == 200:
                return {"source": "jina", "results": res.text}
        except Exception as e:
            pass
        return {"source": "none", "results": None}

    def scrape(self, url):
        """Scrape page using Firecrawl, fallback to Jina."""
        fc_key = os.environ.get("FIRECRAWL_API_KEY")
        if fc_key:
            try:
                headers = {"Authorization": f"Bearer {fc_key}", "Content-Type": "application/json"}
                res = requests.post("https://api.firecrawl.dev/v1/scrape", headers=headers, json={"url": url}, timeout=15)
                if res.status_code == 200:
                    return {"source": "firecrawl", "content": res.json().get("data", {}).get("markdown", "")}
            except Exception as e:
                print("Firecrawl failed:", e)
                
        # Fallback to Jina
        print("Falling back to Jina Reader...")
        jina_key = os.environ.get("JINA_SEARCH_API_KEY")
        headers = {"Authorization": f"Bearer {jina_key}"} if jina_key else {}
        try:
            res = requests.get(f"https://r.jina.ai/{url}", headers=headers, timeout=15)
            if res.status_code == 200:
                return {"source": "jina", "content": res.text}
        except Exception as e:
            pass
        return {"source": "none", "content": None}

    def chat(self, provider_name, model_name, messages, max_tokens=1024, auto_failover=True):
        """Standardized chat completion across all providers with automatic failover."""
        if provider_name not in PROVIDERS:
            raise ValueError(f"Unknown provider: {provider_name}")

        prov = PROVIDERS[provider_name]
        
        # Support multiple API keys for load balancing
        keys = prov.get('keys', [prov.get('key')])
        if not keys or not keys[0]:
            raise ValueError(f"No API key configured for {provider_name}")
            
        selected_key = random.choice(keys).strip()
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {selected_key}"
        }

        # AgentRouter specific headers (WAF Fingerprinting bypass)
        if provider_name == "AgentRouter":
            headers["User-Agent"] = "codex_cli_rs/0.101.0 (Windows NT 10.0; x86_64)"
            headers["Originator"] = "codex_cli_rs"
            headers["Version"] = "0.101.0"

        # Construct Payload depending on provider
        if provider_name == "Cohere":
            # Cohere uses /v1/chat and requires 'message' + 'chat_history'
            chat_history = []
            preamble = ""
            for msg in messages[:-1]:
                if msg["role"] == "system":
                    preamble += msg["content"] + "\n"
                else:
                    role = "USER" if msg["role"] == "user" else "CHATBOT"
                    chat_history.append({"role": role, "message": msg["content"]})
                
            payload = {
                "model": model_name,
                "message": messages[-1]["content"],
                "chat_history": chat_history,
                "temperature": 0.7
            }
            if preamble:
                payload["preamble"] = preamble.strip()
        else:
            # Standard OpenAI formatting
            payload = {
                "model": model_name,
                "messages": messages,
                "max_tokens": max_tokens
            }

        try:
            response = requests.post(prov['url'], headers=headers, json=payload, timeout=60)
            if response.status_code == 200:
                data = response.json()
                
                # Extract reply text depending on provider formatting
                if provider_name == "Cohere":
                    reply_text = data.get("text", "")
                    usage = data.get("meta", {}).get("tokens", {})
                else:
                    reply_text = data['choices'][0]['message']['content']
                    usage = data.get('usage', {})
                    
                return {
                    "success": True,
                    "content": reply_text,
                    "usage": usage,
                    "provider": provider_name,
                    "model": model_name
                }
            else:
                error_resp = f"HTTP {response.status_code}: {response.text}"
        except Exception as e:
            error_resp = str(e)
            
        # If we reach here, the request failed.
        if auto_failover:
            print(f"[Divine Engine] {provider_name}/{model_name} failed ({error_resp[:100]}). Initiating failover...")
            fallback_queue = [
                ("Mistral", "mistral-large-latest"),
                ("Groq", "llama-3.3-70b-versatile"),
                ("Bazaarlink", "auto:free")
            ]
            
            # Remove the failed provider from the queue
            fallback_queue = [p for p in fallback_queue if p[0] != provider_name]
            
            # If a deepseek model failed, prioritize official DeepSeek
            if "deepseek" in model_name.lower():
                fallback_queue.insert(0, ("DeepSeek", "deepseek-v4-pro"))
            
            for fb_prov, fb_model in fallback_queue:
                print(f"[Divine Engine] Failing over to {fb_prov}/{fb_model}...")
                fallback_res = self.chat(fb_prov, fb_model, messages, max_tokens, auto_failover=False)
                if fallback_res['success']:
                    fallback_res['failover_occurred'] = True
                    fallback_res['original_provider'] = provider_name
                    fallback_res['error_caught'] = error_resp
                    return fallback_res
                    
        return {"success": False, "error": error_resp}

    def auto_route(self, messages, force_task_type=None):
        """
        The Intelligent Router. Routes requests to optimal model pools using
        a round-robin/random choice selection to evenly distribute load among the best models.
        """
        if force_task_type and force_task_type in ROUTING_POOLS:
            task_type = force_task_type
        else:
            # Use Groq to classify the task rapidly
            last_message = messages[-1]['content'] if messages else ""
            meta_prompt = f"""
Analyze the user's prompt and classify it into EXACTLY ONE of these task types: 'coding', 'reasoning', 'rag', or 'fast'.
- 'coding': Writing scripts, fixing bugs, programming logic.
- 'reasoning': Complex questions, math, deep logic, research.
- 'rag': Document summarization, retrieving specific info from context.
- 'fast': Casual chat, simple questions, translation.

User prompt: "{last_message}"

Reply STRICTLY in JSON format with exactly one key "task_type". Example:
{{"task_type": "coding"}}
"""
            routing_decision = self.chat(
                provider_name="Groq",
                model_name="llama-3.1-8b-instant",
                messages=[{"role": "system", "content": meta_prompt}],
                auto_failover=False
            )
            
            task_type = "fast" # default
            if routing_decision['success']:
                try:
                    raw_json = routing_decision['content'].strip().replace('```json', '').replace('```', '')
                    decision = json.loads(raw_json)
                    task_type = decision.get('task_type', 'fast').lower()
                except json.JSONDecodeError:
                    pass
                    
            if task_type not in ROUTING_POOLS:
                task_type = "fast"

        pool = ROUTING_POOLS[task_type]
        provider, model = random.choice(pool)
        return provider, model

engine = OmniEngine()
