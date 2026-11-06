from datetime import date
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Job, JobProfile, utcnow
from app.services.search_service import search_web
from app.services.ats_postings import SUPPORTED_HOSTS, posting_identity, posting_urls
from app.services import ats_postings
import asyncio
import re
from sqlalchemy import or_


def build_queries(profile: JobProfile) -> list[str]:
    queries = []

    roles = profile.target_roles[:2]

    locations = [
        location
        for location in profile.preferred_locations
        if location.lower() != "remote"
        and len(location) > 2
    ]

    for role in roles:

        for location in locations[:1]:
            queries.append(
                f'"{role}" jobs {location}'
            )

        if profile.remote_ok:
            queries.append(
                f'"{role}" remote jobs'
            )

    # No more than four Tavily searches.
    return list(dict.fromkeys(queries))[:4]


def time_range_for_days(days: int) -> str:
    if days <= 1:
        return "day"

    if days <= 7:
        return "week"

    if days <= 31:
        return "month"

    return "year"


def get_freshness(
    posted: str | None,
    max_days: int,
) -> float | None:

    if not posted:
        return None

    try:
        posted_day = date.fromisoformat(posted)
    except ValueError:
        return None

    days = (date.today() - posted_day).days

    if days < 0 or days > max_days:
        return 0

    if days <= 3:
        return 100

    if days <= 7:
        return 85

    if days <= 14:
        return 65

    return 40


def get_location_score(
    location: str | None,
    profile: JobProfile,
) -> float | None:

    if not location:
        return None

    location = location.lower()

    if "remote" in location:
        return 100 if profile.remote_ok else 20

    preferred = [
        item.lower()
        for item in profile.preferred_locations
        if len(item) > 2
        and item.lower() != "remote"
    ]

    if not preferred:
        return None

    for item in preferred:
        if item in location:
            return 100

    return 30


def valid_url(url: str) -> bool:
    parsed = urlparse(url)

    return (
        parsed.scheme in {"http", "https"}
        and bool(parsed.netloc)
    )


def search_queries(keywords: list[str], locations: list[str], remote_ok: bool) -> list[str]:
    places = [place for place in locations if place.lower() != "remote"]
    if remote_ok or any(place.lower() == "remote" for place in locations):
        places.insert(min(1, len(places)), "remote")
    # Interleave roles so a long location list cannot consume the whole budget.
    queries = [f'"{role}" {place} jobs' for place in (places or [""]) for role in keywords]
    return list(dict.fromkeys(queries))[:8]


async def search_jobs(db: AsyncSession, keywords: list[str], locations: list[str],
                      posted_within_days: int, remote_ok: bool, min_relevance_score: int,
                      strict_dates: bool = False) -> list[Job]:
    keywords = list(dict.fromkeys(word.strip() for word in keywords if word.strip()))
    locations = list(dict.fromkeys(place.strip() for place in locations if place.strip()))
    if not keywords:
        raise ValueError("Enter at least one job keyword.")
    candidates = {}
    search_limit = asyncio.Semaphore(4)

    async def discover(query):
        async with search_limit:
            return await search_web(query=query, max_results=5,
                                    time_range=time_range_for_days(posted_within_days),
                                    include_domains=list(SUPPORTED_HOSTS))

    searches = await asyncio.gather(*(discover(query) for query in search_queries(keywords, locations, remote_ok)))
    for results in searches:
        for result in results:
            identity = posting_identity(result.get("url"))
            if identity:
                candidates.setdefault(identity, result)

    # At most 20 official checks per search, with four requests in flight.
    limiter = asyncio.Semaphore(4)

    async def verify(result):
        async with limiter:
            return await ats_postings.fetch_posting(result["url"])

    selected = list(candidates.items())[:20]
    postings = await asyncio.gather(*(verify(result) for _, result in selected))
    matched = []
    for (identity, result), posting in zip(selected, postings):
        aliases = posting_urls(identity)
        existing = await db.execute(select(Job).where(or_(
            Job.source_url.in_([result["url"], *aliases]), Job.application_url.in_(aliases),
        )).order_by(Job.id))
        job = existing.scalars().first()
        if job is None:
            job = Job(title=(result.get("title") or "Untitled posting")[:300],
                      source_url=aliases[0], source=identity[0])
        job.availability_status = posting.status
        job.availability_checked_at = utcnow()
        job.last_seen = utcnow()
        if posting.status == "open":
            job.title = posting.title[:300]
            if posting.company and (not job.company or posting.company != identity[1]):
                job.company = posting.company[:200]
            job.location = posting.location[:200] if posting.location else None
            job.snippet = posting.description
            job.posted_date_text = posting.posted_date
            job.application_url = posting.application_url
            job.link_status = "verified_ats"
        elif not job.snippet:
            job.snippet = result.get("content") or ""
        # Search-provider dates and ATS update times are not publication evidence.
        posted = posting.posted_date if posting.status == "open" else None
        freshness = get_freshness(posted, posted_within_days)
        if posting.status == "unavailable" or freshness == 0 or (strict_dates and freshness is None):
            continue
        tokens = set(re.findall(r"[a-z0-9+#]+", f"{job.title} {job.snippet or ''}".lower()))
        # Roles are alternatives: matching one complete role should score 100,
        # not be penalized because the user supplied another career direction.
        term_tokens = [set(re.findall(r"[a-z0-9+#]+", keyword.lower())) for keyword in keywords]
        score = max((100 * len(term & tokens) / len(term) for term in term_tokens if term), default=0)
        if score == 0 or score < min_relevance_score:
            continue
        # Filter only when official location metadata is known.
        location = (job.location or "").lower()
        is_remote = "remote" in location
        places = [place.lower() for place in locations if place.lower() != "remote"]
        if is_remote and not remote_ok and "remote" not in [place.lower() for place in locations]:
            continue
        if location and places and not any(place in location for place in places) and not (remote_ok and is_remote):
            continue
        job.match_score = round(score, 1)
        job.final_score = round(score, 1)
        job.freshness_score = freshness or 0
        job.location_score = 100 if location else 0
        if job.id is None:
            db.add(job)
        matched.append(job)
    await db.commit()
    # Response validation accesses defaults such as timestamps, populated by flush.
    return sorted(matched, key=lambda job: (job.availability_status == "open", job.match_score), reverse=True)
