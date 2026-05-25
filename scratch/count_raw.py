import re

with open(r'scratch\full_text.txt', 'r', encoding='utf-16le') as f:
    text = f.read()

# Pattern for question numbers like "1.", "1)", "Q.1", etc.
pattern = re.compile(r'^\s*(\d{1,2})\s*[\.\)]\s*', re.MULTILINE)
matches = pattern.findall(text)

print(f"Total question-like markers: {len(matches)}")

# Print them all to see gaps
last_num = 0
for m in matches:
    num = int(m)
    if num != last_num + 1 and num != 1:
        print(f"GAP? {last_num} -> {num}")
    last_num = num

# Search for "Cluster" again
if "Cluster" in text:
    print("\n'Cluster' found in text!")
    idx = text.find("Cluster")
    print(text[max(0, idx-50):idx+150])
