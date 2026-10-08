from types import SimpleNamespace

from app.services.resume_matcher import (
    role_similarity,
    skill_similarity,
    score_resume,
)


def test_role_similarity():
    score = role_similarity(
        "Software Engineer",
        [
            "Software Engineer",
            "Backend Developer",
        ],
    )

    assert score == 1.0


def test_skill_similarity():
    score, skills = skill_similarity(
        "Python SQL Docker React",
        [
            "Python",
            "SQL",
            "Spark",
        ],
    )

    assert round(score, 2) == 0.67
    assert "Python" in skills
    assert "SQL" in skills


def test_resume_reuse():
    resume = SimpleNamespace(
        role_tags=[
            "Software Engineer"
        ],
        skill_tags=[
            "Python",
            "SQL",
            "Docker",
        ],
    )

    result = score_resume(
        resume,
        "Software Engineer",
        "Python SQL Docker",
    )

    assert result["score"] == 100
    assert result["action"] == "reuse"
    