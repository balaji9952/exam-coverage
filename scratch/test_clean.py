import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from ocr_pipeline import clean_question_text

def test_clean():
    texts = [
        "13 Analyze the role of mobile marketing",
        "Analyze the role of mobile marketing 13",
        "15 Describe digital transformation",
        "Evaluate ethical issues 15",
        "Discuss various email marketing strategies (OR) Analyze the role of"
    ]
    
    for t in texts:
        print(f"Original: '{t}'")
        print(f"Cleaned : '{clean_question_text(t)}'\n")

if __name__ == "__main__":
    test_clean()
