"""Pure roster-diff helper for the assignment-notice pipeline.

Kept out of the notifications service so the diff logic can be unit-tested
without touching the DB or jinja. The shape mirrors what gets persisted
into VolunteerCall.last_sent_roster:

    {
        "<task_id>": {
            "assigned": ["<person_id>", ...],
            "team_lead": "<person_id>" | null,
            # detail fields (serialized scalars) used to detect edits that
            # affect every assignee, e.g.:
            "date": "2026-06-01" | null,
            "time_start": "09:00:00" | null,
            "time_end": ... ,
            "address": ..., "city": ...,
            "short_description": ..., "notes": ...,
            "volunteers_needed": 4, "skilled_needed": 0,
        },
        ...
    }
"""

from typing import NamedTuple, TypedDict


class TaskRoster(TypedDict, total=False):
    assigned: list[str]
    team_lead: str | None
    date: str | None
    time_start: str | None
    time_end: str | None
    address: str | None
    city: str | None
    short_description: str | None
    notes: str | None
    volunteers_needed: int
    skilled_needed: int


Roster = dict[str, TaskRoster]


# Maps a stored snapshot field to the logical "section" of the email it
# belongs to. Several raw fields collapse into one section (the time pair,
# the address/city pair, the two volunteer counts) so an "(Updated)" marker
# lands on a single line.
DETAIL_FIELD_SECTIONS: dict[str, str] = {
    "team_lead": "lead",
    "date": "date",
    "time_start": "time",
    "time_end": "time",
    "address": "location",
    "city": "location",
    "short_description": "description",
    "notes": "notes",
    "volunteers_needed": "needs",
    "skilled_needed": "needs",
}


class RosterDiff(NamedTuple):
    """Result of comparing the last-sent roster against the current one.

    tasks_changed: task_ids where anything (roster or details) differs. On
        the first send (last is None) every current task counts as changed.
    removed_by_task: per-task person_ids assigned at last send but not now.
    added_by_task: per-task person_ids assigned now but not at last send. On
        the first send every assignee counts as added so everyone is emailed.
    changed_fields_by_task: per-task set of *detail* sections that changed
        (e.g. {"time", "location", "lead"}). Roster add/remove is NOT a detail
        change — that's what added_by_task/removed_by_task are for. This lets
        the caller recognise a removal-only edit (removed non-empty while
        added and changed_fields are empty) and drives "(Updated)" markers.
    """

    tasks_changed: set[str]
    removed_by_task: dict[str, set[str]]
    added_by_task: dict[str, set[str]]
    changed_fields_by_task: dict[str, set[str]]


def _task_set(roster: Roster, task_id: str) -> set[str]:
    return set(roster.get(task_id, {}).get("assigned", []))


def _changed_sections(last: TaskRoster, current: TaskRoster) -> set[str]:
    sections: set[str] = set()
    for field, section in DETAIL_FIELD_SECTIONS.items():
        if last.get(field) != current.get(field):
            sections.add(section)
    return sections


def diff_rosters(last: Roster | None, current: Roster) -> RosterDiff:
    """Compute what changed since the last send. See RosterDiff for the shape."""
    if last is None:
        # First send: no baseline. Everyone is "added" so the caller emails
        # all assignees; markers are suppressed on the first send anyway, so
        # changed_fields stays empty.
        first_added = {tid: _task_set(current, tid) for tid in current if _task_set(current, tid)}
        return RosterDiff(set(current.keys()), {}, first_added, {})

    all_ids = set(current.keys()) | set(last.keys())
    changed: set[str] = set()
    removed: dict[str, set[str]] = {}
    added: dict[str, set[str]] = {}
    changed_fields: dict[str, set[str]] = {}
    for tid in all_ids:
        last_set = _task_set(last, tid)
        cur_set = _task_set(current, tid)
        sections = _changed_sections(last.get(tid, {}), current.get(tid, {}))
        removed_set = last_set - cur_set
        added_set = cur_set - last_set
        if last_set != cur_set or sections:
            changed.add(tid)
        if removed_set:
            removed[tid] = removed_set
        if added_set:
            added[tid] = added_set
        if sections:
            changed_fields[tid] = sections
    return RosterDiff(changed, removed, added, changed_fields)
