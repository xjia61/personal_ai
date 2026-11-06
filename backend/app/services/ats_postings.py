"""Read-only integrations for public Greenhouse and Lever postings."""
import re
from dataclasses import dataclass
from datetime import datetime
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx

SUPPORTED_HOSTS = ("boards.greenhouse.io", "job-boards.greenhouse.io", "jobs.lever.co")


def posting_identity(url: str) -> tuple[str, str, str] | None:
    try:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port:
            return None
        parts = parsed.path.strip("/").split("/")
        if parsed.hostname in SUPPORTED_HOSTS[:2] and len(parts) == 3 and parts[1] == "jobs" and parts[2].isdigit():
            provider, board, job_id = "greenhouse", parts[0], parts[2]
        elif parsed.hostname == "jobs.lever.co" and len(parts) in (2, 3) and (len(parts) == 2 or parts[2] == "apply"):
            provider, board, job_id = "lever", parts[0], parts[1]
        else:
            return None
        if not all(re.fullmatch(r"[a-zA-Z0-9_-]+", item) for item in (board, job_id)):
            return None
        return provider, board, job_id
    except (ValueError, TypeError, AttributeError):
        return None


def posting_urls(identity: tuple[str, str, str]) -> list[str]:
    provider, board, job_id = identity
    if provider == "greenhouse":
        return [f"https://{host}/{board}/jobs/{job_id}" for host in SUPPORTED_HOSTS[:2]]
    base = f"https://jobs.lever.co/{board}/{job_id}"
    return [base, base + "/apply"]


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def plain_text(content: str) -> str:
    parser = _Text()
    parser.feed(unescape(content))
    return " ".join(" ".join(parser.parts).split())


def publication_date(value) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return None


@dataclass
class Posting:
    status: str
    title: str = ""
    company: str | None = None
    location: str | None = None
    description: str = ""
    application_url: str | None = None
    posted_date: str | None = None


async def fetch_posting(url: str) -> Posting:
    identity = posting_identity(url)
    if identity is None:
        return Posting("unknown")
    provider, board, job_id = identity
    api_url = (f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{job_id}"
               if provider == "greenhouse" else f"https://api.lever.co/v0/postings/{board}/{job_id}")
    try:
        async with httpx.AsyncClient(timeout=12, follow_redirects=False) as client:
            response = await client.get(api_url)
        if response.status_code in (404, 410):
            return Posting("unavailable")
        if response.status_code != 200:
            return Posting("unknown")
        data = response.json()
        if not isinstance(data, dict) or str(data.get("id")) != job_id:
            return Posting("unknown")
        title = data.get("title" if provider == "greenhouse" else "text")
        if not isinstance(title, str) or not title.strip():
            return Posting("unknown")
        # Prefer a direct supported ATS page over custom career-page URLs returned by APIs.
        official = posting_urls(identity)[0]
        if provider == "lever":
            official += "/apply"
        proposed = data.get("absolute_url" if provider == "greenhouse" else "applyUrl")
        if posting_identity(proposed) == identity:
            official = proposed
        location_data = data.get("location" if provider == "greenhouse" else "categories") or {}
        location = location_data.get("name" if provider == "greenhouse" else "location")
        content = data.get("content" if provider == "greenhouse" else "descriptionPlain") or ""
        if provider == "lever" and not content:
            content = data.get("description") or ""
        if not isinstance(location, (str, type(None))) or not isinstance(content, str):
            return Posting("unknown")
        company = data.get("company_name") if provider == "greenhouse" else None
        # Board identifier is a fallback label, not an inferred legal company name.
        company = company if isinstance(company, str) and company else board
        return Posting("open", title.strip(), company, location, plain_text(content), official,
                       publication_date(data.get("first_published")) if provider == "greenhouse" else None)
    except (httpx.HTTPError, ValueError, TypeError, AttributeError):
        return Posting("unknown")


async def check_job(job) -> Posting:
    """Record an attempt separately from job/application workflow status."""
    from app.models import utcnow
    url = job.application_url if posting_identity(job.application_url) else job.source_url
    posting = await fetch_posting(url)
    job.availability_status = posting.status
    job.availability_checked_at = utcnow()
    if posting.status == "open":
        job.application_url = posting.application_url
        job.link_status = "verified_ats"
    return posting
