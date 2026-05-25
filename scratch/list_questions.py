import json
with open('sample_question_bank.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

count = 0
for sec in data.get('sections', []):
    print(f"\n--- {sec['section_name']} ---")
    for q in sec.get('questions', []):
        count += 1
        print(f"{q['question_no']} | M:{q['marks']} | B:{q['blooms_level']} | U:{q['unit_no']} | {q['question_text'][:50]}")
print(f"\nTotal: {count}")
