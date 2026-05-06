"""Team assignment model."""

import enum

from sqlalchemy import Boolean, Enum, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from volunteer_call_api.models.base import Base, TimestampMixin, generate_uuid


class AssignmentRole(enum.Enum):
    TEAM_LEADER = "team_leader"
    VOLUNTEER = "volunteer"


class TeamAssignment(Base, TimestampMixin):
    """A volunteer assigned to a task."""

    __tablename__ = "team_assignments"
    __table_args__ = (UniqueConstraint("task_id", "person_id", name="uq_assignment_task_person"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    task_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("tasks.id"), nullable=False
    )
    person_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("people.id"), nullable=False
    )
    role: Mapped[AssignmentRole] = mapped_column(
        Enum(AssignmentRole, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        default=AssignmentRole.VOLUNTEER,
    )
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    task: Mapped["Task"] = relationship(back_populates="assignments")
    person: Mapped["Person"] = relationship()


from volunteer_call_api.models.person import Person  # noqa: E402
from volunteer_call_api.models.volunteer_call import Task  # noqa: E402
