"""Tests for tokenization service."""
import pytest
from pathlib import Path

from backend.services import TokenizerService, WordToken


class TestTokenizerService:
    """Tests for TokenizerService."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.tokenizer = TokenizerService()

    def test_normalize_arabic_removes_diacritics(self) -> None:
        """Test that diacritics are removed."""
        text = "بِسْمِ ٱللَّهِ"
        normalized = self.tokenizer.normalize_arabic(text)
        
        # Should not contain diacritics
        assert "ِ" not in normalized  # Kasra
        assert "ْ" not in normalized  # Sukun
        assert "ّ" not in normalized  # Shadda

    def test_normalize_arabic_converts_variants(self) -> None:
        """Test that character variants are normalized."""
        # Alef variants
        assert self.tokenizer.normalize_arabic("أ") == "ا"
        assert self.tokenizer.normalize_arabic("إ") == "ا"
        assert self.tokenizer.normalize_arabic("آ") == "ا"
        
        # Ya/Alef maksura
        assert self.tokenizer.normalize_arabic("ى") == "ي"
        
        # Ta marbuta
        assert self.tokenizer.normalize_arabic("ة") == "ه"

    def test_tokenize_verse_splits_words(self) -> None:
        """Test that verse is split into words."""
        text = "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ"
        tokens = self.tokenizer.tokenize_verse(text, sura=1, aya=1)
        
        assert len(tokens) == 4
        assert all(isinstance(t, WordToken) for t in tokens)
        
        # Check positions
        assert tokens[0].position == 0
        assert tokens[1].position == 1
        assert tokens[2].position == 2
        assert tokens[3].position == 3
        
        # Check sura and aya
        assert all(t.sura == 1 for t in tokens)
        assert all(t.aya == 1 for t in tokens)

    def test_tokenize_verse_normalizes_text(self) -> None:
        """Test that tokens include normalized text."""
        text = "بِسْمِ ٱللَّهِ"
        tokens = self.tokenizer.tokenize_verse(text, sura=1, aya=1)
        
        assert tokens[0].text_ar == "بِسْمِ"
        assert tokens[0].normalized == "بسم"
        
        assert tokens[1].text_ar == "ٱللَّهِ"
        # Normalized should not have diacritics
        assert "َ" not in tokens[1].normalized
        assert "ِ" not in tokens[1].normalized

    def test_tokenize_verse_handles_empty_input(self) -> None:
        """Test handling of empty verse."""
        tokens = self.tokenizer.tokenize_verse("", sura=1, aya=1)
        assert len(tokens) == 0

    def test_tokenize_verse_handles_whitespace(self) -> None:
        """Test handling of extra whitespace."""
        text = "بِسْمِ    ٱللَّهِ  ٱلرَّحْمَٰنِ"
        tokens = self.tokenizer.tokenize_verse(text, sura=1, aya=1)
        
        # Should have 3 tokens despite extra whitespace
        assert len(tokens) == 3

    def test_parse_line_pipe_format(self) -> None:
        """Test parsing line with pipe format."""
        line = "1|1|بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ"
        tokens = self.tokenizer._parse_line(line, 1)
        
        assert len(tokens) == 3
        assert tokens[0].sura == 1
        assert tokens[0].aya == 1

    def test_parse_line_colon_format(self) -> None:
        """Test parsing line with colon format."""
        line = "1:1 بِسْمِ ٱللَّهِ"
        tokens = self.tokenizer._parse_line(line, 1)
        
        assert len(tokens) == 2
        assert tokens[0].sura == 1
        assert tokens[0].aya == 1

    def test_parse_line_invalid_format(self) -> None:
        """Test handling of invalid line format."""
        line = "This is not a valid format"
        tokens = self.tokenizer._parse_line(line, 1)
        
        # Should return empty list for invalid format
        assert len(tokens) == 0


@pytest.mark.asyncio
class TestRootExtraction:
    """Tests for root extraction (placeholder tests)."""

    async def test_root_extractor_placeholder(self) -> None:
        """Placeholder test for root extraction."""
        # TODO: Add tests when root extraction is implemented
        assert True


@pytest.mark.asyncio
class TestDiscrepancyChecker:
    """Tests for discrepancy checking."""

    async def test_discrepancy_checker_placeholder(self) -> None:
        """Placeholder test for discrepancy checker."""
        from backend.services import DiscrepancyChecker
        
        checker = DiscrepancyChecker()
        
        # Test with no discrepancy
        sources = {
            "source1": "جلس",
            "source2": "جلس",
            "source3": "جلس",
        }
        
        report = checker.check_discrepancy("جالس", sources)
        
        assert report.consensus_root == "جلس"
        assert report.has_discrepancy is False
        assert report.confidence == 1.0
        assert report.recommended_status == "verified"
    
    async def test_discrepancy_checker_with_conflict(self) -> None:
        """Test discrepancy detection with conflicting roots."""
        from backend.services import DiscrepancyChecker
        
        checker = DiscrepancyChecker()
        
        # Test with discrepancy
        sources = {
            "source1": "جلس",
            "source2": "قعد",
            "source3": "جلس",
        }
        
        report = checker.check_discrepancy("جالس", sources)
        
        assert report.has_discrepancy is True
        assert report.consensus_root == "جلس"  # Most common
        assert report.confidence < 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
