import json
from pydantic import BaseModel
from openai import AsyncOpenAI

from app.config import settings


class JobAssessment(BaseModel):
    index: int
    is_specific_job: bool
    company: str | None
    location: str | None
    posted_date: str | None
    match_score: int


class RankingResult(BaseModel):
    assessments: list[JobAssessment]


async def rank_jobs(
    resume: str,
    target_roles: list[str],
    candidates: list[dict],
) -> dict[int, JobAssessment]:

    client = AsyncOpenAI(
        api_key=settings.openai_api_key
    )

    data = [
        {
            "index": i,
            "title": job["title"],
            "content": job["content"][:2000],
            "url": job["url"],
        }
        for i, job in enumerate(candidates)
    ]

    instructions = """
    You are a job-matching assistant.

    Compare each candidate with the resume
    and target roles.

    Rules:
    1. Accept only pages describing a specific
       job vacancy, not search-result pages.
    2. Score suitability from 0 to 100.
    3. Consider required skills, education,
       relevant experience and target role.
    4. Do not assume the applicant has skills
       or experience missing from the resume.
    5. If a description is too incomplete
       to assess properly, do not score
       it above 65.
    6. Extract the company and location
       only when explicitly supported.
    7. Extract a posting date in YYYY-MM-DD
       format only when explicitly provided.
       Do not use the search or crawl date
       as the job posting date.
    8. Use null for unknown information.
    9. Return an assessment for every index.
    """

    response = await client.responses.parse(
        model=settings.openai_model,
        instructions=instructions,
        input=json.dumps(
            {
                "resume": resume[:16000],
                "target_roles": target_roles,
                "candidates": data,
            },
            ensure_ascii=False,
        ),
        text_format=RankingResult,
        store=False,
    )

    parsed = response.output_parsed

    if parsed is None:
        raise RuntimeError(
            "AI ranking returned no structured result."
        )

    return {
        item.index: item
        for item in parsed.assessments
        if 0 <= item.index < len(candidates)
    }