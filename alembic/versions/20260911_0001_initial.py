"""Initial schema."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260911_0001"
down_revision = None
branch_labels = None
depends_on = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def owned_columns() -> list[sa.Column]:
    return [
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("folder_id", postgresql.UUID(as_uuid=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("full_name", sa.String(120), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("is_verified", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        *timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_table(
        "folders",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name="fk_folders_user_id_users",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_folders"),
        sa.UniqueConstraint("user_id", "name", name="uq_folders_user_name"),
    )
    op.create_index("ix_folders_user_id", "folders", ["user_id"])
    op.create_table(
        "otp_codes",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purpose", sa.String(32), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name="fk_otp_codes_user_id_users",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_otp_codes"),
    )
    op.create_index("ix_otp_codes_user_id", "otp_codes", ["user_id"])
    op.create_index("ix_otp_user_purpose", "otp_codes", ["user_id", "purpose"])

    definitions = {
        "snippets": [
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("language", sa.String(60)),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("description", sa.Text()),
        ],
        "env_variables": [
            sa.Column("key", sa.String(255), nullable=False),
            sa.Column("encrypted_value", sa.Text(), nullable=False),
            sa.Column("description", sa.Text()),
        ],
        "stored_files": [
            sa.Column("original_name", sa.String(255), nullable=False),
            sa.Column("object_key", sa.String(1024), nullable=False),
            sa.Column("content_type", sa.String(255), nullable=False),
            sa.Column("size", sa.BigInteger(), nullable=False),
            sa.Column("checksum_sha256", sa.String(64), nullable=False),
        ],
    }
    for table, specific in definitions.items():
        op.create_table(
            table,
            *owned_columns(),
            *specific,
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            *timestamps(),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["users.id"],
                ondelete="CASCADE",
                name=f"fk_{table}_user_id_users",
            ),
            sa.ForeignKeyConstraint(
                ["folder_id"],
                ["folders.id"],
                ondelete="CASCADE",
                name=f"fk_{table}_folder_id_folders",
            ),
            sa.PrimaryKeyConstraint("id", name=f"pk_{table}"),
        )
        op.create_index(f"ix_{table}_user_id", table, ["user_id"])
        op.create_index(f"ix_{table}_folder_id", table, ["folder_id"])
    op.create_unique_constraint(
        "uq_env_variables_folder_key", "env_variables", ["folder_id", "key"]
    )
    op.create_unique_constraint("uq_stored_files_object_key", "stored_files", ["object_key"])


def downgrade() -> None:
    for table in ("stored_files", "env_variables", "snippets", "otp_codes", "folders", "users"):
        op.drop_table(table)
