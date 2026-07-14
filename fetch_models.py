import os
import requests
import json
from dotenv import load_dotenv

load_dotenv('D:/divine/.env')

providers = [
    {
        "id": "AgentRouter",
        "url": "https://agentrouter.org/v1/models",
        "headers": {
            "Authorization": f"Bearer {os.environ.get('AGENT_ROUTER_API_KEY', '')}",
            "User-Agent": "codex_cli_rs/0.101.0 (Windows NT 10.0; x86_64)",
            "Originator": "codex_cli_rs",
            "Version": "0.101.0",
            "anthropic-version": "2023-06-01"
        },
        "parser": lambda r: [m['id'] for m in r.json().get('data', [])],
    },
    {
        "id": "Groq",
        "url": "https://api.groq.com/openai/v1/models",
        "headers": {"Authorization": f"Bearer {os.environ.get('GROQ_API_API_KEY', '')}"},
        "parser": lambda r: [m['id'] for m in r.json().get('data', [])],
    },
    {
        "id": "Mistral",
        "url": "https://api.mistral.ai/v1/models",
        "headers": {"Authorization": f"Bearer {os.environ.get('MISTRAL_API_API_KEY', '')}"},
        "parser": lambda r: [m['id'] for m in r.json().get('data', [])],
    },
    {
        "id": "Cohere",
        "url": "https://api.cohere.com/v1/models",
        "headers": {"Authorization": f"Bearer {os.environ.get('COHERE_API_API_KEY', '')}"},
        "parser": lambda r: [m['name'] for m in r.json().get('models', []) if 'chat' in m.get('endpoints', [])],
    },
    {
        "id": "Cerebras",
        "url": "https://api.cerebras.ai/v1/models",
        "headers": {"Authorization": f"Bearer {os.environ.get('CEREBRAS_API_KEY', '')}"},
        "parser": lambda r: [m['id'] for m in r.json().get('data', [])],
    },
    {
        "id": "Bazaarlink",
        "url": None, # Hardcoded due to API constraints
        "headers": {},
        "parser": lambda r: ['auto:free'],
    },
    {
        "id": "OpenRouter",
        "url": "https://openrouter.ai/api/v1/models",
        "headers": {"Authorization": f"Bearer {os.environ.get('OPENROUTER_API_KEY', '')}"},
        "parser": lambda r: [m['id'] for m in r.json().get('data', []) if m.get('pricing', {}).get('prompt', '0') == '0'],
    },
    {
        "id": "NVIDIA",
        "url": "https://integrate.api.nvidia.com/v1/models",
        "headers": {"Authorization": f"Bearer {os.environ.get('NVIDIA_NIM_API_KEY', '')}"},
        "parser": lambda r: [m['id'] for m in r.json().get('data', [])],
    },
    {
        "id": "Google",
        "url": f"https://generativelanguage.googleapis.com/v1beta/models?key={os.environ.get('GOOGLE_AI_API_KEY', '')}",
        "headers": {},
        "parser": lambda r: [m['name'].replace('models/', '') for m in r.json().get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])],
    }
]

def main():
    model_catalog = {"Auto-Select": ["Divine (Meta-Router)"]}
    
    for p in providers:
        provider_id = p["id"]
        print(f"Fetching {provider_id}...")
        try:
            if p['url'] is None:
                models = p['parser'](None)
            else:
                res = requests.get(p['url'], headers=p['headers'], timeout=15)
                if res.status_code == 200:
                    models = p['parser'](res)
                    models.sort()
                else:
                    print(f"  Error {res.status_code}: {res.text[:100]}")
                    models = []
                    
            model_catalog[provider_id] = models
        except Exception as e:
            print(f"  Connection failed: {e}")
            model_catalog[provider_id] = []
            
    with open('D:/divine/models.json', 'w', encoding='utf-8') as f:
        json.dump(model_catalog, f, indent=4)
        
    print("Successfully generated models.json!")

if __name__ == "__main__":
    main()
