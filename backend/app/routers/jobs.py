from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Job, JobProfile, JobRequirement

from app.schemas import (
    JobOut,
    JobProfileOut,
    JobProfileUpdate,
    JobRequirementOut
)
from app.services.job_service import search_jobs
from app.services.job_requirement_service import(
    build_job_source_text,
    hash_job_description,
    extract_job_requirements,
)

from pathlib import Path
from uuid import uuid4
from urllib.parse import urlparse

from fastapi import File, UploadFile

from app.schemas import (
    ApplicationLinkUpdate,
    JobStatusUpdate,
)

from app.services.job_resolver import (
    resolve_job_link,
    safe_https_url,
)

from app.services.application_service import (
    get_session,
    start_application,
)

from app.schemas import (
    JobSearchRequest,
    JobOut,
)


from app.models.job_match import JobMatchAnalysis


from app.services.career_match_service import (
    analyze_career_match,
    build_career_profile_snapshot,
    build_requirements_text,
    calculate_match_scores,
)



router = APIRouter(
    prefix="/api",
    tags=["jobs"],
)


async def get_profile(
    db: AsyncSession,
) -> JobProfile:

    result = await db.execute(
        select(JobProfile)
        .where(JobProfile.id == 1)
    )

    profile = result.scalar_one_or_none()

    if profile is None:

        profile = JobProfile(id=1)

        db.add(profile)
        await db.commit()
        await db.refresh(profile)

    return profile


@router.get(
    "/job-profile",
    response_model=JobProfileOut,
)
async def read_job_profile(
    db: AsyncSession = Depends(get_db),
):

    return await get_profile(db)


@router.put(
    "/job-profile",
    response_model=JobProfileOut,
)
async def update_job_profile(
    data: JobProfileUpdate,
    db: AsyncSession = Depends(get_db),
):

    profile = await get_profile(db)

    profile.first_name = data.first_name
    profile.last_name = data.last_name
    profile.email = data.email
    profile.phone = data.phone
    profile.linkedin_url = data.linkedin_url

    profile.resume_text = data.resume_text
    profile.target_roles = data.target_roles
    profile.preferred_locations = (
        data.preferred_locations
    )

    profile.remote_ok = data.remote_ok

    profile.posted_within_days = (
        data.posted_within_days
    )

    profile.min_match_score = (
        data.min_match_score
    )

    await db.commit()
    await db.refresh(profile)

    return profile


@router.post(
    "/jobs/search",
    response_model=list[JobOut],
)
async def run_job_search(
    data: JobSearchRequest,
    db: AsyncSession = Depends(get_db),
):
    return await search_jobs(
        db=db,
        keywords=data.keywords,
        locations=data.locations,
        posted_within_days=data.posted_within_days,
        remote_ok=data.remote_ok,
        min_relevance_score=data.min_relevance_score,
    )

    

    


@router.get(
    "/jobs",
    response_model=list[JobOut],
)
async def list_jobs(
    db: AsyncSession = Depends(get_db),
):

    result = await db.execute(
        select(Job)
        .order_by(
            Job.final_score.desc(),
            Job.created_at.desc(),
        )
    )

    return list(result.scalars().all())

@router.post("/job-profile/resume")
async def upload_resume(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    profile = await get_profile(db)

    suffix = Path(file.filename or "").suffix.lower()

    if suffix not in {".pdf", ".docx"}:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and DOCX are supported.",
        )

    content = await file.read(5 * 1024 * 1024 + 1)
    await file.close()

    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="Resume must be 5 MB or smaller.",
        )

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Empty file.",
        )

    if suffix == ".pdf" and not content.startswith(b"%PDF"):
        raise HTTPException(
            status_code=400,
            detail="Invalid PDF.",
        )

    if suffix == ".docx" and not content.startswith(b"PK"):
        raise HTTPException(
            status_code=400,
            detail="Invalid DOCX.",
        )

    upload_dir = (
        Path(__file__).resolve().parents[2]
        / "private_uploads"
    )

    upload_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination = (
        upload_dir / f"{uuid4().hex}{suffix}"
    )

    destination.write_bytes(content)

    profile.resume_file_path = str(destination)

    await db.commit()

    return {"uploaded": True}


@router.post(
    "/jobs/{job_id}/resolve",
    response_model=JobOut,
)
async def resolve_application_link(
    job_id: int,
    db: AsyncSession = Depends(get_db),
):

    job = await db.get(Job, job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Job not found.",
        )

    try:
        url, status = await resolve_job_link(job)
    except Exception as exc:
        print(f"Link resolution failed: {exc}")

        raise HTTPException(
            status_code=502,
            detail="Unable to resolve the job link.",
        ) from exc

    job.application_url = url
    job.link_status = status

    await db.commit()
    await db.refresh(job)

    return job


@router.put(
    "/jobs/{job_id}/application-link",
    response_model=JobOut,
)
async def set_application_link(
    job_id: int,
    data: ApplicationLinkUpdate,
    db: AsyncSession = Depends(get_db),
):

    job = await db.get(Job, job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Job not found.",
        )

    if not safe_https_url(data.application_url):
        raise HTTPException(
            status_code=400,
            detail="A valid public HTTPS URL is required.",
        )

    host = (
        urlparse(data.application_url).hostname
        or ""
    ).lower()

    aggregators = {
        "indeed.com",
        "linkedin.com",
        "ziprecruiter.com",
    }

    if any(
        host == domain or host.endswith("." + domain)
        for domain in aggregators
    ):
        raise HTTPException(
            status_code=400,
            detail="Please use the official application URL.",
        )

    job.application_url = data.application_url
    job.link_status = "user_confirmed"

    await db.commit()
    await db.refresh(job)

    return job


@router.post("/jobs/{job_id}/prepare")
async def prepare_application(
    job_id: int,
    db: AsyncSession = Depends(get_db),
):

    job = await db.get(Job, job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Job not found.",
        )

    if (
        not job.application_url
        or job.link_status not in {
            "verified_ats",
            "user_confirmed",
        }
    ):
        raise HTTPException(
            status_code=400,
            detail="Resolve or confirm the application link first.",
        )

    if not safe_https_url(job.application_url):
        raise HTTPException(
            status_code=400,
            detail="Invalid application URL.",
        )

    profile = await get_profile(db)

    if not (
        profile.first_name
        and profile.last_name
        and profile.email
    ):
        raise HTTPException(
            status_code=400,
            detail="Save your name and email first.",
        )

    application_data = {
        "first_name": profile.first_name,
        "last_name": profile.last_name,
        "email": profile.email,
        "phone": profile.phone,
        "linkedin_url": profile.linkedin_url,
        "resume_file_path": profile.resume_file_path,
    }

    started = start_application(
        job.id,
        job.application_url,
        application_data,
    )

    return {
        "state": (
            "starting"
            if started
            else get_session(job.id)
        )
    }


@router.get("/jobs/{job_id}/application-session")
async def application_session(job_id: int):
    return {
        "state": get_session(job_id)
    }


@router.put(
    "/jobs/{job_id}/status",
    response_model=JobOut,
)
async def update_job_status(
    job_id: int,
    data: JobStatusUpdate,
    db: AsyncSession = Depends(get_db),
):

    job = await db.get(Job, job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Job not found.",
        )

    job.status = data.status

    await db.commit()
    await db.refresh(job)

    return job


@router.get(
    "/jobs/{job_id}",
    response_model=JobOut,
)
async def get_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
):
    job = await db.get(Job, job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )

    return job


def requirement_output(
    requirement: JobRequirement,
    *,
    cached: bool,
) -> JobRequirementOut:

    result = JobRequirementOut.model_validate(
        requirement
    )

    return result.model_copy(
        update={
            "cached": cached
        }
    )

@router.get(
    "/jobs/{job_id}/requirements",
    response_model=JobRequirementOut,
)
async def get_job_requirements(
    job_id: int,
    db: AsyncSession = Depends(get_db),
):

    job = await db.get(
        Job,
        job_id,
    )

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )

    source_text = build_job_source_text(
        job.title or "",
        job.snippet or "",
    )

    description_hash = hash_job_description(
        source_text
    )

    result = await db.execute(
        select(JobRequirement)
        .where(
            JobRequirement.job_id == job_id,
            JobRequirement.description_hash
            == description_hash,
        )
    )

    requirement = result.scalar_one_or_none()

    if requirement is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Requirements have not been "
                "extracted for this job."
            ),
        )

    return requirement_output(
        requirement,
        cached=True,
    )

@router.post(
    "/jobs/{job_id}/requirements",
    response_model=JobRequirementOut,
)
async def analyze_job_requirements(
    job_id: int,
    db: AsyncSession = Depends(get_db),
):

    job = await db.get(
        Job,
        job_id,
    )

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )

    if not (
        job.snippet
        and job.snippet.strip()
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "This job does not have enough "
                "description text to analyze."
            ),
        )

    source_text = build_job_source_text(
        job.title or "",
        job.snippet,
    )

    description_hash = hash_job_description(
        source_text
    )

    # --------------------------
    # Cache check
    # --------------------------

    existing = await db.execute(
        select(JobRequirement)
        .where(
            JobRequirement.job_id == job_id,
            JobRequirement.description_hash
            == description_hash,
        )
    )

    cached = existing.scalar_one_or_none()

    if cached is not None:

        return requirement_output(
            cached,
            cached=True,
        )

    # --------------------------
    # AI extraction
    # --------------------------

    extracted = (
        await extract_job_requirements(
            source_text
        )
    )

    requirement = JobRequirement(
        job_id=job_id,

        description_hash=description_hash,

        source_type="snippet",

        source_text=source_text,

        summary=extracted.summary,

        required_items=[
            item.model_dump()
            for item
            in extracted.required_items
        ],

        preferred_items=[
            item.model_dump()
            for item
            in extracted.preferred_items
        ],

        unclassified_items=[
            item.model_dump()
            for item
            in extracted.unclassified_items
        ],

        responsibilities=(
            extracted.responsibilities
        ),
    )

    db.add(requirement)

    await db.commit()
    await db.refresh(requirement)

    return requirement_output(
        requirement,
        cached=False,
    )

@router.post(
    "/jobs/{job_id}/career-match"
)
async def create_career_match(
    job_id: int,
    db: AsyncSession = Depends(get_db),
):
    requirement_result = await db.execute(
        select(JobRequirement)
        .where(
            JobRequirement.job_id == job_id
        )
        .order_by(
            JobRequirement.extracted_at.desc()
        )
    )

    requirement = (
        requirement_result.scalars().first()
    )

    if requirement is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Extract job requirements first."
            ),
        )

    (
        career_profile_text,
        career_profile_hash,
    ) = await build_career_profile_snapshot(db)

    if not career_profile_text or (
        career_profile_text == "[]"
    ):
        raise HTTPException(
            status_code=400,
            detail="Career profile is empty.",
        )

    cached_result = await db.execute(
        select(JobMatchAnalysis).where(
            JobMatchAnalysis.job_id
            == job_id,

            JobMatchAnalysis.job_requirement_hash
            == requirement.description_hash,

            JobMatchAnalysis.career_profile_hash
            == career_profile_hash,
        )
    )

    cached = (
        cached_result.scalars().first()
    )

    if cached:
        return {
            **{
                column.name:
                getattr(cached, column.name)
                for column
                in cached.__table__.columns
            },
            "cached": True,
        }

    requirements_text = (
        build_requirements_text(
            requirement
        )
    )

    result = await analyze_career_match(
        requirements_text,
        career_profile_text,
    )

    (
        match_score,
        required_score,
        preferred_score,
    ) = calculate_match_scores(
        result.assessments
    )

    strengths = [
        item.requirement_text
        for item in result.assessments
        if item.status == "satisfied"
    ]

    gaps = [
        item.requirement_text
        for item in result.assessments
        if item.status in {
            "missing",
            "partial",
        }
    ]

    unknowns = [
        item.requirement_text
        for item in result.assessments
        if item.status == "unknown"
    ]

    analysis = JobMatchAnalysis(
        job_id=job_id,
        job_requirement_hash=(
            requirement.description_hash
        ),
        career_profile_hash=(
            career_profile_hash
        ),
        match_score=match_score,
        required_score=required_score,
        preferred_score=preferred_score,
        summary=result.summary,
        assessments=[
            item.model_dump()
            for item in result.assessments
        ],
        strengths=strengths,
        gaps=gaps,
        unknowns=unknowns,
    )

    db.add(analysis)

    await db.commit()
    await db.refresh(analysis)

    return {
        **{
            column.name:
            getattr(analysis, column.name)
            for column
            in analysis.__table__.columns
        },
        "cached": False,
    }

@router.get(
    "/jobs/{job_id}/career-match"
)
async def get_career_match(
    job_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(JobMatchAnalysis)
        .where(
            JobMatchAnalysis.job_id
            == job_id
        )
        .order_by(
            JobMatchAnalysis.created_at.desc()
        )
    )

    analysis = result.scalars().first()

    if analysis is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Career match has not "
                "been analyzed."
            ),
        )

    return {
        **{
            column.name:
            getattr(analysis, column.name)
            for column
            in analysis.__table__.columns
        },
        "cached": True,
    }

