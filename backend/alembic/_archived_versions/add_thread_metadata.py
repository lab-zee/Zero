"""Add thread_metadata to threads for thread-level preferences

Revision ID: add_thread_metadata
Revises: add_deleted_at_threads
Create Date: 2024-12-02 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_thread_metadata'
down_revision = 'add_usage_logs'  # Chain: add_deleted_at_threads -> add_files_table -> add_custom_agents -> add_execution_trace -> add_usage_logs -> add_thread_metadata
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Check if threads table exists and get its columns
    tables = inspector.get_table_names()
    if 'threads' in tables:
        columns = [col['name'] for col in inspector.get_columns('threads')]
        
        # Add thread_metadata column if it doesn't exist
        if 'thread_metadata' not in columns:
            op.add_column('threads', sa.Column('thread_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    # Remove column
    op.drop_column('threads', 'thread_metadata')


