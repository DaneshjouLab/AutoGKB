"""
Evaluation metrics and scoring functions for the benchmarking system.
"""

import re
import json
from typing import Dict, List, Any, Tuple, Optional, Union
from dataclasses import dataclass
from difflib import SequenceMatcher
from loguru import logger



@dataclass
class FieldScore:
    """Score for a single field evaluation."""
    field_name: str
    exact_match: bool
    score: float
    predicted: Any
    expected: Any
    error_type: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'field_name': self.field_name,
            'exact_match': self.exact_match,
            'score': self.score,
            'predicted': self.predicted,
            'expected': self.expected,
            'error_type': self.error_type
        }


@dataclass
class SampleScore:
    """Score for a complete sample evaluation."""
    pmcid: str
    field_scores: List[FieldScore]
    overall_score: float
    weighted_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'pmcid': self.pmcid,
            'field_scores': [fs.to_dict() for fs in self.field_scores],
            'overall_score': self.overall_score,
            'weighted_score': self.weighted_score
        }


class EvaluationMetrics:
    """Comprehensive evaluation metrics for pharmacogenomic extraction."""
    
    def __init__(self, field_weights: Optional[Dict[str, float]] = None):
        self.field_weights = field_weights or {}
        self.default_weight = 1.0
    
    def evaluate_sample(
        self, 
        predicted: Dict[str, Any], 
        expected: Dict[str, Any],
        pmcid: str
    ) -> SampleScore:
        """Evaluate a single sample prediction against ground truth."""
        field_scores = []
        
        for field_name in expected.keys():
            if field_name in ['variant_annotation_id', 'pmid', 'article_path']:
                continue  # Skip metadata fields
                
            field_score = self._evaluate_field(
                field_name, 
                predicted.get(field_name),
                expected.get(field_name)
            )
            field_scores.append(field_score)
        
        # Calculate overall scores
        if field_scores:
            overall_score = sum(fs.score for fs in field_scores) / len(field_scores)
            weighted_score = self._calculate_weighted_score(field_scores)
        else:
            overall_score = 0.0
            weighted_score = 0.0
        
        return SampleScore(
            pmcid=pmcid,
            field_scores=field_scores,
            overall_score=overall_score,
            weighted_score=weighted_score
        )
    
    def _evaluate_field(
        self, 
        field_name: str, 
        predicted: Any, 
        expected: Any
    ) -> FieldScore:
        """Evaluate a single field."""
        # Handle None values
        if expected is None and predicted is None:
            return FieldScore(field_name, True, 1.0, predicted, expected)
        
        if expected is None or predicted is None:
            return FieldScore(
                field_name, 
                False, 
                0.0, 
                predicted, 
                expected,
                error_type="missing_value"
            )
        
        # Convert to strings for comparison
        pred_str = str(predicted).strip() if predicted is not None else ""
        exp_str = str(expected).strip() if expected is not None else ""
        
        # Exact match check
        if pred_str.lower() == exp_str.lower():
            return FieldScore(field_name, True, 1.0, predicted, expected)
        
        # Field-specific scoring
        score = self._calculate_field_score(field_name, pred_str, exp_str)
        
        return FieldScore(
            field_name,
            False,
            score,
            predicted,
            expected,
            error_type=self._classify_error(pred_str, exp_str)
        )
    
    def _calculate_field_score(self, field_name: str, predicted: str, expected: str) -> float:
        """Calculate field-specific score."""
        # Categorical fields - require exact match
        categorical_fields = {
            "significance", "direction_of_effect", "phenotype_category",
            "is_plural", "is_is_not_associated", "multiple_drugs_and_or",
            "specialty_population"
        }
        
        if field_name in categorical_fields:
            return 1.0 if predicted.lower() == expected.lower() else 0.0
        
        # Entity fields - use fuzzy matching
        entity_fields = {
            "gene", "drugs", "variant_haplotypes", "alleles",
            "comparison_alleles_or_genotypes"
        }
        
        if field_name in entity_fields:
            return self._fuzzy_match_score(predicted, expected)
        
        # Text fields - use semantic similarity
        text_fields = {
            "sentence", "notes", "population_phenotypes_or_diseases",
            "pd_pk_terms", "population_types"
        }
        
        if field_name in text_fields:
            return self._semantic_similarity_score(predicted, expected)
        
        # Default: fuzzy matching
        return self._fuzzy_match_score(predicted, expected)
    
    def _fuzzy_match_score(self, predicted: str, expected: str) -> float:
        """Calculate fuzzy match score using sequence similarity."""
        if not predicted and not expected:
            return 1.0
        if not predicted or not expected:
            return 0.0
        
        # Normalize strings
        pred_norm = self._normalize_entity(predicted)
        exp_norm = self._normalize_entity(expected)
        
        # Calculate similarity
        similarity = SequenceMatcher(None, pred_norm, exp_norm).ratio()
        
        # Apply threshold - partial credit for close matches
        if similarity >= 0.9:
            return 1.0
        elif similarity >= 0.7:
            return 0.8
        elif similarity >= 0.5:
            return 0.5
        else:
            return 0.0
    
    def _semantic_similarity_score(self, predicted: str, expected: str) -> float:
        """Calculate semantic similarity score for text fields."""
        if not predicted and not expected:
            return 1.0
        if not predicted or not expected:
            return 0.0
        
        # Simple token-based similarity (can be enhanced with embeddings)
        pred_tokens = set(self._tokenize_text(predicted.lower()))
        exp_tokens = set(self._tokenize_text(expected.lower()))
        
        if not pred_tokens and not exp_tokens:
            return 1.0
        if not pred_tokens or not exp_tokens:
            return 0.0
        
        # Jaccard similarity
        intersection = len(pred_tokens & exp_tokens)
        union = len(pred_tokens | exp_tokens)
        
        return intersection / union if union > 0 else 0.0
    
    def _normalize_entity(self, entity: str) -> str:
        """Normalize entity names for comparison."""
        # Remove common prefixes/suffixes
        entity = re.sub(r'^(rs|CYP|COMT)', '', entity, flags=re.IGNORECASE)
        
        # Remove special characters and normalize spacing
        entity = re.sub(r'[^\w\s\*\+\-]', ' ', entity)
        entity = re.sub(r'\s+', ' ', entity).strip()
        
        return entity.lower()
    
    def _tokenize_text(self, text: str) -> List[str]:
        """Tokenize text for semantic comparison."""
        # Simple word tokenization
        tokens = re.findall(r'\b\w+\b', text.lower())
        # Remove common stop words
        stop_words = {'is', 'are', 'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        return [token for token in tokens if token not in stop_words and len(token) > 2]
    
    def _classify_error(self, predicted: str, expected: str) -> str:
        """Classify the type of error."""
        if not predicted:
            return "missing_prediction"
        if not expected:
            return "unexpected_prediction"
        
        # Length-based classification
        if len(predicted) < len(expected) * 0.5:
            return "incomplete_extraction"
        if len(predicted) > len(expected) * 2:
            return "over_extraction"
        
        return "content_mismatch"
    
    def _calculate_weighted_score(self, field_scores: List[FieldScore]) -> float:
        """Calculate weighted average score."""
        total_weight = 0.0
        weighted_sum = 0.0
        
        for field_score in field_scores:
            weight = self.field_weights.get(field_score.field_name, self.default_weight)
            weighted_sum += field_score.score * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def aggregate_results(self, sample_scores: List[SampleScore]) -> Dict[str, Any]:
        """Aggregate results across all samples."""
        if not sample_scores:
            return {}
        
        # Overall statistics
        overall_scores = [s.overall_score for s in sample_scores]
        weighted_scores = [s.weighted_score for s in sample_scores]
        
        results = {
            "total_samples": len(sample_scores),
            "mean_overall_score": sum(overall_scores) / len(overall_scores),
            "mean_weighted_score": sum(weighted_scores) / len(weighted_scores),
            "min_score": min(overall_scores),
            "max_score": max(overall_scores)
        }
        
        # Field-level statistics
        field_stats = {}
        all_field_scores = {}
        
        for sample_score in sample_scores:
            for field_score in sample_score.field_scores:
                field_name = field_score.field_name
                if field_name not in all_field_scores:
                    all_field_scores[field_name] = []
                all_field_scores[field_name].append(field_score)
        
        for field_name, scores in all_field_scores.items():
            field_values = [s.score for s in scores]
            exact_matches = sum(1 for s in scores if s.exact_match)
            
            field_stats[field_name] = {
                "mean_score": sum(field_values) / len(field_values),
                "exact_match_rate": exact_matches / len(scores),
                "total_predictions": len(scores),
                "error_types": self._count_error_types(scores)
            }
        
        results["field_statistics"] = field_stats
        
        # Performance by score ranges
        score_ranges = {
            "excellent": sum(1 for s in overall_scores if s >= 0.9),
            "good": sum(1 for s in overall_scores if 0.7 <= s < 0.9),
            "fair": sum(1 for s in overall_scores if 0.5 <= s < 0.7),
            "poor": sum(1 for s in overall_scores if s < 0.5)
        }
        results["score_distribution"] = score_ranges
        
        return results
    
    def _count_error_types(self, field_scores: List[FieldScore]) -> Dict[str, int]:
        """Count error types for a field."""
        error_counts = {}
        for score in field_scores:
            if score.error_type:
                error_counts[score.error_type] = error_counts.get(score.error_type, 0) + 1
        return error_counts
    
    def generate_error_analysis(self, sample_scores: List[SampleScore]) -> Dict[str, Any]:
        """Generate detailed error analysis."""
        error_analysis = {
            "common_errors": {},
            "field_specific_issues": {},
            "difficult_samples": []
        }
        
        # Find samples with low scores
        low_score_samples = [s for s in sample_scores if s.overall_score < 0.5]
        error_analysis["difficult_samples"] = [
            {
                "pmcid": s.pmcid,
                "overall_score": s.overall_score,
                "main_issues": [fs.field_name for fs in s.field_scores if fs.score < 0.3]
            }
            for s in low_score_samples[:10]  # Top 10 most difficult
        ]
        
        return error_analysis