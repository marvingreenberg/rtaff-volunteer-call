"""Volunteer call and task routes."""

import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from volunteer_call_api.config import settings
from volunteer_call_api.database import get_db
from volunteer_call_api.models.person import (
    Person,
    PersonRole,
    Program,
    RoleType,
    VolunteerProgram,
)
from volunteer_call_api.models.team_assignment import TeamAssignment
from volunteer_call_api.models.volunteer_availability import VolunteerAvailability
from volunteer_call_api.models.volunteer_call import CallStatus, Task, TaskStatus, VolunteerCall
from volunteer_call_api.schemas.volunteer_call import (
    AssignmentNoticesResponse,
    AssignmentOverviewResponse,
    AvailableVolunteer,
    JobListItem,
    SendInvitesResponse,
    TaskAssignment,
    TaskCreate,
    TaskOverviewItem,
    TaskResponse,
    TaskUpdate,
    VolunteerCallCreate,
    VolunteerCallListResponse,
    VolunteerCallResponse,
    VolunteerCallUpdate,
    VolunteerOverviewItem,
)
from volunteer_call_api.services.auth import generate_access_token
from volunteer_call_api.services.email_render import jinja_env
from volunteer_call_api.services.notifications import (
    EMAIL_INLINE_IMAGES,
    deliver_notification,
    generate_call_notifications,
    is_subscribed,
    task_view,
)
from volunteer_call_api.services.volunteer_call_helpers import (
    _initials,
    call_list_response,
    call_response,
    get_call_or_404,
    task_response,
)

router = APIRouter()


# --- Volunteer Calls ---


@router.post("", response_model=VolunteerCallResponse, status_code=201)
async def create_volunteer_call(
    body: VolunteerCallCreate, db: AsyncSession = Depends(get_db)
) -> VolunteerCallResponse:
    call = VolunteerCall(
        title=body.title, program=body.program, status=body.status, notes=body.notes
    )
    db.add(call)
    await db.flush()

    # Single-task programs (ACR / RAMP / LIFT) often pass an initial task in
    # the same request so the create form can be one screen, not two. RTX
    # calls can use this too but typically add tasks on the detail page.
    if body.initial_task is not None:
        t = body.initial_task
        db.add(
            Task(
                volunteer_call_id=call.id,
                short_description=t.short_description,
                date=t.date,
                time_start=t.time_start,
                time_end=t.time_end,
                address=t.address,
                city=t.city,
                team_lead_id=t.team_lead_id,
                volunteers_needed=t.volunteers_needed,
                skilled_needed=t.skilled_needed,
                notes=t.notes,
            )
        )

    await db.commit()
    call = await get_call_or_404(call.id, db)
    return call_response(call)


@router.get("", response_model=list[VolunteerCallListResponse])
async def list_volunteer_calls(
    status: CallStatus | None = None,
    program: Program | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[VolunteerCallListResponse]:
    query = select(VolunteerCall).options(
        selectinload(VolunteerCall.tasks).selectinload(Task.assignments)
    )
    if status is not None:
        query = query.where(VolunteerCall.status == status)
    if program is not None:
        query = query.where(VolunteerCall.program == program)
    query = query.order_by(VolunteerCall.created_at.desc())
    result = await db.execute(query)
    return [call_list_response(c) for c in result.scalars().all()]


@router.get("/{call_id}", response_model=VolunteerCallResponse)
async def get_volunteer_call(
    call_id: str, db: AsyncSession = Depends(get_db)
) -> VolunteerCallResponse:
    call = await get_call_or_404(call_id, db)
    return call_response(call)


@router.put("/{call_id}", response_model=VolunteerCallResponse)
async def update_volunteer_call(
    call_id: str, body: VolunteerCallUpdate, db: AsyncSession = Depends(get_db)
) -> VolunteerCallResponse:
    call = await get_call_or_404(call_id, db)

    # PUT is the admin override path; the canonical workflow uses the
    # dedicated send-invites / done-assigning / archive endpoints.
    if body.status == CallStatus.WAITING:
        non_cancelled = [t for t in call.tasks if t.status != TaskStatus.CANCELLED]
        unscheduled = [t for t in non_cancelled if t.date is None]
        if unscheduled:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot open call: {len(unscheduled)} task(s) have no date set",
            )

    for field in ["title", "status", "notes"]:
        value = getattr(body, field)
        if value is not None:
            setattr(call, field, value)

    await db.commit()
    call = await get_call_or_404(call_id, db)
    return call_response(call)


@router.delete("/{call_id}", status_code=204)
async def delete_volunteer_call(call_id: str, db: AsyncSession = Depends(get_db)) -> None:
    """Hard delete a call and everything reachable from it.

    Tasks, availabilities, and assignments cascade via ORM relationship config.
    The frontend gates this behind an admin-confirm dialog (and a second one
    when the call has already gone past Draft, which means notifications
    were sent).
    """
    call = await get_call_or_404(call_id, db)
    await db.delete(call)
    await db.commit()


# --- Jobs (volunteer-facing) ---


@router.get("/{call_id}/jobs", response_model=list[JobListItem])
async def list_jobs(call_id: str, db: AsyncSession = Depends(get_db)) -> list[JobListItem]:
    """Volunteer-facing: list tasks without addresses."""
    query = (
        select(Task)
        .options(selectinload(Task.assignments))
        .where(Task.volunteer_call_id == call_id, Task.status != TaskStatus.CANCELLED)
        .order_by(Task.date)
    )
    result = await db.execute(query)
    tasks = result.scalars().all()

    call = await get_call_or_404(call_id, db)
    return [
        JobListItem(
            task_id=t.id,
            date=t.date,
            time_start=t.time_start,
            time_end=t.time_end,
            short_description=t.short_description,
            city=t.city,
            volunteers_needed=t.volunteers_needed,
            skilled_needed=t.skilled_needed,
            assigned_count=len(t.assignments),
            program=call.program,
            notes=t.notes,
        )
        for t in tasks
    ]


# --- Send Invites ---


@router.post("/{call_id}/send-invites", response_model=SendInvitesResponse)
async def send_invites(call_id: str, db: AsyncSession = Depends(get_db)) -> SendInvitesResponse:
    """Send invitations to all active, subscribed volunteers via their preferred channel.

    Canonical OPEN → WAITING transition. Re-sending while already WAITING is
    allowed (idempotent enough). Rejects from ASSIGNED / ARCHIVED.
    """
    call = await get_call_or_404(call_id, db)
    if call.status not in (CallStatus.OPEN, CallStatus.WAITING):
        raise HTTPException(
            status_code=400,
            detail="Cannot send invites once assignment is complete",
        )

    non_cancelled = [t for t in call.tasks if t.status != TaskStatus.CANCELLED]
    if call.status == CallStatus.OPEN:
        unscheduled = [t for t in non_cancelled if t.date is None]
        if unscheduled:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot send invites: {len(unscheduled)} task(s) have no date set",
            )
        call.status = CallStatus.WAITING

    task_count = len(non_cancelled)
    invite_tasks = sorted(
        non_cancelled,
        key=lambda t: (t.date or datetime.date.max, t.time_start or datetime.time.max),
    )
    invite_task_views = [task_view(t, include_full_details=False) for t in invite_tasks]

    # Filter by program: only members of this call's program get the invite.
    result = await db.execute(
        select(Person)
        .join(Person.roles)
        .join(Person.program_memberships)
        .where(
            PersonRole.role == RoleType.VOLUNTEER,
            Person.active.is_(True),
            VolunteerProgram.program == call.program,
            VolunteerProgram.active.is_(True),
        )
    )
    volunteers = result.scalars().unique().all()

    notified = 0
    skipped = 0
    template = jinja_env.get_template("volunteer_invite.html")

    for v in volunteers:
        if not is_subscribed(v):
            skipped += 1
            continue

        if not v.access_token:
            v.access_token = generate_access_token()

        volunteering_url = f"{settings.app_base_url}/volunteering?token={v.access_token}"
        subject = f"Volunteer Call: {call.title}"
        full_body = template.render(
            subject=subject,
            title=call.title,
            subtitle=f"{task_count} task{'s' if task_count != 1 else ''} need volunteers",
            first_name=v.first_name,
            call_title=call.title,
            tasks=invite_task_views,
            volunteering_url=volunteering_url,
        )
        summary_body = f"RT-AFF Volunteer Call: {call.title} — {task_count} task(s) available."

        delivered = deliver_notification(
            person=v,
            subject=subject,
            full_body=full_body,
            summary_body=summary_body,
            link=f"/volunteering?token={v.access_token}",
            inline_images=EMAIL_INLINE_IMAGES,
        )
        if delivered:
            notified += 1
        else:
            skipped += 1

    await db.commit()
    return SendInvitesResponse(volunteers_notified=notified, volunteers_skipped=skipped)


# --- Send Assignment Notices ---


@router.post("/{call_id}/send-assignment-notices", response_model=AssignmentNoticesResponse)
async def send_assignment_notices(
    call_id: str, db: AsyncSession = Depends(get_db)
) -> AssignmentNoticesResponse:
    """Dispatch assignment + thank-you emails for an ASSIGNED call.

    Stamps assignments_sent_at on success. Does not change the call status;
    the row's "Send Assignments" button switches to "Archive" via the
    timestamp's presence rather than a fifth status.
    """
    call = await get_call_or_404(call_id, db)
    if call.status != CallStatus.ASSIGNED:
        raise HTTPException(
            status_code=400,
            detail="Cannot send assignment notices: assignment is not complete",
        )
    assigned, thanks = await generate_call_notifications(call_id, db)
    call.assignments_sent_at = datetime.datetime.now(datetime.timezone.utc)
    await db.commit()
    return AssignmentNoticesResponse(
        assignment_emails=assigned,
        thanks_emails=thanks,
    )


@router.post("/{call_id}/done-assigning", response_model=VolunteerCallResponse)
async def done_assigning(call_id: str, db: AsyncSession = Depends(get_db)) -> VolunteerCallResponse:
    """Transition WAITING → ASSIGNED. Called by the /assign page's Save button.

    The Phase 4 policy and team-lead gates are enforced UI-side; this endpoint
    only validates the status. Reject when the call has already advanced past
    WAITING (or never reached it).
    """
    call = await get_call_or_404(call_id, db)
    if call.status != CallStatus.WAITING:
        raise HTTPException(
            status_code=400,
            detail="Cannot finish assigning: call is not in the assigning state",
        )
    call.status = CallStatus.ASSIGNED
    await db.commit()
    call = await get_call_or_404(call_id, db)
    return call_response(call)


@router.post("/{call_id}/archive", response_model=VolunteerCallResponse)
async def archive_call(call_id: str, db: AsyncSession = Depends(get_db)) -> VolunteerCallResponse:
    """Transition ASSIGNED → ARCHIVED. Called by the list page's Archive button."""
    call = await get_call_or_404(call_id, db)
    if call.status != CallStatus.ASSIGNED:
        raise HTTPException(
            status_code=400,
            detail="Cannot archive: call is not in the assigned state",
        )
    call.status = CallStatus.ARCHIVED
    await db.commit()
    call = await get_call_or_404(call_id, db)
    return call_response(call)


# --- Assignment Overview ---


@router.get("/{call_id}/assignment-overview", response_model=AssignmentOverviewResponse)
async def assignment_overview(
    call_id: str, db: AsyncSession = Depends(get_db)
) -> AssignmentOverviewResponse:
    call = await get_call_or_404(call_id, db)

    tasks_q = (
        select(Task)
        .where(Task.volunteer_call_id == call_id)
        .options(
            selectinload(Task.assignments).selectinload(TeamAssignment.person),
            selectinload(Task.team_lead),
        )
        .order_by(Task.date)
    )
    tasks_result = await db.execute(tasks_q)
    tasks = tasks_result.scalars().unique().all()

    # Per-task availability (with persons + roles eager-loaded) so we can
    # compute "available but not assigned" candidates per task in one pass.
    task_avail_result = await db.execute(
        select(VolunteerAvailability)
        .options(selectinload(VolunteerAvailability.person).selectinload(Person.roles))
        .where(
            VolunteerAvailability.volunteer_call_id == call_id,
            VolunteerAvailability.task_id.is_not(None),
            VolunteerAvailability.available.is_(True),
        )
    )
    task_availabilities = task_avail_result.scalars().unique().all()
    avail_by_task: dict[str, list[Person]] = {}
    for av in task_availabilities:
        if av.task_id is None:  # filtered in WHERE; narrows for the type checker
            continue
        person = av.person
        if not person.active:
            continue
        roles = {r.role for r in person.roles}
        if RoleType.VOLUNTEER not in roles and RoleType.TEAM_LEADER not in roles:
            continue
        avail_by_task.setdefault(av.task_id, []).append(person)

    task_items = []
    for t in tasks:
        assigned_ids = {a.person_id for a in t.assignments}
        candidates = [p for p in avail_by_task.get(t.id, []) if p.id not in assigned_ids]
        # Skilled (any tag) volunteers float to the top, then alpha by name.
        candidates.sort(key=lambda p: (not p.skills, p.first_name, p.last_name))
        task_items.append(
            TaskOverviewItem(
                task_id=t.id,
                short_description=t.short_description,
                city=t.city,
                date=t.date,
                time_start=t.time_start,
                time_end=t.time_end,
                volunteers_needed=t.volunteers_needed,
                skilled_needed=t.skilled_needed,
                status=t.status.value,
                notes=t.notes,
                team_lead_id=t.team_lead_id,
                team_lead_name=(
                    f"{t.team_lead.first_name} {t.team_lead.last_name}" if t.team_lead else None
                ),
                assignments=[
                    TaskAssignment(
                        assignment_id=a.id,
                        person_id=a.person_id,
                        person_name=f"{a.person.first_name} {a.person.last_name}",
                        initials=_initials(a.person.first_name, a.person.last_name),
                        skills=list(a.person.skills),
                        role=a.role.value,
                    )
                    for a in t.assignments
                ],
                available_volunteers=[
                    AvailableVolunteer(
                        person_id=p.id,
                        person_name=f"{p.first_name} {p.last_name}",
                        initials=_initials(p.first_name, p.last_name),
                        skills=list(p.skills),
                    )
                    for p in candidates
                ],
            )
        )

    avail_result = await db.execute(
        select(VolunteerAvailability)
        .options(selectinload(VolunteerAvailability.person))
        .where(VolunteerAvailability.volunteer_call_id == call_id)
    )
    availabilities = avail_result.scalars().unique().all()

    vol_map: dict[str, VolunteerOverviewItem] = {}
    for av in availabilities:
        p = av.person
        if p.id not in vol_map:
            vol_map[p.id] = VolunteerOverviewItem(
                person_id=p.id,
                person_name=f"{p.first_name} {p.last_name}",
                initials=_initials(p.first_name, p.last_name),
                skills=list(p.skills),
                phone=p.phone,
                max_tasks_per_week=av.max_tasks_per_week or 2,
            )
        if av.task_id and av.available:
            vol_map[p.id].available_task_ids.append(av.task_id)

    assigned_counts: dict[str, int] = {}
    for t in tasks:
        for a in t.assignments:
            assigned_counts[a.person_id] = assigned_counts.get(a.person_id, 0) + 1
    for vid, item in vol_map.items():
        item.assignments_this_call = assigned_counts.get(vid, 0)

    return AssignmentOverviewResponse(
        call_id=call.id,
        call_title=call.title,
        tasks=task_items,
        volunteers=list(vol_map.values()),
    )


# --- Tasks ---


@router.post("/{call_id}/tasks", response_model=TaskResponse, status_code=201)
async def add_task(
    call_id: str, body: TaskCreate, db: AsyncSession = Depends(get_db)
) -> TaskResponse:
    await get_call_or_404(call_id, db)
    task = Task(
        volunteer_call_id=call_id,
        short_description=body.short_description,
        date=body.date,
        time_start=body.time_start,
        time_end=body.time_end,
        address=body.address,
        city=body.city,
        team_lead_id=body.team_lead_id,
        volunteers_needed=body.volunteers_needed,
        skilled_needed=body.skilled_needed,
        notes=body.notes,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    result = await db.execute(
        select(Task)
        .options(selectinload(Task.assignments), selectinload(Task.team_lead))
        .where(Task.id == task.id)
    )
    task = result.scalar_one()
    return task_response(task)


@router.put("/{call_id}/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    call_id: str, task_id: str, body: TaskUpdate, db: AsyncSession = Depends(get_db)
) -> TaskResponse:
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.volunteer_call_id == call_id)
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    # Use exclude_unset so explicit `null` clears nullable fields, while
    # omitted fields are left untouched. (Naively `if value is not None`
    # would conflate "client wants to clear" with "client didn't send".)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(task, field, value)

    await db.commit()
    result = await db.execute(
        select(Task)
        .options(selectinload(Task.assignments), selectinload(Task.team_lead))
        .where(Task.id == task_id)
    )
    task = result.scalar_one()
    return task_response(task)


@router.delete("/{call_id}/tasks/{task_id}", status_code=204)
async def delete_task(call_id: str, task_id: str, db: AsyncSession = Depends(get_db)) -> None:
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.volunteer_call_id == call_id)
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    await db.delete(task)
    await db.commit()
