"""Test duplicate tokenization handling."""
import pytest
from sqlalchemy.orm import Session

from backend.db import get_sync_session_maker
from backend.models import Token, TokenStatus
from backend.tasks.tokenization_tasks import tokenize_sura_chunk


class TestDuplicateTokenization:
    """Test cases for duplicate tokenization scenarios."""
    
    @pytest.fixture
    def db_session(self):
        """Create a test database session."""
        session_maker = get_sync_session_maker()
        session = session_maker()
        yield session
        session.close()
    
    def test_tokenize_verse_once(self, db_session: Session):
        """Test that a verse can be tokenized successfully."""
        # Clean any existing data for sura 1, aya 1
        db_session.query(Token).filter(
            Token.sura == 1,
            Token.aya == 1
        ).delete()
        db_session.commit()
        
        # Tokenize sura 1, verse 1
        result = tokenize_sura_chunk(sura=1, start_aya=1, end_aya=1)
        
        assert result["status"] == "success"
        assert result["sura"] == 1
        assert result["tokens_count"] > 0
        
        # Verify tokens exist in database
        tokens = db_session.query(Token).filter(
            Token.sura == 1,
            Token.aya == 1
        ).all()
        
        assert len(tokens) == result["tokens_count"]
    
    def test_tokenize_same_verse_twice_no_error(self, db_session: Session):
        """Test that tokenizing the same verse twice doesn't cause errors."""
        # Tokenize sura 1, verse 1 first time
        result1 = tokenize_sura_chunk(sura=1, start_aya=1, end_aya=1)
        
        # Count tokens after first run
        count1 = db_session.query(Token).filter(
            Token.sura == 1,
            Token.aya == 1
        ).count()
        
        # Tokenize same verse second time - should handle duplicates gracefully
        result2 = tokenize_sura_chunk(sura=1, start_aya=1, end_aya=1)
        
        # Should return success (either with 0 tokens or same count)
        assert result2["status"] == "success"
        
        # Count tokens after second run - should be the same
        count2 = db_session.query(Token).filter(
            Token.sura == 1,
            Token.aya == 1
        ).count()
        
        assert count1 == count2, "Token count should not change on duplicate tokenization"
    
    def test_tokenize_multiple_verses_with_partial_duplicates(self, db_session: Session):
        """Test tokenizing a range where some verses already exist."""
        # Clean test data
        db_session.query(Token).filter(
            Token.sura == 1,
            Token.aya.in_([1, 2, 3])
        ).delete()
        db_session.commit()
        
        # Tokenize verses 1-2
        result1 = tokenize_sura_chunk(sura=1, start_aya=1, end_aya=2)
        assert result1["status"] == "success"
        initial_count = result1["tokens_count"]
        
        # Tokenize verses 2-3 (verse 2 is duplicate, verse 3 is new)
        result2 = tokenize_sura_chunk(sura=1, start_aya=2, end_aya=3)
        
        # Should succeed without throwing IntegrityError
        assert result2["status"] == "success"
        
        # Verify we have tokens for all three verses
        verse_counts = {}
        for aya in [1, 2, 3]:
            count = db_session.query(Token).filter(
                Token.sura == 1,
                Token.aya == aya
            ).count()
            verse_counts[aya] = count
            assert count > 0, f"Verse {aya} should have tokens"
    
    def test_tokenize_sura_idempotent(self, db_session: Session):
        """Test that tokenizing entire sura multiple times is idempotent."""
        sura = 1
        
        # Get initial count
        initial_count = db_session.query(Token).filter(Token.sura == sura).count()
        
        # Tokenize sura 1 completely
        result1 = tokenize_sura_chunk(sura=sura, start_aya=1, end_aya=7)
        
        # Get count after first tokenization
        count_after_first = db_session.query(Token).filter(Token.sura == sura).count()
        
        # Tokenize again
        result2 = tokenize_sura_chunk(sura=sura, start_aya=1, end_aya=7)
        
        # Get count after second tokenization
        count_after_second = db_session.query(Token).filter(Token.sura == sura).count()
        
        # Count should be the same (idempotent)
        assert count_after_first == count_after_second
        
        # Both results should indicate success
        assert result1["status"] == "success"
        assert result2["status"] == "success"
    
    def test_parallel_tokenization_simulation(self, db_session: Session):
        """Test that parallel chunk processing handles overlaps correctly."""
        # Clean test data
        db_session.query(Token).filter(Token.sura == 2).delete()
        db_session.commit()
        
        # Simulate parallel processing with overlapping chunks
        # This could happen if chunk_size doesn't divide evenly
        
        # Chunk 1: verses 1-3
        result1 = tokenize_sura_chunk(sura=2, start_aya=1, end_aya=3)
        
        # Chunk 2: verses 3-5 (verse 3 overlaps)
        result2 = tokenize_sura_chunk(sura=2, start_aya=3, end_aya=5)
        
        # Both should succeed
        assert result1["status"] == "success"
        assert result2["status"] == "success"
        
        # Verify we have exactly one set of tokens for each verse
        for aya in [1, 2, 3, 4, 5]:
            tokens = db_session.query(Token).filter(
                Token.sura == 2,
                Token.aya == aya
            ).all()
            
            # Check each position appears exactly once
            positions = [t.position for t in tokens]
            assert len(positions) == len(set(positions)), \
                f"Verse 2:{aya} has duplicate positions: {positions}"


def test_integration_full_pipeline():
    """Integration test for full tokenization pipeline with duplicates."""
    session_maker = get_sync_session_maker()
    session = session_maker()
    
    try:
        # Clean test data
        session.query(Token).filter(Token.sura == 1).delete()
        session.commit()
        
        # Process sura 1 completely
        result = tokenize_sura_chunk(sura=1, start_aya=1, end_aya=7)
        assert result["status"] == "success"
        
        initial_count = result["tokens_count"]
        assert initial_count > 0
        
        # Verify all verses have tokens
        for aya in range(1, 8):
            count = session.query(Token).filter(
                Token.sura == 1,
                Token.aya == aya
            ).count()
            assert count > 0, f"Verse 1:{aya} should have tokens"
        
        # Process again - should handle gracefully
        result2 = tokenize_sura_chunk(sura=1, start_aya=1, end_aya=7)
        assert result2["status"] == "success"
        
        # Total count should remain the same
        final_count = session.query(Token).filter(Token.sura == 1).count()
        assert final_count == initial_count
        
    finally:
        session.close()


if __name__ == "__main__":
    """Run tests manually for debugging."""
    print("Running duplicate tokenization tests...")
    print()
    
    # Test 1: Single verse twice
    print("Test 1: Tokenize same verse twice...")
    test_integration_full_pipeline()
    print("✓ PASS")
    print()
    
    print("All tests completed successfully!")
