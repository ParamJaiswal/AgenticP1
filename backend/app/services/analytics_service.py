"""Analytics service — per-tenant call metrics."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.call import Call

log = structlog.get_logger()


class AnalyticsService:
    """Compute call metrics from stored data."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_dashboard_stats(self, organization_id: str) -> dict[str, Any]:
        """Main dashboard statistics."""
        today = datetime.utcnow().date()
        today_start = datetime.combine(today, datetime.min.time())
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)

        # Calls today
        calls_today_q = await self._db.execute(
            select(func.count(Call.id)).where(
                Call.organization_id == organization_id,
                Call.created_at >= today_start,
            )
        )
        calls_today = calls_today_q.scalar() or 0

        # Active calls (in-progress)
        active_q = await self._db.execute(
            select(func.count(Call.id)).where(
                Call.organization_id == organization_id,
                Call.status == "active",
            )
        )
        active_calls = active_q.scalar() or 0

        # Avg duration (seconds) for completed calls this month
        avg_dur_q = await self._db.execute(
            select(func.avg(Call.duration_seconds)).where(
                Call.organization_id == organization_id,
                Call.status == "completed",
                Call.created_at >= month_start,
            )
        )
        avg_duration = int(avg_dur_q.scalar() or 0)

        # Resolution rate this month
        total_q = await self._db.execute(
            select(func.count(Call.id)).where(
                Call.organization_id == organization_id,
                Call.created_at >= month_start,
                Call.status == "completed",
            )
        )
        total = total_q.scalar() or 0

        resolved_q = await self._db.execute(
            select(func.count(Call.id)).where(
                Call.organization_id == organization_id,
                Call.created_at >= month_start,
                Call.resolution == "resolved",
            )
        )
        resolved = resolved_q.scalar() or 0
        resolution_rate = round((resolved / total * 100) if total > 0 else 0, 1)

        # Minutes used this month
        minutes_q = await self._db.execute(
            select(func.sum(Call.duration_seconds)).where(
                Call.organization_id == organization_id,
                Call.created_at >= month_start,
            )
        )
        minutes_used = int((minutes_q.scalar() or 0) / 60)

        return {
            "calls_today": calls_today,
            "active_calls": active_calls,
            "avg_duration_seconds": avg_duration,
            "resolution_rate_percent": resolution_rate,
            "minutes_used_this_month": minutes_used,
        }

    async def get_call_volume_chart(
        self, organization_id: str, days: int = 30
    ) -> list[dict]:
        """Call volume per day for the last N days."""
        since = datetime.utcnow() - timedelta(days=days)

        result = await self._db.execute(
            select(
                func.date(Call.created_at).label("date"),
                func.count(Call.id).label("count"),
            )
            .where(
                Call.organization_id == organization_id,
                Call.created_at >= since,
            )
            .group_by(func.date(Call.created_at))
            .order_by(func.date(Call.created_at))
        )
        rows = result.fetchall()
        return [{"date": str(row.date), "calls": row.count} for row in rows]

    async def get_sentiment_distribution(self, organization_id: str) -> dict[str, int]:
        """Count of positive/neutral/negative calls."""
        result = await self._db.execute(
            select(Call.sentiment_label, func.count(Call.id).label("count"))
            .where(
                Call.organization_id == organization_id,
                Call.sentiment_label.is_not(None),
            )
            .group_by(Call.sentiment_label)
        )
        rows = result.fetchall()
        return {row.sentiment_label: row.count for row in rows}

    async def get_recent_calls(
        self, organization_id: str, limit: int = 20, offset: int = 0
    ) -> list[dict]:
        """Paginated recent calls."""
        result = await self._db.execute(
            select(Call)
            .where(Call.organization_id == organization_id)
            .order_by(Call.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        calls = result.scalars().all()
        return [self._call_to_dict(c) for c in calls]

    def _call_to_dict(self, call: Call) -> dict[str, Any]:
        return {
            "id": call.id,
            "direction": call.direction,
            "caller_number": call.caller_number,
            "called_number": call.called_number,
            "status": call.status,
            "duration_seconds": call.duration_seconds,
            "sentiment_label": call.sentiment_label,
            "sentiment_score": call.sentiment_score,
            "resolution": call.resolution,
            "summary": call.summary,
            "created_at": call.created_at.isoformat() if call.created_at else None,
        }
