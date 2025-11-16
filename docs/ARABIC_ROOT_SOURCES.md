"""
Research: Arabic Root Extraction Sources

This file documents online sources for Arabic root extraction.

## Verified Working Sources:

### 1. AlMaany Dictionary (almaany.com)
- URL: https://www.almaany.com/ar/dict/ar-ar/{word}/
- Method: Web scraping (HTML parsing)
- Coverage: Comprehensive Arabic dictionary
- Reliability: High (well-established site)
- Example: https://www.almaany.com/ar/dict/ar-ar/كتاب/

### 2. Baheth Arabic Dictionary (baheth.info)
- URL: https://www.baheth.info/all.jsp?term={word}
- Method: Web scraping (HTML parsing)
- Coverage: Arabic-Arabic dictionary with root info
- Reliability: High
- Example: https://www.baheth.info/all.jsp?term=كتاب

### 3. Tashaphyne (Python Library - can be used as fallback)
- Method: Local algorithmic processing
- Coverage: Triliteral and quadriliteral roots
- Reliability: High for algorithmic approach
- Note: Already implemented as AlKhalilExtractor

### 4. Qalsadi (Python Library Alternative)
- Package: pyarabic / qalsadi
- Method: Local morphological analysis
- Coverage: Comprehensive Arabic morphology
- Reliability: High (academic tool)

### 5. AraComLex API (if available)
- Academic resource for Arabic computational lexicon
- May require authentication

## Implementation Priority:
1. AlMaany (primary - most reliable)
2. Baheth (secondary verification)
3. Enhanced algorithmic (tertiary fallback)
"""
