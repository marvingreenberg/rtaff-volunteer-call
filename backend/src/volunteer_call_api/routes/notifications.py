"""Notification endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from volunteer_call_api.database import get_db
from volunteer_call_api.dependencies import get_current_user
from volunteer_call_api.models.notification import Notification
from volunteer_call_api.models.person import Person
from volunteer_call_api.schemas.notification import NotificationResponse, UnreadCountResponse

router = APIRouter()


@router.get("")
async def list_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: Person = Depends(get_current_user),
) -> list[NotificationResponse]:
    result = await db.execute(
        select(Notification)
        .where(Notification.person_id == current_user.id)
        .order_by(Notification.created_at.desc())
    )
    return [NotificationResponse.model_validate(n) for n in result.scalars().all()]


@router.get("/unread-count")
async def unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: Person = Depends(get_current_user),
) -> UnreadCountResponse:
    result = await db.execute(
        select(func.count())
        .select_from(Notification)
        .where(Notification.person_id == current_user.id)
        .where(Notification.read == False)  # noqa: E712
    )
    return UnreadCountResponse(count=result.scalar() or 0)


@router.patch("/{notification_id}/read")
async def mark_read(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Person = Depends(get_current_user),
) -> NotificationResponse:
    result = await db.execute(
        select(Notification)
        .where(Notification.id == notification_id)
        .where(Notification.person_id == current_user.id)
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.read = True
    await db.commit()
    await db.refresh(notification)
    return NotificationResponse.model_validate(notification)
