"""
Export the current root assignments for cross-checking by a second agent.

Produces a JSON file with every unique (normalized_word → assigned_root)
mapping along with an example Arabic text form and occurrence count,
so the second agent can evaluate each mapping independently.
"""
import sys, json, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, ".")

from sqlalchemy import select, func
from backend.db import get_sync_session_maker, init_db
from backend.models.token_model import Token

init_db()
S = get_sync_session_maker()
with S() as s:
    stmt = (
        select(
            Token.normalized,
            Token.root,
            func.min(Token.text_ar).label("example_text"),
            func.count().label("count"),
            func.min(Token.sura).label("first_sura"),
            func.min(Token.aya).label("first_aya"),
        )
        .group_by(Token.normalized, Token.root)
        .order_by(func.count().desc())
    )
    
    results = []
    for r in s.execute(stmt):
        results.append({
            "normalized": r.normalized,
            "assigned_root": r.root,
            "example_text": r.example_text,
            "count": r.count,
            "first_occurrence": f"{r.first_sura}:{r.first_aya}",
        })

    with open("data/root_assignments_for_review.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"Exported {len(results)} word→root mappings to data/root_assignments_for_review.json")
