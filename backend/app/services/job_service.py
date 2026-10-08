from datetime import date
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Job, JobProfile, utcnow
from app.services.search_service import search_web
from app.services.job_ranker import rank_jobs


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



async def search_jobs(
    db: AsyncSession,
    keywords: list[str],
    locations: list[str],
    posted_within_days: int,
    remote_ok: bool,
    min_relevance_score: int,
) -> list[Job]:

    # Clean user input
    clean_keywords = [
        keyword.strip()
        for keyword in keywords
        if keyword.strip()
    ]

    clean_locations = [
        location.strip()
        for location in locations
        if location.strip()
    ]

    if not clean_keywords:
        raise ValueError(
            "Please enter at least one job keyword."
        )

    # -----------------------------------
    # 1. Build search queries
    # -----------------------------------

    queries: list[str] = []

    for keyword in clean_keywords:

        # If locations were supplied, search each combination.
        if clean_locations:

            for location in clean_locations:

                if location.lower() == "remote":
                    query = f'"{keyword}" remote job'
                else:
                    query = (
                        f'"{keyword}" "{location}" job'
                    )

                queries.append(query)

        else:

            queries.append(
                f'"{keyword}" job'
            )

    # Avoid unexpectedly large numbers of web calls.
    queries = queries[:8]

    # -----------------------------------
    # 2. Search Tavily
    # -----------------------------------

    candidates: dict[str, dict] = {}

    for query in queries:

        results = await search_web(
            query=query,
            max_results=5,
            time_range=time_range_for_days(
                posted_within_days
            ),
        )

        for result in results:

            url = result.get("url", "")

            if not valid_url(url):
                continue

            # Deduplicate by URL
            candidates[url] = result

    if not candidates:
        return []

    # -----------------------------------
    # 3. Cheap keyword relevance
    # -----------------------------------

    matched_jobs: list[Job] = []

    for result in candidates.values():

        url = result["url"]

        title = (
            result.get("title") or ""
        ).strip()

        snippet = (
            result.get("content") or ""
        ).strip()

        searchable_text = (
            f"{title} {snippet}"
        ).lower()

        # -----------------------------------
        # Keyword relevance
        # -----------------------------------

        matched_keywords = [
            keyword
            for keyword in clean_keywords
            if keyword.lower()
            in searchable_text
        ]

        if not matched_keywords:
            continue

        keyword_score = (
            len(matched_keywords)
            / len(clean_keywords)
        ) * 100

        # Give an extra boost when a target role
        # appears directly in the page title.
        title_matches = [
            keyword
            for keyword in clean_keywords
            if keyword.lower()
            in title.lower()
        ]

        if title_matches:
            relevance_score = (
                keyword_score * 0.6
                + 100 * 0.4
            )
        else:
            relevance_score = (
                keyword_score * 0.8
                + 50 * 0.2
            )

        relevance_score = max(
            0,
            min(100, relevance_score),
        )

        if relevance_score < min_relevance_score:
            continue

        # -----------------------------------
        # Location filter
        # -----------------------------------

        location_score: float | None = None

        if clean_locations:

            location_matches = [
                location
                for location in clean_locations
                if location.lower()
                in searchable_text
            ]

            remote_requested = (
                remote_ok
                and "remote" in searchable_text
            )

            if location_matches or remote_requested:
                location_score = 100
            else:
                # Do not automatically discard jobs
                # when location metadata is unclear.
                location_score = None

        # -----------------------------------
        # Freshness
        # -----------------------------------

        posted = result.get(
            "published_date"
        )

        fresh = get_freshness(
            posted,
            posted_within_days,
        )

        # If we have an explicit date and it is stale,
        # skip the posting.
        if fresh == 0:
            continue

        # -----------------------------------
        # Final score
        # -----------------------------------

        weighted_scores = [
            (relevance_score, 0.70)
        ]

        if fresh is not None:
            weighted_scores.append(
                (fresh, 0.20)
            )

        if location_score is not None:
            weighted_scores.append(
                (location_score, 0.10)
            )

        final_score = (
            sum(
                score * weight
                for score, weight
                in weighted_scores
            )
            /
            sum(
                weight
                for _, weight
                in weighted_scores
            )
        )

        # -----------------------------------
        # Upsert Job
        # -----------------------------------

        existing = await db.execute(
            select(Job).where(
                Job.source_url == url
            )
        )

        job = existing.scalar_one_or_none()

        if job is None:

            job = Job(
                title=title,
                source_url=url,
                source="tavily",
            )

            db.add(job)

        job.title = title

        # We currently do not ask AI to infer these.
        # Preserve existing values if already available.
        job.snippet = snippet
        job.posted_date_text = posted

        job.match_score = round(
            relevance_score,
            1,
        )

        job.freshness_score = round(
            fresh
            if fresh is not None
            else 0,
            1,
        )

        job.location_score = round(
            location_score
            if location_score is not None
            else 0,
            1,
        )

        job.final_score = round(
            final_score,
            1,
        )

        job.last_seen = utcnow()

        matched_jobs.append(job)

    await db.commit()

    return sorted(
        matched_jobs,
        key=lambda job: (
            job.final_score or 0
        ),
        reverse=True,
    )

    


    


    

    queries = build_queries(keywords)

    if not queries:
        raise ValueError(
            "Please configure your target roles and locations."
        )

    candidates = {}

    for query in queries:

        results = await search_web(
            query=query,
            max_results=5,
            time_range=time_range_for_days(
                keywords.posted_within_days
            ),
        )

        for result in results:

            url = result.get("url", "")

            if valid_url(url):
                candidates[url] = result

    if not candidates:
        return []

    candidate_list = list(candidates.values())

    assessments = await rank_jobs(
        resume=profile.resume_text,
        target_roles=profile.target_roles,
        candidates=candidate_list,
    )

    matched_jobs = []

    for index, result in enumerate(candidate_list):

        assessment = assessments.get(index)

        if assessment is None:
            continue

        if not assessment.is_specific_job:
            continue

        url = result["url"]

        posted = assessment.posted_date

        fresh = get_freshness(
            posted,
            keywords.posted_within_days,
        )

        if fresh == 0:
            continue

        loc_score = get_location_score(
            assessment.location,
            keywords,
        )

        match = max(
            0,
            min(100, assessment.match_score),
        )

        # Use only scores supported by available data.
        weighted_scores = [(match, 0.55)]

        if fresh is not None:
            weighted_scores.append(
                (fresh, 0.25)
            )

        if loc_score is not None:
            weighted_scores.append(
                (loc_score, 0.20)
            )

        final = sum(
            score * weight
            for score, weight in weighted_scores
        ) / sum(
            weight
            for _, weight in weighted_scores
        )

        existing = await db.execute(
            select(Job).where(
                Job.source_url == url
            )
        )

        job = existing.scalar_one_or_none()

        if job is None:

            job = Job(
                title=result["title"],
                source_url=url,
                source="tavily",
            )

            db.add(job)

        job.title = result["title"]
        job.company = assessment.company
        job.location = assessment.location

        job.snippet = result.get("content", "")
        job.posted_date_text = posted

        job.match_score = round(match, 1)

        job.freshness_score = round(
            fresh if fresh is not None else 0,
            1,
        )

        job.location_score = round(
            loc_score if loc_score is not None else 0,
            1,
        )

        job.final_score = round(final, 1)
        job.last_seen = utcnow()

        if final >= profile.min_match_score:
            matched_jobs.append(job)

    await db.commit()

    return sorted(
        matched_jobs,
        key=lambda job: job.final_score,
        reverse=True,
    )

