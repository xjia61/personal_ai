import hashlib
import json
import re

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import (
    CareerRecord,
    JobProfile,
    ResumeVersion,
)
from app.schemas import ResumeInput, ResumeOut

from pathlib import Path

from fastapi import File, UploadFile, Response

from app.services.resume_files import extract_resume_text

from app.services.resume_export import (
    build_resume_docx,
    build_resume_pdf,
)


router = APIRouter(
    prefix="/api/resumes",
    tags=["resumes"],
)


async def get_profile_hash(db: AsyncSession) -> str:
    result = await db.execute(
        select(CareerRecord)
        .where(CareerRecord.profile_id == 1)
        .order_by(CareerRecord.id)
    )

    records = [
        {
            "id": r.id,
            "category": r.category,
            "title": r.title,
            "organization": r.organization,
            "start_date": r.start_date,
            "end_date": r.end_date,
            "description": r.description,
            "skills": r.skills,
        }
        for r in result.scalars().all()
    ]

    data = json.dumps(
        records,
        sort_keys=True,
        ensure_ascii=False,
    )

    return hashlib.sha256(data.encode()).hexdigest()


def require_draft(resume: ResumeVersion):
    if resume.status != "draft":
        raise HTTPException(
            status_code=409,
            detail=(
                "Approved resumes cannot be edited. "
                "Create a new version instead."
            ),
        )


def to_output(
    resume: ResumeVersion,
    current_hash: str,
) -> ResumeOut:
    output = ResumeOut.model_validate(resume)

    return output.model_copy(
        update={
            "profile_changed": (
                resume.status == "approved"
                and resume.source_profile_hash is not None
                and resume.source_profile_hash != current_hash
            )
        }
    )


@router.get("", response_model=list[ResumeOut])
async def list_resumes(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ResumeVersion)
        .where(ResumeVersion.profile_id == 1)
        .order_by(ResumeVersion.id.desc())
    )

    current_hash = await get_profile_hash(db)

    return [
        to_output(resume, current_hash)
        for resume in result.scalars().all()
    ]


@router.post("", response_model=ResumeOut)
async def create_resume(
    data: ResumeInput,
    db: AsyncSession = Depends(get_db),
):
    profile = await db.get(JobProfile, 1)

    if profile is None:
        profile = JobProfile(id=1)
        db.add(profile)
        await db.flush()

    resume = ResumeVersion(
        profile_id=1,
        family_id=str(uuid4()),
        version=1,
        status="draft",
        **data.model_dump(),
    )

    db.add(resume)
    await db.commit()
    await db.refresh(resume)

    return to_output(
        resume,
        await get_profile_hash(db),
    )


@router.put("/{resume_id}", response_model=ResumeOut)
async def update_resume(
    resume_id: int,
    data: ResumeInput,
    db: AsyncSession = Depends(get_db),
):
    resume = await db.get(ResumeVersion, resume_id)

    if resume is None or resume.profile_id != 1:
        raise HTTPException(404, "Resume not found")

    require_draft(resume)

    for field, value in data.model_dump().items():
        setattr(resume, field, value)

    await db.commit()
    await db.refresh(resume)

    return to_output(
        resume,
        await get_profile_hash(db),
    )


@router.post(
    "/{resume_id}/approve",
    response_model=ResumeOut,
)
async def approve_resume(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
):
    resume = await db.get(ResumeVersion, resume_id)

    if resume is None or resume.profile_id != 1:
        raise HTTPException(404, "Resume not found")

    require_draft(resume)

    if not resume.content.strip():
        raise HTTPException(
            400,
            "Resume content cannot be empty",
        )

    resume.status = "approved"
    resume.approved_at = datetime.now(timezone.utc)

    resume.source_profile_hash = (
        await get_profile_hash(db)
    )

    await db.commit()
    await db.refresh(resume)

    return to_output(
        resume,
        await get_profile_hash(db),
    )


@router.post(
    "/{resume_id}/new-version",
    response_model=ResumeOut,
)
async def create_new_version(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
):
    original = await db.get(ResumeVersion, resume_id)

    if original is None or original.profile_id != 1:
        raise HTTPException(404, "Resume not found")

    if original.status != "approved":
        raise HTTPException(
            409,
            "Only approved resumes can be versioned",
        )

    existing_draft = await db.scalar(
        select(ResumeVersion.id).where(
            ResumeVersion.family_id == original.family_id,
            ResumeVersion.status == "draft",
        )
    )

    if existing_draft is not None:
        raise HTTPException(
            409,
            "This resume already has an unfinished draft",
        )

    latest_version = await db.scalar(
        select(func.max(ResumeVersion.version))
        .where(
            ResumeVersion.family_id == original.family_id
        )
    )

    new_resume = ResumeVersion(
        profile_id=1,
        family_id=original.family_id,
        version=(latest_version or 0) + 1,
        name=original.name,
        content=original.content,
        role_tags=list(original.role_tags),
        skill_tags=list(original.skill_tags),
        status="draft",
        based_on_resume_id=original.id,
    )

    db.add(new_resume)
    await db.commit()
    await db.refresh(new_resume)

    return to_output(
        new_resume,
        await get_profile_hash(db),
    )


MAX_UPLOAD_SIZE = 5 * 1024 * 1024


@router.post("/import", response_model=ResumeOut)
async def import_resume(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    filename = Path(file.filename or "").name
    extension = Path(filename).suffix.lower()

    if extension not in {".pdf", ".docx"}:
        raise HTTPException(
            status_code=400,
            detail="Please upload a PDF or DOCX file",
        )

    raw = await file.read(MAX_UPLOAD_SIZE + 1)
    await file.close()

    if not raw or len(raw) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400,
            detail="File must be between 1 byte and 5 MB",
        )

    try:
        content = extract_resume_text(raw, filename)
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=(
                "Unable to extract resume text. "
                "Check that the file is valid and contains "
                "selectable text."
            ),
        ) from exc

    profile = await db.get(JobProfile, 1)

    if profile is None:
        profile = JobProfile(id=1)
        db.add(profile)
        await db.flush()

    resume = ResumeVersion(
        profile_id=1,
        family_id=str(uuid4()),
        version=1,
        name=Path(filename).stem[:200],
        content=content,
        role_tags=[],
        skill_tags=[],
        status="draft",
    )

    db.add(resume)

    await db.commit()
    await db.refresh(resume)

    return to_output(
        resume,
        await get_profile_hash(db),
    )

def safe_filename(name: str) -> str:
    cleaned = re.sub(
        r"[^A-Za-z0-9._-]+",
        "_",
        name,
    )

    cleaned = cleaned.strip("._")

    return cleaned or "resume"

@router.get("/{resume_id}/export/docx")
async def export_resume_docx(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
):
    resume = await db.get(
        ResumeVersion,
        resume_id,
    )

    if resume is None or resume.profile_id != 1:
        raise HTTPException(
            status_code=404,
            detail="Resume not found",
        )

    content = build_resume_docx(
        resume.content
    )

    filename = (
        f"{safe_filename(resume.name)}"
        f"_v{resume.version}.docx"
    )

    return Response(
        content=content,
        media_type=(
            "application/vnd.openxmlformats-"
            "officedocument.wordprocessingml.document"
        ),
        headers={
            "Content-Disposition":
                f'attachment; filename="{filename}"'
        },
    )


@router.get("/{resume_id}/export/pdf")
async def export_resume_pdf(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
):
    resume = await db.get(
        ResumeVersion,
        resume_id,
    )

    if resume is None or resume.profile_id != 1:
        raise HTTPException(
            status_code=404,
            detail="Resume not found",
        )

    content = build_resume_pdf(
        resume.content
    )

    filename = (
        f"{safe_filename(resume.name)}"
        f"_v{resume.version}.pdf"
    )

    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition":
                f'attachment; filename="{filename}"'
        },
    )