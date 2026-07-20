"""Add deleted_at to threads for soft delete

Revision ID: add_deleted_at_threads
Revises: 9e28809a6107
Create Date: 2025-01-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_deleted_at_threads'
down_revision = '9e28809a6107'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Check if threads table exists and get its columns
    tables = inspector.get_table_names()
    if 'threads' in tables:
        columns = [col['name'] for col in inspector.get_columns('threads')]
        
        # Add deleted_at column if it doesn't exist
        if 'deleted_at' not in columns:
            op.add_column('threads', sa.Column('deleted_at', postgresql.TIMESTAMP(timezone=True), nullable=True))
        
        # Create index if it doesn't exist
        indexes = [idx['name'] for idx in inspector.get_indexes('threads')]
        if 'ix_threads_deleted_at' not in indexes:
            op.create_index(op.f('ix_threads_deleted_at'), 'threads', ['deleted_at'], unique=False)


def downgrade() -> None:
    # Remove index and column
    op.drop_index(op.f('ix_threads_deleted_at'), table_name='threads')
    op.drop_column('threads', 'deleted_at')

