from typing import List, Dict, Any, Tuple, Set
from dataclasses import dataclass
import re


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

    # Fields with weighted importance
    FIELD_WEIGHTS = {
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

    def __init__(self, matching_threshold: float = 0.7):
        """
        Initialize benchmark.

        Args:
            matching_threshold: Minimum score to consider a match (0-1)
        """
        self.matching_threshold = matching_threshold

    def _normalize_value(self, value: Any) -> str:
        """Normalize a field value for comparison."""
        if value is None:
            return ""

        # Convert to string and normalize
        s = str(value).lower().strip()

        # Remove extra whitespace
        s = re.sub(r'\s+', ' ', s)

        # Remove punctuation variations
        s = re.sub(r'[,;]+', '', s)

        return s

    def _compare_field(self, pred_value: Any, gt_value: Any) -> float:
        """
        Compare two field values and return similarity score (0-1).

        Args:
            pred_value: Predicted value
            gt_value: Ground truth value

        Returns:
            Similarity score between 0 and 1
        """
        pred_norm = self._normalize_value(pred_value)
        ground_truth_norm = self._normalize_value(gt_value)

        # Both empty or None
        if not pred_norm and not ground_truth_norm:
            return 1.0

        # One empty, one not
        if not pred_norm or not ground_truth_norm:
            return 0.0

        # Exact match
        if pred_norm == ground_truth_norm:
            return 1.0

        # Check if one contains the other (useful for partial matches)
        if pred_norm in ground_truth_norm or ground_truth_norm in pred_norm:
            return 0.8

        #The Jaccard index is particularly useful when the presence or absence of elements 
        # in the sets is more important than their frequency or order.
        # could be used to help check for multiple entries put in one annotation?
        pred_tokens = set(pred_norm.split())
        gt_tokens = set(ground_truth_norm.split())

        if pred_tokens and gt_tokens:
            intersection = len(pred_tokens & gt_tokens)
            union = len(pred_tokens | gt_tokens)
            jaccard = intersection / union if union > 0 else 0.0
            return jaccard

        return 0.0

    def _compare_annotations(self, pred: Dict[str, Any], gt: Dict[str, Any]) -> float:
        """
        Compare a predicted annotation with a ground truth annotation.

        Args:
            pred: Predicted annotation
            gt: Ground truth annotation

        Returns:
            Float ranging from 0 - 1 denoting similarity
        """
        field_scores = {}
        weighted_sum = 0.0
        total_weight = 0.0

        for field in self.CORE_FIELDS:
            weight = self.FIELD_WEIGHTS.get(field, 1.0)
            similarity = self._compare_field(pred.get(field), gt.get(field))

            field_scores[field] = similarity
            weighted_sum += similarity * weight
            total_weight += weight

        # Calculate weighted average
        matching_score = weighted_sum / total_weight

        return matching_score

    def _find_best_matches(
        self,
        predictions: List[Dict[str, Any]],
        ground_truths: List[Dict[str, Any]]
    ) -> List[Tuple[int, int, float]]:
        """
        Find best matches between predictions and ground truths.

        Returns:
            List of (pred_idx, gt_idx, score) tuples sorted by score descending
        """
        matches = []

        for pred_idx, pred in enumerate(predictions):
            for gt_idx, gt in enumerate(ground_truths):
                match_score = self._compare_annotations(pred, gt)
                if match_score >= self.matching_threshold:
                    matches.append((pred_idx, gt_idx, match_score))

        # Sort by score descending
        matches.sort(key=lambda x: x[2], reverse=True)

        return matches

    def evaluate(
        self,
        samples: List[Any]
    ) -> float:
        """
        Evaluate predictions against ground truths and return similarity score.

        Handles both single annotation pairs and lists of annotations.

        Args:
            samples: List with exactly 2 items:
                    - [ground_truth_dict, prediction_dict] for single comparison
                    - [ground_truth_list, prediction_list] for multiple comparisons

        Returns:
            Similarity score between 0 and 1
        """
        if not isinstance(samples, list) or len(samples) != 2:
            raise ValueError("Expected a list with exactly two items: [ground_truth, prediction].")

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
            raise ValueError("Both items must be either dicts or lists: [ground_truth, prediction].")

        if not gt_list or not pred_list:
            return 0.0

        # Find all potential matches
        all_matches = self._find_best_matches(pred_list, gt_list)

        # Greedily assign matches (allowing many-to-one mapping)
        matched_preds: Set[int] = set()
        matched_gts: Set[int] = set()
        match_scores = []

        for pred_idx, gt_idx, score in all_matches:
            # Allow multiple predictions to match same ground truth (many-to-one)
            # but each prediction can only match once (one-to-one from pred side)
            if pred_idx not in matched_preds:
                matched_preds.add(pred_idx)
                matched_gts.add(gt_idx)
                match_scores.append(score)

        # Calculate average similarity across all ground truths
        # Matched GTs contribute their match score
        # Unmatched GTs contribute 0
        total_score = sum(match_scores)
        total_possible = len(gt_list)

        return total_score / total_possible


def evaluate_phenotype_annotations(
    samples: List[Any],
    matching_threshold: float = 0.7
) -> float:
    """
    Benchmark phenotype annotations and return an aggregate similarity score.

    Handles both single annotation pairs and lists of annotations.

    Args:
        samples: List with exactly 2 items:
                - [ground_truth_dict, prediction_dict] for single comparison
                - [ground_truth_list, prediction_list] for multiple comparisons
        matching_threshold: Minimum similarity score to consider a match (0-1)

    Returns:
        Similarity score between 0-100 representing how well prediction(s)
        match ground truth(s) across all fields.

    Examples:
        # Single annotation pair
        >>> ground_truth = {"Phenotype": "sensitivity", "Drug(s)": "etoposide", ...}
        >>> prediction = {"Phenotype": "sensitivity", "Drug(s)": "etoposide", ...}
        >>> score = benchmark_phenotype_annotations([ground_truth, prediction])
        >>> print(f"Model Score: {score:.1f}/100")

        # Multiple annotations
        >>> ground_truths = [gt1, gt2, gt3]
        >>> predictions = [pred1, pred2]
        >>> score = benchmark_phenotype_annotations([ground_truths, predictions])
        >>> print(f"Model Score: {score:.1f}/100")
    """
    benchmark = PhenotypeAnnotationBenchmark(matching_threshold=matching_threshold)
    similarity = benchmark.evaluate(samples)

    # Return as 0-100 scale
    return similarity * 100
