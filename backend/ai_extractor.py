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

IMPORTANT EXTRACTION RULES:
1. A question may continue in the next line, next row, next table section, or even below a page break.
2. If a sentence is incomplete, continue reading the next visible text until the sentence meaning is fully completed.
3. DO NOT split one question into multiple questions unless a new question number starts.
4. A new question starts ONLY when:
   - A new serial number appears (1., 2., 3., etc.)
   - OR a new question identifier clearly starts.
5. Ignore table breaks, page gaps, borders, and spacing issues.
6. Merge wrapped lines into a single complete question.
7. Preserve full question meaning.
8. If text appears below the table continuation area, attach it to the previous incomplete question.
9. Extract only the exam question text. Ignore and do not include any Bloom's taxonomy labels or codes such as K1, K2, K3, KI, or any similar alphanumeric tags that appear alongside the questions. Return only the clean question text without any trailing codes, labels, or punctuation artifacts associated with those tags.
10. CRITICAL: DO NOT extract university headers, degree names (e.g., B.E., B.Tech, DEGREE EXAMINATIONS), semester details, subject codes, subject names, regulations, instructions, or maximum marks as questions. Skip them entirely.

OUTPUT FORMAT:
Return ONLY a valid JSON array of objects with the following keys:
- q_no: The question number string (e.g. "3")
- question: The FULL merged question text.
- marks: The numeric marks (e.g. 13)
- bloom: The Bloom's Level (K1-K6)
- section: The section name (e.g. "PART A")

Example of Correct Extraction:
[
  {
    "q_no": "3",
    "question": "Analyze the various opportunities and stages involved in developing a Brand Website and examine their significance in brand building",
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
