"""add_executive_fields

Revision ID: a1b2c3d4e5f6
Revises: f46f81c8e28b
Create Date: 2026-06-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f46f81c8e28b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # projects — executive fields
    op.add_column('projects', sa.Column('strategic', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('projects', sa.Column('quarter', sa.String(length=20), nullable=True))
    op.add_column('projects', sa.Column('owner', sa.String(length=100), nullable=True))
    op.add_column('projects', sa.Column('strategic_priority', sa.Integer(), nullable=False, server_default='0'))

    # missions — executive fields
    op.add_column('missions', sa.Column(
        'impact_level',
        sa.Enum('critical', 'high', 'medium', 'low', name='impactlevel'),
        nullable=False, server_default='medium'
    ))
    op.add_column('missions', sa.Column(
        'urgency',
        sa.Enum('critical', 'high', 'medium', 'low', name='urgencylevel'),
        nullable=False, server_default='medium'
    ))
    op.add_column('missions', sa.Column('weekly_focus', sa.Boolean(), nullable=False, server_default='0'))

    # tasks — executive fields
    op.add_column('tasks', sa.Column(
        'cognitive_load',
        sa.Enum('low', 'medium', 'high', 'deep', 'pressure', name='cognitiveload'),
        nullable=False, server_default='medium'
    ))
    op.add_column('tasks', sa.Column('financial_impact', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('tasks', sa.Column('operational_risk', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('tasks', sa.Column('strategic_impact', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('tasks', sa.Column('task_urgency', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('tasks', sa.Column('effort', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('tasks', sa.Column('priority_score', sa.Float(), nullable=False, server_default='0.0'))
    op.create_index(op.f('ix_tasks_priority_score'), 'tasks', ['priority_score'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_tasks_priority_score'), table_name='tasks')
    op.drop_column('tasks', 'priority_score')
    op.drop_column('tasks', 'effort')
    op.drop_column('tasks', 'task_urgency')
    op.drop_column('tasks', 'strategic_impact')
    op.drop_column('tasks', 'operational_risk')
    op.drop_column('tasks', 'financial_impact')
    op.drop_column('tasks', 'cognitive_load')
    op.drop_column('missions', 'weekly_focus')
    op.drop_column('missions', 'urgency')
    op.drop_column('missions', 'impact_level')
    op.drop_column('projects', 'strategic_priority')
    op.drop_column('projects', 'owner')
    op.drop_column('projects', 'quarter')
    op.drop_column('projects', 'strategic')
