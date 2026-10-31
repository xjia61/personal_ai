import asyncio
from unittest.mock import patch

import httpx
import pytest

from app.services import search_service


def test_search_normalizes_provider_response_and_passes_filters(monkeypatch):
    monkeypatch.setattr(search_service.settings, "tavily_api_key", "test-only-key")
    requests = []

    def respond(request):
        import json
        requests.append(json.loads(request.content))
        assert request.headers["Authorization"] == "Bearer test-only-key"
        return httpx.Response(200, json={"results": [
            {"title": "Engineer", "url": "https://example.invalid/job",
             "content": "Python", "score": 0.9, "published_date": "2026-10-01"},
            {},
        ]})

    async def run():
        client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
        with patch.object(search_service.httpx, "AsyncClient", return_value=client):
            return await search_service.search_web("Python jobs", 3, "week")

    results = asyncio.run(run())
    assert requests[0]["query"] == "Python jobs"
    assert requests[0]["max_results"] == 3
    assert requests[0]["time_range"] == "week"
    assert results[0]["published_date"] == "2026-10-01"
    assert results[1] == dict(title="", url="", content="", score=None, published_date=None)


def test_search_missing_key_does_not_send_request(monkeypatch):
    monkeypatch.setattr(search_service.settings, "tavily_api_key", "")
    with patch.object(search_service.httpx, "AsyncClient") as client:
        with pytest.raises(search_service.WebSearchError, match="missing"):
            asyncio.run(search_service.search_web("Python jobs"))
        client.assert_not_called()


@pytest.mark.parametrize("status", [401, 429, 500])
def test_search_provider_error(monkeypatch, status):
    monkeypatch.setattr(search_service.settings, "tavily_api_key", "test-only-key")

    async def run():
        client = httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request: httpx.Response(status, text="provider error")
        ))
        with patch.object(search_service.httpx, "AsyncClient", return_value=client):
            with pytest.raises(search_service.WebSearchError, match=str(status)):
                await search_service.search_web("Python jobs")
    asyncio.run(run())
