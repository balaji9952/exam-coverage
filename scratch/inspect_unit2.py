import pdfplumber
import io

pdf_path = r'd:\man\man\backend\uploads\0737da16-042e-4fc9-9a29-46b510e6154b_AL3451 All Unit QB (1).pdf'
with pdfplumber.open(pdf_path) as pdf:
    for page in pdf.pages:
        text = page.extract_text()
        if text and "straight line to the data" in text:
            print(f"--- PAGE {page.page_number} ---")
            # print(text)
            tables = page.extract_tables()
            for t in tables:
                for row in t:
                    if row and any("straight line" in str(c) for c in row if c):
                        print("FOUND UNIT 2 PART B TABLE")
                        for r in t:
                            print(r)
