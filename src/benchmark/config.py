"""
Configuration management for the benchmarking system.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any
import json


@dataclass
class BenchmarkConfig:
    """Configuration class for benchmark system."""
    
    # Data paths
    data_dir: Path = field(default_factory=lambda: Path("data"))
    articles_dir: Path = field(default_factory=lambda: Path("data/articles"))
    benchmark_dir: Path = field(default_factory=lambda: Path("data/benchmark"))
    
    # Model configuration
    model_name: str = "claude-3-sonnet"
    model_params: Dict[str, Any] = field(default_factory=dict)
    max_tokens: int = 4000
    temperature: float = 0.0
    
    # Evaluation settings
    batch_size: int = 10
    max_articles: Optional[int] = None
    random_seed: int = 42
    
    # Metrics configuration
    exact_match_fields: List[str] = field(default_factory=lambda: [
        "gene", "drugs", "significance", "direction_of_effect", 
        "phenotype_category", "specialty_population"
    ])
    
    fuzzy_match_fields: List[str] = field(default_factory=lambda: [
        "variant_haplotypes", "alleles", "population_phenotypes_or_diseases"
    ])
    
    semantic_match_fields: List[str] = field(default_factory=lambda: [
        "sentence", "notes"
    ])
    
    # Scoring weights
    field_weights: Dict[str, float] = field(default_factory=lambda: {
        "gene": 1.0,
        "drugs": 1.0,
        "variant_haplotypes": 0.8,
        "significance": 1.2,
        "direction_of_effect": 1.2,
        "phenotype_category": 1.0,
        "sentence": 0.1,
        "alleles": 0.8,
        "specialty_population": 0.6,
        "population_phenotypes_or_diseases": 0.6
    })
    
    # Output configuration
    output_dir: Path = field(default_factory=lambda: Path("results"))
    save_predictions: bool = True
    save_detailed_results: bool = True
    
    @classmethod
    def from_file(cls, config_path: Path) -> "BenchmarkConfig":
        """Load configuration from JSON file."""
        with open(config_path, 'r') as f:
            config_dict = json.load(f)
        
        # Convert path strings to Path objects
        for key in ['data_dir', 'articles_dir', 'benchmark_dir', 'output_dir']:
            if key in config_dict:
                config_dict[key] = Path(config_dict[key])
        
        return cls(**config_dict)
    
    def to_file(self, config_path: Path) -> None:
        """Save configuration to JSON file."""
        config_dict = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Path):
                config_dict[key] = str(value)
            else:
                config_dict[key] = value
        
        with open(config_path, 'w') as f:
            json.dump(config_dict, f, indent=2)
    
    def validate(self) -> None:
        """Validate configuration parameters."""
        if not self.data_dir.exists():
            raise ValueError(f"Data directory does not exist: {self.data_dir}")
        
        if not self.articles_dir.exists():
            raise ValueError(f"Articles directory does not exist: {self.articles_dir}")
        
        if not self.benchmark_dir.exists():
            raise ValueError(f"Benchmark directory does not exist: {self.benchmark_dir}")
        
        if self.batch_size <= 0:
            raise ValueError("Batch size must be positive")
        
        if self.temperature < 0 or self.temperature > 2:
            raise ValueError("Temperature must be between 0 and 2")
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)