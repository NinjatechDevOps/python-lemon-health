"""Add DEFAULT to PromptType enum

Revision ID: 54a05f5e2ebd
Revises: a647a8b355c8
Create Date: 2025-08-05 13:22:09.185688

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '54a05f5e2ebd'
down_revision: Union[str, Sequence[str], None] = 'a647a8b355c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add 'DEFAULT' to the prompttype enum
    op.execute("ALTER TYPE prompttype ADD VALUE 'DEFAULT'")


def downgrade() -> None:
    """Downgrade schema."""
    # Note: PostgreSQL doesn't support removing enum values directly
    # This would require recreating the enum, which is complex
    # For now, we'll leave the DEFAULT value in place
    pass
