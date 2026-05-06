"""Task event models for postponement, cancellation, and rescheduling."""

import datetime
import enum

from sqlalchemy import JSON, Date, DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from volunteer_call_api.models.base import Base, generate_uuid


class SlotEventType(str, enum.Enum):
    POSTPONED = "postponed"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"


class SlotEvent(Base):
    """A schedule change event for a task."""

    __tablename__ = "slot_events"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    task_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("tasks.id"), nullable=False
    )
    event_type: Mapped[SlotEventType] = mapped_column(
        Enum(SlotEventType, name="sloteventtype", create_type=False), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    new_date: Mapped[datetime.date | None] = mapped_column(Date)
    created_by_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("people.id"))
    notified_people: Mapped[list[dict[str, str]]] = mapped_column(JSON, server_default="[]")
    cc_people: Mapped[list[dict[str, str]]] = mapped_column(JSON, server_default="[]")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    task: Mapped["Task"] = relationship()
    created_by: Mapped["Person | None"] = relationship()


from volunteer_call_api.models.person import Person  # noqa: E402
from volunteer_call_api.models.volunteer_call import Task  # noqa: E402
