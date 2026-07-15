import os

from dotenv import load_dotenv

load_dotenv()

"""
Jina AI Search API Client & Documentation

PROVIDER INFO:
- URL: https://s.jina.ai/{query}
- Capabilities: Jina AI provides incredibly fast, lightweight web search that returns clean, markdown-formatted results specifically tailored for LLMs to read.
- Use Case: Real-time agentic internet access. (Also supports jina reader for reading raw URLs at r.jina.ai).

CURRENT STATUS:
- Authentication: The API key works perfectly!
"""

import urllib.parse

import requests

API_KEY = os.environ.get("JINA_SEARCH_API_KEY")

HEADERS = {"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"}


def search(query):
    """Perform a web search using Jina."""
    # Jina passes the query directly in the URL
    encoded_query = urllib.parse.quote(query)

    try:
        response = requests.get(
            f"https://s.jina.ai/{encoded_query}",
            headers=HEADERS,
            timeout=15,
        )

        if response.status_code != 200:
            print(f"Error {response.status_code}: {response.text}")
            return None

        return response.json().get("data", [])
    except Exception as e:
        print(f"Request failed: {e}")
        return None


def main():
    """Interactive search loop for Jina AI."""
    print("=" * 60)
    print("  Jina AI Web Search Interactive CLI")
    print("=" * 60)
    print("  Type 'quit' to exit.")
    print("=" * 60)
    print()

    while True:
        try:
            query = input("\033[36mSearch Jina > \033[0m").strip()
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
        for i, res in enumerate(results[:5], 1):
            title = res.get("title", "No Title")
            url = res.get("url", "No URL")
            desc = res.get("description", "")
            print(f"\033[33m{i}. {title}\033[0m")
            print(f"   {url}")
            if desc:
                print(f"   \033[90m{desc[:100]}...\033[0m")
        print()


if __name__ == "__main__":
    main()
