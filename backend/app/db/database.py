"""Database connection and session management."""

from collections.abc import AsyncGenerator

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import settings

log = structlog.get_logger()


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all models."""


# Build engine kwargs based on database type
_engine_kwargs: dict = {
    "echo": settings.DEBUG,
}

if settings.DATABASE_URL.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency: yields an async DB session and ensures cleanup."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Create all tables on startup."""
    # Import all models so they are registered with Base
    from app.models import agent_config, call, conversation, knowledge, user  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info("Database tables created/verified")


async def check_db_connection() -> bool:
    """Verify the database is reachable."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        log.error("Database connection failed", error=str(exc))
        return False
