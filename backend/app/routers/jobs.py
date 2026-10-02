from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Job, JobProfile
from app.schemas import (
    JobOut,
    JobProfileOut,
    JobProfileUpdate,
)
from app.services.job_service import search_jobs


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
    db: AsyncSession = Depends(get_db),
):

    profile = await get_profile(db)

    try:
        return await search_jobs(
            db,
            profile,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        print(f"AI ranking failed: {exc}")

        raise HTTPException(
            status_code=502,
            detail="AI matching failed. Check backend logs.",
        ) from exc


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