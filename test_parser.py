import sys
sys.path.insert(0, '.')
from ocr_pipeline import parse_questions_from_text

sample = """
PART - A (2 Marks)
1. Define data structure. [2] K1
2) What is an algorithm? (2 Marks) K1
3. State the difference between stack and queue. [2] K2
Q4. List the types of linked lists. (2)

PART - B (16 Marks)
5. Explain the working of binary search tree with example. [16] K2
6) Analyze the time complexity of merge sort and quick sort. [16] K4
Q.7. Design a hash table with chaining collision resolution. [16] K6
(8) Compare DFS and BFS traversal algorithms. [16] K4
a) Write a program to implement stack using arrays.
b) Discuss the applications of queues in operating systems.
"""

questions = parse_questions_from_text(sample)
print(f"Parsed {len(questions)} questions:")
for q in questions:
    print(f"  no={q['question_no']} marks={q['marks']} bloom={q['blooms_level']} section={q['section_name']}")
    print(f"    -> {q['question_text'][:80]}")
