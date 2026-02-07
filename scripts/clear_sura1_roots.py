#!/usr/bin/env python3
"""
Clear roots from Sura 1 to re-extract with Corpus
"""
import sys
import asyncio
sys.path.insert(0, 'C:/quran-backend')

from backend.db import get_async_session_maker
from backend.models import Token
from sqlalchemy import update

async def main():
    async_session = get_async_session_maker()
    async with async_session() as db:
        # Clear roots for Sura 1
        result = await db.execute(
            update(Token)
            .where(Token.sura == 1)
            .values(root=None, root_sources={}, status='missing')
        )
        
        await db.commit()
        
        print(f"Cleared roots for {result.rowcount} tokens in Sura 1")
        print("Ready to re-extract with Corpus extractor!")

asyncio.run(main())
