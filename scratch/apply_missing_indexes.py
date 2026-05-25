import sqlite3

def apply_indexes():
    conn = sqlite3.connect('d:/man/man/backend/exam_coverage.db')
    cursor = conn.cursor()
    
    commands = [
        "CREATE INDEX IF NOT EXISTS ix_syllabus_units_subject_id ON syllabus_units (subject_id)",
        "CREATE INDEX IF NOT EXISTS ix_question_staging_review_doc_id ON question_staging_review (doc_id)",
        "CREATE INDEX IF NOT EXISTS ix_question_bank_master_doc_id ON question_bank_master (doc_id)",
        "CREATE INDEX IF NOT EXISTS ix_question_bank_master_subject_id ON question_bank_master (subject_id)",
        "CREATE INDEX IF NOT EXISTS ix_question_bank_master_unit_id ON question_bank_master (unit_id)"
    ]
    
    for cmd in commands:
        try:
            print(f"Executing: {cmd}")
            cursor.execute(cmd)
        except Exception as e:
            print(f"Error: {e}")
            
    conn.commit()
    conn.close()
    print("\nIndexes applied successfully.")

if __name__ == "__main__":
    apply_indexes()
