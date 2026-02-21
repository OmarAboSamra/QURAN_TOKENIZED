"""
Arabic morphology utilities for the similar-word comparison feature (D7).

Provides:
    compute_pattern()     – Derive the morphological pattern (وزن) of an Arabic word
    levenshtein()         – Compute edit distance between two strings
    find_similar_words()  – Find words within a given edit distance

The pattern algorithm maps each consonant in a word to its corresponding
position in the standard فعل paradigm (ف = first radical, ع = second,
ل = third). Extra letters (prefixes, infixes, suffixes) are kept as-is.

This is a simplified heuristic — full morphological analysis would require
a dedicated Arabic morphological analyzer. The heuristic covers the most
common patterns found in the Qurʾān.
"""
import re
import unicodedata

# Arabic diacritics (tashkeel) Unicode range
_DIACRITICS = re.compile(
    "[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06DC\u06DF-\u06E4\u06E7\u06E8\u06EA-\u06ED]"
)

# Common Arabic prefixes/suffixes that are NOT part of the root
_PREFIXES = ("ال", "و", "ف", "ب", "ك", "ل", "س")
_SUFFIXES = ("ون", "ين", "ات", "ة", "ه", "ها", "هم", "هن", "كم", "كن", "نا")

# The three paradigm letters
_FA = "ف"
_AIN = "ع"
_LAM = "ل"


def strip_diacritics(text: str) -> str:
    """Remove Arabic diacritics (tashkeel) from text."""
    return _DIACRITICS.sub("", text)


def strip_tatweel(text: str) -> str:
    """Remove Arabic tatweel (kashida) character."""
    return text.replace("\u0640", "")


def normalize_arabic(text: str) -> str:
    """Normalize Arabic text: strip diacritics, tatweel, normalize hamza forms."""
    text = strip_diacritics(text)
    text = strip_tatweel(text)
    # Normalize hamza carriers to bare alif
    text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ٱ", "ا")
    return text


def compute_pattern(word: str, root: str | None = None) -> str | None:
    """
    Compute the morphological pattern (وزن) of an Arabic word.

    Args:
        word: Arabic word (diacritics optional, will be stripped).
        root: Three-letter root string (e.g. "كتب"). If None, the pattern
              cannot be computed and None is returned.

    Returns:
        Pattern string using ف/ع/ل paradigm (e.g. "فعل", "افعال", "مفعول"),
        or None if the root is missing or the word cannot be mapped.

    Examples:
        >>> compute_pattern("كتاب", "كتب")
        'فعال'
        >>> compute_pattern("مكتوب", "كتب")
        'مفعول'
        >>> compute_pattern("استغفر", "غفر")
        'استفعل'
    """
    if not root or not word:
        return None

    word = normalize_arabic(word)
    root = normalize_arabic(root)

    # We need at least the root letters
    root_letters = list(root)
    if len(root_letters) < 2:
        return None

    # Map paradigm letters based on root length
    paradigm = [_FA, _AIN, _LAM]
    if len(root_letters) > 3:
        # Quadriliteral root: فعلل
        paradigm = [_FA, _AIN, _LAM, _LAM]

    # Build pattern by walking through the word and matching root letters
    pattern_chars: list[str] = []
    root_idx = 0

    for char in word:
        if root_idx < len(root_letters) and char == root_letters[root_idx]:
            # This character matches the next root letter
            if root_idx < len(paradigm):
                pattern_chars.append(paradigm[root_idx])
            else:
                pattern_chars.append(_LAM)
            root_idx += 1
        else:
            # Extra letter (prefix, infix, suffix) — keep as-is
            pattern_chars.append(char)

    # Only valid if we consumed all root letters
    if root_idx < len(root_letters):
        return None

    return "".join(pattern_chars)


def levenshtein(s1: str, s2: str) -> int:
    """
    Compute the Levenshtein edit distance between two strings.

    This is a standard dynamic-programming implementation, O(m·n) time
    and O(min(m,n)) space.
    """
    if len(s1) < len(s2):
        return levenshtein(s2, s1)

    if len(s2) == 0:
        return len(s1)

    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            # Insertion, deletion, substitution
            cost = 0 if c1 == c2 else 1
            curr_row.append(
                min(
                    curr_row[j] + 1,       # insertion
                    prev_row[j + 1] + 1,   # deletion
                    prev_row[j] + cost,     # substitution
                )
            )
        prev_row = curr_row

    return prev_row[-1]
