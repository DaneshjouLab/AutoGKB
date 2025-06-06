"""
Core evaluation logic for the benchmarking system.
"""

import json
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging

from .data_loader import BenchmarkSample
from .metrics import EvaluationMetrics, SampleScore
from .models import LanguageModelInterface, PharmacogenomicPromptBuilder

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    """Result of evaluating a language model on the benchmark."""
    model_name: str
    sample_scores: List[SampleScore]
    aggregate_metrics: Dict[str, Any]
    error_analysis: Dict[str, Any]
    total_samples: int
    successful_predictions: int
    failed_predictions: List[str]  # PMCIDs of failed predictions


class BenchmarkEvaluator:
    """Main evaluator for the benchmarking system."""
    
    def __init__(
        self,
        model: LanguageModelInterface,
        metrics: EvaluationMetrics,
        schema: Dict[str, str],
        categorical_fields: Dict[str, List[str]]
    ):
        self.model = model
        self.metrics = metrics
        self.schema = schema
        self.categorical_fields = categorical_fields
        self.prompt_builder = PharmacogenomicPromptBuilder(schema, categorical_fields)
    
    def evaluate(self, samples: List[BenchmarkSample]) -> EvaluationResult:
        """Evaluate the model on a list of benchmark samples."""
        logger.info(f"Starting evaluation of {self.model.model_name} on {len(samples)} samples")
        
        sample_scores = []
        failed_predictions = []
        
        for i, sample in enumerate(samples):
            logger.info(f"Processing sample {i+1}/{len(samples)}: {sample.pmcid}")
            
            try:
                # Generate prediction
                prediction = self._generate_prediction(sample)
                
                if prediction is None:
                    failed_predictions.append(sample.pmcid)
                    continue
                
                # Evaluate prediction
                sample_score = self.metrics.evaluate_sample(
                    prediction, sample.annotation, sample.pmcid
                )
                sample_scores.append(sample_score)
                
            except Exception as e:
                logger.error(f"Error processing sample {sample.pmcid}: {e}")
                failed_predictions.append(sample.pmcid)
        
        # Aggregate results
        aggregate_metrics = self.metrics.aggregate_results(sample_scores)
        error_analysis = self.metrics.generate_error_analysis(sample_scores)
        
        logger.info(f"Evaluation completed: {len(sample_scores)} successful, {len(failed_predictions)} failed")
        
        return EvaluationResult(
            model_name=self.model.model_name,
            sample_scores=sample_scores,
            aggregate_metrics=aggregate_metrics,
            error_analysis=error_analysis,
            total_samples=len(samples),
            successful_predictions=len(sample_scores),
            failed_predictions=failed_predictions
        )
    
    def _generate_prediction(self, sample: BenchmarkSample) -> Optional[Dict[str, Any]]:
        """Generate prediction for a single sample."""
        try:
            # Build prompt
            prompt = self.prompt_builder.build_extraction_prompt(sample.article_content)
            
            # Generate response
            response = self.model.generate(prompt)
            
            # Parse JSON response
            prediction = self._parse_model_response(response.content)
            
            if prediction is None:
                logger.warning(f"Failed to parse response for {sample.pmcid}")
                return None
            
            # Validate and clean prediction
            prediction = self._validate_prediction(prediction, sample)
            
            return prediction
            
        except Exception as e:
            logger.error(f"Error generating prediction for {sample.pmcid}: {e}")
            return None
    
    def _parse_model_response(self, response_content: str) -> Optional[Dict[str, Any]]:
        """Parse JSON from model response."""
        # Try to extract JSON from response
        json_patterns = [
            r'```json\s*(\{.*?\})\s*```',  # JSON in code blocks
            r'```\s*(\{.*?\})\s*```',      # JSON in generic code blocks
            r'(\{.*?\})',                   # Direct JSON
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, response_content, re.DOTALL)
            for match in matches:
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue
        
        # If no JSON found, try parsing the entire response
        try:
            return json.loads(response_content.strip())
        except json.JSONDecodeError:
            logger.warning("Could not parse JSON from model response")
            return None
    
    def _validate_prediction(
        self, 
        prediction: Dict[str, Any], 
        sample: BenchmarkSample
    ) -> Dict[str, Any]:
        """Validate and clean prediction."""
        validated = {}
        
        # Ensure required fields are present
        for field_name in self.schema.keys():
            if field_name in ['variant_annotation_id', 'pmid', 'article_path']:
                continue  # Skip metadata fields
            
            value = prediction.get(field_name)
            
            # Clean and validate field value
            cleaned_value = self._clean_field_value(field_name, value)
            validated[field_name] = cleaned_value
        
        # Add metadata from sample
        validated['pmcid'] = sample.pmcid
        validated['article_title'] = sample.article_title
        
        return validated
    
    def _clean_field_value(self, field_name: str, value: Any) -> Any:
        """Clean and validate a field value."""
        if value is None or value == "":
            return None
        
        # Convert to string and clean
        if isinstance(value, (int, float)):
            value = str(value)
        elif not isinstance(value, str):
            value = str(value)
        
        value = value.strip()
        
        # Handle categorical fields
        if field_name in self.categorical_fields:
            allowed_values = self.categorical_fields[field_name]
            
            # Try exact match first
            for allowed in allowed_values:
                if allowed is None and value.lower() in ['null', 'none', '']:
                    return None
                elif allowed is not None and value.lower() == str(allowed).lower():
                    return allowed
            
            # Try partial match for some fields
            if field_name in ['significance']:
                if 'yes' in value.lower() or 'significant' in value.lower():
                    return 'yes'
                elif 'no' in value.lower() or 'not significant' in value.lower():
                    return 'no'
                else:
                    return 'not stated'
            
            # If no match found, keep original value but log warning
            logger.warning(f"Invalid value '{value}' for categorical field '{field_name}'")
        
        return value
    
    def evaluate_single(self, sample: BenchmarkSample) -> Optional[SampleScore]:
        """Evaluate a single sample (useful for debugging)."""
        try:
            prediction = self._generate_prediction(sample)
            if prediction is None:
                return None
            
            return self.metrics.evaluate_sample(
                prediction, sample.annotation, sample.pmcid
            )
        except Exception as e:
            logger.error(f"Error evaluating single sample {sample.pmcid}: {e}")
            return None
    
    def get_prediction_only(self, sample: BenchmarkSample) -> Optional[Dict[str, Any]]:
        """Get prediction without evaluation (useful for analysis)."""
        return self._generate_prediction(sample)