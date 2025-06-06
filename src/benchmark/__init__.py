"""
AutoGKB Benchmarking System

A comprehensive framework for evaluating language model performance on 
pharmacogenomic knowledge extraction from scientific articles.
"""

from .data_loader import BenchmarkDataLoader
from .evaluator import BenchmarkEvaluator
from .metrics import EvaluationMetrics
from .models import LanguageModelInterface
from .pipeline import BenchmarkPipeline
from .config import BenchmarkConfig

__version__ = "1.0.0"
__all__ = [
    "BenchmarkDataLoader",
    "BenchmarkEvaluator", 
    "EvaluationMetrics",
    "LanguageModelInterface",
    "BenchmarkPipeline",
    "BenchmarkConfig"
]