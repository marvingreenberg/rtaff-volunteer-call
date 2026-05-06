"""Person and PersonRole models."""

import enum
from datetime import date

from sqlalchemy import Boolean, Date, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from volunteer_call_api.models.base import Base, TimestampMixin, generate_uuid


class SkillCategory(enum.Enum):
    SKILLED = "skilled"
    UNSKILLED = "unskilled"
    UNKNOWN = "unknown"


class RoleType(enum.Enum):
    STAFF = "staff"
    TEAM_LEADER = "team_leader"
    VOLUNTEER = "volunteer"


class NotificationPreference(enum.Enum):
    EMAIL = "email"
    SMS = "sms"
    BOTH = "both"


class NotificationDetailLevel(enum.Enum):
    SUMMARY = "summary"
    FULL = "full"


class SubscriptionStatus(enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    UNSUBSCRIBED = "unsubscribed"


class Person(Base, TimestampMixin):
    """A person in the volunteer call system (staff, team leader, volunteer)."""

    __tablename__ = "people"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    phone_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    skill_category: Mapped[SkillCategory] = mapped_column(
        Enum(SkillCategory, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        default=SkillCategory.UNKNOWN,
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    access_token: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)

    notification_preference: Mapped[NotificationPreference] = mapped_column(
        Enum(NotificationPreference, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        default=NotificationPreference.EMAIL,
    )
    notification_detail_level: Mapped[NotificationDetailLevel] = mapped_column(
        Enum(NotificationDetailLevel, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        default=NotificationDetailLevel.FULL,
    )
    subscription_status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        default=SubscriptionStatus.ACTIVE,
    )
    pause_start: Mapped[date | None] = mapped_column(Date)
    pause_end: Mapped[date | None] = mapped_column(Date)

    roles: Mapped[list["PersonRole"]] = relationship(
        back_populates="person", cascade="all, delete-orphan"
    )


class PersonRole(Base):
    """A role assigned to a person."""

    __tablename__ = "person_roles"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    person_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("people.id"), nullable=False
    )
    role: Mapped[RoleType] = mapped_column(
        Enum(RoleType, values_callable=lambda e: [x.value for x in e]), nullable=False
    )

    person: Mapped["Person"] = relationship(back_populates="roles")
