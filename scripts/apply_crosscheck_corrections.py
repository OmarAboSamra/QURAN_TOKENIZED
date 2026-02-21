"""
Apply cross-check corrections from the second agent.

Reads data/root_crosscheck_corrections.json and updates all tokens
where the second agent disagreed with the first agent's root assignment.
Only applies high-confidence corrections by default.

Usage:
    python scripts/apply_crosscheck_corrections.py --dry-run
    python scripts/apply_crosscheck_corrections.py
    python scripts/apply_crosscheck_corrections.py --min-confidence medium
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from backend.db import get_sync_session_maker, init_db
from backend.models.token_model import Token, TokenStatus
from backend.models.root_model import Root

CORRECTIONS_FILE = Path(__file__).resolve().parents[1] / "data" / "root_crosscheck_corrections.json"
CONFIDENCE_ORDER = {"high": 3, "medium": 2, "low": 1}


def get_or_create_root(session, root_str: str) -> Root:
    obj = session.execute(select(Root).where(Root.root == root_str)).scalar_one_or_none()
    if obj is None:
        obj = Root(root=root_str, token_count=0, token_ids=[])
        session.add(obj)
        session.flush()
    return obj


def apply_corrections(dry_run: bool = False, min_confidence: str = "high") -> int:
    if not CORRECTIONS_FILE.exists():
        print(f"No corrections file found at {CORRECTIONS_FILE}")
        return 0

    data = json.loads(CORRECTIONS_FILE.read_text(encoding="utf-8"))
    corrections = data.get("corrections", [])
    min_level = CONFIDENCE_ORDER.get(min_confidence, 3)

    eligible = [
        c for c in corrections
        if CONFIDENCE_ORDER.get(c.get("confidence", "low"), 0) >= min_level
    ]

    print(f"Total corrections in file: {len(corrections)}")
    print(f"Eligible (>= {min_confidence}): {len(eligible)}")

    if not eligible:
        return 0

    init_db()
    S = get_sync_session_maker()
    updated = 0

    with S() as session:
        for c in eligible:
            word = c["normalized"]
            new_root = c["suggested_root"]
            old_root = c.get("current_root", "")

            tokens = session.execute(
                select(Token).where(Token.normalized == word)
            ).scalars().all()

            if not tokens:
                print(f"  SKIP: no tokens found for '{word}'")
                continue

            if dry_run:
                print(f"  [DRY-RUN] {word}: {len(tokens)} tokens '{old_root}' -> '{new_root}' ({c.get('reason', '')})")
                updated += len(tokens)
                continue

            root_obj = get_or_create_root(session, new_root)
            for t in tokens:
                t.root = new_root
                t.root_id = root_obj.id
                t.status = TokenStatus.VERIFIED.value
                sources = t.root_sources or {}
                sources["crosscheck_review"] = new_root
                t.root_sources = sources
            root_obj.token_count = (root_obj.token_count or 0) + len(tokens)
            updated += len(tokens)

        if not dry_run:
            session.commit()

    prefix = "[DRY-RUN] " if dry_run else ""
    print(f"\n{prefix}Applied corrections to {updated} tokens.")
    return updated


def main():
    parser = argparse.ArgumentParser(description="Apply cross-check root corrections")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--min-confidence", choices=["high", "medium", "low"], default="high")
    args = parser.parse_args()
    apply_corrections(dry_run=args.dry_run, min_confidence=args.min_confidence)


if __name__ == "__main__":
    main()
