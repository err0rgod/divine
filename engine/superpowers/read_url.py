import os

import requests


def read_url(url: str) -> str:
    # Try Firecrawl first if API key is present
    fc_key = os.environ.get("FIRECRAWL_API_KEY", "")
    if fc_key:
        try:
            resp = requests.post(
                "https://api.firecrawl.dev/v1/scrape",
                headers={
                    "Authorization": f"Bearer {fc_key}",
                    "Content-Type": "application/json",
                },
                json={"url": url, "formats": ["markdown"]},
                timeout=20,
            )
            if resp.status_code == 200:
                data = resp.json()
                md = data.get("data", {}).get("markdown", "")
                if md:
                    return f"Content from {url} (via Firecrawl):\n{md[:10000]}"
        except:
            pass

    # Fallback to Jina AI
    try:
        jina_resp = requests.get(f"https://r.jina.ai/{url}", timeout=10)
        if jina_resp.status_code == 200:
            return f"Content from {url} (via Jina):\n{jina_resp.text[:10000]}"
    except Exception as e:
        return f"Failed to read URL: {e!s}"

    return f"Failed to extract content from {url}"
