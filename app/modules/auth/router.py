from datetime import timedelta

import jwt
from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from sqlalchemy import select

from app.core.config import settings
from app.core.security import create_token, hash_password, verify_password
from app.db.models import Folder, User
from app.dependencies import CurrentUser, DbSession
from app.modules.auth.schemas import (
    EmailRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenPair,
    UserResponse,
    VerifyOTPRequest,
)
from app.modules.auth.service import change_password, consume_otp, create_otp
from app.schemas.common import Message
from app.services.email import email_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


def token_pair(user: User) -> TokenPair:
    return TokenPair(
        access_token=create_token(
            str(user.id), "access", timedelta(minutes=settings.access_token_expire_minutes)
        ),
        refresh_token=create_token(
            str(user.id), "refresh", timedelta(days=settings.refresh_token_expire_days)
        ),
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: DbSession, background_tasks: BackgroundTasks) -> User:
    email = body.email.lower()
    if await db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = User(
        email=email,
        full_name=body.full_name.strip(),
        password_hash=hash_password(body.password),
    )
    db.add(user)
    await db.flush()
    db.add(Folder(user_id=user.id, name="Default", is_default=True))
    code = await create_otp(db, user, "email_verification")
    await db.commit()
    await db.refresh(user)
    background_tasks.add_task(email_service.send_otp, user.email, code, "email_verification")
    return user


@router.post("/login", response_model=TokenPair)
async def login(body: LoginRequest, db: DbSession) -> TokenPair:
    user = await db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email is not verified")
    return token_pair(user)


@router.post("/verify-otp", response_model=Message)
async def verify_otp(body: VerifyOTPRequest, db: DbSession) -> Message:
    user = await db.scalar(select(User).where(User.email == body.email.lower()))
    valid = user is not None and await consume_otp(db, user, "email_verification", body.code)
    if not valid:
        await db.commit()  # persist a failed-attempt counter when an OTP was found
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    assert user is not None
    user.is_verified = True
    await db.commit()
    return Message(message="OTP verified")


@router.post("/resend-verification", response_model=Message)
async def resend_verification(
    body: EmailRequest, db: DbSession, background_tasks: BackgroundTasks
) -> Message:
    user = await db.scalar(select(User).where(User.email == body.email.lower()))
    if user and not user.is_verified:
        code = await create_otp(db, user, "email_verification")
        await db.commit()
        background_tasks.add_task(email_service.send_otp, user.email, code, "email_verification")
    return Message(message="If the account exists, a verification code has been sent")


@router.post("/forgot-password", response_model=Message)
async def forgot_password(
    body: EmailRequest, db: DbSession, background_tasks: BackgroundTasks
) -> Message:
    user = await db.scalar(select(User).where(User.email == body.email.lower()))
    if user and user.is_active:
        code = await create_otp(db, user, "password_reset")
        await db.commit()
        background_tasks.add_task(email_service.send_otp, user.email, code, "password_reset")
    return Message(message="If the account exists, a password reset code has been sent")


@router.post("/reset-password", response_model=Message)
async def reset_password(body: ResetPasswordRequest, db: DbSession) -> Message:
    user = await db.scalar(select(User).where(User.email == body.email.lower()))
    valid = user is not None and await consume_otp(db, user, "password_reset", body.code)
    if not valid:
        await db.commit()  # persist a failed-attempt counter when an OTP was found
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    assert user is not None
    await change_password(db, user, body.new_password)
    await db.commit()
    return Message(message="Password reset successfully")


@router.post("/refresh", response_model=TokenPair)
async def refresh(body: RefreshRequest, db: DbSession) -> TokenPair:
    from app.core.security import decode_token

    try:
        payload = decode_token(body.refresh_token, "refresh")
        from uuid import UUID

        user = await db.get(User, UUID(payload["sub"]))
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid refresh token") from None
    if not user or not user.is_active or not user.is_verified:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    return token_pair(user)


@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUser) -> User:
    return user
