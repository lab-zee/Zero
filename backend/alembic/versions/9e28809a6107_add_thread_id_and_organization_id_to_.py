"""Add thread_id and organization_id to chat_queries, create threads table

Revision ID: 9e28809a6107
Revises: 
Create Date: 2025-11-19 04:28:58.639550

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '9e28809a6107'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Check if threads table exists
    tables = inspector.get_table_names()
    columns = [col['name'] for col in inspector.get_columns('chat_queries')] if 'chat_queries' in tables else []
    
    # Create threads table if it doesn't exist
    if 'threads' not in tables:
        op.create_table(
            'threads',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('organization_id', sa.Integer(), nullable=False),
            sa.Column('title', sa.String(), nullable=True),
            sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_threads_id'), 'threads', ['id'], unique=False)
        op.create_index(op.f('ix_threads_organization_id'), 'threads', ['organization_id'], unique=False)
        op.create_index(op.f('ix_threads_user_id'), 'threads', ['user_id'], unique=False)
    
    # Add organization_id column to chat_queries if it doesn't exist
    if 'organization_id' not in columns:
        op.add_column('chat_queries', sa.Column('organization_id', sa.Integer(), nullable=True))
        op.create_index(op.f('ix_chat_queries_organization_id'), 'chat_queries', ['organization_id'], unique=False)
        # Check if foreign key already exists
        fk_constraints = [fk['name'] for fk in inspector.get_foreign_keys('chat_queries')]
        if 'chat_queries_organization_id_fkey' not in fk_constraints:
            op.create_foreign_key('chat_queries_organization_id_fkey', 'chat_queries', 'organizations', ['organization_id'], ['id'])
    
    # Add thread_id column to chat_queries if it doesn't exist
    if 'thread_id' not in columns:
        op.add_column('chat_queries', sa.Column('thread_id', sa.Integer(), nullable=True))
        op.create_index(op.f('ix_chat_queries_thread_id'), 'chat_queries', ['thread_id'], unique=False)
        # Check if foreign key already exists
        fk_constraints = [fk['name'] for fk in inspector.get_foreign_keys('chat_queries')]
        if 'chat_queries_thread_id_fkey' not in fk_constraints:
            op.create_foreign_key('chat_queries_thread_id_fkey', 'chat_queries', 'threads', ['thread_id'], ['id'])
    
    # Handle existing data: create threads for existing queries
    # First, set organization_id for existing queries if they don't have one
    # (This assumes queries might have been created before organizations existed)
    op.execute("""
        UPDATE chat_queries 
        SET organization_id = (
            SELECT id FROM organizations LIMIT 1
        )
        WHERE organization_id IS NULL
        AND EXISTS (SELECT 1 FROM organizations);
    """)
    
    # Create a default thread for each user-organization pair that has queries
    op.execute("""
        INSERT INTO threads (user_id, organization_id, title, created_at)
        SELECT DISTINCT 
            cq.user_id,
            cq.organization_id,
            'Default Thread' as title,
            MIN(cq.created_at) as created_at
        FROM chat_queries cq
        WHERE cq.thread_id IS NULL
        AND cq.organization_id IS NOT NULL
        GROUP BY cq.user_id, cq.organization_id;
    """)
    
    # Assign existing queries to their corresponding threads
    op.execute("""
        UPDATE chat_queries cq
        SET thread_id = t.id
        FROM threads t
        WHERE cq.thread_id IS NULL
        AND cq.user_id = t.user_id
        AND cq.organization_id = t.organization_id;
    """)
    
    # Now make the columns NOT NULL
    op.alter_column('chat_queries', 'thread_id',
                   existing_type=sa.INTEGER(),
                   nullable=False)
    op.alter_column('chat_queries', 'organization_id',
                   existing_type=sa.INTEGER(),
                   nullable=False)


def downgrade() -> None:
    # Remove foreign keys and indexes first
    op.drop_constraint('chat_queries_thread_id_fkey', 'chat_queries', type_='foreignkey')
    op.drop_constraint('chat_queries_organization_id_fkey', 'chat_queries', type_='foreignkey')
    op.drop_index(op.f('ix_chat_queries_thread_id'), table_name='chat_queries')
    op.drop_index(op.f('ix_chat_queries_organization_id'), table_name='chat_queries')
    
    # Drop columns
    op.drop_column('chat_queries', 'thread_id')
    op.drop_column('chat_queries', 'organization_id')
    
    # Drop threads table
    op.drop_index(op.f('ix_threads_user_id'), table_name='threads')
    op.drop_index(op.f('ix_threads_organization_id'), table_name='threads')
    op.drop_index(op.f('ix_threads_id'), table_name='threads')
    op.drop_table('threads')

