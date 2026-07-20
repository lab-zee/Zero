"""Add files table and associations

Revision ID: add_files_table
Revises: add_deleted_at_threads
Create Date: 2025-01-20 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_files_table'
down_revision = 'add_deleted_at_threads'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    # Create files table if it doesn't exist
    if 'files' not in tables:
        op.create_table(
            'files',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('organization_id', sa.Integer(), nullable=False),
            sa.Column('filename', sa.String(), nullable=False),
            sa.Column('original_filename', sa.String(), nullable=False),
            sa.Column('file_path', sa.String(), nullable=False),
            sa.Column('content_type', sa.String(), nullable=True),
            sa.Column('file_size', sa.Integer(), nullable=False),
            sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_files_id'), 'files', ['id'], unique=False)
        op.create_index(op.f('ix_files_organization_id'), 'files', ['organization_id'], unique=False)
        op.create_index(op.f('ix_files_user_id'), 'files', ['user_id'], unique=False)
    
    # Create chat_query_files association table if it doesn't exist
    if 'chat_query_files' not in tables:
        op.create_table(
            'chat_query_files',
            sa.Column('chat_query_id', sa.Integer(), nullable=False),
            sa.Column('file_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['chat_query_id'], ['chat_queries.id'], ),
            sa.ForeignKeyConstraint(['file_id'], ['files.id'], ),
            sa.PrimaryKeyConstraint('chat_query_id', 'file_id')
        )


def downgrade() -> None:
    # Drop association table
    op.drop_table('chat_query_files')
    
    # Drop files table
    op.drop_index(op.f('ix_files_user_id'), table_name='files')
    op.drop_index(op.f('ix_files_organization_id'), table_name='files')
    op.drop_index(op.f('ix_files_id'), table_name='files')
    op.drop_table('files')

