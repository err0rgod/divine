import os
import requests
from dotenv import load_dotenv

load_dotenv('D:/divine/.env')

providers = [
    {
        "name": "Groq",
        "url": "https://api.groq.com/openai/v1/models",
        "headers": {"Authorization": f"Bearer {os.environ.get('GROQ_API_API_KEY', '')}"},
        "parser": lambda r: [m['id'] for m in r.json().get('data', [])],
        "notes": "Fastest LPU inference. Strictly rate limited to free tier TPM/RPM."
    },
    {
        "name": "Mistral AI",
        "url": "https://api.mistral.ai/v1/models",
        "headers": {"Authorization": f"Bearer {os.environ.get('MISTRAL_API_API_KEY', '')}"},
        "parser": lambda r: [m['id'] for m in r.json().get('data', [])],
        "notes": "~1 Billion free tokens/month. Perfect for coding (codestral)."
    },
    {
        "name": "Cohere",
        "url": "https://api.cohere.com/v1/models",
        "headers": {"Authorization": f"Bearer {os.environ.get('COHERE_API_API_KEY', '')}"},
        "parser": lambda r: [m['name'] for m in r.json().get('models', []) if 'chat' in m.get('endpoints', [])],
        "notes": "Excellent for RAG. Generous free tier for prototyping."
    },
    {
        "name": "Cerebras",
        "url": "https://api.cerebras.ai/v1/models",
        "headers": {"Authorization": f"Bearer {os.environ.get('CEREBRAS_API_KEY', '')}"},
        "parser": lambda r: [m['id'] for m in r.json().get('data', [])],
        "notes": "Wafer-scale hardware. High tokens/sec."
    },
    {
        "name": "Bazaarlink.ai",
        "url": None, # Hardcoded due to API constraints
        "headers": {},
        "parser": lambda r: ['auto:free'],
        "notes": "STRICT 10 RPM LIMIT. Only 'auto:free' works (internally routes to a random model). Use only as emergency fallback."
    },
    {
        "name": "OpenRouter",
        "url": "https://openrouter.ai/api/v1/models",
        "headers": {"Authorization": f"Bearer {os.environ.get('OPENROUTER_API_KEY', '')}"},
        "parser": lambda r: [m['id'] for m in r.json().get('data', []) if m.get('pricing', {}).get('prompt', '0') == '0'],
        "notes": "Unified gateway. Filtering to show ONLY explicitly free models (cost=0)."
    },
    {
        "name": "NVIDIA NIM",
        "url": "https://integrate.api.nvidia.com/v1/models",
        "headers": {"Authorization": f"Bearer {os.environ.get('NVIDIA_NIM_API_KEY', '')}"},
        "parser": lambda r: [m['id'] for m in r.json().get('data', [])],
        "notes": "1000 free credits/month. Enterprise hardware."
    },
    {
        "name": "Google AI Studio",
        "url": f"https://generativelanguage.googleapis.com/v1beta/models?key={os.environ.get('GOOGLE_AI_API_KEY', '')}",
        "headers": {},
        "parser": lambda r: [m['name'].replace('models/', '') for m in r.json().get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])],
        "notes": "15 RPM, 1 million TPM free tier."
    }
]

with open('D:/divine/models.txt', 'w', encoding='utf-8') as f:
    f.write("# Verified Model Access List\n")
    f.write("# This file contains dynamically verified models pulled directly from the APIs.\n\n")

    for p in providers:
        f.write(f"=================================================\n")
        f.write(f"PROVIDER: {p['name']}\n")
        f.write(f"NOTES/LIMITS: {p['notes']}\n")
        f.write(f"=================================================\n")
        
        try:
            if p['url'] is None:
                # Handle hardcoded models like Bazaarlink
                models = p['parser'](None)
                f.write(f"Total Verified Models: {len(models)}\n\n")
                for m in models:
                    f.write(f"  - {m}\n")
            else:
                print(f"Fetching {p['name']}...")
                res = requests.get(p['url'], headers=p['headers'], timeout=15)
                if res.status_code == 200:
                    models = p['parser'](res)
                    f.write(f"Total Verified Models: {len(models)}\n\n")
                    
                    models.sort()
                    for m in models:
                        f.write(f"  - {m}\n")
                else:
                    f.write(f"Error validating models. HTTP {res.status_code}\n")
                    f.write(f"Details: {res.text[:100]}\n")
        except Exception as e:
            f.write(f"Connection failed: {str(e)}\n")
            
        f.write("\n\n")

print("Done writing to models.txt!")
