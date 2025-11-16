"""
Test suite for verifying data completeness of Sura 1 and Sura 2.

This module contains tests to ensure:
- All expected verses are present in the database
- All verses have been tokenized correctly
- Root extraction has been performed (though coverage may vary)
- Data integrity is maintained
"""
import random
from typing import List

import pytest
from sqlalchemy.orm import Session

from backend.db import get_sync_session_maker
from backend.models import Token, TokenStatus


class TestDataCompleteness:
    """Test suite for data completeness verification."""
    
    @pytest.fixture(scope="class")
    def db_session(self) -> Session:
        """Provide database session for tests."""
        session_maker = get_sync_session_maker()
        session = session_maker()
        yield session
        session.close()
    
    def test_sura_1_has_all_verses(self, db_session: Session):
        """Verify Sura 1 (Al-Fatihah) has all 7 verses tokenized."""
        # Sura 1 should have 7 verses
        expected_verses = 7
        
        # Get distinct verse numbers for Sura 1
        verses = db_session.query(Token.aya).filter(
            Token.sura == 1
        ).distinct().all()
        
        verse_numbers = sorted([v[0] for v in verses])
        
        assert len(verse_numbers) == expected_verses, (
            f"Sura 1 should have {expected_verses} verses, found {len(verse_numbers)}"
        )
        assert verse_numbers == list(range(1, expected_verses + 1)), (
            f"Sura 1 verses should be 1-{expected_verses}, found {verse_numbers}"
        )
        
        # Verify we have tokens for Sura 1
        token_count = db_session.query(Token).filter(Token.sura == 1).count()
        assert token_count > 0, "Sura 1 should have at least one token"
        assert token_count >= 29, f"Sura 1 should have at least 29 tokens, found {token_count}"
        
        print(f"\n✓ Sura 1: {expected_verses} verses, {token_count} tokens")
    
    def test_sura_2_has_all_verses(self, db_session: Session):
        """Verify Sura 2 (Al-Baqarah) has all 286 verses tokenized."""
        # Sura 2 should have 286 verses
        expected_verses = 286
        
        # Get distinct verse numbers for Sura 2
        verses = db_session.query(Token.aya).filter(
            Token.sura == 2
        ).distinct().all()
        
        verse_numbers = sorted([v[0] for v in verses])
        
        assert len(verse_numbers) == expected_verses, (
            f"Sura 2 should have {expected_verses} verses, found {len(verse_numbers)}"
        )
        
        # Check for any gaps in verse numbers
        missing_verses = set(range(1, expected_verses + 1)) - set(verse_numbers)
        assert not missing_verses, f"Sura 2 is missing verses: {sorted(missing_verses)}"
        
        # Verify we have tokens for Sura 2
        token_count = db_session.query(Token).filter(Token.sura == 2).count()
        assert token_count > 0, "Sura 2 should have at least one token"
        assert token_count >= 6000, f"Sura 2 should have at least 6000 tokens, found {token_count}"
        
        print(f"\n✓ Sura 2: {expected_verses} verses, {token_count} tokens")
    
    def test_all_tokens_have_normalized_text(self, db_session: Session):
        """Verify all tokens have normalized text (no NULL values)."""
        # Check Sura 1
        null_count_s1 = db_session.query(Token).filter(
            Token.sura == 1,
            Token.normalized.is_(None)
        ).count()
        assert null_count_s1 == 0, f"Sura 1 has {null_count_s1} tokens without normalized text"
        
        # Check Sura 2
        null_count_s2 = db_session.query(Token).filter(
            Token.sura == 2,
            Token.normalized.is_(None)
        ).count()
        assert null_count_s2 == 0, f"Sura 2 has {null_count_s2} tokens without normalized text"
        
        print(f"\n✓ All tokens have normalized text")
    
    def test_token_sample_has_valid_structure(self, db_session: Session):
        """Verify a random sample of tokens has valid data structure."""
        # Get random sample from each sura
        sura_1_tokens = db_session.query(Token).filter(Token.sura == 1).all()
        sura_2_tokens = db_session.query(Token).filter(Token.sura == 2).limit(100).all()
        
        sample_tokens = (
            random.sample(sura_1_tokens, min(10, len(sura_1_tokens))) +
            random.sample(sura_2_tokens, min(20, len(sura_2_tokens)))
        )
        
        for token in sample_tokens:
            # Check required fields
            assert token.id is not None, f"Token missing ID"
            assert token.sura in [1, 2], f"Invalid sura: {token.sura}"
            assert token.aya >= 1, f"Invalid aya: {token.aya}"
            assert token.position >= 0, f"Invalid position: {token.position}"
            assert token.text_ar, f"Token {token.id} missing Arabic text"
            assert token.normalized, f"Token {token.id} missing normalized text"
            assert token.status in [s.value for s in TokenStatus], f"Invalid status: {token.status}"
            
            # If token has a root, verify it's not empty
            if token.root:
                assert len(token.root) > 0, f"Token {token.id} has empty root"
                assert token.status == TokenStatus.VERIFIED.value, (
                    f"Token {token.id} has root but status is {token.status}"
                )
        
        print(f"\n✓ Validated {len(sample_tokens)} random token samples")
    
    def test_root_extraction_attempted(self, db_session: Session):
        """Verify root extraction has been attempted for both suras."""
        # Count tokens with roots in Sura 1
        sura_1_with_roots = db_session.query(Token).filter(
            Token.sura == 1,
            Token.root.isnot(None)
        ).count()
        
        # Count tokens with roots in Sura 2  
        sura_2_with_roots = db_session.query(Token).filter(
            Token.sura == 2,
            Token.root.isnot(None)
        ).count()
        
        # We expect at least SOME roots (even with limited fallback dictionary)
        total_with_roots = sura_1_with_roots + sura_2_with_roots
        assert total_with_roots > 0, "No roots found - root extraction may not have run"
        
        # Get total tokens
        total_tokens = db_session.query(Token).filter(
            Token.sura.in_([1, 2])
        ).count()
        
        coverage_pct = (total_with_roots / total_tokens * 100) if total_tokens > 0 else 0
        
        print(f"\n✓ Root extraction completed:")
        print(f"  Sura 1: {sura_1_with_roots} tokens with roots")
        print(f"  Sura 2: {sura_2_with_roots} tokens with roots")
        print(f"  Total coverage: {coverage_pct:.1f}% ({total_with_roots}/{total_tokens})")
        
        # Note: We don't assert a minimum coverage since we're using a limited fallback dictionary
        # The important thing is that root extraction ran without errors
    
    def test_no_duplicate_tokens_per_position(self, db_session: Session):
        """Verify no duplicate tokens exist for the same (sura, aya, position)."""
        from sqlalchemy import func
        
        # Check for duplicates in Sura 1
        duplicates_s1 = db_session.query(
            Token.sura, Token.aya, Token.position, func.count(Token.id).label('count')
        ).filter(
            Token.sura == 1
        ).group_by(
            Token.sura, Token.aya, Token.position
        ).having(
            func.count(Token.id) > 1
        ).all()
        
        assert len(duplicates_s1) == 0, f"Sura 1 has duplicate tokens: {duplicates_s1}"
        
        # Check for duplicates in Sura 2 (sample check - full check would be slow)
        duplicates_s2 = db_session.query(
            Token.sura, Token.aya, Token.position, func.count(Token.id).label('count')
        ).filter(
            Token.sura == 2,
            Token.aya <= 10  # Check first 10 verses as sample
        ).group_by(
            Token.sura, Token.aya, Token.position
        ).having(
            func.count(Token.id) > 1
        ).all()
        
        assert len(duplicates_s2) == 0, f"Sura 2 (sample) has duplicate tokens: {duplicates_s2}"
        
        print(f"\n✓ No duplicate tokens found")
    
    def test_verse_word_counts_reasonable(self, db_session: Session):
        """Verify verse word counts are within reasonable ranges."""
        from sqlalchemy import func
        
        # Get token counts per verse for Sura 1
        sura_1_verses = db_session.query(
            Token.aya, func.count(Token.id).label('count')
        ).filter(Token.sura == 1).group_by(Token.aya).all()
        
        for aya, count in sura_1_verses:
            assert count >= 1, f"Sura 1, Verse {aya} has no tokens"
            assert count <= 100, f"Sura 1, Verse {aya} has {count} tokens (suspiciously high)"
        
        # Sample check for Sura 2 (first 10 verses)
        sura_2_sample = db_session.query(
            Token.aya, func.count(Token.id).label('count')
        ).filter(
            Token.sura == 2,
            Token.aya <= 10
        ).group_by(Token.aya).all()
        
        for aya, count in sura_2_sample:
            assert count >= 1, f"Sura 2, Verse {aya} has no tokens"
            assert count <= 200, f"Sura 2, Verse {aya} has {count} tokens (suspiciously high)"
        
        print(f"\n✓ Verse word counts are reasonable")


def test_completeness_summary(capsys):
    """Print a summary of data completeness."""
    from backend.db import get_sync_session_maker
    
    session_maker = get_sync_session_maker()
    session = session_maker()
    
    try:
        # Get statistics
        sura_1_tokens = session.query(Token).filter(Token.sura == 1).count()
        sura_1_verses = session.query(Token.aya).filter(Token.sura == 1).distinct().count()
        sura_1_roots = session.query(Token).filter(Token.sura == 1, Token.root.isnot(None)).count()
        
        sura_2_tokens = session.query(Token).filter(Token.sura == 2).count()
        sura_2_verses = session.query(Token.aya).filter(Token.sura == 2).distinct().count()
        sura_2_roots = session.query(Token).filter(Token.sura == 2, Token.root.isnot(None)).count()
        
        print("\n" + "=" * 70)
        print("DATA COMPLETENESS SUMMARY")
        print("=" * 70)
        print(f"\nSura 1 (Al-Fatihah):")
        print(f"  Verses:  {sura_1_verses}/7 ({sura_1_verses/7*100:.0f}%)")
        print(f"  Tokens:  {sura_1_tokens}")
        print(f"  Roots:   {sura_1_roots}/{sura_1_tokens} ({sura_1_roots/sura_1_tokens*100:.1f}%)")
        
        print(f"\nSura 2 (Al-Baqarah):")
        print(f"  Verses:  {sura_2_verses}/286 ({sura_2_verses/286*100:.0f}%)")
        print(f"  Tokens:  {sura_2_tokens}")
        print(f"  Roots:   {sura_2_roots}/{sura_2_tokens} ({sura_2_roots/sura_2_tokens*100:.1f}%)")
        
        print(f"\nTotal:")
        print(f"  Verses:  {sura_1_verses + sura_2_verses}")
        print(f"  Tokens:  {sura_1_tokens + sura_2_tokens}")
        print(f"  Roots:   {sura_1_roots + sura_2_roots}")
        print("=" * 70)
        
    finally:
        session.close()


class TestDatabaseFreshness:
    """Test suite to detect stale cached data and ensure database is current."""
    
    @pytest.fixture(scope="class")
    def db_session(self):
        """Provide database session for tests."""
        session_maker = get_sync_session_maker()
        session = session_maker()
        yield session
        session.close()
    
    def test_expected_token_counts(self, db_session: Session):
        """
        Verify database has expected token counts.
        
        This test catches issues where:
        - Database file is stale/cached
        - Tokenization didn't commit properly
        - Wrong database file is being used
        """
        # Expected counts based on complete Sura 1 + Sura 2
        EXPECTED_SURA_1_TOKENS = 29  # Al-Fatihah has 29 words
        EXPECTED_SURA_2_TOKENS = 6144  # Al-Baqarah tokenized count
        
        sura_1_count = db_session.query(Token).filter(Token.sura == 1).count()
        sura_2_count = db_session.query(Token).filter(Token.sura == 2).count()
        
        assert sura_1_count == EXPECTED_SURA_1_TOKENS, (
            f"Sura 1 token count mismatch: expected {EXPECTED_SURA_1_TOKENS}, got {sura_1_count}. "
            f"Database may be stale or incomplete."
        )
        
        assert sura_2_count == EXPECTED_SURA_2_TOKENS, (
            f"Sura 2 token count mismatch: expected {EXPECTED_SURA_2_TOKENS}, got {sura_2_count}. "
            f"Database may be stale or incomplete."
        )
        
        print(f"\n✓ Database has expected token counts:")
        print(f"  Sura 1: {sura_1_count} tokens")
        print(f"  Sura 2: {sura_2_count} tokens")
    
    def test_sample_verses_exist(self, db_session: Session):
        """
        Verify strategic sample verses exist (beginning, middle, end).
        
        Uses sampling to quickly detect if database is incomplete without
        checking every verse.
        """
        # Sample verses to check: beginning, middle, end of each sura
        test_samples = [
            (1, 1, "Sura 1, Verse 1 (first)"),
            (1, 4, "Sura 1, Verse 4 (middle)"),
            (1, 7, "Sura 1, Verse 7 (last)"),
            (2, 1, "Sura 2, Verse 1 (first)"),
            (2, 143, "Sura 2, Verse 143 (middle)"),
            (2, 286, "Sura 2, Verse 286 (last)"),
        ]
        
        for sura, aya, description in test_samples:
            token_count = db_session.query(Token).filter(
                Token.sura == sura,
                Token.aya == aya
            ).count()
            
            assert token_count > 0, (
                f"{description} has no tokens. "
                f"Database may be incomplete or using old cached data."
            )
        
        print(f"\n✓ All sampled verses exist (beginning/middle/end check)")
    
    def test_root_coverage_by_sampling(self, db_session: Session):
        """
        Check root coverage using strategic sampling.
        
        Samples tokens from different positions to verify:
        - Root extraction ran successfully
        - Results were committed to database
        - Distribution is reasonable (not all in one section)
        """
        # Sample tokens from beginning, middle, end of each sura
        sample_ranges = [
            # (sura, aya_min, aya_max, description)
            (1, 1, 2, "Sura 1 beginning"),
            (1, 6, 7, "Sura 1 end"),
            (2, 1, 10, "Sura 2 beginning"),
            (2, 140, 150, "Sura 2 middle"),
            (2, 280, 286, "Sura 2 end"),
        ]
        
        results = []
        for sura, aya_min, aya_max, description in sample_ranges:
            total = db_session.query(Token).filter(
                Token.sura == sura,
                Token.aya >= aya_min,
                Token.aya <= aya_max
            ).count()
            
            with_roots = db_session.query(Token).filter(
                Token.sura == sura,
                Token.aya >= aya_min,
                Token.aya <= aya_max,
                Token.root.isnot(None)
            ).count()
            
            coverage = (with_roots / total * 100) if total > 0 else 0
            results.append((description, with_roots, total, coverage))
        
        print(f"\n✓ Root coverage by sample region:")
        for desc, with_roots, total, coverage in results:
            print(f"  {desc}: {with_roots}/{total} ({coverage:.1f}%)")
        
        # Verify at least SOME roots exist in EACH region
        # This catches issues where root extraction only partially completed
        for desc, with_roots, total, coverage in results:
            # We expect at least 1-2% coverage even with limited fallback dictionary
            # If coverage is 0%, root extraction likely didn't run for this section
            if total >= 50:  # Only check if sample size is reasonable
                assert with_roots > 0, (
                    f"{desc} has no roots ({with_roots}/{total}). "
                    f"Root extraction may not have completed fully."
                )
    
    def test_no_all_missing_status(self, db_session: Session):
        """
        Verify not ALL tokens have 'missing' status.
        
        If all tokens are marked 'missing', root extraction never ran or failed.
        """
        total_tokens = db_session.query(Token).filter(
            Token.sura.in_([1, 2])
        ).count()
        
        missing_tokens = db_session.query(Token).filter(
            Token.sura.in_([1, 2]),
            Token.status == TokenStatus.MISSING.value
        ).count()
        
        # Allow some missing tokens, but not 100%
        missing_pct = (missing_tokens / total_tokens * 100) if total_tokens > 0 else 0
        
        print(f"\n✓ Token status distribution:")
        print(f"  Total: {total_tokens}")
        print(f"  Missing: {missing_tokens} ({missing_pct:.1f}%)")
        print(f"  Has roots: {total_tokens - missing_tokens} ({100-missing_pct:.1f}%)")
        
        # If more than 99% are missing, root extraction likely failed
        assert missing_pct < 99, (
            f"{missing_pct:.1f}% of tokens have 'missing' status. "
            f"Root extraction may have failed to run or commit results."
        )

