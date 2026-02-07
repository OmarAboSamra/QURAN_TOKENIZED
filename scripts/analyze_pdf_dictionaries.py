"""
Analyze PDF dictionaries to understand their structure and extract sample text.

This script examines each PDF dictionary to:
1. Check if it's text-based or requires OCR
2. Extract sample pages to understand structure
3. Identify patterns for root word entries
4. Determine parsing strategies
"""

import fitz  # PyMuPDF
from pathlib import Path
import re
from collections import defaultdict
import json

# Arabic character ranges for detection
ARABIC_REGEX = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+')

def analyze_pdf(pdf_path: Path) -> dict:
    """
    Analyze a single PDF dictionary.
    
    Returns:
        Dictionary with analysis results
    """
    print(f"\n{'='*80}")
    print(f"Analyzing: {pdf_path.name}")
    print(f"{'='*80}")
    
    results = {
        'filename': pdf_path.name,
        'path': str(pdf_path),
        'total_pages': 0,
        'has_text': False,
        'sample_pages': {},
        'arabic_density': 0,
        'structure_notes': []
    }
    
    try:
        doc = fitz.open(pdf_path)
        results['total_pages'] = len(doc)
        
        print(f"Total pages: {results['total_pages']}")
        
        # Sample pages: first, middle, and last
        sample_indices = [
            0,  # First page
            len(doc) // 4,  # Quarter
            len(doc) // 2,  # Middle
            3 * len(doc) // 4,  # Three-quarters
            len(doc) - 1  # Last page
        ]
        
        total_text_length = 0
        total_arabic_chars = 0
        
        for page_num in sample_indices:
            if page_num < len(doc):
                page = doc[page_num]
                text = page.get_text()
                
                # Count Arabic characters
                arabic_matches = ARABIC_REGEX.findall(text)
                arabic_text = ''.join(arabic_matches)
                
                total_text_length += len(text)
                total_arabic_chars += len(arabic_text)
                
                # Store sample
                results['sample_pages'][page_num] = {
                    'text_length': len(text),
                    'arabic_chars': len(arabic_text),
                    'preview': text[:1000] if text else '[No text extracted]',
                    'has_images': len(page.get_images()) > 0
                }
                
                print(f"\nPage {page_num + 1}:")
                print(f"  Text length: {len(text)} chars")
                print(f"  Arabic chars: {len(arabic_text)} chars")
                print(f"  Images: {len(page.get_images())}")
                
                if text:
                    results['has_text'] = True
                    # Show first 500 chars
                    preview = text[:500]
                    print(f"  Preview: {preview[:200]}...")
                    
                    # Try to find root patterns (Arabic words of 2-4 letters)
                    potential_roots = re.findall(r'[\u0600-\u06FF]{2,4}(?:\s|$)', text[:2000])
                    if potential_roots:
                        print(f"  Potential roots found: {potential_roots[:10]}")
        
        # Calculate overall Arabic density
        if total_text_length > 0:
            results['arabic_density'] = total_arabic_chars / total_text_length
            print(f"\nArabic density: {results['arabic_density']:.2%}")
        
        # Structure analysis
        if results['has_text']:
            results['structure_notes'].append("PDF has extractable text")
        else:
            results['structure_notes'].append("PDF appears to be scanned images (OCR required)")
        
        # Check for table of contents or structure
        toc = doc.get_toc()
        if toc:
            results['structure_notes'].append(f"Has table of contents with {len(toc)} entries")
            print(f"\nTable of Contents ({len(toc)} entries):")
            for entry in toc[:10]:
                print(f"  {entry}")
        
        doc.close()
        
    except Exception as e:
        results['error'] = str(e)
        print(f"Error analyzing PDF: {e}")
    
    return results


def extract_dictionary_structure(pdf_path: Path, max_pages: int = 50) -> dict:
    """
    Extract detailed structure from a dictionary PDF to identify root entry patterns.
    
    Returns:
        Dictionary with structural patterns
    """
    print(f"\n{'='*80}")
    print(f"Extracting structure from: {pdf_path.name}")
    print(f"{'='*80}")
    
    patterns = {
        'filename': pdf_path.name,
        'entry_patterns': [],
        'root_markers': [],
        'definition_markers': [],
        'sample_entries': []
    }
    
    try:
        doc = fitz.open(pdf_path)
        
        # Analyze first max_pages to find patterns
        for page_num in range(min(max_pages, len(doc))):
            page = doc[page_num]
            text = page.get_text()
            
            if not text or len(text) < 100:
                continue
            
            # Look for common dictionary patterns:
            # 1. Bold or large font for root words
            # 2. Indentation or special markers
            # 3. Definition markers (like colons, parentheses)
            
            # Extract text with formatting
            blocks = page.get_text("dict")["blocks"]
            
            for block in blocks[:20]:  # Sample first 20 blocks per page
                if "lines" in block:
                    for line in block["lines"]:
                        line_text = ""
                        for span in line["spans"]:
                            line_text += span["text"]
                        
                        # Check if line might be a root entry (2-4 Arabic letters at start)
                        root_match = re.match(r'^[\u0600-\u06FF]{2,4}\s*[:؛\-]', line_text)
                        if root_match:
                            patterns['sample_entries'].append({
                                'page': page_num + 1,
                                'text': line_text[:200]
                            })
            
            # Sample a few pages
            if page_num < 5 or (10 < page_num < 15) or (30 < page_num < 35):
                print(f"\n--- Page {page_num + 1} sample ---")
                print(text[:1000])
        
        doc.close()
        
    except Exception as e:
        patterns['error'] = str(e)
        print(f"Error extracting structure: {e}")
    
    return patterns


def main():
    """Analyze all PDF dictionaries."""
    pdf_dir = Path(r"c:\quran-backend\Downloaded books")
    
    if not pdf_dir.exists():
        print(f"Directory not found: {pdf_dir}")
        return
    
    pdf_files = list(pdf_dir.glob("*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in {pdf_dir}")
        return
    
    print(f"Found {len(pdf_files)} PDF files")
    
    all_results = []
    
    for pdf_path in pdf_files:
        # Basic analysis
        results = analyze_pdf(pdf_path)
        all_results.append(results)
        
        # If text is extractable, try to understand structure
        if results.get('has_text'):
            structure = extract_dictionary_structure(pdf_path, max_pages=20)
            results['structure_patterns'] = structure
    
    # Save results
    output_file = Path(r"c:\quran-backend\pdf_analysis_results.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*80}")
    print(f"Analysis complete. Results saved to: {output_file}")
    print(f"{'='*80}")
    
    # Summary
    print("\nSUMMARY:")
    for result in all_results:
        print(f"\n{result['filename']}:")
        print(f"  Pages: {result['total_pages']}")
        print(f"  Has text: {result['has_text']}")
        print(f"  Arabic density: {result.get('arabic_density', 0):.2%}")
        for note in result.get('structure_notes', []):
            print(f"  - {note}")


if __name__ == "__main__":
    main()
