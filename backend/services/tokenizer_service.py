"""
Tokenization service for Qur'an text processing.

Converts raw Qur'an text (with full Arabic diacritics) into individual
word tokens suitable for storage in the Token table.

Pipeline:
    1. Read input file (format: "sura|aya|text" per line)
    2. Split each verse into words by whitespace
    3. Normalize each word: remove diacritics, unify letter forms
    4. Produce WordToken dataclass objects with location metadata
    5. Optionally export to CSV for offline inspection

Normalization rules:
    - Remove tashkeel (ًٌٍَُِّ etc.)
    - Unify hamza variants (أإآٱ → ا)
    - Alef maksura to Ya (ى → ي)
    - Ta marbuta to Ha (ة → ه)
"""
import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class WordToken:
    """Represents a single word token from the Qur'an."""

    sura: int
    aya: int
    position: int
    text_ar: str
    normalized: str


class TokenizerService:
    """
    Service for tokenizing Qur'an text into individual words.
    
    This service handles:
    - Word-level tokenization
    - Arabic text normalization (removing diacritics)
    - Position tracking within verses
    """

    # Arabic diacritical marks to remove for normalization
    ARABIC_DIACRITICS = re.compile(
        r"[\u064B-\u065F\u0670\u06D6-\u06DC\u06DF-\u06ED\u08D4-\u08E1\u08D4-\u08ED\uFE70-\uFE7F]"
    )

    # Punctuation and special characters to remove
    ARABIC_PUNCTUATION = re.compile(r"[۝۞﴿﴾،؛؟]")

    def __init__(self) -> None:
        """Initialize the tokenizer service."""
        pass

    def normalize_arabic(self, text: str) -> str:
        """
        Normalize Arabic text by removing diacritics and special characters.
        
        Args:
            text: Original Arabic text with diacritics
            
        Returns:
            Normalized text without diacritics
        """
        # Remove diacritics
        text = self.ARABIC_DIACRITICS.sub("", text)
        
        # Remove punctuation
        text = self.ARABIC_PUNCTUATION.sub("", text)
        
        # Normalize common character variants
        text = text.replace("ٱ", "ا")  # Alef wasla to regular Alef
        text = text.replace("أ", "ا")  # Hamza on Alef
        text = text.replace("إ", "ا")  # Hamza under Alef
        text = text.replace("آ", "ا")  # Alef with madda
        text = text.replace("ى", "ي")  # Alef maksura to Ya
        text = text.replace("ة", "ه")  # Ta marbuta to Ha
        
        # Remove extra whitespace
        text = " ".join(text.split())
        
        return text.strip()

    def tokenize_verse(
        self,
        text: str,
        sura: int,
        aya: int,
    ) -> list[WordToken]:
        """
        Tokenize a single verse into word tokens.
        
        Args:
            text: Verse text in Arabic
            sura: Surah number (1-114)
            aya: Verse number (1-based)
            
        Returns:
            List of WordToken objects
        """
        tokens: list[WordToken] = []
        
        # Split by whitespace to get individual words
        words = text.strip().split()
        
        for position, word in enumerate(words):
            # Skip empty words
            if not word.strip():
                continue
            
            # Clean the word
            text_ar = word.strip()
            normalized = self.normalize_arabic(text_ar)
            
            # Skip if normalized text is empty
            if not normalized:
                continue
            
            token = WordToken(
                sura=sura,
                aya=aya,
                position=position,
                text_ar=text_ar,
                normalized=normalized,
            )
            tokens.append(token)
        
        return tokens

    def tokenize_file(
        self,
        input_path: Path,
        output_csv_path: Optional[Path] = None,
    ) -> list[WordToken]:
        """
        Tokenize entire Qur'an from a text file.
        
        Expected format: Each line should be "sura|aya|text"
        or "sura:aya text"
        or numbered format.
        
        Args:
            input_path: Path to input text file
            output_csv_path: Optional path to write CSV output
            
        Returns:
            List of all word tokens
        """
        all_tokens: list[WordToken] = []
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        with open(input_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                
                if not line or line.startswith("#"):
                    continue
                
                # Try to parse the line
                tokens = self._parse_line(line, line_num)
                all_tokens.extend(tokens)
        
        # Write to CSV if path provided
        if output_csv_path:
            self.write_tokens_to_csv(all_tokens, output_csv_path)
        
        return all_tokens

    def _parse_line(self, line: str, line_num: int) -> list[WordToken]:
        """Parse a single line from the input file."""
        # Try format: sura|aya|text
        if "|" in line:
            parts = line.split("|", 2)
            if len(parts) == 3:
                try:
                    sura = int(parts[0].strip())
                    aya = int(parts[1].strip())
                    text = parts[2].strip()
                    return self.tokenize_verse(text, sura, aya)
                except ValueError:
                    pass
        
        # Try format: sura:aya text
        if ":" in line:
            parts = line.split(None, 1)
            if len(parts) == 2:
                ref, text = parts
                if ":" in ref:
                    try:
                        sura_str, aya_str = ref.split(":")
                        sura = int(sura_str.strip())
                        aya = int(aya_str.strip())
                        return self.tokenize_verse(text, sura, aya)
                    except ValueError:
                        pass
        
        # If we can't parse, warn and skip
        print(f"Warning: Could not parse line {line_num}: {line[:50]}...")
        return []

    def write_tokens_to_csv(
        self,
        tokens: list[WordToken],
        output_path: Path,
    ) -> None:
        """
        Write tokens to CSV file.
        
        Args:
            tokens: List of WordToken objects
            output_path: Path to output CSV file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow(["sura", "aya", "position", "text_ar", "normalized"])
            
            # Write data
            for token in tokens:
                writer.writerow([
                    token.sura,
                    token.aya,
                    token.position,
                    token.text_ar,
                    token.normalized,
                ])
        
        print(f"[OK] Wrote {len(tokens)} tokens to {output_path}")
