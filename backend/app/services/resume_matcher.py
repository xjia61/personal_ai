import re
from difflib import SequenceMatcher

from app.models import ResumeVersion


def normalize(text: str) -> str:
    return re.sub(
        r"[^a-z0-9+#.]+",
        " ",
        text.lower(),
    ).strip()


def role_similarity(
    job_title: str,
    role_tags: list[str],
) -> float:
    if not role_tags:
        return 0.0

    job = normalize(job_title)

    return max(
        SequenceMatcher(
            None,
            job,
            normalize(role),
        ).ratio()
        for role in role_tags
    )


def skill_similarity(
    job_text: str,
    skill_tags: list[str],
) -> tuple[float, list[str]]:
    if not skill_tags:
        return 0.0, []

    normalized_job = normalize(job_text)

    matched = [
        skill
        for skill in skill_tags
        if normalize(skill) in normalized_job
    ]

    return (
        len(matched) / len(skill_tags),
        matched,
    )


def score_resume(
    resume: ResumeVersion,
    job_title: str,
    job_text: str,
) -> dict:
    role_score = role_similarity(
        job_title,
        resume.role_tags,
    )

    skill_score, matched_skills = skill_similarity(
        job_text,
        resume.skill_tags,
    )

    # Role is currently more important than skills.
    score = (
        role_score * 0.65
        + skill_score * 0.35
    )

    score_percent = round(score * 100, 1)

    if score_percent >= 85:
        action = "reuse"
    elif score_percent >= 60:
        action = "tailor"
    else:
        action = "new"

    return {
        "score": score_percent,
        "action": action,
        "role_score": round(role_score * 100, 1),
        "skill_score": round(skill_score * 100, 1),
        "matched_skills": matched_skills,
    }