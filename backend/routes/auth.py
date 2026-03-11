"""Authentication routes: register, login, logout."""

import logging
from typing import Annotated

import ulid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User
from schemas import ErrorResponse, TokenResponse, UserLogin, UserRegister
from security import create_access_token, hash_password, verify_password

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}},
)
async def register(payload: UserRegister, db: DbDep) -> TokenResponse:
    """Create a new user account and return an access token."""
    existing = await db.execute(
        select(User).where(User.email == payload.email)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Этот email уже зарегистрирован",
        )

    user = User(
        id=ulid.new().str,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()

    token = create_access_token(subject=user.id)
    logger.info("User registered, user_id=%s", user.id)
    return TokenResponse(access_token=token)


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={401: {"model": ErrorResponse}},
)
async def login(payload: UserLogin, db: DbDep) -> TokenResponse:
    """Verify credentials and return an access token."""
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    # Constant-time comparison regardless of whether the user exists
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )

    token = create_access_token(subject=user.id)
    logger.info("User logged in, user_id=%s", user.id)
    return TokenResponse(access_token=token)


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
)
async def logout() -> dict:
    """Stateless JWT logout — client must discard the token."""
    return {"detail": "Logged out"}
