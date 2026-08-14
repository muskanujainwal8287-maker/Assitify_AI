"""doubt chat sessions and messages

Revision ID: 0003_doubt_chat
Revises: 0002_mobile
Create Date: 2026-08-14
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0003_doubt_chat"
down_revision: Union[str, None] = "0002_mobile"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS doubt_sessions (
            id UUID PRIMARY KEY,
            document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
            title VARCHAR(255) NOT NULL DEFAULT 'Doubt chat',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS ix_doubt_sessions_document_id ON doubt_sessions (document_id);
        CREATE INDEX IF NOT EXISTS ix_doubt_sessions_user_id ON doubt_sessions (user_id);

        CREATE TABLE IF NOT EXISTS doubt_messages (
            id UUID PRIMARY KEY,
            session_id UUID NOT NULL REFERENCES doubt_sessions(id) ON DELETE CASCADE,
            role VARCHAR(16) NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS ix_doubt_messages_session_id ON doubt_messages (session_id);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS doubt_messages;
        DROP TABLE IF EXISTS doubt_sessions;
        """
    )
