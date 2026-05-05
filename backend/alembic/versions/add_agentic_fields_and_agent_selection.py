"""add_agentic_fields_and_agent_selection

Add agentic capability fields to custom_agents (tools, can_delegate_to, model,
role, is_agentic, organization_id, shared_with_org), add selected_agent_ids to
threads, and add agent_ids_used to chat_queries.

Revision ID: add_agentic_fields
Revises: a723d9d31588
Create Date: 2025-02-16

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_agentic_fields'
down_revision = 'a723d9d31588'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # --- custom_agents table: add agentic fields ---
    if 'custom_agents' in inspector.get_table_names():
        columns = [c['name'] for c in inspector.get_columns('custom_agents')]

        if 'role' not in columns:
            op.add_column('custom_agents', sa.Column('role', sa.String(), nullable=True))
        if 'tools' not in columns:
            op.add_column('custom_agents', sa.Column('tools', sa.Text(), nullable=True))
        if 'can_delegate_to' not in columns:
            op.add_column('custom_agents', sa.Column('can_delegate_to', sa.Text(), nullable=True))
        if 'model' not in columns:
            op.add_column('custom_agents', sa.Column('model', sa.String(), nullable=True))
        if 'is_agentic' not in columns:
            op.add_column('custom_agents', sa.Column('is_agentic', sa.Boolean(), server_default='0', nullable=False))
        if 'organization_id' not in columns:
            op.add_column('custom_agents', sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id'), nullable=True))
            op.create_index('ix_custom_agents_organization_id', 'custom_agents', ['organization_id'], unique=False)
        if 'shared_with_org' not in columns:
            op.add_column('custom_agents', sa.Column('shared_with_org', sa.Boolean(), server_default='0', nullable=False))

    # --- threads table: add selected_agent_ids ---
    if 'threads' in inspector.get_table_names():
        columns = [c['name'] for c in inspector.get_columns('threads')]

        if 'selected_agent_ids' not in columns:
            op.add_column('threads', sa.Column('selected_agent_ids', sa.Text(), nullable=True))

    # --- chat_queries table: add agent_ids_used ---
    if 'chat_queries' in inspector.get_table_names():
        columns = [c['name'] for c in inspector.get_columns('chat_queries')]

        if 'agent_ids_used' not in columns:
            op.add_column('chat_queries', sa.Column('agent_ids_used', sa.Text(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # --- chat_queries: remove agent_ids_used ---
    if 'chat_queries' in inspector.get_table_names():
        columns = [c['name'] for c in inspector.get_columns('chat_queries')]
        if 'agent_ids_used' in columns:
            op.drop_column('chat_queries', 'agent_ids_used')

    # --- threads: remove selected_agent_ids ---
    if 'threads' in inspector.get_table_names():
        columns = [c['name'] for c in inspector.get_columns('threads')]
        if 'selected_agent_ids' in columns:
            op.drop_column('threads', 'selected_agent_ids')

    # --- custom_agents: remove agentic fields ---
    if 'custom_agents' in inspector.get_table_names():
        columns = [c['name'] for c in inspector.get_columns('custom_agents')]
        for col in ['shared_with_org', 'organization_id', 'is_agentic', 'model', 'can_delegate_to', 'tools', 'role']:
            if col in columns:
                if col == 'organization_id':
                    try:
                        op.drop_index('ix_custom_agents_organization_id', table_name='custom_agents')
                    except Exception:
                        pass
                op.drop_column('custom_agents', col)
