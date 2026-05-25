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
    "recall": ["define", "what", "how", "why", "state", "mention", "list", "name", "identify", "recall", "give", "write", "enumerate"],
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
    re.compile(r'\b(\d+)\s*[Mm]\b'),                         # 2M shorthand
    re.compile(r'[,.\s]+(\d{1,2})\s*$'),                    # ... . 13 at end of line
    re.compile(r'(?<=\d\.\s)(\d+)(?=\s+K[1-6])'),           # 1. 2 K2 (tabular)
    re.compile(r'\s+(\d+)\s+K[1-6]\s*$'),                   # ... 2 K2 at end of line
    re.compile(r'^\s*(\d+)\s*$'),                           # 2 (standalone tabular)
]

SECTION_PATTERNS = re.compile(
    r'^(?:Q\.?\s*No\.?\s*)?(PART|SECTION|Section|Part)\s*[-–—\s]*([A-Za-z0-9]+)',
    re.IGNORECASE
)

# ─── FLEXIBLE question number patterns ──────────────────────────────────────
#  Handles:
#    1.  1)  1:  Q1  Q.1  Q.No.1  1(a)  (1)  i.  ii.  (i)
QUESTION_NO_PATTERNS = re.compile(
    r'^('
    r'\(\s*[ivxIVX]+\s*\)'         # (i), (ii), (iv)
    r'|[ivxIVX]+\s*[.),]'          # i. ii. iv) iv,
    r'|\(\s*[a-zA-Z]\s*\)'         # (a), (b)
    r'|Q\s*\.?\s*No\s*\.?\s*\d+'   # Q.No.1, QNo1
    r'|Q\s*\.?\s*\d+\s*[\-.:),–]?'  # Q1. Q.1 Q1: Q1,
    r'|\d{1,2}\s*\(\s*[a-z]\s*\)' # 1(a) 2(b)
    r'|\d{1,3}\s*[.):,]\s*'        # 1. 1) 1: 1, (Updated to 3 digits)
    r'|\(\s*\d{1,3}\s*\)'         # (1) (123) (Updated to 3 digits)
    r'|[a-hA-H]\s*[.),]\s*'       # a. b) a, (sub-questions)
    r')',
    re.IGNORECASE
)

# Pattern for detecting a question start IN THE MIDDLE of a string
INLINE_Q_START_PATTERN = re.compile(
    r'(?:^|[\.?!,\]\)])\s*('
    r'\d{1,2}\s*[.):,]\s+[A-Z]'           # 7. What
    r'|\(\s*[a-z]\s*\)\s+[A-Z]'           # (a) Explain
    r'|Q\s*\.?\s*\d+\s*[.):,]\s+[A-Z]'    # Q7. Define
    r')'
)

OCR_INLINE_QNO_VERBS = [
    "what is", "how does", "why", "define", "explain", "list", "compare",
    "differentiate", "discuss", "elaborate", "compute", "find", "solve",
    "give", "identify", "mention", "examine", "elucidate", "construct",
    "analyze", "analyse", "apply", "state", "describe", "distinguish",
    "illustrate", "relate", "write", "design"
]
OCR_INLINE_QNO_PATTERN = re.compile(
    r'^\s*(\d{1,2})\s*[,.:]?\s+(?=(?:'
    + "|".join(re.escape(verb) for verb in sorted(OCR_INLINE_QNO_VERBS, key=len, reverse=True))
    + r')\b)',
    re.IGNORECASE
)
STANDALONE_OR_PATTERN = re.compile(r'^[\s\)\],.;:-]*or[\s,.;:()\-]*$', re.IGNORECASE)
STANDALONE_MARKS_LINE = re.compile(r'^\s*[\(\[]\s*(\d+)\s*[\)\]]\s*$')
STANDALONE_BLOOM_LINE = re.compile(r'^\s*(K[1-6])\s*$', re.IGNORECASE)

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
    r'|END\s+OF\s+QUESTION'         # End of paper/bank
    r'|Downloaded\s+from'           # Downloaded from watermark sites
    r'|(?:Engg|Enggl)Tree(?:\.com)?' # EnggTree watermark lines
    r'|Signature\s+of\s+the\s+(staff|HoD)' # Staff/HoD signatures
    r'|^\s*\d{1,3}\s*$'            # Standalone page numbers or stray digits
    r'|\d{1,2}\s+\d{4,}\s*$'       # Page code lines like "2 20070"
    r'|[-_=]{5,}'                  # border lines --------
    r'|\*{3,}'                     # ***
    r')',
    re.IGNORECASE
)

# ─── Header & Unit Patterns ───────────────────────────────────────────────────
HEADER_PATTERNS = {
    "subject_name": re.compile(r'(?:Subject|Course|QUESTION BANK)(?:\s+Name)?\s*[:–—\-]\s*([A-Z\s\-–—]+?)(?=\s+(?:Course Code|Class|Semester|Department)|$)', re.IGNORECASE),
    "subject_code": re.compile(r'(?:Subject|Course)?\s*Code\s*[:–-]\s*([A-Z0-9]+)', re.IGNORECASE),
    "department": re.compile(r'Department\s+of\s+(.*?)(?=\s+(?:Course|Semester|Regulation)|$)', re.IGNORECASE),
    "regulation": re.compile(r'(?:Reg|Regulation)\s*[:–-]?\s*(R\d{4}|\d{4})', re.IGNORECASE),
    "semester": re.compile(r'Semester\s*[:–-]?\s*([IVX]+|\d+)', re.IGNORECASE),
}

UNIT_HEADER_PATTERN = re.compile(r'^\s*(UNIT|Unit)\s*([IVX]+|\d+)\s*[-–—:]?\s*(.*)', re.IGNORECASE)

# Inline K-level tag pattern: "(K1)", "[K2]", "K3", " CO1" at end of line
INLINE_BLOOM_TAG = re.compile(r'[\(\[]\s*(K[1-6]|BTL\s*\d)\s*[\)\]]|(?<!\w)(K[1-6])(?!\w)', re.IGNORECASE)
INLINE_CO_TAG    = re.compile(r'[\(\[]\s*CO\s*\d\s*[\)\]]', re.IGNORECASE)
INLINE_MARKS_TAG = re.compile(r'[\(\[]\s*(\d+)\s*[\)\]]')  # Matches [2] or (16) anywhere
INLINE_MARKS_END = re.compile(r'[\(\[]\s*(\d+)\s*[\)\]]\s*$')  # Matches [2] or (16) at the end of a line


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
    
    # Check for standalone K tokens in tabular format
    m = re.search(r'\b(K[1-6])\b', text)
    if m:
        return m.group(1).upper()
        
    return None


def remove_marking_artifacts(text: str) -> str:
    """Remove marking words like 13, 15, co2, co3, co, cos, etc."""
    if not text:
        return text
    
    # 1. Matches combination markings: e.g. "13 CO4,", "13 COs,", "15 COS,", "15 COs,", "13 CO", "15 CO", etc.
    text = re.sub(
        r'\b(?:[2-9]|1[0-9])\s*(?:CO[1-6sS]?|C0[1-6sS]?|COS|COs|CO)\b\s*,?\s*',
        ' ',
        text,
        flags=re.IGNORECASE
    )
    
    # 2. Matches standalone CO indicators like: CO2, CO3, CO4, CO5, COs, COS (case-insensitive)
    text = re.sub(
        r'(?<![-/])\b(?:CO[1-6]|C0[1-6]|COs|COS)\b\s*,?\s*',
        ' ',
        text,
        flags=re.IGNORECASE
    )
    
    # 3. Matches standalone CO/co word (case-insensitive, protected against hyphens/slashes)
    text = re.sub(
        r'(?<![-/])\bCO\b(?!\s*[-/])\s*,?\s*',
        ' ',
        text,
        flags=re.IGNORECASE
    )
    
    # 4. Matches standalone marks numbers like: 12, 13, 14, 15, 16, 20
    # only if not followed by a percent sign, hyphen, or more digits (to protect "15-digit", "13%", etc.)
    text = re.sub(
        r'\b(?:12|13|14|15|16|20)\b(?!\s*[-%\d])\s*,?\s*',
        ' ',
        text
    )
    
    # 5. Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def normalize_question(text: str) -> str:
    """Clean and normalize question text for semantic comparison"""
    text = remove_marking_artifacts(text)
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


def normalize_ocr_line(line: str) -> str:
    """Fix common OCR numbering glitches before parsing the line."""
    line = re.sub(r'^\|\s*', '', line).strip()
    m = OCR_INLINE_QNO_PATTERN.match(line)
    if m:
        line = f"{m.group(1)}. {line[m.end():].strip()}"
    return line


def roman_to_int(roman: str) -> int:
    roman = roman.upper().strip()
    val = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    res = 0
    for i in range(len(roman)):
        if i > 0 and val[roman[i]] > val[roman[i - 1]]:
            res += val[roman[i]] - 2 * val[roman[i - 1]]
        else:
            res += val[roman[i]]
    return res


def clean_extracted_text(text: str) -> str:
    """Stage 1: Basic cleanup of OCR noise and watermarks."""
    if not text: return ""
    
    # Remove watermarks and common noise
    text = re.sub(r'Downloaded from EnggTree\.com', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Page \d+ of \d+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\b\d{12}\b', '', text) # Registration numbers
    
    # Fix broken sub-question markers (OCR errors)
    text = re.sub(r'\bta\)', '(a)', text)
    text = re.sub(r'\btb\)', '(b)', text)
    text = re.sub(r'\btc\)', '(c)', text)
    text = re.sub(r'\btd\)', '(d)', text)
    
    # Normalize duplicate punctuation (often from OCR artifacts)
    text = re.sub(r'\.{2,}', '.', text)
    text = re.sub(r',{2,}', ',', text)
    
    # Normalize spaces
    text = re.sub(r'[ \t]+', ' ', text)
    return text


def preprocess_raw_text(text: str) -> str:
    """Stage 2: Split merged questions into separate lines."""
    text = clean_extracted_text(text)
    
    # 1. Handle Marks/Bloom Tag + Question Number: "... (16) 14. Explain..."
    text = re.sub(r'([\(\[]\s*\d+\s*[\)\]])\s+(\d{1,2}\s*[.):,])', r'\1\n\2', text)
    text = re.sub(r'([\(\[]\s*\d+\s*[\)\]])\s+(\(\s*[a-zA-Z]\s*\))', r'\1\n\2', text)
    text = re.sub(r'([\(\[]\s*\d+\s*[\)\]])\s+(Q\s*\.?\s*\d+)', r'\1\n\2', text)
    
    # 2. Handle period/sentence end + Question Number: "... detail. 15. Describe..."
    text = re.sub(r'([.?!,])\s*(\d{1,2}\s*[.):,]\s+[A-Z])', r'\1\n\2', text)
    text = re.sub(r'([.?!,])\s*(\(\s*[a-zA-Z]\s*\)\s+[A-Z])', r'\1\n\2', text)
    
    # 3. Handle cases where the number is just merged: "example.7. What"
    text = re.sub(r'([a-zA-Z0-9])\s*[.?!,]\s*(\d{1,2}\s*[.):,])', r'\1.\n\2', text)

    # 4. Handle Part Transitions
    text = re.sub(r'(PART\s+[A-C])', r'\n\1\n', text, flags=re.IGNORECASE)

    return text


def post_process_questions(questions: List[Dict]) -> List[Dict]:
    """Stage 4: Validation and final cleanup pass."""
    final_questions = []
    for q in questions:
        text = q["question_text"].strip()
        if not text: continue
        
        # CONFIDENCE CHECK: If question text contains an inline question number, split it.
        # This handles cases that the regex pre-processing might have missed.
        split_pattern = r'([\.?!,])\s*(\d{1,2}\s*[.):,]\s+[A-Z]|\(\s*[a-z]\s*\)\s+[A-Z])'
        if re.search(split_pattern, text):
            sub_parts = re.split(f'({split_pattern})', text)
            # Reconstruct and split
            current_t = sub_parts[0]
            for i in range(1, len(sub_parts), 2):
                separator = sub_parts[i]
                payload = sub_parts[i+1] if i+1 < len(sub_parts) else ""
                
                # The separator contains the end of previous sentence and start of next
                sep_match = re.search(r'([\.?!,])\s+(\d{1,2}\s*[.):,])\s+([A-Z].*)', separator + payload)
                if sep_match:
                    # Previous question ends here
                    prev_end = sep_match.group(1)
                    q_copy = q.copy()
                    q_copy["question_text"] = (current_t + prev_end).strip()
                    final_questions.append(q_copy)
                    
                    # Next question starts here
                    new_q_no = sep_match.group(2)
                    current_t = sep_match.group(3)
                    # We create a temporary new question
                    q = q.copy()
                    q["question_no"] = new_q_no
                else:
                    current_t += separator + payload
            
            q["question_text"] = current_t.strip()
            final_questions.append(q)
        else:
            final_questions.append(q)

    # Final cleanup of all questions
    for q in final_questions:
        # Remove trailing marks like (16)
        q["question_text"] = re.sub(r'\s*[\(\[]\s*\d+\s*[\)\]]\s*$', '', q["question_text"])
        # Remove stray numbers at the end
        q["question_text"] = re.sub(r'\s+\d{1,2}\s*$', '', q["question_text"])
        # Final space normalization
        q["question_text"] = re.sub(r'\s+', ' ', q["question_text"]).strip()
        
    return final_questions


def parse_questions_from_text(raw_text: str) -> List[Dict]:
    """
    Parse structured questions from raw OCR/PDF text.
    Handles multi-line questions, inline marks, inline Bloom tags.
    """
    # PRE-SPLIT: Handle cases where multiple questions are merged on the same line.
    raw_text = preprocess_raw_text(raw_text)

    lines = [l.rstrip() for l in raw_text.split('\n')]
    questions = []
    current_section = "GENERAL"
    current_section_marks: Optional[float] = None
    current_unit_no = 0
    current_unit_title = None
    current_q: Optional[Dict] = None

    def flush():
        nonlocal current_q
        if current_q:
            raw_qt = current_q["question_text"].strip()
            qt = clean_question_text(raw_qt)
            
            if qt and not current_q.get("marks"):
                current_q["marks"] = current_section_marks or extract_marks(qt)
            if qt and not current_q.get("blooms_level"):
                current_q["blooms_level"] = extract_blooms(qt)

            # Must still look like a real question after cleanup
            if qt and len(qt) >= 8 and not is_junk_question(
                current_q.get("question_no", ""),
                qt,
                current_q.get("marks"),
                current_q.get("blooms_level"),
            ):
                current_q["question_text"] = qt
                current_q["normalized_text"] = normalize_question(qt)
                current_q["question_type"] = classify_question_type(current_q.get("marks"))
                questions.append(current_q)
        current_q = None

    for raw_line in lines:
        line = normalize_ocr_line(raw_line)

        # Skip blank lines
        if not line:
            continue

        # Skip standalone "Or" artifacts like "Or", ") Or", or "Or ,"
        if STANDALONE_OR_PATTERN.match(line):
            continue

        # Skip noise lines (headers, borders, instructions)
        if is_noise(line):
            continue

        # Unit header (UNIT I — ...)
        unit_match = UNIT_HEADER_PATTERN.match(line)
        if unit_match:
            flush()
            u_no_str = unit_match.group(2)
            try:
                if u_no_str.isdigit():
                    current_unit_no = int(u_no_str)
                else:
                    current_unit_no = roman_to_int(u_no_str)
            except:
                current_unit_no += 1
            current_unit_title = unit_match.group(3).strip()
            continue

        # Section header (Part A, Part B, Section I ...)
        sec_match = is_section_header(line)
        if sec_match:
            flush()
            # Special case for headers like (10 x 2 = 20 Marks)
            # We want the '2' marks per question, not the total '20'
            formula_match = re.search(r'\(?\d+\s*x\s*(\d+)', line, re.I)
            if formula_match:
                current_section_marks = float(formula_match.group(1))
            else:
                current_section_marks = extract_marks(line)
            
            # Clean section name like "PART - A (2 Marks)" -> "PART - A"
            clean_sec = re.sub(r'\s*[\(\[].*[\)\]]\s*$', '', line).strip().upper()
            current_section = clean_sec
            continue

        # A bare marks/bloom line usually belongs to the current question.
        if current_q is not None:
            marks_only = STANDALONE_MARKS_LINE.match(line)
            if marks_only:
                if not current_q.get("marks"):
                    current_q["marks"] = float(marks_only.group(1))
                continue

            bloom_only = STANDALONE_BLOOM_LINE.match(line)
            if bloom_only:
                if not current_q.get("blooms_level"):
                    current_q["blooms_level"] = bloom_only.group(1).upper()
                continue

        # New question start
        q_match = is_question_start(line)
        if q_match:
            flush()
            qno_str = q_match.group(0).strip()
            rest = line[q_match.end():].strip()
            
            # Check for [2] K1 at the end of the line
            end_meta = re.search(r'[\(\[]\s*(\d+)\s*[\)\]]\s*(K[1-6])\s*$', line, re.I)
            marks = None
            blooms = None
            if end_meta:
                marks = float(end_meta.group(1))
                blooms = end_meta.group(2).upper()
                # Strip this from the text
                rest = line[q_match.end():end_meta.start()].strip()
            else:
                # Check for tabular metadata: "1. 2 K2"
                tab_meta = re.search(r'^(\d+)\s+(K[1-6])(?:\s+|$)', rest)
                if tab_meta:
                    marks = float(tab_meta.group(1))
                    blooms = tab_meta.group(2)
                    rest = rest[tab_meta.end():].strip()
                else:
                    if not marks: marks = extract_marks(line)
                    if not blooms: blooms = extract_blooms(line)
            
            current_q = {
                "question_no": qno_str,
                "section_name": current_section.upper(),
                "question_text": rest,
                "marks": marks,
                "blooms_level": blooms,
                "question_type": classify_question_type(marks),
                "unit_no": current_unit_no,
                "unit_title": current_unit_title,
            }
            continue

        # Continuation line — attach to current question
        if current_q is not None:
            # Check if this line looks like a completely new question that missed its number
            is_new_question_without_number = False
            if len(line) > 15 and (line[0].isupper() or line[0].isdigit()):
                # Strip leading numbers/spaces just for the verb check
                clean_start = re.sub(r'^\d+\s*', '', line)
                if clean_start and clean_start[0].isupper():
                    lower_line = clean_start.lower()
                    is_verb_start = any(
                        lower_line.startswith(v) or f" {v} " in lower_line[:15]
                        for group in VERB_GROUPS.values() for v in group
                    )
                    if is_verb_start:
                        # Check if the previous question ended with a continuation word
                        prev_text = current_q["question_text"].strip().lower()
                        if not prev_text.endswith((" in", " and", " of", " the", " to", " with", " for", " by", " a", " an", " or")):
                            is_new_question_without_number = True

            if is_new_question_without_number:
                flush()
                marks = extract_marks(line) or current_section_marks
                blooms = extract_blooms(line)
                current_q = {
                    "question_no": "—",
                    "section_name": current_section.upper(),
                    "question_text": line,
                    "marks": marks,
                    "blooms_level": blooms,
                    "question_type": classify_question_type(marks),
                    "unit_no": current_unit_no,
                    "unit_title": current_unit_title,
                }
            else:
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
                        "section_name": current_section.upper(),
                        "question_text": line,
                        "marks": marks,
                        "blooms_level": blooms,
                        "question_type": classify_question_type(marks),
                        "unit_no": current_unit_no,
                        "unit_title": current_unit_title,
                    }

    flush()
    # Post-processing pass for validation and splitting missed merges
    questions = post_process_questions(questions)
    return questions


def extract_structured_bank_data(raw_text: str) -> Dict:
    """
    Full structured extraction for Question Banks, including metadata.
    """
    # 1. Extract metadata from first ~20 lines
    lines = raw_text.split('\n')[:25]
    meta = {
        "subject_name": None,
        "subject_code": None,
        "department": None,
        "regulation": None,
        "semester": None
    }
    
    for line in lines:
        for key, pattern in HEADER_PATTERNS.items():
            if meta[key] is None:
                m = pattern.search(line)
                if m:
                    meta[key] = m.group(1).strip().split('|')[0].strip() # Handle pipes

    # 2. Extract questions
    questions = parse_questions_from_text(raw_text)

    # 3. Organize into requested JSON format
    sections_map = {}
    for q in questions:
        sec = q.get("section_name", "GENERAL")
        if sec not in sections_map:
            sections_map[sec] = []
        
        # Clean up question for output
        q_out = {
            "question_no": q["question_no"],
            "question_text": q["question_text"],
            "marks": q["marks"],
            "blooms_level": q["blooms_level"],
            "question_type": q["question_type"],
            "unit_no": q["unit_no"]
        }
        sections_map[sec].append(q_out)

    sections_list = []
    # Preserve order of appearance if possible, but usually PART A then PART B
    for sec_name in sorted(sections_map.keys()):
        sections_list.append({
            "section_name": sec_name,
            "questions": sections_map[sec_name]
        })

    result = {**meta, "sections": sections_list}
    return result


# ─── OCR text cleanup helpers ─────────────────────────────────────────────────

# Patterns for fixing OCR word splits (e.g. "Di fferentiate" → "Differentiate")
OCR_SPLIT_FIXES = [
    (re.compile(r'\bDi fferentiate\b', re.I), 'Differentiate'),
    (re.compile(r'\bDiff erentiate\b', re.I), 'Differentiate'),
    (re.compile(r'\bW hy\b', re.I), 'Why'),
    (re.compile(r'\bWh y\b', re.I), 'Why'),
    (re.compile(r'\bWh at\b', re.I), 'What'),
    (re.compile(r'\bWh en\b', re.I), 'When'),
    (re.compile(r'\bLis t\b', re.I), 'List'),
    (re.compile(r'\bLi st\b', re.I), 'List'),
    (re.compile(r'\bHo w\b', re.I), 'How'),
    (re.compile(r'\bDef ine\b', re.I), 'Define'),
    (re.compile(r'\bboot strapping\b', re.I), 'bootstrapping'),
    (re.compile(r'\bhyper parameter\b', re.I), 'hyperparameter'),
    # Generic: single capital + space + lowercase (e.g. "E lucidate" → "Elucidate")
    (re.compile(r'\b([A-Z]) ([a-z]{3,})'), lambda m: m.group(1) + m.group(2)),
]

# Patterns to strip from question text (marks/bloom annotations that belong in metadata)
QTEXT_STRIP = [
    re.compile(r'\[\s*\d+\s*\]'),              # [2], [16]
    re.compile(r'\(\s*\d+\s*[Mm]arks?\s*\)'),  # (2 Marks)
    re.compile(r'\(\s*\d{1,2}\s*\)'),          # Generic (16), (2) anywhere
    re.compile(r'\b\d+\s*[Mm]arks?\b'),        # 2 marks
    re.compile(r'\(\s*(K[1-6]|BTL\s*\d)\s*\)', re.I),  # (K2), (BTL3)
    re.compile(r'\[\s*(K[1-6]|BTL\s*\d)\s*\]', re.I),  # [K2]
    re.compile(r'(?<!\w)(K[1-6])(?!\w)', re.I),          # standalone K2
    re.compile(r'\s+CO\s*\d\b'),               # CO1, CO2 at end
    re.compile(r'\s*[\(\[]\s*\d+\s*[\)\]]\s*[)\]]?\s*(?i:Or)?\s*$', re.I), # (13) ) Or
    re.compile(r'[,.]?\s*\(\s*\d+\s*\)\s*(?i:Or)?\s*$', re.I), # , (7) Or
    re.compile(r'\s+(?i:Or)\s*$', re.I),                      # standalone Or at end
    re.compile(r'^\s*(?i:Or)\s+', re.I),                      # standalone Or at start
    re.compile(r'\(\s*(?i:Or)\s*\)', re.I),                   # (OR) anywhere
    re.compile(r'(?i)Downloaded\s+from\s+EnggTree\.com', re.I),
    re.compile(r'(?i)EnggTree\.com', re.I),
    re.compile(r'(?i)EnggTree', re.I),
    re.compile(r'(?i)www\.[a-z0-9\.]+', re.I),
    re.compile(r'\b\d{5,12}\b'),               # Registration numbers like 20070...
    re.compile(r'^\s*\d{1,2}\s+(?=[A-Z])'),    # Stray marks (e.g. "13 ") at the start
    re.compile(r'\s+\d{1,2}\s*$'),             # Stray marks (e.g. " 13") at the end
    re.compile(r'\s*[|:.;:!]+\s*$'),           # Trailing noise symbols
    re.compile(r'\s+[|]\s*'),                  # Pipe symbols anywhere
]

# Academic Header phrases to skip
HEADER_PHRASES = [
    "B.E/B.Tech", "Degree Examinations", "Regulations 2021", 
    "Maximum : 100 marks", "Time : Three hours", "Answer ALL questions",
    "Department of", "Subject Code", "Subject Name", "Semester",
    "Internal Assessment"
]

# Bloom keyword mapping from User's "Perfect Prompt"
BLOOM_KEYWORDS = {
    "K1": ["list", "define", "state", "name", "give", "mention"],
    "K2": ["explain", "describe", "discuss", "differentiate", "compare", "distinguish", "illustrate", "what is", "relate"],
    "K3": ["apply", "solve", "compute", "construct", "analyze", "examine", "elucidate", "elaborate", "find", "calculate", "identify"]
}

# Question Verbs to validate "Real" questions
QUESTION_VERBS = [
    "define", "explain", "list", "compare", "differentiate", "discuss", "elaborate", 
    "compute", "find", "solve", "what is", "how does", "why", "give", "identify", 
    "mention", "examine", "elucidate", "construct", "analyze", "apply", "state", 
    "describe", "distinguish", "illustrate", "relate", "design", "write", "trace", 
    "summarize", "cluster", "classify", "predict", "calculate", "derive", "show", "evaluate"
]

# Junk single-word weather / numeric values that come from embedded data tables
JUNK_WORDS = {'Sunny', 'Overcast', 'Rain', 'Rainy', 'Hot', 'Mild', 'Cool',
               'High', 'Normal', 'Weak', 'Strong', 'Yes', 'No',
               'PASS', 'FAIL', 'Pass', 'Fail'}


def clean_question_text(text: str) -> str:
    """Remove marks/bloom annotations embedded in question text and fix OCR splits."""
    if not text:
        return text
    # Fix OCR word splits
    for pattern, repl in OCR_SPLIT_FIXES:
        if callable(repl):
            text = pattern.sub(repl, text)
        else:
            text = pattern.sub(repl, text)
            
    # Clean OCR bullet point artifacts
    text = re.sub(r'^\s*[@*°•\-–—]\s*', '', text)
    text = re.sub(r'\s+[@*°•\-–—]\s+', ' ', text)
    # Strip marks/bloom annotations
    for pattern in QTEXT_STRIP:
        text = pattern.sub('', text)

    # Remove marking artifacts like 13, 15, CO2, CO3, COs, etc.
    text = remove_marking_artifacts(text)

    # Remove leading question number prefixes (a), 1. (i) etc. and stray noise like }
    text = re.sub(r'^\s*[\)\].:,{}[\]@*#~]+\s*', '', text)
    text = re.sub(r'^\(\s*[ivx]+\s*\)\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^[ivx]+\s*[.)\s]\s*', '', text, flags=re.IGNORECASE)
    
    # Catch "13.", "13)", "13 (a)", "13", and even "(a)"
    text = re.sub(r'^\d{1,3}\s*[\.\):]?\s*(?:\(\s*[a-zA-Z]\s*\))?\s*', '', text)
    text = re.sub(r'^\(\s*[a-z]\s*\)\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^\(\s*\d{1,3}\s*\)\s*', '', text)
    text = re.sub(r'^[a-h]\s*[.)]\s*', '', text, flags=re.IGNORECASE)

    # Final cleanup of trailing punctuation and "Or"
    text = re.sub(r'[,.\s]+(?i:Or)\s*$', '', text)
    text = re.sub(r'\s*[\(\[]\s*\d+\s*[\)\]]\s*$', '', text)
    text = re.sub(r'([.?!])\s+\d{1,2}\s*$', r'\1', text)
    # Aggressively remove stray standalone digits at the very end
    text = re.sub(r'\s+\d{1,3}\s*[,.]?\s*$', '', text)
    
    # Remove trailing noise symbols
    text = re.sub(r'\s*[|:.;:!]+\s*$', '', text)
    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def is_junk_question(qno: str, qtext: str, marks, blooms) -> bool:
    """Return True for watermark noise, headers, or registration numbers."""
    text = qtext.strip()
    if not text: return True
    text_lower = text.lower()
    
    # 1. Skip if it contains "EnggTree" or other watermarks (anywhere in text)
    if any(p.search(text) for p in QTEXT_STRIP[7:10]): 
        if len(text) < 100: return True
        
    # 2. Skip if it's a Header Phrase (even if long)
    if any(phrase.lower() in text_lower for phrase in HEADER_PHRASES):
        # Unless it specifically contains a question number AND is relatively short, it's a header
        if not (qno and len(text) < 200):
            return True
        
    # 3. If it has a QNo or Marks/Blooms, it's very likely NOT junk, even if long
    if (qno and len(text) > 10) or (marks and len(text) > 15):
        return False

    # 4. Skip if it's too long (>150) but has NO question verbs (Typical for titles)
    if len(text) > 150 and not any(verb in text_lower for verb in QUESTION_VERBS):
        return True

    # 4. Registration number fields (Reg. No: ENGGTREE.COM)
    if "reg. no" in text_lower or "roll no" in text_lower:
        return True

    # NUCLEAR OPTION: If there are NO alphabetical letters in the text, it's JUNK.
    if not any(c.isalpha() for c in text) and len(text) < 20:
        return True

    # STRICT: If text is extremely short (e.g. just a number or artifact), it's JUNK
    if len(text) < 10:
        return True

    # If it has a QNo or Marks/Blooms, it's likely NOT junk
    if (qno or marks or blooms) and len(text) > 5:
        return False
        
    # Student IDs or standalone numbers
    if re.match(r'^\d{5,12}$', text): return True
    if text in JUNK_WORDS: return True
    
    try:
        float(text)
        return True
    except (ValueError, TypeError):
        pass
    if len(text) < 4: return True
    
    return False


def detect_qbank_columns(header_row: list) -> Optional[dict]:
    """
    Given a table header row, detect which column index maps to:
    qno, question, marks, blooms.
    Returns None if this doesn't look like a question bank table.
    """
    col_map = {}
    for i, cell in enumerate(header_row):
        if cell is None:
            continue
        cell_lower = str(cell).lower().strip()
        if any(k in cell_lower for k in ['q. no', 'q.no', 'q no', 'sl.', 's.no', 'sno', 'no.']):
            col_map['qno'] = i
        elif any(k in cell_lower for k in ['question', 'questions']):
            col_map['q'] = i
        elif any(k in cell_lower for k in ['marks', 'mark']):
            col_map['m'] = i
        elif any(k in cell_lower for k in ['blooms', 'bloom', 'btl', 'level']):
            col_map['bl'] = i
    
    # We need at least 'question' column to be a valid question bank table
    if 'q' in col_map:
        return col_map
    return None


async def extract_questions_from_pdf_tables(file_bytes: bytes) -> List[Dict]:
    """
    Handles the tabular question bank layout with all edge cases:
    - Header may embed section name: 'Questions\nPART A'
    - Wide tables (>4 cols) on some pages
    - Marks split across lines: '6\n7' = 13
    - Unit description rows appear before the real header
    """
    import pdfplumber

    questions = []
    current_unit_no = 0
    current_unit_title = None
    current_section = "GENERAL"
    current_section_marks: Optional[float] = None

    DATA_TABLE_KEYS = {"day", "outlook", "temperature", "s.no", "cgpa",
                       "assess", "humidity", "wind", "play tennis", "result"}

    def is_data_table(header_row):
        cells = {str(c or "").lower().strip() for c in header_row if c}
        return bool(DATA_TABLE_KEYS & cells)

    def find_header_row(table):
        for idx, row in enumerate(table):
            if not row:
                continue
            cells = [str(c or "").lower() for c in row]
            has_question = any("question" in c for c in cells)
            has_qno = any(k in c for c in cells for k in ["q. no", "q.no", "q no", "sl.", "no."])
            has_bloom = any(k in c for c in cells for k in ["knowl", "level", "bloom", "btl"])
            
            # If it has "question" and either "mark", "qno", or "bloom", it's likely a header
            if has_question and (any("mark" in c for c in cells) or has_qno or has_bloom):
                return idx, row
        return None, None

    def parse_marks(raw):
        nums = re.findall(r"\d+", str(raw or ""))
        if nums:
            total = sum(int(n) for n in nums)
            if 1 <= total <= 100:
                return float(total)
        return None

    def section_from_cell(cell_str):
        for line in cell_str.strip().split("\n"):
            if SECTION_PATTERNS.match(line.strip()):
                return line.strip().upper()
        return None

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        # Enhanced table settings to handle nested borders and boxes
        table_settings = {
            "vertical_strategy": "lines",
            "horizontal_strategy": "lines",
            "snap_tolerance": 6,
            "join_tolerance": 6,
            "text_x_tolerance": 3,
            "text_y_tolerance": 3,
        }

        logger.info(f"PHASE: START_TABLE_EXTRACTION - Pages: {len(pdf.pages)}")
        last_col_map = None

        for i, page in enumerate(pdf.pages):
            logger.info(f"PHASE: PROCESSING_PAGE - {i+1}/{len(pdf.pages)}")
            page_text = page.extract_text() or ""
            # Scan text for unit headers
            for line in page_text.split("\n"):
                um = UNIT_HEADER_PATTERN.match(line.strip())
                if um:
                    u_str = um.group(2)
                    try: current_unit_no = int(u_str) if u_str.isdigit() else roman_to_int(u_str)
                    except: pass
                    current_unit_title = um.group(3).strip()

            for table in (page.extract_tables(table_settings) or []):
                if not table or len(table) < 1:
                    continue
                if is_data_table(table[0]):
                    continue

                h_idx, h_row = find_header_row(table)
                
                # IMPORTANT: Process rows BEFORE the new header
                if h_idx is not None and h_idx > 0 and last_col_map:
                    # Even if column count changed slightly, try to map the most likely columns
                    qc_old = last_col_map.get("q", 1)
                    qnoc_old = last_col_map.get("qno", 0)
                    mc_old = last_col_map.get("m", len(table[0])-2 if len(table[0])>2 else None)
                    blc_old = last_col_map.get("bl", len(table[0])-1 if len(table[0])>1 else None)
                    
                    for row in table[:h_idx]:
                        # Process these orphan rows as continuations or new questions
                        self_qno = str(row[qnoc_old] or "").strip() if qnoc_old < len(row) else ""
                        self_qtext = str(row[qc_old] or "").strip() if qc_old < len(row) else ""
                        if self_qtext:
                            self_marks = parse_marks(str(row[mc_old] or "")) if mc_old and mc_old < len(row) else None
                            self_blooms = extract_blooms(str(row[blc_old] or "")) if blc_old and blc_old < len(row) else None
                            
                            # CRITICAL: Validate orphan rows against junk filter too!
                            if is_junk_question(self_qno, self_qtext, self_marks, self_blooms):
                                continue

                            self_qtext_start_qno = QUESTION_NO_PATTERNS.match(self_qtext.strip())
                            is_new_orphan = bool(self_qtext_start_qno)
                            if is_new_orphan:
                                questions.append({
                                    "question_no": self_qno if self_qno else (questions[-1].get("question_no") if questions else "?"),
                                    "section_name": current_section,
                                    "question_text": clean_question_text(self_qtext),
                                    "marks": self_marks or current_section_marks, 
                                    "blooms_level": self_blooms,
                                    "unit_no": current_unit_no, "unit_title": current_unit_title
                                })
                            elif questions:
                                questions[-1]["question_text"] += "\n" + clean_question_text(self_qtext)

                col = {}
                start_idx = 0
                if h_row is not None:
                    for i, cell in enumerate(h_row):
                        cl = str(cell or "").lower()
                        if "question" in cl:
                            col["q"] = i
                            # Check if the header cell itself contains section info
                            sec = section_from_cell(str(cell or ""))
                            if sec:
                                current_section = sec
                        elif any(k in cl for k in ["q. no", "q.no", "q no", "sl.", "no."]):
                            col["qno"] = i
                        elif "mark" in cl:
                            col["m"] = i
                        elif any(k in cl for k in ["knowl", "level", "bloom", "btl"]):
                            col["bl"] = i
                    
                    # Store col mapping for future orphan pages
                    last_col_map = col
                    start_idx = h_idx + 1
                elif last_col_map and len(table[0]) == last_col_map.get("nc", 0):
                    col = last_col_map
                else:
                    continue

                qc = col.get("q", 1)
                qnoc = col.get("qno", 0)
                mc = col.get("m")
                blc = col.get("bl")

                for row in table[start_idx:]:
                    if not row:
                        continue
                    
                    sg = lambda i: str(row[i] or "").strip() if i is not None and i < len(row) else ""
                    qno = sg(qnoc)
                    qtext = sg(qc)
                    
                    if not qtext:
                        continue

                    lines = qtext.split('\n')
                    if SECTION_PATTERNS.match(lines[0].strip()):
                        current_section = lines[0].strip().upper()
                        qtext = '\n'.join(lines[1:]).strip()
                        if not qtext:
                            continue

                    marks = parse_marks(sg(mc)) if mc else extract_marks(qtext)
                    blooms = extract_blooms(sg(blc)) if blc else extract_blooms(qtext)

                    if is_junk_question(qno, qtext, marks, blooms):
                        if questions and len(qtext) > 0:
                            questions[-1]["question_text"] += "\n" + qtext
                        continue

                    if not qno and len(qtext) > 200 and not marks:
                        continue

                    is_new_orphan = bool(re.match(r'^\d{1,3}[\.\)]?.*$', qno))
                    is_new = is_new_orphan or (not qno and len(qtext) > 10 and (marks or blooms))

                    if not is_new and len(qtext) < 5:
                        if questions:
                            questions[-1]["question_text"] += "\n" + qtext
                        continue

                    clean = clean_question_text(qtext)
                    if not clean and not marks:
                        continue

                    if is_new:
                        questions.append({
                            "question_no": qno,
                            "section_name": current_section,
                            "question_text": clean,
                            "marks": marks,
                            "blooms_level": blooms,
                            "question_type": classify_question_type(marks),
                            "unit_no": current_unit_no,
                            "unit_title": current_unit_title
                        })
                    elif questions:
                        questions[-1]["question_text"] += "\n" + clean
                        if marks and not questions[-1].get("marks"):
                            questions[-1]["marks"] = marks
                        if blooms and not questions[-1].get("blooms_level"):
                            questions[-1]["blooms_level"] = blooms

    for q in questions:
        q["question_text"] = clean_question_text(q["question_text"])
        if not q.get("marks"):
            q["marks"] = extract_marks(q["question_text"])
        if not q.get("blooms_level"):
            q["blooms_level"] = extract_blooms(q["question_text"])
        q["question_type"] = classify_question_type(q["marks"])

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
        
        # Aggressive Fallback: if total text is suspiciously short (e.g. < 500 chars), 
        # it's likely a scanned document where some pages had tiny "garbage" text layers (like watermarks)
        if len(result.strip()) < 500 and len(pdf.pages) > 0:
            logger.info(f"Total text too short ({len(result)} chars) — forcing Full OCR Scan")
            text_parts = []
            for page in pdf.pages:
                try:
                    img = page.to_image(resolution=300).original
                    ocr_text = await _ocr_pil_image(img)
                    if ocr_text:
                        text_parts.append(ocr_text)
                except Exception as ocr_err:
                    logger.warning(f"Forced Page OCR failed: {ocr_err}")
            result = "\n".join(text_parts)

        logger.info(f"PDF extraction final: {len(result)} chars from {len(pdf.pages)} pages")
        return result
    except Exception as e:
        logger.error(f"PDF text extraction error: {e}")
        return ""


async def _ocr_pil_image(pil_img) -> str:
    """OCR a PIL image object."""
    try:
        import pytesseract
        import os
        # Check if tesseract is in PATH, if not, try default Windows location
        tess_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        if not os.path.exists(pytesseract.pytesseract.tesseract_cmd) and os.path.exists(tess_path):
            pytesseract.pytesseract.tesseract_cmd = tess_path
            
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
        # 1. Try table-aware extraction (good for tabular Part B/C and Question Banks)
        table_questions = await extract_questions_from_pdf_tables(file_bytes)
        
        # 2. Get full text and parse via regex (good for non-tabular Part A)
        raw_text = await extract_text_from_pdf(file_bytes)
        text_questions = parse_questions_from_text(raw_text)
        
        if not table_questions:
            return raw_text, text_questions
            
        if not text_questions:
            return raw_text, table_questions

        # 3. SMART MERGE: Combine both while avoiding duplicates.
        # We prioritize table_questions for metadata (marks/blooms) 
        # but use text_questions to fill in gaps (like Part A).
        final_questions = table_questions[:]
        
        # Build a set of normalized texts for existing questions to detect duplicates
        seen_texts = {normalize_question(q["question_text"]) for q in final_questions}
        seen_nos = {str(q["question_no"]).strip('.') for q in final_questions if q.get("question_no")}

        for tq in text_questions:
            norm = normalize_question(tq["question_text"])
            qno = str(tq["question_no"]).strip('.')
            
            # If this question number or text is not in our table list, add it!
            if norm not in seen_texts and qno not in seen_nos:
                # Add to the beginning if it has a lower question number than our first table question
                if final_questions and qno.isdigit() and str(final_questions[0].get("question_no", "")).strip('.').isdigit():
                    if int(qno) < int(str(final_questions[0]["question_no"]).strip('.')):
                        final_questions.insert(0, tq)
                    else:
                        final_questions.append(tq)
                else:
                    final_questions.append(tq)
                
                seen_texts.add(norm)
                if qno: seen_nos.add(qno)

        # Sort by question number if possible
        def sort_key(q):
            no = str(q.get("question_no", "999")).strip('.')
            # Handle 11(a) -> 11.1
            m = re.match(r'^(\d+)', no)
            if m:
                base = int(m.group(1))
                sub = 0
                if '(' in no:
                    sub_char = re.search(r'\(([a-z])\)', no)
                    if sub_char: sub = ord(sub_char.group(1)) - ord('a') + 1
                return base + (sub / 100.0)
            return 999.0

        final_questions.sort(key=sort_key)
        return raw_text, final_questions
    elif filename_lower.endswith((".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp")):
        raw_text = await extract_text_from_image(file_bytes)
    elif filename_lower.endswith(".txt"):
        raw_text = file_bytes.decode("utf-8", errors="ignore")
    else:
        raw_text = file_bytes.decode("utf-8", errors="ignore")

    if not raw_text.strip():
        logger.warning(f"No text extracted from {filename}")
        return "", []

    raw_text = preprocess_raw_text(raw_text)
    logger.info("PHASE: STRUCTURING_QUESTIONS")
    questions = parse_questions_from_text(raw_text)
    logger.info(f"PHASE: EXTRACTION_COMPLETE - Parsed {len(questions)} questions")
    return raw_text, questions


def format_question_bank_to_text(data: Dict) -> str:
    """
    Formats structured question bank data into the pretty text format
    seen in sample_question_bank.txt.
    """
    lines = []
    lines.append("=" * 80)
    lines.append(f"{'QUESTION BANK — ' + (data.get('subject_name', 'SUBJECT')).upper():^80}")
    
    code = data.get('subject_code', 'CODE')
    sem = data.get('semester', 'III')
    reg = data.get('regulation', 'R2021')
    meta_line = f"Subject Code: {code}  |  Semester: {sem}  |  Reg: {reg}"
    lines.append(f"{meta_line:^80}")
    lines.append("=" * 80)
    lines.append("")

    for section in data.get("sections", []):
        # Check if this is a Unit start or just a section
        sec_name = section.get("section_name", "GENERAL").upper()
        lines.append(f"{sec_name:^80}")
        lines.append("")
        
        for q in section.get("questions", []):
            qno = q.get("question_no", "")
            qtext = q.get("question_text", "")
            marks = q.get("marks", "")
            blooms = q.get("blooms_level", "")
            
            # Format: 1. Question text [Marks] Bloom
            metadata = ""
            if marks: metadata += f" [{int(marks) if float(marks).is_integer() else marks}]"
            if blooms: metadata += f" {blooms}"
            
            lines.append(f"{qno} {qtext}{metadata}")
        
        lines.append("")
        lines.append("-" * 40)
        lines.append("")

    return "\n".join(lines)
