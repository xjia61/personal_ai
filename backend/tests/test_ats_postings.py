import asyncio
from unittest.mock import patch

import httpx
import pytest

from app.services.ats_postings import fetch_posting, posting_identity, publication_date


@pytest.mark.parametrize("url,expected", [
    ("https://boards.greenhouse.io/example/jobs/123?source=search", ("greenhouse", "example", "123")),
    ("https://job-boards.greenhouse.io/example/jobs/123", ("greenhouse", "example", "123")),
    ("https://jobs.lever.co/example/id/apply", ("lever", "example", "id")),
    ("https://jobs.lever.co.evil.invalid/example/id", None),
    ("https://user:password@jobs.lever.co/example/id", None),
    ("https://jobs.lever.co/example/../admin", None),
    ("https://jobs.lever.co/example", None),
    ("https://jobs.lever.co:bad/example/id", None),
    (None, None),
])
def test_posting_identity(url, expected):
    assert posting_identity(url) == expected


@pytest.mark.parametrize("status,expected", [(404, "unavailable"), (410, "unavailable"),
                                            (429, "unknown"), (500, "unknown"), (302, "unknown")])
def test_ats_http_status(status, expected):
    async def run():
        client = httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(status)))
        with patch("app.services.ats_postings.httpx.AsyncClient", return_value=client):
            assert (await fetch_posting("https://jobs.lever.co/example/id")).status == expected
    asyncio.run(run())


def test_timeout_is_unknown_not_closed():
    def timeout(request):
        raise httpx.ReadTimeout("test timeout", request=request)

    async def run():
        client = httpx.AsyncClient(transport=httpx.MockTransport(timeout))
        with patch("app.services.ats_postings.httpx.AsyncClient", return_value=client):
            assert (await fetch_posting("https://jobs.lever.co/example/id")).status == "unknown"
    asyncio.run(run())


def test_greenhouse_normalizes_official_data_and_publication_date():
    async def run():
        def response(request):
            assert str(request.url) == "https://boards-api.greenhouse.io/v1/boards/example/jobs/123"
            return httpx.Response(200, json=dict(id=123, title="Python Engineer", company_name="Example Inc",
                location={"name": "Chicago, IL"}, content="&lt;p&gt;Python &amp; SQL&lt;/p&gt;",
                first_published="2026-10-30T10:00:00Z", updated_at="2026-10-31T10:00:00Z",
                absolute_url="https://custom.invalid/careers?gh_jid=123"))
        client = httpx.AsyncClient(transport=httpx.MockTransport(response))
        with patch("app.services.ats_postings.httpx.AsyncClient", return_value=client):
            posting = await fetch_posting("https://boards.greenhouse.io/example/jobs/123")
        assert posting.status == "open"
        assert posting.company == "Example Inc"
        assert posting.description == "Python & SQL"
        assert posting.posted_date == "2026-10-30"
        assert posting.application_url == "https://boards.greenhouse.io/example/jobs/123"
    asyncio.run(run())


def test_lever_unknown_date_and_mismatched_application_link():
    async def run():
        client = httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=dict(
            id="id", text="Engineer", categories={"location": "Remote"}, descriptionPlain="Python",
            applyUrl="https://jobs.lever.co/another/different/apply", updated_at="2026-10-31"))))
        with patch("app.services.ats_postings.httpx.AsyncClient", return_value=client):
            posting = await fetch_posting("https://jobs.lever.co/example/id")
        assert posting.status == "open"
        assert posting.posted_date is None
        assert posting.application_url == "https://jobs.lever.co/example/id/apply"
    asyncio.run(run())


@pytest.mark.parametrize("data", [[], {}, {"id": "other", "text": "Engineer"},
    {"id": "id", "text": "Engineer", "categories": "not-an-object"}])
def test_bad_provider_data_is_unknown(data):
    async def run():
        client = httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=data)))
        with patch("app.services.ats_postings.httpx.AsyncClient", return_value=client):
            assert (await fetch_posting("https://jobs.lever.co/example/id")).status == "unknown"
    asyncio.run(run())


def test_invalid_publication_dates_are_unknown():
    for value in (None, "", "bad", 1770000000):
        assert publication_date(value) is None
