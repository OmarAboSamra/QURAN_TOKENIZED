#!/usr/bin/env python3
"""
Check root extraction progress
"""
import sys
import asyncio
sys.path.insert(0, 'C:/quran-backend')

from backend.db import get_async_session_maker
from backend.models import Token
from sqlalchemy import select, func

async def main():
    async_session = get_async_session_maker()
    async with async_session() as db:
        # Count tokens by root status for Sura 1
        result = await db.execute(
            select(
                func.count(Token.id).label('total'),
                func.count(Token.root).label('with_root'),
            )
            .filter(Token.sura == 1)
        )
        row = result.first()
        
        print("="*70)
        print("Sura 1 Root Extraction Progress")
        print("="*70)
        print(f"Total tokens: {row.total}")
        print(f"With roots:   {row.with_root}")
        print(f"Progress:     {row.with_root}/{row.total} ({100*row.with_root/row.total if row.total > 0 else 0:.1f}%)")
        print("="*70)
        
        # Show sample roots
        result = await db.execute(
            select(Token)
            .filter(Token.sura == 1, Token.root.isnot(None))
            .limit(10)
        )
        tokens = result.scalars().all()
        
        if tokens:
            print("\nSample extracted roots:")
            for t in tokens:
                sources = list(t.root_sources.keys()) if t.root_sources else []
                print(f"  {t.sura}:{t.aya}:{t.position} {t.normalized:15} -> {t.root:6} (sources: {', '.join(sources)})")

asyncio.run(main())
