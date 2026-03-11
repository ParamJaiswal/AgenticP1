"""Billing service — usage metering + Stripe integration ready."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.call import Call
from app.models.database import Organization

log = structlog.get_logger()

PLAN_LIMITS = {
    "starter": {"minutes": 500, "agents": 1, "knowledge_docs": 10},
    "growth": {"minutes": 2000, "agents": 5, "knowledge_docs": 50},
    "pro": {"minutes": 10000, "agents": 20, "knowledge_docs": 200},
    "enterprise": {"minutes": -1, "agents": -1, "knowledge_docs": -1},  # unlimited
}

PLAN_PRICES = {
    "starter": 49,
    "growth": 149,
    "pro": 399,
    "enterprise": 999,
}


class BillingService:
    """Track usage and enforce plan limits."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_usage(self, organization_id: str) -> dict[str, Any]:
        """Get current month usage for an organization."""
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)

        # Minutes used
        result = await self._db.execute(
            select(func.sum(Call.duration_seconds)).where(
                Call.organization_id == organization_id,
                Call.created_at >= month_start,
                Call.status == "completed",
            )
        )
        seconds_used = result.scalar() or 0
        minutes_used = int(seconds_used / 60)

        # Get org plan
        org_result = await self._db.execute(
            select(Organization).where(Organization.id == organization_id)
        )
        org = org_result.scalar_one_or_none()
        plan = org.plan if org else "starter"
        limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["starter"])

        return {
            "plan": plan,
            "plan_price_usd": PLAN_PRICES.get(plan, 49),
            "minutes_used": minutes_used,
            "minutes_limit": limits["minutes"],
            "minutes_remaining": max(0, limits["minutes"] - minutes_used)
            if limits["minutes"] > 0
            else -1,
            "overage_minutes": max(0, minutes_used - limits["minutes"])
            if limits["minutes"] > 0
            else 0,
        }

    async def check_can_make_call(self, organization_id: str) -> tuple[bool, str]:
        """Check if the organization can make another call."""
        usage = await self.get_usage(organization_id)
        if usage["minutes_limit"] < 0:
            return True, ""  # Unlimited

        if usage["minutes_remaining"] <= 0:
            return False, (
                f"Monthly limit of {usage['minutes_limit']} minutes reached. "
                "Please upgrade your plan."
            )
        return True, ""

    async def record_call_cost(
        self, call_id: str, duration_seconds: int, rate_per_minute: float = 0.005
    ) -> float:
        """Record cost for a completed call. Returns cost in USD."""
        cost = (duration_seconds / 60) * rate_per_minute

        from sqlalchemy import update

        await self._db.execute(
            update(Call).where(Call.id == call_id).values(cost_usd=cost)
        )
        await self._db.commit()
        return cost
