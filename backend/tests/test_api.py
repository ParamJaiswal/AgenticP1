"""Integration tests for API routes."""

from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport

from main import app


@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    """Health check should return 200."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_openapi_docs_available() -> None:
    """OpenAPI docs should be accessible."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "paths" in schema


@pytest.mark.asyncio
async def test_register_and_login() -> None:
    """Full auth flow: register, then login."""

    # Use in-memory SQLite for test
    from config import settings

    original_db = settings.DATABASE_URL
    # Override for test
    settings.DATABASE_URL = "sqlite+aiosqlite:///:memory:"

    from app.db.database import engine, Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Register
        reg_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "securepass123",
                "full_name": "Test User",
                "organization_name": "Test Company",
            },
        )
        assert reg_response.status_code == 201
        token_data = reg_response.json()
        assert "access_token" in token_data

        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "securepass123"},
        )
        assert login_response.status_code == 200
        assert "access_token" in login_response.json()

        # Get me
        me_response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        assert me_response.status_code == 200
        assert me_response.json()["email"] == "test@example.com"

    settings.DATABASE_URL = original_db


@pytest.mark.asyncio
async def test_unauthenticated_calls_returns_401() -> None:
    """Unauthenticated requests to protected routes should return 401."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/calls/")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_unauthenticated_agents_returns_401() -> None:
    """Unauthenticated requests to agents route should return 401."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/agents/")
    assert response.status_code == 401
