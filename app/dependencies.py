from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.models import Folder, User
from app.db.session import get_db

DbSession = Annotated[AsyncSession, Depends(get_db)]
bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not credentials:
        raise unauthorized
    try:
        payload = decode_token(credentials.credentials, "access")
        user_id = UUID(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise unauthorized from None
    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def owned_folder(db: AsyncSession, user: User, folder_id: UUID | None) -> Folder:
    if folder_id is None:
        from sqlalchemy import select

        folder = await db.scalar(
            select(Folder).where(Folder.user_id == user.id, Folder.is_default.is_(True))
        )
    else:
        folder = await db.get(Folder, folder_id)
    if not folder or folder.user_id != user.id:
        raise HTTPException(status_code=404, detail="Folder not found")
    return folder
