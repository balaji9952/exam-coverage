import os
import json
import logging
import google.generativeai as genai
from typing import List, Dict

logger = logging.getLogger(__name__)

# The "Perfect Prompt" provided by the user, adapted for JSON output
SYSTEM_PROMPT = """
You are an advanced OCR and question paper extraction system.
Extract all questions from the uploaded text accurately.

CRITICAL TABULAR LAYOUT FRAMEWORK RULES:
The uploaded document is often a full question bank with a complex tabular layout (containing headers, subject codes, etc., and columns like "Q. No.", "Questions", "Marks", "Knowledge Level").
When you analyze this full layout, your extracted "question" field MUST perfectly isolate and extract ONLY the text found inside the "Questions" column. 
- DO NOT include the "Q. No." in the "question" field.
- DO NOT include the "Marks" in the "question" field.
- DO NOT include the "Knowledge Level" (e.g., K1, K2) or "CO" (e.g., CO1, CO2) in the "question" field.
The extracted "question" string should look exactly as if you cropped just the "Questions" column from the table and read the text.

IMPORTANT EXTRACTION RULES:
1. A question may continue in the next line, next row, next table section, or even below a page break.
2. If a sentence is incomplete, continue reading the next visible text until the sentence meaning is fully completed.
3. DO NOT split one question into multiple questions unless a new question number starts.
4. A new question starts ONLY when a new serial number appears (1., 2., 3., etc.) or a new question identifier clearly starts in the "Q. No." column.
5. Ignore table breaks, page gaps, borders, and spacing issues.
6. Merge wrapped lines in the "Questions" column into a single complete question string.
7. Preserve full question meaning.
8. If text appears below the table continuation area, attach it to the previous incomplete question.
9. Extract only the exam question text. Ignore and do not include any Bloom's taxonomy labels or codes (K1-K6, KI) or Course Outcomes (CO1-CO6) in the question text. Return only the clean question text.
10. CRITICAL: DO NOT extract university headers, degree names, semester details, subject codes, subject names, regulations, instructions, or maximum marks as questions. Skip them entirely.

OUTPUT FORMAT:
Return ONLY a valid JSON array of objects with the following keys:
- q_no: The question number string (e.g. "1", "2(a)") extracted from the Q.No column.
- question: The FULL merged question text strictly from the "Questions" column.
- marks: The numeric marks (e.g. 13)
- bloom: The Bloom's Level (K1-K6)
- section: The section name (e.g. "PART A", "PART B")

Example of Correct Extraction:
[
  {
    "q_no": "1",
    "question": "Analyze the key elements of a Digital Marketing Strategy and examine how each element contributes to achieving business objectives.",
    "marks": 13,
    "bloom": "K4",
    "section": "PART B"
  }
]

Do not include any conversational text or markdown blocks.
"""

import re

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


def clean_ai_question_text(text: str) -> str:
    """Helper to strip marks and noise from AI-extracted question text as a fallback."""
    if not text:
        return text
    
    # 1. Strip marks in parentheses or brackets: (16), [2], (2 Marks), [13 marks] anywhere
    text = re.sub(r'[\(\[]\s*\d+\s*(?:marks?|m)?\s*[\)\]]', ' ', text, flags=re.IGNORECASE)
    
    # 2. Strip standalone marks patterns: "16 marks", "2M"
    text = re.sub(r'\b\d+\s*marks?\b', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'\b\d+M\b', ' ', text)
    
    # Remove marking artifacts like 13, 15, CO2, CO3, COs, etc.
    text = remove_marking_artifacts(text)
    
    # 3. Remove leading artifacts like ") ", ". ", "1) ", "(a) ", "}", "*", etc.
    text = re.sub(r'^\s*[\)\].:,{}[\]@*#~]+\s*', '', text)
    
    # 4. Strip trailing noise symbols: |, :, .: , .; , etc.
    text = re.sub(r'\s*[|:.;:!,]+\s*$', '', text)
    text = re.sub(r'\s*[|]\s*', ' ', text) # Remove pipe symbols anywhere
    
    # 5. Remove Bloom taxonomy markers that AI might have included (e.g., ", K1", ", KI")
    text = re.sub(r'[,.\s]*\b(K[1-6I]|BTL\s*\d)\b', '', text, flags=re.IGNORECASE)
    
    # User's requested rule to strictly remove trailing Bloom tags
    text = re.sub(r'[,.\s]*K[1-6I]\s*$', '', text, flags=re.IGNORECASE)
    
    # 6. Remove stray numbers at the end (often marks that missed parentheses)
    text = re.sub(r'\s+\d{1,2}\s*$', '', text)
    
    # 7. Final cleanup of trailing commas and punctuation
    text = re.sub(r'[,.\s]+$', '', text)
    
    # 6. Final cleanup: normalize spaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Remove trailing periods if they are redundant
    if text.endswith('.') and not text.endswith('?.'):
        text = text.rstrip('.')
    
    return text.strip()


def extract_questions_with_ai(raw_text: str) -> List[Dict]:
    """
    Use Google Gemini to extract questions from OCR text using the Perfect Prompt.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.warning("GOOGLE_API_KEY not found in environment. Falling back to local OCR parser.")
        return []

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Use a higher temperature for reasoning, but keep it low for structure
        prompt = f"{SYSTEM_PROMPT}\n\nExtract all questions from the following exam paper text:\n\n{raw_text}"
        
        response = model.generate_content(prompt)
        content = response.text.strip()
        
        # Clean up possible markdown artifacts if Gemini ignored the "No markdown" instruction
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        elif content.startswith("```"):
            content = content.replace("```", "").strip()
        
        # Handle cases where Gemini adds conversational text before/after JSON
        if "[" in content and "]" in content:
            start = content.find("[")
            end = content.rfind("]") + 1
            content = content[start:end]
            
        questions = json.loads(content)
        
        # Re-map fields to internal format
        final_questions = []
        for i, q in enumerate(questions):
            # Ensure question is not empty
            raw_question = q.get("question", "")
            if not raw_question:
                continue
                
            # Post-process cleaning to remove marks and noise artifacts
            cleaned_question = clean_ai_question_text(raw_question)
            
            if not cleaned_question:
                continue
            
            # Explicitly filter out headers/junk if Gemini ignored the prompt
            from ocr_pipeline import is_junk_question
            if is_junk_question(str(q.get("q_no", "")), cleaned_question, q.get("marks"), q.get("bloom")):
                logger.info(f"Filtered out junk AI question: {cleaned_question[:50]}...")
                continue

            final_questions.append({
                "question_no": str(q.get("q_no", i+1)),
                "question_text": cleaned_question,
                "marks": q.get("marks"),
                "blooms_level": q.get("bloom"),
                "section_name": q.get("section", "EXTRACTED"),
                "question_type": "descriptive" if (q.get("marks") or 0) > 2 else "short"
            })
            
        return final_questions

        
    except Exception as e:
        logger.error(f"Gemini extraction failed: {e}", exc_info=True)
        return []
