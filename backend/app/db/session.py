from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.app.core.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _ensure_compat_columns() -> None:
    """Add columns that create_all will not alter on existing tables."""
    statements = [
        """
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY,
            email VARCHAR(320) NOT NULL UNIQUE,
            full_name VARCHAR(255) NOT NULL DEFAULT '',
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_users_email ON users (email)",
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'mobile_number'
            ) THEN
                ALTER TABLE users ADD COLUMN mobile_number VARCHAR(10);
                CREATE UNIQUE INDEX IF NOT EXISTS ix_users_mobile_number ON users (mobile_number);
            END IF;
        END $$;
        """,
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'documents' AND column_name = 'user_id'
            ) THEN
                ALTER TABLE documents
                ADD COLUMN user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL;
                CREATE INDEX IF NOT EXISTS ix_documents_user_id ON documents (user_id);
            END IF;
        END $$;
        """,
        """
        CREATE TABLE IF NOT EXISTS doubt_sessions (
            id UUID PRIMARY KEY,
            document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
            title VARCHAR(255) NOT NULL DEFAULT 'Doubt chat',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_doubt_sessions_document_id ON doubt_sessions (document_id)",
        "CREATE INDEX IF NOT EXISTS ix_doubt_sessions_user_id ON doubt_sessions (user_id)",
        """
        CREATE TABLE IF NOT EXISTS doubt_messages (
            id UUID PRIMARY KEY,
            session_id UUID NOT NULL REFERENCES doubt_sessions(id) ON DELETE CASCADE,
            role VARCHAR(16) NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_doubt_messages_session_id ON doubt_messages (session_id)",
    ]
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))


def init_db() -> None:
    from backend.app.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_compat_columns()
