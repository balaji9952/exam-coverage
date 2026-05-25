import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from ocr_pipeline import extract_questions_from_pdf_tables

async def debug_tables():
    file_path = r'backend\uploads\f2893e29-2972-4f1b-9e6b-1954169a42b2_dm question paper(2).pdf'
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, 'rb') as f:
        file_bytes = f.read()

    questions = await extract_questions_from_pdf_tables(file_bytes)
    
    print(f"\n--- Extraction Summary ---")
    print(f"Total Questions Extracted from Tables: {len(questions)}")
    
    for i, q in enumerate(questions[:30]):
        no = q.get('question_no', '')
        txt = q.get('question_text', '').replace('\n', ' ')[:50]
        blooms = q.get('blooms_level', '')
        marks = q.get('marks', '')
        print(f"{i+1:2}. [{no:6}] | Blooms: {blooms} | Marks: {marks} | {txt}...")

if __name__ == "__main__":
    asyncio.run(debug_tables())
