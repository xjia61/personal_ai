import threading
from pathlib import Path

from playwright.sync_api import sync_playwright


LOCK = threading.Lock()
SESSIONS = {}


def get_session(job_id: int):
    with LOCK:
        return SESSIONS.get(job_id, "not_started")


def set_session(job_id: int, state: str):
    with LOCK:
        SESSIONS[job_id] = state


def fill_field(page, value, labels, selectors):
    if not value:
        return False

    for selector in selectors:
        locator = page.locator(selector)

        if locator.count() == 1:
            try:
                if locator.is_visible():
                    locator.fill(value, timeout=2000)
                    return True
            except Exception:
                pass

    for label in labels:
        locator = page.get_by_label(label, exact=False)

        if locator.count() == 1:
            try:
                if locator.is_visible():
                    locator.fill(value, timeout=2000)
                    return True
            except Exception:
                pass

    return False


def run_application(
    job_id: int,
    url: str,
    profile: dict,
):
    try:
        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=False
            )

            try:
                page = browser.new_page()

                page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=30000,
                )

                page.wait_for_timeout(1200)

                fields = [
                    (
                        "first_name",
                        ["First Name"],
                        [
                            'input[name="first_name"]',
                            'input[autocomplete="given-name"]',
                        ],
                    ),
                    (
                        "last_name",
                        ["Last Name"],
                        [
                            'input[name="last_name"]',
                            'input[autocomplete="family-name"]',
                        ],
                    ),
                    (
                        "email",
                        ["Email", "Email Address"],
                        [
                            'input[name="email"]',
                            'input[type="email"]',
                        ],
                    ),
                    (
                        "phone",
                        ["Phone", "Phone Number"],
                        [
                            'input[name="phone"]',
                            'input[autocomplete="tel"]',
                        ],
                    ),
                    (
                        "linkedin_url",
                        ["LinkedIn"],
                        [
                            'input[name="linkedin"]',
                            'input[name="urls[LinkedIn]"]',
                        ],
                    ),
                ]

                for key, labels, selectors in fields:
                    fill_field(
                        page,
                        profile.get(key, ""),
                        labels,
                        selectors,
                    )

                resume = profile.get("resume_file_path")

                if resume and Path(resume).is_file():

                    locator = page.locator(
                        'input[type="file"]'
                        '[name*="resume" i],'
                        'input[type="file"]'
                        '[id*="resume" i]'
                    )

                    if locator.count() == 1:
                        try:
                            locator.set_input_files(
                                resume,
                                timeout=3000,
                            )
                        except Exception:
                            pass

                set_session(job_id, "browser_open")

                print(
                    f"Application ready for review: "
                    f"job {job_id}"
                )

                # Keep the window open for the user.
                # The code does not click Submit.
                page.wait_for_event(
                    "close",
                    timeout=0,
                )

                set_session(job_id, "finished")

            finally:
                browser.close()

    except Exception as exc:
        print(
            f"Application browser failed "
            f"for job {job_id}: {exc}"
        )
        set_session(job_id, "error")


def start_application(
    job_id: int,
    url: str,
    profile: dict,
) -> bool:

    with LOCK:
        current = SESSIONS.get(job_id)

        if current in {"starting", "browser_open"}:
            return False

        SESSIONS[job_id] = "starting"

    thread = threading.Thread(
        target=run_application,
        args=(job_id, url, profile),
        daemon=True,
    )

    thread.start()

    return True