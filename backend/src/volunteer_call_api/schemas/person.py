"""Pydantic schemas for person endpoints."""

from datetime import date, datetime

from pydantic import BaseModel

from volunteer_call_api.models.person import (
    NotificationDetailLevel,
    NotificationPreference,
    RoleType,
    SkillCategory,
    SubscriptionStatus,
)


class PersonCreate(BaseModel):
    first_name: str
    last_name: str
    email: str | None = None
    phone: str | None = None
    skill_category: SkillCategory = SkillCategory.UNKNOWN
    active: bool = True
    notification_preference: NotificationPreference = NotificationPreference.EMAIL
    notification_detail_level: NotificationDetailLevel = NotificationDetailLevel.FULL
    subscription_status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    notes: str | None = None
    roles: list[RoleType] = []


class PersonUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    skill_category: SkillCategory | None = None
    active: bool | None = None
    notification_preference: NotificationPreference | None = None
    notification_detail_level: NotificationDetailLevel | None = None
    subscription_status: SubscriptionStatus | None = None
    pause_start: date | None = None
    pause_end: date | None = None
    notes: str | None = None
    roles: list[RoleType] | None = None


class PersonResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: str | None
    phone: str | None
    phone_verified: bool
    skill_category: SkillCategory
    active: bool
    notification_preference: NotificationPreference
    notification_detail_level: NotificationDetailLevel
    subscription_status: SubscriptionStatus
    pause_start: date | None
    pause_end: date | None
    notes: str | None
    roles: list[RoleType]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PersonListResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    skill_category: SkillCategory
    active: bool
    roles: list[RoleType]

    model_config = {"from_attributes": True}
