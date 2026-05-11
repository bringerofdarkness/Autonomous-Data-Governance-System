"""add paused document status

Revision ID: ff872e8fd29c
Revises: 1ce31578702e
Create Date: 2026-05-10 04:45:55.533600

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ff872e8fd29c'
down_revision: Union[str, None] = '1ce31578702e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute("ALTER TYPE document_status ADD VALUE IF NOT EXISTS 'PAUSED'")


def downgrade() -> None:
    pass