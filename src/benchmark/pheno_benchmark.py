from typing import List, Dict, Any, Tuple, Set, Optional
import re
from src.benchmark.shared_utils import (
    semantic_similarity,
    category_equal,
    variant_substring_match,
    compute_weighted_score,
    parse_variant_list,
    normalize_variant,
)


def expand_pheno_annotations_by_variant(
    annotations: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Expand annotations with multiple variants into separate records."""
    expanded: List[Dict[str, Any]] = []
    for ann in annotations:
        variants_field = ann.get("Variant/Haplotypes")
        tokens = parse_variant_list(variants_field)
        if len(tokens) <= 1:
            expanded.append(ann)
            continue
        for tok in tokens:
            new_ann = dict(ann)
            new_ann["Variant/Haplotypes"] = normalize_variant(tok)
            new_ann["_expanded_from_multi_variant"] = True
            expanded.append(new_ann)
    return expanded


def align_pheno_annotations_by_variant(
    ground_truth_list: List[Dict[str, Any]],
    predictions_list: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Align pheno annotations by variant string with robust matching:
    1) Expand multi-variant records to one per variant
    2) Prefer rsID intersection; fallback to normalized substring containment
    3) If no variant match, fallback to Gene + Drug(s) matching
    Returns aligned (gt_list, pred_list)
    """
    rs_re = re.compile(r"rs\d+", re.IGNORECASE)

    gt_expanded = expand_pheno_annotations_by_variant(ground_truth_list or [])
    pred_expanded = expand_pheno_annotations_by_variant(predictions_list or [])

    pred_index: List[Tuple[set, str, Dict[str, Any]]] = []
    for rec in pred_expanded:
        raw = (rec.get("Variant/Haplotypes") or "").strip()
        raw_norm = normalize_variant(raw).lower()
        rsids = set(m.group(0).lower() for m in rs_re.finditer(raw))
        pred_index.append((rsids, raw_norm, rec))

    aligned_gt: List[Dict[str, Any]] = []
    aligned_pred: List[Dict[str, Any]] = []
    matched_pred_indices: Set[int] = set()

    # First pass: try variant-based matching
    for gt_rec in gt_expanded:
        gt_raw = (gt_rec.get("Variant/Haplotypes") or "").strip()
        gt_norm = normalize_variant(gt_raw).lower()
        gt_rs = set(m.group(0).lower() for m in rs_re.finditer(gt_raw))

        match_idx = None
        match_rec = None
        
        if gt_rs:
            for idx, (rsids, raw_norm, pred_rec) in enumerate(pred_index):
                if idx not in matched_pred_indices and rsids & gt_rs:
                    match_idx = idx
                    match_rec = pred_rec
                    break
        if match_idx is None and gt_norm:
            for idx, (rsids, raw_norm, pred_rec) in enumerate(pred_index):
                if idx not in matched_pred_indices and (gt_norm in raw_norm or raw_norm in gt_norm):
                    match_idx = idx
                    match_rec = pred_rec
                    break

        if match_idx is not None:
            aligned_gt.append(gt_rec)
            aligned_pred.append(match_rec)
            matched_pred_indices.add(match_idx)

    # Second pass: for unmatched GT records, try Gene + Drug(s) matching
    for gt_idx, gt_rec in enumerate(gt_expanded):
        if gt_idx < len(aligned_gt) and aligned_gt[gt_idx] == gt_rec:
            continue  # Already matched
            
        gt_gene = str(gt_rec.get("Gene", "")).strip().lower()
        gt_drug = str(gt_rec.get("Drug(s)", "")).strip().lower()
        
        if not gt_gene and not gt_drug:
            continue
            
        # Try to find match by Gene + Drug
        for idx, (_, _, pred_rec) in enumerate(pred_index):
            if idx in matched_pred_indices:
                continue
                
            pred_gene = str(pred_rec.get("Gene", "")).strip().lower()
            pred_drug = str(pred_rec.get("Drug(s)", "")).strip().lower()
            
            # Match if Gene matches and (Drug matches or both are empty)
            gene_match = gt_gene and pred_gene and gt_gene == pred_gene
            drug_match = (not gt_drug and not pred_drug) or (gt_drug and pred_drug and gt_drug == pred_drug)
            
            if gene_match and drug_match:
                aligned_gt.append(gt_rec)
                aligned_pred.append(pred_rec)
                matched_pred_indices.add(idx)
                break

    return aligned_gt, aligned_pred


class PhenotypeAnnotationBenchmark:
    """Benchmark for evaluating phenotype annotation predictions."""

    # Fields to compare (excluding metadata fields)
    CORE_FIELDS = [
        "Variant/Haplotypes",
        "Gene",
        "Drug(s)",
        "Phenotype Category",
        "Alleles",
        "Is/Is Not associated",
        "Direction of effect",
        "Phenotype",
        "When treated with/exposed to/when assayed with",
        "Comparison Allele(s) or Genotype(s)",
    ]

    # Default field weights (can be overridden via parameter)
    DEFAULT_FIELD_WEIGHTS = {
        "Phenotype": 2.0,
        "Drug(s)": 1.5,
        "Direction of effect": 2.0,
        "Alleles": 1.5,
        "Is/Is Not associated": 1.0,
        "Variant/Haplotypes": 1.0,
        "Gene": 1.0,
        "Phenotype Category": 0.5,
        "When treated with/exposed to/when assayed with": 0.5,
        "Comparison Allele(s) or Genotype(s)": 1.0,
    }

    def __init__(self, matching_threshold: float = 0.3):
        """
        Initialize benchmark.

        Args:
            matching_threshold: Minimum score to consider a match (0-1)
        """
        self.matching_threshold = matching_threshold

    def _get_field_evaluator(self, field: str):
        """Get the appropriate evaluator function for a field."""
        # Map fields to evaluators using shared utilities
        field_evaluators = {
            "Variant/Haplotypes": variant_substring_match,
            "Gene": semantic_similarity,
            "Drug(s)": semantic_similarity,
            "Phenotype Category": category_equal,
            "Alleles": semantic_similarity,
            "Is/Is Not associated": category_equal,
            "Direction of effect": category_equal,
            "Phenotype": semantic_similarity,
            "When treated with/exposed to/when assayed with": semantic_similarity,
            "Comparison Allele(s) or Genotype(s)": semantic_similarity,
        }
        return field_evaluators.get(field, semantic_similarity)

    def _compare_annotations(
        self, pred: Dict[str, Any], gt: Dict[str, Any], field_weights: Dict[str, float]
    ) -> Tuple[float, Dict[str, float]]:
        """
        Compare a predicted annotation with a ground truth annotation.

        Args:
            pred: Predicted annotation
            gt: Ground truth annotation
            field_weights: Field weights for scoring

        Returns:
            Tuple of (matching_score, field_scores_dict)
        """
        field_scores = {}

        for field in self.CORE_FIELDS:
            evaluator = self._get_field_evaluator(field)
            similarity = evaluator(pred.get(field), gt.get(field))
            field_scores[field] = similarity

        # Calculate weighted average
        matching_score = compute_weighted_score(field_scores, field_weights)

        return matching_score, field_scores

    def _find_best_matches(
        self,
        predictions: List[Dict[str, Any]],
        ground_truths: List[Dict[str, Any]],
        field_weights: Dict[str, float],
    ) -> List[Tuple[int, int, float, Dict[str, float]]]:
        """
        Find best matches between predictions and ground truths.

        Returns:
            List of (pred_idx, gt_idx, score, field_scores) tuples sorted by score descending
        """
        matches = []

        for pred_idx, pred in enumerate(predictions):
            for gt_idx, gt in enumerate(ground_truths):
                match_score, field_scores = self._compare_annotations(
                    pred, gt, field_weights
                )
                if match_score >= self.matching_threshold:
                    matches.append((pred_idx, gt_idx, match_score, field_scores))

        # Sort by score descending
        matches.sort(key=lambda x: x[2], reverse=True)

        return matches

    def evaluate(
        self,
        samples: List[Any],
        field_weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate predictions against ground truths and return detailed results.

        Handles both single annotation pairs and lists of annotations.

        Args:
            samples: List with exactly 2 items:
                    - [ground_truth_dict, prediction_dict] for single comparison
                    - [ground_truth_list, prediction_list] for multiple comparisons
            field_weights: Optional dict mapping field names to weights for weighted scoring.
                          If None, uses DEFAULT_FIELD_WEIGHTS.

        Returns:
            Dict with field_scores, overall_score (0-1 scale), detailed_results, total_samples
        """
        if not isinstance(samples, list) or len(samples) != 2:
            raise ValueError(
                "Expected a list with exactly two items: [ground_truth, prediction]."
            )

        gt, pred = samples[0], samples[1]

        # Normalize to lists
        if isinstance(gt, dict) and isinstance(pred, dict):
            # Single annotation pair
            gt_list = [gt]
            pred_list = [pred]
        elif isinstance(gt, list) and isinstance(pred, list):
            # Multiple annotations
            gt_list = gt
            pred_list = pred
        else:
            raise ValueError(
                "Both items must be either dicts or lists: [ground_truth, prediction]."
            )

        if not gt_list or not pred_list:
            return {
                "total_samples": 0,
                "field_scores": {},
                "overall_score": 0.0,
                "detailed_results": [],
            }

        # Align by variant first (similar to FA/Drug benchmarks)
        aligned_gt, aligned_pred = align_pheno_annotations_by_variant(gt_list, pred_list)
        
        if not aligned_gt:
            return {
                "total_samples": 0,
                "field_scores": {},
                "overall_score": 0.0,
                "detailed_results": [],
                "status": "no_overlap_after_alignment",
            }

        # Use provided field weights or default
        weights = (
            field_weights if field_weights is not None else self.DEFAULT_FIELD_WEIGHTS
        )

        # Find all potential matches from aligned pairs
        all_matches = self._find_best_matches(aligned_pred, aligned_gt, weights)

        # Greedily assign matches (allowing many-to-one mapping)
        matched_preds: Set[int] = set()
        matched_pairs: List[
            Tuple[Dict[str, Any], Dict[str, Any], float, Dict[str, float]]
        ] = []

        for pred_idx, gt_idx, score, field_scores in all_matches:
            # Allow multiple predictions to match same ground truth (many-to-one)
            # but each prediction can only match once (one-to-one from pred side)
            if pred_idx not in matched_preds:
                matched_preds.add(pred_idx)
                matched_pairs.append(
                    (aligned_gt[gt_idx], aligned_pred[pred_idx], score, field_scores)
                )

        # Build detailed results structure
        results: Dict[str, Any] = {
            "total_samples": len(matched_pairs),
            "field_scores": {},
            "overall_score": 0.0,
            "detailed_results": [],
        }

        # Compute field scores for matched pairs
        for field in self.CORE_FIELDS:
            field_scores_list = []
            for gt, pred, _, field_scores_dict in matched_pairs:
                field_scores_list.append(field_scores_dict.get(field, 0.0))

            if field_scores_list:
                results["field_scores"][field] = {
                    "mean_score": sum(field_scores_list) / len(field_scores_list),
                    "scores": field_scores_list,
                }
            else:
                results["field_scores"][field] = {
                    "mean_score": 0.0,
                    "scores": [],
                }

        # Build detailed results for each matched pair
        for i, (gt, pred, match_score, field_scores_dict) in enumerate(matched_pairs):
            sample_result: Dict[str, Any] = {
                "sample_id": i,
                "field_scores": field_scores_dict.copy(),
                "field_values": {},
                "dependency_issues": [],  # Placeholder for future dependency validation
            }
            
            # Store actual values for display
            for field in self.CORE_FIELDS:
                sample_result["field_values"][field] = {
                    "ground_truth": gt.get(field),
                    "prediction": pred.get(field)
                }

            results["detailed_results"].append(sample_result)

        # Recompute field scores from detailed results (after any penalties)
        for field in self.CORE_FIELDS:
            field_scores = [
                s["field_scores"].get(field, 0.0) for s in results["detailed_results"]
            ]
            if field_scores:
                results["field_scores"][field] = {
                    "mean_score": sum(field_scores) / len(field_scores),
                    "scores": field_scores,
                }

        # Compute overall score with field weights
        field_mean_scores = {
            k: v["mean_score"] for k, v in results["field_scores"].items()
        }
        results["overall_score"] = compute_weighted_score(field_mean_scores, weights)

        return results


def evaluate_phenotype_annotations(
    samples: List[Any],
    field_weights: Optional[Dict[str, float]] = None,
        matching_threshold: float = 0.3,
) -> Dict[str, Any]:
    """
    Benchmark phenotype annotations and return detailed results.

    Args:
        samples: List with exactly 2 items:
                - [ground_truth_dict, prediction_dict] for single comparison
                - [ground_truth_list, prediction_list] for multiple comparisons
        field_weights: Optional dict mapping field names to weights for weighted scoring.
                      If None, uses default weights.
        matching_threshold: Minimum similarity score to consider a match (0-1)

    Returns:
        Dict with field_scores, overall_score (0-1 scale), detailed_results, total_samples

    Examples:
        # Single annotation pair
        >>> ground_truth = {"Phenotype": "sensitivity", "Drug(s)": "etoposide", ...}
        >>> prediction = {"Phenotype": "sensitivity", "Drug(s)": "etoposide", ...}
        >>> result = evaluate_phenotype_annotations([ground_truth, prediction])
        >>> print(f"Overall Score: {result['overall_score']:.3f}")

        # Multiple annotations
        >>> ground_truths = [gt1, gt2, gt3]
        >>> predictions = [pred1, pred2]
        >>> result = evaluate_phenotype_annotations([ground_truths, predictions])
        >>> print(f"Overall Score: {result['overall_score']:.3f}")
    """
    benchmark = PhenotypeAnnotationBenchmark(matching_threshold=matching_threshold)
    return benchmark.evaluate(samples, field_weights=field_weights)
