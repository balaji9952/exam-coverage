import sys
sys.path.insert(0, 'backend')
from ocr_pipeline import parse_questions_from_text
import json

with open('sample_question_bank.txt', 'r', encoding='utf-8') as f:
    text = f.read()

questions = parse_questions_from_text(text)
print(f"Extracted {len(questions)} questions.")

for q in questions[:2]:
    print(f"Q{q['question_no']} [{q['section_name']}] (Unit {q['unit_no']}) Marks: {q['marks']} Bloom: {q['blooms_level']}")
    print(f"  TEXT: |{q['question_text']}|")
