"""Add usage logs table

Revision ID: add_usage_logs
Revises: 
Create Date: 2025-01-02 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_usage_logs'
down_revision = 'add_execution_trace'  # Chain: add_deleted_at_threads -> add_files_table -> add_custom_agents -> add_execution_trace -> add_usage_logs
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Check if usage_logs table exists
    tables = inspector.get_table_names()
    if 'usage_logs' not in tables:
        op.create_table(
            'usage_logs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('endpoint', sa.String(), nullable=False),
            sa.Column('method', sa.String(), nullable=False),
            sa.Column('authenticated_via', sa.String(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
    
    # Check if indexes exist before creating them
    if 'usage_logs' in tables:
        indexes = [idx['name'] for idx in inspector.get_indexes('usage_logs')]
        if 'ix_usage_logs_user_id' not in indexes:
            op.create_index(op.f('ix_usage_logs_user_id'), 'usage_logs', ['user_id'], unique=False)
        if 'ix_usage_logs_created_at' not in indexes:
            op.create_index(op.f('ix_usage_logs_created_at'), 'usage_logs', ['created_at'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_usage_logs_created_at'), table_name='usage_logs')
    op.drop_index(op.f('ix_usage_logs_user_id'), table_name='usage_logs')
    op.drop_table('usage_logs')

