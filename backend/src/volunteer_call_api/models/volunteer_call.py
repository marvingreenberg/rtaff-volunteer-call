"""Volunteer call and task models."""

import datetime
import enum

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, String, Text, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from volunteer_call_api.models.base import Base, TimestampMixin, generate_uuid
from volunteer_call_api.models.person import Program


class CallStatus(enum.Enum):
    """Volunteer call lifecycle.

    open      — created; tasks can still be added.
    waiting   — invites sent; volunteers are responding.
    assigned  — admin clicked Done Assigning. Notices may or may not have
                gone out yet (toggled by assignments_sent_at).
    archived  — call closed out.
    """

    OPEN = "open"
    WAITING = "waiting"
    ASSIGNED = "assigned"
    ARCHIVED = "archived"


class TaskStatus(enum.Enum):
    OPEN = "open"
    FULL = "full"
    CANCELLED = "cancelled"


class VolunteerCall(Base, TimestampMixin):
    """A recruitment period for assembling volunteer teams."""

    __tablename__ = "volunteer_calls"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    program: Mapped[Program] = mapped_column(
        Enum(Program, name="program", values_callable=lambda e: [x.value for x in e]),
        nullable=False,
    )
    status: Mapped[CallStatus] = mapped_column(
        Enum(CallStatus, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        default=CallStatus.OPEN,
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_by_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("people.id"), nullable=True
    )
    # Stamped on Send Assignments. Absence (NULL) == admin has clicked Done
    # Assigning (status == ASSIGNED) but not yet sent notification emails.
    assignments_sent_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    tasks: Mapped[list["Task"]] = relationship(
        back_populates="volunteer_call", cascade="all, delete-orphan"
    )
    availabilities: Mapped[list["VolunteerAvailability"]] = relationship(
        back_populates="volunteer_call", cascade="all, delete-orphan"
    )


class Task(Base, TimestampMixin):
    """A task needing volunteers within a call — entered directly by admins."""

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    volunteer_call_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("volunteer_calls.id"), nullable=False
    )
    short_description: Mapped[str] = mapped_column(String(500), nullable=False)
    date: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    time_start: Mapped[datetime.time | None] = mapped_column(Time, nullable=True)
    time_end: Mapped[datetime.time | None] = mapped_column(Time, nullable=True)
    address: Mapped[str | None] = mapped_column(String(500))
    city: Mapped[str | None] = mapped_column(String(100))
    team_lead_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("people.id"), nullable=True
    )
    volunteers_needed: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    skilled_needed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        default=TaskStatus.OPEN,
    )
    notes: Mapped[str | None] = mapped_column(Text)

    volunteer_call: Mapped["VolunteerCall"] = relationship(back_populates="tasks")
    team_lead: Mapped["Person | None"] = relationship(foreign_keys=[team_lead_id])
    assignments: Mapped[list["TeamAssignment"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )


from volunteer_call_api.models.person import Person  # noqa: E402,F811
from volunteer_call_api.models.team_assignment import TeamAssignment  # noqa: E402
from volunteer_call_api.models.volunteer_availability import VolunteerAvailability  # noqa: E402
