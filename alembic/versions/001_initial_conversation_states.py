"""Initial conversation_states table

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create conversation_states table
    op.create_table(
        "conversation_states",
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("state_json", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("session_id"),
    )
    op.create_index(
        op.f("ix_conversation_states_session_id"),
        "conversation_states",
        ["session_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_conversation_states_session_id"), table_name="conversation_states")
    op.drop_table("conversation_states")
