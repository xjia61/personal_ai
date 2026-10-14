from app.services.job_requirement_service import (
    build_job_source_text,
    hash_job_description,
)


def test_description_hash_is_stable():

    text1 = build_job_source_text(
        "Software Engineer",
        "Python and SQL required.",
    )

    text2 = build_job_source_text(
        "Software Engineer",
        "Python and SQL required.",
    )

    assert (
        hash_job_description(text1)
        ==
        hash_job_description(text2)
    )


def test_description_hash_changes():

    text1 = build_job_source_text(
        "Software Engineer",
        "Python required.",
    )

    text2 = build_job_source_text(
        "Software Engineer",
        "Python and AWS required.",
    )

    assert (
        hash_job_description(text1)
        !=
        hash_job_description(text2)
    )