"""
Download complete Quran text from API and convert to required format.
Uses quran.com API to fetch all 114 suras with Arabic text.
"""
import httpx
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def download_quran():
    """Download complete Quran text from API."""
    output_file = Path(__file__).parent.parent / "data" / "quran_original_text.txt"
    
    print("=" * 60)
    print("Downloading Complete Quran Text")
    print("=" * 60)
    print(f"Output: {output_file}")
    print()
    
    lines = []
    lines.append("# Complete Qur'an Text Data")
    lines.append("# Format: sura|aya|arabic_text")
    lines.append("# Source: Quran.com API (Uthmani text)")
    lines.append("#")
    lines.append("")
    
    total_verses = 0
    
    # Download all 114 suras
    with httpx.Client(timeout=30.0) as client:
        for sura_num in range(1, 115):
            print(f"Downloading Sura {sura_num}...", end=" ", flush=True)
            
            try:
                # Use Quran.com API v4 - get Uthmani text
                url = f"https://api.quran.com/api/v4/quran/verses/uthmani?chapter_number={sura_num}"
                response = client.get(url)
                response.raise_for_status()
                data = response.json()
                
                verses = data.get("verses", [])
                
                for verse in verses:
                    verse_key = verse.get("verse_key", "")  # Format: sura:aya
                    text_uthmani = verse.get("text_uthmani", "")
                    
                    # Extract aya number from verse_key
                    if ":" in verse_key:
                        _, aya = verse_key.split(":")
                        aya = int(aya)
                    else:
                        # Fallback to verse id
                        aya = verse.get("id", 0)
                    
                    line = f"{sura_num}|{aya}|{text_uthmani}"
                    lines.append(line)
                    total_verses += 1
                
                print(f"✓ ({len(verses)} verses)")
                
            except Exception as e:
                print(f"✗ Error: {e}")
                return False
    
    # Write to file
    print()
    print("Writing to file...")
    output_file.write_text("\n".join(lines), encoding="utf-8")
    
    print()
    print("=" * 60)
    print(f"[OK] Downloaded {total_verses} verses from 114 suras")
    print(f"[OK] Saved to: {output_file}")
    print("=" * 60)
    print()
    print("Next step: Run tokenization")
    print("  python scripts/tokenize_quran.py --save-to-db")
    
    return True


if __name__ == "__main__":
    success = download_quran()
    sys.exit(0 if success else 1)
