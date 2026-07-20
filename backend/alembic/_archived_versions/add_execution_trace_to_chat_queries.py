"""Add execution_trace to chat_queries

Revision ID: add_execution_trace
Revises: add_files_table
Create Date: 2025-12-02 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_execution_trace'
down_revision = 'add_custom_agents'  # Linear chain: add_files_table -> add_custom_agents -> add_execution_trace
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add execution_trace column to chat_queries table
    op.add_column(
        'chat_queries',
        sa.Column('execution_trace', postgresql.JSONB, nullable=True)
    )


def downgrade() -> None:
    # Remove execution_trace column
    op.drop_column('chat_queries', 'execution_trace')
