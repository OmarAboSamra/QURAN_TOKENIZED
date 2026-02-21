"""
Database migration: add FK columns and populate verses.

Applies the D1–D4 schema changes from DESIGN_REVIEW_PLAN.md:
  - Adds root_id and verse_id columns to the tokens table
  - Renames the legacy 'tokens' column in roots to 'tokens_legacy'
  - Populates the verses table from existing token data
  - Links tokens to their verse rows (sets verse_id)
  - Links tokens to their root rows (sets root_id)

Safe to run multiple times — each step checks before acting.

Usage:
    python scripts/migrate_add_relationships.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import inspect, text

from backend.db import get_sync_engine, get_sync_session_maker, init_db
from backend.models import Root, Token, Verse


def column_exists(engine, table: str, column: str) -> bool:
    """Check if a column exists in a table."""
    insp = inspect(engine)
    columns = [c["name"] for c in insp.get_columns(table)]
    return column in columns


def table_exists(engine, table: str) -> bool:
    """Check if a table exists."""
    insp = inspect(engine)
    return table in insp.get_table_names()


def main() -> None:
    print("=" * 60)
    print("Migration: Add Relationships (D1–D4)")
    print("=" * 60)
    print()

    engine = get_sync_engine()
    SessionMaker = get_sync_session_maker()

    # ── Step 0: Ensure all tables exist ────────────────────────────
    # create_all only creates tables that don't exist yet.
    print("[Step 0] Ensuring all tables exist...")
    init_db()
    print("  OK")

    is_sqlite = str(engine.url).startswith("sqlite")

    with engine.connect() as conn:
        # ── Step 1: Add root_id column to tokens ──────────────────
        if not column_exists(engine, "tokens", "root_id"):
            print("[Step 1] Adding root_id column to tokens...")
            conn.execute(text(
                "ALTER TABLE tokens ADD COLUMN root_id INTEGER REFERENCES roots(id)"
            ))
            conn.commit()
            print("  OK")
        else:
            print("[Step 1] root_id column already exists — skipping")

        # ── Step 2: Add verse_id column to tokens ─────────────────
        if not column_exists(engine, "tokens", "verse_id"):
            print("[Step 2] Adding verse_id column to tokens...")
            conn.execute(text(
                "ALTER TABLE tokens ADD COLUMN verse_id INTEGER REFERENCES verses(id)"
            ))
            conn.commit()
            print("  OK")
        else:
            print("[Step 2] verse_id column already exists — skipping")

        # ── Step 3: Rename legacy 'tokens' column in roots ────────
        # SQLite doesn't support RENAME COLUMN before 3.25.
        # We handle this gracefully: if the old column exists, rename it.
        if column_exists(engine, "roots", "tokens"):
            if not column_exists(engine, "roots", "tokens_legacy"):
                print("[Step 3] Renaming roots.tokens → roots.tokens_legacy...")
                if is_sqlite:
                    # SQLite >= 3.25 supports ALTER TABLE RENAME COLUMN
                    try:
                        conn.execute(text(
                            "ALTER TABLE roots RENAME COLUMN tokens TO tokens_legacy"
                        ))
                        conn.commit()
                        print("  OK")
                    except Exception as e:
                        print(f"  WARNING: Could not rename column ({e})")
                        print("  This is non-blocking — the legacy column will still work.")
                else:
                    conn.execute(text(
                        "ALTER TABLE roots RENAME COLUMN tokens TO tokens_legacy"
                    ))
                    conn.commit()
                    print("  OK")
            else:
                print("[Step 3] tokens_legacy column already exists — skipping")
        else:
            print("[Step 3] No legacy 'tokens' column found — skipping")

    # ── Step 4: Create indexes if needed ───────────────────────────
    with engine.connect() as conn:
        existing_indexes = {idx["name"] for idx in inspect(engine).get_indexes("tokens")}
        
        if "ix_tokens_root_id" not in existing_indexes:
            print("[Step 4a] Creating index ix_tokens_root_id...")
            conn.execute(text("CREATE INDEX ix_tokens_root_id ON tokens (root_id)"))
            conn.commit()

        if "ix_tokens_verse_id" not in existing_indexes:
            print("[Step 4b] Creating index ix_tokens_verse_id...")
            conn.execute(text("CREATE INDEX ix_tokens_verse_id ON tokens (verse_id)"))
            conn.commit()

        print("[Step 4] Indexes OK")

    # ── Step 5: Populate verses table (D3) ─────────────────────────
    print("[Step 5] Populating verses table from token data...")
    with SessionMaker() as session:
        # Check if verses already exist
        existing_verse_count = session.query(Verse).count()
        token_count = session.query(Token).count()

        if token_count == 0:
            print("  No tokens in database — skipping verse population")
        elif existing_verse_count > 0:
            print(f"  Verses table already has {existing_verse_count} rows — skipping")
        else:
            # Get all distinct (sura, aya) pairs from tokens
            from sqlalchemy import distinct, func

            verse_groups = (
                session.query(
                    Token.sura,
                    Token.aya,
                )
                .group_by(Token.sura, Token.aya)
                .order_by(Token.sura, Token.aya)
                .all()
            )

            verse_count = 0
            for sura, aya in verse_groups:
                # Get all tokens for this verse to reconstruct text
                tokens = (
                    session.query(Token)
                    .filter(Token.sura == sura, Token.aya == aya)
                    .order_by(Token.position)
                    .all()
                )

                text_ar = " ".join(t.text_ar for t in tokens)
                text_normalized = " ".join(t.normalized for t in tokens)

                verse = Verse(
                    sura=sura,
                    aya=aya,
                    text_ar=text_ar,
                    text_normalized=text_normalized,
                    word_count=len(tokens),
                )
                session.add(verse)
                verse_count += 1

            session.commit()
            print(f"  Created {verse_count} verse rows")

    # ── Step 6: Link tokens → verses (set verse_id) ───────────────
    print("[Step 6] Linking tokens to verses (setting verse_id)...")
    with SessionMaker() as session:
        # Count tokens that already have verse_id set
        linked = session.query(Token).filter(Token.verse_id.isnot(None)).count()
        total = session.query(Token).count()

        if total == 0:
            print("  No tokens — skipping")
        elif linked == total:
            print(f"  All {total} tokens already linked — skipping")
        else:
            # Build a lookup: (sura, aya) → verse.id
            verses = session.query(Verse).all()
            verse_lookup = {(v.sura, v.aya): v.id for v in verses}

            if not verse_lookup:
                print("  No verses found — run Step 5 first")
            else:
                # Update tokens in batches
                batch_size = 1000
                unlinked_tokens = (
                    session.query(Token)
                    .filter(Token.verse_id.is_(None))
                    .all()
                )
                updated = 0
                for token in unlinked_tokens:
                    verse_id = verse_lookup.get((token.sura, token.aya))
                    if verse_id:
                        token.verse_id = verse_id
                        updated += 1

                    if updated % batch_size == 0 and updated > 0:
                        session.flush()

                session.commit()
                print(f"  Linked {updated} tokens to verses")

    # ── Step 7: Link tokens → roots (set root_id) ─────────────────
    print("[Step 7] Linking tokens to roots (setting root_id)...")
    with SessionMaker() as session:
        # Count tokens that already have root_id set
        linked = session.query(Token).filter(Token.root_id.isnot(None)).count()
        has_root = session.query(Token).filter(Token.root.isnot(None)).count()

        if has_root == 0:
            print("  No tokens have roots — skipping")
        elif linked == has_root:
            print(f"  All {has_root} rooted tokens already linked — skipping")
        else:
            # Build a lookup: root_string → root.id
            roots = session.query(Root).all()
            root_lookup = {r.root: r.id for r in roots}

            # Update tokens that have a root string but no root_id
            tokens_to_link = (
                session.query(Token)
                .filter(Token.root.isnot(None), Token.root_id.is_(None))
                .all()
            )

            updated = 0
            missing_roots = set()
            batch_size = 1000

            for token in tokens_to_link:
                root_id = root_lookup.get(token.root)
                if root_id:
                    token.root_id = root_id
                    updated += 1
                else:
                    missing_roots.add(token.root)

                if updated % batch_size == 0 and updated > 0:
                    session.flush()

            session.commit()
            print(f"  Linked {updated} tokens to roots")
            if missing_roots:
                print(f"  WARNING: {len(missing_roots)} root strings not found in roots table")
                print(f"  Examples: {list(missing_roots)[:5]}")

    # ── Done ───────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("Migration complete!")
    print()

    # Print summary
    with SessionMaker() as session:
        total_tokens = session.query(Token).count()
        tokens_with_root_id = session.query(Token).filter(Token.root_id.isnot(None)).count()
        tokens_with_verse_id = session.query(Token).filter(Token.verse_id.isnot(None)).count()
        total_verses = session.query(Verse).count()
        total_roots = session.query(Root).count()

        print(f"  Tokens:           {total_tokens}")
        print(f"  Tokens → root_id: {tokens_with_root_id}")
        print(f"  Tokens → verse_id:{tokens_with_verse_id}")
        print(f"  Verses:           {total_verses}")
        print(f"  Roots:            {total_roots}")
    print("=" * 60)


if __name__ == "__main__":
    main()
