"""Add answer_mode fields to threads and chat_queries for verbosity control

Revision ID: add_answer_modes
Revises: add_thread_metadata
Create Date: 2026-01-23 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_answer_modes'
down_revision = 'add_thread_metadata'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Check if threads table exists and get its columns
    tables = inspector.get_table_names()
    if 'threads' in tables:
        columns = [col['name'] for col in inspector.get_columns('threads')]

        # Add default_answer_mode column if it doesn't exist
        if 'default_answer_mode' not in columns:
            op.add_column('threads', sa.Column(
                'default_answer_mode',
                sa.String(20),
                nullable=False,
                server_default='light'
            ))

    # Check if chat_queries table exists and get its columns
    if 'chat_queries' in tables:
        columns = [col['name'] for col in inspector.get_columns('chat_queries')]

        # Add answer_mode column if it doesn't exist
        if 'answer_mode' not in columns:
            op.add_column('chat_queries', sa.Column(
                'answer_mode',
                sa.String(20),
                nullable=False,
                server_default='light'
            ))

        # Add reask_of_query_id column if it doesn't exist
        if 'reask_of_query_id' not in columns:
            op.add_column('chat_queries', sa.Column(
                'reask_of_query_id',
                sa.Integer(),
                nullable=True
            ))
            # Add foreign key constraint
            op.create_foreign_key(
                'fk_chat_queries_reask_of_query_id',
                'chat_queries',
                'chat_queries',
                ['reask_of_query_id'],
                ['id']
            )


def downgrade() -> None:
    # Remove columns in reverse order
    op.drop_constraint('fk_chat_queries_reask_of_query_id', 'chat_queries', type_='foreignkey')
    op.drop_column('chat_queries', 'reask_of_query_id')
    op.drop_column('chat_queries', 'answer_mode')
    op.drop_column('threads', 'default_answer_mode')
