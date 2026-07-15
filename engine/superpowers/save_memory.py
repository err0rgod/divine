import json
import os

CONTEXT_DIR = "D:/divine/context"
MEMORY_FILE = os.path.join(CONTEXT_DIR, "memory.json")


def load_memory() -> str:
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, encoding="utf-8") as f:
                data = json.load(f)
                return "\n".join(data)
        except:
            pass
    return ""


def save_memory(fact: str) -> str:
    data = []
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, encoding="utf-8") as f:
                data = json.load(f)
        except:
            pass
    if fact not in data:
        data.append(fact)

    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    return f"Saved to memory: {fact}"
