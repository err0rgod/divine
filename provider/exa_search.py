import os

from dotenv import load_dotenv

load_dotenv()

"""
Exa Search API Client & Documentation

PROVIDER INFO:
- URL: https://api.exa.ai/search
- Capabilities: Exa is a semantic search engine built explicitly for AI. Instead of keyword matching like Google, it understands the *meaning* of the query.
- Use Case: Deep web research, finding specific articles, datasets, or company documentation.
- Note: The user mentioned in 'working.txt' that Exa "very good has a mcp" (Model Context Protocol), making it great for Agent orchestration!

CURRENT STATUS:
- Authentication: The API key works perfectly!
"""


import requests

API_KEY = os.environ.get("EXA_SEARCH_API_KEY")
BASE_URL = "https://api.exa.ai"

HEADERS = {"Content-Type": "application/json", "x-api-key": API_KEY}


def search(query, num_results=5):
    """Perform a semantic search using Exa."""
    payload = {
        "query": query,
        "numResults": num_results,
        "useAutoprompt": True,  # Exa will optimize the query automatically
    }

    try:
        response = requests.post(
            f"{BASE_URL}/search",
            headers=HEADERS,
            json=payload,
            timeout=15,
        )

        if response.status_code != 200:
            print(f"Error {response.status_code}: {response.text}")
            return None

        return response.json().get("results", [])
    except Exception as e:
        print(f"Request failed: {e}")
        return None


def main():
    """Interactive search loop for Exa."""
    print("=" * 60)
    print("  Exa Semantic Search Interactive CLI")
    print("=" * 60)
    print("  Type 'quit' to exit.")
    print("=" * 60)
    print()

    while True:
        try:
            query = input("\033[36mSearch Exa > \033[0m").strip()
        except EOFError, KeyboardInterrupt:
            print("\nBye!")
            break

        if not query:
            continue
        if query.lower() == "quit":
            break

        print("\033[90mSearching...\033[0m")
        results = search(query)

        if not results:
            print("\033[31mNo results found.\033[0m\n")
            continue

        print("\n\033[32m--- Search Results ---\033[0m")
        for i, res in enumerate(results, 1):
            title = res.get("title", "No Title")
            url = res.get("url", "No URL")
            print(f"\033[33m{i}. {title}\033[0m")
            print(f"   {url}")
        print()


if __name__ == "__main__":
    main()
