import asyncio
import os
import sys

# Add backend to path
sys.path.append(r'd:\man\man\backend')

from ocr_pipeline import process_uploaded_file

async def main():
    pdf_path = r'd:\man\man\sample_question_bank.pdf'
    with open(pdf_path, 'rb') as f:
        file_bytes = f.read()
    
    print(f"Processing {pdf_path}...")
    raw_text, questions = await process_uploaded_file(file_bytes, "sample_question_bank.pdf")
    
    print("\n--- RAW TEXT START ---")
    print(raw_text[:5000]) # First 5000 chars
    print("--- RAW TEXT END ---\n")
    
    print(f"Extracted {len(questions)} questions.")
    for i, q in enumerate(questions[:10]):
        print(f"{i+1}. [{q.get('section_name')}] {q.get('question_no')}: {q.get('question_text')[:100]}... ({q.get('marks')}M, {q.get('blooms_level')})")

if __name__ == "__main__":
    asyncio.run(main())
