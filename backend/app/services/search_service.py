import httpx

from app.config import settings


class WebSearchError(Exception):
    pass


async def search_web(
    query: str,
    max_results: int = 5,
    time_range: str | None = None,
    include_domains: list[str] | None = None,
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

    if include_domains:
        payload["include_domains"] = include_domains
        payload["include_published_date"] = True
        payload["filter_by_published_date"] = False

    if time_range:
        payload["time_range"] = time_range

    headers = {
        "Authorization": f"Bearer {settings.tavily_api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.tavily.com/search", headers=headers, json=payload,
            )
        if response.status_code != 200:
            raise WebSearchError(f"Search provider failed ({response.status_code}). Please retry.")
        data = response.json()
        if not isinstance(data, dict) or not isinstance(data.get("results"), list):
            raise WebSearchError("Search provider returned an invalid response.")
    except httpx.HTTPError as exc:
        raise WebSearchError("Search provider is unreachable. Please retry.") from exc
    except ValueError as exc:
        raise WebSearchError("Search provider returned an invalid response.") from exc

    return [
        {
            "title": result.get("title", ""),
            "url": result.get("url", ""),
            "content": result.get("content", ""),
            "score": result.get("score"),
            "published_date": result.get("published_date"),
        }
        for result in data.get("results", []) if isinstance(result, dict)
    ]
