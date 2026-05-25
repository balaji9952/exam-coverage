import sqlite3

db_path = 'd:/man/man/backend/exam_coverage.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM exam_papers")
exams = cursor.fetchone()[0]
print(f"Total ExamPaper records: {exams}")

cursor.execute("SELECT COUNT(*) FROM question_bank_master")
bank_qs = cursor.fetchone()[0]
print(f"Total QuestionBankMaster questions: {bank_qs}")

# Count distinct doc_id in master to see how many bank files are active
cursor.execute("SELECT COUNT(DISTINCT doc_id) FROM question_bank_master")
bank_docs = cursor.fetchone()[0]
print(f"Total active Question Bank documents: {bank_docs}")

conn.close()
