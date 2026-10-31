"""Exercise the exact extension-injected function against local ATS-shaped HTML."""
import asyncio
import json
import os
from pathlib import Path

import pytest
from playwright.async_api import async_playwright, expect

pytestmark = [pytest.mark.integration, pytest.mark.browser,
              pytest.mark.skipif(os.getenv("RUN_BROWSER_TESTS") != "1", reason="Set RUN_BROWSER_TESTS=1")]


@pytest.mark.parametrize("host", ["jobs.lever.co", "job-boards.greenhouse.io", "boards.greenhouse.io"])
def test_extension_contact_fill_preserves_answers_and_manual_steps(host):
    async def run():
        source = (Path(__file__).resolve().parents[2] / "extension" / "autofill.js").read_text()
        injected = source.split("export function fillContactFields", 1)[1]
        function = "function fillContactFields" + injected
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            try:
                page = await browser.new_page()
                url = f"https://{host}/example/job-id"
                # Fulfill every request locally; no employer website is contacted.
                await page.route("**/*", lambda route: route.fulfill(content_type="text/html", body='''
                    <form onsubmit="window.submitted=true; return false">
                    <label>Full name<input name="name"></label>
                    <label>First Name<input name="first_name"></label>
                    <label>Last Name<input name="last_name" value="Keep my answer"></label>
                    <label>Email<input name="email" type="email"></label>
                    <label>Phone<input name="phone" type="tel"></label>
                    <label>GitHub<input name="github"></label><label>GitHub<input name="github"></label>
                    <label>LinkedIn<input name="linkedin" type="hidden"></label>
                    <label>Salary expectations<input name="portfolio_url"></label>
                    <label>Password<input type="password" name="password"></label>
                    <label>Electronic signature<input name="signature"></label>
                    <label>Work authorization<input name="authorization"></label>
                    <label>Gender<input name="gender"></label>
                    <label>Legal attestation<input type="checkbox" name="legal"></label>
                    <input type="file" name="resume"><button type="submit">Submit</button></form>'''))
                await page.goto(url)
                fields = dict(first_name="Test", last_name="Replace", email="test@example.invalid", phone="123",
                              github_url="https://github.com/test", linkedin_url="https://linkedin.com/in/test",
                              portfolio_url="https://example.invalid", password="never", signature="never")
                result = await page.evaluate(f"args => ({function})(args.fields, args.url)", dict(fields=fields, url=url))
                assert result["filled"] == ["full_name", "first_name", "email", "phone"]
                assert await page.locator('[name="name"]').input_value() == "Test Replace"
                assert result["manual_review_required"]
                assert await page.locator('[name="first_name"]').input_value() == "Test"
                assert await page.locator('[name="email"]').input_value() == "test@example.invalid"
                assert await page.locator('[name="last_name"]').input_value() == "Keep my answer"
                for name in ("signature", "password", "authorization", "gender", "portfolio_url", "linkedin"):
                    assert await page.locator(f'[name="{name}"]').input_value() == ""
                assert not await page.locator('[name="legal"]').is_checked()
                assert await page.locator('[name="resume"]').evaluate("el => el.files.length") == 0
                assert not await page.evaluate("Boolean(window.submitted)")
                # A different posting must never receive the exported details.
                with pytest.raises(Exception, match="exact application"):
                    await page.evaluate(f"args => ({function})(args.fields, args.url)",
                                        dict(fields=fields, url=url + "-other"))
            finally:
                await browser.close()
    asyncio.run(run())


def test_installed_extension_popup_import_clear_and_invalid_file(tmp_path):
    async def run():
        extension = Path(__file__).resolve().parents[2] / "extension"
        async with async_playwright() as playwright:
            context = await playwright.chromium.launch_persistent_context(
                str(tmp_path / "chrome-profile"), channel="chromium", headless=True,
                args=[f"--disable-extensions-except={extension}", f"--load-extension={extension}"],
            )
            try:
                manager = await context.new_page()
                await manager.goto("chrome://extensions")
                item = manager.locator("extensions-item").filter(has_text="Career Agent Autofill")
                extension_id = await item.get_attribute("id")
                assert extension_id
                popup = await context.new_page()
                await popup.goto(f"chrome-extension://{extension_id}/popup.html")
                assert await popup.locator("#fill").is_disabled()
                handoff = dict(format="career-agent-autofill-v1", application_id=17,
                    application_url="https://jobs.lever.co/example/job-id",
                    fields=dict(first_name="Test", last_name="Applicant", email="test@example.invalid"),
                    resume=dict(id=2, name="Selected Resume", version=3))
                await popup.locator("#handoff").set_input_files(dict(
                    name="application.json", mimeType="application/json", buffer=json.dumps(handoff).encode()))
                await expect(popup.locator("#fill")).to_be_enabled()
                assert "Selected Resume (v3)" in await popup.locator("#selection").inner_text()
                assert "Application #17" in await popup.locator("#selection").inner_text()
                await popup.locator("#clear").click()
                assert await popup.locator("#fill").is_disabled()
                assert await popup.locator("#handoff").input_value() == ""
                assert "No application selected" in await popup.locator("#selection").inner_text()
                await popup.locator("#handoff").set_input_files(dict(
                    name="bad.json", mimeType="application/json", buffer=b'{"format":"wrong"}'))
                await expect(popup.locator("#result")).to_contain_text("Import a Career Agent")
                assert await popup.locator("#fill").is_disabled()
                assert "Import a Career Agent" in await popup.locator("#result").inner_text()
                for content, message in [
                    (b"{broken", "JSON"),
                    (b"x" * (32 * 1024 + 1), "smaller than 32 KB"),
                    (json.dumps({**handoff, "application_url": "https://example.invalid/job"}).encode(), "official Greenhouse or Lever"),
                ]:
                    await popup.locator("#handoff").set_input_files(dict(
                        name="invalid.json", mimeType="application/json", buffer=content))
                    await expect(popup.locator("#result")).to_contain_text(message)
                    assert await popup.locator("#fill").is_disabled()
                # Data lives in popup memory and must not survive reopening.
                await popup.reload()
                assert await popup.locator("#fill").is_disabled()
                assert "No application selected" in await popup.locator("#selection").inner_text()
            finally:
                await context.close()
    asyncio.run(run())
