"""
Direct database test to show tokenization results.
"""
import asyncio
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from backend.db import get_async_session_maker
from backend.models import Token


async def main():
    """Show tokenization results directly from database."""
    print("=" * 70)
    print("QURÁN TOKENIZATION TEST - SURAH AL-FĀTIḤAH")
    print("=" * 70)
    print()
    
    async_session = get_async_session_maker()
    
    async with async_session() as db:
        # Test 1: Get first 10 tokens
        print("1️⃣  First 10 Tokens (GET /quran/tokens?page=1&page_size=10)")
        print("-" * 70)
        
        query = select(Token).limit(10)
        result = await db.execute(query)
        tokens = result.scalars().all()
        
        tokens_list = []
        for token in tokens:
            token_dict = {
                "id": token.id,
                "sura": token.sura,
                "aya": token.aya,
                "position": token.position,
                "text_ar": token.text_ar,
                "normalized": token.normalized,
                "root": token.root,
                "status": token.status,
            }
            tokens_list.append(token_dict)
        
        response = {
            "tokens": tokens_list,
            "total": len(tokens_list),
            "page": 1,
            "page_size": 10
        }
        print(json.dumps(response, ensure_ascii=False, indent=2))
        print()
        
        # Test 2: Get single token by ID
        print("2️⃣  Single Token (GET /quran/token/1)")
        print("-" * 70)
        
        query = select(Token).where(Token.id == 1)
        result = await db.execute(query)
        token = result.scalar_one()
        
        token_response = {
            "id": token.id,
            "sura": token.sura,
            "aya": token.aya,
            "position": token.position,
            "text_ar": token.text_ar,
            "normalized": token.normalized,
            "root": token.root,
            "status": token.status,
            "references": token.references,
            "interpretations": token.interpretations
        }
        print(json.dumps(token_response, ensure_ascii=False, indent=2))
        print()
        
        # Test 3: Get complete verse 1:1 (Bismillah)
        print("3️⃣  Complete Verse 1:1 (GET /quran/verse/1/1)")
        print("-" * 70)
        
        query = (
            select(Token)
            .where(Token.sura == 1, Token.aya == 1)
            .order_by(Token.position)
        )
        result = await db.execute(query)
        verse_tokens = result.scalars().all()
        
        text_ar = " ".join(t.text_ar for t in verse_tokens)
        verse_response = {
            "sura": 1,
            "aya": 1,
            "word_count": len(verse_tokens),
            "text_ar": text_ar,
            "tokens": [
                {
                    "id": t.id,
                    "position": t.position,
                    "text_ar": t.text_ar,
                    "normalized": t.normalized,
                    "root": t.root,
                    "status": t.status
                }
                for t in verse_tokens
            ]
        }
        print(json.dumps(verse_response, ensure_ascii=False, indent=2))
        print()
        
        # Test 4: Get verse 1:2 (Al-Hamdu lillah)
        print("4️⃣  Complete Verse 1:2 (GET /quran/verse/1/2)")
        print("-" * 70)
        
        query = (
            select(Token)
            .where(Token.sura == 1, Token.aya == 2)
            .order_by(Token.position)
        )
        result = await db.execute(query)
        verse_tokens = result.scalars().all()
        
        text_ar = " ".join(t.text_ar for t in verse_tokens)
        verse_response = {
            "sura": 1,
            "aya": 2,
            "word_count": len(verse_tokens),
            "text_ar": text_ar,
            "tokens": [
                {
                    "id": t.id,
                    "position": t.position,
                    "text_ar": t.text_ar,
                    "normalized": t.normalized,
                    "root": t.root,
                    "status": t.status
                }
                for t in verse_tokens
            ]
        }
        print(json.dumps(verse_response, ensure_ascii=False, indent=2))
        print()
        
        # Test 5: Search for "الحمد"
        print("5️⃣  Search Results (GET /quran/search?q=الحمد)")
        print("-" * 70)
        
        search_term = "الحمد"
        query = select(Token).where(
            (Token.text_ar.contains(search_term)) | 
            (Token.normalized.contains(search_term))
        )
        result = await db.execute(query)
        search_tokens = result.scalars().all()
        
        search_response = {
            "query": search_term,
            "total_results": len(search_tokens),
            "tokens": [
                {
                    "id": t.id,
                    "sura": t.sura,
                    "aya": t.aya,
                    "position": t.position,
                    "text_ar": t.text_ar,
                    "normalized": t.normalized,
                    "root": t.root,
                    "status": t.status
                }
                for t in search_tokens
            ]
        }
        print(json.dumps(search_response, ensure_ascii=False, indent=2))
        print()
        
        # Bonus: Complete Surah Al-Fatiha
        print("📖 COMPLETE SURAH AL-FĀTIḤAH")
        print("=" * 70)
        
        query = select(Token).where(Token.sura == 1).order_by(Token.aya, Token.position)
        result = await db.execute(query)
        all_tokens = result.scalars().all()
        
        verses = {}
        for token in all_tokens:
            if token.aya not in verses:
                verses[token.aya] = []
            verses[token.aya].append(token)
        
        for aya_num, aya_tokens in sorted(verses.items()):
            arabic_text = " ".join(t.text_ar for t in aya_tokens)
            normalized_text = " ".join(t.normalized for t in aya_tokens)
            print(f"\nVerse 1:{aya_num}")
            print(f"  Arabic:     {arabic_text}")
            print(f"  Normalized: {normalized_text}")
            print(f"  Words:      {len(aya_tokens)}")
        
        print()
        print("=" * 70)
        print("✅ TOKENIZATION TEST COMPLETE")
        print("=" * 70)
        print()
        
        # Statistics
        total_query = select(Token)
        total_result = await db.execute(total_query)
        total_tokens = len(total_result.scalars().all())
        
        surah1_query = select(Token).where(Token.sura == 1)
        surah1_result = await db.execute(surah1_query)
        surah1_tokens = len(surah1_result.scalars().all())
        
        print("📊 Database Statistics:")
        print(f"  Total tokens in database: {total_tokens}")
        print(f"  Surah 1 (Al-Fatiha) tokens: {surah1_tokens}")
        print(f"  Surah 1 verses: {len(verses)}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
