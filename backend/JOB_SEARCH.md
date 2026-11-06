# Current job search and extension handoff

Run the existing FastAPI backend and React frontend. Set `TAVILY_API_KEY` in the
backend environment; never put it in the frontend or extension. Searches are
on demand and can consume Tavily credits.

## Use

1. Open Jobs, enter up to four alternative roles/keyword phrases and up to four
   locations (one per line, preserving city/state commas). Choose a publication
   window, remote preference, and minimum keyword relevance.
2. Find Jobs discovers supported Greenhouse/Lever posting URLs. The backend
   checks official APIs and saves relevant results. It performs at most eight
   discovery queries and twenty ATS checks, with four concurrent requests in
   each stage. Coverage is limited to discovered postings, not all employers.
3. Review verified availability and its check timestamp. Unknown publication
   dates are retained unless the strict-date checkbox is selected. Search dates,
   discovery timestamps, and employer update times are not publication evidence.
   Date filtering uses calendar dates; the one-day option is not an exact 24-hour
   timestamp filter. Lever publication dates remain unknown with this integration.
4. Open a job, select an approved resume, and choose Verify & Prepare Application.
   Availability is checked again. Closed or unverifiable postings return 409;
   retry verification later rather than assuming a timeout means closed.
5. Download Extension Data, open the exact official application link, import
   the JSON in the extension, and click Fill contact fields. Review answers,
   upload the selected resume, submit manually, then mark the application applied.

Keyword relevance measures word overlap with the best matching alternative role;
it is not an AI fit assessment. Known official location metadata is filtered;
unknown locations are retained for review. Employer board identifiers are used as
company labels when an official company name is unavailable.

## Data and API compatibility

- `POST /api/jobs/search` retains its list response. Request limits are validated;
  `strict_dates` defaults to false. Provider failures return a readable 502.
- Job responses add nullable `availability_status` and `availability_checked_at`.
  These fields are separate from saved-job status and application progress.
- `POST /api/jobs/{id}/verify` refreshes those fields without changing application
  history. Supported hosts match the extension: boards.greenhouse.io,
  job-boards.greenhouse.io, and jobs.lever.co.
- New postings use a canonical ATS source URL; existing discovery URLs are
  preserved. ATS host aliases and Lever `/apply` URLs share a posting identity.
  Official application URLs remain separate from source URLs.
- `GET /api/applications/{id}/extension-data` requires a supported official URL
  and an approved resume, and exports only allowlisted contact fields and resume
  metadata. Existing local Playwright assistance is still available separately.

## Safe schema upgrade

On the next backend startup, `init_db` runs version `001_job_availability` from
`app/migrations.py` inside a transaction after `create_all`. It adds only missing,
nullable job columns and records completion in `career_schema_migrations`.
PostgreSQL startups take an advisory transaction lock before schema changes.
Existing rows and application history are preserved; nothing is reset or deleted.
The implementation tests use isolated databases; the development database was
not migrated during automated testing. Restart the backend to apply the upgrade.

## Validation

Latest validation: **102 backend/browser tests passed**, **5 extension unit tests
passed**, and the frontend TypeScript/production build passed. The backend count
includes seven Chromium tests. No tests failed or were skipped in the full run.

Run `npm run build` in `frontend/` before the browser suite, then from `backend/`:

```sh
.venv/bin/python -m pytest -m 'not browser' -q
RUN_BROWSER_TESTS=1 .venv/bin/python -m pytest -q
```

The browser suite includes the built React search UI, export download, and the
exact extension autofill function against local forms. That UI test uses API
fixtures; separate integration tests exercise real API routes, services, and
async database persistence. ATS tests cover date provenance, provider failures,
identity matching, invalid URLs, closed postings, and unavailable/unknown states.
Migration tests verify additive changes, preserved rows, and repeat execution.
PostgreSQL concurrency behavior is not established by SQLite tests.

A separate read-only live check successfully discovered five bioinformatics
results and verified five official postings (Greenhouse and Lever). This did
not write to the development database or submit an application. Live form
compatibility and the native Chrome toolbar flow still require manual checks.

The app remains local and single-user. Authentication and per-user ownership
must precede public deployment.
