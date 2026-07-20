"""Add password reset token fields to users table

Revision ID: add_password_reset_fields
Revises: add_tool_cache_table
Create Date: 2026-03-03

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_password_reset_fields'
down_revision = 'add_tool_cache_table'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    tables = inspector.get_table_names()
    if 'users' in tables:
        columns = [col['name'] for col in inspector.get_columns('users')]

        if 'password_reset_token' not in columns:
            op.add_column('users', sa.Column(
                'password_reset_token', sa.String(), nullable=True
            ))
            op.create_index(
                'ix_users_password_reset_token',
                'users',
                ['password_reset_token']
            )

        if 'password_reset_expires' not in columns:
            op.add_column('users', sa.Column(
                'password_reset_expires',
                sa.DateTime(timezone=True),
                nullable=True
            ))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    tables = inspector.get_table_names()
    if 'users' in tables:
        columns = [col['name'] for col in inspector.get_columns('users')]

        if 'password_reset_expires' in columns:
            op.drop_column('users', 'password_reset_expires')

        if 'password_reset_token' in columns:
            op.drop_index('ix_users_password_reset_token', table_name='users')
            op.drop_column('users', 'password_reset_token')
