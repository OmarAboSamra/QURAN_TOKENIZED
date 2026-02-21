"""
Fetch a batch of tokens from the database for root review.

Used by the reviewing agent to get tokens one batch at a time.
Outputs JSON to stdout (or a file) so the agent can parse it.

Usage:
    python scripts/review_roots_fetch.py --offset 0 --limit 50
    python scripts/review_roots_fetch.py --offset 50 --limit 50 --sura 2
    python scripts/review_roots_fetch.py --offset 0 --limit 10 --status verified
    python scripts/review_roots_fetch.py --offset 0 --limit 50 --output batch.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# sys.path fixup so `backend.*` imports resolve when running from project root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select

from backend.db import get_sync_session_maker, init_db
from backend.models.token_model import Token, TokenStatus


def fetch_batch(
    offset: int = 0,
    limit: int = 50,
    status_filter: str | None = None,
    sura_filter: int | None = None,
) -> dict:
    """
    Query the database for a batch of tokens and return structured JSON.

    Returns:
        {
            "tokens": [ ... ],
            "progress": { "offset", "limit", "batch_count", "total_matching" }
        }
    """
    init_db()
    SessionMaker = get_sync_session_maker()

    with SessionMaker() as session:
        # Build the base query
        base_where = []
        if status_filter:
            base_where.append(Token.status == status_filter)
        if sura_filter:
            base_where.append(Token.sura == sura_filter)

        # Count total matching tokens
        count_stmt = select(func.count(Token.id))
        if base_where:
            count_stmt = count_stmt.where(*base_where)
        total_matching = session.execute(count_stmt).scalar() or 0

        # Fetch the batch
        stmt = (
            select(Token)
            .order_by(Token.sura, Token.aya, Token.position)
            .offset(offset)
            .limit(limit)
        )
        if base_where:
            stmt = stmt.where(*base_where)

        tokens = list(session.execute(stmt).scalars().all())

        # Serialize
        token_list = []
        for t in tokens:
            token_list.append({
                "token_id": t.id,
                "sura": t.sura,
                "aya": t.aya,
                "position": t.position,
                "text_ar": t.text_ar,
                "normalized": t.normalized,
                "current_root": t.root,
                "root_sources": t.root_sources or {},
                "status": t.status,
                "pattern": t.pattern,
            })

        return {
            "tokens": token_list,
            "progress": {
                "offset": offset,
                "limit": limit,
                "batch_count": len(token_list),
                "total_matching": total_matching,
                "next_offset": offset + limit if (offset + limit) < total_matching else None,
            },
        }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch a batch of tokens for root review",
    )
    parser.add_argument(
        "--offset", type=int, default=0,
        help="Starting offset (default: 0)",
    )
    parser.add_argument(
        "--limit", type=int, default=50,
        help="Number of tokens to fetch per batch (default: 50)",
    )
    parser.add_argument(
        "--status", type=str, default=None,
        choices=[s.value for s in TokenStatus],
        help="Filter by token status (default: all statuses)",
    )
    parser.add_argument(
        "--sura", type=int, default=None,
        help="Filter by sura number (default: all suras)",
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Write output to a file instead of stdout",
    )
    args = parser.parse_args()

    result = fetch_batch(
        offset=args.offset,
        limit=args.limit,
        status_filter=args.status,
        sura_filter=args.sura,
    )

    json_str = json.dumps(result, ensure_ascii=False, indent=2)

    if args.output:
        Path(args.output).write_text(json_str, encoding="utf-8")
        print(f"Wrote {result['progress']['batch_count']} tokens to {args.output}")
    else:
        # Force UTF-8 on Windows to handle Arabic characters
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        print(json_str)


if __name__ == "__main__":
    main()
