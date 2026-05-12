"""Pure roster-diff helper for the assignment-notice pipeline.

Kept out of the notifications service so the diff logic can be unit-tested
without touching the DB or jinja. The shape mirrors what gets persisted
into VolunteerCall.last_sent_roster:

    {
        "<task_id>": {
            "assigned": ["<person_id>", ...],
            "team_lead": "<person_id>" | null
        },
        ...
    }
"""

from typing import TypedDict


class TaskRoster(TypedDict, total=False):
    assigned: list[str]
    team_lead: str | None


Roster = dict[str, TaskRoster]


def _task_set(roster: Roster, task_id: str) -> set[str]:
    return set(roster.get(task_id, {}).get("assigned", []))


def _task_lead(roster: Roster, task_id: str) -> str | None:
    return roster.get(task_id, {}).get("team_lead")


def diff_rosters(
    last: Roster | None,
    current: Roster,
) -> tuple[set[str], dict[str, set[str]]]:
    """Compute which tasks changed since the last send and who was dropped.

    Returns:
        tasks_changed: set of task_ids where either the assigned-set or
            the team_lead differs between `last` and `current`. On the
            first send (last is None), every task in `current` counts as
            changed so first-send emails go to everyone.
        removed_by_task: per-task set of person_ids who were assigned at
            last send but aren't now. Used to fire removal emails.
            Empty on the first send.
    """
    if last is None:
        return set(current.keys()), {}

    all_ids = set(current.keys()) | set(last.keys())
    changed: set[str] = set()
    removed: dict[str, set[str]] = {}
    for tid in all_ids:
        last_set = _task_set(last, tid)
        cur_set = _task_set(current, tid)
        if last_set != cur_set or _task_lead(last, tid) != _task_lead(current, tid):
            changed.add(tid)
            removed_set = last_set - cur_set
            if removed_set:
                removed[tid] = removed_set
    return changed, removed
