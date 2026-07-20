"""add_custom_agents_table

Revision ID: add_custom_agents
Revises: add_files_table_and_associations
Create Date: 2024-01-XX XX:XX:XX.XXXXXX

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_custom_agents'
down_revision = 'add_files_table'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    # Create custom_agents table if it doesn't exist
    if 'custom_agents' not in tables:
        op.create_table(
            'custom_agents',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('system_prompt', sa.Text(), nullable=False),
            sa.Column('use_cases', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column('style', sa.String(), nullable=True),
            sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_custom_agents_id'), 'custom_agents', ['id'], unique=False)
        op.create_index(op.f('ix_custom_agents_user_id'), 'custom_agents', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_custom_agents_user_id'), table_name='custom_agents')
    op.drop_index(op.f('ix_custom_agents_id'), table_name='custom_agents')
    op.drop_table('custom_agents')

