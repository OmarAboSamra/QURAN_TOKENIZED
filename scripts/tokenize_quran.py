"""
Offline script to tokenize the entire Qur'an by word.

This script reads the original Qur'an text and produces a CSV file
with one row per word, containing: sura, aya, position, text_ar, normalized.

Usage:
    python scripts/tokenize_quran.py
    python scripts/tokenize_quran.py --input data/quran_original_text.txt --output data/quran_tokens_word.csv
"""
import argparse
import sys
from pathlib import Path

# Add parent directory to path to import backend modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import get_settings
from backend.db import get_sync_session_maker, init_db
from backend.models import Token, TokenStatus, Verse
from backend.services import TokenizerService


def main() -> None:
    """Main entry point for tokenization script."""
    parser = argparse.ArgumentParser(
        description="Tokenize Qur'an text into word-level CSV"
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="Path to input Qur'an text file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Path to output CSV file",
    )
    parser.add_argument(
        "--save-to-db",
        action="store_true",
        help="Also save tokens to database",
    )
    
    args = parser.parse_args()
    settings = get_settings()
    
    # Determine input and output paths
    input_path = args.input if args.input else Path(settings.quran_data_path)
    output_path = args.output if args.output else Path(settings.output_csv_path)
    
    print("=" * 60)
    print("Qur'an Tokenization Script")
    print("=" * 60)
    print(f"Input file:  {input_path}")
    print(f"Output file: {output_path}")
    print()
    
    # Check if input file exists
    if not input_path.exists():
        print(f"[ERROR] Input file not found: {input_path}")
        print()
        print("Please provide a Qur'an text file with format:")
        print("  sura|aya|text")
        print("  or")
        print("  sura:aya text")
        print()
        print("Example:")
        print("  1|1|بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ")
        print("  1:1 بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ")
        sys.exit(1)
    
    # Initialize tokenizer
    print("Initializing tokenizer...")
    tokenizer = TokenizerService()
    
    # Tokenize file
    print(f"Reading and tokenizing {input_path}...")
    try:
        tokens = tokenizer.tokenize_file(input_path, output_path)
        print()
        print("=" * 60)
        print(f"[OK] Successfully tokenized {len(tokens)} words")
        print(f"[OK] CSV output written to: {output_path}")
        print("=" * 60)
        
        # Display statistics
        if tokens:
            unique_suras = len(set(t.sura for t in tokens))
            unique_ayas = len(set((t.sura, t.aya) for t in tokens))
            
            print()
            print("Statistics:")
            print(f"  Total words:     {len(tokens)}")
            print(f"  Unique suras:    {unique_suras}")
            print(f"  Unique verses:   {unique_ayas}")
            print(f"  Avg words/verse: {len(tokens) / unique_ayas:.1f}")
        
        # Save to database if requested
        if args.save_to_db:
            print()
            print("Saving tokens to database...")
            init_db()
            
            SessionMaker = get_sync_session_maker()
            with SessionMaker() as session:
                # Clear existing data
                session.query(Token).delete()
                session.query(Verse).delete()

                # Group tokens by (sura, aya) to create Verse rows (D3)
                from collections import defaultdict
                verse_groups: dict[tuple[int, int], list] = defaultdict(list)
                for token in tokens:
                    verse_groups[(token.sura, token.aya)].append(token)
                
                # Create Verse rows first so we can set verse_id on tokens
                verse_id_lookup: dict[tuple[int, int], int] = {}
                for (sura, aya), verse_tokens in sorted(verse_groups.items()):
                    text_ar = " ".join(t.text_ar for t in verse_tokens)
                    text_normalized = " ".join(t.normalized for t in verse_tokens)
                    verse = Verse(
                        sura=sura,
                        aya=aya,
                        text_ar=text_ar,
                        text_normalized=text_normalized,
                        word_count=len(verse_tokens),
                    )
                    session.add(verse)
                    session.flush()  # Get the auto-generated verse.id
                    verse_id_lookup[(sura, aya)] = verse.id

                # Create Token rows with verse_id FK set
                for token in tokens:
                    db_token = Token(
                        sura=token.sura,
                        aya=token.aya,
                        position=token.position,
                        text_ar=token.text_ar,
                        normalized=token.normalized,
                        status=TokenStatus.MISSING.value,
                        verse_id=verse_id_lookup.get((token.sura, token.aya)),
                    )
                    session.add(db_token)
                
                session.commit()
                print(f"[OK] Saved {len(tokens)} tokens + {len(verse_id_lookup)} verses to database")
        
        print()
        print("Next steps:")
        print("  1. Run root extraction: python scripts/fetch_roots.py")
        print("  2. Reconcile discrepancies: python scripts/reconcile_roots.py")
        print("  3. Build references: python scripts/index_references.py")
        print("  4. Start API server: python backend/main.py")
        
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Error during tokenization: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
