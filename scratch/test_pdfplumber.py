import asyncio
import os
import sys

async def test_pdfplumber():
    file_path = r'backend\uploads\f2893e29-2972-4f1b-9e6b-1954169a42b2_dm question paper(2).pdf'
    import pdfplumber
    with pdfplumber.open(file_path) as pdf:
        page = pdf.pages[0]
        
        print("--- DEFAULT ---")
        print(page.extract_text()[:500])
        
        print("\n--- X=1, Y=1 ---")
        print(page.extract_text(x_tolerance=1, y_tolerance=1)[:500])
        
        print("\n--- X=3, Y=3 ---")
        print(page.extract_text(x_tolerance=3, y_tolerance=3)[:500])

if __name__ == "__main__":
    asyncio.run(test_pdfplumber())
