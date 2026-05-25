import pdfplumber
import io

def inspect_tables():
    pdf_path = r'd:\man\man\sample_question_bank.pdf'
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages[:2]): # First 2 pages
            print(f"--- PAGE {i+1} ---")
            tables = page.extract_tables()
            for t_idx, table in enumerate(tables):
                print(f"Table {t_idx}:")
                for r_idx, row in enumerate(table[:20]): # First 20 rows
                    print(f"  Row {r_idx}: {row}")

if __name__ == "__main__":
    inspect_tables()
