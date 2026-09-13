import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.db.models import OTPCode, User

OTP_TTL_MINUTES = 10
OTP_MAX_ATTEMPTS = 5


def _otp_hash(user_id: object, purpose: str, code: str) -> str:
    return hmac.new(
        settings.secret_key.encode(),
        f"{user_id}:{purpose}:{code}".encode(),
        hashlib.sha256,
    ).hexdigest()


async def create_otp(db: AsyncSession, user: User, purpose: str) -> str:
    now = datetime.now(UTC)
    await db.execute(
        update(OTPCode)
        .where(
            OTPCode.user_id == user.id,
            OTPCode.purpose == purpose,
            OTPCode.consumed_at.is_(None),
        )
        .values(consumed_at=now)
    )
    code = f"{secrets.randbelow(1_000_000):06d}"
    db.add(
        OTPCode(
            user_id=user.id,
            purpose=purpose,
            code_hash=_otp_hash(user.id, purpose, code),
            expires_at=now + timedelta(minutes=OTP_TTL_MINUTES),
            created_at=now,
        )
    )
    await db.flush()
    return code


async def consume_otp(db: AsyncSession, user: User, purpose: str, code: str) -> bool:
    now = datetime.now(UTC)
    otp = await db.scalar(
        select(OTPCode)
        .where(
            OTPCode.user_id == user.id,
            OTPCode.purpose == purpose,
            OTPCode.consumed_at.is_(None),
        )
        .order_by(OTPCode.created_at.desc())
        .with_for_update()
    )
    if not otp or otp.expires_at <= now or otp.attempts >= OTP_MAX_ATTEMPTS:
        return False
    otp.attempts += 1
    if not secrets.compare_digest(otp.code_hash, _otp_hash(user.id, purpose, code)):
        await db.flush()
        return False
    otp.consumed_at = now
    await db.flush()
    return True


async def change_password(db: AsyncSession, user: User, password: str) -> None:
    user.password_hash = hash_password(password)
    await db.flush()
