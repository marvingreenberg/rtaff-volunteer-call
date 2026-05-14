"""Person and PersonRole models."""

import enum
from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from volunteer_call_api.models.base import Base, TimestampMixin, generate_uuid


class Skill(enum.Enum):
    PLUMBING = "plumbing"
    ELECTRICAL = "electrical"
    CARPENTRY = "carpentry"
    HVAC = "hvac"


class Program(enum.Enum):
    RTX = "RTX"
    ACR = "ACR"
    RAMP = "RAMP"
    LIFT = "LIFT"


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
    # Tag set of skills. Postgres ARRAY of the `skill` enum in production;
    # JSON-list fallback for sqlite-backed unit tests via `with_variant`.
    skills: Mapped[list[Skill]] = mapped_column(
        ARRAY(
            PG_ENUM(Skill, name="skill", values_callable=lambda e: [x.value for x in e])
        ).with_variant(JSON, "sqlite"),
        nullable=False,
        default=list,
        server_default="{}",
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    access_token: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)

    # Calendar integration. `calendar_url` is treated as a bearer secret —
    # never returned in any API response. Only `calendar_connected` derives
    # for the frontend.
    calendar_url: Mapped[str | None] = mapped_column(String(2048))
    calendar_provider: Mapped[str | None] = mapped_column(String(20))
    calendar_url_added_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

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
    program_memberships: Mapped[list["VolunteerProgram"]] = relationship(
        back_populates="person", cascade="all, delete-orphan"
    )
    login_aliases: Mapped[list["PersonLoginAlias"]] = relationship(
        back_populates="person", cascade="all, delete-orphan"
    )


class VolunteerProgram(Base):
    """Many-to-many: which programs a person volunteers for, with metadata."""

    __tablename__ = "volunteer_programs"

    person_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("people.id", ondelete="CASCADE"), primary_key=True
    )
    program: Mapped[Program] = mapped_column(
        Enum(Program, name="program", values_callable=lambda e: [x.value for x in e]),
        primary_key=True,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    person: Mapped["Person"] = relationship(back_populates="program_memberships")


class PersonLoginAlias(Base):
    """Alternate email address usable to request a magic-link login.

    The primary `Person.email` remains the channel for all outbound
    notifications; aliases only widen the set of addresses a user can
    type into the login form. The magic link itself is sent to whichever
    address the user typed.
    """

    __tablename__ = "person_login_aliases"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    person_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("people.id", ondelete="CASCADE"), nullable=False
    )
    # Stored lowercased; uniqueness is enforced case-insensitively at write time.
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)

    person: Mapped["Person"] = relationship(back_populates="login_aliases")


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
