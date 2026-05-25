import sqlite3
conn = sqlite3.connect('backend/exam_coverage.db')
cursor = conn.cursor()
cursor.execute("SELECT id, name, code FROM subjects")
print("SUBJECTS:")
for row in cursor.fetchall():
    print(row)
cursor.execute("SELECT id, subject_id, question_no, question_text FROM question_bank_master LIMIT 5")
print("\nQUESTIONS:")
for row in cursor.fetchall():
    print(row)
conn.close()
