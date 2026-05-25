import sqlite3
import json
import os

DB_PATH = 'backend/exam_coverage.db'
JSON_PATH = 'sample_question_bank.json'

def import_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Clear existing questions (they are dirty/mislinked)
    cursor.execute("DELETE FROM question_bank_master")
    print("Cleared existing questions.")

    # 2. Read JSON
    with open(JSON_PATH, 'r') as f:
        data = json.load(f)

    # 3. Get or Create Subject
    sub_name = data.get('subject_name', 'DATA STRUCTURES AND ALGORITHMS')
    sub_code = data.get('subject_code', 'CS3301')
    cursor.execute("SELECT id FROM subjects WHERE code = ?", (sub_code,))
    row = cursor.fetchone()
    if row:
        subject_id = row[0]
    else:
        # Need department and regulation
        cursor.execute("INSERT INTO subjects (name, code, semester, department_id, regulation_id) VALUES (?, ?, ?, ?, ?)",
                       (sub_name, sub_code, 3, 1, 1))
        subject_id = cursor.lastrowid
    print(f"Using Subject: {sub_name} (ID: {subject_id})")

    # 4. Get or Create Units
    unit_map = {}
    for section in data.get('sections', []):
        for q in section.get('questions', []):
            u_no = q.get('unit_no')
            if u_no and u_no not in unit_map:
                cursor.execute("SELECT id FROM syllabus_units WHERE subject_id = ? AND unit_no = ?", (subject_id, u_no))
                u_row = cursor.fetchone()
                if u_row:
                    unit_map[u_no] = u_row[0]
                else:
                    cursor.execute("INSERT INTO syllabus_units (subject_id, unit_no, unit_title) VALUES (?, ?, ?)",
                                   (subject_id, u_no, f"Unit {u_no}"))
                    unit_map[u_no] = cursor.lastrowid

    # 5. Import Questions
    count = 0
    for section in data.get('sections', []):
        sec_name = section.get('section_name', 'GENERAL')
        for q in section.get('questions', []):
            u_no = q.get('unit_no')
            cursor.execute("""
                INSERT INTO question_bank_master 
                (subject_id, unit_id, section_name, question_no, question_text, normalized_text, marks, blooms_level, question_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                subject_id,
                unit_map.get(u_no),
                sec_name,
                q.get('question_no'),
                q.get('question_text'),
                q.get('question_text').lower(), # simple normalization
                q.get('marks'),
                q.get('blooms_level'),
                q.get('question_type')
            ))
            count += 1
    
    conn.commit()
    conn.close()
    print(f"Successfully imported {count} clean questions.")

if __name__ == "__main__":
    import_data()
