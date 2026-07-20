"""add_followup_of_query_id

Add followup_of_query_id column to chat_queries table for deep-dive
follow-up questions that carry the full parent analysis context.

Revision ID: add_followup_of_query_id
Revises: fix_json_column_types
Create Date: 2025-02-23

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_followup_of_query_id'
down_revision = 'fix_json_column_types'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if 'chat_queries' in inspector.get_table_names():
        columns = [c['name'] for c in inspector.get_columns('chat_queries')]
        if 'followup_of_query_id' not in columns:
            op.add_column('chat_queries',
                sa.Column('followup_of_query_id', sa.Integer(),
                          sa.ForeignKey('chat_queries.id'), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if 'chat_queries' in inspector.get_table_names():
        columns = [c['name'] for c in inspector.get_columns('chat_queries')]
        if 'followup_of_query_id' in columns:
            op.drop_column('chat_queries', 'followup_of_query_id')
