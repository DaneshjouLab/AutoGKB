# AutoGKB Benchmarking System

A comprehensive framework for evaluating language model performance on pharmacogenomic knowledge extraction from scientific articles.

## Overview

This benchmarking system provides standardized evaluation of language models' ability to extract structured pharmacogenomic annotations from scientific literature. It implements the specifications outlined in the [Benchmarking System PRD](../../docs/benchmarking_system_prd.md).

### Key Features

- **Separated Response Generation and Evaluation**: Generate model responses to JSONL files, then evaluate separately
- **Response Caching**: Reuse generated responses for different evaluation metrics  
- **Flexible Evaluation**: Evaluate any JSONL response file from external models
- **Multi-model Support**: OpenAI, Anthropic, and custom models
- **Comprehensive Metrics**: Field-specific scoring with weighted aggregation

## Quick Start

### 1. Separated Response Generation and Evaluation (Recommended)

```python
from pathlib import Path
from src.benchmark import BenchmarkPipeline, BenchmarkConfig

# Create configuration
config = BenchmarkConfig(
    data_dir=Path("data"),
    max_articles=50,
    output_dir=Path("benchmark_results")
)

# Initialize pipeline
pipeline = BenchmarkPipeline(config)

# Step 1: Generate responses to JSONL files
model_configs = [
    {"name": "claude-3-sonnet", "model_name": "claude-3-sonnet-20240229"},
    {"name": "gpt-4", "model_name": "gpt-4"}
]

response_files = pipeline.generate_responses(model_configs, split="test")
# Output: {'claude-3-sonnet': Path('benchmark_results/responses/claude-3-sonnet_test_123456.jsonl'), ...}

# Step 2: Evaluate response files separately
results = {}
for model_name, response_file in response_files.items():
    result = pipeline.evaluate_responses_file(response_file)
    results[model_name] = result
```

### 2. Combined Mode (Legacy)

```python
# Traditional approach - generates and evaluates in one step
results = pipeline.run_benchmark(model_configs, split="test")
```

### 3. Evaluate External Response Files

```python
# Evaluate any JSONL response file (from external models/systems)
result = pipeline.evaluate_responses_file(Path("path/to/external_responses.jsonl"))
print(f"Score: {result.aggregate_metrics['mean_overall_score']:.3f}")
```

### 4. Using the Example Script

```bash
# Validate setup
python benchmark_example.py --validate

# Run full benchmark (separated workflow)
python benchmark_example.py

# Evaluate specific response file
python benchmark_example.py --evaluate benchmark_results/responses/gpt-4_test_123456.jsonl
```

### 5. Configuration File

```python
from src.benchmark import BenchmarkConfig

# Load from JSON
config = BenchmarkConfig.from_file(Path("config/benchmark_config.json"))

# Or create programmatically
config = BenchmarkConfig(
    data_dir=Path("data"),
    output_dir=Path("benchmark_results"),
    max_articles=100
)
```

## Architecture

### Core Components

1. **BenchmarkDataLoader**: Loads and preprocesses articles and annotations
2. **EvaluationMetrics**: Implements scoring functions for different field types
3. **LanguageModelInterface**: Abstracts different LM APIs (OpenAI, Anthropic, etc.)
4. **BenchmarkEvaluator**: Orchestrates prediction generation and evaluation
5. **BenchmarkPipeline**: Main interface for running benchmarks
6. **BenchmarkReporter**: Generates reports and visualizations

### Data Flow

#### Separated Workflow (Recommended)
```
Articles (Markdown) + Annotations (JSONL) 
    ↓
BenchmarkDataLoader → BenchmarkSample objects
    ↓
LanguageModel → Response Generation → JSONL Files
    ↓
JSONL Files → Evaluation → Scores
    ↓
BenchmarkReporter → Reports
```

#### Combined Workflow (Legacy)
```
Articles (Markdown) + Annotations (JSONL) 
    ↓
BenchmarkDataLoader → BenchmarkSample objects
    ↓
LanguageModel → Predictions → EvaluationMetrics → Scores
    ↓
BenchmarkReporter → Reports
```

## Evaluation Tasks

### Task 1: Entity Extraction
- **Goal**: Extract genes, drugs, variants from articles
- **Metrics**: Precision, Recall, F1-score per entity type
- **Fields**: `gene`, `drugs`, `variant_haplotypes`, `alleles`

### Task 2: Relationship Classification  
- **Goal**: Classify pharmacogenomic associations and effects
- **Metrics**: Classification accuracy, confusion matrices
- **Fields**: `significance`, `direction_of_effect`, `phenotype_category`

### Task 3: Structured Sentence Generation
- **Goal**: Generate standardized sentences describing relationships
- **Metrics**: BLEU, ROUGE, semantic similarity
- **Fields**: `sentence`

### Task 4: Population Context Extraction
- **Goal**: Identify specialty populations and disease contexts
- **Metrics**: Multi-label classification metrics
- **Fields**: `specialty_population`, `population_phenotypes_or_diseases`

## Scoring System

### Field Types and Scoring

1. **Exact Match Fields** (Score: 1.0 or 0.0)
   - Categorical fields requiring precise matches
   - Examples: `significance`, `direction_of_effect`

2. **Fuzzy Match Fields** (Score: 0.0-1.0)
   - Entity names allowing for variations
   - Uses sequence similarity with thresholds
   - Examples: `gene`, `drugs`, `variant_haplotypes`

3. **Semantic Match Fields** (Score: 0.0-1.0)
   - Free text requiring semantic understanding
   - Uses token-based similarity (extensible to embeddings)
   - Examples: `sentence`, `notes`

### Weighted Scoring

Fields are weighted by importance:
- **High importance** (1.2): `significance`, `direction_of_effect`
- **Standard importance** (1.0): `gene`, `drugs`, `phenotype_category`
- **Lower importance** (0.6-0.8): Population context fields

## Model Support

### Supported Models

1. **OpenAI Models**: GPT-4, GPT-3.5-turbo
2. **Anthropic Models**: Claude-3-Sonnet, Claude-3-Haiku
3. **Mock Model**: For testing and development

### Adding New Models

```python
from src.benchmark.models import LanguageModelInterface, ModelResponse

class MyCustomModel(LanguageModelInterface):
    def generate(self, prompt: str, **kwargs) -> ModelResponse:
        # Implementation here
        pass
    
    def is_available(self) -> bool:
        # Check availability
        pass
```

## Output and Reporting

### Generated Files

#### Response Generation Phase
1. **Response Files** (`responses/{model}_{split}_{timestamp}.jsonl`): Model predictions in JSONL format
   ```json
   {"pmcid": "PMC123", "model_name": "gpt-4", "timestamp": 1234567890, "gene": "CYP2C9", "drugs": "warfarin", ...}
   ```

#### Evaluation Phase  
2. **Summary Report** (`summary.html`): Comparative overview
3. **Detailed Reports** (`{model}_detailed.json`): Per-model analysis
4. **Performance Comparison** (`performance_comparison.json`): Side-by-side metrics
5. **Intermediate Results** (`intermediate/{model}_{split}_{timestamp}.json`): Evaluation results

### JSONL Response File Format

Each line contains a complete model prediction:
```json
{
  "pmcid": "PMC1234567",
  "model_name": "gpt-4",
  "timestamp": 1703123456.789,
  "gene": "CYP2C9",
  "drugs": "warfarin",
  "significance": "yes",
  "direction_of_effect": "decreased",
  "phenotype_category": "Dosage",
  "sentence": "CYP2C9 variants are associated with decreased warfarin dose requirements.",
  "alleles": "*2/*3",
  "comparison_alleles_or_genotypes": "*1/*1"
}
```

### Export Formats

- **JSONL**: Sample-level predictions and scores (primary format)
- **CSV**: Tabular format for statistical analysis  
- **JSON**: Structured data for programmatic access

## Configuration Options

### Key Parameters

```python
@dataclass
class BenchmarkConfig:
    # Data paths
    data_dir: Path
    articles_dir: Path
    benchmark_dir: Path
    
    # Model settings
    model_name: str
    temperature: float = 0.0
    max_tokens: int = 4000
    
    # Evaluation settings
    batch_size: int = 10
    max_articles: Optional[int] = None
    
    # Field weights and matching strategies
    field_weights: Dict[str, float]
    exact_match_fields: List[str]
    fuzzy_match_fields: List[str]
    semantic_match_fields: List[str]
```

## Advanced Usage

### Single Sample Analysis

```python
# Analyze specific sample in detail
analysis = pipeline.analyze_sample(
    pmcid="PMC1234567",
    model_config={"name": "gpt-4", "model_name": "gpt-4"},
    split="test"
)

print(f"Prediction: {analysis['prediction']}")
print(f"Ground truth: {analysis['ground_truth']}")
print(f"Scores: {analysis['scores']}")
```

### Custom Evaluation Metrics

```python
from src.benchmark.metrics import EvaluationMetrics

# Create custom metrics with different weights
custom_metrics = EvaluationMetrics(field_weights={
    "gene": 2.0,  # Higher weight for gene extraction
    "significance": 1.5,
    "drugs": 1.0
})

evaluator = BenchmarkEvaluator(model, custom_metrics, schema, categorical_fields)
```

### Batch Processing

```python
# Process large datasets efficiently
config.batch_size = 50  # Larger batches
config.max_articles = 1000  # Limit for faster iteration

results = pipeline.run_benchmark(model_configs, split="test")
```

## API Reference

### Core Classes

- **BenchmarkPipeline**: Main interface
  - `generate_responses()`: Generate model responses to JSONL files
  - `evaluate_responses_file()`: Evaluate JSONL response file and return scores
  - `run_benchmark()`: Complete benchmark (generates + evaluates)
  - `validate_setup()`: Check configuration
  - `analyze_sample()`: Single sample analysis

- **BenchmarkConfig**: Configuration management
  - `from_file()`: Load from JSON
  - `validate()`: Check settings

- **EvaluationMetrics**: Scoring functions
  - `evaluate_sample()`: Score single prediction
  - `aggregate_results()`: Compute summary statistics

### Model Interfaces

- **LanguageModelInterface**: Abstract base class
- **OpenAIModel**: OpenAI API integration
- **AnthropicModel**: Anthropic API integration
- **MockModel**: Testing model

## Best Practices

### 1. Development Workflow
1. Start with `MockModel` for testing
2. Use small `max_articles` for development
3. Validate setup before full runs
4. Monitor API costs and rate limits

### 2. Production Evaluation
1. Use full test set for final evaluation
2. Set `temperature=0.0` for reproducibility
3. Run multiple evaluation rounds for statistical significance
4. Save intermediate results for recovery

### 3. Performance Optimization
1. Use separated workflow to cache responses
2. Use appropriate batch sizes
3. Parallelize evaluation when feasible
4. Monitor memory usage with large datasets

## Separated vs Combined Workflows

### Benefits of Separated Workflow

1. **Cost Efficiency**: Avoid re-running expensive API calls during metric development
2. **Flexibility**: Evaluate external model responses from any source
3. **Debugging**: Inspect intermediate responses for issues
4. **Parallelization**: Generate responses and evaluation can be distributed
5. **Metric Development**: Iterate on evaluation metrics without regenerating responses
6. **Comparison**: Evaluate same responses with different metric configurations

### When to Use Each Approach

**Use Separated Workflow When:**
- Developing or iterating on evaluation metrics
- Working with expensive API models  
- Need to evaluate external model outputs
- Want to cache responses for multiple evaluations
- Distributing workload across systems

**Use Combined Workflow When:**
- Quick one-off evaluations
- Working with local/fast models
- Simple benchmarking scenarios

## Troubleshooting

### Common Issues

1. **Data Loading Errors**
   - Check file paths in configuration
   - Verify JSONL format integrity
   - Ensure article files exist

2. **Model API Errors**
   - Verify API keys are set
   - Check rate limits and quotas
   - Handle network timeouts

3. **Evaluation Errors**
   - Check JSON parsing in model responses
   - Validate field schema consistency
   - Handle missing or malformed predictions

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable detailed logging
pipeline = BenchmarkPipeline(config)
```

## Contributing

### Adding Features

1. **New Models**: Implement `LanguageModelInterface`
2. **New Metrics**: Extend `EvaluationMetrics`
3. **New Reports**: Add to `BenchmarkReporter`

### Testing

```bash
# Run validation
python benchmark_example.py --validate

# Test with mock model
python -c "
from src.benchmark import *
config = BenchmarkConfig(model_name='mock', max_articles=1)
pipeline = BenchmarkPipeline(config)
results = pipeline.run_benchmark([{'name': 'mock', 'model_name': 'mock'}])
"
```

## License

See [LICENSE](../../LICENSES/) for details.