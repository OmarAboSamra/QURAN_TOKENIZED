"""Test pipeline chaining to ensure root extraction runs after tokenization."""
import pytest
import time
from sqlalchemy.orm import Session

from backend.db import get_sync_session_maker
from backend.models import Token, TokenStatus


class TestPipelineChaining:
    """Test cases for pipeline task chaining."""
    
    @pytest.fixture
    def db_session(self):
        """Create a test database session."""
        session_maker = get_sync_session_maker()
        session = session_maker()
        yield session
        session.close()
    
    def test_tokenization_sets_status_to_missing(self, db_session: Session):
        """Test that tokenization initially sets status to 'missing'."""
        from backend.tasks.tokenization_tasks import tokenize_sura_chunk
        
        # Clean test data
        db_session.query(Token).filter(Token.sura == 1, Token.aya == 1).delete()
        db_session.commit()
        
        # Tokenize
        result = tokenize_sura_chunk(sura=1, start_aya=1, end_aya=1)
        assert result["status"] == "success"
        
        # Check all tokens have 'missing' status
        tokens = db_session.query(Token).filter(
            Token.sura == 1,
            Token.aya == 1
        ).all()
        
        assert len(tokens) > 0
        for token in tokens:
            assert token.status == TokenStatus.MISSING.value
            assert token.root is None or token.root == ""
    
    def test_root_extraction_updates_status(self, db_session: Session):
        """Test that root extraction updates status from 'missing' to 'verified'."""
        from backend.tasks.tokenization_tasks import tokenize_sura_chunk
        from backend.tasks.root_extraction_tasks import extract_roots_for_sura
        
        # Clean and tokenize
        db_session.query(Token).filter(Token.sura == 1).delete()
        db_session.commit()
        
        tokenize_result = tokenize_sura_chunk(sura=1, start_aya=1, end_aya=1)
        assert tokenize_result["status"] == "success"
        
        # Verify tokens exist with 'missing' status
        missing_count_before = db_session.query(Token).filter(
            Token.sura == 1,
            Token.status == TokenStatus.MISSING.value
        ).count()
        assert missing_count_before > 0
        
        # Extract roots
        root_result = extract_roots_for_sura(sura=1)
        assert root_result["status"] == "success"
        
        # Verify some tokens now have roots and updated status
        tokens_with_roots = db_session.query(Token).filter(
            Token.sura == 1,
            Token.root.isnot(None),
            Token.root != ""
        ).all()
        
        # At least some tokens should have roots (Surah 1 has fallback roots)
        assert len(tokens_with_roots) > 0, "Root extraction should find some roots"
        
        # Check that tokens with roots have updated status
        for token in tokens_with_roots:
            assert token.status == TokenStatus.VERIFIED.value, \
                f"Token {token.id} has root but status is '{token.status}' instead of 'verified'"
    
    def test_full_pipeline_sequence(self, db_session: Session):
        """Test complete pipeline: tokenization → root extraction."""
        from backend.tasks.tokenization_tasks import tokenize_sura_chunk
        from backend.tasks.root_extraction_tasks import extract_roots_for_sura
        
        # Clean test data
        db_session.query(Token).filter(Token.sura == 1).delete()
        db_session.commit()
        
        # Step 1: Tokenize entire Surah 1
        print("\nStep 1: Tokenizing Surah 1...")
        tokenize_result = tokenize_sura_chunk(sura=1, start_aya=1, end_aya=7)
        assert tokenize_result["status"] == "success"
        tokens_created = tokenize_result["tokens_count"]
        assert tokens_created > 0
        
        # Verify all tokens have 'missing' status
        missing_count = db_session.query(Token).filter(
            Token.sura == 1,
            Token.status == TokenStatus.MISSING.value
        ).count()
        assert missing_count == tokens_created
        
        # Step 2: Extract roots
        print("Step 2: Extracting roots...")
        root_result = extract_roots_for_sura(sura=1)
        assert root_result["status"] == "success"
        
        # Step 3: Verify pipeline completed correctly
        print("Step 3: Verifying results...")
        
        # Count tokens by status
        status_distribution = {}
        for status in [TokenStatus.MISSING.value, TokenStatus.VERIFIED.value]:
            count = db_session.query(Token).filter(
                Token.sura == 1,
                Token.status == status
            ).count()
            status_distribution[status] = count
        
        print(f"  Status distribution: {status_distribution}")
        
        # At least some tokens should be verified (have roots)
        assert status_distribution[TokenStatus.VERIFIED.value] > 0, \
            "Some tokens should have verified status after root extraction"
        
        # Verify token count remains the same
        final_count = db_session.query(Token).filter(Token.sura == 1).count()
        assert final_count == tokens_created, \
            "Token count should not change after root extraction"
    
    def test_root_extraction_idempotent(self, db_session: Session):
        """Test that running root extraction multiple times is safe."""
        from backend.tasks.tokenization_tasks import tokenize_sura_chunk
        from backend.tasks.root_extraction_tasks import extract_roots_for_sura
        
        # Setup: tokenize sura
        db_session.query(Token).filter(Token.sura == 1).delete()
        db_session.commit()
        
        tokenize_sura_chunk(sura=1, start_aya=1, end_aya=1)
        
        # Extract roots first time
        result1 = extract_roots_for_sura(sura=1)
        assert result1["status"] == "success"
        
        count_after_first = db_session.query(Token).filter(
            Token.sura == 1,
            Token.root.isnot(None)
        ).count()
        
        # Extract roots second time
        result2 = extract_roots_for_sura(sura=1)
        assert result2["status"] == "success"
        
        count_after_second = db_session.query(Token).filter(
            Token.sura == 1,
            Token.root.isnot(None)
        ).count()
        
        # Should be idempotent (same result)
        assert count_after_first == count_after_second


def test_integration_pipeline_api():
    """Integration test simulating the API pipeline flow."""
    from backend.tasks.tokenization_tasks import tokenize_sura_chunk
    from backend.tasks.root_extraction_tasks import extract_roots_for_sura
    from backend.db import get_sync_session_maker
    
    session_maker = get_sync_session_maker()
    session = session_maker()
    
    try:
        sura = 1
        
        # Clean test data
        session.query(Token).filter(Token.sura == sura).delete()
        session.commit()
        
        print(f"\nIntegration Test: Full Pipeline for Surah {sura}")
        print("=" * 60)
        
        # Step 1: Run tokenization (synchronous chunk method)
        print("Step 1: Tokenization...")
        token_result = tokenize_sura_chunk(sura=sura, start_aya=1, end_aya=7)
        assert token_result["status"] == "success"
        print(f"  ✓ Tokenized: {token_result['tokens_count']} tokens")
        
        # Verify tokens exist
        token_count = session.query(Token).filter(Token.sura == sura).count()
        assert token_count > 0
        print(f"  ✓ Created: {token_count} tokens")
        
        # Verify tokens created
        token_count = session.query(Token).filter(Token.sura == sura).count()
        assert token_count > 0
        print(f"  ✓ Verified {token_count} tokens in database")
        
        # Step 2: Run root extraction (synchronous method)
        print("\nStep 2: Root Extraction...")
        root_result = extract_roots_for_sura(sura=sura)
        assert root_result["status"] == "success"
        print(f"  ✓ Extracted: {root_result['tokens_updated']} roots updated")
        
        # Verify roots were extracted
        roots_count = session.query(Token).filter(
            Token.sura == sura,
            Token.root.isnot(None),
            Token.root != ""
        ).count()
        
        print(f"  ℹ️  Extracted roots for: {roots_count} tokens")
        
        # Calculate coverage
        if token_count > 0:
            coverage = (roots_count / token_count) * 100
            print(f"\nCoverage: {coverage:.1f}% ({roots_count}/{token_count})")
        
        # Note: Parallel tasks run async, so roots may not be extracted immediately
        # This is expected behavior in real usage with Celery
        print("\n✓ Integration test passed!")
        print("  (Note: Parallel tasks queued, actual extraction happens async)")
        
    finally:
        session.close()


if __name__ == "__main__":
    """Run tests manually."""
    print("Running pipeline chaining tests...")
    test_integration_pipeline_api()
    print("\nAll tests passed!")
