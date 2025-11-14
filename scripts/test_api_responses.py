"""
Test script to demonstrate API responses with real Surah Al-Fatiha data.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.db import get_async_session_maker
from backend.api.routes_quran import (
    get_tokens,
    get_token,
    get_verse,
    search_tokens,
)
from sqlalchemy import select
from backend.models import Token
import json


async def main():
    """Run API endpoint tests."""
    print("=" * 70)
    print("QURÁN ANALYSIS API - TEST RESPONSES")
    print("=" * 70)
    print()
    
    # Get async session
    async_session = get_async_session_maker()
    
    async with async_session() as db:
        # Test 1: GET /quran/tokens?page=1&page_size=10
        print("1️⃣  GET /quran/tokens?page=1&page_size=10")
        print("-" * 70)
        
        result = await get_tokens(page=1, page_size=10, db=db)
        print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))
        print()
        
        # Test 2: GET /quran/token/1
        print("2️⃣  GET /quran/token/1")
        print("-" * 70)
        
        token = await get_token(token_id=1, db=db)
        print(json.dumps(token.model_dump(), ensure_ascii=False, indent=2))
        print()
        
        # Test 3: GET /quran/verse/1/1 (Bismillah)
        print("3️⃣  GET /quran/verse/1/1")
        print("-" * 70)
        
        verse = await get_verse(sura=1, aya=1, db=db)
        print(json.dumps(verse.model_dump(), ensure_ascii=False, indent=2))
        print()
        
        # Test 4: GET /quran/verse/1/2 (Al-Hamdu lillah)
        print("4️⃣  GET /quran/verse/1/2")
        print("-" * 70)
        
        verse2 = await get_verse(sura=1, aya=2, db=db)
        print(json.dumps(verse2.model_dump(), ensure_ascii=False, indent=2))
        print()
        
        # Test 5: Search for "الحمد"
        print("5️⃣  GET /quran/search?q=الحمد")
        print("-" * 70)
        
        search_result = await search_tokens(q="الحمد", page=1, page_size=10, db=db)
        print(json.dumps(search_result.model_dump(), ensure_ascii=False, indent=2))
        print()
        
        # Test 6: Get all tokens from Surah 1
        print("6️⃣  GET /quran/tokens?sura=1&page_size=50")
        print("-" * 70)
        
        surah_tokens = await get_tokens(
            page=1,
            page_size=50,
            sura=1,
            db=db
        )
        print(json.dumps(surah_tokens.model_dump(), ensure_ascii=False, indent=2))
        print()
        
        # Summary
        print("=" * 70)
        print("✅ ALL TESTS COMPLETED")
        print("=" * 70)
        print()
        print("Summary:")
        print(f"  Total tokens in database: {surah_tokens.total}")
        print(f"  Surah 1 (Al-Fatiha) tokens: {len(surah_tokens.tokens)}")
        print()
        print("Complete Surah Al-Fatiha text:")
        print("-" * 70)
        
        # Reconstruct verses
        query = select(Token).where(Token.sura == 1).order_by(Token.aya, Token.position)
        result = await db.execute(query)
        all_tokens = result.scalars().all()
        
        current_aya = None
        for token in all_tokens:
            if token.aya != current_aya:
                if current_aya is not None:
                    print()
                current_aya = token.aya
                print(f"Verse {token.aya}: ", end="")
            print(token.text_ar, end=" ")
        print()


if __name__ == "__main__":
    asyncio.run(main())
