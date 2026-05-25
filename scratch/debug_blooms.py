import asyncio
import os
import sys
import io
import re

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from ocr_pipeline import extract_blooms

async def debug_blooms():
    file_path = r'backend\uploads\e7e767bf-99cb-46d9-a4b2-3ad21a9e7498_DM QUESTION BANK.pdf'
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    import pdfplumber
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        # Page 2 is where the continuation is
        page = pdf.pages[1] 
        table = page.extract_tables()[0]
        row = table[0] # The very first row of page 2
        qno = str(row[0] or "").strip()
        qtext = str(row[1] or "").strip()
        blooms_cell = str(row[3] or "").strip() if len(row) > 3 else ""
        
        detected_blooms = extract_blooms(blooms_cell) or extract_blooms(qtext)
        print(f"Row: QNo='{qno}' | Text='{qtext[:50]}...' | BloomsCell='{blooms_cell}' | DetectedBlooms='{detected_blooms}'")

if __name__ == "__main__":
    # We need to read file_bytes
    with open(r'backend\uploads\e7e767bf-99cb-46d9-a4b2-3ad21a9e7498_DM QUESTION BANK.pdf', 'rb') as f:
        file_bytes = f.read()
    
    asyncio.run(debug_blooms())
