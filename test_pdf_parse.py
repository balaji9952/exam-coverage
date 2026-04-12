import asyncio, sys
sys.path.insert(0, 'backend')
from ocr_pipeline import extract_text_from_pdf, parse_questions_from_text

files = [
    ('sample_question_paper.pdf',  'EXAM PAPER'),
    ('sample_question_bank.pdf',   'QUESTION BANK'),
    ('sample_question_bank.txt',   'BANK TXT'),
]

async def run():
    for fname, label in files:
        try:
            with open(fname, 'rb') as f:
                data = f.read()
            if fname.endswith('.txt'):
                text = data.decode('utf-8', errors='ignore')
            else:
                text = await extract_text_from_pdf(data)
            qs = parse_questions_from_text(text)
            print(f"\n{'='*60}")
            print(f"  {label}: {fname}")
            print(f"  Chars extracted : {len(text)}")
            print(f"  Questions found : {len(qs)}")
            part_a = [q for q in qs if q['marks'] and q['marks'] <= 2]
            part_b = [q for q in qs if q['marks'] and q['marks'] > 2]
            no_marks = [q for q in qs if not q['marks']]
            print(f"  Part A (<=2M)   : {len(part_a)}")
            print(f"  Part B (>2M)    : {len(part_b)}")
            print(f"  No marks tagged : {len(no_marks)}")
            blooms = {}
            for q in qs:
                b = q['blooms_level'] or 'None'
                blooms[b] = blooms.get(b, 0) + 1
            print(f"  Bloom's dist    : {dict(sorted(blooms.items()))}")
        except Exception as e:
            print(f"  ERROR: {e}")

asyncio.run(run())
