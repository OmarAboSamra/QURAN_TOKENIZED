"""
Script to fetch complete sura data from Al-Quran Cloud API and append to data file.

Usage:
    python scripts/fetch_sura_data.py --sura 2
    python scripts/fetch_sura_data.py --sura 2 --edition quran-simple-enhanced
"""
import argparse
import sys
from pathlib import Path
import requests


def fetch_sura_from_api(sura_number: int, edition: str = "quran-simple-enhanced") -> list[tuple[int, int, str]]:
    """
    Fetch sura data from Al-Quran Cloud API.
    
    Args:
        sura_number: Sura number (1-114)
        edition: Text edition to fetch (default: quran-simple-enhanced for Uthmanic text)
    
    Returns:
        List of tuples: (sura, aya, arabic_text)
    """
    url = f"http://api.alquran.cloud/v1/surah/{sura_number}/{edition}"
    print(f"Fetching Sura {sura_number} from {url}...")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data.get("code") != 200 or data.get("status") != "OK":
            raise Exception(f"API returned error: {data}")
        
        sura_data = data["data"]
        ayahs = sura_data["ayahs"]
        
        print(f"✓ Fetched {len(ayahs)} verses for Sura {sura_number} ({sura_data['englishName']})")
        
        verses = []
        for ayah in ayahs:
            sura = ayah["numberInSurah"]  # This is actually the ayah number
            aya = ayah["numberInSurah"]
            text = ayah["text"]
            verses.append((sura_number, aya, text))
        
        return verses
    
    except requests.RequestException as e:
        print(f"✗ Error fetching data: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error processing data: {e}")
        sys.exit(1)


def read_existing_data(file_path: Path) -> set[tuple[int, int]]:
    """Read existing sura:aya pairs from data file."""
    existing = set()
    if not file_path.exists():
        return existing
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            parts = line.split('|')
            if len(parts) >= 2:
                try:
                    sura = int(parts[0])
                    aya = int(parts[1])
                    existing.add((sura, aya))
                except ValueError:
                    continue
    
    return existing


def append_to_data_file(file_path: Path, verses: list[tuple[int, int, str]], overwrite_sura: bool = False):
    """
    Append verses to data file, skipping duplicates.
    
    Args:
        file_path: Path to data file
        verses: List of (sura, aya, text) tuples
        overwrite_sura: If True, remove existing verses for this sura first
    """
    if not verses:
        print("No verses to add.")
        return
    
    sura_number = verses[0][0]
    
    # Read existing data
    if overwrite_sura and file_path.exists():
        print(f"Removing existing Sura {sura_number} data...")
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        with open(file_path, 'w', encoding='utf-8') as f:
            for line in lines:
                if not line.strip().startswith(f"{sura_number}|"):
                    f.write(line)
        
        existing = read_existing_data(file_path)
    else:
        existing = read_existing_data(file_path)
    
    # Filter out duplicates
    new_verses = [v for v in verses if (v[0], v[1]) not in existing]
    
    if not new_verses:
        print(f"All {len(verses)} verses already exist in the data file.")
        return
    
    # Append new verses
    with open(file_path, 'a', encoding='utf-8') as f:
        if existing:  # Add a newline if file is not empty
            f.write('\n')
        
        for sura, aya, text in new_verses:
            f.write(f"{sura}|{aya}|{text}\n")
    
    print(f"✓ Added {len(new_verses)} new verses to {file_path}")
    if len(new_verses) < len(verses):
        print(f"  (Skipped {len(verses) - len(new_verses)} existing verses)")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Fetch Qur'an sura data from Al-Quran Cloud API"
    )
    parser.add_argument(
        "--sura",
        type=int,
        required=True,
        help="Sura number to fetch (1-114)"
    )
    parser.add_argument(
        "--edition",
        type=str,
        default="quran-simple-enhanced",
        help="Text edition (default: quran-simple-enhanced)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/quran_original_text.txt"),
        help="Output data file path"
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing verses for this sura"
    )
    
    args = parser.parse_args()
    
    if args.sura < 1 or args.sura > 114:
        print(f"✗ Error: Sura number must be between 1 and 114, got {args.sura}")
        sys.exit(1)
    
    print("=" * 70)
    print("Fetch Qur'an Sura Data")
    print("=" * 70)
    print(f"Sura: {args.sura}")
    print(f"Edition: {args.edition}")
    print(f"Output: {args.output}")
    print()
    
    # Fetch data
    verses = fetch_sura_from_api(args.sura, args.edition)
    
    # Append to file
    append_to_data_file(args.output, verses, overwrite_sura=args.overwrite)
    
    print()
    print("=" * 70)
    print("✓ Done!")
    print("=" * 70)


if __name__ == "__main__":
    main()
