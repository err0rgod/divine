import json
import os
from threading import Lock

CONFIG_FILE = "D:/divine/config/dashboard_config.json"
STATS_FILE = "D:/divine/config/dashboard_stats.json"

class StateManager:
    def __init__(self):
        self.lock = Lock()
        self._init_files()

    def _init_files(self):
        if not os.path.exists(CONFIG_FILE):
            # Read from .env initially to populate config
            from dotenv import dotenv_values
            env_vars = dotenv_values("D:/divine/.env")
            initial_keys = {}
            
            # Map of known prefixes to correct provider names
            env_mapping = {
                "GROQ": "Groq",
                "MISTRAL": "Mistral",
                "CEREBRAS": "Cerebras",
                "NVIDIA": "NVIDIA",
                "BAZAARLINK": "Bazaarlink",
                "COHERE": "Cohere",
                "BLUESMIND": "Bluesmind",
                "AGENT_ROUTER": "AgentRouter",
                "FORGE_AI": "ForgeAI",
                "FUTUREPPO": "FuturePPO",
                "DEEPSEEK": "DeepSeek",
                "EXA": "Exa",
                "FIRECRAWL": "Firecrawl",
                "JINA": "Jina"
            }
            
            for k, v in env_vars.items():
                if "API_KEY" in k and v:
                    # Find matching provider
                    provider_name = None
                    for prefix, name in env_mapping.items():
                        if k.startswith(prefix):
                            provider_name = name
                            break
                    
                    if provider_name:
                        if provider_name not in initial_keys:
                            initial_keys[provider_name] = []
                        
                        # Avoid duplicates
                        new_keys = [x.strip() for x in v.split(",") if x.strip()]
                        for key in new_keys:
                            if key not in initial_keys[provider_name]:
                                initial_keys[provider_name].append(key)
            
            with open(CONFIG_FILE, 'w') as f:
                json.dump({"keys": initial_keys}, f, indent=4)

        if not os.path.exists(STATS_FILE):
            with open(STATS_FILE, 'w') as f:
                json.dump({
                    "total_tokens": 0,
                    "total_savings_usd": 0.0,
                    "requests_made": 0,
                    "provider_usage": {}
                }, f, indent=4)

    def get_keys(self):
        with self.lock:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f).get("keys", {})

    def update_keys(self, keys_dict):
        with self.lock:
            data = {"keys": keys_dict}
            with open(CONFIG_FILE, 'w') as f:
                json.dump(data, f, indent=4)
            # Also sync back to .env? (Optional, but good for local CLI tools)
            self._sync_to_env(keys_dict)

    def _sync_to_env(self, keys_dict):
        env_path = "D:/divine/.env"
        if not os.path.exists(env_path):
            return
        with open(env_path, 'r') as f:
            lines = f.readlines()
            
        new_lines = []
        for line in lines:
            if "=" in line:
                k = line.split("=")[0]
                provider = k.split("_")[0].capitalize()
                if provider in keys_dict and "API_KEY" in k:
                    # Don't keep duplicates if we overwrite
                    continue
            new_lines.append(line)
            
        # Append new keys
        for provider, key_list in keys_dict.items():
            if key_list:
                key_str = ",".join(key_list)
                if provider.upper() == "NVIDIA":
                    new_lines.append(f"NVIDIA_NIM_API_KEY={key_str}\n")
                else:
                    new_lines.append(f"{provider.upper()}_API_KEYS={key_str}\n")
                    new_lines.append(f"{provider.upper()}_API_KEY={key_list[0]}\n")
                
        with open(env_path, 'w') as f:
            f.writelines(new_lines)

    def get_stats(self):
        with self.lock:
            with open(STATS_FILE, 'r') as f:
                return json.load(f)

    def add_usage(self, provider, model, tokens):
        """Estimate savings and track usage"""
        with self.lock:
            with open(STATS_FILE, 'r') as f:
                stats = json.load(f)

            stats["total_tokens"] += tokens
            stats["requests_made"] += 1
            
            if provider not in stats["provider_usage"]:
                stats["provider_usage"][provider] = 0
            stats["provider_usage"][provider] += tokens

            # Rough estimate of savings (Assume OpenAI GPT-4 costs $0.03/1k tokens on avg, and open source is free or super cheap)
            # We'll say we save $0.025 per 1k tokens by using Groq/Mistral/etc instead of OpenAI
            savings_per_1k = 0.025
            if provider in ["Groq", "Mistral", "Cloudflare", "Bazaarlink", "Cerebras"]:
                savings_per_1k = 0.03 # Saved full cost
            elif provider in ["AgentRouter", "ForgeAI", "Bluesmind", "DeepSeek"]:
                savings_per_1k = 0.015 # Cheaper than OpenAI but still costs
                
            stats["total_savings_usd"] += (tokens / 1000.0) * savings_per_1k

            with open(STATS_FILE, 'w') as f:
                json.dump(stats, f, indent=4)

state_manager = StateManager()
