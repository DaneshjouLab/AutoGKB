"""
Data models for the annotation extraction pipeline.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Union
from enum import Enum
from loguru import logger
from pathlib import Path
class AnnotationType(Enum):
    FUNCTIONAL = "functional"
    DRUG = "drug"
    PHENOTYPE = "phenotype"


class PhenotypeCategory(Enum):
    METABOLISM_PK = "Metabolism/PK"
    EFFICACY = "Efficacy"
    TOXICITY = "Toxicity"
    DOSAGE = "Dosage"
    OTHER = "Other"


class Significance(Enum):
    YES = "yes"
    NO = "no"
    NOT_STATED = "not stated"


class SpecialtyPopulation(Enum):
    PEDIATRIC = "Pediatric"
    GERIATRIC = "Geriatric"


class Direction(Enum):
    INCREASED = "increased"
    DECREASED = "decreased"


class Association(Enum):
    IS = "Is"
    IS_NOT = "Is Not"
    ARE = "Are"
    ARE_NOT = "Are Not"
@dataclass
class RelevanceResult:
    """Result of relevance screening."""
    is_relevant: bool
    summary: Optional[str] = None
    confidence: Optional[float] = None


@dataclass
class ExtractedEntity:
    """Single extracted entity."""
    entity_type: str
    value: str
    context: str
    supporting_text: str


@dataclass
class ExtractedEntities:
    """All extracted entities from an article."""
    genetic_variants: List[ExtractedEntity]
    drugs: List[ExtractedEntity]
    phenotypes: List[ExtractedEntity]
    population_info: List[ExtractedEntity]
    associations: List[ExtractedEntity]


@dataclass
class Relationship:
    """Variant-outcome relationship."""
    variant: str
    gene: str
    drug: Optional[str]
    phenotype: str
    association_type: str
    evidence_text: str
    statistical_measures: Optional[Dict[str, Union[str, float]]]


@dataclass
class ClassificationResult:
    """Result of annotation type classification."""
    relationship: Relationship
    annotation_types: List[AnnotationType]
    confidence: float
    evidence_summary: str


@dataclass
class AnnotationRow:
    """Generated annotation row for TSV output."""
    annotation_type: AnnotationType
    row_data: List[str]
    fields: List[str]
    
    def to_tsv(self) -> str:
        """Convert to TSV format."""
        return "\t".join(self.row_data)


@dataclass
class ValidationResult:
    """Result of quality validation."""
    is_valid: bool
    errors: List[str]
    corrected_row: Optional[AnnotationRow] = None
    confidence_score: Optional[float] = None