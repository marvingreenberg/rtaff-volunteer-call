"""Notification creation and delivery service."""

import datetime
import logging

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


async def generate_call_notifications(call_id: str, db: AsyncSession) -> tuple[int, int]:
    """Send summary notifications when a call closes.

    Each volunteer who expressed availability gets one message: assigned volunteers
    see their task list with thanks; unassigned volunteers get a "thanks, all filled" note.

    Returns (assignment_emails, thanks_emails).
    """
    tasks_q = (
        select(Task)
        .where(Task.volunteer_call_id == call_id)
        .options(selectinload(Task.assignments).selectinload(TeamAssignment.person))
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

    volunteer_tasks: dict[str, tuple[Person, list[str]]] = {}
    for task in tasks:
        date_str = task.date.strftime("%b %d") if task.date else "TBD"
        task_desc = f"{task.short_description} ({date_str})"
        for assignment in task.assignments:
            if assignment.person_id not in volunteer_tasks:
                volunteer_tasks[assignment.person_id] = (assignment.person, [])
            volunteer_tasks[assignment.person_id][1].append(task_desc)

    assigned_ids = set(volunteer_tasks.keys())
    avail_people: dict[str, Person] = {}
    for a in availabilities:
        avail_people[a.person_id] = a.person
    available_ids = set(avail_people.keys())

    assignment_emails = 0
    thanks_emails = 0

    for person_id, (person, task_list) in volunteer_tasks.items():
        if not is_subscribed(person):
            continue
        items = "\n".join(f"- {t}" for t in task_list)
        full_body = (
            f"Thank you for volunteering for {call.title}!\n\n"
            f"You have been assigned to the following tasks:\n\n{items}"
        )
        summary_body = f"You're assigned to {len(task_list)} task(s) for {call.title}."
        subject = f"Your assignments for {call.title}"

        if deliver_notification(
            person=person,
            subject=subject,
            full_body=full_body,
            summary_body=summary_body,
            link="/volunteering",
        ):
            assignment_emails += 1

    for person_id in available_ids - assigned_ids:
        person = avail_people[person_id]
        if not is_subscribed(person):
            continue
        subject = f"Thank you for volunteering for {call.title}"
        full_body = (
            f"Thank you for offering your availability for {call.title}. "
            f"All teams have been filled for this round, but we "
            f"appreciate your willingness to help and will reach out for "
            f"future opportunities."
        )
        summary_body = f"Thanks for volunteering for {call.title} — all teams filled this round."

        if deliver_notification(
            person=person,
            subject=subject,
            full_body=full_body,
            summary_body=summary_body,
            link="/volunteering",
        ):
            thanks_emails += 1

    return assignment_emails, thanks_emails
