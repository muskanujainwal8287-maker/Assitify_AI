"""initial schema with users (idempotent for existing DBs)

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-13
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY,
            email VARCHAR(320) NOT NULL UNIQUE,
            full_name VARCHAR(255) NOT NULL DEFAULT '',
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS ix_users_email ON users (email);

        CREATE TABLE IF NOT EXISTS documents (
            id UUID PRIMARY KEY,
            user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
            filename VARCHAR(512) NOT NULL,
            detected_type VARCHAR(128) NOT NULL,
            text TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS ix_documents_user_id ON documents (user_id);

        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'documents' AND column_name = 'user_id'
            ) THEN
                ALTER TABLE documents
                ADD COLUMN user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL;
            END IF;
        END $$;

        CREATE TABLE IF NOT EXISTS questions (
            id UUID PRIMARY KEY,
            document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            external_id VARCHAR(64) NOT NULL,
            prompt TEXT NOT NULL,
            question_type VARCHAR(32) NOT NULL,
            options JSONB NOT NULL DEFAULT '[]'::jsonb,
            answer TEXT NOT NULL,
            difficulty VARCHAR(16) NOT NULL,
            topic VARCHAR(255) NOT NULL DEFAULT 'General',
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS ix_questions_document_id ON questions (document_id);
        CREATE INDEX IF NOT EXISTS ix_questions_external_id ON questions (external_id);

        CREATE TABLE IF NOT EXISTS attempts (
            id UUID PRIMARY KEY,
            document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            total_score FLOAT NOT NULL DEFAULT 0,
            recommended_difficulty VARCHAR(16) NOT NULL DEFAULT 'easy',
            source VARCHAR(16) NOT NULL DEFAULT 'fallback',
            scoring_source VARCHAR(16) NOT NULL DEFAULT 'fallback',
            weak_topics JSONB NOT NULL DEFAULT '[]'::jsonb,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS ix_attempts_document_id ON attempts (document_id);

        CREATE TABLE IF NOT EXISTS attempt_answers (
            id UUID PRIMARY KEY,
            attempt_id UUID NOT NULL REFERENCES attempts(id) ON DELETE CASCADE,
            question_external_id VARCHAR(64) NOT NULL,
            user_answer TEXT NOT NULL,
            expected_answer TEXT NOT NULL,
            is_correct BOOLEAN NOT NULL DEFAULT FALSE,
            score FLOAT NOT NULL DEFAULT 0,
            explanation TEXT NOT NULL DEFAULT '',
            topic VARCHAR(255) NOT NULL DEFAULT 'General'
        );
        CREATE INDEX IF NOT EXISTS ix_attempt_answers_attempt_id ON attempt_answers (attempt_id);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS attempt_answers;
        DROP TABLE IF EXISTS attempts;
        DROP TABLE IF EXISTS questions;
        DROP TABLE IF EXISTS documents;
        DROP TABLE IF EXISTS users;
        """
    )
