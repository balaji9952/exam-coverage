from sqlalchemy.orm import Session
from database import SessionLocal, Subject, Department, Regulation

def check():
    db = SessionLocal()
    try:
        subjects = db.query(Subject).all()
        print(f"Found {len(subjects)} subjects")
        for s in subjects:
            print(f"Subject: {s.name} ({s.code})")
            print(f"  Dept: {s.department.name if s.department else 'NONE'}")
            print(f"  Reg: {s.regulation.name if s.regulation else 'NONE'}")
            
            # This is what main.py does:
            result = {
                "id": s.id, "name": s.name, "code": s.code,
                "semester": s.semester,
                "department_id": s.department_id,
                "regulation_id": s.regulation_id,
                "department": s.department.name if s.department else None,
                "department_code": s.department.code if s.department else None,
                "regulation": s.regulation.name if s.regulation else None,
            }
            print(f"  Result dict: {result}")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    check()
