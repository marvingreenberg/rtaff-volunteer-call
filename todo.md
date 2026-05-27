# todo

Branch chain plan. Each item below is a feature branch
`feat/NN-short-desc`, stacked off the previous one. Tick `[/]` as
each branch lands. Deferred items (bottom) need a user decision
before they can be executed unattended.

## Chain — application work

### [/] Housekeeping — clean up stale feature branches

Deleted `call-ux-phase1`, `feat/email-redesign`,
`feat/programs-skills-calendar`, `lotsofchanges`, `team-lead-dropdown`
— all confirmed integrated via `git cherry main <branch>` (0 or 1
patch-id-unique commits, and the "unique" commits had subject/date
matches with the rebased main commits).

### [/] feat/01-program-membership-filter

Backend filters the volunteer-call list by the caller's program
memberships when the caller is volunteer-only (no staff/team-leader
role). Staff still see every program.

- `routes/volunteer_calls.py::list_volunteer_calls` joins
  `Person.program_memberships` when the user is volunteer-only.
- `routes/volunteering.py::my_assignments` already scoped by person,
  no change.

### [/] feat/02-pause-date-enforce

`routes/volunteer_availability.py::submit_availability` rejects the
POST when `today ∈ [pause_start, pause_end]` for the calling person.
Reuses the pause check already in `services/notifications.is_subscribed`.

### [ ] feat/03-referrer-policy

`main.py` adds a middleware emitting `Referrer-Policy:
no-referrer-when-downgrade` on every response. Keeps URL tokens from
leaking via Referer while the session-cookie migration is finishing.

### [ ] feat/04-task-assignees-display

Show assigned volunteers on each task row in the call detail page.
Task rows already have an `assignments` selectinload via
`/jobs`/`/assignment-overview`; reuse those payloads. Display as
initials chips, with team-lead distinguished.

### [ ] feat/05-add-to-calendar-deeplinks

Replace the `.ics` download path on `/volunteering`'s My Assignments
with a deeplink to **Google Calendar's "render event" URL** (the
most common case). Fall back to the existing `.ics` download for
users who prefer it.

**Decision recorded**: Google Calendar deeplink is the default. Apple
Calendar requires the `.ics` route (no equivalent deeplink). Outlook
has its own URL builder; do not add yet — wait for a user to ask.

### [ ] feat/06-avatar-settings-move

Move notification preference (channel + detail), **pause** (instead
of full subscription_status), and calendar connection into the
Avatar menu (gear icon). Retain a one-line hint on `/volunteering`:
"See user settings to connect your calendar to detect conflicts."

### [ ] feat/07-recurring-events

Install `recurring-ical-events`. In
`services/calendar.py::parse_ics`, expand RRULE-bearing VEVENTs
across the conflict window so weekly standing meetings register on
every occurrence, not just the first.

### [ ] feat/08-sms-stubs

`services/sms.py` exists but is a no-op. Wire it into
`deliver_notification` for `NotificationPreference.SMS` / `BOTH`
paths so the code path executes end-to-end.

**Decision recorded**: stub provider logs to stdout via
`logger.info("[SMS stub] to=%s body=%s", ...)` — no Twilio
integration yet, but the call site is real so it's easy to drop a
provider in later.

### [ ] feat/09-svelte-pulldowns

Replace native `<select>` with a styled Svelte component for visual
consistency.

**Decision recorded**: tiny custom component (`SelectButton.svelte`)
— no new dependency. Keeps keyboard and ARIA semantics by wrapping a
real `<select>` for accessibility, with a styled overlay for the
visible UI.

### [ ] feat/10-csrf-protection

Double-submit-cookie CSRF: backend sets a non-HttpOnly `csrf` cookie
on `/auth/verify` and `/auth/me`. A middleware rejects
POST/PUT/PATCH/DELETE on authenticated routes when the
`X-CSRF-Token` header doesn't equal the cookie. Frontend `client.ts`
reads the cookie and sends the header on writes.

### [ ] feat/11-backend-test-fixtures

`backend/tests/conftest.py` gains a Postgres test-DB fixture (via a
`docker compose` Postgres started for the test session, mirroring
`scripts/dev-db.sh`). Tests from the original list land:

- `send-invites` transitions OPEN → WAITING and rejects ASSIGNED / ARCHIVED.
- `send-invites` recipient query filters by `call.program` membership.
- `POST /send-assignment-notices` requires ASSIGNED, returns counts.
- `assignment-overview` includes `available_volunteers` filtered correctly.
- `GET /people/{id}` never serializes `calendar_url` even after `PUT /calendar`.
- `GET /volunteer-calls/{id}/calendar/conflicts` enforces self-only access.
- `DELETE /volunteer-calls/{id}` cascades through tasks, availabilities, assignments.
- `PUT /people/{id}/calendar` returns 422 on unreachable / non-iCal URLs.

### [ ] feat/12-e2e-make-target

**Decision recorded**: `demo.spec.ts` stays manual-only for video
recording (AUTODEMO=0 / AUTODEMO=1 from `make demo`). Add
`make test-e2e` that runs the spec headless under `AUTODEMO=1`
purely as a smoke test — fails CI if a refactor breaks the demo
path.

## Chain — deployment / operations (do last)

### [ ] feat/13-scheduled-warmer

Cloud Scheduler cron `*/5 9-19 * * 5-0` hits `/health`. Frontend
heartbeat every ~4 min while a session is active. Animated
"Loading…" on first hit to absorb cold starts outside the window.
Estimated $0/mo within Cloud Run free tier (Neon DB).

### [ ] feat/14-github-actions

`ci.yml` (backend + frontend lint/test, type-generation
verification), `deploy.yml` (Docker build to GHCR + GCP Artifact
Registry, Cloud Run deploy on `v*` tags), Dependabot config for npm
+ uv lockfiles.

## Deferred — questions for the user

These need a decision before they can be executed unattended.

- **CSP headers.** Current frontend uses inline `<style>` blocks
  heavily. Two paths: (1) build-time CSS extraction (cleaner, larger
  refactor); (2) per-request nonces threaded through SvelteKit
  rendering (smaller, more runtime complexity). Which?
- **UI design review** — "prettier, Notion-style header backgrounds,
  consistent with rtaff.org." Too open-ended for unattended work.
  Want a concrete spec — mockups, color palette, components to touch?
- **Avatar menu "more Material Design."** Specifically: material-symbols
  icons? Ripple effect? Card elevation? List preferred targets.
- **Address autocomplete on TaskEntryForm.** Provider: Google Places
  (paid, polished), OpenStreetMap/Photon (free, NoVA coverage is
  fine), or a static dataset (RT-AFF's known client list)?
- **Cross-timezone correctness.** Project TZ should be
  `America/New_York`? Make it a settings value or hardcoded?
- **Multi-instance cache** for calendar conflicts. Deferred per
  current note; revisit when traffic warrants.
- **Multiple calendar connections per person.** UX: pick one as
  primary or merge events from all? Data model: array of
  `(provider, url)` tuples on `Person` or a child table?
- **Resend for a particular task.** (Already deferred — spec needed.)
- **Gamification.** (Already deferred — design discussion.)
