#!/usr/bin/env python3
"""
Buckwalter to Arabic converter for Quran Corpus roots
"""

# Buckwalter transliteration to Arabic mapping
BUCKWALTER_TO_ARABIC = {
    'A': 'ا',  # alif
    'b': 'ب',  # ba
    't': 'ت',  # ta
    'v': 'ث',  # tha
    'j': 'ج',  # jeem
    'H': 'ح',  # ha
    'x': 'خ',  # kha
    'd': 'د',  # dal
    '*': 'ذ',  # dhal
    'r': 'ر',  # ra
    'z': 'ز',  # zay
    's': 'س',  # seen
    '$': 'ش',  # sheen
    'S': 'ص',  # sad
    'D': 'ض',  # dad
    'T': 'ط',  # ta
    'Z': 'ظ',  # za
    'E': 'ع',  # ain
    'g': 'غ',  # ghain
    'f': 'ف',  # fa
    'q': 'ق',  # qaf
    'k': 'ك',  # kaf
    'l': 'ل',  # lam
    'm': 'م',  # meem
    'n': 'ن',  # noon
    'h': 'ه',  # ha
    'w': 'و',  # waw
    'y': 'ي',  # ya
    'Y': 'ى',  # alif maqsurah
    "'": 'ء',  # hamza
    'p': 'ة',  # ta marbuta
    '|': 'آ',  # alif madda
    '>': 'أ',  # hamza on alif
    '<': 'إ',  # hamza under alif
    '&': 'ؤ',  # hamza on waw
    '}': 'ئ',  # hamza on ya
}

def buckwalter_to_arabic(text: str) -> str:
    """
    Convert Buckwalter transliteration to Arabic
    
    Args:
        text: Buckwalter transliteration (e.g., 'ktb', 'smw', 'rHm')
        
    Returns:
        Arabic text
    """
    result = ''
    for char in text:
        result += BUCKWALTER_TO_ARABIC.get(char, char)
    return result


if __name__ == "__main__":
    print("="*70)
    print("Testing Buckwalter to Arabic Conversion")
    print("="*70)
    
    test_roots = [
        ('smw', 'سمو'),    # name
        ('ktb', 'كتب'),    # write
        ('rHm', 'رحم'),    # mercy
        ('Hmd', 'حمد'),    # praise
        ('Alh', 'اله'),    # Allah
        ('Elm', 'علم'),    # knowledge
        ('qwm', 'قوم'),    # people/stand
        ('hdy', 'هدي'),    # guidance
        ('*hb', 'ذهب'),    # go
        ('$rk', 'شرك'),    # partner/associate
    ]
    
    for buckwalter, expected_arabic in test_roots:
        arabic = buckwalter_to_arabic(buckwalter)
        status = '✓' if arabic == expected_arabic else '✗'
        print(f"{status} {buckwalter:6} -> {arabic:6} (expected: {expected_arabic})")
