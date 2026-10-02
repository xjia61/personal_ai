import httpx

from app.config import settings


class WebSearchError(Exception):
    pass


async def search_web(
    query: str,
    max_results: int = 5,
    time_range: str | None = None,
) -> list[dict]:

    if not settings.tavily_api_key:
        raise WebSearchError(
            "TAVILY_API_KEY is missing."
        )

    payload = {
        "query": query,
        "search_depth": "basic",
        "max_results": max_results,
        "include_answer": False,
        "include_raw_content": False,
    }

    if time_range:
        payload["time_range"] = time_range

    headers = {
        "Authorization": f"Bearer {settings.tavily_api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.tavily.com/search",
            headers=headers,
            json=payload,
        )

    if response.status_code != 200:
        raise WebSearchError(
            f"Tavily search failed: {response.status_code}"
        )

    data = response.json()

    return [
        {
            "title": result.get("title", ""),
            "url": result.get("url", ""),
            "content": result.get("content", ""),
            "score": result.get("score"),
            "published_date": result.get("published_date"),
        }
        for result in data.get("results", [])
    ]
"""
async def search_web(
    query: str,
    max_results: int = 5,
) -> list[dict]:
    if not settings.tavily_api_key:
        raise WebSearchError(
            "TAVILY_API_KEY is missing."
        )

    payload = {
        "query": query,
        "search_depth": "basic",
        "max_results": max_results,
        "include_answer": False,
        "include_raw_content": False,
    }

    headers = {
        "Authorization": f"Bearer {settings.tavily_api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.tavily.com/search",
            headers=headers,
            json=payload,
        )

    if response.status_code != 200:
        raise WebSearchError(
            f"Tavily search failed: {response.status_code}"
        )

    data = response.json()

    return [
        {
            "title": result.get("title", ""),
            "url": result.get("url", ""),
            "content": result.get("content", ""),
            "score": result.get("score"),
        }
        for result in data.get("results", [])
    ]
"""