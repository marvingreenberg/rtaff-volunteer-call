# RT-AFF Volunteer Call System

A standalone web application for managing volunteer call notifications for Rebuilding Together Arlington/Fairfax/Falls Church.

## Overview

This system handles the volunteer recruitment workflow: administrators create volunteer calls describing upcoming tasks, send notifications to a volunteer pool, volunteers indicate availability, administrators assign teams, and assigned volunteers receive confirmation notifications.

Extracted from the larger [rtaff workflow system](https://github.com/...) to operate independently with a narrower scope.

## Planned Features

- **Volunteer Call Creation** — administrators enter a list of tasks, each with description, date, start time, full address, and team lead
- **Notification Dispatch** — send calls via email (cloud service integration) and/or SMS with subscription management
- **Volunteer Response** — volunteers indicate availability through a mobile-friendly interface
- **Team Assignment** — assign volunteers to tasks, set/update team leads
- **Assignment Notification** — notify assigned volunteers with task details
- **Subscription Management** — volunteers can unsubscribe, pause (date range), and choose delivery method (email/SMS)
- **Volunteer Database** — under 1,000 volunteers with stats (last assignment, assignment rate)
- **External Data Adapter** — architectural stub for connecting to external volunteer data sources (SharePoint, external DB)

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy 2.0, PostgreSQL
- **Frontend**: SvelteKit, Svelte 5, TypeScript
- **Infrastructure**: Docker for dev DB, single-container deployment

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python project manager)
- [pnpm](https://pnpm.io/) (frontend package manager)
- [Docker](https://www.docker.com/) (PostgreSQL for development)

## Project Structure

```
rtaff-volunteer-call/
├── backend/
│   └── src/volunteer_call_api/
│       ├── models/         # SQLAlchemy models
│       ├── routes/         # FastAPI endpoints
│       ├── schemas/        # Pydantic request/response schemas
│       └── services/       # Business logic (notifications, etc.)
├── frontend/
│   └── src/
│       ├── routes/         # SvelteKit pages
│       └── lib/
│           ├── api/        # API client + types
│           └── components/ # Reusable components
├── scripts/
│   └── dev-db.sh           # Dev database lifecycle
├── Makefile
└── volunteer-call.md       # Original task specification
```

## Development

```bash
make dev          # Start DB + Mailpit + backend + frontend
make test         # Run all tests
make lint         # Run all linters
make dev-db-reset # Destroy DB volume and start fresh
```

The dev stack runs PostgreSQL and Mailpit (a local SMTP catcher) in
Docker; the backend defaults to `localhost:1025` for SMTP and emails
are visible in Mailpit's web UI at `http://localhost:8025`.

## Database schema and migrations

Pre-1.0: schema lives in `scripts/initdb/01-schema.sql` and reference
data in `scripts/initdb/02-reference-data.sql`. The dev DB is reset
and reseeded freely (`make dev-db-reset`); schema changes go directly
into those files. The `backend/src/volunteer_call_api/alembic/`
scaffolding is in place but **no migrations are written or applied
until after the 1.0.0 release** — there is no production data to
preserve, and migration overhead would only slow down iteration.
After 1.0.0, write migrations against `scripts/initdb/01-schema.sql`
as the baseline.

## Deployment

Production deployment is to GCP Cloud Run with PostgreSQL hosted on
Neon (free tier) or Cloud SQL. Setup is staged across three docs:

1. `docs/GCP_SETUP.howto` — one-time GCP project setup (gcloud auth,
   project create, API enablement, service accounts, GitHub Actions
   secrets). Driven by `scripts/setup-gcp-project` and
   `scripts/set-gcloud-creds-for-deploy`.
2. `docs/NEON_SQL.howto` — Neon database setup, asyncpg connection
   string, Secret Manager wiring, seeding.
3. `docs/CLOUD_SQL.howto` — upgrade path from Neon to Cloud SQL.

A CI/deploy workflow modelled on the parent rtaff project still needs to
be ported (see `# todo.md`).

## Status

Phase-1 implementation is in place: backend (FastAPI + SQLAlchemy +
PostgreSQL) with magic-link auth, people management, volunteer calls
with tasks, availability submission, team assignments with an
interactive assign view, and email/SMS notification scaffolding (email
via Mailpit in dev). Frontend (SvelteKit + Svelte 5) covers the admin
flows for call creation, the assignment view, and the volunteer-facing
availability submission. Local dev runs end-to-end via `make dev`.

Production deployment hasn't been performed yet — the GitHub Actions
CI/deploy workflows still need to be ported from the parent rtaff
project. See `# todo.md` for the outstanding items.

## License

Private — Rebuilding Together Arlington/Fairfax/Falls Church
