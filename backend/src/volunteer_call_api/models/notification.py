"""Notification models for in-app messaging."""

import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from volunteer_call_api.models.base import Base, generate_uuid


class NotificationType(Base):
    """Configuration for a notification category."""

    __tablename__ = "notification_types"

    type: Mapped[str] = mapped_column(String(50), primary_key=True)
    delivery: Mapped[str] = mapped_column(String(20), server_default="none", nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)


class Notification(Base):
    """An in-app notification sent to a person."""

    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    person_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("people.id"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    link: Mapped[str | None] = mapped_column(Text)
    read: Mapped[bool] = mapped_column(
        Boolean, server_default="false", default=False, nullable=False
    )
    call_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("volunteer_calls.id")
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    person: Mapped["Person"] = relationship()
    volunteer_call: Mapped["VolunteerCall | None"] = relationship()


from volunteer_call_api.models.person import Person  # noqa: E402
from volunteer_call_api.models.volunteer_call import VolunteerCall  # noqa: E402
