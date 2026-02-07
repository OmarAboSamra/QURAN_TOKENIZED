#!/usr/bin/env python3
"""
Check database tokens for Sura 1:1
"""
import sys
import asyncio
sys.path.insert(0, 'C:/quran-backend')

from backend.db import get_async_session_maker
from backend.models import Token
from sqlalchemy import select

async def main():
    async_session = get_async_session_maker()
    async with async_session() as db:
        result = await db.execute(
            select(Token)
            .filter(Token.sura == 1, Token.aya == 1)
            .order_by(Token.position)
        )
        tokens = result.scalars().all()
        
        print("Sura 1:1 tokens:")
        for t in tokens:
            print(f"  pos{t.position}: {t.text_ar:20} (norm: {t.normalized})")

asyncio.run(main())
