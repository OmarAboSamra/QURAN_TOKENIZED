"""
Migration: Add D7 columns (Token.pattern, Root.related_roots).

Adds:
    - tokens.pattern    VARCHAR(50) nullable, indexed
    - roots.related_roots  JSON nullable

Idempotent: safe to run multiple times (columns are only added if missing).

Usage:
    python scripts/migrate_d7_columns.py
"""
import sys

sys.path.insert(0, ".")

from sqlalchemy import text

from backend.db import get_sync_engine, init_db


def _column_exists(conn, table: str, column: str) -> bool:
    """Check if a column exists in a SQLite table."""
    result = conn.execute(text(f"PRAGMA table_info({table})"))
    for row in result.fetchall():
        if row[1] == column:
            return True
    return False


def migrate() -> None:
    """Add D7 columns to the database."""
    init_db()
    engine = get_sync_engine()

    with engine.connect() as conn:
        # 1. Add tokens.pattern
        if not _column_exists(conn, "tokens", "pattern"):
            print("[1/3] Adding tokens.pattern column ...")
            conn.execute(text("ALTER TABLE tokens ADD COLUMN pattern VARCHAR(50)"))
            conn.commit()
        else:
            print("[1/3] tokens.pattern already exists, skipping")

        # 2. Create index on tokens.pattern
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_tokens_pattern ON tokens(pattern)"))
            conn.commit()
            print("[2/3] Index ix_tokens_pattern ready")
        except Exception as e:
            print(f"[2/3] Index creation skipped: {e}")

        # 3. Add roots.related_roots
        if not _column_exists(conn, "roots", "related_roots"):
            print("[3/3] Adding roots.related_roots column ...")
            conn.execute(text("ALTER TABLE roots ADD COLUMN related_roots JSON"))
            conn.commit()
        else:
            print("[3/3] roots.related_roots already exists, skipping")

        print("[OK] D7 migration complete")


if __name__ == "__main__":
    migrate()
