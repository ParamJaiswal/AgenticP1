"""AgenticP1 — AI Calling Agent Platform — Backend Entry Point."""

import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api.routes import agents, analytics, auth, calls, knowledge, webhooks
from app.db.database import init_db
from config import settings

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

log = structlog.get_logger()

app = FastAPI(
    title="AgenticP1 — AI Calling Agent Platform",
    description="Enterprise-grade AI Voice Calling Agent SaaS. Multi-tenant, ultra-low cost.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.TRUSTED_HOSTS:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.TRUSTED_HOSTS,
    )

# Routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(calls.router, prefix="/api/v1/calls", tags=["Calls"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["Agents"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(
    knowledge.router, prefix="/api/v1/knowledge", tags=["Knowledge Base"]
)
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["Webhooks"])


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize database and services on startup."""
    log.info("Starting AgenticP1 backend", version="1.0.0")
    await init_db()
    log.info("Database initialized")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Clean up resources on shutdown."""
    log.info("Shutting down AgenticP1 backend")


@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """Basic health check — always returns 200 if app is running."""
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/ready", tags=["Health"])
async def readiness_check() -> dict:
    """Readiness check — verifies database and required services."""
    from app.db.database import check_db_connection

    db_ok = await check_db_connection()
    return {
        "status": "ready" if db_ok else "not_ready",
        "database": "ok" if db_ok else "error",
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info",
    )
