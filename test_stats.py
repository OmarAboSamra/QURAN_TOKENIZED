"""Quick test to see the actual API error."""
import asyncio
import sys
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, 'c:/quran-backend')

from backend.db import get_db_session
from backend.repositories.token_repository import TokenRepository


async def test_stats():
    """Test the stats endpoint logic."""
    print("Testing stats endpoint...")
    
    async for db in get_db_session():
        token_repo = TokenRepository()
        
        # Test total token count
        try:
            total_tokens = await token_repo.acount(db)
            print(f"[OK] Total tokens: {total_tokens}")
        except Exception as e:
            print(f"[ERROR] getting total tokens: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Test verse count
        try:
            from sqlalchemy import func, select
            from backend.models import Token
            
            verse_subq = select(Token.sura, Token.aya).distinct().subquery()
            verse_result = await db.execute(select(func.count()).select_from(verse_subq))
            total_verses = verse_result.scalar() or 0
            print(f"[OK] Total verses: {total_verses}")
        except Exception as e:
            print(f"[ERROR] getting verse count: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Test root count
        try:
            root_count_query = select(func.count(func.distinct(Token.root))).where(
                Token.root.isnot(None)
            )
            root_result = await db.execute(root_count_query)
            total_roots = root_result.scalar() or 0
            print(f"[OK] Total roots: {total_roots}")
        except Exception as e:
            print(f"[ERROR] getting root count: {e}")
            import traceback
            traceback.print_exc()
            return
        
        print("\n[SUCCESS] All stats queries successful!")
        print(f"Stats: {total_tokens} tokens, {total_verses} verses, {total_roots} roots")
        break


if __name__ == "__main__":
    asyncio.run(test_stats())
