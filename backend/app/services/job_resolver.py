import re
from urllib.parse import urlparse

import httpx

from app.services.search_service import search_web


GREENHOUSE_HOSTS = {
    "boards.greenhouse.io",
    "job-boards.greenhouse.io",
}

LEVER_HOSTS = {
    "jobs.lever.co",
    "jobs.eu.lever.co",
}


def safe_https_url(url: str) -> bool:
    parsed = urlparse(url)

    host = (parsed.hostname or "").lower()

    if parsed.scheme != "https":
        return False

    if not host or parsed.username or parsed.password:
        return False

    if host == "localhost":
        return False

    if host.endswith((".local", ".internal")):
        return False

    # Do not accept direct IP addresses.
    import ipaddress

    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        return True


def ats_info(url: str):
    parsed = urlparse(url)

    host = (parsed.hostname or "").lower()

    parts = [
        part
        for part in parsed.path.split("/")
        if part
    ]

    if (
        host in GREENHOUSE_HOSTS
        and len(parts) >= 3
        and parts[1] == "jobs"
        and parts[2].isdigit()
    ):
        return (
            "greenhouse",
            parts[0],
            parts[2],
            "https://boards-api.greenhouse.io",
        )

    if (
        host in LEVER_HOSTS
        and len(parts) >= 2
        and re.fullmatch(r"[a-zA-Z0-9-]+", parts[1])
    ):
        api_host = (
            "https://api.eu.lever.co"
            if host == "jobs.eu.lever.co"
            else "https://api.lever.co"
        )

        return (
            "lever",
            parts[0],
            parts[1],
            api_host,
        )

    return None


def title_matches(expected: str, actual: str) -> bool:
    stop_words = {
        "job", "jobs", "careers", "apply",
        "hiring", "at", "the",
    }

    def tokens(text):
        return set(
            re.findall(r"[a-z0-9]+", text.lower())
        ) - stop_words

    a = tokens(expected)
    b = tokens(actual)

    if not a or not b:
        return False

    levels = {
        "senior", "sr", "junior", "jr",
        "lead", "staff", "principal",
        "manager", "director", "intern",
    }

    if (a & levels) != (b & levels):
        return False

    overlap = a & b

    return (
        len(overlap) >= 2
        and len(overlap) / len(b) >= 0.75
    )


async def verify_ats(
    url: str,
    expected_title: str,
):
    info = ats_info(url)

    if info is None:
        return None, "needs_review"

    provider, site, job_id, api_host = info

    if provider == "greenhouse":
        api_url = (
            f"{api_host}/v1/boards/"
            f"{site}/jobs/{job_id}"
        )
    else:
        api_url = (
            f"{api_host}/v0/postings/"
            f"{site}/{job_id}"
        )

    try:
        async with httpx.AsyncClient(
            timeout=12.0,
            follow_redirects=False,
        ) as client:
            response = await client.get(api_url)

    except httpx.HTTPError:
        return None, "needs_review"

    if response.status_code == 404:
        return None, "unavailable"

    if response.status_code != 200:
        return None, "needs_review"

    data = response.json()

    if not title_matches(
        expected_title,
        data.get("title", data.get("text", "")),
    ):
        return None, "needs_review"

    if provider == "greenhouse":
        final_url = data.get("absolute_url")
    else:
        final_url = (
            data.get("applyUrl")
            or data.get("hostedUrl")
        )

    if final_url and safe_https_url(final_url):
        return final_url, "verified_ats"

    return None, "needs_review"


async def resolve_job_link(job):
    # Respect a link explicitly confirmed by the user.
    if (
        job.link_status == "user_confirmed"
        and job.application_url
    ):
        return job.application_url, "user_confirmed"

    # First try an official ATS URL already found.
    if ats_info(job.source_url):
        return await verify_ats(
            job.source_url,
            job.title,
        )

    # If the original result is an aggregator,
    # make at most one fallback Tavily search.
    if not job.company:
        return None, "needs_review"

    query = (
        f'"{job.company}" "{job.title}" '
        "jobs Greenhouse Lever apply"
    )

    results = await search_web(
        query=query,
        max_results=5,
    )

    for result in results:
        url = result.get("url", "")

        if not ats_info(url):
            continue

        resolved, status = await verify_ats(
            url,
            job.title,
        )

        if status == "verified_ats":
            return resolved, status

    return None, "needs_review"