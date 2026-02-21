"""
Stage a suspected-incorrect root for human review.

The reviewing agent calls this script each time it believes a token's
root is wrong.  Entries accumulate in ``data/root_review_staging.json``
until 200 are collected, at which point the human reviews them via the
Streamlit app (``scripts/review_roots_app.py``).

Usage:
    # Stage a correction
    python scripts/review_roots_stage.py \\
        --token-id 12345 \\
        --suggested-root "كتب" \\
        --reason "Current root 'كتاب' is the noun form, not the trilateral root" \\
        --confidence high

    # Show staging summary
    python scripts/review_roots_stage.py --show

    # Clear the staging file (start fresh)
    python scripts/review_roots_stage.py --clear
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# sys.path fixup so `backend.*` imports resolve
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

STAGING_FILE = Path(__file__).resolve().parents[1] / "data" / "root_review_staging.json"


def _load_staging() -> dict:
    """Load or initialize the staging file."""
    if STAGING_FILE.exists():
        text = STAGING_FILE.read_text(encoding="utf-8")
        if text.strip():
            return json.loads(text)
    return {
        "version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "corrections": [],
    }


def _save_staging(data: dict) -> None:
    """Write the staging data back to disk."""
    STAGING_FILE.parent.mkdir(parents=True, exist_ok=True)
    STAGING_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _enrich_from_db(token_id: int) -> dict:
    """Fetch token details from the database to enrich the staging entry."""
    from backend.db import get_sync_session_maker, init_db
    from backend.models.token_model import Token

    init_db()
    SessionMaker = get_sync_session_maker()
    with SessionMaker() as session:
        token = session.get(Token, token_id)
        if not token:
            print(f"ERROR: Token ID {token_id} not found in database.", file=sys.stderr)
            sys.exit(1)
        return {
            "token_id": token.id,
            "sura": token.sura,
            "aya": token.aya,
            "position": token.position,
            "text_ar": token.text_ar,
            "normalized": token.normalized,
            "current_root": token.root,
            "root_sources": token.root_sources or {},
            "status": token.status,
            "pattern": token.pattern,
        }


def stage_correction(
    token_id: int,
    suggested_root: str,
    reason: str,
    confidence: str = "medium",
) -> int:
    """
    Add one correction to the staging file.

    Returns the new total count of staged corrections.
    """
    data = _load_staging()

    # Check for duplicate
    existing_ids = {c["token_id"] for c in data["corrections"]}
    if token_id in existing_ids:
        print(f"Token {token_id} already staged — skipping duplicate.")
        return len(data["corrections"])

    token_info = _enrich_from_db(token_id)

    entry = {
        **token_info,
        "suggested_root": suggested_root,
        "reason": reason,
        "confidence": confidence,
        "staged_at": datetime.now(timezone.utc).isoformat(),
    }
    data["corrections"].append(entry)
    _save_staging(data)

    count = len(data["corrections"])
    print(f"Staged token {token_id} ({token_info['text_ar']}): "
          f"'{token_info['current_root']}' → '{suggested_root}'  "
          f"[{count} total staged]")

    if count >= 200:
        print(
            "\n*** 200 corrections staged! ***\n"
            "Tell the user to review them:\n"
            "    streamlit run scripts/review_roots_app.py\n"
        )

    return count


def show_summary() -> None:
    """Print a summary of the current staging file."""
    data = _load_staging()
    corrections = data["corrections"]
    count = len(corrections)

    if count == 0:
        print("Staging file is empty — no corrections pending.")
        return

    print(f"Staged corrections: {count}")
    print(f"Created: {data.get('created_at', 'unknown')}")
    print()

    # Confidence breakdown
    by_conf = {}
    for c in corrections:
        conf = c.get("confidence", "unknown")
        by_conf[conf] = by_conf.get(conf, 0) + 1
    print("By confidence:")
    for conf, n in sorted(by_conf.items()):
        print(f"  {conf}: {n}")

    # Sura breakdown (top 5)
    by_sura: dict[int, int] = {}
    for c in corrections:
        s = c["sura"]
        by_sura[s] = by_sura.get(s, 0) + 1
    print("\nTop suras:")
    for sura, n in sorted(by_sura.items(), key=lambda x: -x[1])[:5]:
        print(f"  Sura {sura}: {n}")


def clear_staging() -> None:
    """Reset the staging file."""
    if STAGING_FILE.exists():
        STAGING_FILE.unlink()
    print("Staging file cleared.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage a suspected-incorrect root for human review",
    )
    parser.add_argument("--token-id", type=int, help="Token ID to stage")
    parser.add_argument("--suggested-root", type=str, help="The correct root you suggest")
    parser.add_argument("--reason", type=str, help="Why you think the current root is wrong")
    parser.add_argument(
        "--confidence", type=str, default="medium",
        choices=["high", "medium", "low"],
        help="How confident you are (default: medium)",
    )
    parser.add_argument("--show", action="store_true", help="Show staging summary")
    parser.add_argument("--clear", action="store_true", help="Clear the staging file")

    args = parser.parse_args()

    if args.show:
        show_summary()
        return
    if args.clear:
        clear_staging()
        return

    if not args.token_id or not args.suggested_root or not args.reason:
        parser.error("--token-id, --suggested-root, and --reason are required to stage a correction")

    stage_correction(
        token_id=args.token_id,
        suggested_root=args.suggested_root,
        reason=args.reason,
        confidence=args.confidence,
    )


if __name__ == "__main__":
    main()
