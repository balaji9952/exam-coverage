import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from ocr_pipeline import parse_questions_from_text, extract_text_from_pdf

async def debug_text():
    file_path = r'backend\uploads\f2893e29-2972-4f1b-9e6b-1954169a42b2_dm question paper(2).pdf'
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, 'rb') as f:
        file_bytes = f.read()

    raw_text = await extract_text_from_pdf(file_bytes)
    print("--- RAW TEXT ---")
    print(raw_text[:1000])
    print("--- END RAW TEXT ---")
    
    questions = parse_questions_from_text(raw_text)
    
    print(f"\n--- Extraction Summary ---")
    print(f"Total Questions Extracted from Text: {len(questions)}")
    
    for i, q in enumerate(questions[:30]):
        no = q.get('question_no', '')
        txt = q.get('question_text', '').replace('\n', ' ')[:50]
        blooms = q.get('blooms_level', '')
        marks = q.get('marks', '')
        print(f"{i+1:2}. [{no:6}] | Blooms: {blooms} | Marks: {marks} | {txt}...")

if __name__ == "__main__":
    asyncio.run(debug_text())
