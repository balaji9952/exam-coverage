import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from ocr_pipeline import parse_questions_from_text, extract_text_from_pdf, is_noise, is_section_header, UNIT_HEADER_PATTERN, STANDALONE_OR_PATTERN, is_question_start, VERB_GROUPS

async def debug_text_loop():
    file_path = r'backend\uploads\f2893e29-2972-4f1b-9e6b-1954169a42b2_dm question paper(2).pdf'
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, 'rb') as f:
        file_bytes = f.read()

    raw_text = await extract_text_from_pdf(file_bytes)
    
    lines = [l.rstrip() for l in raw_text.split('\n')]
    
    for line in lines:
        if "essentials and measurement" in line:
            print(f"FOUND TARGET LINE: '{line}'")
            print(f"Length: {len(line)}")
            print(f"is_noise: {is_noise(line)}")
            print(f"is_section_header: {bool(is_section_header(line))}")
            print(f"is_question_start: {bool(is_question_start(line))}")
            
            lower_line = line.lower()
            is_verb_start = any(
                lower_line.startswith(v) or f" {v} " in lower_line[:15]
                for group in VERB_GROUPS.values() for v in group
            )
            print(f"is_verb_start: {is_verb_start}")

if __name__ == "__main__":
    asyncio.run(debug_text_loop())
