"""Tests for the assignment-notice diff helper."""

from volunteer_call_api.services.roster_diff import diff_rosters


def task(assigned: list[str], team_lead: str | None = None) -> dict:
    return {"assigned": assigned, "team_lead": team_lead}


def test_first_send_treats_every_task_as_changed_with_no_removals() -> None:
    """The first Send Assignments click has no prior baseline to diff against.
    Pinning that every task in the current roster lands in tasks_changed —
    otherwise the first-send case would silently drop emails.
    """
    changed, removed = diff_rosters(None, {"t1": task(["a"]), "t2": task(["b", "c"])})
    assert changed == {"t1", "t2"}
    assert removed == {}


def test_no_changes_at_all_returns_empty_sets() -> None:
    # A re-Send when nothing has been edited shouldn't trigger any
    # emails. Pinning this catches a regression that always returns
    # tasks_changed=all on second-send.
    last = {"t1": task(["a", "b"]), "t2": task(["c"])}
    current = {"t1": task(["a", "b"]), "t2": task(["c"])}
    changed, removed = diff_rosters(last, current)
    assert changed == set()
    assert removed == {}


def test_addition_marks_task_changed_with_no_removals() -> None:
    last = {"t1": task(["a"])}
    current = {"t1": task(["a", "b"])}
    changed, removed = diff_rosters(last, current)
    assert changed == {"t1"}
    assert removed == {}


def test_removal_marks_task_changed_and_records_removed_volunteer() -> None:
    last = {"t1": task(["a", "b"])}
    current = {"t1": task(["a"])}
    changed, removed = diff_rosters(last, current)
    assert changed == {"t1"}
    assert removed == {"t1": {"b"}}


def test_swap_marks_task_changed_and_records_the_outgoing_volunteer() -> None:
    # Swapping a volunteer must record the outgoing person so they get a
    # removal email — that's the whole reason this helper exists vs. just
    # a roster comparison.
    last = {"t1": task(["a"])}
    current = {"t1": task(["b"])}
    changed, removed = diff_rosters(last, current)
    assert changed == {"t1"}
    assert removed == {"t1": {"a"}}


def test_team_lead_change_alone_marks_task_changed() -> None:
    # The team lead is part of "who needs to be notified". A team-lead
    # change with no roster change still triggers a re-send (the new
    # lead gets their roster email).
    last = {"t1": task(["a"], team_lead="lead-1")}
    current = {"t1": task(["a"], team_lead="lead-2")}
    changed, removed = diff_rosters(last, current)
    assert changed == {"t1"}
    # No volunteer removed — the team lead change isn't a removal event.
    assert removed == {}


def test_new_task_added_after_first_send_only_emails_the_new_task() -> None:
    last = {"t1": task(["a"])}
    current = {"t1": task(["a"]), "t2": task(["b"])}
    changed, removed = diff_rosters(last, current)
    assert changed == {"t2"}
    assert removed == {}


def test_task_deleted_after_first_send_records_all_its_assignees_as_removed() -> None:
    # A task that existed at last send but isn't in current means every
    # assignee at that task got dropped. Pin that the diff treats the
    # missing task as "everyone removed" — they all need a removal email.
    last = {"t1": task(["a"]), "t2": task(["b", "c"])}
    current = {"t1": task(["a"])}
    changed, removed = diff_rosters(last, current)
    assert changed == {"t2"}
    assert removed == {"t2": {"b", "c"}}


def test_mixed_changes_across_multiple_tasks() -> None:
    last = {
        "t1": task(["a"]),  # unchanged
        "t2": task(["b", "c"]),  # b removed
        "t3": task(["d"], team_lead="L1"),  # team lead changes
    }
    current = {
        "t1": task(["a"]),
        "t2": task(["c"]),
        "t3": task(["d"], team_lead="L2"),
        "t4": task(["e"]),  # newly added
    }
    changed, removed = diff_rosters(last, current)
    assert changed == {"t2", "t3", "t4"}
    assert removed == {"t2": {"b"}}
