"""create rag search audit logs

Revision ID: 2f4c1d9e8a7b
Revises: ff872e8fd29c
Create Date: 2026-05-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "2f4c1d9e8a7b"
down_revision: Union[str, None] = "ff872e8fd29c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rag_search_audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "actor_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("result_limit", sa.Integer(), nullable=False),
        sa.Column("min_score", sa.Float(), nullable=False),
        sa.Column("matches_count", sa.Integer(), nullable=False),
        sa.Column("matched_document_ids", postgresql.JSONB(), nullable=False),
        sa.Column("matched_point_ids", postgresql.JSONB(), nullable=False),
        sa.Column("extra_data", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_rag_search_audit_logs_actor_user_id",
        "rag_search_audit_logs",
        ["actor_user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_rag_search_audit_logs_actor_user_id",
        table_name="rag_search_audit_logs",
    )
    op.drop_table("rag_search_audit_logs")
