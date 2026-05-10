# todo

## Deferred items from prior sessions

### CI / CD

- Set up GitHub Actions for this project, modelled on `../rtaff/.github/workflows/`:
  - `ci.yml` — backend job (Postgres service, `make lint-be`, `make test-backend`, codecov upload),
    frontend job (`make lint-fe`, `make test-frontend`), and a type-generation verification job.
  - `deploy.yml` — Docker build to GHCR + GCP Artifact Registry, Cloud Run deploy on `v*` tags.
  - Dependabot config for npm + uv lockfiles.

### End-to-end testing

- `frontend/e2e/demo-scenario.spec.ts` exists but is stale — references the old "Add Task" toggle,
  old placeholders ("e.g., Roof repair at 123 Main St", "123 Main St"), the removed
  "Open for Volunteers" / "Close Call" buttons, and the deleted dashboard/availability routes.
  Either rebuild it against the current UI or split into smaller targeted specs (call creation,
  task entry, assignment).
- Decide whether e2e runs in CI (headless) or stays manual-only for the demo recording use case.
- Wire whichever choice into `make test-e2e` so it's discoverable.

### Backend tests

- `backend/tests/conftest.py` currently has no DB fixture, so route-level tests are absent
  (route coverage is 20-40%). Add a Postgres test-DB fixture (mirroring rtaff's CI service
  pattern) and write integration tests for:
  - `send-invites` self-transitions Draft to Open and rejects when already Closed.
  - `send-invites` recipient query filters by `call.program` membership.
  - `PUT /volunteer-calls/{id}` no longer fires notifications on close.
  - `POST /send-assignment-notices` requires Closed status and returns counts.
  - `assignment-overview` includes `available_volunteers` filtered correctly.
  - `GET /people/{id}` never serializes `calendar_url` even after PUT /calendar.
  - `GET /volunteer-calls/{id}/calendar/conflicts` enforces self-only access.
  - `DELETE /volunteer-calls/{id}` cascades through tasks, availabilities, assignments.
  - `PUT /people/{id}/calendar` returns 422 on unreachable / non-iCal URLs.

### Task / call UI follow-ups

- Address autocomplete on `TaskEntryForm` (city is hardcoded; address is plain text pending a source).
- Under-/over-assignment policy: the assign view doesn't cap at `volunteers_needed`, and
  Send Assignment Notices doesn't gate on every task being full. Decide intended behaviour.
- "Assignment complete" gate: per the team-lead spec, an assignment can't be complete if any
  task has no team lead. Wire this into the Send Assignment Notices guard once the
  under/over-assignment policy is decided.
- Admin-on-behalf-of-volunteer availability entry was dropped with the `/availability` page;
  if needed, add a small affordance inside the assign view (per-task "Add availability" combobox).
- Optimistic UI on the assign page (currently refetches `assignment-overview` after each
  click — fine at this scale but will feel sluggish at higher task/volunteer counts).

### Calendar follow-ups

- Recurring-event expansion. `services/calendar.py::parse_ics` reads DTSTART/DTEND only, no
  RRULE expansion. Volunteers with weekly standing meetings on their calendar will only
  conflict on the *first* occurrence. Add `recurring-ical-events` (or equivalent) once a
  user reports the issue or the conflict view goes beyond ~30-day windows.
- Cross-timezone correctness. `services/calendar.py::_task_window` assumes naive task
  times are UTC. The volunteer-call use case is regional (NoVA), so a single TZ would be
  fine — store the project TZ in settings and apply it when building task windows.
- Multi-instance cache. `_cache` is process-local; a multi-replica Cloud Run deploy
  re-fetches per instance. Acceptable for current volume; revisit when bills show up.

## Additional tasks, need some design discussion

### Way to resend a request for a particular task, when someone becomes unavailable

Spec needed: re-notify only volunteers who didn't respond for *this* task (skipping
already-assigned and already-said-no), or re-blast the whole program? Most likely a
button on the assign view next to under-staffed tasks.

### Make color of buttons everywhere consistent.
    Buttns are blue or gray, seemingly unrelated to whetehr thhey are active.  Ideally the buttons should somehow express the workflow.  Maybe the volunteer call button should have create, assign, notify, reopen.  Lets plan and discuss this.

### People

- Import / export for users: bulk and per-user, after the source-of-truth
  volunteer adapter is decided
  (SharePoint, external DB, manual). The People editor at `/people/[id]` is the current entry point.
