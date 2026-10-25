from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ApplicationProfile
from app.schemas.application_profile import (
    ApplicationProfileOut,
    ApplicationProfileUpdate,
)


router = APIRouter(
    prefix="/api/application-profile",
    tags=["application-profile"],
)


@router.get("", response_model=ApplicationProfileOut | None)
async def get_application_profile(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ApplicationProfile)
        .order_by(ApplicationProfile.id)
    )

    return result.scalars().first()


@router.put("", response_model=ApplicationProfileOut)
async def save_application_profile(
    data: ApplicationProfileUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ApplicationProfile)
        .order_by(ApplicationProfile.id)
    )

    profile = result.scalars().first()

    if profile is None:
        profile = ApplicationProfile()
        db.add(profile)

    for field, value in data.model_dump().items():
        setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)

    return profile