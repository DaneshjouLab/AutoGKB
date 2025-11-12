# SPDX-FileCopyrightText: 2025 Stanford University and the project authors (see CONTRIBUTORS.md)
# SPDX-License-Identifier: Apache-2.0
from typing import Dict, List, Any, Optional, Tuple
from difflib import SequenceMatcher
import numpy as np
import re
from sentence_transformers import SentenceTransformer


_model: Optional[SentenceTransformer] = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("pritamdeka/S-PubMedBert-MS-MARCO")
    return _model


def align_study_parameters_by_variant_id(
    ground_truth_list: List[Dict[str, Any]],
    predictions_list: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Align study parameters by Variant Annotation ID.
    """
    aligned_gt: List[Dict[str, Any]] = []
    aligned_pred: List[Dict[str, Any]] = []

    # prediction index by Variant Annotation ID
    pred_by_id: Dict[Any, Dict[str, Any]] = {}
    pred_by_pmid_id: Dict[Tuple[Any, Any], Dict[str, Any]] = {}

    for pred_rec in predictions_list:
        variant_id = pred_rec.get('Variant Annotation ID')
        pmid = pred_rec.get('PMID')
        if variant_id is not None:
            pred_by_id[variant_id] = pred_rec
            if pmid is not None:
                pred_by_pmid_id[(pmid, variant_id)] = pred_rec

    # ground truth to predictions
    for gt_rec in ground_truth_list:
        variant_id = gt_rec.get('Variant Annotation ID')
        pmid = gt_rec.get('PMID')

        match = None
        if variant_id is not None and variant_id in pred_by_id:
            match = pred_by_id[variant_id]

        if match is not None:
            aligned_gt.append(gt_rec)
            aligned_pred.append(match)

    return aligned_gt, aligned_pred


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


def parse_p_value(pval_str: Any) -> Tuple[Optional[str], Optional[float]]:
    """Parse P value string into operator and numeric value."""
    if pval_str is None:
        return None, None

    pval_str = str(pval_str).strip()
    if not pval_str:
        return None, None

    # Extract operator (<=, >=, <, >, =)
    operator_match = re.search(r'([<>=≤≥]=?)', pval_str)
    operator = operator_match.group(1) if operator_match else '='

    # Extract numeric value
    value_str = re.sub(r'[<>=≤≥\s]', '', pval_str)
    value = parse_numeric(value_str)

    return operator, value


def p_value_match(gt_val: Any, pred_val: Any) -> float:
    """Match P value with both operator and value."""
    gt_op, gt_val_num = parse_p_value(gt_val)
    pred_op, pred_val_num = parse_p_value(pred_val)

    if gt_op is None and pred_op is None:
        return 1.0
    if gt_op is None or pred_op is None:
        return 0.0

    # Normalize operators for comparison
    op_map = {'<=': '≤', '>=': '≥', '<': '<', '>': '>', '=': '='}
    gt_op_norm = op_map.get(gt_op, gt_op)
    pred_op_norm = op_map.get(pred_op, pred_op)

    operator_score = 1.0 if gt_op_norm == pred_op_norm else 0.0
    value_score = numeric_tolerance_match(gt_val_num, pred_val_num, exact_weight=1.0, tolerance_5pct=0.9, tolerance_10pct=0.7)

    # Combined: 50% operator, 50% value
    return 0.5 * operator_score + 0.5 * value_score


def evaluate_study_parameters(samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Evaluate study parameters when provided a list with exactly two dicts:
      - samples[0] = ground truth study parameters dict
      - samples[1] = prediction study parameters dict
    """

    if not isinstance(samples, list) or len(samples) != 2:
        raise ValueError("Expected a list with exactly two dicts: [ground_truth, prediction].")
    gt, pred = samples[0], samples[1]
    if not isinstance(gt, dict) or not isinstance(pred, dict):
        raise ValueError("Both items must be dicts: [ground_truth_dict, prediction_dict].")

    # Prepare lists and align
    gt_list_raw: List[Dict[str, Any]] = [gt]
    pred_list_raw: List[Dict[str, Any]] = [pred]
    gt_list, pred_list = align_study_parameters_by_variant_id(gt_list_raw, pred_list_raw)

    if not gt_list:
        # nothing aligned; return empty result structure
        return {'total_samples': 0, 'field_scores': {}, 'overall_score': 0.0, 'detailed_results': []}

    model = _get_model()

    def exact_match(gt_val: Any, pred_val: Any) -> float:
        if gt_val is None and pred_val is None:
            return 1.0
        if gt_val is None or pred_val is None:
            return 0.0
        return 1.0 if str(gt_val).strip().lower() == str(pred_val).strip().lower() else 0.0

    def semantic_similarity(gt_val: Any, pred_val: Any) -> float:
        if gt_val is None and pred_val is None:
            return 1.0
        if gt_val is None or pred_val is None:
            return 0.0
        gt_str = str(gt_val).strip()
        pred_str = str(pred_val).strip()
        if gt_str == pred_str:
            return 1.0
        try:
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
        a_norm = (re.sub(r"\s+", " ", str(a).strip().lower()) if a is not None else None)
        b_norm = (re.sub(r"\s+", " ", str(b).strip().lower()) if b is not None else None)
        if a_norm is None and b_norm is None:
            return 1.0
        if a_norm is None or b_norm is None:
            return 0.0
        return 1.0 if a_norm == b_norm else 0.0

    # Map evaluators to study parameters schema fields
    field_evaluators = {
        'Study Parameters ID': exact_match,
        'Variant Annotation ID': exact_match,
        'Study Type': category_equal,
        'Study Cases': lambda gt, pred: numeric_tolerance_match(gt, pred, exact_weight=1.0, tolerance_5pct=0.9, tolerance_10pct=0.8),
        'Study Controls': lambda gt, pred: numeric_tolerance_match(gt, pred, exact_weight=1.0, tolerance_5pct=0.9, tolerance_10pct=0.8),
        'Characteristics': semantic_similarity,
        'Characteristics Type': category_equal,
        'Frequency in Cases': lambda gt, pred: numeric_tolerance_match(gt, pred, exact_weight=1.0, tolerance_5pct=0.9, tolerance_10pct=0.8),
        'Allele of Frequency in Cases': semantic_similarity,
        'Frequency in Controls': lambda gt, pred: numeric_tolerance_match(gt, pred, exact_weight=1.0, tolerance_5pct=0.9, tolerance_10pct=0.8),
        'Allele of Frequency in Controls': semantic_similarity,
        'P Value': p_value_match,
        'Ratio Stat Type': category_equal,
        'Ratio Stat': lambda gt, pred: numeric_tolerance_match(gt, pred, exact_weight=1.0, tolerance_5pct=0.9, tolerance_10pct=0.8),
        'Confidence Interval Start': lambda gt, pred: numeric_tolerance_match(gt, pred, exact_weight=1.0, tolerance_5pct=0.9, tolerance_10pct=0.8),
        'Confidence Interval Stop': lambda gt, pred: numeric_tolerance_match(gt, pred, exact_weight=1.0, tolerance_5pct=0.9, tolerance_10pct=0.8),
        'Biogeographical Groups': category_equal,
    }

    results: Dict[str, Any] = {'total_samples': len(gt_list), 'field_scores': {}, 'overall_score': 0.0}

    for field, evaluator in field_evaluators.items():
        scores: List[float] = []
        for g, p in zip(gt_list, pred_list):
            scores.append(evaluator(g.get(field), p.get(field)))
        results['field_scores'][field] = {'mean_score': sum(scores) / len(scores), 'scores': scores}

    results['detailed_results'] = []
    for i, (g, p) in enumerate(zip(gt_list, pred_list)):
        sample_result: Dict[str, Any] = {'sample_id': i, 'field_scores': {}}
        for field, evaluator in field_evaluators.items():
            sample_result['field_scores'][field] = evaluator(g.get(field), p.get(field))
        # No dependency penalties wired yet for study parameters; can be added later if needed
        sample_result['dependency_issues'] = []
        results['detailed_results'].append(sample_result)

    for field in list(field_evaluators.keys()):
        field_scores = [s['field_scores'][field] for s in results['detailed_results']]
        results['field_scores'][field] = {'mean_score': sum(field_scores) / len(field_scores), 'scores': field_scores}

    field_means = [v['mean_score'] for v in results['field_scores'].values()]
    results['overall_score'] = sum(field_means) / len(field_means) if field_means else 0.0
    return results

