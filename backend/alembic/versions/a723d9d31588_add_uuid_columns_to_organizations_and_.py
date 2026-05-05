"""add_uuid_columns_to_organizations_and_threads

Revision ID: a723d9d31588
Revises: add_user_is_active
Create Date: 2026-01-31

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid


# revision identifiers, used by Alembic.
revision = 'a723d9d31588'
down_revision = 'add_user_is_active'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add UUID columns to organizations table
    # Step 1: Add column as nullable first (to allow existing rows)
    op.add_column('organizations', sa.Column('uuid', UUID(as_uuid=True), nullable=True))

    # Step 2: Generate UUIDs for existing organizations
    # Create connection and execute raw SQL to update existing rows
    connection = op.get_bind()
    # For PostgreSQL
    connection.execute(sa.text("UPDATE organizations SET uuid = gen_random_uuid() WHERE uuid IS NULL"))

    # Step 3: Make the column non-nullable and add unique constraint
    op.alter_column('organizations', 'uuid', nullable=False)
    op.create_unique_constraint('uq_organizations_uuid', 'organizations', ['uuid'])
    op.create_index('ix_organizations_uuid', 'organizations', ['uuid'])

    # Add UUID columns to threads table
    # Step 1: Add column as nullable first
    op.add_column('threads', sa.Column('uuid', UUID(as_uuid=True), nullable=True))

    # Step 2: Generate UUIDs for existing threads
    connection.execute(sa.text("UPDATE threads SET uuid = gen_random_uuid() WHERE uuid IS NULL"))

    # Step 3: Make the column non-nullable and add unique constraint
    op.alter_column('threads', 'uuid', nullable=False)
    op.create_unique_constraint('uq_threads_uuid', 'threads', ['uuid'])
    op.create_index('ix_threads_uuid', 'threads', ['uuid'])


def downgrade() -> None:
    # Remove UUID columns from threads
    op.drop_index('ix_threads_uuid', table_name='threads')
    op.drop_constraint('uq_threads_uuid', 'threads', type_='unique')
    op.drop_column('threads', 'uuid')

    # Remove UUID columns from organizations
    op.drop_index('ix_organizations_uuid', table_name='organizations')
    op.drop_constraint('uq_organizations_uuid', 'organizations', type_='unique')
    op.drop_column('organizations', 'uuid')
