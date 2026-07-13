import os
import requests

try:
    from exa_py import Exa
    EXA_API_KEY = os.environ.get("EXA_SEARCH_API_KEY", "")
    if not EXA_API_KEY:
        EXA_API_KEY = os.environ.get("EXA_API_KEY", "")
    exa = Exa(api_key=EXA_API_KEY) if EXA_API_KEY else None
except ImportError:
    exa = None

def search_web(query: str) -> str:
    if not exa:
        return "Exa search is not configured (missing EXA_API_KEY or exa_py not installed)."
    try:
        results = exa.search(query, num_results=3)
        out = f"Search Results for '{query}':\n"
        for res in results.results:
            out += f"- {res.title} ({res.url})\n"
            # Use Jina to scrape the content
            try:
                jina_resp = requests.get(f"https://r.jina.ai/{res.url}", timeout=10)
                if jina_resp.status_code == 200:
                    content = jina_resp.text[:1500] # Limit content length
                    out += f"  Content snippet: {content}...\n\n"
            except:
                pass
        return out
    except Exception as e:
        return f"Web search failed: {str(e)}"
