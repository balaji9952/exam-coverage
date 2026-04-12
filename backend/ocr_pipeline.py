"""
OCR + Layout Parsing Pipeline for Question Papers and Question Banks
Handles Indian college exam formats with flexible question number detection.
"""

import re
import json
import io
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# ─── Bloom Level Patterns ───────────────────────────────────────────────────────
BLOOMS_PATTERNS = {
    "K1": re.compile(r'\b(K1|BTL[-\s]?1|L1|BL[-\s]?1|CO[-\s]?1|Remember|Define|State|List|Identify|Recall|Name|Label|Match|Write)\b', re.IGNORECASE),
    "K2": re.compile(r'\b(K2|BTL[-\s]?2|L2|BL[-\s]?2|CO[-\s]?2|Understand|Explain|Describe|Summarize|Discuss|Interpret|Classify|Illustrate)\b', re.IGNORECASE),
    "K3": re.compile(r'\b(K3|BTL[-\s]?3|L3|BL[-\s]?3|CO[-\s]?3|Apply|Solve|Demonstrate|Use|Compute|Calculate|Implement|Show)\b', re.IGNORECASE),
    "K4": re.compile(r'\b(K4|BTL[-\s]?4|L4|BL[-\s]?4|CO[-\s]?4|Analyze|Compare|Differentiate|Examine|Break\s+down|Categorize|Contrast)\b', re.IGNORECASE),
    "K5": re.compile(r'\b(K5|BTL[-\s]?5|L5|BL[-\s]?5|CO[-\s]?5|Evaluate|Justify|Assess|Judge|Critique|Recommend)\b', re.IGNORECASE),
    "K6": re.compile(r'\b(K6|BTL[-\s]?6|L6|BL[-\s]?6|CO[-\s]?6|Create|Design|Develop|Formulate|Construct|Plan|Produce|Draw)\b', re.IGNORECASE),
}

# ─── Verb Groups for intent inference ─────────────────────────────────────────
VERB_GROUPS = {
    "recall": ["define", "what is", "state", "mention", "list", "name", "identify", "recall", "give", "write", "enumerate"],
    "explain": ["explain", "elaborate", "describe", "discuss", "comment", "illustrate", "highlight", "outline", "summarize", "brief"],
    "apply": ["solve", "calculate", "compute", "find", "determine", "implement", "use", "apply", "show", "evaluate", "derive"],
    "analyze": ["analyze", "analyse", "compare", "differentiate", "distinguish", "examine", "categorize", "classify", "contrast"],
    "design": ["design", "develop", "create", "construct", "formulate", "plan", "propose", "draw", "build", "write a program"],
}

MARKS_PATTERNS = [
    re.compile(r'\[\s*(\d+)\s*\]'),                        # [2], [16]
    re.compile(r'\(\s*(\d+)\s*[Mm]arks?\s*\)'),            # (2 Marks)
    re.compile(r'\b(\d+)\s*[Mm]arks?\b'),                  # 2 marks
    re.compile(r'\(\s*(\d+)\s*\)\s*$'),                    # (16) at end of line
    re.compile(r'(\d+)\s*[Mm]\b'),                         # 2M shorthand
]

SECTION_PATTERNS = re.compile(
    r'^\s*(PART|SECTION|Section|Part)\s*[-–—]?\s*([A-Za-z0-9]+)',
    re.IGNORECASE
)

# ─── FLEXIBLE question number patterns ──────────────────────────────────────
#  Handles:
#    1.  1)  1:  Q1  Q.1  Q.No.1  1(a)  (1)  i.  ii.  (i)
QUESTION_NO_PATTERNS = re.compile(
    r'^('
    r'\(\s*[ivxIVX]+\s*\)'         # (i), (ii), (iv)
    r'|[ivx]+\s*[.)]'              # i. ii. iv)
    r'|\(\s*[a-zA-Z]\s*\)'         # (a), (b)
    r'|Q\s*\.?\s*No\s*\.?\s*\d+'   # Q.No.1, QNo1
    r'|Q\s*\.?\s*\d+\s*[.):–-]?'  # Q1. Q.1 Q1:
    r'|\d{1,2}\s*\(\s*[a-z]\s*\)' # 1(a) 2(b)
    r'|\d{1,2}\s*[.):]\s*'        # 1. 1) 1:
    r'|\(\s*\d{1,2}\s*\)'         # (1) (12)
    r'|[a-hA-H]\s*[.)]\s*'       # a. b) (sub-questions)
    r')',
    re.IGNORECASE
)

# Lines that look like noise / headers — not question text
NOISE_PATTERNS = re.compile(
    r'^\s*('
    r'Reg\.?\s*(No|Number)?\.?'     # Reg. No.
    r'|Roll\s*(No|Number)?\.?'      # Roll No.
    r'|Answer\s+(ALL|any|all)'      # Answer ALL questions
    r'|Maximum\s+Marks?'            # Maximum Marks
    r'|Time\s*[:–]\s*\d'           # Time: 3 hours
    r'|Duration\s*[:–]'            # Duration
    r'|Hall\s*Ticket'              # Hall Ticket
    r'|Question\s+Paper'           # Question Paper
    r'|UNIVERSITY\s+EXAM'          # UNIVERSITY EXAM
    r'|Semester\s+Exam'            # Semester Exam
    r'|Course\s+(Code|Name)'        # Course Code/Name
    r'|[-_=]{5,}'                  # border lines --------
    r'|\*{3,}'                     # ***
    r')',
    re.IGNORECASE
)

# Inline K-level tag pattern: "(K1)", "[K2]", "K3", " CO1" at end of line
INLINE_BLOOM_TAG = re.compile(r'[\(\[]\s*(K[1-6]|BTL\s*\d)\s*[\)\]]|(?<!\w)(K[1-6])(?!\w)', re.IGNORECASE)
INLINE_CO_TAG    = re.compile(r'[\(\[]\s*CO\s*\d\s*[\)\]]', re.IGNORECASE)
INLINE_MARKS_END = re.compile(r'[\(\[]\s*\d+\s*[\)\]]$')  # (16) or [2] at end


def extract_marks(text: str) -> Optional[float]:
    for pattern in MARKS_PATTERNS:
        m = pattern.search(text)
        if m:
            try:
                v = float(m.group(1))
                # Sanity check: marks should be between 1 and 100
                if 1 <= v <= 100:
                    return v
            except Exception:
                pass
    return None


def extract_blooms(text: str) -> Optional[str]:
    # First, check explicit K-labels in the line
    m = INLINE_BLOOM_TAG.search(text)
    if m:
        raw = m.group(0).upper()
        for lvl in ["K1","K2","K3","K4","K5","K6"]:
            if lvl in raw or f"BTL{lvl[-1]}" in raw.replace(' ',''):
                return lvl
    # Second, check full phrase Bloom patterns
    for level, pattern in BLOOMS_PATTERNS.items():
        if pattern.search(text):
            return level
    # Third, infer from command verb at start of question
    lower = text.lower().strip()
    for verb in VERB_GROUPS["recall"]:
        if lower.startswith(verb):
            return "K1"
    for verb in VERB_GROUPS["explain"]:
        if lower.startswith(verb):
            return "K2"
    for verb in VERB_GROUPS["apply"]:
        if lower.startswith(verb):
            return "K3"
    for verb in VERB_GROUPS["analyze"]:
        if lower.startswith(verb):
            return "K4"
    for verb in VERB_GROUPS["design"]:
        if lower.startswith(verb):
            return "K6"
    return None


def normalize_question(text: str) -> str:
    """Clean and normalize question text for semantic comparison"""
    text = text.strip()
    # Remove marks annotations
    for p in MARKS_PATTERNS:
        text = p.sub("", text)
    # Remove inline Bloom/CO tags
    text = INLINE_BLOOM_TAG.sub("", text)
    text = INLINE_CO_TAG.sub("", text)
    # Remove Bloom level words (to reduce surface noise in matching)
    for pattern in BLOOMS_PATTERNS.values():
        text = pattern.sub("", text)
    # Remove question number prefixes
    text = re.sub(r'^\(\s*[ivx]+\s*\)\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^[ivx]+\s*[.)\s]\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^\(\s*[a-z]\s*\)\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^Q\s*\.?\s*No\s*\.?\s*\d+\s*[.):–-]?\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^Q\s*\.?\s*\d+\s*[.):–-]?\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^\d{1,2}\s*[.):]\s*', '', text)
    text = re.sub(r'^\(\s*\d{1,2}\s*\)\s*', '', text)
    text = re.sub(r'^[a-h]\s*[.)]\s*', '', text, flags=re.IGNORECASE)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    # Lowercase
    text = text.lower()
    # Remove trailing punctuation
    text = text.rstrip('.')
    return text


def is_question_start(line: str) -> Optional[re.Match]:
    """Return match if line looks like a new question start."""
    m = QUESTION_NO_PATTERNS.match(line.strip())
    return m


def is_section_header(line: str) -> Optional[re.Match]:
    return SECTION_PATTERNS.match(line.strip())


def is_noise(line: str) -> bool:
    return bool(NOISE_PATTERNS.match(line.strip()))


def parse_questions_from_text(raw_text: str) -> List[Dict]:
    """
    Parse structured questions from raw OCR/PDF text.
    Handles multi-line questions, inline marks, inline Bloom tags.
    """
    lines = [l.rstrip() for l in raw_text.split('\n')]
    questions = []
    current_section = "General"
    current_q: Optional[Dict] = None

    def flush():
        nonlocal current_q
        if current_q:
            qt = current_q["question_text"].strip()
            # Must be at least 8 characters to be a real question
            if qt and len(qt) >= 8:
                current_q["question_text"] = qt
                current_q["normalized_text"] = normalize_question(qt)
                if not current_q.get("marks"):
                    current_q["marks"] = extract_marks(qt)
                if not current_q.get("blooms_level"):
                    current_q["blooms_level"] = extract_blooms(qt)
                current_q["question_type"] = classify_question_type(current_q.get("marks"))
                questions.append(current_q)
        current_q = None

    for raw_line in lines:
        line = raw_line.strip()

        # Skip blank lines
        if not line:
            continue

        # Skip noise lines (headers, borders, instructions)
        if is_noise(line):
            continue

        # Section header (Part A, Part B, Section I ...)
        sec_match = is_section_header(line)
        if sec_match:
            flush()
            current_section = line
            continue

        # New question start
        q_match = is_question_start(line)
        if q_match:
            flush()
            qno_str = q_match.group(0).strip()
            rest = line[q_match.end():]
            marks = extract_marks(line)
            blooms = extract_blooms(line)
            current_q = {
                "question_no": qno_str,
                "section_name": current_section,
                "question_text": rest,
                "marks": marks,
                "blooms_level": blooms,
                "question_type": classify_question_type(marks),
            }
            continue

        # Continuation line — attach to current question
        if current_q is not None:
            current_q["question_text"] += " " + line
            if not current_q.get("marks"):
                current_q["marks"] = extract_marks(line)
            if not current_q.get("blooms_level"):
                current_q["blooms_level"] = extract_blooms(line)
        else:
            # No question started yet — could be a question without a number prefix
            # If it looks substantial and not a header, treat it as a bare question
            if len(line) > 20 and not is_noise(line):
                # Heuristic: if it starts with a capital and has question-like verbs
                lower = line.lower()
                is_question_like = any(
                    lower.startswith(v) or f" {v} " in lower
                    for group in VERB_GROUPS.values()
                    for v in group
                )
                if is_question_like:
                    flush()
                    marks = extract_marks(line)
                    blooms = extract_blooms(line)
                    current_q = {
                        "question_no": "—",
                        "section_name": current_section,
                        "question_text": line,
                        "marks": marks,
                        "blooms_level": blooms,
                        "question_type": classify_question_type(marks),
                    }

    flush()
    return questions


def classify_question_type(marks: Optional[float]) -> str:
    if marks is None:
        return "unknown"
    if marks <= 2:
        return "short"
    elif marks <= 8:
        return "medium"
    else:
        return "descriptive"


async def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF. Tries pdfplumber first; falls back to OCR for scanned PDFs."""
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                # Try native text extraction
                page_text = page.extract_text()
                if page_text and len(page_text.strip()) > 30:
                    text_parts.append(page_text)
                else:
                    # Fallback: render page as image and OCR
                    logger.info("Page has no text layer — trying image OCR fallback")
                    try:
                        img = page.to_image(resolution=200).original
                        ocr_text = await _ocr_pil_image(img)
                        if ocr_text:
                            text_parts.append(ocr_text)
                    except Exception as ocr_err:
                        logger.warning(f"Page OCR fallback failed: {ocr_err}")

        result = "\n".join(text_parts)
        logger.info(f"PDF extraction: {len(result)} chars from {len(pdf.pages) if hasattr(pdf, 'pages') else '?'} pages")
        return result
    except Exception as e:
        logger.error(f"PDF text extraction error: {e}")
        return ""


async def _ocr_pil_image(pil_img) -> str:
    """OCR a PIL image object."""
    try:
        import pytesseract
        from PIL import ImageFilter, ImageEnhance
        img = pil_img.convert("L")
        img = img.filter(ImageFilter.SHARPEN)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.8)
        text = pytesseract.image_to_string(img, config='--psm 6 --oem 3')
        return text
    except Exception as e:
        logger.error(f"PIL OCR error: {e}")
        return ""


async def extract_text_from_image(file_bytes: bytes) -> str:
    """Extract text from image file using Tesseract OCR with preprocessing."""
    try:
        from PIL import Image, ImageFilter, ImageEnhance
        img = Image.open(io.BytesIO(file_bytes))
        text = await _ocr_pil_image(img)
        logger.info(f"Image OCR: {len(text)} chars extracted")
        return text
    except Exception as e:
        logger.error(f"Image OCR error: {e}")
        return ""


async def process_uploaded_file(file_bytes: bytes, filename: str) -> Tuple[str, List[Dict]]:
    """Main entry point: given file bytes, return raw text + parsed questions."""
    filename_lower = filename.lower()

    if filename_lower.endswith(".pdf"):
        raw_text = await extract_text_from_pdf(file_bytes)
    elif filename_lower.endswith((".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp")):
        raw_text = await extract_text_from_image(file_bytes)
    elif filename_lower.endswith(".txt"):
        raw_text = file_bytes.decode("utf-8", errors="ignore")
    else:
        raw_text = file_bytes.decode("utf-8", errors="ignore")

    if not raw_text.strip():
        logger.warning(f"No text extracted from {filename}")
        return "", []

    questions = parse_questions_from_text(raw_text)
    logger.info(f"Parsed {len(questions)} questions from {filename}")
    return raw_text, questions
