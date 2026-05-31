"""
FastAPI Backend — Exam Coverage Analysis System
"""

import os
import json
import uuid
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Dict

from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, status, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload, defer

from database import (
    get_db, create_tables,
    Department, Regulation, Subject, SyllabusUnit, CourseOutcome,
    UploadedDocument, QuestionStagingReview, QuestionBankMaster,
    ExamPaper, ExtractedExamQuestion, MatchResult, CoverageReport, User
)
from ocr_pipeline import process_uploaded_file, normalize_question, extract_blooms, extract_marks
from matcher import (
    encode_text, embedding_to_json, json_to_embedding,
    match_exam_to_bank, compute_coverage_report, classify_match
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── App Setup ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Exam Coverage Analysis API",
    description="AI-powered exam paper vs question bank coverage analyzer",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@app.on_event("startup")
def startup():
    create_tables()
    logger.info("Database initialized")


# ─── Pydantic Schemas ──────────────────────────────────────────────────────────

class DepartmentCreate(BaseModel):
    name: str
    code: str

class RegulationCreate(BaseModel):
    name: str

class SubjectCreate(BaseModel):
    name: str
    code: str
    semester: int
    department_id: int
    regulation_id: int

class SubjectUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    semester: Optional[int] = None
    department_id: Optional[int] = None
    regulation_id: Optional[int] = None

class SyllabusUnitCreate(BaseModel):
    subject_id: int
    unit_no: int
    unit_title: str
    keywords: Optional[str] = None

class StagingUpdateItem(BaseModel):
    id: int
    question_text: Optional[str] = None
    marks: Optional[float] = None
    blooms_level: Optional[str] = None
    unit_id: Optional[int] = None
    review_status: Optional[str] = None  # approved | rejected

class BulkApproveRequest(BaseModel):
    staging_ids: List[int]

class QuestionBankAdd(BaseModel):
    subject_id: int
    unit_id: Optional[int] = None
    section_name: Optional[str] = None
    question_no: Optional[str] = None
    question_text: str
    marks: Optional[float] = None
    blooms_level: Optional[str] = None

# ─── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# ─── Debug: Preview raw extracted text from a file ────────────────────────────

@app.post("/debug/raw-text")
async def preview_raw_text(file: UploadFile = File(...)):
    """Debug endpoint: upload any PDF/image to see what text is extracted"""
    file_bytes = await file.read()
    from ocr_pipeline import process_uploaded_file, parse_questions_from_text
    raw_text, questions = await process_uploaded_file(file_bytes, file.filename)
    lines = raw_text.split('\n') if raw_text else []
    return {
        "filename": file.filename,
        "char_count": len(raw_text),
        "line_count": len(lines),
        "questions_parsed": len(questions),
        "raw_text": raw_text[:5000],
        "lines_preview": [
            {"line_no": i, "content": l}
            for i, l in enumerate(lines[:80])
            if l.strip()
        ],
        "parsed_questions": [
            {
                "question_no": q.get("question_no"),
                "section": q.get("section_name"),
                "text": q.get("question_text", "")[:150],
                "marks": q.get("marks"),
                "blooms": q.get("blooms_level"),
            }
            for q in questions
        ]
    }


# ─── Departments ───────────────────────────────────────────────────────────────

@app.get("/departments")
def list_departments(db: Session = Depends(get_db)):
    return db.query(Department).all()

@app.post("/departments")
def create_department(data: DepartmentCreate, db: Session = Depends(get_db)):
    dept = Department(name=data.name, code=data.code)
    db.add(dept); db.commit(); db.refresh(dept)
    return dept


# ─── Regulations ───────────────────────────────────────────────────────────────

@app.get("/regulations")
def list_regulations(db: Session = Depends(get_db)):
    return db.query(Regulation).all()

@app.post("/regulations")
def create_regulation(data: RegulationCreate, db: Session = Depends(get_db)):
    reg = Regulation(name=data.name)
    db.add(reg); db.commit(); db.refresh(reg)
    return reg


# ─── Subjects ──────────────────────────────────────────────────────────────────

@app.get("/subjects")
def list_subjects(
    department_id: Optional[int] = None,
    semester: Optional[int] = None,
    unique: bool = False,
    db: Session = Depends(get_db)
):
    q = db.query(Subject)
    if department_id:
        q = q.filter(Subject.department_id == department_id)
    if semester:
        q = q.filter(Subject.semester == semester)
    subjects = q.all()
    result = []
    seen = set()
    for s in subjects:
        if unique:
            key = (s.name.strip().lower(), s.code.strip().lower())
            if key in seen:
                continue
            seen.add(key)
            
        result.append({
            "id": s.id, "name": s.name, "code": s.code,
            "semester": s.semester,
            "department_id": s.department_id,
            "regulation_id": s.regulation_id,
            "department": s.department.name if s.department else None,
            "department_code": s.department.code if s.department else None,
            "regulation": s.regulation.name if s.regulation else None,
        })
    return result

@app.post("/subjects")
def create_subject(data: SubjectCreate, db: Session = Depends(get_db)):
    # Check for exact duplicate: same subject code in the same department
    existing = db.query(Subject).filter(
        Subject.code == data.code,
        Subject.department_id == data.department_id
    ).first()
    if existing:
        dept = db.query(Department).filter(Department.id == data.department_id).first()
        dept_name = dept.name if dept else f"Department #{data.department_id}"
        raise HTTPException(
            status_code=409,
            detail=f"Subject with code '{data.code}' already exists in '{dept_name}'. "
                   f"The same subject code can be added to a different department."
        )
    subj = Subject(**data.dict())
    db.add(subj); db.commit(); db.refresh(subj)
    return subj

@app.delete("/subjects/{subject_id}")
def delete_subject(subject_id: int, db: Session = Depends(get_db)):
    subj = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subj:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    # Delete related syllabus units
    db.query(SyllabusUnit).filter(SyllabusUnit.subject_id == subject_id).delete()
    
    db.delete(subj)
    db.commit()
    return {"message": "Subject deleted"}

@app.patch("/subjects/{subject_id}")
def update_subject(subject_id: int, data: SubjectUpdate, db: Session = Depends(get_db)):
    subj = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subj:
        raise HTTPException(status_code=404, detail="Subject not found")
    if data.name is not None:
        subj.name = data.name
    if data.code is not None:
        subj.code = data.code
    if data.semester is not None:
        subj.semester = data.semester
    if data.department_id is not None:
        subj.department_id = data.department_id
    if data.regulation_id is not None:
        subj.regulation_id = data.regulation_id
    db.commit()
    db.refresh(subj)
    return subj


# ─── Syllabus Units ────────────────────────────────────────────────────────────

@app.get("/subjects/{subject_id}/units")
def list_units(subject_id: int, db: Session = Depends(get_db)):
    return db.query(SyllabusUnit).filter(SyllabusUnit.subject_id == subject_id).order_by(SyllabusUnit.unit_no).all()

@app.post("/syllabus-units")
def create_unit(data: SyllabusUnitCreate, db: Session = Depends(get_db)):
    unit = SyllabusUnit(**data.dict())
    db.add(unit); db.commit(); db.refresh(unit)
    return unit


# ─── Question Bank Upload + Auto-Extraction ───────────────────────────────────

@app.post("/question-bank/upload")
async def upload_question_bank(
    file: UploadFile = File(...),
    subject_id: int = Form(...),
    unit_id: Optional[int] = Form(None),
    uploaded_by: Optional[str] = Form("faculty"),
    db: Session = Depends(get_db)
):
    """Upload question bank PDF/image → OCR → staging table"""
    file_bytes = await file.read()
    safe_name = f"{uuid.uuid4()}_{file.filename}"
    file_path = UPLOAD_DIR / safe_name
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    # Save document record
    doc = UploadedDocument(
        filename=file.filename,
        file_path=str(file_path),
        doc_type="question_bank",
        subject_id=subject_id,
        unit_id=unit_id,
        uploaded_by=uploaded_by,
        status="processing"
    )
    db.add(doc); db.commit(); db.refresh(doc)

    # OCR + parse
    try:
        raw_text, questions = await process_uploaded_file(file_bytes, file.filename)

        # ─── Perfect AI Extraction Fallback ───
        # If OCR missed major parts (e.g. only Part B found), or if GOOGLE_API_KEY is present, try AI
        # Most papers have > 18 questions. If we found fewer, AI should verify.
        if (not questions or len(questions) < 18) and os.getenv("GOOGLE_API_KEY"):
            try:
                from ai_extractor import extract_questions_with_ai
                ai_questions = extract_questions_with_ai(raw_text)
                if ai_questions and len(ai_questions) > 0:
                    logger.info(f"AI-Enhanced bank extraction SUCCESS: {len(ai_questions)} questions found.")
                    questions = ai_questions
            except Exception as ai_err:
                logger.error(f"AI Bank Enhancement failed: {ai_err}")

        # If no questions found, still save to staging but return a warning with raw text
        if not questions and raw_text.strip():
            logger.warning(f"No questions parsed from {file.filename}. Raw text length: {len(raw_text)}")
            doc.status = "staged"
            db.commit()
            return {
                "doc_id": doc.id,
                "filename": file.filename,
                "extracted_count": 0,
                "status": "staged",
                "warning": "No questions could be automatically parsed from this file. "
                           "The question format may not match expected patterns. "
                           "Please use the raw text preview to understand the format, "
                           "or add questions manually.",
                "raw_text_preview": raw_text[:2000],
                "message": "0 questions extracted — check file format or use manual entry."
            }
        elif not raw_text.strip():
            doc.status = "error"
            db.commit()
            return {
                "doc_id": doc.id,
                "filename": file.filename,
                "extracted_count": 0,
                "status": "error",
                "warning": "No text could be extracted from this file. "
                           "If it is a scanned image PDF, make sure Tesseract OCR is installed. "
                           "For image files (JPG/PNG), Tesseract must be installed and available in PATH.",
                "raw_text_preview": "",
                "message": "Text extraction failed — ensure Tesseract is installed for image/scanned PDFs."
            }

        # Map extracted unit numbers to database unit IDs
        subject_units = db.query(SyllabusUnit).filter(SyllabusUnit.subject_id == subject_id).all()
        unit_map = {u.unit_no: u.id for u in subject_units}

        staging_records = []
        for q in questions:
            extracted_unit_no = q.get("unit_no")
            predicted_uid = unit_map.get(extracted_unit_no) if extracted_unit_no else unit_id

            sr = QuestionStagingReview(
                doc_id=doc.id,
                subject_id=subject_id,
                unit_id=predicted_uid or unit_id,
                predicted_unit_id=predicted_uid or unit_id,
                section_name=q.get("section_name") or q.get("section"),
                question_no=q.get("question_no") or q.get("q_no"),
                question_text=q.get("question_text") or q.get("question", ""),
                marks=q.get("marks"),
                blooms_level=q.get("blooms_level") or q.get("bloom"),
                question_type=q.get("question_type") or ("descriptive" if (q.get("marks") or 0) > 2 else "short"),
                confidence_score=0.9 if q.get("question_text") else 0.3,
                review_status="pending"
            )
            db.add(sr)
            staging_records.append(sr)

        doc.status = "staged"
        db.commit()

        return {
            "doc_id": doc.id,
            "filename": file.filename,
            "extracted_count": len(questions),
            "status": "staged",
            "raw_text_preview": raw_text[:500],
            "message": f"Extracted {len(questions)} questions. Please review before approving."
        }
    except Exception as e:
        doc.status = "error"
        db.commit()
        logger.error(f"Processing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@app.get("/question-bank/staging/{doc_id}")
def get_staging_questions(doc_id: int, db: Session = Depends(get_db)):
    """Get all staged (pending review) questions for a document"""
    questions = db.query(QuestionStagingReview).options(
        joinedload(QuestionStagingReview.unit)
    ).filter(
        QuestionStagingReview.doc_id == doc_id
    ).all()
    
    result = []
    for q in questions:
        result.append({
            "id": q.id,
            "question_no": q.question_no,
            "section_name": q.section_name,
            "question_text": q.question_text,
            "marks": q.marks,
            "blooms_level": q.blooms_level,
            "question_type": q.question_type,
            "confidence_score": q.confidence_score,
            "review_status": q.review_status,
            "unit_id": q.unit_id,
            "unit_title": q.unit.unit_title if q.unit else None,
        })
    return result


@app.patch("/question-bank/staging/update")
def update_staging_question(updates: List[StagingUpdateItem], db: Session = Depends(get_db)):
    """Faculty edits to staging questions"""
    for item in updates:
        q = db.query(QuestionStagingReview).filter(QuestionStagingReview.id == item.id).first()
        if not q:
            continue
        if item.question_text is not None:
            q.question_text = item.question_text
        if item.marks is not None:
            q.marks = item.marks
        if item.blooms_level is not None:
            q.blooms_level = item.blooms_level
        if item.unit_id is not None:
            q.unit_id = item.unit_id
        if item.review_status is not None:
            q.review_status = item.review_status
    db.commit()
    return {"message": "Updated successfully"}


@app.post("/question-bank/staging/approve")
def approve_staging_questions(req: BulkApproveRequest, db: Session = Depends(get_db)):
    """Move approved staging questions to the master question bank"""
    approved = 0
    for sid in req.staging_ids:
        sq = db.query(QuestionStagingReview).filter(QuestionStagingReview.id == sid).first()
        if not sq or sq.review_status == "rejected":
            continue
        normalized = normalize_question(sq.question_text)
        embedding = encode_text(normalized)
        master = QuestionBankMaster(
            subject_id=sq.subject_id,
            unit_id=sq.unit_id,
            doc_id=sq.doc_id,
            section_name=sq.section_name,
            question_no=sq.question_no,
            question_text=sq.question_text,
            normalized_text=normalized,
            marks=sq.marks,
            blooms_level=sq.blooms_level,
            question_type=sq.question_type,
            embedding=embedding_to_json(embedding) if embedding else None,
        )
        db.add(master)
        sq.review_status = "approved"
        approved += 1
    db.commit()
    return {"approved_count": approved}


@app.get("/question-bank/documents")
def list_bank_documents(db: Session = Depends(get_db)):
    """List all uploaded question bank source files"""
    from sqlalchemy import func
    
    docs = db.query(UploadedDocument).options(
        joinedload(UploadedDocument.subject)
    ).filter(UploadedDocument.doc_type == "question_bank").all()
    
    # Pre-calculate question counts to avoid N+1 queries
    counts = dict(db.query(
        QuestionBankMaster.doc_id, 
        func.count(QuestionBankMaster.id)
    ).filter(QuestionBankMaster.doc_id.isnot(None)).group_by(QuestionBankMaster.doc_id).all())
    
    result = []
    for d in docs:
        result.append({
            "id": d.id,
            "filename": d.filename,
            "subject_id": d.subject_id,
            "subject_name": d.subject.name if d.subject else "Unknown",
            "subject_code": d.subject.code if d.subject else "---",
            "uploaded_at": d.uploaded_at.isoformat(),
            "status": d.status,
            "question_count": counts.get(d.id, 0)
        })
    return sorted(result, key=lambda x: x["uploaded_at"], reverse=True)

@app.delete("/question-bank/documents/{doc_id}")
def delete_bank_document(doc_id: int, db: Session = Depends(get_db)):
    """Delete a source document and all its questions"""
    doc = db.query(UploadedDocument).filter(UploadedDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # 1. Delete questions from master
    db.query(QuestionBankMaster).filter(QuestionBankMaster.doc_id == doc_id).delete()
    
    # 2. Delete questions from staging
    db.query(QuestionStagingReview).filter(QuestionStagingReview.doc_id == doc_id).delete()
    
    # 3. Delete the document record
    db.delete(doc)
    
    # 4. Try to delete the physical file
    try:
        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)
    except Exception as e:
        logger.error(f"Failed to delete file {doc.file_path}: {e}")

    db.commit()
    return {"message": "Document and associated questions deleted"}

# ─── Question Bank Management ─────────────────────────────────────────────────

@app.get("/question-bank")
def list_bank_questions(
    subject_id: Optional[int] = None,
    unit_id: Optional[int] = None,
    doc_id: Optional[int] = None,
    blooms_level: Optional[str] = None,
    db: Session = Depends(get_db)
):
    # Defer large text/blob columns and eagerly load the unit relationship
    q = db.query(QuestionBankMaster).options(
        defer(QuestionBankMaster.embedding),
        defer(QuestionBankMaster.normalized_text),
        joinedload(QuestionBankMaster.unit)
    )
    if subject_id:
        q = q.filter(QuestionBankMaster.subject_id == subject_id)
    if unit_id:
        q = q.filter(QuestionBankMaster.unit_id == unit_id)
    if doc_id:
        q = q.filter(QuestionBankMaster.doc_id == doc_id)
    if blooms_level:
        q = q.filter(QuestionBankMaster.blooms_level == blooms_level)
    
    questions = q.all()
    result = []
    for bq in questions:
        unit = bq.unit
        result.append({
            "id": bq.id,
            "question_no": bq.question_no,
            "section_name": bq.section_name,
            "question_text": bq.question_text,
            "marks": bq.marks,
            "blooms_level": bq.blooms_level,
            "question_type": bq.question_type,
            "unit_id": bq.unit_id,
            "unit_no": unit.unit_no if unit else None,
            "unit_title": unit.unit_title if unit else None,
            "created_at": bq.created_at.isoformat() if bq.created_at else None,
        })
    return result

@app.post("/question-bank/manual-add")
def manual_add_question(data: QuestionBankAdd, db: Session = Depends(get_db)):
    normalized = normalize_question(data.question_text)
    embedding = encode_text(normalized)
    master = QuestionBankMaster(
        **data.dict(),
        normalized_text=normalized,
        embedding=embedding_to_json(embedding) if embedding else None,
    )
    db.add(master); db.commit(); db.refresh(master)
    return {"id": master.id, "message": "Question added to bank"}

@app.delete("/question-bank/clear")
def clear_bank_questions(subject_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Delete all questions from the master bank, optionally for a specific subject.
    Nulls out MatchResult.bank_question_id first to avoid FK constraint errors.
    """
    # Gather IDs to delete
    q = db.query(QuestionBankMaster)
    if subject_id:
        q = q.filter(QuestionBankMaster.subject_id == subject_id)
    ids_to_delete = [row.id for row in q.with_entities(QuestionBankMaster.id).all()]

    if not ids_to_delete:
        return {"deleted_count": 0, "message": "No questions found to delete."}

    # Null out FK references in match_results first (avoids SQLite constraint error)
    db.query(MatchResult).filter(
        MatchResult.bank_question_id.in_(ids_to_delete)
    ).update({MatchResult.bank_question_id: None}, synchronize_session=False)

    # Now safe to bulk-delete
    db.query(QuestionBankMaster).filter(
        QuestionBankMaster.id.in_(ids_to_delete)
    ).delete(synchronize_session=False)

    db.commit()
    return {"deleted_count": len(ids_to_delete), "message": f"Cleared {len(ids_to_delete)} questions from the bank."}

@app.delete("/question-bank/{question_id}")
def delete_bank_question(question_id: int, db: Session = Depends(get_db)):
    q = db.query(QuestionBankMaster).filter(QuestionBankMaster.id == question_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    db.delete(q); db.commit()
    return {"message": "Deleted"}


# ─── JSON Question Bank Import ────────────────────────────────────────────────

@app.post("/question-bank/import-json")
async def import_json_question_bank(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Import a structured JSON question bank (the output format of the OCR pipeline).
    Auto-creates subject + units if needed, then directly imports questions into master bank.
    Expected JSON shape:
      { subject_name, subject_code, regulation, semester, department,
        sections: [ { section_name, questions: [ {question_no, question_text, marks, blooms_level, unit_no} ] } ] }
    """
    raw = await file.read()
    try:
        data = json.loads(raw)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON file")

    subject_name = (data.get("subject_name") or "").strip().upper()
    subject_code = (data.get("subject_code") or "").strip().upper()
    regulation_name = (data.get("regulation") or "R2021").strip()
    semester_raw = data.get("semester")
    department_name = (data.get("department") or "GENERAL").strip().upper()

    if not subject_name or not subject_code:
        raise HTTPException(status_code=400, detail="JSON must contain subject_name and subject_code")

    # ── Get or create Regulation ──
    regulation = db.query(Regulation).filter(Regulation.name == regulation_name).first()
    if not regulation:
        regulation = Regulation(name=regulation_name)
        db.add(regulation); db.commit(); db.refresh(regulation)

    # ── Get or create Department ──
    dept_code = "".join(w[0] for w in department_name.split()[:4]) or "GEN"
    department = db.query(Department).filter(Department.name == department_name).first()
    if not department:
        department = Department(name=department_name, code=dept_code)
        db.add(department); db.commit(); db.refresh(department)

    # ── Get or create Subject ──
    subject = db.query(Subject).filter(
        Subject.code == subject_code,
        Subject.department_id == department.id
    ).first()
    if not subject:
        sem_val = 1
        if semester_raw:
            try:
                sem_val = int(str(semester_raw).strip())
            except ValueError:
                from ocr_pipeline import roman_to_int
                try:
                    sem_val = roman_to_int(str(semester_raw).strip())
                except Exception:
                    sem_val = 1
        subject = Subject(
            name=subject_name,
            code=subject_code,
            semester=sem_val,
            department_id=department.id,
            regulation_id=regulation.id
        )
        db.add(subject); db.commit(); db.refresh(subject)

    # ── Collect all unit numbers used and create SyllabusUnits ──
    all_unit_nos = set()
    for section in data.get("sections", []):
        for q in section.get("questions", []):
            u = q.get("unit_no")
            if u:
                all_unit_nos.add(int(u))

    existing_units = {u.unit_no: u for u in db.query(SyllabusUnit).filter(
        SyllabusUnit.subject_id == subject.id
    ).all()}

    for unit_no in sorted(all_unit_nos):
        if unit_no not in existing_units:
            unit = SyllabusUnit(
                subject_id=subject.id,
                unit_no=unit_no,
                unit_title=f"Unit {unit_no}"
            )
            db.add(unit); db.commit(); db.refresh(unit)
            existing_units[unit_no] = unit

    # ── Import questions directly to master bank ──
    imported = 0
    skipped = 0
    for section in data.get("sections", []):
        section_name = section.get("section_name", "GENERAL")
        for q in section.get("questions", []):
            qtext = (q.get("question_text") or "").strip()
            if not qtext or len(qtext) < 6:
                skipped += 1
                continue

            unit_no = q.get("unit_no")
            unit_obj = existing_units.get(int(unit_no)) if unit_no else None

            normalized = normalize_question(qtext)
            embedding = encode_text(normalized)

            master = QuestionBankMaster(
                subject_id=subject.id,
                unit_id=unit_obj.id if unit_obj else None,
                section_name=section_name,
                question_no=q.get("question_no"),
                question_text=qtext,
                normalized_text=normalized,
                marks=q.get("marks"),
                blooms_level=q.get("blooms_level"),
                question_type=q.get("question_type", "short"),
                embedding=embedding_to_json(embedding) if embedding is not None else None,
            )
            db.add(master)
            imported += 1

    db.commit()
    return {
        "subject_id": subject.id,
        "subject_name": subject.name,
        "subject_code": subject.code,
        "imported_count": imported,
        "skipped_count": skipped,
        "units_created": len(all_unit_nos),
        "message": f"Successfully imported {imported} questions for {subject_name} ({subject_code})"
    }


# ─── Exam Paper Upload + Analysis ─────────────────────────────────────────────

@app.post("/exam-paper/upload-analyze")
async def upload_and_analyze_exam(
    file: UploadFile = File(...),
    subject_id: int = Form(...),
    exam_type: Optional[str] = Form("Internal"),
    exam_date: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Upload exam paper → extract questions → semantic matching → coverage report"""
    file_bytes = await file.read()
    safe_name = f"{uuid.uuid4()}_{file.filename}"
    file_path = UPLOAD_DIR / safe_name
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    # Save doc
    doc = UploadedDocument(
        filename=file.filename,
        file_path=str(file_path),
        doc_type="exam_paper",
        subject_id=subject_id,
        status="processing"
    )
    db.add(doc); db.commit(); db.refresh(doc)

    # Create exam paper record
    exam = ExamPaper(
        subject_id=subject_id,
        doc_id=doc.id,
        exam_type=exam_type,
        exam_date=exam_date
    )
    db.add(exam); db.commit(); db.refresh(exam)

    try:
        # OCR
        raw_text, questions = await process_uploaded_file(file_bytes, file.filename)
        
        # ─── Perfect AI Extraction Fallback ───
        # If GOOGLE_API_KEY is present, we use the "Perfect Prompt" to clean the extraction
        # This fixes bugs like stray numbers, watermark noise, and trailing digits.
        if os.getenv("GOOGLE_API_KEY"):
            try:
                from ai_extractor import extract_questions_with_ai
                ai_questions = extract_questions_with_ai(raw_text)
                if ai_questions and len(ai_questions) > 0:
                    logger.info(f"AI-Enhanced extraction SUCCESS: {len(ai_questions)} questions found.")
                    questions = ai_questions
                else:
                    logger.warning("AI extraction returned empty. Keeping local OCR results.")
            except Exception as ai_err:
                logger.error(f"AI Enhancement failed: {ai_err}. Using local OCR fallback.")
        
        # NEW: Subject Auto-Detection logic
        from ocr_pipeline import HEADER_PATTERNS
        detected_code = None
        detected_name = None
        for pattern_name, pattern in HEADER_PATTERNS.items():
            m = pattern.search(raw_text[:2000])
            if m:
                val = m.group(1).strip()
                if pattern_name == "subject_code": detected_code = val
                if pattern_name == "subject_name": detected_name = val
        
        logger.info(f"Detected in paper: Code={detected_code}, Name={detected_name}")

        if not questions:
            doc.status = "error"
            db.commit()
            detail = (
                "No questions could be extracted from the exam paper. "
                f"Raw text extracted: {len(raw_text)} chars. "
                "Possible reasons: (1) Scanned PDF needs Tesseract OCR installed, "
                "(2) Question numbers don't match expected patterns like '1.' '1)' 'Q1' '(a)', "
                "(3) The file is image-only and Tesseract is not installed. "
                f"First 300 chars of extracted text: [{raw_text[:300]}]"
            )
            raise HTTPException(status_code=400, detail=detail)

        # Fetch and PRE-PARSE question bank for this subject
        bank_questions_db = db.query(QuestionBankMaster).filter(
            QuestionBankMaster.subject_id == subject_id
        ).all()

        # Serialize bank questions for matcher
        units = {u.id: u for u in db.query(SyllabusUnit).all()}
        bank_q_list = []
        for bq in bank_questions_db:
            unit = units.get(bq.unit_id)
            bank_q_list.append({
                "id": bq.id,
                "question_text": bq.question_text,
                "normalized_text": bq.normalized_text,
                "embedding": bq.embedding,
                "marks": bq.marks,
                "blooms_level": bq.blooms_level,
                "unit_id": bq.unit_id,
                "unit_no": unit.unit_no if unit else None,
                "unit_title": unit.unit_title if unit else None,
            })
            
        # Optimization: Pre-parse embeddings once
        from matcher import prepare_bank_embeddings
        prepared_bank = prepare_bank_embeddings(bank_q_list)

        # Process each exam question
        match_results_list = []
        exam_q_list = []

        for q in questions:
            normalized = normalize_question(q.get("question_text", ""))
            embedding = encode_text(normalized)

            # Save extracted question
            eq = ExtractedExamQuestion(
                exam_paper_id=exam.id,
                section_name=q.get("section_name"),
                question_no=q.get("question_no"),
                question_text=q.get("question_text", ""),
                normalized_text=normalized,
                marks=q.get("marks"),
                blooms_level=q.get("blooms_level"),
                embedding=embedding_to_json(embedding) if embedding else None,
            )
            db.add(eq)
            db.flush()

            exam_q_list.append({
                "id": eq.id,
                "question_text": eq.question_text,
                "marks": eq.marks,
                "blooms_level": eq.blooms_level,
            })

            # Match against bank using PRE-PARSED embeddings
            best_bq, score, match_status = match_exam_to_bank(
                normalized, embedding, prepared_bank
            )

            mr = MatchResult(
                exam_question_id=eq.id,
                bank_question_id=best_bq["id"] if best_bq else None,
                similarity_score=score,
                match_status=match_status,
            )
            db.add(mr)
            db.flush()

            match_results_list.append({
                "exam_question_id": eq.id,
                "exam_question_text": eq.question_text,
                "bank_question_id": best_bq["id"] if best_bq else None,
                "bank_question_text": best_bq["question_text"] if best_bq else None,
                "similarity_score": round(score, 4),
                "match_status": match_status,
                "blooms_level": eq.blooms_level,
                "marks": eq.marks,
            })

        # Compute coverage
        coverage = compute_coverage_report(exam_q_list, bank_q_list, match_results_list)

        # Save report
        cr = CoverageReport(
            exam_paper_id=exam.id,
            report_data=json.dumps(coverage)
        )
        db.add(cr)
        doc.status = "approved"
        db.commit()

        return {
            "exam_paper_id": exam.id,
            "coverage_report_id": cr.id,
            "extracted_questions": len(questions),
            "bank_questions_compared": len(bank_q_list),
            "match_results": match_results_list,
            "coverage": coverage,
        }

    except HTTPException:
        raise
    except Exception as e:
        doc.status = "error"
        db.commit()
        logger.error(f"Exam analysis error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/exam-paper/{exam_id}/report")
def get_exam_report(exam_id: int, db: Session = Depends(get_db)):
    """Retrieve a previously computed coverage report"""
    cr = db.query(CoverageReport).filter(CoverageReport.exam_paper_id == exam_id).first()
    if not cr:
        raise HTTPException(status_code=404, detail="Report not found")
    return {
        "exam_paper_id": exam_id,
        "generated_at": cr.generated_at.isoformat(),
        "coverage": json.loads(cr.report_data)
    }


@app.get("/exam-papers")
def list_exam_papers(subject_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(ExamPaper)
    if subject_id:
        # If subject_id is provided, find all subjects with the same name and code
        # to ensure we show papers across departments if they share the same subject.
        subj = db.query(Subject).filter(Subject.id == subject_id).first()
        if subj:
            related_ids = [s.id for s in db.query(Subject).filter(
                Subject.name == subj.name,
                Subject.code == subj.code
            ).all()]
            q = q.filter(ExamPaper.subject_id.in_(related_ids))
        else:
            q = q.filter(ExamPaper.subject_id == subject_id)
    papers = q.order_by(ExamPaper.analyzed_at.desc()).all()
    
    subjects = {s.id: s.name for s in db.query(Subject).all()}
    result = []
    for p in papers:
        # Check if has report
        has_report = db.query(CoverageReport).filter(CoverageReport.exam_paper_id == p.id).first() is not None
        result.append({
            "id": p.id,
            "subject_id": p.subject_id,
            "subject_name": subjects.get(p.subject_id),
            "exam_type": p.exam_type,
            "exam_date": p.exam_date,
            "analyzed_at": p.analyzed_at.isoformat() if p.analyzed_at else None,
            "has_report": has_report,
        })
    return result


@app.delete("/exam-papers/{paper_id}")
def delete_exam_paper(paper_id: int, db: Session = Depends(get_db)):
    paper = db.query(ExamPaper).filter(ExamPaper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Exam paper not found")
    
    # Relationships with cascade will handle other tables
    db.delete(paper)
    db.commit()
    return {"status": "success", "message": "Exam paper and related analysis deleted"}


# ─── Dashboard Summary ────────────────────────────────────────────────────────

@app.get("/dashboard/summary")
def dashboard_summary(db: Session = Depends(get_db)):
    total_bank_qs = db.query(QuestionBankMaster).count()
    total_exams = db.query(ExamPaper).count()
    total_subjects = db.query(Subject).count()
    
    # Meaningful documents: Approved exam papers + Distinct Bank docs
    # This avoids showing '73' when most are failed uploads or noise.
    active_bank_docs = db.query(QuestionBankMaster.doc_id).distinct().count()
    total_docs = total_exams + active_bank_docs
    
    # Recent exam coverage
    recent_reports = []
    recent_exams = db.query(ExamPaper).order_by(ExamPaper.analyzed_at.desc()).limit(5).all()
    subjects_map = {s.id: s.name for s in db.query(Subject).all()}
    for exam in recent_exams:
        cr = db.query(CoverageReport).filter(CoverageReport.exam_paper_id == exam.id).first()
        if cr:
            try:
                data = json.loads(cr.report_data)
                recent_reports.append({
                    "exam_id": exam.id,
                    "subject": subjects_map.get(exam.subject_id, "Unknown"),
                    "exam_type": exam.exam_type,
                    "overall_coverage_pct": data.get("overall_coverage_pct", 0),
                    "weighted_coverage_pct": data.get("weighted_coverage_pct", 0),
                    "analyzed_at": exam.analyzed_at.isoformat() if exam.analyzed_at else None,
                })
            except:
                continue

    return {
        "total_bank_questions": total_bank_qs,
        "total_exam_papers": total_exams,
        "total_subjects": total_subjects,
        "total_bank_docs": active_bank_docs,
        "recent_coverage": recent_reports,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
