"""
Semantic Matching Engine using sentence-transformers
"""

import json
import re
import numpy as np
from typing import List, Optional, Dict, Tuple
import logging

logger = logging.getLogger(__name__)

# Lazy-load model to avoid startup delay
_model = None

MATCH_THRESHOLD = 0.75       # Above this → "matched"
POSSIBLE_THRESHOLD = 0.45    # Between this and MATCH_THRESHOLD → "possible match"

# --- Intent-Aware Matching Configuration ---

INTENT_MAP = {
    "definition": ["define", "what is", "what are", "meaning of", "explain the term", "explain what", "state ", "write ", "give the ", "what do you mean"],
    "types_list": ["types", "list", "classify", "categorise", "categories", "components", "parts of", "different kinds"],
    "applications": ["applications", "uses", "where is it used", "utility", "practical uses", "industrial applications"],
    "methods_prep": ["preparation", "methods of", "synthesis", "how to prepare", "how is it made", "manufacturing", "production process", "methods of preparation", "how "],
    "advantages_importance": ["advantages", "importance", "benefits", "significance", "merits", "pros", "positive aspects"],
    "derivation_proof": ["derive", "derivation", "proof", "show that", "deduction", "mathematical expression for", "derive an expression", "obtain an expression"],
    "comparison_diff": ["compare", "difference", "distinguish", "versus", "vs", "differentiation between", "contrast"],
    "factors": ["factors affecting", "factors influencing", "what factors", "depend on", "dependence of"],
    "diagram_explain": ["diagram", "draw", "sketch", "label", "circuit", "schematic", "explain with diagram"],
    "numerical": ["calculate", "numerical", "solve", "compute", "find the value", "determine the value", "estimation"],
}

COMMON_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "else", "when",
    "at", "from", "by", "for", "with", "about", "against", "between",
    "into", "through", "during", "before", "after", "above", "below",
    "to", "from", "up", "down", "in", "out", "on", "off", "over", "under",
    "again", "further", "then", "once", "here", "there", "when", "where",
    "why", "how", "all", "any", "both", "each", "few", "more", "most",
    "other", "some", "such", "no", "nor", "not", "only", "own", "same",
    "so", "than", "too", "very", "can", "will", "just", "should", "now", 
    "of", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "having", "do", "does", "did", "doing",
    "various", "different", "multiple", "several", "kind", "kinds"
}

# Intents that are somewhat related and shouldn't be penalized heavily
INTENT_COMPATIBILITY = {
    "definition": {"derivation_proof", "diagram_explain", "factors"},
    "derivation_proof": {"definition", "numerical"},
    "diagram_explain": {"definition", "methods_prep"},
    "types_list": {"applications"}, # Sometimes types and applications overlap in lists
}

ACTION_WORDS = [
    "define", "explain", "derive", "compare", "list", "classify", 
    "applications", "advantages", "preparation", "methods", 
    "factors", "importance", "diagram", "types", "write", "state", "how", "show", "prove"
]

def extract_intent(text: str) -> str:
    """Categorize question intent based on keywords."""
    text_lower = text.lower()
    for intent, keywords in INTENT_MAP.items():
        for kw in keywords:
            if kw in text_lower:
                return intent
    return "general"

def extract_action_words(text: str) -> set:
    """Extract key action verbs for weighting."""
    text_lower = text.lower()
    return {word for word in ACTION_WORDS if word in text_lower}

def extract_technical_keywords(text: str) -> set:
    """Extract significant technical terms, ignoring stopwords and intent words."""
    words = re.findall(r'\b\w+\b', text.lower())
    return {
        w for w in words 
        if w not in COMMON_STOPWORDS 
        and w not in ACTION_WORDS 
        and len(w) > 2
    }

def calculate_refined_score(
    semantic_score: float, 
    exam_text: str, 
    bank_text: str,
    exam_intent: Optional[str] = None,
    bank_intent: Optional[str] = None
) -> float:
    """
    Adjust semantic similarity based on intent and action word matching.
    """
    if exam_intent is None:
        exam_intent = extract_intent(exam_text)
    if bank_intent is None:
        bank_intent = extract_intent(bank_text)
    
    # Intent Matching Logic
    intent_match = (exam_intent == bank_intent)
    
    # Action Word Matching
    exam_actions = extract_action_words(exam_text)
    bank_actions = extract_action_words(bank_text)
    
    action_overlap = exam_actions.intersection(bank_actions)
    action_diff = exam_actions.symmetric_difference(bank_actions)
    
    # Refinement Logic
    score = semantic_score
    
    if intent_match and exam_intent != "general":
        # Boost score for same intent
        score *= 1.15
    elif not intent_match:
        if exam_intent != "general" and bank_intent != "general":
            # Check for compatibility
            is_compatible = (
                bank_intent in INTENT_COMPATIBILITY.get(exam_intent, set()) or
                exam_intent in INTENT_COMPATIBILITY.get(bank_intent, set())
            )
            if is_compatible:
                score *= 0.92 # Mild penalty for compatible intents
            else:
                # Both have clear but different intents (e.g. Applications vs Prep)
                score *= 0.65
        elif exam_intent != "general" or bank_intent != "general":
            # One is specific, other is general - milder penalty
            score *= 0.88
    
    # Action word penalty/bonus
    if action_overlap:
        score += 0.05
    if action_diff and not action_overlap:
        score -= 0.05
        
    # Topic Matching (Technical Keywords)
    exam_tech = extract_technical_keywords(exam_text)
    bank_tech = extract_technical_keywords(bank_text)
    
    if exam_tech and bank_tech:
        intersection = exam_tech.intersection(bank_tech)
        if not intersection:
            # Significant topic mismatch (e.g. Lead Acid vs Lithium Ion)
            score *= 0.60
        else:
            # Check for partial topic match using Jaccard similarity
            jaccard = len(intersection) / len(exam_tech.union(bank_tech))
            if jaccard < 0.35:
                # Topics are related but have distinct specific components
                score *= 0.85
    elif exam_tech or bank_tech:
        # One has tech terms, the other is extremely generic
        score *= 0.90
    
    # Clamp score between 0 and 1
    return max(0.0, min(1.0, float(score)))

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
    """Return embedding for a single string as a Python float list"""
    model = get_model()
    if model is None:
        return None
    try:
        embedding = model.encode(text, normalize_embeddings=True)
        return embedding.tolist()
    except Exception as e:
        logger.error(f"Encoding error: {e}")
        return None

def encode_texts(texts: List[str]) -> List[Optional[List[float]]]:
    """Return embeddings for multiple strings as a list of float lists"""
    if not texts:
        return []
    model = get_model()
    if model is None:
        return [None] * len(texts)
    try:
        embeddings = model.encode(texts, normalize_embeddings=True, batch_size=32, show_progress_bar=False)
        return embeddings.tolist()
    except Exception as e:
        logger.error(f"Batch encoding error: {e}")
        return [None] * len(texts)


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


def prepare_bank_embeddings(bank_questions: List[Dict]) -> Dict:
    """
    Pre-parse all bank embeddings and metadata once.
    Returns a dict containing the matrix and metadata for fast matching.
    """
    embeddings = []
    metadata = []
    
    for bq in bank_questions:
        emb_raw = bq.get("embedding")
        if not emb_raw:
            continue
        
        bank_emb = emb_raw if isinstance(emb_raw, list) else json_to_embedding(emb_raw)
        if bank_emb:
            # Pre-extract intent, actions, and technical terms to save time during matching
            q_text = bq.get("question_text", "")
            bq["intent"] = extract_intent(q_text)
            bq["action_words"] = extract_action_words(q_text)
            bq["tech_keywords"] = extract_technical_keywords(q_text)
            
            embeddings.append(bank_emb)
            metadata.append(bq)
            
    if not embeddings:
        return {"matrix": np.array([]), "metadata": []}
        
    return {
        "matrix": np.array(embeddings),
        "metadata": metadata
    }


def match_exam_batch_to_bank(
    exam_questions: List[Dict], # List of {text, embedding}
    prepared_bank: Dict
) -> List[Tuple[Optional[Dict], float, str]]:
    """
    Highly optimized batch matching using vectorized operations and pre-cached metadata.
    """
    bank_matrix = prepared_bank.get("matrix")
    bank_meta = prepared_bank.get("metadata")
    
    if bank_matrix is None or len(bank_matrix) == 0 or not exam_questions:
        return [(None, 0.0, "not_matched")] * len(exam_questions)

    # 1. Prepare exam embeddings matrix
    exam_embs = []
    for eq in exam_questions:
        emb = eq.get("embedding")
        if emb is None:
            # Fallback if not provided, but should be pre-encoded
            emb = encode_text(eq.get("question_text", ""))
        exam_embs.append(emb or [0.0] * bank_matrix.shape[1])
    
    exam_matrix = np.array(exam_embs)
    
    # 2. Vectorized Cosine Similarity: (N x D) @ (D x M) -> (N x M)
    # Since embeddings are normalized, dot product is cosine similarity
    similarity_matrix = np.dot(exam_matrix, bank_matrix.T)
    
    # 3. Apply refined scoring logic with pre-cached metadata
    results = []
    for i, eq in enumerate(exam_questions):
        exam_text = eq.get("question_text", "")
        exam_intent = extract_intent(exam_text)
        exam_actions = extract_action_words(exam_text)
        exam_tech = extract_technical_keywords(exam_text)
        
        best_score = -1.0
        best_q = None
        
        # We still need to loop for refined scoring, but we use pre-cached values
        for j, bq in enumerate(bank_meta):
            raw_score = similarity_matrix[i, j]
            
            # Fast refined score calculation
            # Inlined logic from calculate_refined_score to avoid function call overhead
            score = raw_score
            bank_intent = bq.get("intent", "general")
            
            # Intent refinement
            if exam_intent == bank_intent and exam_intent != "general":
                score *= 1.15
            elif exam_intent != bank_intent:
                if exam_intent != "general" and bank_intent != "general":
                    is_compatible = (
                        bank_intent in INTENT_COMPATIBILITY.get(exam_intent, set()) or
                        exam_intent in INTENT_COMPATIBILITY.get(bank_intent, set())
                    )
                    score *= 0.92 if is_compatible else 0.65
                elif exam_intent != "general" or bank_intent != "general":
                    score *= 0.88
            
            # Action word refinement
            bank_actions = bq.get("action_words", set())
            overlap = exam_actions.intersection(bank_actions)
            if overlap:
                score += 0.05
            elif exam_actions.symmetric_difference(bank_actions):
                score -= 0.05

            # Topic Matching (Technical Keywords)
            bank_tech = bq.get("tech_keywords", set())
            if exam_tech and bank_tech:
                intersection = exam_tech.intersection(bank_tech)
                if not intersection:
                    score *= 0.60
                else:
                    jaccard = len(intersection) / len(exam_tech.union(bank_tech))
                    if jaccard < 0.35:
                        score *= 0.85
            elif exam_tech or bank_tech:
                score *= 0.90
                
            refined_score = max(0.0, min(1.0, float(score)))
            
            if refined_score > best_score:
                best_score = refined_score
                best_q = bq
                
        results.append((best_q, best_score, classify_match(best_score)))
        
    return results

def match_exam_to_bank(
    exam_text: str,
    exam_embedding: Optional[List[float]],
    prepared_bank: Dict
) -> Tuple[Optional[Dict], float, str]:
    """Legacy wrapper for single question matching"""
    res = match_exam_batch_to_bank(
        [{"question_text": exam_text, "embedding": exam_embedding}],
        prepared_bank
    )
    return res[0]


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
        u_no = bq.get('unit_no')
        u_title = bq.get('unit_title')
        
        # Skip questions without a unit so they don't appear in unit coverage or uncovered topics
        if u_no is None and not u_title:
            continue
            
        unit_key = f"Unit {u_no if u_no is not None else '?'} - {u_title if u_title else 'Unknown'}"
        
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
