# Chrome extension autofill test report

Date: October 30, 2026 (America/Chicago)

## Result

**Pass for the tested local preview. Not yet validated for public release.**

| Check | Result |
| --- | --- |
| Complete backend suite, including browser tests | 66 passed, 0 failed, 0 skipped (6.39 seconds) |
| Extension JavaScript unit tests | 5 passed, 0 failed (38.97 milliseconds) |
| Frontend TypeScript and production build | Passed |
| Working diff whitespace check | Passed |

The 66 backend tests include 6 real Chromium tests: 2 existing browser-service
tests, 3 extension form tests, and 1 installed-extension popup test. Other tests
cover API/database integration and isolated logic. Test counts include prior
project tests; they are not all new extension tests.

## What was verified

- Loaded the actual unpacked extension manifest and popup in bundled Chromium,
  using a fresh temporary browser profile. No manifest changes or mocked Chrome
  installation were required.
- Imported a valid application JSON; displayed its application ID and selected
  resume name/version; enabled autofill only after successful import.
- Cleared imported data and verified that reloading the popup resets selection.
- Rejected invalid formats, malformed JSON, files over 32 KB, and unsupported URLs;
  autofill remained disabled.
- Executed the exact injected autofill function against local HTML served at
  intercepted URLs for `jobs.lever.co`, `job-boards.greenhouse.io`, and
  `boards.greenhouse.io`. All requests in those form tests were fulfilled locally.
- Filled full name, first name, email, and phone. Preserved an existing last-name
  answer; skipped ambiguous GitHub inputs, a hidden LinkedIn input, and a salary
  question whose technical name resembled a portfolio field.
- Left password, signature, work-authorization, demographic, legal-checkbox,
  resume-upload, and final-submit controls untouched.
- Rejected a different job posting before writing fields.
- Verified unit-level rejection of unsupported schemes, lookalike hosts, credential
  URLs, non-string contact fields, and oversized field values.
- Verified the manifest requests only `activeTab` and `scripting`, without
  persistent host permissions or automatic content scripts.
- Exercised the real export API with an isolated async SQLite database: exact
  approved resume metadata, only allowlisted contact fields, no resume content,
  404 for an unknown application, and 400 after resume approval is revoked.
- Re-ran the existing application/search regression suite and frontend build.

## Findings and limits

No product failure was found in these executed scenarios. An initial popup test
failed because its polling helper conflicted with the extension's Content
Security Policy. Replacing that helper with locator assertions fixed the test;
the extension policy and product code were not relaxed.

These checks do **not** prove compatibility with current live employer forms.
The form fixtures are representative local HTML, not copies fetched from live
Greenhouse or Lever postings. No real application or personal data was submitted.

The installed-popup test opens `popup.html` as an extension page. It verifies
actual module loading and import UI, but does not reproduce a native toolbar
click, OS file picker, or the complete `activeTab` grant-to-injection flow.
That full interaction still needs a manual test in normal Chrome.

Cross-origin iframes, shadow DOM, custom widgets, and changing live ATS layouts
remain unverified or unsupported. Resume upload and submission remain manual.
Account linking is absent; the export API retains the app's current local
single-user behavior. Public deployment needs authentication and per-user ownership.
SQLite tests do not establish PostgreSQL locking or concurrency behavior.

## Reproduce

From `backend/`:

```sh
RUN_BROWSER_TESTS=1 .venv/bin/python -m pytest -q
```

From `extension/`:

```sh
npm test
```

From `frontend/`:

```sh
npm run build
```

## Remaining manual acceptance check

Load this directory unpacked in normal Chrome. Prepare an application using
synthetic contact data, download its export, and open a matching live ATS page.
Click the extension toolbar action, use the native file picker to import the
export, verify the resume selection, and click Fill contact fields. Check the
reported fields against the visible form, verify existing answers remain intact,
and confirm nothing uploads or submits. Repeat for Greenhouse and Lever, then
close/reopen the popup and verify no imported data remains. Do not submit.
