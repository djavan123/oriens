"""add_context

Revision ID: f46f81c8e28b
Revises: 0001
Create Date: 2026-06-15 11:05:57.998191

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f46f81c8e28b'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('contexts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('type', sa.Enum('work', 'home_recovery', 'home_operational', 'gym', name='contexttype'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('type'),
    )
    op.create_index(op.f('ix_contexts_id'), 'contexts', ['id'], unique=False)
    op.add_column('missions', sa.Column('context_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_missions_context_id'), 'missions', ['context_id'], unique=False)
    op.add_column('projects', sa.Column('context_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_projects_context_id'), 'projects', ['context_id'], unique=False)
    op.add_column('tasks', sa.Column('context_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_tasks_context_id'), 'tasks', ['context_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_tasks_context_id'), table_name='tasks')
    op.drop_column('tasks', 'context_id')
    op.drop_index(op.f('ix_projects_context_id'), table_name='projects')
    op.drop_column('projects', 'context_id')
    op.drop_index(op.f('ix_missions_context_id'), table_name='missions')
    op.drop_column('missions', 'context_id')
    op.drop_index(op.f('ix_contexts_id'), table_name='contexts')
    op.drop_table('contexts')
