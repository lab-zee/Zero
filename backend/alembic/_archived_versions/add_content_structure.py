"""Add content_structure and followup_questions to chat_queries

Revision ID: add_content_structure
Revises: add_answer_modes
Create Date: 2026-01-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_content_structure'
down_revision = 'add_answer_modes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Check if chat_queries table exists and get its columns
    tables = inspector.get_table_names()
    if 'chat_queries' in tables:
        columns = [col['name'] for col in inspector.get_columns('chat_queries')]

        # Add content_structure column if it doesn't exist
        if 'content_structure' not in columns:
            op.add_column('chat_queries', sa.Column(
                'content_structure',
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True
            ))

        # Add followup_questions column if it doesn't exist
        if 'followup_questions' not in columns:
            op.add_column('chat_queries', sa.Column(
                'followup_questions',
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True
            ))


def downgrade() -> None:
    # Remove columns
    op.drop_column('chat_queries', 'followup_questions')
    op.drop_column('chat_queries', 'content_structure')
