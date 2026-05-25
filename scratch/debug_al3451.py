import sys
import os
import asyncio

# Add backend to path so we can import ocr_pipeline
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))
import ocr_pipeline

async def main():
    pdf_path = r'd:\man\man\backend\uploads\0737da16-042e-4fc9-9a29-46b510e6154b_AL3451 All Unit QB (1).pdf'
    with open(pdf_path, 'rb') as f:
        file_bytes = f.read()

    # Try tabular extraction first
    questions = await ocr_pipeline.extract_questions_from_pdf_tables(file_bytes)
    
    if not questions:
        import fitz
        print("Tabular extraction returned 0 questions. Trying plain text...")
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
        questions = ocr_pipeline.parse_questions_from_text(text)
    
    print(f"Extracted {len(questions)} questions.")
    
    # Just list all question numbers and texts to see what's missing
    for idx, q in enumerate(questions):
        qno = q.get('question_no', '?')
        text = q.get('question_text', '').replace('\n', ' ')[:80]
        print(f"[{idx+1}] Q.{qno} -> {text}")

if __name__ == '__main__':
    asyncio.run(main())
