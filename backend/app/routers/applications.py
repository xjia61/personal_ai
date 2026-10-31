from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


from app.database import get_db
from app.models import (
    Application,
    Job,
    ResumeVersion,
    ApplicationProfile,
)
from app.schemas.application import (
    PrepareApplicationRequest, ApplicationStatusUpdate, ApplicationSummary,
)
from app.services.browser_service import open_application_browser, resolve_application_page, autofill_application_form
from app.services.resume_export import build_resume_pdf


router = APIRouter(
    prefix="/api/applications",
    tags=["applications"],
)


@router.post("/prepare")
async def prepare_application(
    data: PrepareApplicationRequest,
    db: AsyncSession = Depends(get_db),
):
    job = await db.get(Job, data.job_id, with_for_update=True)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Job not found.",
        )

    resume = await db.get(
        ResumeVersion,
        data.resume_version_id,
    )

    if resume is None:
        raise HTTPException(
            status_code=404,
            detail="Resume not found.",
        )

    if resume.status != "approved":
        raise HTTPException(
            status_code=400,
            detail="Resume must be approved before use.",
        )

    # Serialize prepares for this job and reuse the exact selected resume.
    existing = (await db.execute(
        select(Application).where(
            Application.job_id == job.id,
            Application.resume_version_id == resume.id,
        ).order_by(Application.id.desc())
    )).scalars().first()
    if existing is not None:
        await db.commit()
        return {
            "application_id": existing.id, "job_id": existing.job_id,
            "resume_version_id": existing.resume_version_id,
            "application_url": existing.application_url,
            "status": existing.status, "created_at": existing.created_at,
        }

    application_url = (
        getattr(job, "application_url", None)
        or getattr(job, "source_url", "")
        or ""
    )

    application = Application(
        job_id=job.id,
        resume_version_id=resume.id,
        status="preparing",
        application_url=application_url,
    )

    db.add(application)

    await db.commit()
    await db.refresh(application)

    return {
        "application_id": application.id,
        "job_id": application.job_id,
        "resume_version_id": application.resume_version_id,
        "application_url": application.application_url,
        "status": application.status,
        "created_at": application.created_at,
    }

def _summary_query():
    return select(
        Application.id, Application.job_id, Job.title.label("job_title"),
        Job.company, Application.resume_version_id,
        ResumeVersion.name.label("resume_name"),
        ResumeVersion.version.label("resume_version"),
        Application.status, Application.application_url, Application.created_at,
    ).join(Job, Job.id == Application.job_id).join(
        ResumeVersion, ResumeVersion.id == Application.resume_version_id
    )


@router.get("", response_model=list[ApplicationSummary])
async def list_applications(job_id: int | None = None, db: AsyncSession = Depends(get_db)):
    query = _summary_query().order_by(Application.created_at.desc(), Application.id.desc())
    if job_id is not None:
        query = query.where(Application.job_id == job_id)
    return (await db.execute(query)).mappings().all()


@router.get("/{application_id}", response_model=ApplicationSummary)
async def get_application(application_id: int, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(_summary_query().where(Application.id == application_id))).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Application not found.")
    return row


@router.patch("/{application_id}/status", response_model=ApplicationSummary)
async def update_application_status(
    application_id: int, data: ApplicationStatusUpdate, db: AsyncSession = Depends(get_db),
):
    application = await db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found.")
    application.status = data.status
    await db.commit()
    return await get_application(application_id, db)


@router.post("/{application_id}/open")
async def open_application(
    application_id: int,
    db: AsyncSession = Depends(get_db),
):
    application = await db.get(
        Application,
        application_id,
    )

    if application is None:
        raise HTTPException(
            status_code=404,
            detail="Application not found.",
        )

    if not application.application_url:
        raise HTTPException(
            status_code=400,
            detail="Application URL is missing.",
        )

    current_url = await open_application_browser(
        application_id=application.id,
        url=application.application_url,
    )

    return {
        "application_id": application.id,
        "status": "browser_open",
        "url": current_url,
    }


@router.get("/{application_id}/extension-data")
async def export_extension_data(application_id: int, db: AsyncSession = Depends(get_db)):
    """Explicit local handoff; export only safe contact fields, never work authorization."""
    application = await db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found.")
    resume = await db.get(ResumeVersion, application.resume_version_id)
    if resume is None or resume.status != "approved":
        raise HTTPException(status_code=400, detail="Selected resume must be approved.")
    profile = (await db.execute(select(ApplicationProfile).order_by(ApplicationProfile.id))).scalars().first()
    if profile is None:
        raise HTTPException(status_code=400, detail="Application profile has not been configured.")
    return {
        "format": "career-agent-autofill-v1",
        "application_id": application.id,
        "application_url": application.application_url,
        "resume": {"id": resume.id, "name": resume.name, "version": resume.version},
        "fields": {key: getattr(profile, key) for key in (
            "first_name", "last_name", "email", "phone", "linkedin_url", "github_url", "portfolio_url",
        )},
    }


@router.post(
    "/{application_id}/resolve"
)
async def resolve_application(
    application_id: int,
    db: AsyncSession = Depends(get_db),
):
    application = await db.get(
        Application,
        application_id,
    )

    if application is None:
        raise HTTPException(
            status_code=404,
            detail="Application not found.",
        )

    try:
        result = await resolve_application_page(
            application.id
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    if result["status"] == "resolved":
        application.application_url = (
            result["url"]
        )

        await db.commit()
        await db.refresh(application)

    return {
        "application_id": application.id,
        **result,
    }



@router.post("/{application_id}/autofill")
async def autofill_application(
    application_id: int,
    db: AsyncSession = Depends(get_db),
):
    application = await db.get(
        Application,
        application_id,
    )

    if application is None:
        raise HTTPException(
            status_code=404,
            detail="Application not found.",
        )

    # Application Profile
    result = await db.execute(
        select(ApplicationProfile)
        .order_by(ApplicationProfile.id)
    )

    profile = result.scalars().first()

    if profile is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Application profile has not been configured."
            ),
        )

    # Resume selected when the application was prepared
    resume = await db.get(
        ResumeVersion,
        application.resume_version_id,
    )

    if resume is None:
        raise HTTPException(
            status_code=404,
            detail="Selected resume was not found.",
        )

    if resume.status != "approved":
        raise HTTPException(
            status_code=400,
            detail=(
                "Selected resume is no longer approved."
            ),
        )

    # Build the selected resume as a PDF in memory.
    try:
        resume_bytes = build_resume_pdf(
            resume.content
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to generate resume PDF."
            ),
        ) from exc

    resume_filename = (
        f"resume_v{resume.version}.pdf"
    )

    try:
        autofill_result = (
            await autofill_application_form(
                application_id=application.id,
                profile=profile,
                resume_bytes=resume_bytes,
                resume_filename=resume_filename,
            )
        )

    except RuntimeError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    # If the user manually navigated from Teal/etc.
    # to the real ATS page, remember the real URL.
    current_url = autofill_result.get("url")

    if (
        current_url
        and current_url.startswith(("https://", "http://"))
        and current_url != application.application_url
    ):
        application.application_url = current_url

    if application.status in {"preparing", "ready_for_review"}:
        application.status = "ready_for_review"
    autofill_result["status"] = application.status

    await db.commit()
    await db.refresh(application)

    return {
        "application_id": application.id,
        **autofill_result,
    }


