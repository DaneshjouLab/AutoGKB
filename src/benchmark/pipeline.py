"""
Main benchmark pipeline orchestrating the entire evaluation process.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

from .config import BenchmarkConfig
from .data_loader import BenchmarkDataLoader, BenchmarkSample
from .metrics import EvaluationMetrics
from .models import create_model, LanguageModelInterface
from .evaluator import BenchmarkEvaluator, EvaluationResult
from .reporting import BenchmarkReporter

logger = logging.getLogger(__name__)


class BenchmarkPipeline:
    """Main pipeline for running benchmarks."""
    
    def __init__(self, config: BenchmarkConfig):
        self.config = config
        config.validate()
        
        # Initialize components
        self.data_loader = BenchmarkDataLoader(
            config.data_dir,
            config.articles_dir, 
            config.benchmark_dir
        )
        
        self.metrics = EvaluationMetrics(config.field_weights)
        self.reporter = BenchmarkReporter(config.output_dir)
        
        # Get schema information
        self.schema = self.data_loader.get_field_schema()
        self.categorical_fields = self.data_loader.get_categorical_fields()
    
    def generate_responses(
        self,
        model_configs: List[Dict[str, Any]],
        split: str = "test"
    ) -> Dict[str, Path]:
        """Generate model responses and save to JSONL files."""
        logger.info(f"Generating responses on {split} split with {len(model_configs)} models")
        
        # Load data
        samples = self.data_loader.load_split(split)
        if self.config.max_articles:
            samples = samples[:self.config.max_articles]
        
        logger.info(f"Loaded {len(samples)} samples for response generation")
        
        # Generate responses for each model
        response_files = {}
        for model_config in model_configs:
            model_name = model_config.get("name", "unknown")
            logger.info(f"Generating responses for model: {model_name}")
            
            try:
                # Create model
                model = create_model(**model_config)
                
                # Check availability
                if not model.is_available():
                    logger.warning(f"Model {model_name} is not available, skipping")
                    continue
                
                # Generate responses file
                response_file = self._generate_model_responses(model, samples, split)
                response_files[model_name] = response_file
                
            except Exception as e:
                logger.error(f"Error generating responses for model {model_name}: {e}")
                continue
        
        logger.info(f"Response generation completed for {len(response_files)} models")
        return response_files

    def evaluate_responses_file(self, response_file: Path) -> EvaluationResult:
        """Evaluate a JSONL file of model responses and return score."""
        logger.info(f"Evaluating responses from {response_file}")
        
        # Load responses from file
        responses = self._load_responses_from_file(response_file)
        
        if not responses:
            raise ValueError(f"No valid responses found in {response_file}")
        
        # Extract model name from first response
        model_name = responses[0].get("model_name", "unknown")
        
        # Load ground truth data
        split = self._extract_split_from_filename(response_file)
        samples_dict = {s.pmcid: s for s in self.data_loader.load_split(split)}
        
        # Evaluate each response
        sample_scores = []
        failed_predictions = []
        
        for response in responses:
            pmcid = response.get("pmcid")
            if pmcid not in samples_dict:
                logger.warning(f"No ground truth found for PMCID: {pmcid}")
                failed_predictions.append(pmcid)
                continue
            
            try:
                ground_truth = samples_dict[pmcid].annotation
                prediction = {k: v for k, v in response.items() 
                            if k not in ["model_name", "timestamp", "pmcid"]}
                
                sample_score = self.metrics.evaluate_sample(prediction, ground_truth, pmcid)
                sample_scores.append(sample_score)
                
            except Exception as e:
                logger.error(f"Error evaluating response for {pmcid}: {e}")
                failed_predictions.append(pmcid)
        
        # Aggregate results
        aggregate_metrics = self.metrics.aggregate_results(sample_scores)
        error_analysis = self.metrics.generate_error_analysis(sample_scores)
        
        logger.info(f"Evaluation completed: {len(sample_scores)} successful, {len(failed_predictions)} failed")
        
        return EvaluationResult(
            model_name=model_name,
            sample_scores=sample_scores,
            aggregate_metrics=aggregate_metrics,
            error_analysis=error_analysis,
            total_samples=len(responses),
            successful_predictions=len(sample_scores),
            failed_predictions=failed_predictions
        )

    def run_benchmark(
        self, 
        model_configs: List[Dict[str, Any]],
        split: str = "test"
    ) -> Dict[str, EvaluationResult]:
        """Run benchmark on multiple models (legacy method - generates and evaluates in one step)."""
        logger.info(f"Starting benchmark on {split} split with {len(model_configs)} models")
        
        # Generate responses
        response_files = self.generate_responses(model_configs, split)
        
        # Evaluate each response file
        results = {}
        for model_name, response_file in response_files.items():
            try:
                result = self.evaluate_responses_file(response_file)
                results[model_name] = result
                
                # Save intermediate results
                self._save_intermediate_result(result, split)
                
            except Exception as e:
                logger.error(f"Error evaluating model {model_name}: {e}")
                continue
        
        # Generate comparative report
        if results:
            self.reporter.generate_comparative_report(results, split)
        
        logger.info(f"Benchmark completed for {len(results)} models")
        return results
    
    def run_single_model(
        self, 
        model_config: Dict[str, Any],
        split: str = "test"
    ) -> EvaluationResult:
        """Run benchmark on a single model."""
        results = self.run_benchmark([model_config], split)
        model_name = model_config.get("name", "unknown")
        
        if model_name not in results:
            raise RuntimeError(f"Failed to evaluate model {model_name}")
        
        return results[model_name]
    
    def analyze_sample(
        self, 
        pmcid: str, 
        model_config: Dict[str, Any],
        split: str = "test"
    ) -> Dict[str, Any]:
        """Analyze a specific sample in detail."""
        logger.info(f"Analyzing sample {pmcid}")
        
        # Load sample
        samples = self.data_loader.load_split(split)
        sample = next((s for s in samples if s.pmcid == pmcid), None)
        
        if sample is None:
            raise ValueError(f"Sample {pmcid} not found in {split} split")
        
        # Create model and evaluator
        model = create_model(**model_config)
        evaluator = BenchmarkEvaluator(
            model=model,
            metrics=self.metrics,
            schema=self.schema,
            categorical_fields=self.categorical_fields
        )
        
        # Get prediction and evaluation
        prediction = evaluator.get_prediction_only(sample)
        sample_score = evaluator.evaluate_single(sample)
        
        analysis = {
            "pmcid": pmcid,
            "article_title": sample.article_title,
            "model": model_config.get("name", "unknown"),
            "prediction": prediction,
            "ground_truth": sample.annotation,
            "scores": sample_score.__dict__ if sample_score else None,
            "article_content_preview": sample.article_content[:1000] + "..."
        }
        
        # Save detailed analysis
        self.reporter.save_sample_analysis(analysis)
        
        return analysis
    
    def validate_setup(self) -> Dict[str, Any]:
        """Validate the benchmark setup."""
        validation_report = {
            "config_valid": True,
            "data_available": True,
            "models_accessible": {},
            "issues": []
        }
        
        try:
            # Check data availability
            train_samples = self.data_loader.load_split("train")
            val_samples = self.data_loader.load_split("val") 
            test_samples = self.data_loader.load_split("test")
            
            validation_report["data_statistics"] = {
                "train_samples": len(train_samples),
                "val_samples": len(val_samples), 
                "test_samples": len(test_samples)
            }
            
            if not train_samples:
                validation_report["issues"].append("No training samples found")
                validation_report["data_available"] = False
            
        except Exception as e:
            validation_report["issues"].append(f"Data loading error: {e}")
            validation_report["data_available"] = False
        
        # Test model configurations
        test_configs = [
            {"name": "mock", "model_name": "mock"},
            {"name": "gpt-4", "model_name": "gpt-4"},
            {"name": "claude-3-sonnet", "model_name": "claude-3-sonnet-20240229"}
        ]
        
        for config in test_configs:
            try:
                model = create_model(**config)
                is_available = model.is_available()
                validation_report["models_accessible"][config["name"]] = is_available
                
                if not is_available:
                    validation_report["issues"].append(f"Model {config['name']} not accessible")
                    
            except Exception as e:
                validation_report["models_accessible"][config["name"]] = False
                validation_report["issues"].append(f"Error testing {config['name']}: {e}")
        
        # Overall validation
        if validation_report["issues"]:
            validation_report["config_valid"] = False
        
        return validation_report
    
    def _generate_model_responses(
        self, 
        model: LanguageModelInterface, 
        samples: List[BenchmarkSample], 
        split: str
    ) -> Path:
        """Generate responses for all samples and save to JSONL file."""
        from .evaluator import BenchmarkEvaluator
        
        # Create evaluator for response generation
        evaluator = BenchmarkEvaluator(
            model=model,
            metrics=self.metrics,
            schema=self.schema,
            categorical_fields=self.categorical_fields
        )
        
        # Create output file
        timestamp = int(time.time())
        filename = f"{model.model_name}_{split}_{timestamp}.jsonl"
        filepath = self.config.output_dir / "responses" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Generating responses to {filepath}")
        
        with open(filepath, 'w') as f:
            for i, sample in enumerate(samples):
                logger.info(f"Processing sample {i+1}/{len(samples)}: {sample.pmcid}")
                
                try:
                    # Generate prediction
                    prediction = evaluator.get_prediction_only(sample)
                    
                    if prediction is None:
                        logger.warning(f"Failed to generate prediction for {sample.pmcid}")
                        continue
                    
                    # Add metadata
                    response_data = {
                        "pmcid": sample.pmcid,
                        "model_name": model.model_name,
                        "timestamp": time.time(),
                        **prediction
                    }
                    
                    # Write to JSONL file
                    f.write(json.dumps(response_data) + '\n')
                    
                except Exception as e:
                    logger.error(f"Error processing sample {sample.pmcid}: {e}")
                    continue
        
        logger.info(f"Response generation completed: {filepath}")
        return filepath
    
    def _load_responses_from_file(self, response_file: Path) -> List[Dict[str, Any]]:
        """Load responses from a JSONL file."""
        responses = []
        
        with open(response_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    response = json.loads(line)
                    responses.append(response)
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON on line {line_num} in {response_file}: {e}")
                    continue
        
        logger.info(f"Loaded {len(responses)} responses from {response_file}")
        return responses
    
    def _extract_split_from_filename(self, filepath: Path) -> str:
        """Extract split name from response filename."""
        filename = filepath.stem
        parts = filename.split('_')
        
        # Filename format: {model_name}_{split}_{timestamp}
        if len(parts) >= 2:
            return parts[-2]  # Second to last part should be split
        
        return "test"  # Default fallback

    def _save_intermediate_result(self, result: EvaluationResult, split: str) -> None:
        """Save intermediate result to file."""
        timestamp = int(time.time())
        filename = f"{result.model_name}_{split}_{timestamp}.json"
        filepath = self.config.output_dir / "intermediate" / filename
        
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert result to serializable format
        result_dict = {
            "model_name": result.model_name,
            "total_samples": result.total_samples,
            "successful_predictions": result.successful_predictions,
            "failed_predictions": result.failed_predictions,
            "aggregate_metrics": result.aggregate_metrics,
            "error_analysis": result.error_analysis,
            "timestamp": timestamp
        }
        
        with open(filepath, 'w') as f:
            json.dump(result_dict, f, indent=2)
        
        logger.info(f"Intermediate result saved to {filepath}")
    
    def get_data_statistics(self, split: str = "train") -> Dict[str, Any]:
        """Get comprehensive statistics about the data."""
        samples = self.data_loader.load_split(split)
        return self.data_loader.get_statistics(samples)
    
    def export_predictions(
        self, 
        result: EvaluationResult, 
        split: str,
        format: str = "jsonl"
    ) -> Path:
        """Export model predictions for analysis."""
        return self.reporter.export_predictions(result, split, format)