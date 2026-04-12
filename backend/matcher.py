"""
Semantic Matching Engine using sentence-transformers
"""

import json
import numpy as np
from typing import List, Optional, Dict, Tuple
import logging

logger = logging.getLogger(__name__)

# Lazy-load model to avoid startup delay
_model = None

MATCH_THRESHOLD = 0.72       # Above this → "matched"
POSSIBLE_THRESHOLD = 0.50    # Between this and MATCH_THRESHOLD → "possible match"

def get_model():
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading sentence transformer model...")
            _model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load sentence transformer: {e}")
            _model = None
    return _model


def encode_text(text: str) -> Optional[List[float]]:
    """Return embedding as a Python float list"""
    model = get_model()
    if model is None:
        return None
    try:
        embedding = model.encode(text, normalize_embeddings=True)
        return embedding.tolist()
    except Exception as e:
        logger.error(f"Encoding error: {e}")
        return None


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    a = np.array(vec_a)
    b = np.array(vec_b)
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def classify_match(score: float) -> str:
    if score >= MATCH_THRESHOLD:
        return "matched"
    elif score >= POSSIBLE_THRESHOLD:
        return "possible"
    return "not_matched"


def embedding_to_json(embedding: List[float]) -> str:
    return json.dumps(embedding)


def json_to_embedding(json_str: str) -> Optional[List[float]]:
    try:
        return json.loads(json_str)
    except Exception:
        return None


def match_exam_to_bank(
    exam_text: str,
    exam_embedding: Optional[List[float]],
    bank_questions: List[Dict]
) -> Tuple[Optional[Dict], float, str]:
    """
    Compare one exam question against all bank questions.
    Returns: (best_bank_question or None, best_score, match_status)
    """
    if not bank_questions:
        return None, 0.0, "not_matched"

    if exam_embedding is None:
        exam_embedding = encode_text(exam_text)
    if exam_embedding is None:
        return None, 0.0, "not_matched"

    best_score = -1.0
    best_q = None

    for bq in bank_questions:
        bank_emb = None
        if bq.get("embedding"):
            bank_emb = json_to_embedding(bq["embedding"])
        if bank_emb is None:
            bank_emb = encode_text(bq.get("normalized_text") or bq.get("question_text", ""))
        if bank_emb is None:
            continue

        score = cosine_similarity(exam_embedding, bank_emb)
        if score > best_score:
            best_score = score
            best_q = bq

    match_status = classify_match(best_score)
    return best_q, best_score, match_status


def compute_coverage_report(
    exam_questions: List[Dict],
    bank_questions: List[Dict],
    match_results: List[Dict]
) -> Dict:
    """
    Compute coverage percentages:
    - Overall coverage
    - Unit-wise coverage
    - Bloom's level coverage
    - Marks-weighted coverage
    """
    report = {
        "total_exam_questions": len(exam_questions),
        "total_bank_questions": len(bank_questions),
        "matched": 0,
        "possible": 0,
        "not_matched": 0,
        "overall_coverage_pct": 0.0,
        "weighted_coverage_pct": 0.0,
        "unit_coverage": {},
        "blooms_coverage": {
            "K1": {"exam": 0, "matched": 0, "pct": 0.0},
            "K2": {"exam": 0, "matched": 0, "pct": 0.0},
            "K3": {"exam": 0, "matched": 0, "pct": 0.0},
            "K4": {"exam": 0, "matched": 0, "pct": 0.0},
            "K5": {"exam": 0, "matched": 0, "pct": 0.0},
            "K6": {"exam": 0, "matched": 0, "pct": 0.0},
        },
        "unmatched_exam_questions": [],
        "uncovered_bank_topics": [],
    }

    # Count match statuses
    matched_bank_ids = set()
    for mr in match_results:
        status = mr.get("match_status", "not_matched")
        if status == "matched":
            report["matched"] += 1
            if mr.get("bank_question_id"):
                matched_bank_ids.add(mr["bank_question_id"])
        elif status == "possible":
            report["possible"] += 1
        else:
            report["not_matched"] += 1
            report["unmatched_exam_questions"].append(mr.get("exam_question_text", ""))

    # Overall coverage (count-based)
    if len(exam_questions) > 0:
        report["overall_coverage_pct"] = round(
            (report["matched"] / len(exam_questions)) * 100, 2
        )

    # Marks-weighted coverage
    total_exam_marks = sum(q.get("marks") or 0 for q in exam_questions)
    matched_marks = 0.0
    matched_exam_ids = {mr["exam_question_id"] for mr in match_results if mr.get("match_status") == "matched"}
    for q in exam_questions:
        if q.get("id") in matched_exam_ids:
            matched_marks += q.get("marks") or 0
    if total_exam_marks > 0:
        report["weighted_coverage_pct"] = round((matched_marks / total_exam_marks) * 100, 2)

    # Unit-wise coverage (based on bank questions touched)
    unit_bank_map: Dict[str, set] = {}
    for bq in bank_questions:
        unit_key = f"Unit {bq.get('unit_no', '?')} - {bq.get('unit_title', 'Unknown')}"
        unit_bank_map.setdefault(unit_key, set())
        unit_bank_map[unit_key].add(bq["id"])

    for unit_key, bank_ids in unit_bank_map.items():
        covered = matched_bank_ids & bank_ids
        pct = round(len(covered) / len(bank_ids) * 100, 2) if bank_ids else 0.0
        report["unit_coverage"][unit_key] = {
            "total": len(bank_ids),
            "covered": len(covered),
            "pct": pct
        }
        if len(covered) < len(bank_ids):
            uncovered_ids = bank_ids - matched_bank_ids
            report["uncovered_bank_topics"].append({
                "unit": unit_key,
                "uncovered_count": len(uncovered_ids)
            })

    # Bloom's level distribution
    for eq in exam_questions:
        bl = eq.get("blooms_level") or "Unknown"
        if bl in report["blooms_coverage"]:
            report["blooms_coverage"][bl]["exam"] += 1

    for mr in match_results:
        if mr.get("match_status") == "matched":
            bl = mr.get("blooms_level") or "Unknown"
            if bl in report["blooms_coverage"]:
                report["blooms_coverage"][bl]["matched"] += 1

    for bl, data in report["blooms_coverage"].items():
        if data["exam"] > 0:
            data["pct"] = round(data["matched"] / data["exam"] * 100, 2)

    return report
