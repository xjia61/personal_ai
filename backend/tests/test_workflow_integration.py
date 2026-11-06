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
from app.services.ats_postings import Posting

pytestmark = pytest.mark.integration


@asynccontextmanager
async def workflow_client(postings=None):
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
            # Mock only the external ATS boundary; API and ORM remain real.
            async def posting_for(url):
                return (postings or {}).get(url, Posting("unknown"))
            with patch("app.services.ats_postings.fetch_posting", new=AsyncMock(side_effect=posting_for)):
                yield client, sessions
    finally:
        await engine.dispose()


SEARCH = dict(keywords=["Python"], locations=["Chicago"], posted_within_days=14,
              remote_ok=True, min_relevance_score=0)


def test_search_filters_persists_and_deduplicates():
    async def run():
        source = "https://jobs.lever.co/example/1"
        official = source + "/apply"
        postings = {
            source: Posting("open", "Python Engineer", "Example", "Chicago", "Chicago Python", official),
            "https://jobs.lever.co/example/2": Posting("open", "Accountant", "Example", "Chicago", "Accounting", "https://jobs.lever.co/example/2/apply"),
            "https://jobs.lever.co/example/3": Posting("open", "Python Engineer", "Example", "Chicago", "Python", "https://jobs.lever.co/example/3/apply", (date.today() - timedelta(days=30)).isoformat()),
        }
        async with workflow_client(postings) as (client, sessions):
            results = [
                dict(title="Python Engineer", url=source, content="Chicago Python"),
                dict(title="Python Engineer", url=source, content="Chicago Python updated"),
                dict(title="Python Engineer", url="javascript:bad", content="Python"),
                dict(title="Accountant", url="https://jobs.lever.co/example/2", content="Accounting"),
                dict(title="Python Engineer", url="https://jobs.lever.co/example/3", content="Python",
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
                    job.application_url = official
                    await db.commit()
                second = await client.post("/api/jobs/search", json=SEARCH)
                assert second.status_code == 200, second.text
                assert second.json()[0]["id"] == job_id
                assert second.json()[0]["application_url"] == official
            async with sessions() as db:
                jobs = (await db.execute(select(Job))).scalars().all()
                # New nonmatching/stale candidates do not clutter saved results.
                assert len(jobs) == 1
                matching = [job for job in jobs if job.id == job_id]
                assert len(matching) == 1
                assert matching[0].company == "Example"
                assert matching[0].source_url != matching[0].application_url
    asyncio.run(run())


def test_selected_resume_prepare_autofill_review_and_manual_tracking():
    async def run():
        source = "https://jobs.lever.co/example/job-id"
        official = source + "/apply"
        posting = Posting("open", "Engineer", "Example", "Chicago", "Python", official)
        async with workflow_client({source: posting, official: posting}) as (client, sessions):
            async with sessions() as db:
                profile = JobProfile()
                job = Job(title="Engineer", source_url=source, application_url=official)
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
            export = await client.get(f"/api/applications/{application_id}/extension-data")
            assert export.status_code == 200, export.text
            assert export.json()["resume"] == dict(id=resume_id, name="Selected", version=2)
            assert export.json()["fields"]["email"] == "test@example.invalid"
            assert set(export.json()["fields"]) == {
                "first_name", "last_name", "email", "phone", "linkedin_url", "github_url", "portfolio_url",
            }
            assert "Selected professional history" not in export.text
            assert (await client.get("/api/applications/999/extension-data")).status_code == 404
            again = await client.post("/api/applications/prepare", json=dict(job_id=job_id, resume_version_id=resume_id))
            assert again.json()["application_id"] == application_id

            browser_result = dict(url=official, filled_fields=["first_name", "email"],
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
            async with sessions() as db:
                selected = await db.get(ResumeVersion, resume_id)
                selected.status = "draft"
                await db.commit()
            # Revoking approval must also prevent further extension exports.
            assert (await client.get(f"/api/applications/{application_id}/extension-data")).status_code == 400
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


def test_search_to_extension_export_and_closed_posting_guard():
    async def run():
        source = "https://jobs.lever.co/example/current"
        official = source + "/apply"
        postings = {source: Posting("open", "Python Engineer", "Example", "Chicago", "Python", official)}
        postings[official] = postings[source]
        async with workflow_client(postings) as (client, sessions):
            async with sessions() as db:
                profile = JobProfile()
                db.add_all([profile, ApplicationProfile(first_name="Test", email="test@example.invalid")])
                await db.flush()
                resume = ResumeVersion(profile_id=profile.id, family_id="search-flow", version=1,
                                       name="Approved", content="Real history", status="approved")
                db.add(resume)
                await db.commit()
                resume_id = resume.id
            with patch("app.services.job_service.search_web", new=AsyncMock(return_value=[dict(
                title="Search title", url=source + "?source=tracking", content="Python")])):
                # Tracking parameters must not change ATS identity.
                postings[source + "?source=tracking"] = postings[source]
                response = await client.post("/api/jobs/search", json=SEARCH)
                assert response.status_code == 200, response.text
                job = response.json()[0]
                assert job["availability_status"] == "open"
                assert job["availability_checked_at"]
                assert job["posted_date_text"] is None
                assert job["title"] == "Python Engineer"
                request = dict(job_id=job["id"], resume_version_id=resume_id)
                prepared = await client.post("/api/applications/prepare", json=request)
                assert prepared.status_code == 200, prepared.text
                exported = await client.get(f'/api/applications/{prepared.json()["application_id"]}/extension-data')
                assert exported.status_code == 200, exported.text
                assert exported.json()["application_url"] == official
                assert exported.json()["resume"]["id"] == resume_id
                assert exported.json()["fields"]["first_name"] == "Test"
                # Strict date filtering excludes unknown dates; default search retains them.
                strict = await client.post("/api/jobs/search", json={**SEARCH, "strict_dates": True})
                assert strict.status_code == 200 and strict.json() == []
            postings[official] = Posting("unavailable")
            blocked = await client.post("/api/applications/prepare", json=request)
            assert blocked.status_code == 409
            refreshed = await client.get(f'/api/jobs/{job["id"]}')
            assert refreshed.json()["availability_status"] == "unavailable"
            assert (await client.get("/api/applications")).json()[0]["status"] == "preparing"
    asyncio.run(run())


def test_job_search_validation_and_search_outage():
    async def run():
        async with workflow_client() as (client, _):
            with patch("app.services.job_service.search_web", new=AsyncMock(side_effect=WebSearchError("Search unavailable"))) as search:
                assert (await client.post("/api/jobs/search", json={**SEARCH, "keywords": [" "]})).status_code == 422
                search.assert_not_awaited()
                response = await client.post("/api/jobs/search", json=SEARCH)
                assert response.status_code == 502
                assert response.json()["detail"] == "Search unavailable"
    asyncio.run(run())


def test_alternative_roles_and_unknown_availability():
    async def run():
        source = "https://jobs.lever.co/example/python"
        postings = {source: Posting("open", "Python Engineer", "Example", "Remote", "Python",
                                    source + "/apply")}
        async with workflow_client(postings) as (client, _):
            with patch("app.services.job_service.search_web", new=AsyncMock(return_value=[dict(
                title="Python Engineer", content="Python", url=source)])):
                response = await client.post("/api/jobs/search", json={**SEARCH,
                    "keywords": ["Python Engineer", "Bioinformatics Scientist"], "min_relevance_score": 60})
                assert response.status_code == 200, response.text
                assert response.json()[0]["match_score"] == 100
                job_id = response.json()[0]["id"]
            postings[source + "/apply"] = Posting("unknown")
            response = await client.post(f"/api/jobs/{job_id}/verify")
            assert response.status_code == 200
            assert response.json()["availability_status"] == "unknown"
            assert response.json()["status"] == "new"
    asyncio.run(run())
