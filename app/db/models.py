from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    folders: Mapped[list["Folder"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class OTPCode(UUIDMixin, Base):
    __tablename__ = "otp_codes"
    __table_args__ = (Index("ix_otp_user_purpose", "user_id", "purpose"),)

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    purpose: Mapped[str] = mapped_column(String(32))
    code_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Folder(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "folders"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_folders_user_name"),)

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    user: Mapped[User] = relationship(back_populates="folders")
    snippets: Mapped[list["Snippet"]] = relationship(cascade="all, delete-orphan")
    env_variables: Mapped[list["EnvVariable"]] = relationship(cascade="all, delete-orphan")
    files: Mapped[list["StoredFile"]] = relationship(cascade="all, delete-orphan")


class Snippet(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "snippets"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    folder_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("folders.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    language: Mapped[str | None] = mapped_column(String(60), nullable=True)
    content: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class EnvVariable(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "env_variables"
    __table_args__ = (UniqueConstraint("folder_id", "key", name="uq_env_variables_folder_key"),)

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    folder_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("folders.id", ondelete="CASCADE"), index=True
    )
    key: Mapped[str] = mapped_column(String(255))
    encrypted_value: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class StoredFile(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "stored_files"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    folder_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("folders.id", ondelete="CASCADE"), index=True
    )
    original_name: Mapped[str] = mapped_column(String(255))
    object_key: Mapped[str] = mapped_column(String(1024), unique=True)
    content_type: Mapped[str] = mapped_column(String(255))
    size: Mapped[int] = mapped_column(BigInteger)
    checksum_sha256: Mapped[str] = mapped_column(String(64))
