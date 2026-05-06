"""Volunteer availability model."""

from sqlalchemy import Boolean, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from volunteer_call_api.models.base import Base, TimestampMixin, generate_uuid


class VolunteerAvailability(Base, TimestampMixin):
    """A volunteer's availability response for a task within a call."""

    __tablename__ = "volunteer_availability"
    __table_args__ = (
        UniqueConstraint(
            "volunteer_call_id", "person_id", "task_id", name="uq_availability_call_person_task"
        ),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    volunteer_call_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("volunteer_calls.id"), nullable=False
    )
    person_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("people.id"), nullable=False
    )
    task_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("tasks.id"), nullable=True
    )
    available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    max_tasks_per_week: Mapped[int | None] = mapped_column(Integer, default=1)
    notes: Mapped[str | None] = mapped_column(Text)

    volunteer_call: Mapped["VolunteerCall"] = relationship(back_populates="availabilities")
    person: Mapped["Person"] = relationship()


from volunteer_call_api.models.person import Person  # noqa: E402
from volunteer_call_api.models.volunteer_call import VolunteerCall  # noqa: E402
