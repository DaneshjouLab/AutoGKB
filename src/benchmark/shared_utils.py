"""Shared utilities for benchmark evaluation functions."""
from typing import Any, Optional, Dict, List
from difflib import SequenceMatcher
import numpy as np
import re
from sentence_transformers import SentenceTransformer


_model: Optional[SentenceTransformer] = None


def _get_model() -> SentenceTransformer:
    """Get or initialize the PubMedBERT model."""
    global _model
    if _model is None:
        _model = SentenceTransformer("pritamdeka/S-PubMedBert-MS-MARCO")
    return _model


def exact_match(gt_val: Any, pred_val: Any) -> float:
    """Exact string match - case and whitespace insensitive."""
    if gt_val is None and pred_val is None:
        return 1.0
    if gt_val is None or pred_val is None:
        return 0.0
    return (
        1.0 if str(gt_val).strip().lower() == str(pred_val).strip().lower() else 0.0
    )


def semantic_similarity(gt_val: Any, pred_val: Any) -> float:
    """Semantic similarity using PubMedBERT embeddings."""
    if gt_val is None and pred_val is None:
        return 1.0
    if gt_val is None or pred_val is None:
        return 0.0
    gt_str = str(gt_val).strip()
    pred_str = str(pred_val).strip()
    if gt_str == pred_str:
        return 1.0
    try:
        model = _get_model()
        embeddings = model.encode([gt_str, pred_str])
        gt_embedding = embeddings[0]
        pred_embedding = embeddings[1]
        similarity = float(
            np.dot(gt_embedding, pred_embedding)
            / (np.linalg.norm(gt_embedding) * np.linalg.norm(pred_embedding))
        )
        return similarity
    except Exception:
        return SequenceMatcher(None, gt_str.lower(), pred_str.lower()).ratio()


def category_equal(a: Any, b: Any) -> float:
    """Category equality check (normalized string comparison)."""
    a_norm = re.sub(r"\s+", " ", str(a).strip().lower()) if a is not None else None
    b_norm = re.sub(r"\s+", " ", str(b).strip().lower()) if b is not None else None
    if a_norm is None and b_norm is None:
        return 1.0
    if a_norm is None or b_norm is None:
        return 0.0
    return 1.0 if a_norm == b_norm else 0.0


def parse_numeric(value: Any) -> Optional[float]:
    """Parse numeric value from string or number, handling scientific notation."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        # Remove common formatting (commas, spaces, currency symbols)
        cleaned = re.sub(r'[,\s$]', '', value.strip())
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def numeric_tolerance_match(
    gt_val: Any,
    pred_val: Any,
    exact_weight: float = 1.0,
    tolerance_5pct: float = 0.9,
    tolerance_10pct: float = 0.8,
) -> float:
    """Numeric comparison with tolerance levels."""
    gt_num = parse_numeric(gt_val)
    pred_num = parse_numeric(pred_val)

    if gt_num is None and pred_num is None:
        return 1.0
    if gt_num is None or pred_num is None:
        return 0.0

    if gt_num == 0 and pred_num == 0:
        return 1.0
    if gt_num == 0 or pred_num == 0:
        return 0.0

    diff = abs(gt_num - pred_num)
    pct_diff = diff / abs(gt_num)

    if diff == 0:
        return exact_weight
    elif pct_diff <= 0.05:
        return tolerance_5pct
    elif pct_diff <= 0.10:
        return tolerance_10pct
    else:
        return 0.0


def parse_variant_list(variants_text: Optional[str]) -> List[str]:
    """Parse variant list from text, splitting on common delimiters."""
    if not variants_text:
        return []
    tokens = re.split(r"[,;|\s]+(?:\+\s*)?", variants_text)
    return [t.strip() for t in tokens if t and t.strip()]


def normalize_variant(variant: str) -> str:
    """Normalize variant string for comparison."""
    v = variant.strip()
    if v.lower().startswith("rs"):
        return v.lower()
    return re.sub(r"\s+", "", v)


def variant_substring_match(gt_val: Any, pred_val: Any) -> float:
    """Return 1.0 if GT substring appears in prediction (case-insensitive)."""
    if gt_val is None and pred_val is None:
        return 1.0
    if gt_val is None or pred_val is None:
        return 0.0
    gt_str = re.sub(r"\s+", " ", str(gt_val).strip().lower())
    pred_str = re.sub(r"\s+", " ", str(pred_val).strip().lower())
    if not gt_str:
        return 1.0 if not pred_str else 0.0
    return 1.0 if gt_str in pred_str else 0.0


def compute_weighted_score(
    field_scores: Dict[str, float],
    field_weights: Optional[Dict[str, float]] = None,
) -> float:
    """Compute weighted average of field scores."""
    if not field_scores:
        return 0.0
    
    if field_weights is None:
        # Unweighted mean (default behavior)
        return sum(field_scores.values()) / len(field_scores)
    
    # Weighted mean
    weighted_sum = 0.0
    total_weight = 0.0
    for field, score in field_scores.items():
        weight = field_weights.get(field, 1.0)
        weighted_sum += score * weight
        total_weight += weight
    
    return weighted_sum / total_weight if total_weight > 0 else 0.0

