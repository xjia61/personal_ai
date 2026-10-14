import hashlib

from openai import AsyncOpenAI

from app.config import settings

from app.schemas import (
    JobRequirementExtraction,
)


client = AsyncOpenAI(
    api_key=settings.openai_api_key
)


MAX_JOB_TEXT_LENGTH = 20000


def build_job_source_text(
    title: str,
    description: str,
) -> str:

    title = title.strip()
    description = description.strip()

    text = (
        f"JOB TITLE:\n{title}\n\n"
        f"JOB DESCRIPTION:\n{description}"
    )

    return text[:MAX_JOB_TEXT_LENGTH]


def hash_job_description(
    source_text: str,
) -> str:

    normalized = (
        source_text
        .replace("\r\n", "\n")
        .strip()
    )

    return hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()


async def extract_job_requirements(
    source_text: str,
) -> JobRequirementExtraction:

    response = await client.responses.parse(

        model=settings.openai_model,

        instructions="""
You extract structured job requirements.

Use ONLY information explicitly supported by
the supplied job posting.

Do not infer requirements that are not stated.

Classification rules:

1. required_items:
   Put qualifications here when the posting
   explicitly presents them as required,
   minimum qualifications, must-have, or
   clearly mandatory qualifications.

2. preferred_items:
   Only use when the posting describes them
   as preferred, bonus, desired, nice-to-have,
   plus, or similar.

3. unclassified_items:
   Use this when something appears to be a
   qualification but the posting does not
   clearly indicate whether it is required
   or preferred.

4. responsibilities:
   Job duties belong here. Do not treat normal
   job responsibilities as candidate
   qualifications unless the posting clearly
   states them as qualifications.

Categories:
- skill
- experience
- education
- certification
- domain
- other

Keep each item concise.
Remove duplicates.
Do not evaluate the candidate.
Do not calculate a match score.
""",

        input=source_text,

        text_format=JobRequirementExtraction,
    )

    result = response.output_parsed

    if result is None:
        raise RuntimeError(
            "Requirement extraction returned no structured output."
        )

    return result