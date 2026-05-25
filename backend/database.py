from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./exam_coverage.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── Models ────────────────────────────────────────────────────────────────────

class Department(Base):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    code = Column(String(20), nullable=False, unique=True)
    subjects = relationship("Subject", back_populates="department")


class Regulation(Base):
    __tablename__ = "regulations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True)   # e.g. "R2021", "R2017"
    subjects = relationship("Subject", back_populates="regulation")


class Subject(Base):
    __tablename__ = "subjects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    code = Column(String(30), nullable=False)
    semester = Column(Integer, nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"))
    regulation_id = Column(Integer, ForeignKey("regulations.id"))
    department = relationship("Department", back_populates="subjects")
    regulation = relationship("Regulation", back_populates="subjects")
    units = relationship("SyllabusUnit", back_populates="subject")
    question_banks = relationship("QuestionBankMaster", back_populates="subject")


class SyllabusUnit(Base):
    __tablename__ = "syllabus_units"
    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), index=True)
    unit_no = Column(Integer, nullable=False)
    unit_title = Column(String(200), nullable=False)
    keywords = Column(Text, nullable=True)          # comma-separated keywords for unit detection
    subject = relationship("Subject", back_populates="units")
    questions = relationship("QuestionBankMaster", back_populates="unit")


class CourseOutcome(Base):
    __tablename__ = "course_outcomes"
    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    co_number = Column(String(10), nullable=False)   # e.g. CO1, CO2
    description = Column(Text, nullable=False)
    bloom_level = Column(String(10), nullable=True)  # K1-K6


class UploadedDocument(Base):
    __tablename__ = "uploaded_documents"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(300), nullable=False)
    file_path = Column(String(500), nullable=False)
    doc_type = Column(String(30), nullable=False)    # "question_bank" | "exam_paper"
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    unit_id = Column(Integer, ForeignKey("syllabus_units.id"), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(30), default="processing")  # processing | staged | approved | error
    uploaded_by = Column(String(100), nullable=True)
    subject = relationship("Subject")
    staging_questions = relationship("QuestionStagingReview", back_populates="document")


class QuestionStagingReview(Base):
    """Temporary holding area — faculty reviews & corrects before final save"""
    __tablename__ = "question_staging_review"
    id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(Integer, ForeignKey("uploaded_documents.id"), index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    unit_id = Column(Integer, ForeignKey("syllabus_units.id"), nullable=True)
    predicted_unit_id = Column(Integer, ForeignKey("syllabus_units.id"), nullable=True)
    section_name = Column(String(50), nullable=True)    # Part A / Part B
    question_no = Column(String(20), nullable=True)
    question_text = Column(Text, nullable=False)
    marks = Column(Float, nullable=True)
    blooms_level = Column(String(10), nullable=True)    # K1-K6
    question_type = Column(String(30), nullable=True)   # short / descriptive / problem
    confidence_score = Column(Float, nullable=True)
    review_status = Column(String(20), default="pending")   # pending | approved | rejected
    edited_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    document = relationship("UploadedDocument", back_populates="staging_questions")
    unit = relationship("SyllabusUnit", foreign_keys=[unit_id])


class QuestionBankMaster(Base):
    """Final approved question bank"""
    __tablename__ = "question_bank_master"
    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), index=True)
    unit_id = Column(Integer, ForeignKey("syllabus_units.id"), nullable=True, index=True)
    doc_id = Column(Integer, ForeignKey("uploaded_documents.id"), nullable=True, index=True)
    section_name = Column(String(50), nullable=True)
    question_no = Column(String(20), nullable=True)
    question_text = Column(Text, nullable=False)
    normalized_text = Column(Text, nullable=True)
    marks = Column(Float, nullable=True)
    blooms_level = Column(String(10), nullable=True)
    question_type = Column(String(30), nullable=True)
    embedding = Column(Text, nullable=True)   # JSON-serialized float list
    topic_keywords = Column(Text, nullable=True)
    added_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    subject = relationship("Subject", back_populates="question_banks")
    unit = relationship("SyllabusUnit", back_populates="questions")


class ExamPaper(Base):
    __tablename__ = "exam_papers"
    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    doc_id = Column(Integer, ForeignKey("uploaded_documents.id"))
    exam_type = Column(String(50), nullable=True)       # Internal / University / CAT
    exam_date = Column(String(20), nullable=True)
    analyzed_at = Column(DateTime, default=datetime.utcnow)
    extracted_questions = relationship("ExtractedExamQuestion", back_populates="exam_paper", cascade="all, delete-orphan")
    coverage_reports = relationship("CoverageReport", back_populates="exam_paper", cascade="all, delete-orphan")


class ExtractedExamQuestion(Base):
    __tablename__ = "extracted_exam_questions"
    id = Column(Integer, primary_key=True, index=True)
    exam_paper_id = Column(Integer, ForeignKey("exam_papers.id"))
    section_name = Column(String(50), nullable=True)
    question_no = Column(String(20), nullable=True)
    question_text = Column(Text, nullable=False)
    normalized_text = Column(Text, nullable=True)
    marks = Column(Float, nullable=True)
    blooms_level = Column(String(10), nullable=True)
    embedding = Column(Text, nullable=True)
    exam_paper = relationship("ExamPaper", back_populates="extracted_questions")
    match_results = relationship("MatchResult", back_populates="exam_question", cascade="all, delete-orphan")


class MatchResult(Base):
    __tablename__ = "match_results"
    id = Column(Integer, primary_key=True, index=True)
    exam_question_id = Column(Integer, ForeignKey("extracted_exam_questions.id"))
    bank_question_id = Column(Integer, ForeignKey("question_bank_master.id"), nullable=True)
    similarity_score = Column(Float, nullable=True)
    match_status = Column(String(20), nullable=False)   # matched | possible | not_matched
    exam_question = relationship("ExtractedExamQuestion", back_populates="match_results")
    bank_question = relationship("QuestionBankMaster")


class CoverageReport(Base):
    __tablename__ = "coverage_reports"
    id = Column(Integer, primary_key=True, index=True)
    exam_paper_id = Column(Integer, ForeignKey("exam_papers.id"))
    report_data = Column(Text, nullable=False)    # JSON
    generated_at = Column(DateTime, default=datetime.utcnow)
    exam_paper = relationship("ExamPaper", back_populates="coverage_reports")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(200), unique=True, nullable=False)
    hashed_password = Column(String(300), nullable=False)
    full_name = Column(String(200), nullable=True)
    role = Column(String(30), default="faculty")   # admin | faculty
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


def create_tables():
    Base.metadata.create_all(bind=engine)
