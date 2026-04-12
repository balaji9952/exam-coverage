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
from sqlalchemy.orm import Session

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
    db: Session = Depends(get_db)
):
    q = db.query(Subject)
    if department_id:
        q = q.filter(Subject.department_id == department_id)
    if semester:
        q = q.filter(Subject.semester == semester)
    subjects = q.all()
    result = []
    for s in subjects:
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

        staging_records = []
        for q in questions:
            sr = QuestionStagingReview(
                doc_id=doc.id,
                subject_id=subject_id,
                unit_id=unit_id,
                predicted_unit_id=unit_id,
                section_name=q.get("section_name"),
                question_no=q.get("question_no"),
                question_text=q.get("question_text", ""),
                marks=q.get("marks"),
                blooms_level=q.get("blooms_level"),
                question_type=q.get("question_type"),
                confidence_score=0.85 if q.get("question_text") else 0.3,
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
    questions = db.query(QuestionStagingReview).filter(
        QuestionStagingReview.doc_id == doc_id
    ).all()
    
    units = {u.id: u for u in db.query(SyllabusUnit).all()}
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
            "unit_title": units[q.unit_id].unit_title if q.unit_id and q.unit_id in units else None,
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


# ─── Question Bank Management ─────────────────────────────────────────────────

@app.get("/question-bank")
def list_bank_questions(
    subject_id: Optional[int] = None,
    unit_id: Optional[int] = None,
    blooms_level: Optional[str] = None,
    db: Session = Depends(get_db)
):
    q = db.query(QuestionBankMaster)
    if subject_id:
        q = q.filter(QuestionBankMaster.subject_id == subject_id)
    if unit_id:
        q = q.filter(QuestionBankMaster.unit_id == unit_id)
    if blooms_level:
        q = q.filter(QuestionBankMaster.blooms_level == blooms_level)
    
    questions = q.all()
    units = {u.id: u for u in db.query(SyllabusUnit).all()}
    result = []
    for bq in questions:
        result.append({
            "id": bq.id,
            "question_no": bq.question_no,
            "section_name": bq.section_name,
            "question_text": bq.question_text,
            "marks": bq.marks,
            "blooms_level": bq.blooms_level,
            "question_type": bq.question_type,
            "unit_id": bq.unit_id,
            "unit_title": units[bq.unit_id].unit_title if bq.unit_id and bq.unit_id in units else None,
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

        # Fetch question bank for this subject
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

            # Match against bank
            best_bq, score, match_status = match_exam_to_bank(
                normalized, embedding, bank_q_list
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


# ─── Dashboard Summary ────────────────────────────────────────────────────────

@app.get("/dashboard/summary")
def dashboard_summary(db: Session = Depends(get_db)):
    total_bank = db.query(QuestionBankMaster).count()
    total_exams = db.query(ExamPaper).count()
    total_subjects = db.query(Subject).count()
    total_docs = db.query(UploadedDocument).count()
    
    # Recent exam coverage
    recent_reports = []
    recent_exams = db.query(ExamPaper).order_by(ExamPaper.analyzed_at.desc()).limit(5).all()
    subjects_map = {s.id: s.name for s in db.query(Subject).all()}
    for exam in recent_exams:
        cr = db.query(CoverageReport).filter(CoverageReport.exam_paper_id == exam.id).first()
        if cr:
            data = json.loads(cr.report_data)
            recent_reports.append({
                "exam_id": exam.id,
                "subject": subjects_map.get(exam.subject_id, "Unknown"),
                "exam_type": exam.exam_type,
                "overall_coverage_pct": data.get("overall_coverage_pct", 0),
                "weighted_coverage_pct": data.get("weighted_coverage_pct", 0),
                "analyzed_at": exam.analyzed_at.isoformat() if exam.analyzed_at else None,
            })

    return {
        "total_bank_questions": total_bank,
        "total_exam_papers": total_exams,
        "total_subjects": total_subjects,
        "total_documents": total_docs,
        "recent_coverage": recent_reports,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
