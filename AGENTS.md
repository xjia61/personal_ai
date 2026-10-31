# AGENTS.md

## Project Purpose

This project is a Personal AI Career Agent.

The goal is to build a real, deployable web application that helps users manage their career information, discover relevant jobs, prepare job applications, track application outcomes, and eventually understand job-market trends and career-development opportunities.

This is not intended to be a tutorial project or a simple job-search wrapper.

The product should become something users can access online and use regularly during a real job search.

---

## Product Vision

The Career Agent should support the full career workflow:

```text
Career Profile
      ↓
Job Discovery
      ↓
Job Analysis
      ↓
Resume Selection / Tailoring
      ↓
Application Assistance
      ↓
Application Tracking
      ↓
Market / Career Intelligence
      ↓
Career Development Plan
```

The system should reduce repetitive work while keeping important decisions under human control.

---

## Core Product Areas

The application should support the following major areas.

### Career Profile

Maintain a structured record of the user's real professional background, including:

- education
- employment
- projects
- technical skills
- domain expertise
- certifications
- publications
- research
- other verified experience

Career Profile is the source of truth for professional information.

AI must not invent qualifications that are not supported by the Career Profile.

### Resume Management

Support multiple resume versions.

Users should be able to:

- create resumes
- import resumes
- edit resumes
- approve resume versions
- export PDF/DOCX
- select a specific resume for an application

An application must record the exact ResumeVersion used.

Future resume generation or tailoring must remain grounded in the Career Profile.

### Job Discovery

Support job discovery from multiple sources.

The system must not depend permanently on a single provider.

Possible sources may include:

- web/search APIs
- Greenhouse
- Lever
- Ashby
- Workday
- company career pages
- public job APIs
- curated job sources
- future providers

Tavily may be used for discovery, but it is a provider, not the architecture.

### Job Database

Relevant jobs should be normalized and stored in PostgreSQL.

Jobs may later support:

- deduplication
- source tracking
- official application URLs
- requirement extraction
- classification
- analytics

Keep `source_url` separate from `application_url`.

Prefer official company or ATS application URLs when available.

### Job Analysis

The system may analyze jobs for:

- required skills
- preferred skills
- education
- experience
- responsibilities
- certifications
- domain knowledge

Requirement extraction should be cached so unchanged job descriptions are not repeatedly analyzed.

### Job Classification

Jobs may eventually be classified along multiple dimensions:

- seniority
- role family
- industry/domain
- specialties

Examples:

Seniorities:
- intern
- new_grad
- entry
- mid
- senior
- staff_plus
- manager

Role families:
- software engineering
- data analytics
- data engineering
- data science
- AI / ML
- bioinformatics
- QA / test
- DevOps / cloud

Industries:
- healthcare / life sciences
- finance
- general technology
- education
- government

Classification and requirement extraction are separate concepts.

### Application Assistance

The system should support semi-automatic job applications.

Typical flow:

```text
Choose Job
→ Choose Resume
→ Prepare Application
→ Open Application Page
→ User handles login if needed
→ Autofill safe fields
→ Upload Resume
→ Human Review
→ User submits manually
```

The application process must remain human-in-the-loop.

### Application Tracker

Track application history and outcomes.

Applications may include statuses such as:

- preparing
- ready_for_review
- applied
- screening
- interview
- rejected
- offer
- withdrawn

Track the exact job and resume used.

### Career Intelligence

Long-term, the system should analyze groups of relevant jobs rather than only individual jobs.

Potential analysis includes:

- popular technologies
- common requirements
- requirements by career direction
- requirements by industry
- requirements by seniority
- skill trends over time

The system should compare market demand with the Career Profile and help identify high-value learning priorities.

---

## Core Domain Rules

Keep these concepts separate:

### Career Profile
Source of truth for real professional history.

### ResumeVersion
A particular presentation of Career Profile information.

### ApplicationProfile
Stable application-form information such as name, email, phone, address, LinkedIn, GitHub, portfolio, and work authorization.

### Job
An external job posting.

### Application
One real application attempt linking a Job with one exact ResumeVersion.

Do not merge these concepts.

---

## Backend Technology

Core backend stack:

- Python
- FastAPI
- async SQLAlchemy
- PostgreSQL
- Playwright
- configurable AI / LLM providers

External search, ATS, and job-data services should be treated as interchangeable integrations.

Provider-specific code should be isolated when practical.

Do not tightly couple business logic to one external API.

---

## Frontend Technology

Core frontend stack:

- React
- TypeScript
- Vite

The frontend should remain a web application that can eventually be deployed publicly.

Avoid unnecessary frontend frameworks unless there is a clear reason.

---

## Architecture Principles

Prefer clear separation between:

```text
Frontend
API layer
Domain / service logic
Provider integrations
Database
Background processing
```

Provider-specific behavior should stay in provider or ingestion services.

Downstream features should operate on normalized internal models.

Avoid duplicating working functionality.

Before introducing a new service or model, inspect whether equivalent functionality already exists.

---

## AI Usage Principles

Use AI where semantic interpretation adds value.

Do not use expensive AI calls for tasks that can be handled reliably with:

- SQL
- Python
- deterministic rules
- dictionaries
- regex
- cached results

Possible future strategy:

```text
deterministic extraction
→ cheap/local model
→ stronger model only when necessary
```

AI output should be structured whenever practical.

---

## Browser Automation Safety

Browser automation must remain human-in-the-loop.

Never automatically:

- click final Submit
- solve or bypass CAPTCHA
- enter MFA codes
- create accounts without user action
- store passwords
- provide electronic signatures
- accept legal attestations
- answer demographic questions
- answer ambiguous sponsorship questions
- submit salary expectations without explicit user instruction

Manual authentication and review are expected parts of the workflow.

---

## Database Safety

The development database contains real project data.

Never:

- destroy database volumes
- run `docker compose down -v`
- reset the database to fix ordinary bugs
- delete existing data unless explicitly requested

Prefer safe migrations and targeted schema changes.

Do not create a second SQLAlchemy `Base`.

---

## Existing Model Structure

The project previously used:

- `app/models.py`
- `app/schemas.py`

These were moved to:

- `app/legacy_models.py`
- `app/legacy_schemas.py`

because package directories now exist:

- `app/models/`
- `app/schemas/`

Do not recreate the conflicting files.

Inspect existing import patterns before adding models or schemas.

---

## Security

Never expose or commit:

- `.env`
- API keys
- passwords
- MFA codes
- private tokens
- database credentials

Do not place backend secrets in frontend code.

Do not log sensitive user values unnecessarily.

---

## Deployment Goal

Localhost is the development environment, not the final product.

The long-term goal is an internet-accessible application.

Conceptually:

```text
Internet
   ↓
Web Frontend
   ↓
Backend API
   ↓
Managed PostgreSQL
   ↓
Background Workers / Schedulers
   ↓
External AI / Search / ATS Providers
```

Hosting vendors are not permanently fixed.

The architecture should remain portable.

Interactive browser automation may remain a specialized local, browser-extension, or remote-browser component even while the main application is deployed online.

---

## Multi-User Direction

The product may eventually support users beyond the original developer.

Avoid architecture that unnecessarily assumes all data belongs to one permanent global user.

Future production needs may include:

- authentication
- authorization
- per-user data ownership
- privacy
- per-user Career Profiles
- per-user resumes
- per-user applications

Do not build unnecessary enterprise infrastructure prematurely.

---

## Development Guidelines

Before changing code:

1. inspect the existing implementation
2. search for reusable code
3. inspect actual model fields
4. inspect existing API patterns
5. understand relevant tests
6. make the smallest coherent change

Prefer feature-level implementation over one-line-at-a-time edits.

Do not perform unrelated large refactors.

Do not replace working frameworks or major technologies without a clear reason.

---

## Testing

After meaningful changes:

- run relevant backend tests
- run frontend TypeScript/build checks
- perform manual integration testing when appropriate

Example commands may include:

```bash
pytest
npm run build
```

Use repository-specific commands where they differ.

Do not claim a feature works without testing when practical.

---

## Git Hygiene

Before commits, inspect:

```bash
git status
```

Do not commit:

- `.env`
- API keys
- local browser profiles
- temporary resume files
- generated secrets
- database volumes

Use focused commits for coherent features.

---

## Product Development Principle

The goal is not to maximize feature count.

Prioritize:

- real usability
- reliable behavior
- good architecture
- real job data
- user control
- useful career insight
- deployability
- maintainability

The system should evolve based on real usage and evidence.

---

## Task-Specific Instructions

This file defines project-level context and long-term constraints.

Specific implementation tasks, acceptance criteria, and temporary priorities belong in the current Codex prompt.

Do not implement roadmap features simply because they are described here.

When the current task conflicts with an established architectural rule in this file, identify the conflict before making a broad architectural change.