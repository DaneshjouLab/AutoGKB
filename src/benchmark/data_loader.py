"""
Data loading and preprocessing utilities for the benchmarking system.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from loguru import logger


@dataclass
class BenchmarkSample:
    """A single benchmark sample containing article and annotation."""
    pmcid: str
    article_title: str
    article_content: str
    annotation: Dict[str, Any]
    article_path: str


class BenchmarkDataLoader:
    """Loads and preprocesses benchmark data."""
    
    def __init__(self, data_dir: Path, articles_dir: Path, benchmark_dir: Path):
        self.data_dir = data_dir
        self.articles_dir = articles_dir
        self.benchmark_dir = benchmark_dir
        self.column_mapping = self._load_column_mapping()
    
    def _load_column_mapping(self) -> Dict[str, str]:
        """Load column mapping configuration."""
        mapping_path = self.benchmark_dir / "column_mapping.json"
        if mapping_path.exists():
            with open(mapping_path, 'r') as f:
                return json.load(f)
        return {}
    
    def load_split(self, split: str = "train") -> List[BenchmarkSample]:
        """Load a specific data split (train/val/test)."""
        split_path = self.benchmark_dir / f"{split}.jsonl"
        if not split_path.exists():
            raise FileNotFoundError(f"Split file not found: {split_path}")
        
        samples = []
        with open(split_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    annotation = json.loads(line.strip())
                    sample = self._create_sample(annotation)
                    if sample:
                        samples.append(sample)
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON at line {line_num}: {e}")
                except Exception as e:
                    logger.warning(f"Error processing line {line_num}: {e}")
        
        logger.info(f"Loaded {len(samples)} samples from {split} split")
        return samples
    
    def _create_sample(self, annotation: Dict[str, Any]) -> Optional[BenchmarkSample]:
        """Create a benchmark sample from annotation data."""
        pmcid = annotation.get("pmcid")
        if not pmcid:
            logger.warning("Missing PMCID in annotation")
            return None
        
        # Load article content
        article_content = self._load_article_content(pmcid)
        if not article_content:
            logger.warning(f"Could not load article content for {pmcid}")
            return None
        
        return BenchmarkSample(
            pmcid=pmcid,
            article_title=annotation.get("article_title", ""),
            article_content=article_content,
            annotation=annotation,
            article_path=annotation.get("article_path", f"articles/{pmcid}.md")
        )
    
    def _load_article_content(self, pmcid: str) -> Optional[str]:
        """Load article content from markdown file."""
        article_path = self.articles_dir / f"{pmcid}.md"
        if not article_path.exists():
            return None
        
        try:
            with open(article_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return self._preprocess_article_content(content)
        except Exception as e:
            logger.warning(f"Error reading article {pmcid}: {e}")
            return None
    
    def _preprocess_article_content(self, content: str) -> str:
        """Preprocess article content for model consumption."""
        # Remove excessive whitespace
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        
        # Clean up markdown formatting
        content = re.sub(r'^#{1,6}\s+', '', content, flags=re.MULTILINE)  # Remove header markers
        content = re.sub(r'\*\*(.*?)\*\*', r'\1', content)  # Remove bold formatting
        content = re.sub(r'\*(.*?)\*', r'\1', content)  # Remove italic formatting
        content = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', content)  # Remove links, keep text
        
        # Remove metadata section if present
        if content.startswith('# '):
            # Find the end of metadata section (usually after first ## heading)
            lines = content.split('\n')
            start_idx = 0
            for i, line in enumerate(lines):
                if line.startswith('## Abstract') or line.startswith('## Introduction'):
                    start_idx = i
                    break
            content = '\n'.join(lines[start_idx:])
        
        return content.strip()
    
    def get_field_schema(self) -> Dict[str, str]:
        """Get the schema of annotation fields."""
        return {
            "pmcid": "PubMed Central ID",
            "article_title": "Title of the article",
            "variant_annotation_id": "Unique identifier for the annotation",
            "variant_haplotypes": "Genetic variant or haplotype information",
            "gene": "Gene symbol or name",
            "drugs": "Drug name(s) involved in the association",
            "pmid": "PubMed ID",
            "phenotype_category": "Category of phenotype (Dosage, Efficacy, Metabolism/PK, etc.)",
            "significance": "Statistical significance (yes/no/not stated)",
            "notes": "Additional notes or context",
            "sentence": "Structured sentence describing the association",
            "alleles": "Specific alleles involved",
            "specialty_population": "Special population (Pediatric, etc.)",
            "metabolizer_types": "Metabolizer phenotype",
            "is_plural": "Grammatical form (Is/Are)",
            "is_is_not_associated": "Association type (Associated with/Not associated with)",
            "direction_of_effect": "Direction of effect (increased/decreased/null)",
            "pd_pk_terms": "Pharmacodynamic/pharmacokinetic terms",
            "multiple_drugs_and_or": "Conjunction for multiple drugs (and/or)",
            "population_types": "Population description",
            "population_phenotypes_or_diseases": "Disease or phenotype context",
            "multiple_phenotypes_or_diseases_and_or": "Conjunction for multiple conditions",
            "comparison_alleles_or_genotypes": "Comparison group genotypes",
            "comparison_metabolizer_types": "Comparison metabolizer types"
        }
    
    def get_categorical_fields(self) -> Dict[str, List[str]]:
        """Get possible values for categorical fields."""
        return {
            "significance": ["yes", "no", "not stated"],
            "phenotype_category": [
                "Dosage", "Efficacy", "Metabolism/PK", "Other", 
                "Toxicity", "Dosage, Efficacy", "Dosage, Metabolism/PK",
                "Efficacy, Metabolism/PK", "Other, Metabolism/PK"
            ],
            "direction_of_effect": ["increased", "decreased", None],
            "is_plural": ["Is", "Are"],
            "is_is_not_associated": ["Associated with", "Not associated with"],
            "multiple_drugs_and_or": ["and", "or"],
            "multiple_phenotypes_or_diseases_and_or": ["and", "or"],
            "specialty_population": ["Pediatric", None]
        }
    
    def get_statistics(self, samples: List[BenchmarkSample]) -> Dict[str, Any]:
        """Get statistics about the loaded samples."""
        if not samples:
            return {}
        
        stats = {
            "total_samples": len(samples),
            "unique_pmcids": len(set(s.pmcid for s in samples)),
            "avg_article_length": sum(len(s.article_content) for s in samples) / len(samples),
        }
        
        # Field completion rates
        field_counts = {}
        for sample in samples:
            for field, value in sample.annotation.items():
                if field not in field_counts:
                    field_counts[field] = 0
                if value is not None and value != "":
                    field_counts[field] += 1
        
        stats["field_completion_rates"] = {
            field: count / len(samples) for field, count in field_counts.items()
        }
        
        return stats