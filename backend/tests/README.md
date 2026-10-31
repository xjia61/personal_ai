# Career Agent tests

From `backend/`, install test dependencies into the virtual environment:

```sh
.venv/bin/python -m pip install -r requirements-test.txt
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest -m unit -q
.venv/bin/python -m pytest -m 'integration and not browser' -q
```

`aiosqlite` is test-only. Runtime dependencies and PostgreSQL configuration are unchanged.
Integration tests create a fresh in-memory SQLite database using the existing SQLAlchemy
Base and async sessions, with foreign keys enabled. They construct a test FastAPI app
without the production startup lifecycle and override its database dependency.
No development database, real credentials, or external services are needed.

Coverage includes provider response normalization and failures, search time/date rules,
job filtering and deduplication, preservation of application URLs, approved resume
selection, application preparation, autofill handoff, persistence, and manual status updates.
Network and browser boundaries are mocked in API/database integration tests.
SQLite does not verify PostgreSQL migrations, locking, or concurrent transactions.

## Browser integration

```sh
.venv/bin/python -m playwright install chromium
RUN_BROWSER_TESTS=1 .venv/bin/python -m pytest -m browser -q
```

These tests use local HTML forms, not employer sites. They exercise real Chromium,
iframe/delayed-form discovery, resume uploads, ambiguous field handling, and leaving
sensitive fields and submission untouched. Chromium must be permitted to launch.

Frontend validation runs separately from `frontend/` with `npm run build`.
The browser extension is not implemented yet; these tests cover the current backend
autofill workflow, not future extension permissions or authentication.
