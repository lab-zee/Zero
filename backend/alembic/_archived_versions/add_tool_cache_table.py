"""add_tool_cache_table

Create tool_cache table for persistent caching of tool call results.

Revision ID: add_tool_cache_table
Revises: add_followup_of_query_id
Create Date: 2025-02-23

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_tool_cache_table'
down_revision = 'add_followup_of_query_id'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if 'tool_cache' not in inspector.get_table_names():
        op.create_table(
            'tool_cache',
            sa.Column('key', sa.String(), primary_key=True),
            sa.Column('tool_name', sa.String(), nullable=False, index=True),
            sa.Column('result', sa.Text(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False, index=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if 'tool_cache' in inspector.get_table_names():
        op.drop_table('tool_cache')
