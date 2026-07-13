import os
import requests
import json
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
    "OpenRouter": {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "key": os.environ.get('OPENROUTER_API_KEY')
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
    "Google": {
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "key": os.environ.get('GOOGLE_AI_API_KEY')
    }
}

class OmniEngine:
    def __init__(self):
        pass

    def chat(self, provider_name, model_name, messages, max_tokens=1024, auto_failover=True):
        """Standardized chat completion across all providers with automatic failover."""
        if provider_name not in PROVIDERS:
            raise ValueError(f"Unknown provider: {provider_name}")

        prov = PROVIDERS[provider_name]
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {prov['key']}"
        }

        # OpenRouter specific headers
        if provider_name == "OpenRouter":
            headers["HTTP-Referer"] = "https://github.com/err0rgod/divine"
            headers["X-Title"] = "Divine"

        # Construct Payload depending on provider
        if provider_name == "Cohere":
            # Cohere uses /v1/chat and requires 'message' + 'chat_history'
            chat_history = []
            for msg in messages[:-1]:
                role = "USER" if msg["role"] == "user" else "CHATBOT"
                chat_history.append({"role": role, "message": msg["content"]})
                
            payload = {
                "model": model_name,
                "message": messages[-1]["content"],
                "chat_history": chat_history,
                "temperature": 0.7
            }
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
                ("Google", "gemini-1.5-pro"),
                ("OpenRouter", "google/gemini-pro")
            ]
            
            # Remove the failed provider from the queue
            fallback_queue = [p for p in fallback_queue if p[0] != provider_name]
            
            for fb_prov, fb_model in fallback_queue:
                print(f"[Divine Engine] Failing over to {fb_prov}/{fb_model}...")
                fallback_res = self.chat(fb_prov, fb_model, messages, max_tokens, auto_failover=False)
                if fallback_res['success']:
                    fallback_res['failover_occurred'] = True
                    fallback_res['original_provider'] = provider_name
                    fallback_res['error_caught'] = error_resp
                    return fallback_res
                    
        return {"success": False, "error": error_resp}

    def auto_route(self, messages):
        """
        The Meta-Router. Uses Groq to read the user's prompt and decide the best
        provider and model based on the request type (e.g., code -> mistral, fast -> groq).
        """
        last_message = messages[-1]['content'] if messages else ""
        
        meta_prompt = f"""
You are the Divine Meta-Router. Analyze the user's prompt and pick the absolute best provider and model combination to answer it.
We have access to:
- Groq (models: llama-3.1-8b-instant, llama-3.3-70b-versatile, mixtral-8x7b-32768) -> Use for speed, casual chat, translation.
- Mistral (models: codestral-latest, mistral-large-latest) -> Use for heavy coding, scripts, logic.
- Cerebras (models: llama3.1-8b) -> Use for extremely fast answers.
- NVIDIA (models: meta/llama-3.1-70b-instruct) -> Use for heavy reasoning.
- Cohere (models: command-r-plus-08-2024) -> Use for RAG, text summarization, data extraction.

User's prompt: "{last_message}"

Reply STRICTLY in JSON format with exactly two keys: "provider" and "model". Example:
{{"provider": "Mistral", "model": "codestral-latest"}}
Do not output any other text or markdown block.
"""
        # Ask Groq to decide
        routing_decision = self.chat(
            provider_name="Groq",
            model_name="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": meta_prompt}]
        )

        if routing_decision['success']:
            try:
                # Clean up any potential markdown formatting
                raw_json = routing_decision['content'].strip().replace('```json', '').replace('```', '')
                decision = json.loads(raw_json)
                return decision['provider'], decision['model']
            except json.JSONDecodeError:
                # Fallback if Groq messes up the JSON
                return "Groq", "llama-3.3-70b-versatile"
        
        # Absolute fallback if meta-router fails
        return "Mistral", "mistral-large-latest"

engine = OmniEngine()
