"""Generate comprehensive root mappings for Sura 1 and 2."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.db import get_sync_session_maker
from backend.models import Token


def generate_placeholder_roots():
    """
    Generate placeholder roots for all words in Sura 1 and 2.
    
    Note: In a production system, these would come from:
    1. Quranic Arabic Corpus API
    2. A comprehensive Arabic morphology database
    3. Manual verification by Arabic language experts
    
    For now, we'll use a simplified root extraction algorithm:
    - Remove common prefixes (ال, و, ف, ب, ل, ك)
    - Remove common suffixes (ون, ين, ان, ات, ة)
    - Take first 3-4 letters as potential root
    """
    print("=" * 70)
    print("  Generating Placeholder Roots for Sura 1 & 2")
    print("=" * 70)
    print()
    print("[!] WARNING: These are PLACEHOLDER roots generated algorithmically.")
    print("    Real Arabic roots require linguistic analysis.")
    print("    For production, integrate with Quranic Arabic Corpus or")
    print("    use a verified morphological database.")
    print()
    
    session_maker = get_sync_session_maker()
    session = session_maker()
    
    # Get all unique normalized words
    words = session.query(Token.normalized).filter(
        Token.sura.in_([1, 2])
    ).distinct().all()
    
    print(f"[1/3] Found {len(words)} unique words to process")
    print()
    
    # Generate placeholder roots
    roots_dict = {}
    
    # Common Arabic prefixes and suffixes
    prefixes = ['ال', 'و', 'ف', 'ب', 'ل', 'ك', 'لل']
    suffixes = ['ون', 'ين', 'ان', 'ات', 'ة', 'ه', 'ها', 'هم', 'كم', 'نا']
    
    for (word,) in words:
        root = word
        
        # Remove prefixes
        for prefix in sorted(prefixes, key=len, reverse=True):
            if root.startswith(prefix) and len(root) > len(prefix):
                root = root[len(prefix):]
                break
        
        # Remove suffixes  
        for suffix in sorted(suffixes, key=len, reverse=True):
            if root.endswith(suffix) and len(root) > len(suffix):
                root = root[:-len(suffix)]
                break
        
        # Take first 3-4 letters as root (most Arabic roots are triliteral)
        if len(root) > 4:
            root = root[:4]
        elif len(root) == 0:
            root = word  # Fallback to original word
        
        roots_dict[word] = root
    
    print(f"[2/3] Generated {len(roots_dict)} placeholder roots")
    print()
    
    # Save to file
    cache_path = Path("data/quran_roots_comprehensive.json")
    
    # Format: {word: {"placeholder": root}}
    formatted_cache = {
        word: {"placeholder": root}
        for word, root in roots_dict.items()
    }
    
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(formatted_cache, f, ensure_ascii=False, indent=2)
    
    print(f"[3/3] Saved to {cache_path}")
    print()
    print("=" * 70)
    print("  NEXT STEPS:")
    print("=" * 70)
    print()
    print("1. Update root_extractor.py to load from this file")
    print("2. Run root extraction: POST /pipeline/extract-roots?sura=1")
    print("3. Run root extraction: POST /pipeline/extract-roots?sura=2")
    print("4. Run tests: pytest tests/test_data_completeness.py")
    print()
    print("For production:")
    print("- Replace placeholder roots with verified linguistic data")
    print("- Integrate with Quranic Arabic Corpus")
    print("- Add manual verification workflow")
    print()
    
    session.close()


if __name__ == "__main__":
    generate_placeholder_roots()
