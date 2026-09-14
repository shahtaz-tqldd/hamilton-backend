"""Group environment variables into named sets."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260914_0002"
down_revision = "20260911_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "env_variable_entries",
        sa.Column("env_variable_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(255), nullable=False),
        sa.Column("encrypted_value", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["env_variable_id"],
            ["env_variables.id"],
            ondelete="CASCADE",
            name="fk_env_variable_entries_env_variable_id_env_variables",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_env_variable_entries"),
        sa.UniqueConstraint("env_variable_id", "key", name="uq_env_variable_entries_group_key"),
    )
    op.create_index(
        "ix_env_variable_entries_env_variable_id",
        "env_variable_entries",
        ["env_variable_id"],
    )

    op.execute(
        """
        INSERT INTO env_variable_entries (id, env_variable_id, key, encrypted_value, position)
        SELECT id, id, key, encrypted_value, 0
        FROM env_variables
        """
    )
    op.drop_constraint("uq_env_variables_folder_key", "env_variables", type_="unique")
    op.alter_column("env_variables", "key", new_column_name="name")
    op.drop_column("env_variables", "encrypted_value")
    op.create_unique_constraint(
        "uq_env_variables_folder_name", "env_variables", ["folder_id", "name"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_env_variables_folder_name", "env_variables", type_="unique")
    op.add_column("env_variables", sa.Column("encrypted_value", sa.Text(), nullable=True))
    op.execute(
        """
        UPDATE env_variables AS groups
        SET encrypted_value = entries.encrypted_value
        FROM (
            SELECT DISTINCT ON (env_variable_id) env_variable_id, encrypted_value
            FROM env_variable_entries
            ORDER BY env_variable_id, position
        ) AS entries
        WHERE groups.id = entries.env_variable_id
        """
    )
    op.alter_column("env_variables", "encrypted_value", existing_type=sa.Text(), nullable=False)
    op.alter_column("env_variables", "name", new_column_name="key")
    op.create_unique_constraint(
        "uq_env_variables_folder_key", "env_variables", ["folder_id", "key"]
    )
    op.drop_index("ix_env_variable_entries_env_variable_id", table_name="env_variable_entries")
    op.drop_table("env_variable_entries")
