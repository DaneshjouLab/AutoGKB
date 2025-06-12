"""
Annotation extraction module for pharmacogenomic variant annotations.

This module implements a multi-stage LLM pipeline for extracting structured
pharmacogenomic variant annotations from biomedical articles.
"""

from .pipeline import AnnotationPipeline
from .inference import (
    RelevanceScreener,
    EntityExtractor,
    AnnotationClassifier,
    RowGenerator,
    QualityValidator
)
from .models import (
    ArticleInput,
    RelevanceResult,
    ExtractedEntities,
    ClassificationResult,
    AnnotationRow,
    ValidationResult
)

__all__ = [
    'AnnotationPipeline',
    'RelevanceScreener',
    'EntityExtractor',
    'AnnotationClassifier',
    'RowGenerator',
    'QualityValidator',
    'ArticleInput',
    'RelevanceResult',
    'ExtractedEntities',
    'ClassificationResult',
    'AnnotationRow',
    'ValidationResult'
]