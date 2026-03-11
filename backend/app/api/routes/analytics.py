"""Analytics routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.auth_middleware import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/dashboard")
async def dashboard_stats(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Dashboard statistics."""
    svc = AnalyticsService(db)
    return await svc.get_dashboard_stats(current_user.organization_id)


@router.get("/call-volume")
async def call_volume(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(30, ge=1, le=365),
) -> dict:
    """Call volume chart data."""
    svc = AnalyticsService(db)
    data = await svc.get_call_volume_chart(current_user.organization_id, days=days)
    return {"data": data, "period_days": days}


@router.get("/sentiment")
async def sentiment_distribution(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Sentiment distribution."""
    svc = AnalyticsService(db)
    data = await svc.get_sentiment_distribution(current_user.organization_id)
    return {"data": data}


@router.get("/billing")
async def billing_usage(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Current billing usage."""
    from app.services.billing_service import BillingService

    svc = BillingService(db)
    return await svc.get_usage(current_user.organization_id)
