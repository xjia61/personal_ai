"""Built React UI + export + injected extension, using explicit API fixtures."""
import asyncio
import json
import mimetypes
import os
from pathlib import Path
from urllib.parse import urlparse

import pytest
from playwright.async_api import async_playwright, expect

pytestmark = [pytest.mark.integration, pytest.mark.browser,
              pytest.mark.skipif(os.getenv("RUN_BROWSER_TESTS") != "1", reason="Set RUN_BROWSER_TESTS=1")]


def test_search_ui_to_extension_download_and_autofill():
    root = Path(__file__).resolve().parents[2]
    dist = root / "frontend" / "dist"
    assert (dist / "index.html").is_file(), "Run npm run build in frontend first"

    async def run():
        source = "https://jobs.lever.co/example/posting-id"
        job = dict(id=1, title="Python Engineer", company="Example", location="Houston, TX",
            source="lever", source_url=source, application_url=source + "/apply", snippet="Python",
            posted_date_text=None, match_score=100, final_score=100, status="new", link_status="verified_ats",
            availability_status="open", availability_checked_at="2026-10-31T12:00:00Z")
        export = dict(format="career-agent-autofill-v1", application_id=7,
            application_url=job["application_url"], fields=dict(first_name="Test", last_name="Applicant", email="test@example.invalid"),
            resume=dict(id=2, name="Approved", version=1))
        searches = []
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            try:
                page = await browser.new_page()

                async def serve(route):
                    request = route.request
                    url = urlparse(request.url)
                    headers = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "Content-Type",
                               "Access-Control-Allow-Methods": "GET, POST, OPTIONS"}
                    if request.method == "OPTIONS":
                        return await route.fulfill(status=204, headers=headers)
                    if url.hostname == "career.test":
                        path = (dist / (url.path.lstrip("/") or "index.html")).resolve()
                        if not path.is_relative_to(dist.resolve()) or not path.is_file():
                            return await route.fulfill(status=404)
                        return await route.fulfill(body=path.read_bytes(), content_type=mimetypes.guess_type(path)[0] or "application/octet-stream")
                    if url.hostname == "jobs.lever.co":
                        return await route.fulfill(content_type="text/html", body='<label>Email<input name="email" type="email"></label><button onclick="window.submitted=true">Submit</button>')
                    data, status = [], 200
                    if url.path == "/api/jobs/search":
                        searches.append(request.post_data_json)
                        data = [job]
                    elif url.path == "/api/jobs/1":
                        data = job
                    elif url.path == "/api/resumes":
                        data = [dict(id=2, name="Approved", version=1, status="approved")]
                    elif url.path == "/api/applications/prepare":
                        assert request.post_data_json == dict(job_id=1, resume_version_id=2)
                        data = dict(application_id=7, status="preparing", application_url=job["application_url"])
                    elif url.path == "/api/applications/7/extension-data":
                        data = export
                    elif url.path.endswith("/requirements"):
                        status, data = 404, {"detail": "Not analyzed"}
                    await route.fulfill(status=status, json=data, headers=headers)

                await page.route("**/*", serve)
                await page.goto("http://career.test/")
                await page.get_by_role("button", name="💼 Jobs").click()
                await page.get_by_label("Target roles/ keywords").fill("Python Engineer")
                await page.get_by_label("Preferred locations").fill("Houston, TX\nChicago, IL")
                await page.get_by_role("button", name="Find Jobs", exact=True).click()
                await expect(page.get_by_text("Python Engineer", exact=True)).to_be_visible()
                assert searches[0]["locations"] == ["Houston, TX", "Chicago, IL"]
                assert searches[0]["strict_dates"] is False
                await expect(page.get_by_text("Posting date unknown", exact=True)).to_be_visible()
                await page.get_by_role("button", name="Review & Prepare Application").click()
                await page.get_by_label("Approved resume").select_option("2")
                await page.get_by_role("button", name="Verify & Prepare Application").click()
                await expect(page.get_by_role("link", name="Open Official Application")).to_have_attribute("href", job["application_url"])
                async with page.expect_download() as download:
                    await page.get_by_role("button", name="Download Extension Data").click()
                payload = json.loads(Path(await (await download.value).path()).read_text())
                assert payload == export
                await page.goto(payload["application_url"])
                source_code = (root / "extension" / "autofill.js").read_text().split("export function fillContactFields", 1)[1]
                result = await page.evaluate("args => (function fillContactFields" + source_code + ")(args.fields, args.url)",
                    dict(fields=payload["fields"], url=payload["application_url"]))
                assert result["filled"] == ["email"]
                assert await page.locator('[name="email"]').input_value() == "test@example.invalid"
                assert not await page.evaluate("Boolean(window.submitted)")
            finally:
                await browser.close()
    asyncio.run(run())
