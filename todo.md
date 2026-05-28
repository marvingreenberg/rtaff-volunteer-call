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

### [ ] feat/01-program-membership-filter

Backend filters the volunteer-call list by the caller's program
memberships when the caller is volunteer-only (no staff/team-leader
role). Staff still see every program.

- `routes/volunteer_calls.py::list_volunteer_calls` joins
  `Person.program_memberships` when the user is volunteer-only.
- `routes/volunteering.py::my_assignments` already scoped by person,
  no change.

### [ ] feat/02-pause-date-enforce

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

Follow-ups on the same branch:
- `feat/06b` — `calendar_kind` setting + provider-aware Add to Calendar.
- `feat/06c` — AvatarMenu redesign per the user's reference screenshot:
  email header line, icon+label rows with outline SVG icons,
  horizontal dividers grouping (Settings · Inbox) | (staff: People) |
  Logout. Display density relocates to `/settings` since the new menu
  shape doesn't have a home for the radio group. Inventory item
  removed — there's no `/inventory` route in this project.

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

### [/] feat/15-multiple-calendars

**Decision recorded**: store a list of `(provider, url, label)` per
person in a child table; conflict detection merges events from every
connected calendar (so personal + work meetings both block a task).

- New `person_calendars` child table: `id`, `person_id` FK,
  `calendar_url` (bearer-secret), `calendar_provider`, `label`
  (free-form, e.g. "Work"), `added_at`. Existing
  `person.calendar_url` / `calendar_provider` columns retire — there's
  no production data yet, so connected users will need to re-add.
- Backend: `GET/POST/DELETE /api/people/{id}/calendars` for list /
  add / remove. `connect_calendar` becomes append-only; the
  conflicts route iterates over all of the user's calendars and
  unions the events.
- Frontend: Settings page swaps the single `CalendarConnectPanel` for
  a list with an Add row. Each row shows label + provider + an
  "X" to remove.
- Conflict cache: keyed by `(person_id, list of urls, window)` so
  adding/removing a calendar invalidates correctly. Continue to use
  the existing per-URL fetcher under the hood.

### [ ] feat/16-people-pagination

`routes/people.py::list_people` silently truncates results at
`.limit(25)`. With 57 volunteers in the seed and 25 visible, an
admin clicking "Send invites" sees "Called: 57 notifications sent"
on a People page that only ever showed 21 of them — confusing
mismatch surfaced during the demo on 2026-05-28.

Compounding bug on the same page: the "25 people · 4 staff · 3
leaders · 21 volunteers" header is derived **client-side** off the
truncated list (`personList.filter(...).length`) so the per-role
counts never add up to the total, and they shift wildly as the role
filter changes (e.g. "Volunteer" filter → "25 people · 0 staff · 4
leaders · 25 volunteers").

**Decision recorded**: drop the per-role breakdown. One count per
query, labeled by the active filter — "people" when no role filter,
otherwise the pluralized role name ("staff", "team leaders",
"volunteers").

- Backend: pagination via `?start=N&count=M` (default `start=0`,
  `count=25`). Response shape: `{ items, total, start, count }`.
  `total` is a separate `SELECT COUNT(*)` against the same WHERE,
  not `len(items)`.
- Frontend `/people`:
  - Header reads "N people" / "N staff" / "N team leaders" /
    "N volunteers" depending on the active role filter.
  - Footer "showing N–M of TOTAL" with Previous / Next buttons.
  - Search input keeps working against the full table.
- Backend test: `total` reflects the filter (`role`, `program`,
  `search`, `active`) and is independent of `start` / `count`.

### [ ] feat/17-convert-remaining-native-selects

The Select.svelte component (feat/09) only got adopted in a few
spots; eight native `<select>`s remain that still pop the OS-native
option list. The global CSS rule restyles their trigger so they look
right at rest, but the dropdown surface is jarringly different from
the rest of the app. Convert all eight to `Select.svelte`.

Inventory:
- `routes/people/+page.svelte:218` — "All Roles" filter (the one
  flagged on 2026-05-28).
- `routes/people/[id]/+page.svelte:236, :242, :250` — staff editor:
  notification preference, detail level, subscription status.
- `routes/volunteer-calls/[id]/assign/+page.svelte:344` — Desired
  policy picker.
- `routes/volunteer-calls/[id]/assign/+page.svelte:443` — per-task
  team-lead override inside the assign view.
- `lib/components/TaskEntryForm.svelte:306` — City picker.
- `lib/components/TaskEntryForm.svelte:359` — Team-lead picker.

Notes:
- City + team-lead pickers have dynamic option lists — pass through
  `options={...}`.
- Empty-state options (e.g. `<option value="">City</option>`,
  `<option value={null}>Team lead (optional)</option>`) need a
  `placeholder` prop on `Select` so the empty/null sentinel renders
  consistently.
- Update the demo helpers (`pickComboboxByAriaLabel` already exists)
  for any new aria-label introduced by the conversion.

## Deferred — questions for the user

These need a decision before they can be executed unattended.

- **CSP headers.** Current frontend uses inline `<style>` blocks
  heavily. Two paths: (1) build-time CSS extraction (cleaner, larger
  refactor); (2) per-request nonces threaded through SvelteKit
  rendering (smaller, more runtime complexity). Which?
- **UI design review** — "prettier, Notion-style header backgrounds,
  consistent with rtaff.org." Too open-ended for unattended work.
  Want a concrete spec — mockups, color palette, components to touch?
- **Address autocomplete on TaskEntryForm.** Provider: Google Places
  (paid, polished), OpenStreetMap/Photon (free, NoVA coverage is
  fine), or a static dataset (RT-AFF's known client list)?
- **Cross-timezone correctness.** Project TZ should be
  `America/New_York`? Make it a settings value or hardcoded?
- **Multi-instance cache** for calendar conflicts. Deferred per
  current note; revisit when traffic warrants.
- **Resend for a particular task.** (Already deferred — spec needed.)
- **Gamification.** (Already deferred — design discussion.)
