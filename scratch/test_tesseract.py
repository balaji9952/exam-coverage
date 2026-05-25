import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from ocr_pipeline import _ocr_pil_image

async def test_tesseract():
    file_path = r'backend\uploads\f2893e29-2972-4f1b-9e6b-1954169a42b2_dm question paper(2).pdf'
    import pdfplumber
    with pdfplumber.open(file_path) as pdf:
        page = pdf.pages[0]
        img = page.to_image(resolution=300).original
        text = await _ocr_pil_image(img)
        print("--- TESSERACT OCR ---")
        print(text[:1000])

if __name__ == "__main__":
    asyncio.run(test_tesseract())
