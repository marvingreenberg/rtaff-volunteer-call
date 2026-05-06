# todo

Let's do some usability items.

## Variations on call "kind"
There are four kinds of calls initially supported: RTX, AC Rescue, Ramp, and Chairlift.

RTX is the only call that supports multiple tasks.  All the others are single task, single date.
When creating a call, a radio button group is presented with the 4 possibilities, one must be chosen to create the call.
The other permutation is that now each Volunteer has additional properties, skill:plumbing, skill:electrical, skill:carpentry,
skill:hvac.  And program:rtx, program:acr, program:ramp, program:chairlift

Only the volunteers for a given program get notifications for a given call.

### Design questions before starting

**Schema impact (current model can't support this without changes):**

- `Person.skill_category` is a single enum today (`skilled | unskilled | unknown`). Per-skill tags
  (plumbing/electrical/carpentry/hvac) need many-to-many — either a `Skill` enum + `PersonSkill`
  join, or a `skills: list[Skill]` array column.
- No `program` concept exists at all. New tables: `Program` (or enum), `PersonProgram` join,
  and either `VolunteerCall.program_id` FK or a call-kind enum.
- `Task.skilled_needed` is currently just an int count, not linked to a specific skill. Open
  question: do tasks need per-skill requirements ("1 plumber, 1 electrician"), or is "N skilled
  people of any kind" sufficient?

**Visibility-filtering touchpoints that all need updating once programs land:**

- `routes/volunteer_calls.py::list_volunteer_calls` and `routes/volunteering.py` open-calls list —
  filter by `volunteer.programs ∋ call.program`.
- `routes/volunteer_calls.py::send_invites` recipient query (currently `role == VOLUNTEER and active`) —
  add program membership.
- `routes/volunteer_calls.py::list_jobs` and the assign-view available-volunteers logic —
  same filter.
- Staff/team-leader bypass: admins likely see all calls regardless of program membership.

**UI implications of single-task-only kinds (AC Rescue / Ramp / Chairlift):**

- The multi-task list + always-visible TaskEntryForm pattern needs to collapse to one inline task
  with no add-more affordance, or the single task is auto-created when the call is created and the
  user just edits it inline.
- "Add Task" is the wrong gesture in single-task mode.

**Rollout questions:**

- Existing volunteers have no programs assigned. Default to all programs, none, or admin-assigned
  per person?
- If a call's `program` is changed after invites have gone out, what happens to existing
  availabilities and assignments?



## User calendar.

Users can connect their google, yahoo, apple calendar to the app.  For each call, it will import relevant dates
and somehow present conflicts to user when volunteering.  (This may require a deployed app with an oauth grant?)


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
  - `PUT /volunteer-calls/{id}` no longer fires notifications on close.
  - `POST /send-assignment-notices` requires Closed status and returns counts.
  - `assignment-overview` includes `available_volunteers` filtered correctly.

### Task / call UI follow-ups

- Delete-task affordance on `TaskRow` (deferred from the task-entry redesign).
- Address autocomplete on `TaskEntryForm` (city is hardcoded; address is plain text pending a source).
- Reintroduce a `notes` affordance for tasks once there's a place to display them
  (currently captured by the API but not surfaced anywhere).
- Gray-default visual for time/number inputs (Svelte placeholder doesn't reach native inputs).
- Backend PUT `update_task` skips `None` values (`routes/volunteer_calls.py:408-411`), so
  clearing nullable fields back to null is impossible; revisit when notes/team_lead become editable.
- Under-/over-assignment policy: the assign view doesn't cap at `volunteers_needed`, and
  Send Assignment Notices doesn't gate on every task being full. Decide intended behaviour.
- Admin-on-behalf-of-volunteer availability entry was dropped with the `/availability` page;
  if needed, add a small affordance inside the assign view (per-task "Add availability" combobox).
- Optimistic UI on the assign page (currently refetches `assignment-overview` after each
  click — fine at this scale but will feel sluggish at higher task/volunteer counts).

### People

- Import / export for users: bulk and per-user, after the source-of-truth volunteer adapter is decided
  (SharePoint, external DB, manual). The People editor at `/people/[id]` is the current entry point.

### Cleanup

- `volunteerCalls.assignmentSummary` API method and `AssignmentSummaryItem` type are now unused
  (the read-only dashboard was replaced). Remove from `frontend/src/lib/api/client.ts`,
  `types.ts`, and the corresponding backend route + schema if nothing else depends on them.
