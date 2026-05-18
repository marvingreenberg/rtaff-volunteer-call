# Demo Scenario

Canonical scenario for showcasing the volunteer-call lifecycle. The
Playwright script at `frontend/e2e/demo.spec.ts` follows this document
step-for-step; if the two drift, this file is the source of truth and
the script gets updated, not the other way around.

## Setup

In one terminal:

```
make dev-db-reset           # fresh seed with real RT-AFF contacts
make dev                    # backend + frontend + Mailpit
```

In another:

```
cd frontend && pnpm exec playwright install chromium    # one-time
make demo                   # records to frontend/test-results/demo/<run>/
```

The recorded `video.webm` shows the full flow with an injected
narration overlay; the live page also shows incoming Mailpit messages
side-by-side via a transient iframe panel.

## Cast

- **Admin (Don Ryan)** — logs in via his personal gmail alias
  (`donryanemail@gmail.com`). His primary, the @rebuildingtogether-aff.org
  address, remains the channel for any outbound *notification* email he
  receives.
- **Vick Fisher** — volunteer, full availability, ends up assigned.
- **Bryan Cobb** — volunteer, partial availability.

## Flow

| # | Step | Narration |
|---|---|---|
| 1 | Admin Don Ryan logs in with his gmail alias. | Demonstrates the email-alias feature: any of a person's emails can authenticate; only the primary receives notifications. |
| 2 | Magic link arrives at gmail (visible in Mailpit panel). Click verifies. | Real magic-link flow — no DEMO_MODE shortcut. |
| 3 | Don creates a new volunteer call ("Call for Volunteers <Date> - …"). | |
| 4 | Don adds two tasks by hand. | Demonstrates the inline Add Task affordance. |
| 4a | `scripts/demo_bulk.py add-tasks --count 7 --thursday 2` adds the rest of the schedule. | Shows seven more tasks landing, two on the upcoming Thursday. |
| 5 | "Send Call" → invites go out; status → `waiting`. | Mailpit panel shows one invite email arriving. |
| 6 | Vick Fisher logs in, checks every task, scrolls up and caps himself at 2/week for week 1 and 4 for week 2, submits. | Demonstrates the per-week cap controls — `max_tasks_per_week` and `max_tasks_per_week_2`. |
| 7 | Bryan Cobb logs in, picks a couple tasks in week 1 and a couple in week 2 (leaves the default cap), submits. | Shows week-aware selection without touching the cap. |
| 8 | Narration: "Overnight, 24 more volunteers responded…" `respond-availability --count 24` runs in parallel. | |
| 9 | Don logs back in, opens the Assignment Dashboard, auto-assigns team leads, then walks task-by-task filling each to exactly `volunteers_needed` — deliberately over-filling a couple to surface the "Extra!" tag and 🥵 badge. Clicks Done Assigning. | Status → `assigned`. The 💯 badge appears next to any volunteer fully booked for a week (e.g. "2/2 for week 1"); 🥵 fires when an admin pushes past the cap. |
| 10 | "Send Assignments" → assignment emails to volunteers + roster emails to team leads. | Mailpit panel shows one assignment email arriving. |
| 11 | Vick Fisher logs back in and sees the final assignment. | |

## Cast / data seed reference

`scripts/initdb/02-reference-data.sql` populates 62 real people (5
admins, 10 team leads, 47 volunteers). Multi-email contacts (Darek
Newby, Don Ryan, Charles Monfort) use the `person_login_aliases` table.
William Marshall has memberships in ACR/RAMP/LIFT in addition to RTX
so single-task program workflows still have a default team-lead
candidate (replaces the old Carmen seed).

## Bulk helpers

`scripts/demo_bulk.py` provides two subcommands the spec invokes
mid-flow. They write through the same async SQLAlchemy session
factory the API uses, so rows are indistinguishable from API-created
ones.

- `add-tasks --call-id <uuid> --count N --thursday K`
- `respond-availability --call-id <uuid> --count N`

Run manually:

```
cd backend && uv run python ../scripts/demo_bulk.py add-tasks \
    --call-id <uuid> --count 7 --thursday 2
```
