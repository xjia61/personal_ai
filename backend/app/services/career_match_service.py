import hashlib
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CareerRecord


from openai import AsyncOpenAI

from app.config import settings
from app.schemas.job_match import (
    CareerMatchExtraction,
)


async def build_career_profile_snapshot(
    db: AsyncSession,
) -> tuple[str, str]:

    result = await db.execute(
        select(CareerRecord).order_by(
            CareerRecord.id
        )
    )

    records = result.scalars().all()

    data = []

    for record in records:
        row = {}

        for column in record.__table__.columns:
            name = column.name
            value = getattr(record, name)

            if value is None:
                continue

            if name in {
                "created_at",
                "updated_at",
            }:
                continue

            row[name] = value

        data.append(row)

    profile_json = json.dumps(
        data,
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )

    profile_hash = hashlib.sha256(
        profile_json.encode("utf-8")
    ).hexdigest()

    return profile_json, profile_hash

client = AsyncOpenAI(
    api_key=settings.openai_api_key
)

async def analyze_career_match(
    requirements_text: str,
    career_profile_text: str,
) -> CareerMatchExtraction:

    prompt = f"""
You are evaluating whether a candidate's actual
career history satisfies a job's qualifications.

Important rules:

1. Evaluate ONLY the listed job requirements.
2. Do not reward unrelated experience.
3. Do not penalize unrelated experience.
4. Use only evidence explicitly present in the
   career profile.
5. Never invent experience, skills, dates,
   certifications, education, or responsibilities.
6. Use these statuses:

satisfied:
The profile clearly supports the requirement.

partial:
The profile has related evidence but does not fully
meet the requirement.

missing:
The profile clearly lacks a requirement.

unknown:
The available career profile does not provide enough
information to determine whether the requirement is met.

7. Do not treat unknown as missing.
8. For every assessment, provide concise supporting
   evidence from the career profile.
9. Keep required and preferred qualifications separate.

JOB REQUIREMENTS:

{requirements_text}

CAREER PROFILE:

{career_profile_text}
"""

    response = await client.responses.parse(
        model=settings.openai_model,
        input=prompt,
        text_format=CareerMatchExtraction,
    )

    return response.output_parsed


STATUS_POINTS = {
    "satisfied": 1.0,
    "partial": 0.5,
    "unknown": 0.25,
    "missing": 0.0,
}

def calculate_match_scores(
    assessments,
) -> tuple[float, float, float]:

    required = [
        item
        for item in assessments
        if item.requirement_type
        == "required"
    ]

    preferred = [
        item
        for item in assessments
        if item.requirement_type
        == "preferred"
    ]

    def score(items):
        if not items:
            return 100.0

        total = sum(
            STATUS_POINTS[item.status]
            for item in items
        )

        return round(
            total / len(items) * 100,
            1,
        )

    required_score = score(required)

    preferred_score = score(preferred)

    if preferred:
        overall = (
            required_score * 0.8
            + preferred_score * 0.2
        )
    else:
        overall = required_score

    return (
        round(overall, 1),
        required_score,
        preferred_score,
    )


def build_requirements_text(
    requirement,
) -> str:

    lines = []

    lines.append("REQUIRED:")

    for item in requirement.required_items:
        lines.append(
            f"- [{item['category']}] "
            f"{item['text']}"
        )

    lines.append("")
    lines.append("PREFERRED:")

    for item in requirement.preferred_items:
        lines.append(
            f"- [{item['category']}] "
            f"{item['text']}"
        )

    return "\n".join(lines)

def build_requirements_text(
    requirement,
) -> str:

    lines = []

    lines.append("REQUIRED:")

    for item in requirement.required_items:
        lines.append(
            f"- [{item['category']}] "
            f"{item['text']}"
        )

    lines.append("")
    lines.append("PREFERRED:")

    for item in requirement.preferred_items:
        lines.append(
            f"- [{item['category']}] "
            f"{item['text']}"
        )

    return "\n".join(lines)