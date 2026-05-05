"""fix_json_column_types

Convert selected_agent_ids and agent_ids_used columns from Text to JSONB
so they match the JSON TypeDecorator's expected dialect implementation.
Without this, SQLAlchemy's JSONB bind processor serializes None to the
string 'null' which gets stored literally in a text column.

Revision ID: fix_json_column_types
Revises: add_agentic_fields
Create Date: 2025-02-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = 'fix_json_column_types'
down_revision = 'add_agentic_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Fix threads.selected_agent_ids: text -> jsonb
    if 'threads' in inspector.get_table_names():
        columns = {c['name']: c for c in inspector.get_columns('threads')}
        if 'selected_agent_ids' in columns:
            col_type = str(columns['selected_agent_ids']['type'])
            if 'JSON' not in col_type.upper():
                # Convert 'null' string values to SQL NULL before type change
                op.execute(
                    "UPDATE threads SET selected_agent_ids = NULL "
                    "WHERE selected_agent_ids = 'null'"
                )
                op.alter_column(
                    'threads', 'selected_agent_ids',
                    type_=JSONB(),
                    existing_nullable=True,
                    postgresql_using='selected_agent_ids::jsonb',
                )

    # Fix chat_queries.agent_ids_used: text -> jsonb
    if 'chat_queries' in inspector.get_table_names():
        columns = {c['name']: c for c in inspector.get_columns('chat_queries')}
        if 'agent_ids_used' in columns:
            col_type = str(columns['agent_ids_used']['type'])
            if 'JSON' not in col_type.upper():
                op.execute(
                    "UPDATE chat_queries SET agent_ids_used = NULL "
                    "WHERE agent_ids_used = 'null'"
                )
                op.alter_column(
                    'chat_queries', 'agent_ids_used',
                    type_=JSONB(),
                    existing_nullable=True,
                    postgresql_using='agent_ids_used::jsonb',
                )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if 'threads' in inspector.get_table_names():
        columns = [c['name'] for c in inspector.get_columns('threads')]
        if 'selected_agent_ids' in columns:
            op.alter_column(
                'threads', 'selected_agent_ids',
                type_=sa.Text(),
                existing_nullable=True,
                postgresql_using='selected_agent_ids::text',
            )

    if 'chat_queries' in inspector.get_table_names():
        columns = [c['name'] for c in inspector.get_columns('chat_queries')]
        if 'agent_ids_used' in columns:
            op.alter_column(
                'chat_queries', 'agent_ids_used',
                type_=sa.Text(),
                existing_nullable=True,
                postgresql_using='agent_ids_used::text',
            )
