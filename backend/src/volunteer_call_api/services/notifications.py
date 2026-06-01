"""Notification creation and delivery service."""

import datetime
import logging
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from volunteer_call_api.config import settings
from volunteer_call_api.models.person import (
    NotificationDetailLevel,
    NotificationPreference,
    Person,
    SubscriptionStatus,
)
from volunteer_call_api.models.team_assignment import TeamAssignment
from volunteer_call_api.models.volunteer_availability import VolunteerAvailability
from volunteer_call_api.models.volunteer_call import Task, VolunteerCall
from volunteer_call_api.services.email import send_email
from volunteer_call_api.services.email_render import jinja_env as _jinja_env
from volunteer_call_api.services.roster_diff import Roster, diff_rosters
from volunteer_call_api.services.sms import send_sms
from volunteer_call_api.services.tokens import issue_invite_token, issue_login_token

logger = logging.getLogger(__name__)


# CIDs of inline images referenced by email_base.html.
EMAIL_INLINE_IMAGES = ["rtaff-logo", "tools-image"]


def is_subscribed(person: Person) -> bool:
    """Check if a person should receive notifications right now."""
    if person.subscription_status == SubscriptionStatus.UNSUBSCRIBED:
        return False
    if person.subscription_status == SubscriptionStatus.PAUSED:
        today = datetime.date.today()
        if person.pause_start and person.pause_end:
            if person.pause_start <= today <= person.pause_end:
                return False
    return True


def deliver_notification(
    person: Person,
    subject: str,
    full_body: str,
    summary_body: str,
    link: str | None = None,
    inline_images: list[str] | None = None,
) -> bool:
    """Deliver a notification via the person's preferred channel and detail level.

    Caller is responsible for checking is_subscribed() before calling.
    Returns True if notification was delivered via any channel.
    """
    is_summary = person.notification_detail_level == NotificationDetailLevel.SUMMARY
    body = summary_body if is_summary else full_body
    pref = person.notification_preference
    delivered = False

    if pref in (NotificationPreference.EMAIL, NotificationPreference.BOTH):
        if person.email:
            unsubscribe_url = (
                f"{settings.app_base_url}/unsubscribe?token={issue_login_token(person.id)}"
            )
            send_email(
                to=person.email,
                subject=subject,
                html_body=body,
                headers={"List-Unsubscribe": f"<{unsubscribe_url}>"},
                inline_images=inline_images if not is_summary else None,
            )
            delivered = True

    if pref in (NotificationPreference.SMS, NotificationPreference.BOTH):
        if person.phone:
            sms_body = summary_body
            if link:
                sms_body += f"\n{settings.app_base_url}{link}"
            send_sms(to=person.phone, body=sms_body)
            delivered = True

    return delivered


def _format_date(d: datetime.date | None) -> str:
    return d.strftime("%A, %B %-d") if d else "Date TBD"


def _format_time_range(start: datetime.time | None, end: datetime.time | None) -> str | None:
    if not start and not end:
        return None

    def fmt(t: datetime.time) -> str:
        # Mac/Linux %-I; on systems without it %I would zero-pad.
        return t.strftime("%-I:%M %p").lstrip("0")

    if start and end:
        return f"{fmt(start)} – {fmt(end)}"
    return fmt(start or end)  # type: ignore[arg-type]


def _full_address(task: Task) -> str | None:
    parts = [p for p in (task.address, task.city) if p]
    if not parts:
        return None
    if task.address and task.city:
        return f"{task.address}\n{task.city}"
    return parts[0]


def _team_lead_block(task: Task) -> dict[str, str | None] | None:
    lead = task.team_lead
    if lead is None:
        return None
    return {
        "name": f"{lead.first_name} {lead.last_name}".strip(),
        "phone": lead.phone,
        "email": lead.email,
    }


def task_view(
    task: Task,
    *,
    include_full_details: bool,
    roster: list[str] | None = None,
    updated_sections: set[str] | None = None,
) -> dict[str, Any]:
    """Render-friendly task dict shared by call-invite and assignment templates.

    `roster` is the list of teammate names shown in the volunteer's email so
    people know who they're working with. `updated_sections` flags which
    sections changed since the last send (drives the "(Updated)" markers); it
    is left empty on first sends.
    """
    view: dict[str, Any] = {
        "date_label": _format_date(task.date),
        "short_description": task.short_description,
        "city": task.city,
        "roster": roster,
        "updated_sections": sorted(updated_sections) if updated_sections else [],
    }
    if include_full_details:
        view.update(
            {
                "time_label": _format_time_range(task.time_start, task.time_end),
                "full_address": _full_address(task),
                "team_lead": _team_lead_block(task),
                "notes": task.notes,
            }
        )
    return view


def task_detail_fields(task: Task) -> dict[str, Any]:
    """Serialized scalar detail fields stored in the roster snapshot so the
    diff can tell *which* field changed between sends. Dates/times are
    isoformatted so the JSON snapshot round-trips identically."""
    return {
        "date": task.date.isoformat() if task.date else None,
        "time_start": task.time_start.isoformat() if task.time_start else None,
        "time_end": task.time_end.isoformat() if task.time_end else None,
        "address": task.address,
        "city": task.city,
        "short_description": task.short_description,
        "notes": task.notes,
        "volunteers_needed": task.volunteers_needed,
        "skilled_needed": task.skilled_needed,
    }


async def generate_call_notifications(call_id: str, db: AsyncSession) -> tuple[int, int, int, int]:
    """Send assignment / thank-you / removal / team-lead emails.

    Behavior depends on whether this is the first Send for the call
    (`call.last_sent_roster` is null) or a subsequent re-send.

    First send:
      - Every current assignee gets a fresh volunteer_assignment email.
      - Every task with a team_lead gets a team_lead_roster email.
      - Every volunteer with availability but no assignment gets a thanks email.

    Re-send (last_sent_roster set):
      - Per-task diff against the snapshot. For each task whose roster or
        team_lead differs:
          - All CURRENT assignees of that task get an "updated" email.
          - All previously-assigned-but-now-removed volunteers get a
            removal email.
          - The current team_lead (if any) gets a fresh roster email.
      - Thanks emails do NOT re-fire on subsequent sends (we have no
        per-person "thanked at" tracking).

    Stamps `call.last_sent_roster` and `call.assignments_sent_at` on
    success.

    Returns (assignment_emails, thanks_emails, team_lead_emails, removal_emails).
    """
    tasks_q = (
        select(Task)
        .where(Task.volunteer_call_id == call_id)
        .options(
            selectinload(Task.team_lead),
            selectinload(Task.assignments).selectinload(TeamAssignment.person),
        )
    )
    tasks_result = await db.execute(tasks_q)
    # Outbound emails list tasks chronologically (matches the in-app views).
    # Python-side so SQLite tests sort identically to Postgres prod.
    tasks = sorted(
        tasks_result.scalars().all(),
        key=lambda t: (
            t.date is None,
            t.date or datetime.date.max,
            t.time_start or datetime.time.max,
            t.created_at,
        ),
    )
    tasks_by_id = {t.id: t for t in tasks}

    call_result = await db.execute(select(VolunteerCall).where(VolunteerCall.id == call_id))
    call = call_result.scalar_one()

    avail_result = await db.execute(
        select(VolunteerAvailability)
        .options(selectinload(VolunteerAvailability.person))
        .where(VolunteerAvailability.volunteer_call_id == call_id)
    )
    availabilities = list(avail_result.scalars().all())

    # Build current_roster in the same shape as last_sent_roster so the
    # diff helper has a like-for-like comparison.
    current_roster: dict[str, dict[str, object]] = {
        t.id: {
            "assigned": sorted(a.person_id for a in t.assignments),
            "team_lead": t.team_lead_id,
            **task_detail_fields(t),
        }
        for t in tasks
    }

    # Index every Person we might email by id, including assignees that
    # have been removed since last send (they aren't in `tasks` anymore;
    # fetch them by id below).
    people_by_id: dict[str, Person] = {}
    for t in tasks:
        for a in t.assignments:
            people_by_id[a.person_id] = a.person
        if t.team_lead is not None:
            people_by_id[t.team_lead.id] = t.team_lead
    for av in availabilities:
        people_by_id[av.person_id] = av.person

    is_first_send = call.last_sent_roster is None
    last_roster: Roster | None = (
        cast(Roster, call.last_sent_roster) if call.last_sent_roster is not None else None
    )
    diff = diff_rosters(last_roster, cast(Roster, current_roster))
    tasks_changed = diff.tasks_changed
    removed_by_task = diff.removed_by_task
    added_by_task = diff.added_by_task
    changed_fields_by_task = diff.changed_fields_by_task

    def updated_sections_for(task_id: str) -> set[str]:
        """Sections to flag "(Updated)" in a volunteer's email. Empty on the
        first send (nothing to mark)."""
        if is_first_send:
            return set()
        sections = set(changed_fields_by_task.get(task_id, set()))
        if added_by_task.get(task_id):
            sections.add("team")
        return sections

    # Hydrate any previously-assigned-but-now-removed Person rows that
    # aren't already in people_by_id (they were dropped from team_assignments
    # so the tasks/assignments eager-load won't see them).
    missing_person_ids: set[str] = set()
    for removed_set in removed_by_task.values():
        for pid in removed_set:
            if pid not in people_by_id:
                missing_person_ids.add(pid)
    if missing_person_ids:
        extra = await db.execute(select(Person).where(Person.id.in_(missing_person_ids)))
        for p in extra.scalars().all():
            people_by_id[p.id] = p

    assignment_template = _jinja_env.get_template("volunteer_assignment.html")
    removal_template = _jinja_env.get_template("volunteer_assignment_removed.html")
    thanks_template = _jinja_env.get_template("volunteer_thanks.html")
    team_lead_template = _jinja_env.get_template("team_lead_roster.html")

    assignment_emails = 0
    thanks_emails = 0
    team_lead_emails = 0
    removal_emails = 0

    def volunteering_url_for(person: Person) -> str:
        token = issue_invite_token(person.id, call.id)
        return f"{settings.app_base_url}/volunteering?token={token}"

    def volunteering_link_for(person: Person) -> str:
        token = issue_invite_token(person.id, call.id)
        return f"/volunteering?token={token}"

    # Group changed-task ids by recipient: who needs an assignment/update
    # email, and what list of tasks goes in that email.
    person_to_changed_tasks: dict[str, list[Task]] = {}
    for tid in tasks_changed:
        changed_task = tasks_by_id.get(tid)
        if changed_task is None:
            continue  # task was deleted post-last-send; no current-state email
        # Email all current assignees only when something additive happened:
        # a volunteer was added, or a detail field changed. A removal-only edit
        # notifies just the removed volunteer (handled below), not teammates.
        if not (added_by_task.get(tid) or changed_fields_by_task.get(tid)):
            continue
        for a in changed_task.assignments:
            person_to_changed_tasks.setdefault(a.person_id, []).append(changed_task)

    # Group removed assignments by person → list of (now-deleted-or-different) tasks.
    person_to_removed_tasks: dict[str, list[Task | None]] = {}
    for tid, removed_set in removed_by_task.items():
        removed_task = tasks_by_id.get(tid)  # None if the task was deleted entirely
        for pid in removed_set:
            person_to_removed_tasks.setdefault(pid, []).append(removed_task)

    # --- Assignment / update emails ---
    for pid, changed_tasks in person_to_changed_tasks.items():
        person = people_by_id.get(pid)
        if person is None or not is_subscribed(person):
            continue
        task_views = [
            task_view(
                t,
                include_full_details=True,
                roster=[f"{a.person.first_name} {a.person.last_name}" for a in t.assignments],
                updated_sections=updated_sections_for(t.id),
            )
            for t in changed_tasks
        ]
        subject = f"Your assignments for {call.title}"
        full_body = assignment_template.render(
            subject=subject,
            title=call.title,
            subtitle=(
                f"You're confirmed for {len(changed_tasks)} "
                f"task{'s' if len(changed_tasks) > 1 else ''}"
            ),
            first_name=person.first_name,
            tasks=task_views,
            volunteering_url=volunteering_url_for(person),
            is_update=not is_first_send,
        )
        summary_body = (
            "Updated: " if not is_first_send else ""
        ) + f"You're assigned to {len(changed_tasks)} task(s) for {call.title}."
        if deliver_notification(
            person=person,
            subject=subject,
            full_body=full_body,
            summary_body=summary_body,
            link=volunteering_link_for(person),
            inline_images=EMAIL_INLINE_IMAGES,
        ):
            assignment_emails += 1

    # --- Removal emails ---
    for pid, removed_tasks in person_to_removed_tasks.items():
        person = people_by_id.get(pid)
        if person is None or not is_subscribed(person):
            continue
        # For tasks that still exist, include their full label; for
        # deleted tasks (None) skip and just note the count.
        removed_task_views = [
            task_view(t, include_full_details=False) for t in removed_tasks if t is not None
        ]
        if not removed_task_views:
            # Task was deleted entirely and we lack title context; render
            # a minimal placeholder so the email still reads sensibly.
            removed_task_views = [
                {"date_label": "(task removed)", "short_description": "", "city": None}
            ]
        subject = f"Assignment update for {call.title}"
        full_body = removal_template.render(
            subject=subject,
            title=call.title,
            subtitle="Assignment changed",
            first_name=person.first_name,
            call_title=call.title,
            removed_tasks=removed_task_views,
            volunteering_url=volunteering_url_for(person),
        )
        summary_body = (
            f"Assignment changed for {call.title}: you're no longer on the team for "
            f"{len(removed_task_views)} task(s)."
        )
        if deliver_notification(
            person=person,
            subject=subject,
            full_body=full_body,
            summary_body=summary_body,
            link=volunteering_link_for(person),
            inline_images=EMAIL_INLINE_IMAGES,
        ):
            removal_emails += 1

    # --- Team-lead roster emails (one per changed task with a lead set) ---
    for tid in tasks_changed:
        lead_task = tasks_by_id.get(tid)
        if lead_task is None or lead_task.team_lead is None:
            continue
        lead = lead_task.team_lead
        if not is_subscribed(lead):
            continue
        # Mark who joined / left since the last send so the lead sees roster
        # churn at a glance. Suppressed on the first send (everything would
        # otherwise read as "(added)").
        added_ids = set() if is_first_send else added_by_task.get(tid, set())
        removed_ids = set() if is_first_send else removed_by_task.get(tid, set())
        roster = [
            {
                "name": f"{a.person.first_name} {a.person.last_name}",
                "phone": a.person.phone,
                "email": a.person.email,
                "skills": list(a.person.skills),
                "status": "added" if a.person_id in added_ids else None,
            }
            for a in lead_task.assignments
        ]
        for pid in removed_ids:
            dropped = people_by_id.get(pid)
            if dropped is None:
                continue
            roster.append(
                {
                    "name": f"{dropped.first_name} {dropped.last_name}",
                    "phone": dropped.phone,
                    "email": dropped.email,
                    "skills": list(dropped.skills),
                    "status": "removed",
                }
            )
        subject = f"Your team for {call.title} — {lead_task.short_description}"
        full_body = team_lead_template.render(
            subject=subject,
            title=call.title,
            subtitle=lead_task.short_description,
            first_name=lead.first_name,
            task=task_view(lead_task, include_full_details=True),
            roster=roster,
            volunteering_url=volunteering_url_for(lead),
        )
        summary_body = (
            f"Team for {call.title} — {lead_task.short_description}: "
            f"{len(roster)} volunteer(s)."
        )
        if deliver_notification(
            person=lead,
            subject=subject,
            full_body=full_body,
            summary_body=summary_body,
            link=volunteering_link_for(lead),
            inline_images=EMAIL_INLINE_IMAGES,
        ):
            team_lead_emails += 1

    # --- Thanks emails: only on first send ---
    if is_first_send:
        assigned_ids = {a.person_id for t in tasks for a in t.assignments}
        avail_people: dict[str, Person] = {a.person_id: a.person for a in availabilities}
        for person_id in set(avail_people.keys()) - assigned_ids:
            person = avail_people[person_id]
            if not is_subscribed(person):
                continue
            subject = f"Thank you for volunteering for {call.title}"
            full_body = thanks_template.render(
                subject=subject,
                title=f"Thanks, {person.first_name}!",
                subtitle=None,
                first_name=person.first_name,
                call_title=call.title,
                volunteering_url=volunteering_url_for(person),
            )
            summary_body = (
                f"Thanks for volunteering for {call.title} — all teams filled this round."
            )
            if deliver_notification(
                person=person,
                subject=subject,
                full_body=full_body,
                summary_body=summary_body,
                link=volunteering_link_for(person),
                inline_images=EMAIL_INLINE_IMAGES,
            ):
                thanks_emails += 1

    # Snapshot the current roster for next send's diff.
    call.last_sent_roster = current_roster  # type: ignore[assignment]

    return assignment_emails, thanks_emails, team_lead_emails, removal_emails


def drop_from_roster_snapshot(call: VolunteerCall, task_id: str, person_id: str) -> None:
    """Remove a person from a task's assigned list in the persisted snapshot.

    Used when a volunteer self-declines: their removal is communicated by the
    immediate decline notice, so trimming the snapshot keeps the next staff
    "Send Changed Assignments" diff from re-firing a removal email at them.
    Reassigns the column to a fresh dict so SQLAlchemy detects the JSON change.
    """
    if not call.last_sent_roster:
        return
    roster = cast(Roster, call.last_sent_roster)
    if task_id not in roster:
        return
    entry: dict[str, Any] = dict(roster[task_id])
    assigned = list(entry.get("assigned") or [])
    if person_id not in assigned:
        return
    entry["assigned"] = [p for p in assigned if p != person_id]
    updated: dict[str, Any] = {**roster, task_id: entry}
    # The model annotates this column as dict[str, list[str]] but the real
    # shape is the nested Roster; cast to the declared type for the assignment.
    call.last_sent_roster = cast("dict[str, list[str]]", updated)


async def notify_decline(
    call_id: str,
    task_id: str,
    volunteer_id: str,
    message: str | None,
    db: AsyncSession,
) -> int:
    """Email the team lead and call admin that a volunteer has declined, with
    the updated roster and the volunteer's note, and send the volunteer a brief
    acknowledgement. Re-queries everything fresh by id so it is safe to call
    after the decline has been committed. Returns the number of emails sent."""
    call = (await db.execute(select(VolunteerCall).where(VolunteerCall.id == call_id))).scalar_one()
    task = (
        await db.execute(
            select(Task)
            .options(
                selectinload(Task.team_lead),
                selectinload(Task.assignments).selectinload(TeamAssignment.person),
            )
            .where(Task.id == task_id)
        )
    ).scalar_one()
    volunteer = (await db.execute(select(Person).where(Person.id == volunteer_id))).scalar_one()
    admin = None
    if call.created_by_id is not None:
        admin = (
            await db.execute(select(Person).where(Person.id == call.created_by_id))
        ).scalar_one_or_none()

    team_lead_template = _jinja_env.get_template("team_lead_roster.html")
    removal_template = _jinja_env.get_template("volunteer_assignment_removed.html")

    def volunteering_url_for(person: Person) -> str:
        return (
            f"{settings.app_base_url}/volunteering?token={issue_invite_token(person.id, call.id)}"
        )

    def volunteering_link_for(person: Person) -> str:
        return f"/volunteering?token={issue_invite_token(person.id, call.id)}"

    volunteer_name = f"{volunteer.first_name} {volunteer.last_name}".strip()
    decline_notice = {"volunteer_name": volunteer_name, "message": message}
    roster = [
        {
            "name": f"{a.person.first_name} {a.person.last_name}",
            "phone": a.person.phone,
            "email": a.person.email,
            "skills": list(a.person.skills),
            "status": None,
        }
        for a in task.assignments
    ]

    sent = 0

    # --- Lead + admin: updated roster with the cannot-attend callout ---
    lead = task.team_lead
    recipients: list[Person] = []
    if lead is not None and is_subscribed(lead):
        recipients.append(lead)
    if admin is not None and is_subscribed(admin) and (lead is None or admin.id != lead.id):
        recipients.append(admin)
    subject = f"Roster update: {call.title} — {task.short_description}"
    summary_body = (
        f"{volunteer_name} can no longer attend {task.short_description} for {call.title}."
    )
    for person in recipients:
        full_body = team_lead_template.render(
            subject=subject,
            title=call.title,
            subtitle=task.short_description,
            first_name=person.first_name,
            task=task_view(task, include_full_details=True),
            roster=roster,
            decline=decline_notice,
            volunteering_url=volunteering_url_for(person),
        )
        if deliver_notification(
            person=person,
            subject=subject,
            full_body=full_body,
            summary_body=summary_body,
            link=volunteering_link_for(person),
            inline_images=EMAIL_INLINE_IMAGES,
        ):
            sent += 1

    # --- Volunteer: brief acknowledgement (no project details) ---
    if is_subscribed(volunteer):
        ack_subject = f"Assignment update for {call.title}"
        ack_body = removal_template.render(
            subject=ack_subject,
            title=call.title,
            subtitle="Assignment changed",
            first_name=volunteer.first_name,
            call_title=call.title,
            removed_tasks=[task_view(task, include_full_details=False)],
            volunteering_url=volunteering_url_for(volunteer),
        )
        if deliver_notification(
            person=volunteer,
            subject=ack_subject,
            full_body=ack_body,
            summary_body=(
                f"You've been removed from a task for {call.title}; "
                "your team lead has been notified."
            ),
            link=volunteering_link_for(volunteer),
            inline_images=EMAIL_INLINE_IMAGES,
        ):
            sent += 1

    return sent
