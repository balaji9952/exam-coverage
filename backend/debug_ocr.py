"""
Debug script — run this to see what raw text + parsed questions look like for your file.
Usage: python debug_ocr.py "your_file.pdf"
"""
import sys
import asyncio
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

async def main():
    filepath = sys.argv[1] if len(sys.argv) > 1 else None
    if not filepath:
        print("Usage: python debug_ocr.py <path_to_pdf_or_image>")
        return

    path = Path(filepath)
    if not path.exists():
        print(f"File not found: {filepath}")
        return

    file_bytes = path.read_bytes()

    # 1. Raw text extraction
    from ocr_pipeline import extract_text_from_pdf, extract_text_from_image, parse_questions_from_text

    print(f"\n{'='*60}")
    print(f"FILE: {path.name}  ({len(file_bytes)//1024} KB)")
    print('='*60)

    if path.suffix.lower() == '.pdf':
        raw_text = await extract_text_from_pdf(file_bytes)
    else:
        raw_text = await extract_text_from_image(file_bytes)

    if not raw_text.strip():
        print("\n❌ NO TEXT extracted. Possible reasons:")
        print("   - Scanned/image PDF with no text layer (needs OCR)")
        print("   - Image file needs Tesseract installed")
        return

    print(f"\n✅ Extracted {len(raw_text)} characters of raw text")
    print("\n--- RAW TEXT (first 3000 chars) ---\n")
    print(raw_text[:3000])

    # 2. Line by line view
    lines = raw_text.split('\n')
    print(f"\n--- LINE-BY-LINE ({len(lines)} lines) ---")
    for i, line in enumerate(lines[:60]):
        if line.strip():
            print(f"  [{i:03d}] |{line}|")

    # 3. Parsed questions
    questions = parse_questions_from_text(raw_text)
    print(f"\n--- PARSED QUESTIONS: {len(questions)} found ---")
    for i, q in enumerate(questions):
        print(f"\n  Q{i+1}: no={q['question_no']}  section={q['section_name']}  marks={q['marks']}  bloom={q['blooms_level']}")
        print(f"       text={q['question_text'][:120]}")

    if len(questions) == 0:
        print("\n⚠️  No questions parsed! Lines that look like question starts:")
        import re
        for i, line in enumerate(lines):
            line = line.strip()
            if re.match(r'^\d', line) and len(line) > 5:
                print(f"  [{i:03d}] {line[:100]}")

if __name__ == '__main__':
    asyncio.run(main())
