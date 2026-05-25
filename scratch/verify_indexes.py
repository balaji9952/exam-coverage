import sqlite3

def check_indexes():
    conn = sqlite3.connect('d:/man/man/backend/exam_coverage.db')
    cursor = conn.cursor()
    
    tables = ['syllabus_units', 'question_staging_review', 'question_bank_master']
    
    for table in tables:
        print(f"\nChecking table: {table}")
        cursor.execute(f"PRAGMA index_list({table})")
        indexes = cursor.fetchall()
        if not indexes:
            print("  No indexes found.")
        for idx in indexes:
            idx_name = idx[1]
            cursor.execute(f"PRAGMA index_info({idx_name})")
            columns = cursor.fetchall()
            col_names = [c[2] for c in columns]
            print(f"  Index: {idx_name}, Columns: {col_names}")
            
    conn.close()

if __name__ == "__main__":
    check_indexes()
