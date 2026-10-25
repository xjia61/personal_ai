"""Visible, human-reviewed application assistance. Never submits forms."""
import asyncio
import logging
import re
from urllib.parse import urlsplit

from playwright.async_api import Browser, Page, Playwright, async_playwright

logger = logging.getLogger(__name__)


def _log_url(url):
    # Query strings/fragments can contain credentials or personal information.
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.hostname or ''}{parts.path}"


class BrowserSession:
    def __init__(self, playwright: Playwright, browser: Browser, page: Page):
        self.playwright = playwright
        self.browser = browser
        self.page = page
        self.context = page.context


_sessions: dict[int, BrowserSession] = {}


async def get_active_page(application_id: int) -> Page:
    session = _sessions.get(application_id)
    if session is None or not session.browser.is_connected():
        raise RuntimeError("Browser session is not open. Open the application browser again.")
    pages = [p for p in session.context.pages if not p.is_closed()]
    if not pages:
        raise RuntimeError("No browser tabs remain open. Open the application browser again.")
    page = pages[-1]
    # An older tab explicitly focused by the user takes precedence.
    for candidate in reversed(pages):
        try:
            if await candidate.evaluate("document.hasFocus()"):
                page = candidate
                break
        except Exception:
            continue
    session.page = page
    try:
        await page.bring_to_front()
    except Exception:
        pass
    logger.info("Application %s: open_pages=%s active_url=%s", application_id, len(pages), _log_url(page.url))
    return page


async def open_application_browser(application_id: int, url: str) -> str:
    if application_id in _sessions:
        try:
            return (await get_active_page(application_id)).url
        except RuntimeError:
            old = _sessions.pop(application_id)
            await old.browser.close()
            await old.playwright.stop()
    playwright = await async_playwright().start()
    try:
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        _sessions[application_id] = BrowserSession(playwright, browser, page)
        await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    except Exception:
        # Keep a launched browser available for manual navigation after a timeout.
        if application_id not in _sessions:
            await playwright.stop()
        raise
    return page.url


async def resolve_application_page(application_id: int) -> dict:
    page = await get_active_page(application_id)
    context = await get_form_context(page)
    # Navigation and Apply clicks remain manual: an Apply button can be final submit.
    has_form = await context.locator('input[type="file"], input[autocomplete="given-name"]').count()
    return {"status": "resolved" if has_form else "needs_manual_navigation", "url": page.url}


async def get_form_context(page: Page):
    """Score main document and nested frames, allowing bounded dynamic injection."""
    best = page
    best_score = 0
    for attempt in range(6):
        best, best_score = page, 0
        contexts = [page, *[f for f in page.frames if f != page.main_frame]]
        for context in contexts:
            try:
                score = 0
                for selector, weight in [
                    ('input[type="file"]', 8),
                    ('input[type="email"]', 3),
                    ('input[autocomplete="given-name"], input[name*="first" i], input[id*="first_name" i]', 3),
                    ('input[autocomplete="family-name"], input[name*="last" i]', 3),
                    ('input[type="tel"]', 1),
                ]:
                    if await context.locator(selector).count():
                        score += weight
                logger.debug("Form candidate url=%s score=%s", _log_url(context.url), score)
                if score > best_score:
                    best, best_score = context, score
            except Exception:
                continue  # A frame may detach while the ATS loads.
        if best_score >= 8 or attempt == 5:
            break
        await asyncio.sleep(0.5)
    logger.info("Selected form context url=%s score=%s frames=%s", _log_url(best.url), best_score,
                [_log_url(f.url) for f in page.frames])
    return best


async def fill_first(page, selectors, value: str) -> bool:
    if not value:
        return False
    for locator in selectors:
        try:
            # Multiple matches are ambiguous; require a unique editable text input.
            eligible = []
            for i in range(await locator.count()):
                item = locator.nth(i)
                kind = (await item.get_attribute("type") or "text").lower()
                if kind not in {"text", "email", "tel", "url"}:
                    continue
                if await item.evaluate("el => el.tagName !== 'INPUT'"):
                    continue
                if await item.is_visible() and await item.is_editable():
                    eligible.append(item)
            if len(eligible) == 1:
                await eligible[0].fill(value, timeout=2000)
                return True
        except Exception:
            continue
    return False


async def upload_resume_file(page, resume_bytes: bytes, resume_filename: str) -> bool:
    if not resume_bytes:
        return False
    payload = {"name": resume_filename, "mimeType": "application/pdf", "buffer": resume_bytes}
    candidates = [
        page.get_by_label(re.compile(r"^(?:upload |attach |your )?(?:resume|curriculum vitae|cv)\b", re.I)),
        page.locator('input[type="file"][name*="resume" i], input[type="file"][id*="resume" i], input[type="file"][name="cv" i], input[type="file"][id="cv" i]'),
        page.locator('input[type="file"]'),
    ]
    for locator in candidates:
        try:
            if await locator.count() != 1:
                continue
            item = locator.nth(0)
            if await item.get_attribute("type") != "file":
                continue
            description = " ".join([(await item.get_attribute(k) or "") for k in ("name", "id", "aria-label")])
            if re.search(r"cover.?letter|photo|transcript|signature", description, re.I):
                continue
            await item.set_input_files(payload, timeout=5000)
            return True
        except Exception:
            continue
    return False


async def autofill_application_form(application_id: int, profile, resume_bytes: bytes | None = None,
                                    resume_filename: str | None = None) -> dict:
    page = await get_active_page(application_id)
    context = await get_form_context(page)
    filled, skipped = [], []
    fields = [
        ("first_name", "first_name", r"first\s*name", "given-name", ["first_name", "firstName", "firstname"]),
        ("last_name", "last_name", r"last\s*name|surname", "family-name", ["last_name", "lastName", "lastname"]),
        ("email", "email", r"e-?mail(?: address)?", "email", ["email"]),
        ("phone", "phone", r"(?:phone|mobile)(?: number)?", "tel", ["phone", "telephone", "mobile"]),
        ("linkedin", "linkedin_url", r"linkedin(?: (?:url|profile))?", None, ["linkedin", "linkedin_url"]),
        ("github", "github_url", r"github(?: (?:url|profile))?", None, ["github", "github_url"]),
        ("portfolio", "portfolio_url", r"(?:portfolio|website|personal site)(?: url)?", None, ["portfolio", "website", "portfolio_url"]),
    ]
    for key, attr, label, autocomplete, names in fields:
        selectors = [context.get_by_label(re.compile(r"^\s*(?:" + label + r")\s*\*?\s*$", re.I))]
        for name in names:
            selectors.append(context.locator(f'input[name="{name}" i], input[id="{name}" i]'))
        if autocomplete:
            selectors.append(context.locator(f'input[autocomplete="{autocomplete}"]'))
        success = await fill_first(context, selectors, getattr(profile, attr, None))
        (filled if success else skipped).append(key)
    uploaded = bool(resume_bytes and resume_filename) and await upload_resume_file(context, resume_bytes, resume_filename)
    logger.info("Application %s: filled=%s skipped=%s resume_uploaded=%s", application_id, filled, skipped, uploaded)
    return {"status": "ready_for_review", "url": page.url, "filled_fields": filled,
            "skipped_fields": skipped, "resume_uploaded": uploaded, "manual_review_required": True}
