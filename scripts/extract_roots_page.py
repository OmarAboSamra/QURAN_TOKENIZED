"""Extract roots for a single token page (chunk)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable

from sqlalchemy import select

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.db import get_sync_session_maker
from backend.models.token_model import Token, TokenStatus
from backend.services.root_extractor_v2 import RootExtractionService


def _iter_tokens_page(session, page: int, page_size: int) -> list[Token]:
    offset = (page - 1) * page_size
    stmt = (
        select(Token)
        .where(Token.status == TokenStatus.MISSING.value)
        .order_by(Token.sura, Token.aya, Token.position)
        .offset(offset)
        .limit(page_size)
    )
    result = session.execute(stmt)
    return list(result.scalars().all())


def extract_page(
    page: int,
    page_size: int,
    commit_batch: int,
    allow_algorithmic: bool,
) -> int:
    session_maker = get_sync_session_maker()
    session = session_maker()
    root_service = RootExtractionService()

    try:
        tokens = _iter_tokens_page(session, page, page_size)
        total = len(tokens)
        if total == 0:
            print(f"No missing-root tokens found for page {page}.")
            return 0

        print(f"Processing page {page} ({total} tokens, page_size={page_size})")

        updated = 0
        processed = 0

        for token in tokens:
            processed += 1
            result = root_service.extract_root_sync(
                token.normalized,
                sura=token.sura,
                aya=token.aya,
                position=token.position,
            )

            if result and result.get("root"):
                if result.get("method") == "algorithmic" and not allow_algorithmic:
                    continue

                token.root = result["root"]
                token.root_sources = result.get("sources", {})
                token.status = TokenStatus.VERIFIED.value
                updated += 1

            if processed % commit_batch == 0:
                session.commit()
                print(f"  Committed {processed}/{total} (updated={updated})")

        session.commit()
        print(f"Done. Updated {updated}/{total} tokens.")
        return updated

    finally:
        session.close()
        root_service.save_cache()


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract roots for a single page of missing-root tokens.",
    )
    parser.add_argument("--page", type=int, required=True, help="1-based page number")
    parser.add_argument(
        "--page-size",
        type=int,
        default=1000,
        help="Number of tokens per page (default: 1000)",
    )
    parser.add_argument(
        "--commit-batch",
        type=int,
        default=50,
        help="Commit every N tokens (default: 50)",
    )
    parser.add_argument(
        "--allow-algorithmic",
        action="store_true",
        help="Allow algorithmic fallbacks when corpus data is missing",
    )
    return parser.parse_args(list(argv))


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)
    if args.page < 1:
        print("Error: --page must be >= 1")
        return 2
    if args.page_size < 1:
        print("Error: --page-size must be >= 1")
        return 2
    if args.commit_batch < 1:
        print("Error: --commit-batch must be >= 1")
        return 2

    extract_page(args.page, args.page_size, args.commit_batch, args.allow_algorithmic)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
