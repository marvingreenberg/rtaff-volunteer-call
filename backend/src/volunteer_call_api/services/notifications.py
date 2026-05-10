"""Notification creation and delivery service."""

import datetime
import logging
from typing import Any

from jinja2 import Environment, PackageLoader, select_autoescape
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
from volunteer_call_api.services.sms import send_sms

logger = logging.getLogger(__name__)


_jinja_env = Environment(
    loader=PackageLoader("volunteer_call_api", "templates"),
    autoescape=select_autoescape(["html", "xml"]),
)


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
            unsubscribe_url = f"{settings.app_base_url}/unsubscribe?token={person.access_token}"
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


def task_view(task: Task, *, include_full_details: bool) -> dict[str, Any]:
    """Render-friendly task dict shared by call-invite and assignment templates."""
    view: dict[str, Any] = {
        "date_label": _format_date(task.date),
        "short_description": task.short_description,
        "city": task.city,
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


async def generate_call_notifications(call_id: str, db: AsyncSession) -> tuple[int, int]:
    """Send rich assignment + thank-you emails when a call closes.

    Each assigned volunteer gets a templated email with their task list (date,
    time, full address, team lead, notes) and a link back to their volunteer
    page. Volunteers who offered availability but went unassigned get a
    thank-you note.

    Returns (assignment_emails, thanks_emails).
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
    tasks = list(tasks_result.scalars().all())

    call_result = await db.execute(select(VolunteerCall).where(VolunteerCall.id == call_id))
    call = call_result.scalar_one()

    avail_result = await db.execute(
        select(VolunteerAvailability)
        .options(selectinload(VolunteerAvailability.person))
        .where(VolunteerAvailability.volunteer_call_id == call_id)
    )
    availabilities = list(avail_result.scalars().all())

    volunteer_tasks: dict[str, tuple[Person, list[Task]]] = {}
    for task in tasks:
        for assignment in task.assignments:
            if assignment.person_id not in volunteer_tasks:
                volunteer_tasks[assignment.person_id] = (assignment.person, [])
            volunteer_tasks[assignment.person_id][1].append(task)

    assigned_ids = set(volunteer_tasks.keys())
    avail_people: dict[str, Person] = {a.person_id: a.person for a in availabilities}
    available_ids = set(avail_people.keys())

    assignment_template = _jinja_env.get_template("volunteer_assignment.html")
    thanks_template = _jinja_env.get_template("volunteer_thanks.html")

    assignment_emails = 0
    thanks_emails = 0

    for person_id, (person, person_tasks) in volunteer_tasks.items():
        if not is_subscribed(person):
            continue
        if not person.access_token:
            # Should already exist from the invite step, but guard anyway.
            continue

        volunteering_url = f"{settings.app_base_url}/volunteering?token={person.access_token}"
        task_views = [task_view(t, include_full_details=True) for t in person_tasks]
        subject = f"Your assignments for {call.title}"

        full_body = assignment_template.render(
            subject=subject,
            title=call.title,
            subtitle=f"You're confirmed for {len(person_tasks)} "
            f"task{'s' if len(person_tasks) > 1 else ''}",
            first_name=person.first_name,
            tasks=task_views,
            volunteering_url=volunteering_url,
        )
        summary_body = f"You're assigned to {len(person_tasks)} task(s) for {call.title}."

        if deliver_notification(
            person=person,
            subject=subject,
            full_body=full_body,
            summary_body=summary_body,
            link=f"/volunteering?token={person.access_token}",
            inline_images=EMAIL_INLINE_IMAGES,
        ):
            assignment_emails += 1

    for person_id in available_ids - assigned_ids:
        person = avail_people[person_id]
        if not is_subscribed(person):
            continue
        if not person.access_token:
            continue

        volunteering_url = f"{settings.app_base_url}/volunteering?token={person.access_token}"
        subject = f"Thank you for volunteering for {call.title}"

        full_body = thanks_template.render(
            subject=subject,
            title=f"Thanks, {person.first_name}!",
            subtitle=None,
            first_name=person.first_name,
            call_title=call.title,
            volunteering_url=volunteering_url,
        )
        summary_body = f"Thanks for volunteering for {call.title} — all teams filled this round."

        if deliver_notification(
            person=person,
            subject=subject,
            full_body=full_body,
            summary_body=summary_body,
            link=f"/volunteering?token={person.access_token}",
            inline_images=EMAIL_INLINE_IMAGES,
        ):
            thanks_emails += 1

    return assignment_emails, thanks_emails
