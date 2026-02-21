"""
Apply human-approved root corrections to the database.

Reads ``data/root_review_approved.json`` (populated by the Streamlit
review app) and updates each token's root, root_id FK, status, and
root_sources in the database.

Usage:
    # Preview what would change (no DB writes)
    python scripts/review_roots_apply.py --dry-run

    # Apply for real
    python scripts/review_roots_apply.py

    # Custom batch size
    python scripts/review_roots_apply.py --batch-size 25
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# sys.path fixup
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse

from sqlalchemy import select

from backend.db import get_sync_session_maker, init_db
from backend.models.root_model import Root
from backend.models.token_model import Token, TokenStatus

# ── File paths ──────────────────────────────────────────────────────
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
APPROVED_FILE = DATA_DIR / "root_review_approved.json"
APPLIED_LOG = DATA_DIR / "root_review_applied_log.json"


def _load_json(path: Path) -> dict:
    if path.exists():
        text = path.read_text(encoding="utf-8")
        if text.strip():
            return json.loads(text)
    return {"version": 1, "corrections": []}


def _save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _get_or_create_root(session, root_str: str) -> Root:
    """Find existing Root row or create a new one."""
    stmt = select(Root).where(Root.root == root_str)
    root_obj = session.execute(stmt).scalar_one_or_none()
    if root_obj is None:
        root_obj = Root(root=root_str, token_count=0, token_ids=[])
        session.add(root_obj)
        session.flush()  # generate ID
    return root_obj


def apply_approved(
    dry_run: bool = False,
    batch_size: int = 50,
) -> tuple[int, list[str]]:
    """
    Apply all approved corrections to the database.

    For each correction the following fields are updated:
        Token.root          ← final_root (the approved root string)
        Token.root_id       ← FK to Root row (created if missing)
        Token.status        ← "verified" (human-approved)
        Token.root_sources  ← existing dict + {"agent_review": final_root}
        Token.updated_at    ← automatic via onupdate=func.now()

    The old Root's token_count is decremented; the new Root's is incremented.

    Returns:
        (applied_count, list_of_error_messages)
    """
    approved_data = _load_json(APPROVED_FILE)
    corrections = approved_data.get("corrections", [])

    if not corrections:
        print("No approved corrections to apply.")
        return 0, []

    init_db()
    SessionMaker = get_sync_session_maker()

    applied = 0
    errors: list[str] = []
    applied_entries: list[dict] = []

    session = SessionMaker()
    try:
        for i, correction in enumerate(corrections):
            token_id = correction["token_id"]
            final_root = correction["final_root"]
            old_root_str = correction.get("current_root")

            try:
                token = session.get(Token, token_id)
                if not token:
                    errors.append(f"Token {token_id} not found — skipped")
                    continue

                if dry_run:
                    print(
                        f"[DRY-RUN] Token {token_id} "
                        f"({token.sura}:{token.aya}:{token.position} '{token.text_ar}'): "
                        f"'{token.root}' → '{final_root}'"
                    )
                    applied += 1
                    continue

                # 1. Update root string
                token.root = final_root

                # 2. Re-link root_id FK
                new_root_obj = _get_or_create_root(session, final_root)
                token.root_id = new_root_obj.id
                new_root_obj.token_count = (new_root_obj.token_count or 0) + 1

                # 3. Decrement old root's counter
                if old_root_str and old_root_str != final_root:
                    old_root_obj = session.execute(
                        select(Root).where(Root.root == old_root_str)
                    ).scalar_one_or_none()
                    if old_root_obj and old_root_obj.token_count and old_root_obj.token_count > 0:
                        old_root_obj.token_count -= 1

                # 4. Update status to verified
                token.status = TokenStatus.VERIFIED.value

                # 5. Append agent_review to root_sources
                sources = token.root_sources or {}
                sources["agent_review"] = final_root
                token.root_sources = sources

                applied += 1

                # Record for audit log
                applied_entries.append({
                    **correction,
                    "applied_at": datetime.now(timezone.utc).isoformat(),
                    "old_root": old_root_str,
                    "new_root": final_root,
                })

                # Commit in batches
                if applied % batch_size == 0:
                    session.commit()
                    print(f"  Committed batch ({applied} so far)")

            except Exception as e:
                errors.append(f"Token {token_id}: {e}")
                session.rollback()
                session = SessionMaker()  # fresh session after rollback

        # Final commit for remaining
        if not dry_run:
            session.commit()

    finally:
        session.close()

    if dry_run:
        print(f"\n[DRY-RUN] Would apply {applied} corrections.")
        return applied, errors

    # ── Post-apply bookkeeping ──────────────────────────────────────

    # Append to audit log
    log_data = _load_json(APPLIED_LOG)
    log_corrections = log_data.get("corrections", [])
    log_corrections.extend(applied_entries)
    log_data["corrections"] = log_corrections
    log_data["last_applied"] = datetime.now(timezone.utc).isoformat()
    _save_json(APPLIED_LOG, log_data)

    # Clear approved file
    _save_json(APPROVED_FILE, {"version": 1, "corrections": []})

    print(f"\nApplied {applied} corrections to the database.")
    if errors:
        print(f"Errors ({len(errors)}):")
        for err in errors:
            print(f"  - {err}")
    print(f"Audit log updated: {APPLIED_LOG}")

    return applied, errors


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply approved root corrections to the database",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview changes without writing to the database",
    )
    parser.add_argument(
        "--batch-size", type=int, default=50,
        help="Commit every N corrections (default: 50)",
    )
    args = parser.parse_args()

    applied, errors = apply_approved(
        dry_run=args.dry_run,
        batch_size=args.batch_size,
    )

    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
