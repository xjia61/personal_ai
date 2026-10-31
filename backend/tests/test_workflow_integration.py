"""Real API/services/async ORM; only provider and browser boundaries are mocked."""
import asyncio
from contextlib import asynccontextmanager
from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.models import Application, ApplicationProfile, Job, JobProfile, ResumeVersion
from app.routers.applications import router as applications_router
from app.routers.jobs import router as jobs_router
from app.routers.search import router as search_router
from app.services.search_service import WebSearchError

pytestmark = pytest.mark.integration


@asynccontextmanager
async def workflow_client():
    # Literal test URL: never consult DATABASE_URL or run production startup.
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    @event.listens_for(engine.sync_engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    tables = [model.__table__ for model in
              (JobProfile, Job, ResumeVersion, ApplicationProfile, Application)]
    try:
        async with engine.begin() as connection:
            await connection.run_sync(lambda conn: Base.metadata.create_all(conn, tables=tables))
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        app = FastAPI()
        for router in (jobs_router, applications_router, search_router):
            app.include_router(router)

        async def test_db():
            async with sessions() as session:
                yield session

        app.dependency_overrides[get_db] = test_db
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            yield client, sessions
    finally:
        await engine.dispose()


SEARCH = dict(keywords=["Python"], locations=["Chicago"], posted_within_days=14,
              remote_ok=True, min_relevance_score=0)


def test_search_filters_persists_and_deduplicates():
    async def run():
        async with workflow_client() as (client, sessions):
            results = [
                dict(title="Python Engineer", url="https://example.invalid/jobs/1", content="Chicago Python"),
                dict(title="Python Engineer", url="https://example.invalid/jobs/1", content="Chicago Python updated"),
                dict(title="Python Engineer", url="javascript:bad", content="Python"),
                dict(title="Accountant", url="https://example.invalid/jobs/2", content="Accounting"),
                dict(title="Python Engineer", url="https://example.invalid/jobs/3", content="Python",
                     published_date=(date.today() - timedelta(days=30)).isoformat()),
            ]
            with patch("app.services.job_service.search_web", new=AsyncMock(return_value=results)):
                first = await client.post("/api/jobs/search", json=SEARCH)
                assert first.status_code == 200, first.text
                assert len(first.json()) == 1
                job_id = first.json()[0]["id"]
                # Enrichment must survive a later discovery of the same posting.
                async with sessions() as db:
                    job = await db.get(Job, job_id)
                    job.company = "Example"
                    job.application_url = "https://example.invalid/apply/1"
                    await db.commit()
                second = await client.post("/api/jobs/search", json=SEARCH)
                assert second.status_code == 200, second.text
                assert second.json()[0]["id"] == job_id
                assert second.json()[0]["application_url"] == "https://example.invalid/apply/1"
            async with sessions() as db:
                jobs = (await db.execute(select(Job))).scalars().all()
                assert len(jobs) == 1
                assert jobs[0].company == "Example"
                assert jobs[0].source_url != jobs[0].application_url
    asyncio.run(run())


def test_selected_resume_prepare_autofill_review_and_manual_tracking():
    async def run():
        async with workflow_client() as (client, sessions):
            async with sessions() as db:
                profile = JobProfile()
                job = Job(title="Engineer", source_url="https://example.invalid/job",
                          application_url="https://example.invalid/apply")
                db.add_all([profile, job, ApplicationProfile(first_name="Test", email="test@example.invalid")])
                await db.flush()
                selected = ResumeVersion(profile_id=profile.id, family_id="selected", version=2,
                                         name="Selected", content="Selected professional history", status="approved")
                other = ResumeVersion(profile_id=profile.id, family_id="other", version=1,
                                      name="Other", content="Wrong resume", status="draft")
                db.add_all([selected, other])
                await db.commit()
                job_id, resume_id, draft_id = job.id, selected.id, other.id

            rejected = await client.post("/api/applications/prepare", json=dict(job_id=job_id, resume_version_id=draft_id))
            assert rejected.status_code == 400
            prepared = await client.post("/api/applications/prepare", json=dict(job_id=job_id, resume_version_id=resume_id))
            assert prepared.status_code == 200, prepared.text
            application_id = prepared.json()["application_id"]
            again = await client.post("/api/applications/prepare", json=dict(job_id=job_id, resume_version_id=resume_id))
            assert again.json()["application_id"] == application_id

            browser_result = dict(url="https://example.invalid/apply", filled_fields=["first_name", "email"],
                                  skipped_fields=["phone"], resume_uploaded=True, manual_review_required=True)
            with patch("app.routers.applications.open_application_browser", new=AsyncMock(return_value=browser_result["url"])) as opened, \
                 patch("app.routers.applications.autofill_application_form", new=AsyncMock(return_value=browser_result)) as filled, \
                 patch("app.routers.applications.build_resume_pdf", return_value=b"%PDF-test") as pdf:
                response = await client.post(f"/api/applications/{application_id}/open")
                assert response.status_code == 200
                opened.assert_awaited_once_with(application_id=application_id, url=browser_result["url"])
                response = await client.post(f"/api/applications/{application_id}/autofill")
                assert response.status_code == 200, response.text
                assert response.json()["status"] == "ready_for_review"
                assert response.json()["manual_review_required"] is True
                pdf.assert_called_once_with("Selected professional history")
                assert filled.call_args.kwargs["resume_filename"] == "resume_v2.pdf"
                assert filled.call_args.kwargs["resume_bytes"] == b"%PDF-test"
                assert filled.call_args.kwargs["profile"].email == "test@example.invalid"

            async with sessions() as db:
                application = await db.get(Application, application_id)
                assert application.status == "ready_for_review"
                assert application.resume_version_id == resume_id
            # Applied is recorded only through the user's explicit status update.
            response = await client.patch(f"/api/applications/{application_id}/status", json={"status": "applied"})
            assert response.status_code == 200, response.text
            response = await client.get("/api/applications")
            assert response.json()[0]["status"] == "applied"
            assert response.json()[0]["resume_version_id"] == resume_id
    asyncio.run(run())


def test_search_api_validation_and_provider_failure():
    async def run():
        async with workflow_client() as (client, _):
            with patch("app.routers.search.search_web", new=AsyncMock(side_effect=WebSearchError("Provider unavailable"))) as search:
                assert (await client.get("/api/search", params={"q": "x"})).status_code == 422
                search.assert_not_awaited()
                response = await client.get("/api/search", params={"q": "Python jobs"})
                assert response.status_code == 502
                assert response.json()["detail"] == "Provider unavailable"
    asyncio.run(run())
