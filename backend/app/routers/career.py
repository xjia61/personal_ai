from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

from app.models import (
    CareerRecord,
    JobProfile,
)

from app.schemas import (
    CareerRecordCreate,
    CareerRecordOut,
)


router = APIRouter(
    prefix="/api/career",
    tags=["career"],
)


async def ensure_profile(db: AsyncSession):

    profile = await db.get(JobProfile, 1)

    if profile is None:
        profile = JobProfile(id=1)
        db.add(profile)
        await db.flush()

    return profile


@router.get(
    "/records",
    response_model=list[CareerRecordOut],
)
async def list_records(
    db: AsyncSession = Depends(get_db),
):

    result = await db.execute(
        select(CareerRecord)
        .where(CareerRecord.profile_id == 1)
        .order_by(CareerRecord.id)
    )

    return list(result.scalars().all())


@router.post(
    "/records",
    response_model=CareerRecordOut,
)
async def create_record(
    data: CareerRecordCreate,
    db: AsyncSession = Depends(get_db),
):

    await ensure_profile(db)

    record = CareerRecord(
        profile_id=1,
        **data.model_dump(),
    )

    db.add(record)

    await db.commit()
    await db.refresh(record)

    return record


@router.put(
    "/records/{record_id}",
    response_model=CareerRecordOut,
)
async def update_record(
    record_id: int,
    data: CareerRecordCreate,
    db: AsyncSession = Depends(get_db),
):

    record = await db.get(
        CareerRecord,
        record_id,
    )

    if record is None or record.profile_id != 1:
        raise HTTPException(
            status_code=404,
            detail="Record not found",
        )

    for key, value in data.model_dump().items():
        setattr(record, key, value)

    await db.commit()
    await db.refresh(record)

    return record


@router.delete(
    "/records/{record_id}",
    status_code=204,
)
async def delete_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
):

    record = await db.get(
        CareerRecord,
        record_id,
    )

    if record is None or record.profile_id != 1:
        raise HTTPException(
            status_code=404,
            detail="Record not found",
        )

    await db.delete(record)
    await db.commit()