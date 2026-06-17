"""add_deadline_to_missions_tasks

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-15 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('missions', sa.Column('deadline', sa.DateTime(), nullable=True))
    op.add_column('tasks', sa.Column('deadline', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('tasks', 'deadline')
    op.drop_column('missions', 'deadline')
