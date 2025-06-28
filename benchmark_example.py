#!/usr/bin/env python3
"""
Example usage of the AutoGKB benchmarking system.

This script demonstrates how to use the benchmarking framework to evaluate
language models on pharmacogenomic knowledge extraction tasks.

The benchmark system now supports two modes:

1. **Separated Response Generation and Evaluation**:
   - Generate model responses and save to JSONL files
   - Evaluate JSONL files separately to get scores
   - Allows for response caching and reuse across different evaluation metrics

2. **Combined Mode** (legacy):
   - Generate responses and evaluate in one step

Usage examples:
  python benchmark_example.py                    # Run full benchmark  
  python benchmark_example.py --validate         # Quick validation
  python benchmark_example.py --evaluate file.jsonl  # Evaluate specific response file
"""

import os
from pathlib import Path
from loguru import logger
from src.benchmark import BenchmarkPipeline, BenchmarkConfig
from dotenv import load_dotenv

load_dotenv()
logger.add("benchmark_example.log", rotation="10 MB")

def main():
    """Main example demonstrating benchmark usage."""
    
    # 1. Create configuration
    config = BenchmarkConfig(
        data_dir=Path("data"),
        articles_dir=Path("data/articles"),
        benchmark_dir=Path("data/benchmark"),
        output_dir=Path("benchmark_results"),
        model_name="claude-3-sonnet",  # Start with mock model for testing
        max_articles=10,    # Limit for example
        batch_size=5
    )
    
    # 2. Initialize pipeline
    pipeline = BenchmarkPipeline(config)
    
    # 3. Validate setup
    logger.info("Validating benchmark setup...")
    validation = pipeline.validate_setup()
    
    if not validation["config_valid"]:
        logger.error("Setup validation failed:")
        for issue in validation["issues"]:
            logger.error(f"  - {issue}")
        return
    
    logger.info("Setup validation passed!")
    logger.info(f"Data statistics: {validation['data_statistics']}")
    
    # 4. Get data statistics
    logger.info("Loading data statistics...")
    stats = pipeline.get_data_statistics("train")
    logger.info(f"Training data: {stats['total_samples']} samples")
    logger.info(f"Average article length: {stats['avg_article_length']:.0f} characters")
    
    # 5. Run benchmark on test models
    model_configs = [
        {
            "name": "claude-3-sonnet",
            "model_name": "claude-3-sonnet-20240229",
            "api_key": os.getenv("ANTHROPIC_API_KEY"),
            "temperature": 0.0,
            "max_tokens": 4000
        }
    ]
    
    # Add real models if API keys are available
    if os.getenv("OPENAI_API_KEY"):
        model_configs.append({
            "name": "gpt-4",
            "model_name": "gpt-4",
            "api_key": os.getenv("OPENAI_API_KEY"),
            "temperature": 0.0,
            "max_tokens": 4000
        })
    
    if os.getenv("ANTHROPIC_API_KEY"):
        model_configs.append({
            "name": "claude-3-sonnet",
            "model_name": "claude-3-sonnet-20240229",
            "api_key": os.getenv("ANTHROPIC_API_KEY"),
            "temperature": 0.0,
            "max_tokens": 4000
        })
    
    # 6. Generate responses first (separate from evaluation)
    logger.info(f"Generating responses with {len(model_configs)} models...")
    
    try:
        # Step 1: Generate responses and save to JSONL files
        response_files = pipeline.generate_responses(model_configs, split="train")  # Using train for example
        
        logger.info(f"Generated {len(response_files)} response files:")
        for model_name, response_file in response_files.items():
            logger.info(f"  {model_name}: {response_file}")
        
        # Step 2: Evaluate each response file separately
        logger.info("Evaluating response files...")
        results = {}
        for model_name, response_file in response_files.items():
            logger.info(f"Evaluating {model_name} responses...")
            result = pipeline.evaluate_responses_file(response_file)
            results[model_name] = result
        
        # 7. Print summary results
        logger.info("\n" + "="*50)
        logger.info("BENCHMARK RESULTS SUMMARY")
        logger.info("="*50)
        
        for model_name, result in results.items():
            metrics = result.aggregate_metrics
            logger.info(f"\nModel: {model_name}")
            logger.info(f"  Total samples: {result.total_samples}")
            logger.info(f"  Successful predictions: {result.successful_predictions}")
            logger.info(f"  Success rate: {result.successful_predictions/result.total_samples*100:.1f}%")
            logger.info(f"  Mean overall score: {metrics.get('mean_overall_score', 0):.3f}")
            logger.info(f"  Mean weighted score: {metrics.get('mean_weighted_score', 0):.3f}")
            
            # Show top performing fields
            field_stats = metrics.get('field_statistics', {})
            if field_stats:
                best_fields = sorted(
                    field_stats.items(), 
                    key=lambda x: x[1].get('mean_score', 0), 
                    reverse=True
                )[:3]
                
                logger.info("  Top performing fields:")
                for field, stats in best_fields:
                    score = stats.get('mean_score', 0)
                    exact_match = stats.get('exact_match_rate', 0) * 100
                    logger.info(f"    {field}: {score:.3f} (exact match: {exact_match:.1f}%)")
        
        # 8. Analyze a specific sample
        if results and config.max_articles and config.max_articles > 0:
            logger.info("\n" + "="*50)
            logger.info("SAMPLE ANALYSIS")
            logger.info("="*50)
            
            # Get first PMCID from results
            first_result = next(iter(results.values()))
            if first_result.sample_scores:
                sample_pmcid = first_result.sample_scores[0].pmcid
                
                logger.info(f"Analyzing sample: {sample_pmcid}")
                
                # Analyze with first available model
                first_model_config = model_configs[0]
                analysis = pipeline.analyze_sample(
                    sample_pmcid, 
                    first_model_config,
                    split="train"
                )
                
                logger.info(f"Article title: {analysis['article_title']}")
                logger.info(f"Model: {analysis['model']}")
                
                if analysis['scores']:
                    logger.info(f"Overall score: {analysis['scores']['overall_score']:.3f}")
                    logger.info(f"Weighted score: {analysis['scores']['weighted_score']:.3f}")
        
        logger.info("\n" + "="*50)
        logger.info("Benchmark completed successfully!")
        logger.info(f"Results saved to: {config.output_dir}")
        logger.info("="*50)
        
    except Exception as e:
        logger.error(f"Benchmark failed: {e}")
        raise


def run_quick_validation():
    """Quick validation without running full benchmark."""
    config = BenchmarkConfig(max_articles=1)
    pipeline = BenchmarkPipeline(config)
    
    validation = pipeline.validate_setup()
    
    print("=== BENCHMARK VALIDATION ===")
    print(f"Config valid: {validation['config_valid']}")
    print(f"Data available: {validation['data_available']}")
    
    if validation.get('data_statistics'):
        stats = validation['data_statistics']
        print(f"Train samples: {stats.get('train_samples', 0)}")
        print(f"Val samples: {stats.get('val_samples', 0)}")
        print(f"Test samples: {stats.get('test_samples', 0)}")
    
    print("\nModel accessibility:")
    for model, accessible in validation.get('models_accessible', {}).items():
        print(f"  {model}: {'✓' if accessible else '✗'}")
    
    if validation.get('issues'):
        print("\nIssues found:")
        for issue in validation['issues']:
            print(f"  - {issue}")
    
    return validation['config_valid']


def evaluate_response_file(response_file_path: str):
    """Example of evaluating a standalone JSONL response file."""
    logger.info(f"Evaluating standalone response file: {response_file_path}")
    
    # Create minimal config for evaluation only
    config = BenchmarkConfig(
        data_dir=Path("data"),
        articles_dir=Path("data/articles"), 
        benchmark_dir=Path("data/benchmark"),
        output_dir=Path("benchmark_results")
    )
    
    # Initialize pipeline
    pipeline = BenchmarkPipeline(config)
    
    # Evaluate the response file
    try:
        result = pipeline.evaluate_responses_file(Path(response_file_path))
        
        logger.info("\n" + "="*50)
        logger.info("EVALUATION RESULTS")
        logger.info("="*50)
        logger.info(f"Model: {result.model_name}")
        logger.info(f"Total samples: {result.total_samples}")
        logger.info(f"Successful predictions: {result.successful_predictions}")
        logger.info(f"Success rate: {result.successful_predictions/result.total_samples*100:.1f}%")
        
        metrics = result.aggregate_metrics
        logger.info(f"Mean overall score: {metrics.get('mean_overall_score', 0):.3f}")
        logger.info(f"Mean weighted score: {metrics.get('mean_weighted_score', 0):.3f}")
        
        # Show field performance
        field_stats = metrics.get('field_statistics', {})
        if field_stats:
            logger.info("\nField performance:")
            for field, stats in field_stats.items():
                score = stats.get('mean_score', 0)
                exact_match = stats.get('exact_match_rate', 0) * 100
                logger.info(f"  {field}: {score:.3f} (exact match: {exact_match:.1f}%)")
        
        return result
        
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        raise


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--validate":
        # Quick validation mode
        success = run_quick_validation()
        sys.exit(0 if success else 1)
    elif len(sys.argv) > 2 and sys.argv[1] == "--evaluate":
        # Evaluate specific response file
        response_file = sys.argv[2]
        evaluate_response_file(response_file)
    else:
        # Full benchmark mode
        main()