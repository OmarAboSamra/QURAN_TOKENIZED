"""
Extract images from sample pages to visually inspect dictionary structure.
We'll convert a few pages to images to understand the layout.
"""

import fitz  # PyMuPDF
from pathlib import Path
from PIL import Image
import io

def extract_sample_pages_as_images(pdf_path: Path, page_numbers: list, output_dir: Path):
    """
    Extract specific pages as images for visual inspection.
    
    Args:
        pdf_path: Path to PDF
        page_numbers: List of 0-indexed page numbers to extract
        output_dir: Directory to save images
    """
    output_dir.mkdir(exist_ok=True)
    
    doc = fitz.open(pdf_path)
    
    for page_num in page_numbers:
        if page_num < len(doc):
            page = doc[page_num]
            
            # Render page to image at high resolution
            mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PIL Image
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            
            # Save
            output_file = output_dir / f"{pdf_path.stem}_page_{page_num + 1}.png"
            img.save(output_file)
            print(f"Saved: {output_file}")
    
    doc.close()


def main():
    pdf_dir = Path(r"c:\quran-backend\Downloaded books")
    output_dir = Path(r"c:\quran-backend\pdf_samples")
    
    # For each dictionary, extract a few representative pages
    # Focus on pages that should contain root entries (skip cover/intro)
    
    samples = {
        "Noor-Book.com  القاموس المحيط ط الحديث.pdf": [28, 29, 30, 50, 100],  # After intro, in "حرف الألف"
        "Noor-Book.com  المعجم الوجيز.pdf": [10, 11, 12, 50, 100],  # Similar pattern
        "Noor-Book.com  قاموس الطالب مرادفات وأضداد 3 .pdf": [5, 10, 15, 20, 25],  # Smaller, sample more
    }
    
    for pdf_name, pages in samples.items():
        pdf_path = pdf_dir / pdf_name
        if pdf_path.exists():
            print(f"\nExtracting from: {pdf_name}")
            extract_sample_pages_as_images(pdf_path, pages, output_dir)
        else:
            print(f"Not found: {pdf_path}")


if __name__ == "__main__":
    main()
