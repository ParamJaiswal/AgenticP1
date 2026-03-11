"""Auth routes — register, login, API keys."""

from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from slugify import slugify
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.auth_middleware import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.db.database import get_db
from app.models.database import Organization
from app.models.user import User

router = APIRouter()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    organization_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    organization_id: str
    role: str


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    body: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Register a new user and create their organization."""
    # Check email uniqueness
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create organization
    slug = slugify(body.organization_name)
    # Ensure slug is unique
    base_slug = slug
    counter = 1
    while True:
        existing_org = await db.execute(
            select(Organization).where(Organization.slug == slug)
        )
        if not existing_org.scalar_one_or_none():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1

    org = Organization(name=body.organization_name, slug=slug)
    db.add(org)
    await db.flush()

    # Create user (admin of new org)
    user = User(
        organization_id=org.id,
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role="admin",
    )
    db.add(user)
    await db.flush()

    token = create_access_token(user.id, org.id, user.role)
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        organization_id=org.id,
        role=user.role,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Login and receive a JWT access token."""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    token = create_access_token(user.id, user.organization_id, user.role)
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        organization_id=user.organization_id,
        role=user.role,
    )


@router.post("/api-key")
async def generate_api_key(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Generate a new API key for the authenticated user."""
    new_key = f"ak_{secrets.token_hex(28)}"
    current_user.api_key = new_key
    db.add(current_user)
    return {"api_key": new_key}


@router.delete("/api-key")
async def revoke_api_key(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Revoke the current API key."""
    current_user.api_key = None
    db.add(current_user)
    return {"message": "API key revoked"}


@router.get("/me")
async def get_me(current_user: Annotated[User, Depends(get_current_user)]) -> dict:
    """Return current user profile."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "organization_id": current_user.organization_id,
        "has_api_key": current_user.api_key is not None,
    }
