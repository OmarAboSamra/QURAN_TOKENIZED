"""
Migration: Create FTS5 full-text search index for the tokens table.

Creates a content-sync'd FTS5 virtual table on (text_ar, normalized)
so that Arabic text searches use an inverted index instead of LIKE scans.

The FTS5 table is a "content=" external-content table backed by the
real tokens table. SQLite triggers keep it in sync on INSERT / UPDATE /
DELETE of the tokens table.

Usage:
    python scripts/migrate_fts5.py          # create & populate
    python scripts/migrate_fts5.py --rebuild  # rebuild index only

Idempotent: safe to run multiple times.
"""
import argparse
import sys

# Ensure repo root is on the import path
sys.path.insert(0, ".")

from backend.db import get_sync_engine, init_db


# ── SQL statements ────────────────────────────────────────────────

CREATE_FTS_TABLE = """
CREATE VIRTUAL TABLE IF NOT EXISTS tokens_fts
USING fts5(
    text_ar,
    normalized,
    content='tokens',
    content_rowid='id',
    tokenize='unicode61'
);
"""

# Triggers that keep the FTS index in sync with the tokens table.
# Each trigger must DELETE the old row and INSERT the new row so
# that the inverted index stays consistent.

TRIGGER_INSERT = """
CREATE TRIGGER IF NOT EXISTS tokens_fts_insert
AFTER INSERT ON tokens
BEGIN
    INSERT INTO tokens_fts(rowid, text_ar, normalized)
    VALUES (new.id, new.text_ar, new.normalized);
END;
"""

TRIGGER_DELETE = """
CREATE TRIGGER IF NOT EXISTS tokens_fts_delete
AFTER DELETE ON tokens
BEGIN
    INSERT INTO tokens_fts(tokens_fts, rowid, text_ar, normalized)
    VALUES ('delete', old.id, old.text_ar, old.normalized);
END;
"""

TRIGGER_UPDATE = """
CREATE TRIGGER IF NOT EXISTS tokens_fts_update
AFTER UPDATE ON tokens
BEGIN
    INSERT INTO tokens_fts(tokens_fts, rowid, text_ar, normalized)
    VALUES ('delete', old.id, old.text_ar, old.normalized);
    INSERT INTO tokens_fts(rowid, text_ar, normalized)
    VALUES (new.id, new.text_ar, new.normalized);
END;
"""

REBUILD = """
INSERT INTO tokens_fts(tokens_fts) VALUES('rebuild');
"""


def migrate(rebuild_only: bool = False) -> None:
    """Run the FTS5 migration."""
    init_db()
    engine = get_sync_engine()

    with engine.connect() as conn:
        # Check SQLite version supports FTS5
        version = conn.execute(
            __import__("sqlalchemy").text("SELECT sqlite_version()")
        ).scalar()
        print(f"SQLite version: {version}")

        if not rebuild_only:
            # Step 1: Create the FTS5 virtual table
            print("[1/3] Creating FTS5 virtual table tokens_fts ...")
            conn.execute(__import__("sqlalchemy").text(CREATE_FTS_TABLE))
            conn.commit()

            # Step 2: Create sync triggers
            print("[2/3] Creating sync triggers ...")
            for trigger_sql in (TRIGGER_INSERT, TRIGGER_DELETE, TRIGGER_UPDATE):
                conn.execute(__import__("sqlalchemy").text(trigger_sql))
            conn.commit()

        # Step 3: Rebuild (populate) the index from existing data
        print("[3/3] Rebuilding FTS5 index from tokens table ...")
        conn.execute(__import__("sqlalchemy").text(REBUILD))
        conn.commit()

        # Verify
        count = conn.execute(
            __import__("sqlalchemy").text("SELECT count(*) FROM tokens_fts")
        ).scalar()
        print(f"[OK] FTS5 index contains {count:,} rows")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create FTS5 index for tokens table")
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Only rebuild the index (skip table/trigger creation)",
    )
    args = parser.parse_args()
    migrate(rebuild_only=args.rebuild)
