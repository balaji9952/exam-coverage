import pdfplumber
import io

pdf_path = r'd:\man\man\backend\uploads\0737da16-042e-4fc9-9a29-46b510e6154b_AL3451 All Unit QB (1).pdf'
with pdfplumber.open(pdf_path) as pdf:
    for page in pdf.pages:
        text = page.extract_text()
        if text and ("Stacking ensemble" in text or "Expectation Maximization" in text):
            print(f"--- PAGE {page.page_number} ---")
            print(text)
            print("-" * 40)
            # Also extract tables on this page
            tables = page.extract_tables()
            for t in tables:
                print("TABLE:")
                for row in t:
                    print(row)
