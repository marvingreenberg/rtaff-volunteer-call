"""Tests for the assignment-notice diff helper."""

from volunteer_call_api.services.roster_diff import diff_rosters


def task(
    assigned: list[str],
    team_lead: str | None = None,
    **details: object,
) -> dict:
    """Build a snapshot entry. Extra kwargs are detail fields (date, time_start,
    address, city, short_description, notes, volunteers_needed, skilled_needed)."""
    return {"assigned": assigned, "team_lead": team_lead, **details}


def test_first_send_treats_every_task_as_changed_with_no_removals() -> None:
    """The first Send Assignments click has no prior baseline to diff against.
    Every task in the current roster lands in tasks_changed, and every assignee
    counts as added so the first-send path emails everyone.
    """
    d = diff_rosters(None, {"t1": task(["a"]), "t2": task(["b", "c"])})
    assert d.tasks_changed == {"t1", "t2"}
    assert d.removed_by_task == {}
    assert d.added_by_task == {"t1": {"a"}, "t2": {"b", "c"}}


def test_no_changes_at_all_returns_empty_sets() -> None:
    # A re-Send when nothing has been edited shouldn't trigger any emails.
    last = {"t1": task(["a", "b"]), "t2": task(["c"])}
    current = {"t1": task(["a", "b"]), "t2": task(["c"])}
    d = diff_rosters(last, current)
    assert d.tasks_changed == set()
    assert d.removed_by_task == {}
    assert d.added_by_task == {}
    assert d.changed_fields_by_task == {}


def test_addition_records_the_added_volunteer_and_no_detail_change() -> None:
    last = {"t1": task(["a"])}
    current = {"t1": task(["a", "b"])}
    d = diff_rosters(last, current)
    assert d.tasks_changed == {"t1"}
    assert d.removed_by_task == {}
    assert d.added_by_task == {"t1": {"b"}}
    # A pure add is not a detail-field change.
    assert d.changed_fields_by_task == {}


def test_removal_only_records_removed_and_no_added_or_detail_change() -> None:
    # The removal-only case: someone dropped, nothing else. added_by_task and
    # changed_fields_by_task must both be empty so the caller can recognise it
    # and email *only* the removed volunteer.
    last = {"t1": task(["a", "b"])}
    current = {"t1": task(["a"])}
    d = diff_rosters(last, current)
    assert d.tasks_changed == {"t1"}
    assert d.removed_by_task == {"t1": {"b"}}
    assert d.added_by_task == {}
    assert d.changed_fields_by_task == {}


def test_swap_records_both_added_and_removed() -> None:
    last = {"t1": task(["a"])}
    current = {"t1": task(["b"])}
    d = diff_rosters(last, current)
    assert d.tasks_changed == {"t1"}
    assert d.removed_by_task == {"t1": {"a"}}
    assert d.added_by_task == {"t1": {"b"}}
    assert d.changed_fields_by_task == {}


def test_team_lead_change_alone_is_a_lead_detail_change() -> None:
    last = {"t1": task(["a"], team_lead="lead-1")}
    current = {"t1": task(["a"], team_lead="lead-2")}
    d = diff_rosters(last, current)
    assert d.tasks_changed == {"t1"}
    assert d.removed_by_task == {}
    assert d.added_by_task == {}
    assert d.changed_fields_by_task == {"t1": {"lead"}}


def test_time_change_is_a_time_detail_change() -> None:
    last = {"t1": task(["a"], time_start="09:00:00")}
    current = {"t1": task(["a"], time_start="10:00:00")}
    d = diff_rosters(last, current)
    assert d.tasks_changed == {"t1"}
    assert d.changed_fields_by_task == {"t1": {"time"}}
    assert d.added_by_task == {}
    assert d.removed_by_task == {}


def test_address_and_city_collapse_into_one_location_section() -> None:
    last = {"t1": task(["a"], address="1 Main", city="Arlington")}
    current = {"t1": task(["a"], address="2 Oak", city="Arlington")}
    d = diff_rosters(last, current)
    assert d.changed_fields_by_task == {"t1": {"location"}}


def test_multiple_detail_fields_yield_multiple_sections() -> None:
    last = {"t1": task(["a"], date="2026-06-01", notes="bring tools")}
    current = {"t1": task(["a"], date="2026-06-02", notes="bring gloves")}
    d = diff_rosters(last, current)
    assert d.changed_fields_by_task == {"t1": {"date", "notes"}}


def test_new_task_added_after_first_send_only_emails_the_new_task() -> None:
    last = {"t1": task(["a"])}
    current = {"t1": task(["a"]), "t2": task(["b"])}
    d = diff_rosters(last, current)
    assert d.tasks_changed == {"t2"}
    assert d.added_by_task == {"t2": {"b"}}
    assert d.removed_by_task == {}


def test_task_deleted_after_first_send_records_all_its_assignees_as_removed() -> None:
    last = {"t1": task(["a"]), "t2": task(["b", "c"])}
    current = {"t1": task(["a"])}
    d = diff_rosters(last, current)
    assert d.tasks_changed == {"t2"}
    assert d.removed_by_task == {"t2": {"b", "c"}}
    assert d.added_by_task == {}


def test_mixed_changes_across_multiple_tasks() -> None:
    last = {
        "t1": task(["a"]),  # unchanged
        "t2": task(["b", "c"]),  # b removed (removal-only)
        "t3": task(["d"], team_lead="L1"),  # team lead changes
    }
    current = {
        "t1": task(["a"]),
        "t2": task(["c"]),
        "t3": task(["d"], team_lead="L2"),
        "t4": task(["e"]),  # newly added
    }
    d = diff_rosters(last, current)
    assert d.tasks_changed == {"t2", "t3", "t4"}
    assert d.removed_by_task == {"t2": {"b"}}
    assert d.added_by_task == {"t4": {"e"}}
    assert d.changed_fields_by_task == {"t3": {"lead"}}
