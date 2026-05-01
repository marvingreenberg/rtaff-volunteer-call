# RT-AFF Volunteer Call System

A standalone web application for managing volunteer call notifications for Rebuilding Together Arlington/Fairfax/Falls Church.

## Overview

This system handles the volunteer recruitment workflow: administrators create volunteer calls describing upcoming tasks, send notifications to a volunteer pool, volunteers indicate availability, administrators assign teams, and assigned volunteers receive confirmation notifications.

Extracted from the larger [rtaff workflow system](https://github.com/...) to operate independently with a narrower scope.

## Planned Features

- **Volunteer Call Creation** — administrators enter a list of tasks, each with description, date, time range, full address, and team lead
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
make dev          # Start DB + backend + frontend
make test         # Run all tests
make lint         # Run all linters
make dev-db-reset # Destroy DB volume and start fresh
```

## Status

Planning phase — no implementation yet. See `volunteer-call.md` for the full task specification.

## License

Private — Rebuilding Together Arlington/Fairfax/Falls Church
