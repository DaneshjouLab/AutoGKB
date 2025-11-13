# SPDX-FileCopyrightText: 2025 Stanford University and the project authors (see CONTRIBUTORS.md)
# SPDX-License-Identifier: Apache-2.0
from typing import Dict, List, Any, Optional, Tuple
from difflib import SequenceMatcher
import re
from src.benchmark.shared_utils import (
    exact_match,
    semantic_similarity,
    category_equal,
    numeric_tolerance_match,
    parse_numeric,
    compute_weighted_score,
)


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
    value_score = numeric_tolerance_match(
        gt_val_num, pred_val_num, exact_weight=1.0, tolerance_5pct=0.9, tolerance_10pct=0.7
    )

    # Combined: 50% operator, 50% value
    return 0.5 * operator_score + 0.5 * value_score


def validate_study_parameters_dependencies(
    annotation: Dict[str, Any],
    related_annotations: Optional[List[Dict[str, Any]]] = None,
) -> List[str]:
    """Validate field dependencies for study parameters."""
    issues: List[str] = []
    
    # Variant Annotation ID should exist in related annotations if provided
    variant_id = annotation.get("Variant Annotation ID")
    if variant_id and related_annotations:
        found = any(
            ann.get("Variant Annotation ID") == variant_id
            for ann in related_annotations
        )
        if not found:
            issues.append(
                f"Variant Annotation ID {variant_id} not found in related annotations"
            )
    
    return issues


def validate_statistical_consistency(annotation: Dict[str, Any]) -> List[str]:
    """Validate statistical consistency of P value, ratio stat, and confidence intervals."""
    issues: List[str] = []
    
    p_value_str = annotation.get("P Value")
    ratio_stat_type = annotation.get("Ratio Stat Type")
    ratio_stat = annotation.get("Ratio Stat")
    ci_start = annotation.get("Confidence Interval Start")
    ci_stop = annotation.get("Confidence Interval Stop")
    
    # Parse P value
    p_op, p_val = parse_p_value(p_value_str)
    ratio_stat_num = parse_numeric(ratio_stat)
    ci_start_num = parse_numeric(ci_start)
    ci_stop_num = parse_numeric(ci_stop)
    
    # Check P value and ratio stat consistency
    if p_op and ratio_stat_type and ratio_stat_num is not None:
        # If P value is significant (< 0.05 or <= 0.05), ratio stat should typically be != 1
        # If P value is not significant (>= 0.05), ratio stat might be closer to 1
        if p_val is not None and p_val < 0.05:
            if ratio_stat_num == 1.0:
                issues.append(
                    "P value is significant (< 0.05) but Ratio Stat equals 1.0 (may indicate inconsistency)"
                )
    
    # Check confidence interval consistency
    if ci_start_num is not None and ci_stop_num is not None:
        if ci_start_num >= ci_stop_num:
            issues.append(
                f"Confidence Interval Start ({ci_start_num}) should be less than Stop ({ci_stop_num})"
            )
        
        # Check if ratio stat is within confidence interval (if both present)
        if ratio_stat_num is not None:
            if ratio_stat_num < ci_start_num or ratio_stat_num > ci_stop_num:
                issues.append(
                    f"Ratio Stat ({ratio_stat_num}) should be within Confidence Interval [{ci_start_num}, {ci_stop_num}]"
                )
    
    # Check frequency consistency
    freq_cases = parse_numeric(annotation.get("Frequency in Cases"))
    freq_controls = parse_numeric(annotation.get("Frequency in Controls"))
    study_cases = parse_numeric(annotation.get("Study Cases"))
    study_controls = parse_numeric(annotation.get("Study Controls"))
    
    if freq_cases is not None and study_cases is not None:
        if freq_cases < 0 or freq_cases > 1:
            issues.append(
                f"Frequency in Cases ({freq_cases}) should be between 0 and 1"
            )
    
    if freq_controls is not None and study_controls is not None:
        if freq_controls < 0 or freq_controls > 1:
            issues.append(
                f"Frequency in Controls ({freq_controls}) should be between 0 and 1"
            )
    
    return issues


def evaluate_study_parameters(
    samples: List[Dict[str, Any]],
    field_weights: Optional[Dict[str, float]] = None,
    related_annotations: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Evaluate study parameters when provided a list with exactly two dicts:
      - samples[0] = ground truth study parameters dict
      - samples[1] = prediction study parameters dict
    
    Args:
        samples: [ground_truth_dict, prediction_dict]
        field_weights: Optional dict mapping field names to weights for weighted scoring.
                      If None, all fields are weighted equally (unweighted mean).
        related_annotations: Optional list of related annotations for dependency validation.
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
        return {'total_samples': 0, 'field_scores': {}, 'overall_score': 0.0, 'detailed_results': []}

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
        
        # Dependency validation
        dependency_issues = []
        dependency_issues.extend(validate_study_parameters_dependencies(p, related_annotations))
        dependency_issues.extend(validate_statistical_consistency(p))
        sample_result['dependency_issues'] = dependency_issues
        
        if dependency_issues:
            penalty_per_issue = 0.05
            total_penalty = min(len(dependency_issues) * penalty_per_issue, 0.3)
            fields_to_penalize = set()
            for issue in dependency_issues:
                if "Variant Annotation ID" in issue:
                    fields_to_penalize.add("Variant Annotation ID")
                elif "P value" in issue.lower() or "ratio stat" in issue.lower():
                    fields_to_penalize.update(["P Value", "Ratio Stat", "Ratio Stat Type"])
                elif "confidence interval" in issue.lower():
                    fields_to_penalize.update(
                        ["Confidence Interval Start", "Confidence Interval Stop", "Ratio Stat"]
                    )
                elif "frequency" in issue.lower():
                    fields_to_penalize.update(
                        [
                            "Frequency in Cases",
                            "Frequency in Controls",
                            "Study Cases",
                            "Study Controls",
                        ]
                    )
                else:
                    fields_to_penalize.update(sample_result['field_scores'].keys())
            for field in fields_to_penalize:
                if field in sample_result['field_scores']:
                    original_score = sample_result['field_scores'][field]
                    sample_result['field_scores'][field] = original_score * (
                        1 - total_penalty
                    )
        results['detailed_results'].append(sample_result)

    for field in list(field_evaluators.keys()):
        field_scores = [s['field_scores'][field] for s in results['detailed_results']]
        results['field_scores'][field] = {'mean_score': sum(field_scores) / len(field_scores), 'scores': field_scores}

    # Compute overall score with optional field weights
    field_mean_scores = {k: v['mean_score'] for k, v in results['field_scores'].items()}
    results['overall_score'] = compute_weighted_score(field_mean_scores, field_weights)
    return results

