"""Extract roots for all tokens until complete, with periodic progress output."""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from sqlalchemy import func, select

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.db import get_sync_session_maker
from backend.models.token_model import Token, TokenStatus
from backend.services.root_extractor_v2 import RootExtractionService


def _count_tokens(session) -> tuple[int, int]:
    total = session.execute(select(func.count()).select_from(Token)).scalar() or 0
    missing = session.execute(
        select(func.count()).select_from(Token).where(Token.status == TokenStatus.MISSING.value)
    ).scalar() or 0
    return total, missing


def _fetch_missing_batch(session, batch_size: int) -> list[Token]:
    stmt = (
        select(Token)
        .where(Token.status == TokenStatus.MISSING.value)
        .order_by(Token.sura, Token.aya, Token.position)
        .limit(batch_size)
    )
    result = session.execute(stmt)
    return list(result.scalars().all())


def _format_bar(done: int, total: int, width: int = 40) -> str:
    if total <= 0:
        return "[" + ("#" * width) + "] 100%"
    ratio = min(max(done / total, 0.0), 1.0)
    filled = int(width * ratio)
    bar = "#" * filled + "-" * (width - filled)
    percent = int(ratio * 100)
    return f"[{bar}] {percent}%"


def extract_all(
    batch_size: int,
    commit_batch: int,
    allow_algorithmic: bool,
    progress_interval_seconds: int,
) -> int:
    session_maker = get_sync_session_maker()
    session = session_maker()
    root_service = RootExtractionService()

    try:
        total_tokens, missing_tokens = _count_tokens(session)
        processed = 0
        updated = 0
        last_progress_time = 0.0

        print(f"Starting root extraction: total_tokens={total_tokens}, missing={missing_tokens}")

        while True:
            batch = _fetch_missing_batch(session, batch_size)
            if not batch:
                break

            for token in batch:
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

                processed += 1
                if processed % commit_batch == 0:
                    session.commit()

                now = time.monotonic()
                if now - last_progress_time >= progress_interval_seconds:
                    total_tokens, missing_tokens = _count_tokens(session)
                    done = total_tokens - missing_tokens
                    bar = _format_bar(done, total_tokens)
                    print(
                        f"Progress {bar} done={done} missing={missing_tokens} "
                        f"processed={processed} updated={updated}"
                    )
                    last_progress_time = now

            session.commit()

        total_tokens, missing_tokens = _count_tokens(session)
        done = total_tokens - missing_tokens
        bar = _format_bar(done, total_tokens)
        print(
            f"Complete {bar} done={done} missing={missing_tokens} "
            f"processed={processed} updated={updated}"
        )
        return updated

    finally:
        session.close()
        root_service.save_cache()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract roots for all tokens until none are missing.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=200,
        help="Number of tokens to pull per batch (default: 200)",
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
    parser.add_argument(
        "--progress-interval-seconds",
        type=int,
        default=300,
        help="Print progress every N seconds (default: 300)",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.batch_size < 1:
        print("Error: --batch-size must be >= 1")
        return 2
    if args.commit_batch < 1:
        print("Error: --commit-batch must be >= 1")
        return 2
    if args.progress_interval_seconds < 1:
        print("Error: --progress-interval-seconds must be >= 1")
        return 2

    extract_all(
        batch_size=args.batch_size,
        commit_batch=args.commit_batch,
        allow_algorithmic=args.allow_algorithmic,
        progress_interval_seconds=args.progress_interval_seconds,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
