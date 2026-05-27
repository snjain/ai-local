"""Web search tool implementations."""

from httpx import AsyncClient


async def web_search(
    query: str,
    http_client: AsyncClient,
    brave_api_key: str | None,
    searxng_base_url: str | None,
) -> str:
    """
    Search the web using SearXNG (preferred) or Brave API (fallback).
    """
    if searxng_base_url:
        return await _searxng_search(query, http_client, searxng_base_url)
    elif brave_api_key:
        return await _brave_search(query, http_client, brave_api_key)
    return "No search provider configured. Set SEARXNG_BASE_URL or BRAVE_API_KEY."


async def _searxng_search(query: str, http_client: AsyncClient, base_url: str) -> str:
    """Search via SearXNG."""
    try:
        response = await http_client.get(
            f"{base_url}/search",
            params={"q": query, "format": "json"},
        )
        response.raise_for_status()
        data = response.json()

        results = []
        for i, page in enumerate(data.get("results", []), 1):
            if i > 10:
                break
            title = page.get("title", "No title")
            url = page.get("url", "No URL")
            content = page.get("content", "No content")[:300]
            results.append(f"{i}. {title}\n   URL: {url}\n   Content: {content}...\n")

        return "\n".join(results) if results else "No results found."
    except Exception as e:
        return f"SearXNG search error: {e}"


async def _brave_search(query: str, http_client: AsyncClient, api_key: str) -> str:
    """Search via Brave API."""
    try:
        response = await http_client.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={
                "q": query,
                "count": 5,
                "text_decorations": True,
                "search_lang": "en",
            },
            headers={
                "X-Subscription-Token": api_key,
                "Accept": "application/json",
            },
        )
        response.raise_for_status()
        data = response.json()

        results = []
        for item in data.get("web", {}).get("results", [])[:3]:
            title = item.get("title", "")
            description = item.get("description", "")
            url = item.get("url", "")
            if title and description:
                results.append(f"Title: {title}\nSummary: {description}\nSource: {url}\n")

        return "\n".join(results) if results else "No results found."
    except Exception as e:
        return f"Brave search error: {e}"
