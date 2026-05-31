import re
import sys

def test_regexes():
    # Define the regexes as they are in ocr_pipeline.py
    BLOOMS_PATTERNS = {
        "K1": r'\b(K1|BTL[-\s]?1|L1|BL[-\s]?1|CO[-\s]?1|Remember|Define|State|List|Identify|Recall|Name|Label|Match|Write)\b',
        "K2": r'\b(K2|BTL[-\s]?2|L2|BL[-\s]?2|CO[-\s]?2|Understand|Explain|Describe|Summarize|Discuss|Interpret|Classify|Illustrate)\b',
        "K3": r'\b(K3|BTL[-\s]?3|L3|BL[-\s]?3|CO[-\s]?3|Apply|Solve|Demonstrate|Use|Compute|Calculate|Implement|Show)\b',
        "K4": r'\b(K4|BTL[-\s]?4|L4|BL[-\s]?4|CO[-\s]?4|Analyze|Compare|Differentiate|Examine|Break\s+down|Categorize|Contrast)\b',
        "K5": r'\b(K5|BTL[-\s]?5|L5|BL[-\s]?5|CO[-\s]?5|Evaluate|Justify|Assess|Judge|Critique|Recommend)\b',
        "K6": r'\b(K6|BTL[-\s]?6|L6|BL[-\s]?6|CO[-\s]?6|Create|Design|Develop|Formulate|Construct|Plan|Produce|Draw)\b',
    }

    MARKS_PATTERNS = [
        r'\[\s*(\d+)\s*\]',
        r'\(\s*(\d+)\s*[Mm]arks?\s*\)',
        r'\b(\d+)\s*[Mm]arks?\b',
        r'\(\s*(\d+)\s*\)\s*$',
        r'\b(\d+)\s*[Mm]\b',
        r'[,.\s]+(\d{1,2})\s*$',
        r'(?<=\d\.\s)(\d+)(?=\s+K[1-6])',
        r'\s+(\d+)\s+K[1-6]\s*$',
        r'^\s*(\d+)\s*$',
    ]

    SECTION_PATTERNS = r'^\s*(PART|SECTION|Section|Part)\s*[-–—\s]*([A-Za-z0-9]+)'

    QUESTION_NO_PATTERNS = (
        r'^('
        r'\(\s*[ivxIVX]+\s*\)'
        r'|[ivxIVX]+\s*[.),]'
        r'|\(\s*[a-zA-Z]\s*\)'
        r'|Q\s*\.?\s*No\s*\.?\s*\d+'
        r'|Q\s*\.?\s*\d+\s*[\-.:),–]?'
        r'|\d{1,2}\s*\(\s*[a-z]\s*\)'
        r'|\d{1,3}\s*[.):,]\s*'
        r'|\(\s*\d{1,3}\s*\)'
        r'|[a-hA-H]\s*[.),]\s*'
        r')'
    )

    INLINE_Q_START_PATTERN = (
        r'(?:^|[\.?!,\]\)])\s*('
        r'\d{1,2}\s*[.):,]\s+[A-Z]'
        r'|\(\s*[a-z]\s*\)\s+[A-Z]'
        r'|Q\s*\.?\s*\d+\s*[.):,]\s+[A-Z]'
        r')'
    )

    OCR_INLINE_QNO_VERBS = [
        "what is", "how does", "why", "define", "explain", "list", "compare",
        "differentiate", "discuss", "elaborate", "compute", "find", "solve",
        "give", "identify", "mention", "examine", "elucidate", "construct",
        "analyze", "analyse", "apply", "state", "describe", "distinguish",
        "illustrate", "relate", "write", "design"
    ]
    OCR_INLINE_QNO_PATTERN = (
        r'^\s*(\d{1,2})\s*[,.:]?\s+(?=(?:'
        + "|".join(re.escape(verb) for verb in sorted(OCR_INLINE_QNO_VERBS, key=len, reverse=True))
        + r')\b)'
    )

    STANDALONE_OR_PATTERN = r'^[\s\)\],.;:-]*or[\s,.;:()\-]*$'
    STANDALONE_MARKS_LINE = r'^\s*[\(\[]\s*(\d+)\s*[\)\]]\s*$'
    STANDALONE_BLOOM_LINE = r'^\s*(K[1-6])\s*$'

    NOISE_PATTERNS = (
        r'^\s*('
        r'Reg\.?\s*(No|Number)?\.?'
        r'|Roll\s*(No|Number)?\.?'
        r'|Answer\s+(ALL|any|all)'
        r'|Maximum\s+Marks?'
        r'|Time\s*[:–]\s*\d'
        r'|Duration\s*[:–]'
        r'|Hall\s*Ticket'
        r'|Question\s+Paper'
        r'|UNIVERSITY\s+EXAM'
        r'|Semester\s+Exam'
        r'|Course\s+(Code|Name)'
        r'|END\s+OF\s+QUESTION'
        r'|Downloaded\s+from'
        r'|(?:Engg|Enggl)Tree(?:\.com)?'
        r'|Signature\s+of\s+the\s+(staff|HoD)'
        r'|^\s*\d{1,3}\s*$'
        r'|\d{1,2}\s+\d{4,}\s*$'
        r'|[-_=]{5,}'
        r'|\*{3,}'
        r')'
    )

    HEADER_PATTERNS = {
        "subject_name": r'(?:Subject|Course|QUESTION BANK)(?:\s+Name)?\s*[:–—\-]\s*([A-Z\s\-–—]+?)(?=\s+(?:Course Code|Class|Semester|Department)|$)',
        "subject_code": r'(?:Subject|Course)?\s*Code\s*[:–-]\s*([A-Z0-9]+)',
        "department": r'Department\s+of\s+(.*?)(?=\s+(?:Course|Semester|Regulation)|$)',
        "regulation": r'(?:Reg|Regulation)\s*[:–-]?\s*(R\d{4}|\d{4})',
        "semester": r'Semester\s*[:–-]?\s*([IVX]+|\d+)',
    }

    UNIT_HEADER_PATTERN = r'^\s*(UNIT|Unit)\s*([IVX]+|\d+)\s*[-–—:]?\s*(.*)'

    INLINE_BLOOM_TAG = r'[\(\[]\s*(K[1-6]|BTL\s*\d)\s*[\)\]]|(?<!\w)(K[1-6])(?!\w)'
    INLINE_CO_TAG    = r'[\(\[]\s*CO\s*\d\s*[\)\]]'
    INLINE_MARKS_TAG = r'[\(\[]\s*(\d+)\s*[\)\]]'
    INLINE_MARKS_END = r'[\(\[]\s*(\d+)\s*[\)\]]\s*$'

    regexes = {
        "BLOOMS_PATTERNS": BLOOMS_PATTERNS,
        "MARKS_PATTERNS": MARKS_PATTERNS,
        "SECTION_PATTERNS": SECTION_PATTERNS,
        "QUESTION_NO_PATTERNS": QUESTION_NO_PATTERNS,
        "INLINE_Q_START_PATTERN": INLINE_Q_START_PATTERN,
        "OCR_INLINE_QNO_PATTERN": OCR_INLINE_QNO_PATTERN,
        "STANDALONE_OR_PATTERN": STANDALONE_OR_PATTERN,
        "STANDALONE_MARKS_LINE": STANDALONE_MARKS_LINE,
        "STANDALONE_BLOOM_LINE": STANDALONE_BLOOM_LINE,
        "NOISE_PATTERNS": NOISE_PATTERNS,
        "HEADER_PATTERNS": HEADER_PATTERNS,
        "UNIT_HEADER_PATTERN": UNIT_HEADER_PATTERN,
        "INLINE_BLOOM_TAG": INLINE_BLOOM_TAG,
        "INLINE_CO_TAG": INLINE_CO_TAG,
        "INLINE_MARKS_TAG": INLINE_MARKS_TAG,
        "INLINE_MARKS_END": INLINE_MARKS_END,
    }

    for name, r in regexes.items():
        try:
            if isinstance(r, dict):
                for k, v in r.items():
                    print(f"Testing {name}[{k}]...")
                    re.compile(v, re.IGNORECASE)
            elif isinstance(r, list):
                for i, v in enumerate(r):
                    print(f"Testing {name}[{i}]...")
                    re.compile(v, re.IGNORECASE)
            else:
                print(f"Testing {name}...")
                re.compile(r, re.IGNORECASE)
        except Exception as e:
            print(f"FAILED: {name} - {e}")
            # print position if possible
            if hasattr(e, 'pos'):
                print(f"Position: {e.pos}")
            if hasattr(e, 'pattern'):
                # print the character at position
                if e.pos is not None and e.pos < len(e.pattern):
                    print(f"Char at pos {e.pos}: '{e.pattern[e.pos]}'")
                    # print hex of char
                    print(f"Hex of char at pos {e.pos}: {hex(ord(e.pattern[e.pos]))}")

if __name__ == "__main__":
    test_regexes()
