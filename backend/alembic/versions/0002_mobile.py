"""add unique mobile_number to users

Revision ID: 0002_mobile
Revises: 0001_initial
Create Date: 2026-08-13
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0002_mobile"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'mobile_number'
            ) THEN
                ALTER TABLE users ADD COLUMN mobile_number VARCHAR(10);
            END IF;
        END $$;
        CREATE UNIQUE INDEX IF NOT EXISTS ix_users_mobile_number ON users (mobile_number);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS ix_users_mobile_number;
        ALTER TABLE users DROP COLUMN IF EXISTS mobile_number;
        """
    )
