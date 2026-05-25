import sqlite3

db_path = 'd:/man/man/backend/exam_coverage.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT doc_type, status, COUNT(*) FROM uploaded_documents GROUP BY doc_type, status")
rows = cursor.fetchall()

print("Uploaded Documents Distribution:")
for row in rows:
    print(f"Type: {row[0]} | Status: {row[1]} | Count: {row[2]}")

cursor.execute("SELECT COUNT(*) FROM uploaded_documents")
total = cursor.fetchone()[0]
print(f"\nTotal Documents: {total}")

conn.close()
