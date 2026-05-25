import fitz
import re

pdf_path = r'd:\man\man\backend\uploads\0737da16-042e-4fc9-9a29-46b510e6154b_AL3451 All Unit QB (1).pdf'
doc = fitz.open(pdf_path)

text = ""
for page in doc:
    text += page.get_text() + "\n"

# Let's search for "Stacking ensemble" and print surrounding text
idx = text.find("Stacking ensemble")
if idx != -1:
    print(text[max(0, idx-500):idx+500])

print("-" * 80)

# Also let's print all questions after 80 to see if Part C is missing
idx2 = text.find("vanishing gradient problem")
if idx2 != -1:
    print(text[max(0, idx2-500):idx2+500])

